# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
from cStringIO import StringIO

import base64
import csv
import logging
import zipfile
import io
import jinja2
import os

from odoo import models, fields, api
from odoo.tools.safe_eval import safe_eval
from odoo.modules.module import get_module_resource
_logger = logging.getLogger(__name__)


class DJ(models.Model):
    """Use discs to create songs from scratch and save it in compact format"""

    _name = 'dj'

    name = fields.Selection([])
    sample_ids = fields.One2many('dj.sample', 'dj_id')
    disc_template = fields.Char(default='base_scratch:discs/default.disc')
    disc_path = fields.Char(default='songs/install/{name}')
    compact_disc = fields.Binary(
        help="Resulting Zip file with all songs and related files",
        attachment=True)
    album_title = fields.Char(default='out.zip')

    @api.model
    def check_company_codename(self):
        """ Check company short codenames have been setup in multi company
        We need those to create unique codenames
        """
        Company = self.env['res.company']
        company_num = Company.search_count([])
        if company_num == 1:
            return
        companies = Company.search([('aka', '=', False)])
        if companies:
            raise  # TODO missing aka

    @api.multi
    def get_all_tracks(self):
        """ Return all csv generated from dj.samples """
        self.ensure_one()
        files = []
        for sample in self.sample_ids:
            files.extend(sample.burn_track())
        files.append(self.burn_disc())
        return files

    @api.multi
    def get_template_vars(self):
        """ Return list of variable for Jinja

        Get name model and path of samples.

        To be inherited
        """
        self.ensure_one()
        return {'samples': self.sample_ids}

    @api.multi
    def get_disc_template(self):
        self.ensure_one()
        # load Jinja template
        mod, filepath = self.disc_template.split(':')
        filepath = get_module_resource(mod, filepath)
        path, filename = os.path.split(filepath)
        return jinja2.Environment(
            loader=jinja2.FileSystemLoader(path)
        ).get_template(path)

    @api.multi
    def burn_disc(self):
        self.ensure_one()
        template = self.get_disc_template()
        path = self.disc_path.format(name=self.name)
        return path, template.render(**self.get_template_vars())

    @api.multi
    def burn(self):
        """ Return a zip file containing all required files """
        self.check_company_codename()
        for rec in self:
            files = rec.get_all_tracks()
            in_mem_zip = io.BytesIO()
            with zipfile.ZipFile(in_mem_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                for filepath, data in files:
                    zf.writestr(filepath, data)
            in_mem_zip.seek(0)
            zip_file = base64.encodestring(in_mem_zip.read())
            rec.compact_disc = zip_file


class Sample(models.Model):
    _name = 'dj.sample'

    dj_id = fields.Many2one('dj', required=True)
    model_id = fields.Many2one('ir.model', required=True)
    name = fields.Char(compute='_compute_sample_name')
    csv_path = fields.Char()
    domain = fields.Char(default="[]")
    field_list = fields.Char(help="List of field to export separated by ','")
    xmlid_fields = fields.Char(help="List of field to use to generate unique"
                                    " xmlid separated by ','")

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
            for d in data:
                if isinstance(d, unicode):
                    try:
                        d = d.encode('utf-8')
                    except UnicodeError:
                        pass
                if d is False:
                    d = None

                # Spreadsheet apps
                # tend to detect formulas on leading =, + and -
                if type(d) is str and d.startswith(('=', '-', '+')):
                    d = "'" + d

                row.append(d)
            writer.writerow(row)

        fp.seek(0)
        data = fp.read()
        fp.close()
        return data

    def burn_csv(self, items):
        # TODO create xmlid starting with __setup__
        # XXX detect auto generated xmlids
        field_names = ['id']
        field_names.extend([f.strip() for f in self.field_list.split(',')])
        if 'company_id' in self.model_id.field_id.mapped('name'):
            field_names.append('company_id')
        export_data = items.export_data(field_names).get('datas', [])
        return self.csv_path, self.csv_from_data(field_names, export_data)

    @api.multi
    def burn_track(self):
        self.ensure_one()
        items = self.env[self.model_id.model].search(self.eval_domain())
        csv_path, csv_data = self.burn_csv(items)
        return [
            (csv_path, csv_data),
        ]
