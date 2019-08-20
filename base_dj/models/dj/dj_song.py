# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import models, fields, api, exceptions, tools, _
from odoo.tools.safe_eval import safe_eval, test_python_expr
from odoo.modules import get_module_path
from ...utils import (
    csv_from_data,
    force_company,
    context_to_string,
    to_str,
    string_to_list,
)
from ...config import (
    SPECIAL_FIELDS,
    SONG_TYPES,
    DEFAULT_PYTHON_CODE,
)
from collections import defaultdict, Counter
import os

testing = tools.config.get('test_enable') or os.environ.get('ODOO_TEST_ENABLE')


class Song(models.Model):
    _name = 'dj.song'
    _description = 'DJ Song'
    _inherit = [
        'dj.template.mixin',
        'onchange.player.mixin',
        'dj.download.mixin',
    ]
    _order = 'sequence ASC'
    _default_dj_template_path = 'base_dj:discs/song.tmpl'
    _dj_download_path = '/dj/download/song/'

    available_song_types = SONG_TYPES

    active = fields.Boolean(default=True)
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
            ('ttype', '!=', 'one2many'),
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
            ('ttype', '!=', 'one2many'),
        ]""",
    )
    csv_path = fields.Char(
        default='{data_mode}/generated/{genre}/{comp_name}/{model}.csv'
    )
    binaries_path = fields.Char(
        default='{data_mode}/generated/{genre}/{comp_name}/binaries/{model}'
    )
    domain = fields.Char(default="[]")
    python_code = fields.Text(
        default=DEFAULT_PYTHON_CODE,
        help="Get a list of ids with a python expression, if both domain and"
             " python_code are used data will be an union of both.")
    model_context = fields.Char(default="{'tracking_disable': True}")
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
    records_order = fields.Char(default='id asc')
    depends_on_ids = fields.One2many(
        string='Depends on',
        comodel_name='dj.song.dependency',
        inverse_name='song_id',
    )
    involved_modules = fields.Html(compute='_compute_involved_modules')
    position_in_collection = fields.Integer(
        compute='_compute_position_in_collection',
        readonly=True
    )
    export_translations = fields.Boolean(default=False)
    export_lang = fields.Char()
    exec_hook = fields.Selection(
        selection=[('pre', 'pre'), ('post', 'post')],
        default='post',
        help="When to execute this? Pre or post module upgrade?"
    )

    @api.depends('model_id', 'sequence', 'compilation_id.song_ids')
    def _compute_position_in_collection(self):
        for item in self:
            item.position_in_collection = [
                i + 1 for i, x in enumerate(item.compilation_id.song_ids)
                if x.id == item.id
            ][0]

    @api.constrains('python_code')
    def _check_python_code(self):
        for song in self.filtered('python_code'):
            msg = test_python_expr(expr=self.python_code.strip(), mode="exec")
            if msg:
                raise exceptions.ValidationError(msg)

    def _select_song_type(self):
        types = []
        for key, data in self.available_song_types.items():
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
            for k, v in defaults.items():
                if isinstance(v, str) and v.startswith('xmlid:'):
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
        # So, here we just ignore existing domain
        # assuming that if you want to play w/ the domain
        # you gonna do it *after* playing w/ song dependencies.
        self.domain = str([('id', 'in', list(ids))])

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
        res = {
            'song': self,
            'header_exclude': self.get_csv_field_names_exclude(),
        }
        return res

    @property
    def _song_model_count_key(self):
        return (self.model_name, self.song_type)

    @property
    def _songs_models_count(self):
        # count songs in the same compilation w/ the same model and same type
        return Counter(
            self.compilation_id.song_ids.mapped(
                lambda x: x._song_model_count_key)
        )

    @api.multi
    @api.depends('model_id.model', 'song_type')
    def _compute_song_name(self):
        for item in self:
            prefix = self.available_song_types.get(
                item.song_type, {}).get('prefix', 'load_')
            suffix = self.available_song_types.get(
                item.song_type, {}).get('suffix', '')
            name = '{}{}{}'.format(
                prefix,
                (item.model_id.model or '').replace('.', '_'),
                suffix,
            )
            if item._songs_models_count[item._song_model_count_key] > 1:
                # make name unique in the compilation
                name += '_%d' % item.position_in_collection
            if item.export_lang:
                name += '_' + item.export_lang
            item.name = name

    @api.multi
    @api.depends('model_id.model', 'domain', 'python_code')
    def _compute_records_count(self):
        for item in self:
            item.records_count = len(item._get_exportable_records())

    def _involved_modules(self):
        mods = defaultdict(list)
        for field in self._get_data_fields():
            mods[field.modules].append(field.name)
        return mods

    def _involved_modules_txt(self):
        val = self.involved_modules
        to_strip = ('<b>', '</b>', '<span>', '</span>', )
        for k in to_strip:
            val = val.replace(k, '')
        to_repl = ('<br />', '\n'), ('<br>', '\n')
        for k, v in to_repl:
            val = val.replace(k, v)
        return val

    @api.multi
    @api.depends('model_id', 'model_fields_ids', 'model_fields_blacklist_ids')
    def _compute_involved_modules(self):
        for item in self:
            txt = []
            for mod, _fields in item._involved_modules().items():
                txt.append('<b>%s:</b> %s' % (mod, ', '.join(_fields)))
            item.involved_modules = '<br />'.join(sorted(txt))

    @api.model
    def eval_domain(self):
        domain = safe_eval(self.domain) if self.domain else []
        ids_blacklist = self._dj_global_config('record_blacklist') or []
        if ids_blacklist:
            domain.append(('id', 'not in', ids_blacklist))
        return domain

    @api.model
    def eval_python_code(self):
        """Get record sets from python code for instance.

        Example:

            records = env['account.journal'].search([]).sequence_id
        """
        eval_context = {'env': self.env}
        safe_eval(self.python_code.strip(), eval_context,
                  mode="exec", nocopy=True)
        recs = eval_context.get('records', None)
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

    def song_model_context(self, as_string=False):
        """Updated context to run songs with."""
        ctx = self.song_model._dj_global_config('model_context')
        song_ctx = safe_eval(self.model_context) if self.model_context else {}
        ctx.update(song_ctx)
        if as_string:
            return context_to_string(ctx)
        return ctx

    def _real_path_data(self):
        return {
            'model': self.song_model._name,
            'data_mode': self.compilation_id.data_mode,
            'genre': self.compilation_id.genre_id.name,
            'comp_name': self.compilation_id.name,
        }

    def _real_path(self, pattern):
        path = pattern.format(**self._real_path_data())
        if self._songs_models_count[self._song_model_count_key] > 1:
            # make filename unique. Include position to match song name
            path, ext = os.path.splitext(path)
            path += '_%d' % self.position_in_collection
            path += ext
        return path

    def real_csv_path(self):
        """Final csv path into zip file."""
        return self._real_path(self.csv_path)

    def real_binaries_path(self):
        """Final path for binary files."""
        return self._real_path(self.binaries_path)

    @api.multi
    def burn_track(self):
        """Search items and burn the track for the compilations."""
        self.ensure_one()
        # pass around corect xmlid module name based on compilation
        song_self = self.with_context(
            dj_xmlid_module=self.compilation_id.xmlid_module_name)
        path = data = None
        if not self.only_config and not self.scratchable():
            path, data = song_self.make_csv()
        if self.scratchable():
            path, data = song_self.scratch_it()
        if path and data:
            res = [(path, data), ]
            if not self.scratchable():
                res.extend(song_self._handle_special_fields())
            return res
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

    def _handle_fields_shortcuts(self, vals):
        """We support some shortcuts to not deal w/ fields relations.

        Available:
            * `fields_list` -> converted to `model_fields_ids`
            * `field_blacklist` -> converted to `model_fields_blacklist_ids`
        """
        shortcuts = (
            ('field_list', 'model_fields_ids'),
            ('field_blacklist', 'model_fields_blacklist_ids'),
        )
        for shortcut, fname in shortcuts:
            if vals.get(shortcut):
                model_id = vals.get('model_id') or self.model_id.id
                ids = vals.get(fname, [])
                if ids and len(ids[0]) > 1 and ids[0][0] == 6:
                    # ids == [(6, 0, [940])] -> preserve values
                    ids = ids[0][-1]
                fields = self._get_fields(model_id, vals.pop(shortcut))
                ids.extend(fields.ids)
                vals[fname] = [(6, 0, ids)]

    @api.multi
    def write(self, vals):
        self._handle_fields_shortcuts(vals)
        for item in self:
            # update dependant songs
            for dep in item._get_dependant_songs():
                dep.onchange_depends_on_ids()
        return super(Song, self).write(vals)

    @api.model
    def create(self, vals):
        self._handle_fields_shortcuts(vals)
        item = super(Song, self).create(vals)
        if self.env.context.get('install_mode') or testing:
            # if we are installing/updating the module
            # let's play all onchanges to make sure
            # defaults, filters, etc are set properly on each song
            item.play_onchanges()
        return item

    def _get_fields(self, model_id, field_list):
        """Helper to retrieve fields records from a name list."""
        model_name = self.env['ir.model'].browse(model_id).name
        return self.env['ir.model.fields'].search([
            ('model_id', '=', model_name),
            ('name', 'in', string_to_list(field_list))
        ])

    def _get_all_fields(self):
        if self.song_model is None:
            return []
        names = set(
            self.song_model.fields_get().keys()
        ).difference(set(SPECIAL_FIELDS))
        # TODO: what about related fields that are not readonly?
        # eg: company.logo -> partner_id.image
        domain = [
            ('model', '=', self.model_name),
            ('store', '=', True),
            ('compute', '=', False),
            ('name', 'in', list(names)),
            # o2m relations are resolved by importing related records
            # and their specific inverse name.
            # We assume that you have to export/import sub records in any case,
            # as we must make sure that those records are already there
            # when we import them.
            ('ttype', '!=', 'one2many'),
        ]
        if self.export_lang:
            # load only translatable fields
            domain.append(('translate', '=', True))
        return self.env['ir.model.fields'].search(domain)

    def _get_data_fields(self):
        _fields = self.model_fields_ids
        if not _fields:
            _fields = self._get_all_fields()
        return _fields

    def _csv_field_names_cache_keys(self):
        return (
            self.id,
            self.model_name,
            self.model_fields_ids.ids,
            self.model_fields_blacklist_ids.ids,
            self._dj_global_config('field_blacklist')
        )

    @tools.ormcache('self._csv_field_names_cache_keys()')
    def get_csv_field_names(self):
        """Retrieve CSV field names."""
        field_names = ['id']
        _fields = self._get_data_fields()

        blacklisted = self.model_fields_blacklist_ids.mapped('name')
        blacklisted.extend(self._dj_global_config('field_blacklist'))
        if 'parent_path' in self.song_model:
            blacklisted.append('parent_path')
        for field in _fields:
            if field.name in blacklisted:
                continue
            name = field.name
            # we always want xmlids (one2many are already excluded)
            if field.ttype in ('many2one', 'many2many'):
                name += '/id'
            field_names.append(name)
        # we always want company_id if the field is there
        if ('company_id' in self.song_model and
                'company_id/id' not in field_names):
            field_names.append('company_id/id')
        # make fields unique and keep always the same ordering
        field_names = sorted((set(field_names)))
        # make sure `id` is always 1st
        field_names.remove('id')
        field_names.insert(0, 'id')
        if 'name' in field_names:
            # make sure is always after `id` to ease csv review
            field_names.remove('name')
            field_names.insert(1, 'name')
        return [to_str(x) for x in field_names]

    def get_csv_field_names_exclude(self):
        """Return fields that must be imported in 2 steps.

        For instance, a picking could have `return_picking_type_id`
        equal to another picking that is not imported yet.
        In such cases we want those fields to be imported later.
        We assume that relations to the same model must be imported in 2 steps.
        """
        exclude = []
        # consider only fields that we really use
        _all_fields = [
            x.replace('/id', '') for x in self.get_csv_field_names()]
        info = self.song_model.fields_get(_all_fields)
        for fname in _all_fields:
            field = info[fname]
            if field.get('relation') == self.song_model._name:
                exclude.append(fname + '/id')
        return [x for x in exclude if x in self.get_csv_field_names()]

    @tools.ormcache_context('self', 'key', keys=('dj_xmlid_force'))
    def _dj_global_config(self, key=None):
        """Retrieve default global config for song model."""
        model = self.model_name
        if self.env.context.get('dj_xmlid_force'):
            # we are exporting the dj.song itself
            model = self._name
        config = self.env['dj.equalizer'].search([
            ('model', '=', model),
        ], limit=1)
        return config.get_conf(key)

    def _get_xmlid_fields(self, include_global=False):
        """Retrieve fields to generate xmlids."""
        xmlid_fields = []
        if self.xmlid_fields:
            xmlid_fields = string_to_list(
                self.xmlid_fields,
                checker=lambda x: (
                    True if x.strip() and
                    x.strip() in self.song_model else False
                ))
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
        order = order or self.records_order
        recs = self.song_model.search(self.eval_domain(), order=order)
        if self.python_code:
            recs2 = self.eval_python_code()
            if recs2:
                recs |= recs2
        return recs

    def _is_multicompany_env(self):
        return self.compilation_id._is_multicompany_env()

    def _dj_export_context(self):
        ctx = dict(
            dj_export=True,
            dj_multicompany=self._is_multicompany_env(),
            dj_xmlid_fields_map=self._get_xmlid_fields_map(),
            dj_export_binaries_path=self.real_binaries_path(),
            dj_export_model=self.model_name,
            dj_export_model_fields=self.get_csv_field_names(),
            xmlid_value_reference=True,
        )
        if self.export_lang:
            ctx['lang'] = self.export_lang
            ctx['dj_export_lang'] = self.export_lang
        return ctx

    def _handle_special_fields(self, items=None):
        """Handle special fields and return extra tracks for them.

        Special fields (binary, html, text) are exported to their own files.
        Here we go through each special field and retrieve the final path.

        :return list tuples: pairs for zip tracks (path, filecontent)
        """
        extra_tracks = []
        if self.env.context.get('dj_read_skip_special_fields'):
            return extra_tracks
        items = items or self._get_exportable_records()
        if self.song_model is None:
            return
        song_model = self.song_model.with_context(
            **self._dj_export_context()
        )
        special = song_model._dj_special_fields()
        for fname, info in special:
            for rec in items:
                if self.export_lang:
                    rec = rec.with_context(lang=self.export_lang)
                content = rec[fname]
                if not content:
                    continue
                path = song_model._dj_file_to_path(rec, fname, bare_path=True)
                fs_content = self.song_model._dj_file_content_to_fs(
                    fname, rec, info=info)
                extra_tracks.append((path, fs_content))
        return extra_tracks

    def make_csv(self, items=None):
        """Create the csv and return path and content."""
        items = items or self._get_exportable_records()
        field_names = self.get_csv_field_names()
        export_data = items.with_context(
            **self._dj_export_context()
        ).export_data(field_names).get('datas', [])
        csv_data = csv_from_data(field_names, export_data)
        # get bytes, convert to string, cleanup, convert back to bytes
        csv_data = str(
            csv_data, 'utf-8'
        ).replace('\r\n', '\n').replace('^M', '\n')
        return (self.real_csv_path(), csv_data.encode())

    def anthem_path(self):
        path = self.compilation_id.disc_full_path(
        ).replace('/', '.').replace('.py', '')
        return '{}::{}'.format(path, self.name)

    settings_char_fields = ('char', 'date', 'datetime')
    settings_text_fields = ('text', )

    def dj_get_settings_vals(self):
        """Prepare of values for res.config settings song.

        Returns [(song_name, company_aka, settings_values), ...]
        """
        global_settings = 'company_id' not in self.song_model
        kwargs = {'limit': 1} if global_settings else {}

        # with a simple context key you can enforce the companies to export
        specific_companies = self.env.context.get('dj_settings_company_xmlids')
        if specific_companies:
            companies = string_to_list(
                specific_companies, modifier=lambda x: self.env.ref(x))
        else:
            companies = self.env['res.company'].search([], **kwargs)

        res = []
        model = self.song_model.with_context(dj_export=True)
        for company in companies:
            with force_company(self.env, company.id):
                fnames = model._dj_settings_fields_get()
                wizard = model.create({})
                values = wizard.read(
                    fields=fnames, load='_classic_write')[0]
            cp_values = {}
            fields_info = model.fields_get(fnames)
            for fname, val in values.items():
                if fname in SPECIAL_FIELDS:
                    continue
                finfo = fields_info[fname]
                val = to_str(val, safe=True)
                label, val = self._dj_settings_val(finfo, fname, val)
                cp_values[fname] = {
                    'val': val,
                    'label': label,
                }
            song_name = '{}_{}'.format(self.name, company.aka)
            res.append((song_name, company.aka, cp_values))
        return res

    def _dj_settings_val(self, finfo, fname, val):
        """Format value to be exported."""
        # knowing which field does what is always difficult
        # if you don't check settings schema definition.
        # Let's add some helpful info.
        label = finfo['string']
        if val:
            if finfo['type'] == 'selection':
                label += ': {}'.format(dict(finfo['selection'])[val])
                # selection field can have many values not only chars
                # let's wrap it only if it's a string
                if isinstance(val, str):
                    val = "'{}'".format(val)
            elif finfo['type'] == 'many2one':
                record = self.env[finfo['relation']].browse(val)
                ext_id = record._dj_export_xmlid()
                val = self.anthem_xmlid_value(ext_id)
            elif finfo['type'] in self.settings_char_fields:
                val = "'{}'".format(val)
            elif finfo['type'] in self.settings_text_fields:
                val = '"""{}"""'.format(val)
        return label, val

    def anthem_xmlid_value(self, xmlid):
        # anthem specific
        return "ctx.env.ref('{}').id".format(xmlid)

    def scratch_installed_addons(self):
        path = 'installed_addons.txt'
        addons = self._get_exportable_records(order='name asc')
        grouped = defaultdict(list)
        core_addons = []
        for mod in addons:
            mod_path = get_module_path(mod.name)
            if not mod_path:
                # be defensive w/ removed but not uninstalled modules
                continue
            repo_name = os.path.split(os.path.dirname(mod_path))[-1]
            if repo_name == 'addons':
                # yeah, not 100% sure but for us work like that ;)
                core_addons.append(mod)
                continue
            grouped[repo_name].append(mod)
        return path, self.dj_render_template({
            'song': self,
            'addons': addons,
            'core_addons': core_addons,
            'grouped_by_repo': grouped,
        })

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = [('model_id.model', 'ilike', '%{}%'.format(name))]
        items = self.search(domain + args, limit=limit)
        return items.name_get()


class SongDependency(models.Model):
    _name = 'dj.song.dependency'
    _description = 'DJ Song dependency'
    _rec_name = 'song_id'

    song_id = fields.Many2one(
        comodel_name='dj.song',
        string='Song',
        ondelete='cascade',
    )
    master_song_id = fields.Many2one(
        comodel_name='dj.song',
        string='Master song',
        ondelete='cascade',
    )
    master_song_model = fields.Char(
        related='master_song_id.model_name',
        readonly=True
    )
    model_field_id = fields.Many2one(
        comodel_name='ir.model.fields',
        string='Relation field',
    )
    model_field = fields.Char(
        string='Advanced field (eg: product_id.seller_ids.name)',
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
        if self.model_field_id:
            fname = self.model_field_id.name
        elif self.model_field:
            fname = self.model_field
        else:
            raise exceptions.UserError(_(
                'Provide either a field name (dotted path supported) '
                'or a link to relation field.'
            ))
        records = master_records.mapped(fname)
        return records.ids
