# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import base64
import csv
import logging
import zipfile
import io
import jinja2
import os
import datetime
from cStringIO import StringIO

from odoo import models, fields, api, exceptions, _
from odoo.tools.safe_eval import safe_eval
from odoo.modules.module import get_module_resource

_logger = logging.getLogger(__name__)


class DJcompilation(models.Model):
    """Use discs to create songs from scratch and save it in compact format"""

    _name = 'dj.compilation'

    name = fields.Selection([])
    data_mode = fields.Selection(
        selection=[
            ('install', 'Install'),
            ('demo', 'Demo'),
        ],
        default='install',
    )
    sample_ids = fields.One2many('dj.sample', 'compilation_id')
    disc_template = fields.Char(
        default='base_dj:discs/default.disc',
        required=True,
    )
    disc_path = fields.Char(
        default='songs/{data_mode}/{name}.py',
        required=True,
    )
    compact_disc = fields.Binary(
        # TODO: make this volatile (use a controller for instance
        # or cleanup attachments w/ a cron?)
        help="Resulting Zip file with all songs and related files",
        attachment=True
    )
    album_title = fields.Char(default='songs.zip')

    @api.model
    def check_company_codename(self):
        """Check company short codenames have been setup in multi company.

        We need those to create unique codenames
        """
        Company = self.env['res.company']
        company_num = Company.search_count([])
        if company_num == 1:
            return
        companies = Company.search([('aka', '=', False)])
        if companies:
            raise exceptions.UserError(
                _("Companies miss `aka` unique code: %s") % ', '.join(
                    companies.mapped('name')
                )
            )

    @api.multi
    def get_all_tracks(self):
        """Return all files to burn into the compilation."""
        self.ensure_one()
        files = []
        for sample in self.sample_ids:
            files.extend(sample.burn_track())
        files.append(self.burn_disc())
        return files

    @api.multi
    def get_template_vars(self):
        """Return context variables to render disc's template."""
        self.ensure_one()
        return {'samples': self.sample_ids}

    @api.multi
    def get_disc_template(self):
        """Retrieve Jinja template for current disc."""
        self.ensure_one()
        # load Jinja template
        mod, filepath = self.disc_template.split(':')
        filepath = get_module_resource(mod, filepath)
        path, filename = os.path.split(filepath)
        return jinja2.Environment(
            loader=jinja2.FileSystemLoader(path)
        ).get_template(filename)

    @api.multi
    def burn_disc(self):
        """Burn the disc with songs."""
        self.ensure_one()
        template = self.get_disc_template()
        path = self.disc_path.format(name=self.name, data_mode=self.data_mode)
        return path, template.render(**self.get_template_vars())

    @api.multi
    def burn(self):
        """Burn disc into a zip file."""
        self.check_company_codename()
        for rec in self:
            files = rec.get_all_tracks()
            in_mem_zip = io.BytesIO()
            with zipfile.ZipFile(in_mem_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                for filepath, data in files:
                    zf.writestr(filepath, data)
            in_mem_zip.seek(0)
            zip_file = base64.encodestring(in_mem_zip.read())
            rec.album_title = rec.make_album_title()
            rec.compact_disc = zip_file

    def make_album_title(self):
        dt = datetime.datetime.now().strftime('%Y%m%d_%H%M')
        return '{}_{}-{}.zip'.format(self.name, self.data_mode, dt)


class Sample(models.Model):
    _name = 'dj.sample'
    _order = 'sequence ASC, create_date ASC'

    compilation_id = fields.Many2one(
        comodel_name='dj.compilation',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(
        'Sequence',
        help="Sequence for the handle.",
        default=10
    )
    model_id = fields.Many2one('ir.model', required=True)
    # basically used on for the domain widget
    model_name = fields.Char(related='model_id.model', readonly=True)
    model_fields_ids = fields.Many2many(
        comodel_name='ir.model.fields',
        string='Fields',
        domain="[('store', '=', True), ('model_id', '=', model_id)]",
    )
    name = fields.Char(compute='_compute_sample_name')
    csv_path = fields.Char(default='data/{data_mode}/{model}.csv')
    domain = fields.Char(default="[]")
    model_context = fields.Char(default="{'tracking_disable':1}")
    # field_list = fields.Char(
    #     default="name",
    #     help="List of field to export separated by ','"
    # )
    # TODO
    # xmlid_fields = fields.Char(help="List of field to use to generate unique"
    #                                 " xmlid separated by ','")

    @api.multi
    @api.depends('model_id.model')
    def _compute_sample_name(self):
        for item in self:
            item.name = (item.model_id.model or '').replace('.', '_')

    @api.model
    def eval_domain(self):
        # TODO: use domain widget
        # https://github.com/OCA/web/pull/672
        return safe_eval(self.domain) or []

    @api.model
    def csv_from_data(self, fields, rows):
        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)

        writer.writerow([name.encode('utf-8') for name in fields])

        for data in rows:
            row = []
            for i, col in enumerate(data):
                if isinstance(col, unicode):
                    try:
                        col = col.encode('utf-8')
                    except UnicodeError:
                        pass
                if col is False:
                    col = None

                # Spreadsheet apps
                # tend to detect formulas on leading =, + and -
                if type(col) is str and col.startswith(('=', '-', '+')):
                    col = "'" + col

                row.append(col)
            writer.writerow(row)

        fp.seek(0)
        data = fp.read()
        fp.close()
        return data

    @property
    def sample_model(self):
        return self.env[self.model_id.model]

    def real_csv_path(self):
        return self.csv_path.format(
            model=self.sample_model._name,
            data_mode=self.compilation_id.data_mode,
        )

    @api.multi
    def burn_track(self):
        self.ensure_one()
        items = self.sample_model.search(self.eval_domain())
        csv_path, csv_data = self.make_csv(items)
        return [
            (csv_path, csv_data),
        ]

    def get_burn_field_names(self):
        field_names = ['id']
        for field in self.model_fields_ids:
            name = field.name
            if field.ttype == 'many2one':
                name += '/id'
            field_names.append(name)
        if ('company_id' in self.sample_model and
                'company_id/id' not in field_names):
            field_names.append('company_id/id')
        return field_names

    def make_csv(self, items):
        # TODO create xmlid starting with __setup__
        # XXX detect auto generated xmlids
        field_names = self.get_burn_field_names()
        export_data = items.export_data(field_names).get('datas', [])
        return (
            self.real_csv_path(),
            self.csv_from_data(field_names, export_data)
        )
