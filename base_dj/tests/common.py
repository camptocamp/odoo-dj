# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.tests.common import SavepointCase
from odoo import tools
from odoo.modules.module import get_resource_path
import difflib

from .lint import run_pylint


class BaseCase(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super(BaseCase, cls).setUpClass()
        cls.compilation_model = cls.env['dj.compilation']
        cls._load_xml('base_dj', 'tests/fixtures/default.xml')

    def _load_filecontent(self, module, filepath):
        with open(get_resource_path(module, filepath), 'r') as fd:
            return fd.read()

    @classmethod
    def _load_xml(cls, module, filepath):
        tools.convert_file(
            cls.cr, module,
            get_resource_path(module, filepath),
            {}, mode='init', noupdate=False, kind='test')

    def _pylint_report(self, filepath):
        return run_pylint(filepath)

    def assertMultiLineEqual(self, first, second, msg=None):
        """Assert that two multi-line strings are equal.

        If they aren't, show a nice diff.
        """
        self.assertTrue(isinstance(first, basestring),
                        'First argument is not a string')
        self.assertTrue(isinstance(second, basestring),
                        'Second argument is not a string')

        if first != second:
            message = ''.join(difflib.ndiff(first.splitlines(True),
                                            second.splitlines(True)))
            if msg:
                message += " : " + msg
            self.fail("Multi-line strings are unequal:\n" + message)
