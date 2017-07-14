# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
from jinja2 import Environment
import json

from odoo import api, fields, models
from odoo.addons.base_scratch.jinja.disc_loader import DiscLoader


class AccountingDJSample(models.Model):
    """ Specific filter for ir.sequences """
    _inherit = 'dj.sample'

class AccountingDJ(models.Model):
    _inherit = 'dj'

    name = fields.Selection(selection_add=[('account', 'Accounting')])
    active_currencies = fields.Boolean(default=True)

    @api.multi
    def get_active_currencies(self):
        if not self.active_currencies:
            return False
        # get active currencies
        cc = self.env['res.currency'].search([])
        return cc.mapped('name')

    @api.multi
    def get_currency_rate_live_beats(self):
        # get active currencies
        cp = self.env['res.company'].search([])[0]
        return {
            'currency_interval_unit': cp.currency_interval_unit,
            'currency_provider': cp.currency_provider,
        }

    @api.multi
    def get_sequence_config(self):
        Journal= self.env['account.journal']
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
    def get_beats(self):
        beats = super(AccountingDJ, self).get_beats()
        beats['currencies'] = self.get_active_currencies()
        beats.update(self.get_currency_rate_live_beats())
        beats['sequence_config'] = self.get_sequence_config()
        return beats 

    @api.multi
    def play_accounting_disc(self):
        disc = 'accounting.disc'
        # load Jinja template
        jnj_env = Environment(loader=DiscLoader('account_scratch'))
        jnj_template = jnj_env.get_template(disc)
        kwargs = self.get_beats()
        return jnj_template.render(**kwargs)

    @api.multi
    def get_all_tracks(self):
        files = super(AccountingDJ, self).get_all_tracks()

        if self.name == 'account':

            disc_content = self.play_accounting_disc()

            files.append((
                'songs/install/accounting.py',
                disc_content
            ))

        return files

