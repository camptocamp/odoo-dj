# -*- coding: utf-8 -*-
# Copyright  Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
# -- This file has been generated --

# pylint: disable=C,E

import anthem
from anthem.lyrics.loaders import load_csv


@anthem.log
def load_res_company(ctx):
    """ Import res.company from csv """
    path = 'install/generated/dj_test/comp1/res.company.csv'
    model = ctx.env['res.company'].with_context(tracking_disable=True)
    header_exclude = ['parent_id/id']
    load_csv(ctx, model, path, header_exclude=header_exclude)
    if header_exclude:
        load_csv(ctx, model, path)


@anthem.log
def load_res_users(ctx):
    """ Import res.users from csv """
    path = 'install/generated/dj_test/comp1/res.users.csv'
    model = ctx.env['res.users'].with_context(
        no_reset_password=True, tracking_disable=True)
    load_csv(ctx, model, path)


@anthem.log
def load_res_partner(ctx):
    """ Import res.partner from csv """
    path = 'install/generated/dj_test/comp1/res.partner.csv'
    model = ctx.env['res.partner'].with_context(tracking_disable=True)
    header_exclude = ['commercial_partner_id/id', 'parent_id/id']
    load_csv(ctx, model, path, header_exclude=header_exclude)
    if header_exclude:
        load_csv(ctx, model, path)


@anthem.log
def post(ctx):
    load_res_company(ctx)
    load_res_users(ctx)
    load_res_partner(ctx)
