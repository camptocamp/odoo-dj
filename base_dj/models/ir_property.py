# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api
from ..utils import property_to_xmlid, xmlid_to_property


class Property(models.Model):

    _inherit = 'ir.property'

    @api.multi
    def _update_values(self, values):
        """Inverse xmlid value to reference value."""
        if (self.env.context.get('xmlid_value_reference', False) and
                values.get('value_reference')):
            values['value_reference'] = \
                xmlid_to_property(values['value_reference'])
        return super(Property, self)._update_values(values)

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        """Get `value_reference` as xmlid."""
        res = super(Property, self).read(fields=fields, load=load)
        if not self.env.context.get('xmlid_value_reference'):
            return res
        # wipe cache otherwise we gonna get the std value in any case
        self.invalidate_cache(['value_reference'])
        for rec in res:
            if rec.get('value_reference'):
                rec['value_reference'] = property_to_xmlid(
                    self.env, rec['value_reference'])
        return res
