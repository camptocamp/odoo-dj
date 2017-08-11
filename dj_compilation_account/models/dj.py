# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import api, models


class AccountingDJ(models.Model):
    _inherit = 'dj.compilation'

    @api.multi
    def get_currency_rate_live_tvars(self):
        # get active currencies
        cp = self.env['res.company'].search([])[0]
        return {
            'currency_interval_unit': cp.currency_interval_unit,
            'currency_provider': cp.currency_provider,
        }
