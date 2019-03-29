# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from . common import BaseCase
from ..config import SPECIAL_FIELDS


class SongCase(BaseCase):

    @classmethod
    def setUpClass(cls):
        super(SongCase, cls).setUpClass()
        fixture = 'fixture_song1'
        cls._load_xml('base_dj', 'tests/fixtures/%s.xml' % fixture)

    def test_get_all_fields(self):
        """Get all the fields that are 'exportable'."""
        song = self.env.ref('base_dj.test_song1_partner_category')
        all_fields = song._get_all_fields().mapped('name')
        special = SPECIAL_FIELDS[:] + [
            # computed and o2m should be excluded
            'parent_right',
            'parent_left',
            'child_ids'
        ]
        for special in SPECIAL_FIELDS:
            self.assertNotIn(special, all_fields)
        self.assertEqual(sorted(all_fields), sorted([
            'name', 'color',
            'parent_id', 'parent_path',
            'partner_ids', 'active',
        ]))

    def test_get_csv_names(self):
        """Retrieve listed filenames."""
        song = self.env.ref('base_dj.test_song1_partner_category')
        fnames = song.get_csv_field_names()
        # we listed only parent_id and name
        self.assertEqual(sorted(fnames), sorted([
            'id',  # always available
            'name', 'parent_id/id',  # relation are always suffixed w/ `/id`
        ]))

    def test_get_csv_names_blacklisted(self):
        """Retrieve listed filenames."""
        song = self.env.ref('base_dj.test_song1_partner2')
        fnames = song.get_csv_field_names()
        for fname in ('phone', 'ref'):
            self.assertNotIn(fname, fnames)

    def test_get_records(self):
        """No particular settings: get all the records."""
        song = self.env.ref('base_dj.test_song1_partner_category')
        all_records = self.env['res.partner.category'].search([])
        records = song._get_exportable_records()
        self.assertEqual(len(records), len(all_records))

    def test_get_records_blacklist(self):
        """Record blacklisted via equalizer."""
        song = self.env.ref('base_dj.test_song1_users')
        all_records = self.env['res.users'].search([])
        records = song._get_exportable_records()
        # thanks to a specific equalizer for users `admin` should be excluded
        self.assertEqual(len(records), len(all_records) - 1)

    def test_make_csv(self):
        """Record blacklisted via equalizer."""
        song = self.env.ref('base_dj.test_song1_partner_category')
        path, content = song.make_csv()
        # TODO: check results, we are just testing that it does not break ATM
        self.assertTrue(path)
        self.assertTrue(content)
