# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import models, api


class IrModel(models.Model):

    _inherit = 'ir.model'

    @api.multi
    def name_get(self):
        """Show only model dotted name on demand."""
        if self.env.context.get('model_dotted_name_only'):
            return [
                (x.id, x.model) for x in self
            ]
        return super(IrModel, self).name_get()
