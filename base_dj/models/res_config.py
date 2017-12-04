# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import models, api
from ..utils import string_to_list


class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'

    @api.model
    def _add_missing_default_values(self, vals):
        """Exclude unwanted fields.

        This method is called to add all missing fields on create.
        When exporting we don't need all the fields.
        All 'default_', 'group_', 'module_' should be discarded
        as we export them separately.
        In this way we speed up the export (is taking a lot w/ all the fields)
        and we export only what we need.
        """
        res = super(ResConfigSettings, self)._add_missing_default_values(vals)
        if self.env.context.get('dj_export'):
            fnames = list(res.keys())
            whitelisted = list(self._dj_settings_fields(vals).keys())
            for fname in fnames:
                if fname not in vals:
                    if fname not in whitelisted:
                        res.pop(fname)
                    else:
                        # such fields can appear in `other` too
                        if fname.startswith(('default_', 'group_', 'module_')):
                            res.pop(fname)
        return res

    def _dj_settings_fields(self, vals=None):
        """Take control on which settings fields are exported."""
        # {'default': [...], 'group': [...], 'module': [...], 'other': [...]}
        # exclude default_ -> add default song in core compilation
        # exclude module_ -> add installed addons in core compilation
        # exclude group_ -> add a core song to export only main groups
        #    (portal, public, user) w/ just implied_ids field
        # exclude related= -> they come within company export
        whitelisted = self._get_classified_fields()['other']
        specific_fields = self.env.context.get('dj_settings_fields_whitelist')
        if specific_fields:
            whitelisted = string_to_list(specific_fields)
        else:
            whitelisted = list(vals.keys() if vals else [])
        return self.fields_get(whitelisted)
