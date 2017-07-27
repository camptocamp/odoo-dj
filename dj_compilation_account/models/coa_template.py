# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api

# TODO: move it to dj_compilation_account (?)


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    @api.multi
    def create_record_with_xmlid(self, company, template, model, vals):
        """Override to use company's `aka` code to discriminate by company."""
        # Create a record for the given model with the given vals and
        # also create an entry in ir_model_data to have an xmlid
        # for the newly created record
        # xmlid is the concatenation of company_id and template_xml_id
        ir_model_data = self.env['ir.model.data']
        template_xmlid = ir_model_data.search([
            ('model', '=', template._name), ('res_id', '=', template.id)])
        # START PATCH
        company_bit = company.aka or company.id
        new_xml_id = str(company_bit) + '_' + template_xmlid.name
        # END PATCH
        return ir_model_data._update(
            model, template_xmlid.module, vals,
            xml_id=new_xml_id, store=True,
            noupdate=True, mode='init', res_id=False)
