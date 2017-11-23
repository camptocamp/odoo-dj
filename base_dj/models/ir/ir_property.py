# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api
from ...utils import property_to_xmlid, xmlid_to_property


class Property(models.Model):

    _inherit = 'ir.property'
    # these fields come in the form `model,ID`
    _property_like_fields_to_update = ('value_reference', 'res_id', )

    @api.multi
    def _update_values(self, values):
        """Inverse xmlid values to property values."""
        if self.env.context.get('xmlid_value_reference'):
            for fname in self._property_like_fields_to_update:
                if values.get(fname):
                    values[fname] = xmlid_to_property(self.env, values[fname])
        return super(Property, self)._update_values(values)

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        """Convert property values to xmlid."""
        res = super(Property, self).read(fields=fields, load=load)
        if not self.env.context.get('xmlid_value_reference'):
            return res
        # wipe cache otherwise we gonna get the std value in any case
        self.invalidate_cache(self._property_like_fields_to_update)
        for rec in res:
            for fname in self._property_like_fields_to_update:
                if rec.get(fname):
                    rec[fname] = property_to_xmlid(self.env, rec[fname])
        return res
