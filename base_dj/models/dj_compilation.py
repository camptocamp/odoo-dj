# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import os

from odoo import models, fields, api, exceptions, _
from ..utils import create_zipfile, make_title


class Compilation(models.Model):
    """Create compilations of songs and burn them."""

    _name = 'dj.compilation'
    _order = 'core,name'
    _inherit = [
        'dj.template.mixin',
        'dj.download.mixin',
    ]
    _default_dj_template_path = 'base_dj:discs/disc.tmpl'
    _dj_download_path = '/dj/download/compilation/'

    name = fields.Char()
    genre_id = fields.Many2one(
        string='Genre',
        comodel_name='dj.genre',
        required=True,
    )
    genre = fields.Char(related='genre_id.name', readonly=True)
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
    core = fields.Boolean(
        string='Core compilation?',
        help='Core compilations are automatically included '
             'in each compilation burn as we assume '
             'they are the base for every compilation.'
    )
    core_compilation_ids = fields.Many2many(
        string='Core compilations',
        comodel_name='dj.compilation',
        relation='dj_compilation_core_compilations_rel',
        compute='_compute_core_compilation_ids',
        readonly=True,
    )

    @api.depends()
    def _compute_core_compilation_ids(self):
        core = self._get_core_compilations()
        for item in self:
            item.core_compilation_ids = core

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

    def _get_core_compilations(self):
        return self.search([('core', '=', True)])

    @api.multi
    def _get_tracks(self):
        """Collect files to burn from all compilations."""
        files = []
        for comp in self:
            files.append(comp.burn_disc())
            for song in comp.song_ids:
                track = song.burn_track()
                if track:
                    files.append(track)
        # add __init__..py to song module folder only once
        init_file = os.path.join(
            os.path.dirname(comp.disc_full_path()), '__init__.py')
        files.append((init_file, '#'))
        # generate dev readme for all compilations
        files.append(self.burn_dev_readme())
        return files

    @api.multi
    def get_all_tracks(self, include_core=True):
        """Return all files to burn into the compilation."""
        compilations = self
        if include_core:
            compilations |= self._get_core_compilations()
        return compilations._get_tracks()

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
        template = self[0].dj_template(path='base_dj:discs/DEV_README.tmpl')
        return 'DEV_README.rst', template.render(compilations=self)

    @api.multi
    def burn(self):
        """Burn disc into a zip file."""
        files = self.get_all_tracks()
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
