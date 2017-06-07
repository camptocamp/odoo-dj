# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
from odoo import api, fields, models


class WizardSettingsExporter(models.TransientModel):
    """ This wizard display the code nicely
    it avoids any trim to keep indented code """

    _name = 'wizard.settings.exporter'
    _description = "Wizard to export as text of file the songs script"

    @api.multi
    def _get_default_song_code(self):
        return self._context.get('code')

    code = fields.Text(default=_get_default_song_code, readonly=True)

    # TODO create a binary field to directly create the songs file
