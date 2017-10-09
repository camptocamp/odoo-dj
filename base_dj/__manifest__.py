# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

{
    'name': 'Base DJ console',
    'summary': """
    Use the DJ console to create compilations w/ your favourite anthem songs.
    """,
    'version': '10.0.1.0.0',
    'author': 'Camptocamp,Odoo Community Association (OCA)',
    'maintainer': 'Camptocamp',
    'license': 'AGPL-3',
    'category': 'songs',
    'depends': [
        'base',
        'web_widget_domain_v11',
    ],
    'website': 'www.camptocamp.com',
    'data': [
        'security/ir.model.access.csv',
        'data/equalizer.xml',
        'data/export_compilation.xml',
        'wizards/burn_selected_wiz.xml',
        'wizards/load_compilation.xml',
        'views/company.xml',
        'views/compilation.xml',
        'views/song.xml',
        'views/equalizer.xml',
        'views/menuitems.xml',
    ],
    'installable': True,
    'auto_install': False,
    'post_load': 'patch_fields',
}
