# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from . common import BaseCompilationCase
try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

DJ_COMPILATION_MODEL_PATH = \
    'odoo.addons.base_dj.models.dj.dj_compilation.Compilation'


class CompilationCase(BaseCompilationCase):

    def burn_contents(self):
        fixture = 'fixture_comp1'
        self._load_xml('base_dj', 'tests/fixtures/%s.xml' % fixture)
        comp = self.env.ref('base_dj.test_comp1')
        tracks = comp.with_context(
            dj_read_skip_special_fields=True
        ).get_all_tracks(include_core=False)
        return tracks

    def test_disc_path(self):
        genre = self.env.ref('base_dj.test_genre')
        comp = self.env['dj.compilation'].create({
            'name': 'Foo',
            'genre_id': genre.id,
        })
        # name is normalized
        self.assertEqual(comp.name, 'foo')
        # path defaults to songs/{data_mode}/generated/{genre}/{name}.py
        self.assertEqual(
            comp.disc_full_path(),
            'songs/install/generated/dj_test/foo.py'
        )

    def test_disc_path_custom(self):
        genre = self.env.ref('base_dj.test_genre')
        comp = self.env['dj.compilation'].create({
            'name': 'Bar Baz',
            'genre_id': genre.id,
            'disc_path': 'songs/{name}.py',
        })
        # name is normalized
        self.assertEqual(comp.name, 'bar_baz')
        # path defaults to songs/{data_mode}/generated/{genre}_{name}.py
        self.assertEqual(
            comp.disc_full_path(),
            'songs/bar_baz.py'
        )

    def test_burn_and_test1(self):
        fixture = 'fixture_comp1'
        expected_path = 'songs/install/generated/dj_test/comp1.py'
        self._burn_and_test(fixture, expected_path, 'base_dj.test_comp1')

    def test_burn_defer_parent(self):
        fixture = 'fixture_defer_parent'
        expected_path = 'songs/install/generated/dj_test/comp4.py'
        self._burn_and_test(fixture, expected_path, 'base_dj.test_comp4')

    def test_burn_contents(self):
        tracks = self.burn_contents()
        paths = sorted([x[0] for x in tracks])
        expected = sorted([
            'DEV_README.rst',
            'install/generated/dj_test/comp1/res.company.csv',
            'install/generated/dj_test/comp1/res.partner.csv',
            'install/generated/dj_test/comp1/res.users.csv',
            'songs/install/__init__.py',
            'songs/install/generated/__init__.py',
            'songs/install/generated/dj_test/__init__.py',
            'songs/install/generated/dj_test/comp1.py',
        ])
        self.assertListEqual(paths, expected)

    def test_burn_contents_with_core(self):
        fixture = 'fixture_comp1'
        self._load_xml('base_dj', 'tests/fixtures/%s.xml' % fixture)
        fixture = 'fixture_comp_core'
        self._load_xml('base_dj', 'tests/fixtures/%s.xml' % fixture)
        comp = self.env.ref('base_dj.test_comp1')

        # patch get core compilation to isolate test
        core_comp = self.env.ref('base_dj.test_comp_core1')
        to_patch = DJ_COMPILATION_MODEL_PATH + '._get_core_compilations'
        with patch(to_patch) as mocked:
            mocked.return_value = core_comp
            tracks = comp.with_context(
                dj_read_skip_special_fields=True).get_all_tracks()

        paths = sorted([x[0] for x in tracks])
        expected = sorted([
            'DEV_README.rst',
            'install/generated/dj_test/core1/ir.default.csv',
            'install/generated/dj_test/core1/res.lang.csv',
            'install/generated/dj_test/comp1/res.company.csv',
            'install/generated/dj_test/comp1/res.partner.csv',
            'install/generated/dj_test/comp1/res.users.csv',
            'songs/install/__init__.py',
            'songs/install/generated/__init__.py',
            'songs/install/generated/dj_test/__init__.py',
            'songs/install/generated/dj_test/comp1.py',
            'songs/install/generated/dj_test/core1.py',
        ])
        self.assertListEqual(paths, expected)

    def test_content__init__(self):
        tracks = self.burn_contents()
        init_content_list = [x[1] for x in tracks if '__init__.py' in x[0]]
        for init_content in init_content_list:
            self.assertEqual(init_content, '#\n')
