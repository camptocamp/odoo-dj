# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import api, fields, models


class AccountingDJ(models.Model):
    _inherit = 'dj'

    name = fields.Selection(selection_add=[('account', 'Accounting')])

    @api.multi
    def play(self):
        files = super(AccountingDJ, self).play()

        if self.name == 'account':
            # load Jinja template and add the result in songs/install/accounting.py
            pass

        return files

