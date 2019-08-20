# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models, fields, exceptions, _
from urllib.parse import urlencode
import mimetypes
import base64
import os


class BurnWiz(models.TransientModel):
    _name = 'dj.compilation.burn.wiz'
    _description = 'DJ Burn compilation wizard'

    compilation_id = fields.Many2one(
        string='Compilation to burn',
        comodel_name='dj.compilation',
        required=True,
        readonly=True,
        default=lambda self: self.env.context.get('active_id'),
    )
    song_id = fields.Many2one(
        string='Song to burn',
        comodel_name='dj.song',
        domain="[('compilation_id','=', compilation_id)]",
    )
    dj_force_data_mode = fields.Selection(
        string='Burn mode',
        help='Force data mode only for this burn session. '
             'When this diverges from compilation data mode '
             '`Force XIDs` is activated but '
             'newly generated XIDs will not be stored.',
        required=True,
        selection=[
            ('install', 'Install'),
            ('sample', 'Sample'),
        ],
    )
    core_compilation_ids = fields.Many2many(
        string='Core compilations',
        comodel_name='dj.compilation',
        help='Force included core compilations for this burn session.',
        readonly=True,
    )
    dj_exclude_core = fields.Boolean(
        string='Exclude core compilations',
        help='Force EXCLUDE core compilations for this burn session. '
             'Only current compilation will be burnt.',
    )
    dj_xmlid_force = fields.Boolean(
        string='Force XIDs',
        help='Force XIDs (re)generation. '
             'When this option is on XIDs are re-generated for all records '
             'that are not module specific (like "base.main_company"). '
             'Combined with "Skip creation of new XIDs" you can generate '
             'one-shot XIDs that are not stored in DB. '
             'You could use this to fix some bad XIDs or '
             'replace outdated XIDs due to XID policy updates.'
    )
    dj_xmlid_skip_create = fields.Boolean(
        string='Skip creation of new XIDs',
        help='Do not store newly generated XIDs',
        default=False,
    )
    burn_url = fields.Char(
        string='Share burn URL',
        default='',
        readonly=True,
    )
    download_filename = fields.Char()
    download_file = fields.Binary(
        attachment=True,
        readonly=True,
    )

    @api.onchange('compilation_id')
    def _onchange_compilation_id(self):
        self.update({
            'dj_force_data_mode': self.compilation_id.data_mode,
            'dj_exclude_core': self.compilation_id.exclude_core,
            'core_compilation_ids': self.compilation_id.core_compilation_ids,
        })

    @api.onchange('dj_force_data_mode')
    def _onchange_data_mode(self):
        if self.dj_force_data_mode != self.compilation_id.data_mode:
            self.update({
                'dj_xmlid_force': True,
                'dj_xmlid_skip_create': True,
            })
        else:
            self.update({
                'dj_xmlid_force': False,
                'dj_xmlid_skip_create': False,
            })

    @api.onchange('dj_exclude_core')
    def _onchange_dj_exclude_core(self):
        core_comps = self.compilation_id.core_compilation_ids
        if self.dj_exclude_core:
            core_comps = False
        self.update({
            'core_compilation_ids': core_comps,
        })
        self._update_url()

    @api.onchange('song_id')
    def _onchange_song_id(self):
        self._update_url()

    @api.onchange('dj_xmlid_force', 'dj_xmlid_skip_create')
    def _onchange_force_flags(self):
        self._update_url()

    def _get_config(self):
        config = {}
        for fname in self.compilation_id.dj_burn_options_flags:
            if self[fname]:
                config[fname] = self[fname]
        return config

    def _update_url(self):
        self.burn_url = '/dj/download/compilation/{id}?{config}'.format(
            id=self.compilation_id.id,
            config=urlencode(self._get_config())
        )
        if self.song_id:
            self.burn_url = '/dj/download/song/{id}?{config}'.format(
                id=self.song_id.id,
                config=urlencode(self._get_config())
            )


    @api.multi
    def action_burn(self):
        self.ensure_one()
        if self.song_id:
            fname, content, __ = self._burn_song()
        else:
            fname, content, __ = self._burn_compilation()
        self.update({
            'download_filename': fname,
            'download_file': base64.b64encode(content),
        })
        return {
            "type": "ir.actions.do_nothing",
        }

    def _burn_compilation(self):
        ctx = self.env['dj.compilation'].make_burn_ctx_via_params(
            **self._get_config()
        )
        filename, content = self.compilation_id.with_context(**ctx).burn()
        return filename, content, 'application/zip'

    def _burn_song(self):
        ctx = self.env['dj.compilation'].make_burn_ctx_via_params(
            **self._get_config()
        )
        track = self.song_id.with_context(**ctx).burn_track()
        if not track:
            raise exceptions.UserError(_('Sorry, nothing to burn here.'))
        path, content = track[0]
        filename = os.path.basename(path)
        ctype = mimetypes.guess_type(filename)[0] or 'text/csv'
        return filename, content, ctype
