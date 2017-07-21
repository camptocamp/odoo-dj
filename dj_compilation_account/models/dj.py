# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import json

from odoo import api, fields, models


class AccountingDJ(models.Model):
    _inherit = 'dj'

    genre = fields.Selection(selection_add=[('accounting', 'Accounting')])
    active_currencies = fields.Boolean(default=True)

    @api.multi
    def get_active_currencies(self):
        if not self.active_currencies:
            return False
        # get active currencies
        cc = self.env['res.currency'].search([])
        return cc.mapped('name')

    @api.multi
    def get_currency_rate_live_tvars(self):
        # get active currencies
        cp = self.env['res.company'].search([])[0]
        return {
            'currency_interval_unit': cp.currency_interval_unit,
            'currency_provider': cp.currency_provider,
        }

    @api.multi
    def get_sequence_config(self):
        Journal = self.env['account.journal']
        ModelData = self.env['ir.model.data']
        res = {}
        for cp in self.env['res.company'].search([]):
            xmlid = ModelData.search([
                ('model', '=', 'res.company'),
                ('res_id', '=', cp.id)]).complete_name
            journals = Journal.search([
                ('code', '=', ('INV', 'BILL')),
                ('company_id', '=', cp.id)]
            )

            res[xmlid] = {j.code: [
                j.sequence_id.prefix, j.sequence_id.padding,
                j.refund_sequence_id.prefix, j.refund_sequence_id.padding]
                for j in journals}
        return json.dumps(res, sort_keys=True, indent=4)

    @api.multi
    def get_template_vars(self):
        tvars = super(AccountingDJ, self).get_template_vars()
        tvars['currencies'] = self.get_active_currencies()
        tvars.update(self.get_currency_rate_live_tvars())
        tvars['sequence_config'] = self.get_sequence_config()
        return tvars
