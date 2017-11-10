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

    def _load_filecontent(self, module, filepath):
        with open(get_resource_path(module, filepath), 'r') as fd:
            return fd.read()

    def _load_xml(self, module, filepath):
        tools.convert_file(
            self.cr, module,
            get_resource_path(module, filepath),
            {}, mode='init', noupdate=False, kind='test')

    def _pylint_report(self, filepath):
        return run_pylint(filepath)
