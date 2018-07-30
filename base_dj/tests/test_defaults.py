# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from . common import BaseCase
from .fake_models import TestDefaults
import json


class DefaultsSongCase(BaseCase):

    TEST_MODELS_KLASSES = [TestDefaults, ]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_test_models()
        # the behavior we expect is the same
        # we only have to switch model name based on odoo version
        fixture = 'fixture_song_ir_default_v11'
        cls._load_xml('base_dj', 'tests/fixtures/%s.xml' % fixture)
        cls.main_partner = cls.env.ref('base.main_partner')

    @classmethod
    def tearDownClass(cls):
        cls._teardown_models()
        super().tearDownClass()

    def _get_default_record(self, model_name, field_name):
        field = self.env['ir.model.fields']._get(model_name, field_name)
        return self.env['ir.default'].search([
            ('field_id', '=', field.id),
        ], limit=1)

    def test_fixture_data(self):
        """Verify that we have proper data to test."""
        default_model = self.env['ir.default']
        defaults = default_model.get_model_defaults('dj.test.defaults')
        self.assertIn('partner_id', defaults)
        self.assertEqual(defaults['partner_id'], self.main_partner.id)

    def test_read_value_standard(self):
        """Verify that we don't alter default behavior."""
        record = self._get_default_record('dj.test.defaults', 'partner_id')
        expected = json.dumps(self.main_partner.id)
        value = record.json_value
        self.assertEqual(value, expected)

    def test_read_value_xmlid_converted(self):
        """Verify that we get an xmlid when dj context key is set."""
        record = self._get_default_record('dj.test.defaults', 'partner_id')
        expected = 'base.main_partner'
        value = record.with_context(xmlid_value_reference=True).json_value
        self.assertEqual(value, expected)

    def test_write_value_standard(self):
        """Verify that standard write is not altered."""
        record = self._get_default_record('dj.test.defaults', 'partner_id')
        expected = record.json_value = json.dumps(self.main_partner.id)
        record = self._get_default_record('dj.test.defaults', 'partner_id')
        self.assertEqual(record.json_value, expected)

    def test_write_value_from_xmlid(self):
        """Verify that we can write w/ xmlids and get converted to IDs."""
        record = self._get_default_record('dj.test.defaults', 'partner_id')
        record.with_context(
            xmlid_value_reference=True).json_value = 'base.main_partner'
        expected = self.main_partner.id
        record.invalidate_cache()
        self.assertEqual(record.json_value, json.dumps(expected))
