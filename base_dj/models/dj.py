# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import csv
import zipfile
import io
import jinja2
import os
import datetime
from cStringIO import StringIO

from odoo import models, fields, api, exceptions, _
from odoo.tools.safe_eval import safe_eval
from odoo.modules.module import get_module_resource
from odoo.addons.website.models.website import slugify, slug


IGNORED_FORM_FIELDS = [
    'display_name',
    '__last_update',
    # TODO: retrieve from inherited schema
    'message_ids',
    'message_follower_ids',
    'message_follower',
    'message_last_post',
    'message_unread',
    'message_unread_counter',
    'message_needaction_counter',
    'website_message_ids',
] + models.MAGIC_COLUMNS


class TemplateMixin(models.AbstractModel):

    _name = 'dj.template.mixin'

    template_path = fields.Char(
        default=lambda self: self._default_dj_template_path,
        required=True,
    )

    _default_dj_template_path = ''

    @api.multi
    def dj_template_vars(self):
        """Return context variables to render template."""
        self.ensure_one()
        return {}

    @api.multi
    def dj_template(self, path=None):
        """Retrieve Jinja template."""
        self.ensure_one()
        path = path or self.template_path
        # load Jinja template
        mod, filepath = path.split(':')
        filepath = get_module_resource(mod, filepath)
        path, filename = os.path.split(filepath)
        return jinja2.Environment(
            loader=jinja2.FileSystemLoader(path)
        ).get_template(filename)

    def dj_render_template(self):
        template = self.dj_template()
        return template.render(**self.dj_template_vars())


