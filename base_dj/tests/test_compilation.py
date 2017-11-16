# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from . common import BaseCompilationCase


class CompilationCase(BaseCompilationCase):

    def test_burn_and_test1(self):
        fixture = 'fixture_comp1'
        expected_path = u'songs/install/generated/dj_test.py'
        self._burn_and_test(fixture, expected_path, 'base_dj.test_comp1')

    def test_burn_defer_parent(self):
        fixture = 'fixture_defer_parent'
        expected_path = u'songs/install/generated/dj_test.py'
        self._burn_and_test(fixture, expected_path, 'base_dj.test_comp4')
