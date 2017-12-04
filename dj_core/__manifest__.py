# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

{
    'name': 'DJ Core compilations and configurations',
    'summary': "Basic configurations and records for all compilations",
    'version': '11.0.1.0.0',
    'author': 'Camptocamp,Odoo Community Association (OCA)',
    'maintainer': 'Camptocamp',
    'website': 'https://github.com/camptocamp/odoo-dj',
    'license': 'AGPL-3',
    'category': 'songs',
    'depends': ['base_dj', ],
    'data': [
        'data/dj.xml',
        'data/settings_song_v11.xml',
        'data/defaults_song_v11.xml',
    ],
    'installable': True,
    'auto_install': False,
}
