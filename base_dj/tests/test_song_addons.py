# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from . common import BaseCase
from ..config import ADDONS_BLACKLIST


class AddonsSongCase(BaseCase):

    @classmethod
    def setUpClass(cls):
        super(AddonsSongCase, cls).setUpClass()
        fixture = 'fixture_addons_song'
        cls._load_xml('base_dj', 'tests/fixtures/%s.xml' % fixture)

    def test_records(self):
        song = self.env.ref('base_dj.test_song_installed_addons')
        addons = song._get_exportable_records().mapped('name')
        for name in ADDONS_BLACKLIST:
            self.assertNotIn(name, addons)

    def test_installed_addons(self):
        song = self.env.ref('base_dj.test_song_installed_addons')
        self.assertTrue(song.scratchable())
        path, output = song.scratch_it()
        self.assertEqual(path, 'installed_addons.txt')
        tmp_file_path = '/tmp/test_installed_addons.txt'
        with open(tmp_file_path, 'w') as fd:
            fd.write(output)
        # we don't verify output one to one w/ a test file
        # as we might have differences in modules installed.
        # Let's just make sure that all the addons we expect to find are there.
        # The txt should be in the form:
        # - account
        # - account_bank_statement_import
        # - account_check_printing
        # - account_invoicing
        # - account_payment_mode
        # - analytic
        # - auth_crypt
        # - auth_signup
        # - barcodes
        addons = song._get_exportable_records().mapped('name')
        out_lines = output.splitlines()
        for addon in addons:
            self.assertIn('- ' + addon, out_lines)

    def test_compilation_include(self):
        comp = self.env.ref('base_dj.test_comp_addons')
        tracks = comp._get_tracks()
        paths = [x[0] for x in tracks]
        self.assertIn('installed_addons.txt', paths)
