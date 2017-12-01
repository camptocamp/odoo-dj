# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields
from odoo.tools import mute_logger
from . common import BaseCase


class SettingsSongCase(BaseCase):

    @classmethod
    def setUpClass(cls):
        super(SettingsSongCase, cls).setUpClass()
        fixture = 'fixture_settings_song1'
        cls._load_xml('base_dj', 'tests/fixtures/%s.xml' % fixture)
        cls.test_model = 'dj.test.config.settings'
        cls.companies = cls.env['res.company'].search([])

    @mute_logger('odoo.models.unlink')
    def tearDown(self):
        try:
            self.env['ir.values'].search([]).unlink()
        except KeyError:
            # v11
            self.env['ir.default'].search([]).unlink()

    def _custom_ctx(self, fields=None):
        fields = fields or (
            'field_bool', 'field_char', 'field_text',
            'field_integer', 'field_float', 'field_date',
            'field_datetime', 'field_selection_int', 'field_selection_char',
            'company_id',
        )
        return dict(
            # limit the export to main company as we are in control of it.
            # In this way we avoid clashes w/ other companies that might
            # been set up from other test suites, when running tests
            # on several modules at once.
            dj_settings_company_xmlids='base.main_company',
            # limit fields to the ones in our settings model.
            # In v11 all the *.config.settings have been merged
            # into `res.config.settings`
            # so we don't want to check all the fields out there.
            dj_settings_fields=','.join(fields),
        )

    def test_settings_values_all_companies(self):
        song = self.env.ref('base_dj.test_song_test_config_settings1')
        self.env[self.test_model].create({})
        all_vals = song.dj_get_settings_vals()
        # we should get as many items as many companies
        self.assertEqual(len(all_vals), len(self.companies))

    def test_settings_values_defaults(self):
        song = self.env.ref('base_dj.test_song_test_config_settings1')
        self.env[self.test_model].create({}).execute()
        all_vals = song.with_context(
            **self._custom_ctx()).dj_get_settings_vals()
        # we should get as many items as many companies
        self.assertEqual(len(all_vals), 1)
        vals = all_vals[0]
        # song name
        self.assertEqual(vals[0], 'dj_test_config_settings_djc')
        # company_aka
        self.assertEqual(vals[1], 'djc')
        expected_vals = {
            # values
            'company_id': {'label': 'The company',
                           'val': "ctx.env.ref('base.main_company').id"},
            'field_bool': {'label': 'A bool field', 'val': False},
            'field_char': {'label': 'A char field', 'val': False},
            'field_date': {'label': 'A date field',
                           'val': "'{}'".format(fields.Date.today())},
            'field_datetime': {
                'label': 'A datetime field',
                'val': "'{} 00:00:00'".format(fields.Date.today())
            },
            'field_float': {'label': 'A float field', 'val': 1.0},
            'field_integer': {'label': 'A integer field', 'val': 1},
            'field_selection_char': {'label': 'A selection field (txt)',
                                     'val': False},
            'field_selection_int': {'label': 'A selection field (int)',
                                    'val': False},
            'field_text': {'label': 'A text field', 'val': False}
        }
        for key in list(expected_vals.keys()):
            self.assertDictEqual(expected_vals[key], vals[-1][key])

    def test_settings_values_custom(self):
        song = self.env.ref('base_dj.test_song_test_config_settings1')
        self.env[self.test_model].create({
            'field_bool': True,
            'field_char': 'Great!',
            'field_text': 'Hello there!\nLet\'s try this.',
            'field_integer': 10,
            'field_float': 20.0,
            'field_date': '2017-11-15',
            'field_datetime': '2017-11-14 10:00:00',
            'field_selection_int': 1,
            'field_selection_char': 'ok',
        }).execute()
        all_vals = song.with_context(
            **self._custom_ctx()).dj_get_settings_vals()
        # we should get as many items as many companies
        self.assertEqual(len(all_vals), 1)
        vals = all_vals[0]
        # song name
        self.assertEqual(vals[0], 'dj_test_config_settings_djc')
        # company_aka
        self.assertEqual(vals[1], 'djc')
        expected_vals = {
            # values
            'company_id': {'label': 'The company',
                           'val': "ctx.env.ref('base.main_company').id"},
            'field_bool': {'label': 'A bool field', 'val': True},
            # text quoted
            'field_char': {'label': 'A char field', 'val': "'Great!'"},
            'field_date': {'label': 'A date field',
                           'val': "'2017-11-15'"},
            'field_datetime': {'label': 'A datetime field',
                               'val': "'2017-11-14 10:00:00'"},
            'field_float': {'label': 'A float field', 'val': 20.0},
            'field_integer': {'label': 'A integer field', 'val': 10},
            'field_selection_char': {'label': 'A selection field (txt): Ok',
                                     'val': "'ok'"},
            'field_selection_int': {'label': 'A selection field (int): Yes',
                                    'val': 1},
            # text triple quoted
            'field_text': {'label': 'A text field',
                           'val': '"""Hello there!\nLet\'s try this."""'}
        }
        for key in list(expected_vals.keys()):
            self.assertDictEqual(expected_vals[key], vals[-1][key])

    def test_settings_output(self):
        song = self.env.ref('base_dj.test_song_test_config_settings1')
        vals = {
            'field_bool': True,
            'field_char': 'Great!',
            'field_text': 'Hello there!\nLet\'s try this.',
            'field_integer': 10,
            'field_float': 20.0,
            'field_date': '2017-11-15',
            'field_datetime': '2017-11-14 10:00:00',
            'field_selection_int': 1,
            'field_selection_char': 'ok',
        }
        self.env[self.test_model].create(vals).execute()
        output = song.with_context(
            **self._custom_ctx()).dj_render_template()
        expected = self._load_filecontent(
            'base_dj', 'tests/fixtures/fixture_settings_song1.pytxt')
        tmp_file_path = '/tmp/test_settings_output.py'
        with open(tmp_file_path, 'w') as fd:
            fd.write(output)
        self.assertMultiLineEqual(output.strip(), expected.strip())
