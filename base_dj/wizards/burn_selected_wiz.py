# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models, fields


class BurnSelectedWiz(models.TransientModel):
    _name = 'dj.compilation.burn_selected.wiz'
    _description = 'DJ Burn selected compilation wizard'


    compilation_ids = fields.Many2many(
        'dj.compilation',
        string='Compilations to burn',
        required=True,
        default=lambda self: self.env.context.get('active_ids')
    )

    @api.multi
    def burn_them_all(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': '/dj/download/compilation/{}'.format(
                ','.join([str(x) for x in self.compilation_ids.ids])
            ),
        }
