# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
{
    'name': 'Base DJ console',
    'summary': """
    Use the DJ console to create compilations w/ your favourite anthem songs.
    """,
    'version': '12.0.1.0.0',
    'author': 'Camptocamp,Odoo Community Association (OCA)',
    'maintainer': 'Camptocamp',
    'website': 'https://github.com/camptocamp/odoo-dj',
    'license': 'AGPL-3',
    'category': 'songs',
    'depends': [
        'base',
    ],
    'external_dependencies': {
        'python': [
            'autopep8',
            'pylint',  # this one is just for tests indeed
            'unicodecsv',
        ]
    },
    'data': [
        'security/ir.model.access.csv',
        'data/equalizer.xml',
        'data/export_compilation.xml',
        'wizards/burn_wiz.xml',
        'wizards/burn_selected_wiz.xml',
        'wizards/load_compilation.xml',
        'views/company.xml',
        'views/compilation.xml',
        'views/song.xml',
        'views/equalizer.xml',
        'views/menuitems.xml',
        'views/info_templates.xml',
    ],
    'installable': True,
    'auto_install': False,
    'post_load': 'patch_fields',
}
