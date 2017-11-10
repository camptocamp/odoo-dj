# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from . common import BaseCase


class CompilationCase(BaseCase):

    @classmethod
    def setUpClass(cls):
        super(CompilationCase, cls).setUpClass()

    def test_create_and_burn(self):
        self._load_xml('base_dj', 'tests/fixtures/fixture_comp1.xml')
        expected = self._load_filecontent(
            'base_dj', 'tests/fixtures/fixture_comp1.py')
        comp = self.env.ref('base_dj.dj_test_comp1')
        # avoid burning self config
        comp = comp.with_context(dj_burn_skip_self=True)
        path, content = comp.burn_disc()
        # write to /tmp to ease verification
        with open('/tmp/test_create_and_burn.py', 'w') as fd:
            fd.write(content)
        self.assertEqual(path, u'songs/install/generated/dj_test.py')
        self.assertEqual(expected, content)
