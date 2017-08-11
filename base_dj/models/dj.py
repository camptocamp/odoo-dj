# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import csv
import zipfile
import io
import jinja2
import os
import datetime
import time
from cStringIO import StringIO

from odoo import models, fields, api, exceptions, _
from odoo.tools.safe_eval import safe_eval, test_python_expr
from odoo.modules.module import get_module_resource
from odoo.addons.website.models.website import slugify


SPECIAL_FIELDS = [
    'display_name',
    '__last_update',
    'parent_left',
    'parent_right',
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

ADDONS_BLACKLIST = (
    # useless to track these modules amongst installed addons
    # TODO: anything else to ignore?
    # XXX: shall we exclude modules that are installed via config settings?
    'base',
    'base_action_rule',
    'base_import',
    'board',
    'bus',
    'calendar',
    'grid',
    'maintenance',
    'report',
    'resource',
    'web',
    'web_calendar',
    'web_editor',
    'web_enterprise',
    'web_gantt',
    'web_kanban',
    'web_kanban_gauge',
    'web_mobile',
    'web_planner',
    'web_settings_dashboard',
    'web_tour',
)
ADDONS_NAME_DOMAIN = '("name", "not in", (%s))' % \
    ','.join(["'%s'" % x for x in ADDONS_BLACKLIST])

# TODO: move this to independent records
# then we can filter particular song types by genre
SONG_TYPES = {
    'settings': {
        'name': _('Config settings'),
        'prefix': '',
        'sequence': 0,
        'defaults': {
            'only_config': True,
            'template_path': 'base_dj:discs/song_settings.tmpl',
            'has_records': False,
        },
    },
    'load_csv': {
        'name': _('Load CSV'),
        'prefix': 'load_',
        'sequence': 10,
        'defaults': {
            'only_config': False,
            'template_path': 'base_dj:discs/song.tmpl',
        },
    },
    'load_csv_defer_parent': {
        'name': _('Load CSV defer parent computation'),
        'prefix': 'load_',
        'sequence': 20,
        'defaults': {
            'only_config': False,
            'template_path': 'base_dj:discs/song_defer_parent.tmpl',
        }
    },
    # TODO
    # 'load_csv_heavy': {
    #     'only_config': False,
    #     'template_path': 'base_dj:discs/song_defer_parent.tmpl',
    # },
    # switch automatically to `load_csv_heavy
    # when this amount of records is reached
    # HEAVY_IMPORT_THRESHOLD = 1000
    'generate_xmlids': {
        'name': _('Generate xmlids (for existing records)'),
        'prefix': 'add_xmlid_to_existing_',
        'sequence': 30,
        'defaults': {
            'only_config': True,
            'template_path': 'base_dj:discs/song_add_xmlids.tmpl',
            'has_records': False,
        },
    },
    'scratch_installed_addons': {
        'name': _('List installed addons'),
        'prefix': '',
        'sequence': 40,
        'defaults': {
            'only_config': True,
            'template_path': 'base_dj:discs/song_addons.tmpl',
            'model_id': 'xmlid:base.model_ir_module_module',
            'domain': '[("state", "=", "installed"), %s]' % ADDONS_NAME_DOMAIN,
            'has_records': True,
        },
    },
}

DEFAULT_PYTHON_CODE = """# Available variable:
#  - env: Odoo Environement
# You have to return a recordset by assigning
# variable recs.
# recs = env[model].search([])
"""
# TODO
# switch automatically to `load_csv_heavy
# when this amount of records is reached
# HEAVY_IMPORT_THRESHOLD = 1000


class EqualizerXMLID(models.Model):
    """Hold models' configuration to generate xmlid."""

    _name = 'dj.equalizer.xmlid'

    model = fields.Char()
    xmlid_fields = fields.Char()

    @api.multi
    def get_xmlid_fields(self):
        self.ensure_one()
        return [x.strip() for x in self.xmlid_fields.split(',')
                if x.strip()]


class TemplateMixin(models.AbstractModel):
    """Provide Jinja rendering capabilities."""

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
        if not filepath:
            raise LookupError(
                _('Template not found: `%s`') % self.template_path)
        path, filename = os.path.split(filepath)
        return jinja2.Environment(
            loader=jinja2.FileSystemLoader(path)
        ).get_template(filename)

    def dj_render_template(self, template_vars=None):
        template = self.dj_template()
        template_vars = template_vars or self.dj_template_vars()
        return template.render(**template_vars)


class Genre(models.Model):
    """Pick your favourite music genre."""

    _name = 'dj.genre'

    name = fields.Char(required=True, help='Name will be normalized.')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', _('The name must be unique')),
    ]

    @api.model
    def create(self, vals):
        if vals.get('name'):
            vals['name'] = slugify(vals['name']).replace('-', '_')
        return super(Genre, self).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('name'):
            vals['name'] = slugify(vals['name']).replace('-', '_')
        return super(Genre, self).write(vals)


