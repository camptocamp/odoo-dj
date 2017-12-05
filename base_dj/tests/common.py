# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.tests.common import SavepointCase
from odoo import tools
from odoo.modules.module import get_resource_path
import difflib
import io

from .lint import run_pylint
from .xml_compare import xml_compare
from ..utils import to_str


def load_filecontent(module, filepath, mode='r'):
    path = get_resource_path(module, filepath)
    with io.open(path, mode) as fd:
        return to_str(fd.read())


class BaseCase(SavepointCase):

    post_install = True
    at_install = False

    @classmethod
    def setUpClass(cls):
        super(BaseCase, cls).setUpClass()
        cls.compilation_model = cls.env['dj.compilation']
        cls._load_xml('base_dj', 'tests/fixtures/default.xml')

    def _load_filecontent(self, module, filepath, mode='r'):
        return load_filecontent(module, filepath, mode=mode)

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
        self.assertTrue(isinstance(first, str),
                        'First argument is not a string')
        self.assertTrue(isinstance(second, str),
                        'Second argument is not a string')

        if first != second:
            message = ''.join(difflib.ndiff(first.splitlines(True),
                                            second.splitlines(True)))
            if msg:
                message += " : " + msg
            self.fail("Multi-line strings are unequal:\n" + message)

    def assertXMLEqual(self, a, b):
        return xml_compare(a, b)

    @classmethod
    def add_xmlid(cls, record, xmlid, noupdate=False):
        """ Add a XMLID on an existing record """
        try:
            ref_id, __, __ = cls.env['ir.model.data'].xmlid_lookup(xmlid)
        except ValueError:
            pass  # does not exist, we'll create a new one
        else:
            return cls.env['ir.model.data'].browse(ref_id)
        if '.' in xmlid:
            module, name = xmlid.split('.')
        else:
            module = ''
            name = xmlid
        return cls.env['ir.model.data'].create({
            'name': name,
            'module': module,
            'model': record._name,
            'res_id': record.id,
            'noupdate': noupdate,
        })


class BaseCompilationCase(BaseCase):

    def _assert_compilation_output(
            self, fixture, output, expected_output, path, expected_path):

        self.assertEqual(path, expected_path)
        self.assertMultiLineEqual(expected_output, output)

        # save it to tmp to be able to run pylint and ease manual check
        tmp_file_path = '/tmp/test_%s.py' % fixture
        with open(tmp_file_path, 'w') as fd:
            fd.write(output)

        lint_errors = self._pylint_report(tmp_file_path)
        self.assertEqual(lint_errors, None)

    def _burn_and_test(self, fixture, expected_path, compilation):
        # load fixture
        self._load_xml('base_dj', 'tests/fixtures/%s.xml' % fixture)
        # load expected result
        expected_output = self._load_filecontent(
            'base_dj', 'tests/fixtures/%s.py' % fixture)
        # load compilation if needed
        if isinstance(compilation, str):
            compilation = self.env.ref(compilation)
        # avoid burning self configs
        comp = compilation.with_context(dj_burn_skip_self=True)
        path, output = comp.burn_disc()
        self._assert_compilation_output(
            fixture,
            output,
            expected_output,
            path,
            expected_path)
