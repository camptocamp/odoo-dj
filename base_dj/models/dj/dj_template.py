# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import jinja2
import os

from odoo import models, fields, api, _
from odoo.modules.module import get_module_resource
from ...utils import to_str


class TemplateMixin(models.AbstractModel):
    """Provide Jinja rendering capabilities."""

    _name = 'dj.template.mixin'
    _description = 'DJ template mixin'

    template_path = fields.Char(
        default=lambda self: self._default_dj_template_path,
        required=True,
    )

    _default_dj_template_path = ''

    @api.multi
    def dj_template_vars(self):
        """Return context variables to render template."""
        self.ensure_one()
        return {}

    @api.multi
    def dj_template(self, path=None):
        """Retrieve Jinja template."""
        self.ensure_one()
        path = path or self.template_path
        # load Jinja template
        mod, filepath = path.split(':')
        filepath = get_module_resource(mod, filepath)
        if not filepath:
            raise LookupError(
                _('Template not found: `%s`') % self.template_path)
        path, filename = os.path.split(filepath)
        return jinja2.Environment(
            loader=jinja2.FileSystemLoader(path)
        ).get_template(filename)

    def dj_render_template(self, template_vars=None):
        """Render template."""
        template = self.dj_template()
        template_vars = template_vars or self.dj_template_vars()
        return to_str(template.render(**template_vars))
