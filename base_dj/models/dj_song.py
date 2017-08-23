# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import models, fields, api, exceptions, _
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval, test_python_expr
from ..utils import csv_from_data
from ..config import (
    SPECIAL_FIELDS,
    SONG_TYPES,
    DEFAULT_PYTHON_CODE,
)


class Song(models.Model):
    _name = 'dj.song'
    _inherit = [
        'dj.template.mixin',
        'onchange.player.mixin',
    ]
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
    depends_on_ids = fields.One2many(
        string='Depends on',
        comodel_name='dj.song.dependency',
        inverse_name='song_id',
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

    @api.onchange('depends_on_ids')
    def onchange_depends_on_ids(self):
        """Collect record IDS from master songs and update domain."""
        ids = set([])
        for dep in self.depends_on_ids:
            ids.update(dep._get_dependant_record_ids())
        if not ids:
            return
        # NOTE: we can end up w/ duplicated domain leafs
        # as there's no easy way (or odoo util AFAIK)
        # to merge existing domains.
        # Eg: ['&', ('id', 'in', [125]), ('id', 'in', [125])]
        # So, here we just put existing ones in AND
        # as is not going to hurt in most of the use cases.
        # Still, you can then edit the final domain
        # via the domain widget.
        domain = expression.AND([
            self.eval_domain(), [('id', 'in', list(ids))]
        ])
        self.domain = str(domain)

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
    @api.depends('model_id.model', 'domain', 'python_code')
    def _compute_records_count(self):
        for item in self:
            item.records_count = len(item._get_exportable_records())

    @api.model
    def eval_domain(self):
        return safe_eval(self.domain) if self.domain else []

    @api.model
    def eval_python_code(self):
        """Get record sets from python code for instance.

        Example:

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

    @property
    def song_model(self):
        # When _register_hook of module queue_job parse models
        # it tries to add this and fail because
        # model is empty. This return nothing instead.
        if not self.model_id:
            return None
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

    def _get_dependant_songs(self):
        self.ensure_one()
        return self.env['dj.song.dependency'].search([
            ('master_song_id', '=', self.id)
        ]).mapped('song_id')

    @api.multi
    def write(self, vals):
        if vals.get('field_list'):
            model_id = vals.get('model_id') or self.model_id.id
            fields = self._get_fields(model_id, vals.pop('field_list'))
            vals['model_fields_ids'] = [(6, 0, fields.ids)]
        for item in self:
            # update dependant songs
            for dep in self._get_dependant_songs():
                dep.onchange_depends_on_ids()
        return super(Song, self).write(vals)

    @api.model
    def create(self, vals):
        if vals.get('field_list') and vals.get('model_id'):
            fields = self._get_fields(vals['model_id'], vals.pop('field_list'))
            vals['model_fields_ids'] = [(6, 0, fields.ids)]
        item = super(Song, self).create(vals)
        if self.env.context.get('install_mode'):
            # if we are installing/updating the module
            # let's play all onchanges to make sure
            # defaults, filters, etc are set properly on each song
            item.play_onchanges()
        return item

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
        if self.song_model is None:
            return []
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
            xmlid_value_reference=True,
        ).export_data(field_names).get('datas', [])
        return (
            self.real_csv_path(),
            csv_from_data(field_names, export_data)
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
                record = self.env[finfo['relation']].browse(val)
                ext_id = record._dj_export_xmlid()
                val = self.anthem_xmlid_value(ext_id.complete_name)
            # knowing which field does what is always difficult
            # if you don't check settings schema definition.
            # Let's add some helpful info.
            label = finfo['string']
            if finfo['type'] == 'selection':
                label += u': {}'.format(dict(finfo['selection'])[val])
                val = u"'{}'".format(val)
            elif finfo['type'] == 'text':
                val = u'"""{}"""'.format(val)
            elif finfo['type'] in ('date', 'datetime'):
                val = u"'{}'".format(val)
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

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = [('model_id.model', 'ilike', u'%{}%'.format(name))]
        items = self.search(domain + args, limit=limit)
        return items.name_get()


class SongDependency(models.Model):
    _name = 'dj.song.dependency'
    _rec_name = 'song_id'

    song_id = fields.Many2one(
        comodel_name='dj.song',
        string='Song',
    )
    master_song_id = fields.Many2one(
        comodel_name='dj.song',
        string='Master song',
        required=True,
    )
    master_song_model = fields.Char(
        related='master_song_id.model_name',
        readonly=True
    )
    model_field_id = fields.Many2one(
        comodel_name='ir.model.fields',
        string='Relation field',
        required=True,
    )

    @api.onchange('master_song_id')
    def onchange_master_song_id(self):
        if self.master_song_id:
            return {'domain': {
                'model_field_id': [
                    ('store', '=', True),
                    ('compute', '=', False),
                    ('model_id', '=', self.master_song_id.model_id.id),
                    ('relation', '=', self.env.context['relation_model']),
                ]
            }}

    def _get_dependant_record_ids(self):
        master_records = self.master_song_id._get_exportable_records()
        records = master_records.mapped(self.model_field_id.name)
        return records.ids
