# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import models, api


class IrModel(models.Model):

    _inherit = 'ir.model'

    @api.multi
    def name_get(self):
        """Show only model dotted name on demand."""
        if self.env.context.get('model_tech_name_only'):
            return [
                (x.id, x.model) for x in self
            ]
        return super(IrModel, self).name_get()


class IrModelFields(models.Model):

    _inherit = 'ir.model.fields'

    @api.multi
    def name_get(self):
        """Show only model dotted name on demand."""
        if self.env.context.get('model_tech_name_only'):
            return [
                (x.id, '%s (%s)' % (x.field_description, x.name)) for x in self
            ]
        return super(IrModelFields, self).name_get()
