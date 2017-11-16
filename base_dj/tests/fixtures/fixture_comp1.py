# -*- coding: utf-8 -*-
# Copyright  Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
# -- This file has been generated --

# pylint: disable=C,E

import anthem
from ...common import load_csv


@anthem.log
def load_res_company(ctx):
    """ Import res.company from csv """
    model = ctx.env['res.company'].with_context({'tracking_disable': 1})
    header_exclude = [u'parent_id/id']
    load_csv(ctx, 'data/install/generated/dj_test/res.company.csv',
             model, header_exclude=header_exclude)
    if header_exclude:
        load_csv(ctx, 'data/install/generated/dj_test/res.company.csv',
                 model, header=['id', ] + header_exclude)


@anthem.log
def load_res_users(ctx):
    """ Import res.users from csv """
    model = ctx.env['res.users'].with_context(
        {'no_reset_password': True, 'tracking_disable': 1})
    load_csv(ctx, 'data/install/generated/dj_test/res.users.csv', model)


@anthem.log
def load_res_partner(ctx):
    """ Import res.partner from csv """
    model = ctx.env['res.partner'].with_context({'tracking_disable': 1})
    header_exclude = [u'commercial_partner_id/id', u'parent_id/id']
    load_csv(ctx, 'data/install/generated/dj_test/res.partner.csv',
             model, header_exclude=header_exclude)
    if header_exclude:
        load_csv(ctx, 'data/install/generated/dj_test/res.partner.csv',
                 model, header=['id', ] + header_exclude)


@anthem.log
def main(ctx):
    load_res_company(ctx)
    load_res_users(ctx)
    load_res_partner(ctx)
