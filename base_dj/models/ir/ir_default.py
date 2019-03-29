# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api
from ...utils import (
    property_to_xmlid,
    xmlid_to_property,
    ODOOVER,
    string_to_list,
)
from odoo.tools import pickle
import json


class DefaultMixin(models.AbstractModel):
    _name = 'default.mixin'
    _value_key = 'value'

    @api.model
    def create(self, vals):
        self._dj_xmlid_to_values(vals)
        return super(DefaultMixin, self).create(vals)

    @api.multi
    def write(self, vals):
        self._dj_xmlid_to_values(vals)
        return super(DefaultMixin, self).write(vals)

    def _dj_xmlid_to_values(self, vals):
        """Convert xmlid to db values."""
        raise NotImplementedError()

    def _dj_get_relation_field(self, vals):
        """Return field info if values match a related field."""
        raise NotImplementedError()

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        """Convert values to xmlid."""
        res = super(DefaultMixin, self).read(fields=fields, load=load)
        if not self.env.context.get('xmlid_value_reference'):
            return res
        # wipe cache otherwise we gonna get the std value in any case
        self.invalidate_cache([self._value_key])
        self._dj_values_to_xmlid(res)
        return res

    def _dj_values_to_xmlid(self, records):
        """Convert values to xmlids when needed."""
        for rec in records:
            if rec.get(self._value_key):
                # handle relation fields
                field = self._dj_get_relation_field(rec['field_id'])
                if field:
                    rec[self._value_key] = self._dj_value_to_xmlid(field, rec)

    def _dj_value_to_xmlid(self, field, rec):
        raise NotImplementedError()


class IRDefault(models.Model):

    _name = 'ir.default'
    _inherit = [
        'ir.default',
        'default.mixin',
    ]
    _value_key = 'json_value'

    def _dj_get_relation_field(self, field_id):
        """Return field info if values match a related field."""
        if not field_id:
            return None
        field = self.env['ir.model.fields'].browse(field_id)
        return field if field.ttype in ('many2one', 'many2many') else None

    def _dj_xmlid_to_values(self, vals):
        """Convert xmlid to db values."""
        if (self.env.context.get('xmlid_value_reference', False) and
                vals.get(self._value_key)):
            # TODO: make this more reliable and make sure we have a field
            field_id = vals.get('field_id', self.field_id.id)
            field = self._dj_get_relation_field(field_id)
            # TODO: `vals[self._value_key] == '[]'` means we are exporting
            # an empty json list. We should avoid that.
            if field and not vals[self._value_key] == '[]':
                values = string_to_list(
                    vals[self._value_key],
                    modifier=lambda x: self.env.ref(x).id)
                if field.ttype == 'many2one':
                    values = values[0]
                vals[self._value_key] = json.dumps(values)

    def _dj_value_to_xmlid(self, field, rec):
        value = rec[self._value_key]
        rec_ids = json.loads(value)
        model = self.env[field['relation']]
        if rec_ids:
            if isinstance(rec_ids, list):
                value = ','.join([model.browse(rec_id)._dj_export_xmlid()
                                    for rec_id in rec_ids])
            else:
                value = model.browse(rec_ids)._dj_export_xmlid()
        return value
