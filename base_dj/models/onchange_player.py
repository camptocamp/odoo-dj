# © 2013-TODAY Akretion (Sébastien Beau)
# © 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

# Grabbed from
# OCA/connector-ecommerce/connector_ecommerce/unit/sale_order_onchange.py
# and adapted to make it generic.
# TODO: release into independent module in server-tools

from odoo import models, api


class OnchangePlayer(models.AbstractModel):
    _name = 'onchange.player.mixin'
    _description = 'Onchange player mixin'

    def _play_new_values(self, values, onchange_values,
                         override_existing=True):
        """Prepare new values with onchaged ones.

        :param values: current record values
        :param onchange_values: current record changed values
        :param override_existing: override existing values or not.
            When true values already contained in `values` will be overridden.
            When false any value already in `values` won't be overriden.
        """
        vals = onchange_values.get('value', {})
        new_values = {}
        for fieldname, value in vals.items():
            if fieldname not in values or override_existing:
                new_values[fieldname] = value
        return new_values

    def _play_onchanges(self, record, model=None,
                        onchange_fields=None, override_existing=True):
        """Play the onchanges on given record.

        :param record: a browse record or dictionary w/ record values
        :param model: if `record` is a dictionary you must pass a model name
        :param onchange_fields: specify onchange fields to play with.
            Default: all onchange fields by model's spec.
        :param override_existing: override existing values or not.
            When true values already contained in `values` will be overridden.
            When false any value already in `values` won't be overriden.
        """
        assert (
            isinstance(record, models.BaseModel) or
            isinstance(record, dict) and model
        ), 'You must pass a browse record or dict and a model.'
        if isinstance(record, models.BaseModel):
            values = record.copy_data()[0]
            model = self.env[record._name]
        else:
            values = record
            model = self.env[model]
        onchange_specs = model._onchange_spec()
        if not onchange_fields:
            onchange_fields = []
            for fname, has_onchange in onchange_specs.items():
                if has_onchange:
                    onchange_fields.append(fname)

        # we need all fields in the dict even the empty ones
        # otherwise 'onchange()' will not apply changes to them
        all_values = values.copy()
        for field in list(model.fields_get().keys()):
            if field not in all_values:
                all_values[field] = False

        # we work on a temporary record
        new_record = model.new(all_values)

        new_values = {}
        for field in onchange_fields:
            onchange_values = new_record.onchange(all_values,
                                                  field, onchange_specs)
            new_values.update(
                self._play_new_values(
                    values, onchange_values,
                    override_existing=override_existing)
            )
            all_values.update(new_values)

        res = {f: v for f, v in all_values.items()
               if f in values or f in new_values}
        return res

    @api.multi
    def play_onchanges(self, inplace=True):
        """Play the onchanges on current recordset.

        :param inplace: modify record on the fly.
        """
        self.ensure_one()
        changed_values = self._play_onchanges(
            self,
            onchange_fields=self.env.context.get('onchange_fields', []))
        if inplace:
            self.write(changed_values)
        return changed_values
