# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api
from ..utils import property_to_xmlid, xmlid_to_property


class IRValues(models.Model):

    _inherit = 'ir.values'

    def _update_values(self, vals):
        if (self.env.context.get('xmlid_value_reference', False) and
                vals.get('value') and vals.get('key') == 'action'):
            vals['value'] = xmlid_to_property(vals['value'])

    @api.model
    def create(self, vals):
        self._update_values(vals)
        return super(IRValues, self).create(vals)

    @api.multi
    def write(self, vals):
        self._update_values(vals)
        return super(IRValues, self).write(vals)

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        """Get `value_reference` as xmlid."""
        res = super(IRValues, self).read(fields=fields, load=load)
        if not self.env.context.get('xmlid_value_reference'):
            return res
        # wipe cache otherwise we gonna get the std value in any case
        self.invalidate_cache(['value'])
        for rec in res:
            if rec.get('value') and rec.get('key') == 'action':
                rec['value'] = property_to_xmlid(self.env, rec['value'])
        return res
