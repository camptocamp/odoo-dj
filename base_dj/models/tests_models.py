# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import api, fields, models, tools
import logging
import os

_logger = logging.getLogger(__file__)

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

    class TestMixin(models.AbstractModel):

        _name = 'test.mixin'
        MOD_NAME = 'base_dj'

        @api.model
        def _setup_complete(self):
            super(TestMixin, self)._setup_complete()
            self._setup_ACL()

        def _setup_ACL(self):
            """Setup ACL on the fly for any test model.

            This makes Odoo happy :)
            """
            xmlid = 'access_test_{}'.format(self._table)
            if (self._auto and
                    not self.env.ref(xmlid, raise_if_not_found=False)):
                model_xmlid = '{module}.model_{model}'.format(
                    module=self.MOD_NAME,
                    model=self._table,
                )
                if self.env.ref(model_xmlid, raise_if_not_found=False):
                    header = ['id', 'name', 'model_id:id', 'group_id:id',
                              'perm_read', 'perm_write',
                              'perm_create', 'perm_unlink']
                    acl_data = [
                        [xmlid,
                         'access_test_{}'.format(self._table),
                         model_xmlid,
                         'base.group_system',
                         '1', '1', '1', '1'],
                    ]
                    result = self.env['ir.model.access'].load(header, acl_data)
                    if result['messages']:
                        _logger.warning(result['messages'])

    class TestDefaults(models.Model):
        _name = 'dj.test.defaults'
        _inherit = 'test.mixin'

        partner_id = fields.Many2one(
            string='The partner',
            comodel_name='res.partner',
        )

    class TestFileFields(models.Model):
        _name = 'dj.test.filefields'
        _inherit = 'test.mixin'

        @property
        def _dj_file_fields_names(self):
            # arch_db is automatically added here
            base = list(super(TestFileFields, self)._dj_file_fields_names)
            return base + ['some_text', ]

        name = fields.Char()
        some_html = fields.Html()
        some_text = fields.Text()
        arch_db = fields.Text()
        some_image = fields.Binary()
        some_file = fields.Binary()
