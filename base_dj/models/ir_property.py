# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api


class Property(models.Model):

    _inherit = 'ir.property'

    @api.multi
    def _update_values(self, values):
        """Inverse xmlid value to reference value."""
        if self.env.context.get('xmlid_value_reference', False):
            record = self.env.ref(values.get('value_reference'))
            value = u'%s,%i' % (record._name, record.id)
            values['value_reference'] = value
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
                model, res_id = rec['value_reference'].split(',')
                value = self.env[model].browse(int(res_id))._dj_export_xmlid()
                rec['value_reference'] = value
        return res
