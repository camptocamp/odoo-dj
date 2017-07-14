# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from jinja2 import BaseLoader, TemplateNotFound
from os.path import join, exists, getmtime

from odoo.modules.module import get_module_resource

class DiscLoader(BaseLoader):
    """ A Jinja2 Loader for Definition of Implementable Songs Code """

    def __init__(self, module):
        self.path = get_module_resource(module, 'discs')

    def get_source(self, environment, disc):
        path = join(self.path, disc)
        if not exists(path):
            raise TemplateNotFound(disc)
        mtime = getmtime(path)
        with file(path) as f:
            source = f.read().decode('utf-8')
        return source, path, lambda: mtime == getmtime(path)
