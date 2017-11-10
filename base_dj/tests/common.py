# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.tests.common import SavepointCase
from odoo import tools
from odoo.modules.module import get_resource_path
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
