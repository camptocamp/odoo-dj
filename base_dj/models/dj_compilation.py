# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import os

from odoo import models, fields, api, exceptions, _
from ..utils import create_zipfile, make_title


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
        zf = create_zipfile(files)
        filename = self.make_album_title()
        return filename, zf.read()

    def make_album_title(self):
        return make_title(self.name, self.data_mode)

    def anthem_path(self):
        path = self.disc_full_path().replace('/', '.').replace('.py', '')
        return '{}::main'.format(path)
