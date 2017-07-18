# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
from odoo import fields, models


class Company(models.Model):

    _inherit = 'res.company'

    aka = fields.Char()

    _sql_constraints = [
        ('aka_uniq', 'unique(aka)', 'Codename must be unique per Company!'),
    ]
