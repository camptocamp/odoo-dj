# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
import pprint
import re
from lxml import etree

from odoo import api, models


SPECIAL_FIELDS = [
    'create_date', 'create_uid', 'write_date',
    'write_uid', '__last_update', 'id',
    'display_name',
    # base.config.settings specific
    'rml_header', 'rml_header2', 'rml_header3'
]


class SettingsExporter(models.AbstractModel):
    _name = 'res.config.settings.exporter'

    @api.multi
    def _get_config_vals(self):
        IrModelData = self.env['ir.model.data']
        values = self.read()[0]

        for k in SPECIAL_FIELDS:
            if k in values.keys():
                del values[k]

        xmlids = []

        for k, v in values.iteritems():
            if v and self._fields[k].type == 'many2one':
                model = self._fields[k].comodel_name
                domain = [('model', '=', model),
                          ('res_id', '=', v[0])]
                # Find xmlid if it exists
                ext_id = IrModelData.search(domain, limit=1)
                if ext_id:
                    xmlid = ext_id.complete_name
                    values[k] = "XMLID%s" % len(xmlids)
                    xmlids.append(xmlid)
        return values, xmlids

    @api.multi
    def _get_formated_config_values(self):
        values, xmlids = self._get_config_vals()
        str_values = pprint.pformat(values)
        if xmlids:
            str_values = str_values.replace('{', '{{')
            str_values = str_values.replace('}', '}}')
            str_values = re.sub(
                r"'XMLID([0-9].*)'", r"ctx.env.ref('{\1}').id",
                str_values)
            str_values = str_values.format(*xmlids)
        return str_values

    @api.multi
    def _get_config_song(self):
        config_values = self._get_formated_config_values()
        # add indent of 8 for value dict
        config_values = '\n'.join(' ' * 8 + l for idx, l in
                                  enumerate(config_values.split('\n')))
        if self._name.split('.')[0] == 'base':
            comment = "Configure {}".format(self.display_name)
        else:
            comment = "{} settings".format(self.display_name)
        self.display_name
        song = ('@anthem.log\n'
                'def settings(ctx):\n'
                '    """ {}"""\n'
                '    ctx.env[\'{}\'].create(\n'
                '{}\n'
                '    ).execute()'
                ).format(comment, self._name, config_values)
        return song

    @api.multi
    def action_export_config(self):
        """ Open wizard that display the code nicely """
        code = self._get_config_song()
        xmlid = 'base_settings_exporter.action_wizard_settings_exporter'
        action_data = self.env.ref(xmlid).read()[0]
        action_data['context'] = {'code': code}
        return action_data

    @api.model
    def fields_view_get(self, view_id=None, view_type='form',
                        toolbar=False, submenu=False):
        result = super(SettingsExporter, self).fields_view_get(
            view_id=view_id, toolbar=toolbar, submenu=submenu)

        if view_type == 'form':
            eview = etree.fromstring(result['arch'])
            nodes = eview.xpath("//header/button[@name='execute']")
            if nodes:
                header = eview.xpath("//header")[0]
                button_export = etree.fromstring(
                    '<button string="Export Config"'
                    ' name="action_export_config" type="object"/>')
                header.insert(1, button_export)
            result['arch'] = etree.tostring(eview)

        return result


class ResConfigSettings(models.TransientModel):

    _name = 'res.config.settings'
    _inherit = ['res.config.settings', 'res.config.settings.exporter']
