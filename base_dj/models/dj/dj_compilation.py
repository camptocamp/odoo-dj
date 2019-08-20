# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

try:
    import autopep8
except ImportError:
    import logging
    _logger = logging.getLogger(__name__)
    _logger.warning('`autopep8` dependency lib is missing.')
import os
from urllib.parse import urlencode

from odoo import models, fields, api, exceptions, _
from ...utils import create_zipfile, make_title, to_str
from ...slugifier import slugify


class Compilation(models.Model):
    """Create compilations of songs and burn them."""

    _name = 'dj.compilation'
    _description = 'DJ Compilation'
    _order = 'sequence,core,name'
    _inherit = [
        'dj.template.mixin',
        'dj.download.mixin',
    ]
    _default_dj_template_path = 'base_dj:discs/disc.tmpl'
    _dj_download_path = '/dj/download/compilation/'

    name = fields.Char(required=True, inverse='_inverse_name')
    active = fields.Boolean(default=True)
    sequence = fields.Integer(
        'Sequence',
        help="Sequence for the handle.",
        default=10
    )
    genre_id = fields.Many2one(
        string='Genre',
        comodel_name='dj.genre',
        required=True,
    )
    genre = fields.Char(
        related='genre_id.name',
        readonly=True,
        string='Genre name',
        help='Tech field for accessing genre name straight in templates.'
    )
    data_mode = fields.Selection(
        selection=[
            ('install', 'Install'),
            ('sample', 'Sample'),
        ],
        default='install',
    )
    song_ids = fields.One2many('dj.song', 'compilation_id')
    disc_path = fields.Char(
        default='songs/{data_mode}/generated/{genre}/{name}.py',
        required=True,
    )
    core = fields.Boolean(
        string='Is this a core compilation?',
        help='Core compilations are automatically included '
             'in each compilation burn as we assume '
             'they are the base for every compilation. '
    )
    core_compilation_ids = fields.Many2many(
        string='Core compilations',
        comodel_name='dj.compilation',
        relation='dj_compilation_core_compilations_rel',
        compute='_compute_core_compilation_ids',
        readonly=True,
    )
    exclude_core = fields.Boolean(
        string='Exclude core compilations?',
        help='Core compilations are automatically included '
             'in each compilation burn as we assume '
             'they are the base for every compilation. '
             'You can turn off this behavior by enabling this flag.'
    )
    sanity_check = fields.Html(compute='_compute_info')
    global_info = fields.Html(compute='_compute_info')

    @property
    def xmlid_module_name(self):
        self.ensure_one()
        mapping = {
            'install': '__setup__',
            'sample': '__sample__',
        }
        mode = self.env.context.get('dj_force_data_mode', self.data_mode)
        return mapping.get(mode, '__setup__')

    @api.multi
    def _inverse_name(self):
        if self.env.context.get('skip_normalize_name'):
            return
        for item in self:
            if item.name:
                item.with_context(
                    skip_normalize_name=True
                ).name = slugify(item.name).replace('-', '_')

    def _compute_core_compilation_ids(self):
        core = self._get_core_compilations()
        for item in self:
            item.core_compilation_ids = core

    @api.depends('song_ids', 'core_compilation_ids')
    def _compute_info(self):
        if self.env.context.get('dj_burning_ids'):
            return
        for item in self:
            item.sanity_check = item._render_sanity_check()
            item.global_info = item._render_global_info()

    def _render_sanity_check(self):
        sanity_msg = _('Ok')
        sanity_state = 'ok'
        sanity_conditions = []
        sanity_tmpl = self.env.ref('base_dj.sanity_check')

        # show warning if we have duplicated models
        core_models = []
        core_comps = self.browse()
        if not self.core:
            core_comps = self.core_compilation_ids
            core_models = core_comps.mapped('song_ids').mapped('model_name')
        comp_models = self.mapped('song_ids').mapped('model_name')
        duplicated = set(core_models) & set(comp_models)
        sanity_conditions.append(duplicated)

        # check xmlid settings
        xmlid_not_safe = []
        for song in self.mapped('song_ids').filtered('has_records'):
            if isinstance(song.song_model, models.TransientModel):
                # no xmlid to generate actually
                continue
            # no global or specific xmlid policy
            config = song._dj_global_config()
            if (not config.get('xmlid_fields') and
                    not song._get_xmlid_fields() and
                    'name' not in song.song_model):
                xmlid_not_safe.append(song)
        sanity_conditions.append(bool(xmlid_not_safe))
        if any(sanity_conditions):
            sanity_msg = _('Warning')
            sanity_state = 'warning'
        return sanity_tmpl.render({
            'compilation': self,
            'core_comps': core_comps,
            'sanity_state': sanity_state,
            'sanity_msg': sanity_msg,
            'duplicated': duplicated,
            'xmlid_not_safe': xmlid_not_safe,
        })

    def _render_global_info(self):
        info_tmpl = self.env.ref('base_dj.global_info')

        core_comps = self.browse()
        if not self.core:
            core_comps = self.core_compilation_ids
        return info_tmpl.render({
            'compilation': self,
            'core_comps': core_comps,
        })

    @property
    @api.model
    def dj_burn_options_flags(self):
        return (
            # ctx keys used to control burning
            'dj_exclude_core',
            'dj_xmlid_force',
            'dj_xmlid_skip_create',
            'dj_force_data_mode',
        )

    def make_burn_ctx_via_params(self, **kw):
        return {k: kw[k] for k in self.dj_burn_options_flags if k in kw}

    @api.multi
    def download_it(self):
        """Download file."""
        self.check_company_codename()
        return super(Compilation, self).download_it()

    @api.multi
    def dj_template_vars(self):
        """Return context variables to render disc's template."""
        self.ensure_one()
        values = super(Compilation, self).dj_template_vars()
        songs = self._get_all_songs()
        values.update({
            # get all songs but scratchable ones
            'songs': songs,
            'pre_songs': songs.filtered(lambda x: x.exec_hook == 'pre'),
            'post_songs': songs.filtered(lambda x: x.exec_hook == 'post'),
        })
        return values

    def _is_multicompany_env(self):
        return bool(self.env['res.company'].search_count([]) > 1)

    @api.model
    def check_company_codename(self):
        """Check company short codenames have been setup.

        We need those to create unique xmlids.
        """
        companies = self.env['res.company'].search([('aka', '=', False)])
        if companies:
            raise exceptions.UserError(
                _("Companies miss `aka` unique code: %s") % ', '.join(
                    companies.mapped('name')
                )
            )

    def _get_core_compilations(self):
        return self.search([('core', '=', True)])

    def _get_installed_langs(self):
        return self.env['res.lang'].get_installed()

    def _get_all_songs(self):
        songs = self.env['dj.song'].browse()
        for song in self.mapped('song_ids'):
            songs |= song
            if song.export_translations:
                songs |= self._add_shadow_song_translations(song)
            if song.song_type == 'load_csv_defer_parent':
                songs |= self._add_shadow_song_compute_parent(song)
        return songs

    def _add_shadow_song_translations(self, song):
        songs = self.env['dj.song'].browse()
        # inject shadow song per each lang
        for lang_code, __ in self._get_installed_langs():
            if lang_code == 'en_US':
                # we assume English is always the main lang
                # and we import/export value in English
                continue
            filepath, ext = os.path.splitext(song.csv_path)
            defaults = {
                'export_translations': False,
                'export_lang': lang_code,
                'model_context': "{'lang': '%s'}" % lang_code,
                # set path as foo/bar/my.model.fr_FR.csv
                'csv_path': filepath + '.' + lang_code + ext,
                'sequence': song.sequence + 1,
            }
            translated_data = song.copy_data(default=defaults)[0]
            # add `shadow song` for each lang
            songs |= song.new(translated_data)
        return songs

    def _add_shadow_song_compute_parent(self, song):
        # inject shadow song to compute parents
        song_data = song.copy_data()[0]
        # just clone the song and inject one to render
        # compute parents after that
        # TODO: a bit hacky... When we move song types to separated records
        # we could have shadow song types and use them on the fly.
        song_data['song_type'] = 'compute_parent'
        types = self.env['dj.song'].available_song_types
        song_data.update(types['compute_parent'].get('defaults', {}))
        return song.new(song_data)

    @api.multi
    def _get_tracks(self):
        """Collect files to burn from all compilations."""
        files = []
        songs = self._get_all_songs()
        for comp in self:
            files.append(comp.burn_disc())
        for song in songs:
            track = song.burn_track()
            if track:
                files.extend(track)

        # add __init__.py to song folders
        mid_path = comp.disc_full_path().rsplit('/', 1)[0]
        while mid_path and '/' in mid_path:
            init_file = os.path.join(mid_path, '__init__.py')
            files.append((init_file, '#\n'))
            mid_path = mid_path.rsplit('/', 1)[0]

        # generate dev readme for all compilations
        files.append(self.burn_dev_readme())
        # if not self.env.context.get('dj_burn_skip_self'):
        if False:
            # XXX: TMP skip config export as it's a bit buggy.
            # The goal is to replace this w/ pure json data export.

            # add current config to export
            forced_args = self._export_config_forced_xmlid_params()
            forced_args['dj_burn_skip_self'] = True
            config_comp = self._export_current_config()
            files.append(config_comp.with_context(**forced_args).burn())
        return files

    @api.multi
    def get_all_tracks(self, include_core=True):
        """Return all files to burn into the compilation."""
        compilations = self
        if include_core:
            compilations |= self._get_core_compilations()
        return compilations._get_tracks()

    def disc_full_path(self):
        path = self.disc_path.format(**self.read()[0])
        return to_str(path)

    @api.multi
    def toggle_active(self):
        super(Compilation, self).toggle_active()
        # FIXME: this does not work ATM :/
        # reflect on songs too
        self.song_ids.write({'active': self.active})

    @api.multi
    def burn_disc(self):
        """Burn the disc with songs."""
        self.ensure_one()
        content = self.dj_render_template()
        # make sure PEP8 is safe
        content = autopep8.fix_code(content)
        return self.disc_full_path(), to_str(content)

    @api.multi
    def burn_dev_readme(self):
        """Burn and additional readme for developers."""
        template = self[0].dj_template(path='base_dj:discs/DEV_README.tmpl')
        return 'DEV_README.rst', template.render(compilations=self)

    @api.multi
    def burn(self):
        """Burn disc into a zip file."""
        # at least one of the compilations requires to exclude core ones
        exclude_core = (
            any(self.mapped('exclude_core')) or
            self.env.context.get('dj_exclude_core')
        )
        files = self.with_context(
            # pass around the IDS the we are asked to burn.
            # Used in export self config for instance.
            dj_burning_ids=self.ids
        ).get_all_tracks(include_core=not exclude_core)
        zf = create_zipfile(files)
        filename = self.make_album_title()
        return filename, zf.read()

    def make_album_title(self):
        name = ['mutiple_compilations', ]
        if len(self) == 1:
            name = [self.name, self.data_mode]
        return make_title('_'.join(name))

    def anthem_path(self):
        path = self.disc_full_path().replace('/', '.').replace('.py', '')
        return '{}::main'.format(path)

    def _export_config_get_song_data(self, song):
        """Return export values for given song."""
        data = song.copy_data(default={'active': True})[0]
        if song.model_name == 'dj.genre':
            data['domain'] = "[('id', '=', %d)]" % self.genre_id.id
        elif song.model_name == 'dj.compilation':
            data['domain'] = "[('id', '=', %d)]" % self.id
        elif song.model_name == 'dj.song':
            data['domain'] = "[('id', 'in', %s)]" % str(self.song_ids.ids)
        elif song.model_name == 'dj.song.dependency':
            data['domain'] = "[('id', 'in', %s)]" % str(
                self.song_ids.mapped('depends_on_ids').ids)
        return data

    def _export_config_forced_xmlid_params(self):
        return {
            # force module name to not override existing record
            # in case we are exporting a default configuration.
            'dj_xmlid_module': '__config__',
            'dj_xmlid_force': 1,
            # do not store the xmlid for this record.
            'dj_xmlid_skip_create': 1,
        }

    @api.multi
    def export_current_config(self):
        url_args = self._export_config_forced_xmlid_params()
        new_comp = self._export_current_config()
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': '{}?{}'.format(
                new_comp.download_url,
                urlencode(url_args),
            )
        }

    @api.multi
    def _export_current_config(self):
        """Download zip file w/ current configuration.

        To achieve this we rely on an hidden compilation
        that is alreadty configured for exporting dj models.
        We grab it and use it as a template to generate a new compilation
        that will link all the records in the compilation we want to export.
        """
        comp_tmpl = self.env.ref(
            'base_dj.dj_self_export', raise_if_not_found=False)
        if not comp_tmpl:
            raise exceptions.UserError(_(
                'Default self export compilation is missing.'))

        def filter_core(x):
            return (x.core and x.id
                    not in self.env.context.get('dj_burning_ids', []))

        self = self.filtered(filter_core)
        assert len(self) == 1, \
            _('Something went wrong: we found too many compilations '
              'to export for this config.')

        # use `copy_data` as `copy` keeps xmlids :(
        defaults = {
            'active': True,
            'name': '{} EXPORT {}'.format(
                self.name, fields.Datetime.now())
        }
        new_comp_data = comp_tmpl.copy_data(default=defaults)[0]
        new_songs = []
        for song in comp_tmpl.with_context(active_test=False).song_ids:
            new_songs.append((0, 0, self._export_config_get_song_data(song)))
        new_comp_data['song_ids'] = new_songs
        new_comp_data['active'] = False
        new_comp_data['core'] = False
        return self.create(new_comp_data)
