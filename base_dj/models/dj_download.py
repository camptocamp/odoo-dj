# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import models, fields, api


class DownloadMixin(models.AbstractModel):
    """Make models downloadable."""

    _name = 'dj.download.mixin'
    _dj_download_path = '/dj/download/'

    download_url = fields.Char(compute='_compute_download_url')

    @api.multi
    @api.depends()
    def _compute_download_url(self):
        for item in self:
            item.download_url = self._dj_download_path + str(item.id)

    @api.multi
    def download_it(self):
        """Download file."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': self.download_url,
        }
