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

    def _create_partner_bank(self, **vals):
        partner = self.env['res.partner'].search([
            ('is_company', '=', True)], limit=1)
        values = {
            'partner_id': partner.id,
        }
        values.update(vals)
        return self.env['res.partner.bank'].create(values)


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
        rec = self._create_partner_bank(acc_number='01234')
        # no specific rule other than `__setup__` as prefix
        # and record ID as suffix (odoo's std)
        # odoo generates xids using an hash at the end, like:
        # `__setup__.res_partner_bank_4_93b36cf5``
        self.assertRegexpMatches(
            rec._dj_export_xmlid(),
            '__setup__.res_partner_bank_%d_[0-9a-f]{8}' % rec.id
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
        rec = self._create_partner_bank(acc_number='11234')
        # pass new xmlids map
        fmap = {'res.partner.bank': ['acc_number', ]}
        self.assertEqual(
            rec.with_context(dj_xmlid_fields_map=fmap)._dj_export_xmlid(),
            '__setup__.res_partner_bank_11234'
        )

    def test_xmlid_with_specific_xmlid_fields_related(self):
        # new record
        rec = self._create_partner_bank(acc_number='30000')
        # pass new xmlids map
        fmap = {'res.partner.bank': ['acc_number', 'company_id.name']}
        self.assertEqual(
            rec.with_context(dj_xmlid_fields_map=fmap)._dj_export_xmlid(),
            '__setup__.res_partner_bank_30000_yourcompany'
        )

    def test_xmlid_with_specific_xmlid_fields_from_equalizer(self):
        # new record
        rec = self._create_partner_bank(acc_number='20000')
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
        rec = self._create_partner_bank(acc_number='56789')
        # we pass `dj_multicompany` flag and we get company's aka as prefix
        self.assertRegexpMatches(
            rec.with_context(dj_multicompany=1)._dj_export_xmlid(),
            '__setup__.djc_res_partner_bank_%d_[0-9a-f]{8}' % rec.id
        )
        # new record, different company
        rec = self._create_partner_bank(
            acc_number='11111',
            acc_type='bank',
            company_id=self.env.ref('base_dj.test_company_foo').id,
        )
        self.assertRegexpMatches(
            rec.with_context(dj_multicompany=1)._dj_export_xmlid(),
            '__setup__.foo_res_partner_bank_%d_[0-9a-f]{8}' % rec.id
        )

    def test_xmlid_hash_policy(self):
        self.env['dj.equalizer'].create({
            'model': 'res.partner.bank',
            'xmlid_fields': 'acc_number',
            'xmlid_policy': 'hash',
        })
        rec = self._create_partner_bank(acc_number='56789')
        # xmlid built w/ hash of `(acc_number, )` tuple
        hashed = self.env['res.partner.bank']._hash_them((rec.acc_number, ))
        self.assertEqual(
            rec._dj_export_xmlid(),
            '__setup__.res_partner_bank_{}'.format(hashed)
        )

    def test_xmlid_force_no_replace(self):
        rec = self.env.ref('base.main_company')
        ctx = {
            'dj_xmlid_module': '__setup__',
            'dj_xmlid_force': True,
        }
        # try to force xid for base.* -> no luck, we get the original xid
        self.assertEqual(
            rec.with_context(**ctx)._dj_export_xmlid(),
            'base.main_company',
        )
        # same for `__sample__`
        ctx = {
            'dj_xmlid_module': '__sample__',
            'dj_xmlid_force': True,
        }
        self.assertEqual(
            rec.with_context(**ctx)._dj_export_xmlid(),
            'base.main_company',
        )

    def test_xmlid_force_replace_stored(self):
        rec = self.company_model.create({
            'name': 'Replace rec',
            'aka': 'rok',
        })
        self.add_xmlid(rec, '__test__.company_rok')
        self.assertTrue(self.env.ref('__test__.company_rok'))
        ctx = {
            'dj_xmlid_module': '__sample__',
            'dj_xmlid_force': True,
        }
        # force xid for overridable xid module name ('__test__') works fine
        self.assertEqual(
            rec.with_context(**ctx)._dj_export_xmlid(),
            '__sample__.company_rok',
        )
        # and new xid is stored
        self.assertTrue(self.env.ref('__sample__.company_rok'))

    def test_xmlid_force_replace_no_stored(self):
        # you can generate one shot xids and not store them
        # so you don't pollute your db
        rec = self.company_model.create({
            'name': 'Replace rec',
            'aka': 'rok',
        })
        self.add_xmlid(rec, '__test__.company_rok')
        self.assertTrue(self.env.ref('__test__.company_rok'))
        ctx = {
            'dj_xmlid_module': '__sample__',
            'dj_xmlid_force': True,
            'dj_xmlid_skip_create': True,
        }
        self.assertEqual(
            rec.with_context(**ctx)._dj_export_xmlid(),
            '__sample__.company_rok',
        )
        # new xid is NOT stored
        with self.assertRaises(ValueError) as err:
            self.env.ref('__sample__.company_rok')
        self.assertEqual(
            str(err.exception),
            'External ID not found in the system: __sample__.company_rok'
        )
