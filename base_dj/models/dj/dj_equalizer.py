# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import models, fields, api
from odoo.tools.safe_eval import safe_eval
from collections import OrderedDict
from ...utils import string_to_list


class OrderedContext(OrderedDict):

    def __str__(self):
        return str(dict(self))

    def __repr__(self):
        return str(dict(self))


class DJEqualizer(models.Model):
    """Hold models' global configuration."""

    _name = 'dj.equalizer'
    _description = 'DJ Equalizer'

    model = fields.Char(default='')
    xmlid_fields = fields.Char(default='')
    xmlid_policy = fields.Selection(
        selection=[('normal', 'Normal'), ('hash', 'Hash')],
        default='normal',
        help='`Normal` will join all fields, '
             '`hash` will use specified fields to build an hash.'
    )
    xmlid_table_name = fields.Char(
        default='',
        help='Sometimes the xmlid can be veeeeery long, like for companies. '
             'You can use this field to short a bit the result. '
             'For instance: `res_company` -> `company`.')
    model_context = fields.Char(default='{}')
    field_blacklist = fields.Char(default='')
    record_blacklist = fields.Char(default='')

    @api.multi
    def get_model_context(self):
        if not self.ids:
            return {}
        self.ensure_one()
        return OrderedContext(
            safe_eval(self.model_context) if self.model_context else {}
        )

    @api.multi
    def get_xmlid_fields(self):
        if not self.ids:
            return []
        self.ensure_one()
        return string_to_list(self.xmlid_fields)

    @api.multi
    def get_field_blacklist(self):
        if not self.ids:
            return []
        self.ensure_one()
        return string_to_list(self.field_blacklist)

    @api.multi
    def get_record_blacklist(self):
        if not self.ids:
            return []
        self.ensure_one()
        return string_to_list(
            self.record_blacklist,
            modifier=lambda x: self.env.ref(x).id)

    def get_conf(self, key=None):
        all_keys = {
            'xmlid_fields': self.get_xmlid_fields(),
            'xmlid_policy': self.xmlid_policy,
            'xmlid_table_name': self.xmlid_table_name,
            'model_context': self.get_model_context(),
            'field_blacklist': self.get_field_blacklist(),
            'record_blacklist': self.get_record_blacklist(),
        }
        return all_keys.get(key, all_keys)
