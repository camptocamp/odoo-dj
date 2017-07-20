# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

{
    'name': 'Base DJ console',
    'summary': """
    Use the DJ console to create compilations w/ your favourite anthem songs.
    """,
    'version': 'version',
    'author': 'Camptocamp',
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
        'views/company.xml',
        'views/compilation.xml',
        'views/song.xml',
    ],
    'installable': True,
    'auto_install': False,
    "post_load": "patch_fields",
}
