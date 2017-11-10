# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from . common import BaseCase


class CompilationCase(BaseCase):

    @classmethod
    def setUpClass(cls):
        super(CompilationCase, cls).setUpClass()

    def _assert_compilation_output(
            self, fixture, output, expected_output, path, expected_path):

        self.assertEqual(path, expected_path)
        self.assertEqual(expected_output, output)

        tmp_file_path = '/tmp/test_%s.py' % fixture
        with open(tmp_file_path, 'w') as fd:
            fd.write(output)

        lint_errors = self._pylint_report(tmp_file_path)
        self.assertEqual(lint_errors, None)

    def test_create_and_burn(self):
        fixture = 'fixture_comp1'
        self._load_xml('base_dj', 'tests/fixtures/%s.xml' % fixture)
        expected_output = self._load_filecontent(
            'base_dj', 'tests/fixtures/%s.py' % fixture)
        expected_path = u'songs/install/generated/dj_test.py'
        comp = self.env.ref('base_dj.test_comp1')
        # avoid burning self config
        comp = comp.with_context(dj_burn_skip_self=True)
        path, output = comp.burn_disc()
        self._assert_compilation_output(
            fixture,
            output,
            expected_output,
            path,
            expected_path)