class DJcompilation(models.Model):
    """Use discs to create songs from scratch and save it in compact format"""

    _name = 'dj.compilation'
    _inherit = 'dj.template.mixin'
    _default_dj_template_path = 'base_dj:discs/disc.tmpl'

    name = fields.Char()
    genre = fields.Selection([])
    data_mode = fields.Selection(
        selection=[
            ('install', 'Install'),
            ('demo', 'Demo'),
        ],
        default='install',
    )
    song_ids = fields.One2many('dj.song', 'compilation_id')
    disc_path = fields.Char(
        default='songs/{data_mode}/generated/{genre}.py',
        required=True,
    )
    download_url = fields.Char(compute='_compute_download_url')

    @api.multi
    @api.depends()
    def _compute_download_url(self):
        for item in self:
            item.download_url = \
                u'/dj/download/compilation/{}'.format(slug(self))

    @api.multi
    def dj_template_vars(self):
        """Return context variables to render disc's template."""
        self.ensure_one()
        values = super(DJcompilation, self).dj_template_vars()
        values.update({'songs': self.song_ids})
        return values

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
        for song in self.song_ids:
            files.extend(song.burn_track())
        files.append(self.burn_disc())
        files.append(self.burn_dev_readme())
        return files

    def disc_full_path(self):
        return self.disc_path.format(**self.read()[0])

    @api.multi
    def burn_disc(self):
        """Burn the disc with songs."""
        self.ensure_one()
        return self.disc_full_path(), self.dj_render_template()

    @api.multi
    def burn_dev_readme(self):
        """Burn and additional readme for developers."""
        self.ensure_one()
        template = self.dj_template(path='base_dj:discs/DEV_README.tmpl')
        return 'DEV_README.rst', template.render(compilation=self)

    @api.multi
    def burn(self):
        """Burn disc into a zip file."""
        self.ensure_one()
        self.check_company_codename()
        files = self.get_all_tracks()
        in_mem_zip = io.BytesIO()
        with zipfile.ZipFile(in_mem_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for filepath, data in files:
                zf.writestr(filepath, data)
        in_mem_zip.seek(0)
        filename = self.make_album_title()
        return filename, in_mem_zip.read()

    def make_album_title(self):
        dt = datetime.datetime.now().strftime('%Y%m%d_%H%M')
        return '{}_{}-{}.zip'.format(
            slugify(self.name).replace('-', '_'),
            self.data_mode, dt)

    @api.multi
    def download_compilation(self):
        """Download zip file."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': self.download_url,
        }


class song(models.Model):
    _name = 'dj.song'
    _inherit = 'dj.template.mixin'
    _order = 'sequence ASC, create_date ASC'
    _default_dj_template_path = 'base_dj:discs/song.tmpl'

    compilation_id = fields.Many2one(
        string='Compilation',
        comodel_name='dj.compilation',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(
        'Sequence',
        help="Sequence for the handle.",
        default=10
    )
    model_id = fields.Many2one(
        string='Model',
        comodel_name='ir.model',
        required=True
    )
    # basically used on for the domain widget
    model_name = fields.Char(related='model_id.model', readonly=True)
    model_fields_ids = fields.Many2many(
        comodel_name='ir.model.fields',
        relation='song_model_fields_rel',
        string='Fields',
        domain="""[
            ('store', '=', True),
            ('model_id', '=', model_id),
            ('compute', '=', False),
        ]""",
    )
    model_fields_blacklist_ids = fields.Many2many(
        comodel_name='ir.model.fields',
        relation='song_model_fields_blacklist_rel',
        string='Fields blacklist',
        domain="""[
            ('store', '=', True),
            ('model_id', '=', model_id),
            ('compute', '=', False),
        ]""",
    )
    name = fields.Char(compute='_compute_song_name')
    csv_path = fields.Char(default='data/{data_mode}/generated/{model}.csv')
    domain = fields.Char(default="[]")
    model_context = fields.Char(default="{'tracking_disable':1}")
    xmlid_fields = fields.Char(
        help="List of field to use to generate unique "
             "xmlid separated by ','.",
        default='',
    )

    @api.multi
    def dj_template_vars(self):
        """Return context variables to render template."""
        self.ensure_one()
        return {
            'song': self,
            'header_exclude': self.get_csv_field_names_exclude(),
        }

    @api.multi
    @api.depends('model_id.model')
    def _compute_song_name(self):
        for item in self:
            item.name = (item.model_id.model or '').replace('.', '_')

    @api.model
    def eval_domain(self):
        return safe_eval(self.domain) or []

    @api.model
    def csv_from_data(self, fields, rows):
        """Copied from std odoo export in controller."""
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
    def song_model(self):
        return self.env[self.model_id.model]

    def real_csv_path(self):
        """Final csv path into zip file."""
        return self.csv_path.format(
            model=self.song_model._name,
            data_mode=self.compilation_id.data_mode,
        )

    @api.multi
    def burn_track(self):
        """Search items and burn the track for the compilations."""
        self.ensure_one()
        csv_path, csv_data = self.make_csv()
        return [
            (csv_path, csv_data),
        ]

    def _get_all_fields(self):
        names = set(
            self.song_model.fields_get().keys()
        ).difference(set(IGNORED_FORM_FIELDS))
        return self.env['ir.model.fields'].search([
            ('model', '=', self.model_name),
            ('store', '=', True),
            ('compute', '=', False),
            ('name', 'in', list(names)),
        ])

    def get_csv_field_names(self):
        """Retrieve CSV field names."""
        field_names = ['id']
        _fields = self.model_fields_ids
        if not _fields:
            _fields = self._get_all_fields()
        blacklisted = self.model_fields_blacklist_ids.mapped('name')
        for field in _fields:
            if field.name in blacklisted:
                continue
            name = field.name
            # we always want xmlids
            # many2many are handled specifically by `export_data`
            if field.ttype in ('many2one', 'one2many'):
                name += '/id'
            field_names.append(name)
        # we always want company_id if the field is there
        if ('company_id' in self.song_model and
                'company_id/id' not in field_names):
            field_names.append('company_id/id')
        return field_names

    def get_csv_field_names_exclude(self):
        """Return fields that must be imported in 2 steps.

        For instance, a picking could have `return_picking_type_id`
        equal to another picking that is not imported yet.
        In such cases we want those fields to be imported later.
        We assume that relations to the same model must be imported in 2 steps.
        """
        exclude = []
        for fname, field in self.song_model.fields_get().iteritems():
            if field.get('relation') == self.song_model._name:
                exclude.append(fname + '/id')
        return exclude

    def _get_xmlid_fields(self):
        """Retrieve fields to generate xmlids."""
        xmlid_fields = []
        if self.xmlid_fields:
            xmlid_fields = [
                x.strip() for x in self.xmlid_fields.split(',')
                if x.strip() and x.strip() in self.song_model
            ]
        return xmlid_fields

    def _get_xmlid_fields_map(self):
        """Build a map for xmlid fields by model.

        We might export related items w/ their xmlids.
        These xmlids must respect the rules defined in each song
        for the respective model.
        """
        xmlid_fields_map = {}
        for song in self.compilation_id.song_ids:
            xmlid_fields_map[song.model_name] = song._get_xmlid_fields()
        return xmlid_fields_map

    def make_csv(self, items=None):
        """Create the csv and return path and content."""
        items = items or self.song_model.search(self.eval_domain())
        field_names = self.get_csv_field_names()
        xmlid_fields_map = self._get_xmlid_fields_map()
        export_data = items.with_context(
            dj_export=True,
            dj_xmlid_fields_map=xmlid_fields_map,
        ).export_data(field_names).get('datas', [])
        return (
            self.real_csv_path(),
            self.csv_from_data(field_names, export_data)
        )

    @api.multi
    def download_csv_preview(self):
        """Download a preview of CSV file."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': u'/dj/download/song/{}'.format(slug(self))
        }
