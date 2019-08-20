# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import models, fields, api, _
from ...slugifier import slugify


class Genre(models.Model):
    """Pick your favourite music genre."""

    _name = 'dj.genre'
    _description = 'DJ Genre'

    name = fields.Char(required=True, help='Name will be normalized.')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', _('The name must be unique')),
    ]

    @api.model
    def create(self, vals):
        if vals.get('name'):
            vals['name'] = slugify(vals['name']).replace('-', '_')
        return super(Genre, self).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('name'):
            vals['name'] = slugify(vals['name']).replace('-', '_')
        return super(Genre, self).write(vals)
