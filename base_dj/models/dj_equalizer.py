# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import models, fields, api


class EqualizerXMLID(models.Model):
    """Hold models' configuration to generate xmlid."""

    _name = 'dj.equalizer.xmlid'

    model = fields.Char()
    xmlid_fields = fields.Char()

    @api.multi
    def get_xmlid_fields(self):
        self.ensure_one()
        return [x.strip() for x in self.xmlid_fields.split(',')
                if x.strip()]
