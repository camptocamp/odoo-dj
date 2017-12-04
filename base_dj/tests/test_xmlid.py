# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from . common import BaseCase


class XMLIDCase(BaseCase):

    @classmethod
    def setUpClass(cls):
        super(XMLIDCase, cls).setUpClass()
        # When testing w/ stock module installed
        # warehouse and location are created
        # and this triggers a parent computation that is broken
        # because here we don't have (and don't want) all the required setup.
        cls.company_model = cls.env['res.company'].with_context(
            defer_parent_store_computation=True)
        foo = cls.company_model.create({
            'name': 'Foo Inc.',
            'aka': 'foo',
        })
        cls.add_xmlid(foo, 'base_dj.test_company_foo')
        baz = cls.company_model.create({
            'name': 'Baz Ltd.',
            'aka': 'baz',
        })
        cls.add_xmlid(baz, 'base_dj.test_company_baz')

    def test_companies(self):
        # records created from setup maintain their own xmlid
        self.assertEqual(
            self.env.ref('base.main_company')._dj_export_xmlid(),
            'base.main_company',
        )
        self.assertEqual(
            self.env.ref('base_dj.test_company_foo')._dj_export_xmlid(),
            'base_dj.test_company_foo',
        )
        self.assertEqual(
            self.env.ref('base_dj.test_company_baz')._dj_export_xmlid(),
            'base_dj.test_company_baz',
        )
        # new records' xmlids are auto-generated matching our rules
        new_company = self.company_model.create({
            'name': 'ACME', 'aka': 'acme'})
        self.assertEqual(
            new_company._dj_export_xmlid(),
            # `company` prefix defined via default equalizer
            '__setup__.company_acme',
        )

    def test_xmlid_no_specific_rule_no_name_field(self):
        # new record
        rec = self.env['res.partner.bank'].create({'acc_number': '01234', })
        # no specific rule other than `__setup__` as prefix
        # and record ID as suffix (odoo's std)
        self.assertEqual(
            rec._dj_export_xmlid(),
            '__setup__.res_partner_bank_{}'.format(rec.id)
        )

    def test_xmlid_no_specific_rule_name_field(self):
        rec = self.env['res.bank'].create({'name': 'C2C Investments Ltd.', })
        # normalized name
        self.assertEqual(
            rec._dj_export_xmlid(),
            '__setup__.res_bank_c2c_investments_ltd'
        )

    def test_xmlid_with_specific_xmlid_fields(self):
        # new record
        rec = self.env['res.partner.bank'].create({'acc_number': '11234', })
        # pass new xmlids map
        fmap = {'res.partner.bank': ['acc_number', ]}
        self.assertEqual(
            rec.with_context(dj_xmlid_fields_map=fmap)._dj_export_xmlid(),
            '__setup__.res_partner_bank_11234'
        )

    def test_xmlid_with_specific_xmlid_fields_from_equalizer(self):
        # new record
        rec = self.env['res.partner.bank'].create({'acc_number': '20000', })
        self.env['dj.equalizer'].create({
            'model': 'res.partner.bank',
            'xmlid_fields': 'acc_number',
            'xmlid_table_name': 'bank_account',
        })
        self.assertEqual(
            rec._dj_export_xmlid(),
            '__setup__.bank_account_20000'
        )

    def test_xmlid_multicompany(self):
        # new record for the same company
        rec = self.env['res.partner.bank'].create({'acc_number': '56789', })
        # we pass `dj_multicompany` flag and we get company's aka as prefix
        self.assertEqual(
            rec.with_context(dj_multicompany=1)._dj_export_xmlid(),
            '__setup__.djc_res_partner_bank_{}'.format(rec.id)
        )
        # new record, different company
        rec = self.env['res.partner.bank'].create({
            'acc_number': '11111',
            'acc_type': 'bank',
            'company_id': self.env.ref('base_dj.test_company_foo').id,
        })
        self.assertEqual(
            rec.with_context(dj_multicompany=1)._dj_export_xmlid(),
            '__setup__.foo_res_partner_bank_{}'.format(rec.id)
        )
