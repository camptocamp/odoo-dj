# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import models, fields, api
from urllib.parse import urlencode


class DownloadMixin(models.AbstractModel):
    """Make models downloadable."""

    _name = 'dj.download.mixin'
    _description = 'DJ download mixin'
    _dj_download_path = '/dj/download/'

    download_url = fields.Char(compute='_compute_download_url')

    @api.multi
    @api.depends()
    def _compute_download_url(self):
        # propagate our ctx keys
        ctx = {k: v for k, v in self.env.context.items() if k.startswith('dj')}
        for item in self:
            url = self._dj_download_path + str(item.id)
            if ctx:
                url += '?' + urlencode(ctx)
            item.download_url = url

    @api.multi
    def download_it(self):
        """Download file."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': self.download_url,
        }
