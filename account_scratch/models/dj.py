# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
from jinja2 import Environment

from odoo import api, fields, models
from odoo.addons.base_scratch.jinja.disc_loader import DiscLoader



class AccountingDJ(models.Model):
    _inherit = 'dj'

    name = fields.Selection(selection_add=[('account', 'Accounting')])
    active_currencies = fields.Boolean(default=True)

    @api.multi
    def get_beats(self):
        beats = {}
        if self.active_currencies:
            # get active currencies
            cc = self.env['res.currency'].search([])
            beats['currencies'] = cc.mapped('name')
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

