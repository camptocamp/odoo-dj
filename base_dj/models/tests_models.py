# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import api, fields, models, tools
import os

testing = tools.config.get('test_enable') or os.environ.get('ODOO_TEST_ENABLE')

if testing:
    class TestConfiguration(models.TransientModel):
        _name = 'dj.test.config.settings'
        _inherit = 'res.config.settings'

        company_id = fields.Many2one(
            string='The company',
            comodel_name='res.company',
            default=lambda self: self.env.user.company_id,
        )
        field_char = fields.Char(string='A char field')
        field_text = fields.Text(string='A text field')
        field_bool = fields.Boolean(string='A bool field', default=False)
        field_integer = fields.Integer(string='A integer field', default=1)
        field_float = fields.Float(string='A float field', default=1.0)
        field_date = fields.Date(
            string='A date field', default=fields.Date.context_today)
        field_datetime = fields.Datetime(
            string='A datetime field', default=fields.Date.context_today)
        field_selection_int = fields.Selection(
            string='A selection field (int)',
            selection=[(0, "No"), (1, "Yes")])
        field_selection_char = fields.Selection(
            string='A selection field (txt)',
            selection=[('not ok', "Not ok"), ("ok", "Ok")])

        def _set_default_value(self, key, value):
            try:
                handler = self.env['ir.values'].sudo().set_default
            except KeyError:
                # v11
                handler = self.env['ir.default'].sudo().set
            return handler(self._name, key, value)

        @api.multi
        def set_values(self):
            _super = super(TestConfiguration, self)
            if hasattr(_super, 'set_values'):
                # v11
                _super.set_values()
            fnames = [
                x for x in self.fields_get().keys() if x.startswith('field_')]
            for fname in fnames:
                self._set_default_value(fname, self[fname])