class DJcompilation(models.Model):
    """Create compilations of songs and burn them."""

    _name = 'dj.compilation'
    _inherit = 'dj.template.mixin'
    _default_dj_template_path = 'base_dj:discs/disc.tmpl'

    name = fields.Char()
    genre_id = fields.Many2one(
        string='Genre',
        comodel_name='dj.genre',
        required=True,
    )
    genre = fields.Char(related='genre_id.name')
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
                u'/dj/download/compilation/{}'.format(item.id)

    @api.multi
    def dj_template_vars(self):
        """Return context variables to render disc's template."""
        self.ensure_one()
        values = super(DJcompilation, self).dj_template_vars()
        values.update({
            # get all songs but scratchable ones
            'songs': self.song_ids.filtered(lambda x: not x.scratchable())
        })
        return values

    def _is_multicompany_env(self):
        return bool(self.env['res.company'].search_count([]) > 1)

    @api.model
    def check_company_codename(self):
        """Check company short codenames have been setup in multi company.

        We need those to create unique codenames
        """
        if not self._is_multicompany_env():
            return
        companies = self.env['res.company'].search([('aka', '=', False)])
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
            track = song.burn_track()
            if track:
                files.append(track)
        # add __init__..py to song module folder
        init_file = os.path.join(
            os.path.dirname(self.disc_full_path()), '__init__.py')
        files.append((init_file, '#'))
        files.append(self.burn_disc())
        files.append(self.burn_dev_readme())
        return files

    def disc_full_path(self):
        return self.disc_path.format(**self.read()[0])

    @api.multi
    def burn_disc(self):
        """Burn the disc with songs."""
        self.ensure_one()
        content = self.dj_render_template()
        # make sure PEP8 is safe
        # no triple empty line, only an empty line at the end
        content = content.replace('\n\n\n\n', '\n\n\n').strip() + '\n'
        return self.disc_full_path(), content

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
        files = self.get_all_tracks()
        in_mem_zip = io.BytesIO()
        with zipfile.ZipFile(in_mem_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for filepath, data in files:
                # File "/usr/lib/python2.7/zipfile.py", line 1247, in writestr
                # TypeError: 'unicode' does not have the buffer interface
                if isinstance(data, unicode):
                    data = data.encode('utf-8')
                # use info to keep date and set permissions
                info = zipfile.ZipInfo(
                    filepath, date_time=time.localtime(time.time()))
                # set proper permissions
                info.external_attr = 0644 << 16L
                zf.writestr(info, data)
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
        self.check_company_codename()
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': self.download_url,
        }

    def anthem_path(self):
        path = self.disc_full_path().replace('/', '.').replace('.py', '')
        return '{}::main'.format(path)


