# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import models, api, tools
from ..utils import string_to_list

import logging
_logger = logging.getLogger(__file__)

# TODO remove as deprecated.
# ATM we are exporting / importing full records
# and being res.config.settings just a proxy to real records field_strings
# is kind of useless to import them too.
# Plus, they are hard to debug and really heavy to create/update
# since in v11 they stay in one single model.


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
        res = super()._add_missing_default_values(vals)
        if self.env.context.get('dj_export'):
            _logger.info('Settings export DEPRECATED.')
            fnames = list(res.keys())
            allowed = self._dj_settings_fields_get(vals)
            for fname in fnames:
                if fname not in allowed and fname not in vals:
                    res.pop(fname)
        return res

    @tools.ormcache('self')
    def _dj_settings_fields_get(self, vals=None):
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
        whitelisted.append('company_id')
        required = [
            k for k, v in self.fields_get().items()
            if v['required']
        ]
        allowed = list(vals.keys() if vals else []) + whitelisted + required
        return list(set(allowed))
