# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api
from ...utils import (
    property_to_xmlid,
    xmlid_to_property,
    ODOOVER,
)
from odoo.tools import pickle


class DefaultMixin(models.AbstractModel):
    _name = 'default.mixin'

    def _get_relation_field(self, vals):
        """Return field info if values match a related field."""
        fname = vals['name']
        model = self.env[vals['model']]
        if fname in model:
            field = model.fields_get([fname])[fname]
            # catch x2x + company_dependent fields (that are m2o anyway)
            return field if field.get('relation') else None
        return None

    def _dj_xmlid_to_values(self, vals):
        """Convert xmlid to db values."""
        if (self.env.context.get('xmlid_value_reference', False) and
                vals.get('value')):
            if vals.get('key') == 'action':
                vals['value'] = xmlid_to_property(self.env, vals['value'])
            elif vals.get('key') == 'default':
                field = self._get_relation_field(vals)
                if field:
                    vals['value'] = \
                        pickle.dumps(self.env.ref(vals['value']).id)

    @api.model
    def create(self, vals):
        self._dj_xmlid_to_values(vals)
        return super(DefaultMixin, self).create(vals)

    @api.multi
    def write(self, vals):
        self._dj_xmlid_to_values(vals)
        return super(DefaultMixin, self).write(vals)

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        """Convert values to xmlid."""
        res = super(DefaultMixin, self).read(fields=fields, load=load)
        if not self.env.context.get('xmlid_value_reference'):
            return res
        # wipe cache otherwise we gonna get the std value in any case
        self.invalidate_cache(['value'])
        for rec in res:
            if rec.get('value') and rec.get('key') == 'action':
                # relation to actions
                rec['value'] = property_to_xmlid(self.env, rec['value'])
            elif rec.get('value') and rec.get('key') == 'default':
                # handle relation fields
                field = self._get_relation_field(rec)
                if field:
                    # DO NOT USE `value_unpickle` + browse record
                    # otherwise when changing `value` we are going
                    # to break `value_unpickle` computation
                    rec_id = int(pickle.loads(rec['value']))
                    model = self.env[field['relation']]
                    rec['value'] = model.browse(rec_id)._dj_export_xmlid()
        return res


if ODOOVER >= 11.0:
    class IRDefault(models.Model):

        _name = 'ir.default'
        _inherit = [
            'ir.default',
            'default.mixin',
        ]
else:
    class IRValues(models.Model):

        _name = 'ir.values'
        _inherit = [
            'ir.values',
            'default.mixin',
        ]