class Song(models.Model):
    _name = 'dj.song'
    _inherit = 'dj.template.mixin'
    _order = 'sequence ASC'
    _default_dj_template_path = 'base_dj:discs/song.tmpl'

    available_song_types = SONG_TYPES

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
    name = fields.Char(compute='_compute_song_name')
    model_id = fields.Many2one(
        string='Model',
        comodel_name='ir.model',
        required=True
    )
    song_type = fields.Selection(
        selection='_select_song_type',
        default='load_csv',
        help='Load pre-configured song type.'
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
    csv_path = fields.Char(default='data/{data_mode}/generated/{model}.csv')
    domain = fields.Char(default="[]")
    python_code = fields.Text(
        default=DEFAULT_PYTHON_CODE,
        help="Get a list of ids with a python expression, if both domain and"
             " python_code are used data will be an union of both.")
    model_context = fields.Char(default="{'tracking_disable':1}")
    xmlid_fields = fields.Char(
        help="List of field to use to generate unique "
             "xmlid separated by ','.",
        default='',
    )
    only_config = fields.Boolean(
        help="This record is only for configuration "
             "and it won't generate CSV data to be imported.",
        default=False
    )
    has_records = fields.Boolean(
        help="Control flag to display records settings (like domain).",
        default=True,
    )
    records_count = fields.Integer(
        compute='_compute_records_count',
        readonly=True
    )

    @api.constrains('python_code')
    def _check_python_code(self):
        for song in self.filtered('python_code'):
            msg = test_python_expr(expr=self.python_code.strip(), mode="exec")
            if msg:
                raise exceptions.ValidationError(msg)

    def _select_song_type(self):
        types = []
        for key, data in self.available_song_types.iteritems():
            # decorated sorting
            types.append((data['sequence'], key, data['name']))
        return [x[1:] for x in sorted(types)]

    @api.onchange('song_type')
    def onchange_song_type(self):
        """Load defaults by song type."""
        if self.song_type:
            defaults = self.available_song_types.get(
                self.song_type, {}).get('defaults', {})
            # self.write does play good w/ NewId records
            for k, v in defaults.iteritems():
                if isinstance(v, basestring):
                    if v.startswith('xmlid:'):
                        v = self.env.ref(v[6:]).id
                self[k] = v
            if 'model_id' not in defaults:
                # reset model
                self.model_id = False

    @api.onchange('records_count')
    def onchange_records_count(self):
        """Switch song type if needed."""
        # TODO: decide if we want this or something similar
        # if self.records_count > HEAVY_IMPORT_THRESHOLD:
        #     self.song_type = 'load_csv_defer_parent'
        # else:
        #     self.song_type = 'load_csv'
        pass

    @api.multi
    def dj_template_vars(self):
        """Return context variables to render template."""
        self.ensure_one()
        return {
            'song': self,
            'header_exclude': self.get_csv_field_names_exclude(),
        }

    @api.multi
    @api.depends('model_id.model', 'song_type')
    def _compute_song_name(self):
        for item in self:
            prefix = self.available_song_types.get(
                item.song_type, {}).get('prefix', 'load_')
            item.name = u'{}{}'.format(
                prefix,
                (item.model_id.model or '').replace('.', '_'),
            )

    @api.multi
    @api.depends('model_id.model', 'domain')
    def _compute_records_count(self):
        for item in self:
            item.records_count = len(item._get_exportable_records())

    @api.model
    def eval_domain(self):
        return safe_eval(self.domain) or []

    @api.model
    def eval_python_code(self):
        """ Get record sets from python code for instance :

        result = env['account.journal'].search([]).sequence_id
        """
        eval_context = {'env': self.env}
        safe_eval(self.python_code.strip(), eval_context,
                  mode="exec", nocopy=True)
        recs = eval_context.get('recs', None)
        if recs is None:
            return
        if not isinstance(recs, models.Model):
            raise exceptions.UserError(
                _("Wrong type.\n"
                  "Python code must return a recordset for %s.")
                % self.model_id.model
            )

        if self.model_id.model != recs._name:
            raise exceptions.UserError(
                _("Wrong recordset model.\n"
                  "Python code must return a recordset for %s got %s instead.")
                % (self.model_id.model, recs._name)
            )
        return recs

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

                # ---- START CHANGE ----
                # Here we remove this feature as csv with negative values
                # are unimportable with an additional quote
                # ----------------------

                # # Spreadsheet apps
                # # tend to detect formulas on leading =, + and -
                # if type(col) is str and col.startswith(('=', '-', '+')):
                #     col = "'" + col
                # ----- END CHANGE -----

                row.append(col)
            writer.writerow(row)

        fp.seek(0)
        data = fp.read()
        fp.close()
        return data

    @property
    def song_model(self):
        # When _register_hook of module queue_job parse models
        # it tries to add this and fail because
        # model is empty. This return nothing instead.
        if not self.model_id:
            return
        return self.env.get(self.model_id.model)

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
        path = data = None
        if not self.only_config and not self.scratchable():
            path, data = self.make_csv()
        if self.scratchable():
            path, data = self.scratch_it()
        if path and data:
            return path, data
        return None

    def scratchable(self):
        """Tell you if the song is scratchable.

        `scratchable` songs are songs that play differently
        and you can scratch them as you like
        to make them produce the result you want.
        """
        return self.song_type.startswith('scratch_')

    def scratch_it(self):
        """Retrieve scratch handler and play it."""
        return getattr(self, self.song_type)()

    @api.multi
    def write(self, vals):
        if vals.get('field_list'):
            model_id = vals.get('model_id') or self.model_id.id
            fields = self._get_fields(model_id, vals.pop('field_list'))
            vals['model_fields_ids'] = [(6, 0, fields.ids)]
        return super(Song ,self).write(vals)

    @api.model
    def create(self, vals):
        if vals.get('field_list') and vals.get('model_id'):
            fields = self._get_fields(vals['model_id'], vals.pop('field_list'))
            vals['model_fields_ids'] = [(6, 0, fields.ids)]
        return super(Song ,self).create(vals)

    def _get_fields(self, model_id, field_list):
        """ helper to set fields from a list """
        model_name = self.env['ir.model'].browse(model_id).name
        field_names = [f.strip() for f in field_list.split(',')]
        return self.env['ir.model.fields'].search([
            ('model_id', '=', model_name),
            ('name', 'in', field_names)
            ])

    def _get_all_fields(self):
        names = set(
            self.song_model.fields_get().keys()
        ).difference(set(SPECIAL_FIELDS))
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
            if field.ttype in ('many2one', 'one2many', 'many2many'):
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

    def _get_exportable_records(self, order=None):
        recs = self.song_model.search(self.eval_domain(), order=order)
        if self.python_code:
            recs2 = self.eval_python_code()
            if recs2:
                recs |= recs2
        return recs

    def _is_multicompany_env(self):
        return self.compilation_id._is_multicompany_env()

    def make_csv(self, items=None):
        """Create the csv and return path and content."""
        items = items or self._get_exportable_records()
        field_names = self.get_csv_field_names()
        xmlid_fields_map = self._get_xmlid_fields_map()
        export_data = items.with_context(
            dj_export=True,
            dj_multicompany=self._is_multicompany_env(),
            dj_xmlid_fields_map=xmlid_fields_map,
        ).export_data(field_names).get('datas', [])
        return (
            self.real_csv_path(),
            self.csv_from_data(field_names, export_data)
        )

    @api.multi
    def download_preview(self):
        """Download a preview file."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': u'/dj/download/song/{}'.format(self.id)
        }

    def anthem_path(self):
        path = self.compilation_id.disc_full_path(
        ).replace('/', '.').replace('.py', '')
        return '{}::{}'.format(path, self.name)

    def dj_get_settings_vals(self):
        """Prepare values for res.config settings song."""
        # TODO: handle multicompany
        values = self.song_model.create({}).read(load='_classic_write')[0]

        res = {}
        fields_info = self.song_model.fields_get()
        for fname, val in values.iteritems():
            if fname in SPECIAL_FIELDS:
                continue
            finfo = fields_info[fname]
            if val and finfo['type'] == 'many2one':
                domain = [('model', '=', finfo['relation']),
                          ('res_id', '=', val)]
                # Find xmlid if it exists
                ext_id = self.env['ir.model.data'].search(domain, limit=1)
                if ext_id:
                    val = self.anthem_xmlid_value(ext_id.complete_name)
            # knowing which field does what is always difficult
            # if you don't check settings schema definition.
            # Let's add some helpful info.
            label = finfo['string']
            if finfo['type'] == 'selection':
                label += u': {}'.format(dict(finfo['selection'])[val])
            res[fname] = {
                'val': val,
                'label': label,
            }
        return res

    def anthem_xmlid_value(self, xmlid):
        # anthem specific
        return "ctx.env.ref('{}').id".format(xmlid)

    def scratch_installed_addons(self):
        path = 'installed_addons.txt'
        return path, self.dj_render_template({
            'song': self,
            'addons': self._get_exportable_records(order='name asc'),
        })
