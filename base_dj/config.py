# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import models, _

SPECIAL_FIELDS = [
    'display_name',
    '__last_update',
    'parent_left',
    'parent_right',
    # TODO: retrieve from inherited schema
    'message_ids',
    'message_follower_ids',
    'message_follower',
    'message_last_post',
    'message_unread',
    'message_unread_counter',
    'message_needaction_counter',
    'website_message_ids',
] + models.MAGIC_COLUMNS

ADDONS_BLACKLIST = (
    # useless to track these modules amongst installed addons
    # TODO: anything else to ignore?
    'base',
    'base_setup',
    'base_action_rule',
    'base_import',
    'board',
    'bus',
    'calendar',
    'grid',
    'maintenance',
    'report',
    'resource',
    'web',
    'web_calendar',
    'web_editor',
    'web_enterprise',
    'web_gantt',
    'web_kanban',
    'web_kanban_gauge',
    'web_mobile',
    'web_planner',
    'web_settings_dashboard',
    'web_tour',
)
ADDONS_NAME_DOMAIN = '("name", "not in", (%s))' % \
    ','.join(["'%s'" % x for x in ADDONS_BLACKLIST])

# TODO: move this to independent records
# then we can filter particular song types by genre
SONG_TYPES = {
    'settings': {
        'name': _('Config settings'),
        'prefix': '',
        'sequence': 0,
        'defaults': {
            'only_config': True,
            'template_path': 'base_dj:discs/song_settings.tmpl',
            'has_records': False,
        },
    },
    'load_csv': {
        'name': _('Load CSV'),
        'prefix': 'load_',
        'sequence': 10,
        'defaults': {
            'only_config': False,
            'template_path': 'base_dj:discs/song.tmpl',
        },
    },
    # TODO
    # switch automatically to `load_csv_heavy
    # when this amount of records is reached
    # HEAVY_IMPORT_THRESHOLD = 1000
    'load_csv_defer_parent': {
        'name': _('Load CSV defer parent computation'),
        'prefix': 'load_',
        'sequence': 20,
        'defaults': {
            'only_config': False,
            'template_path': 'base_dj:discs/song_defer_parent.tmpl',
        }
    },
    'compute_parent': {
        # TODO: this song type is to be used under the hood
        # by `_add_shadow_song_compute_parent`.
        # We cannot hide it because otherwise the `song_type` selection field
        # will complain about not having this option enabled.
        # ATM we live with this. As soon as we move to `song.type` model
        # and `song_type` to a m2o `song_type_id`
        # we can make this type inactive and search for it by reference.
        'name': _('Parent computation (DO NOT USE THIS)'),
        'prefix': 'load_',
        'suffix': '_compute_parent',
        'sequence': 20,
        'defaults': {
            'only_config': False,
            'template_path': 'base_dj:discs/song_compute_parent.tmpl',
        }
    },
    'generate_xmlids': {
        'name': _('Generate xmlids (for existing records)'),
        'prefix': 'add_xmlid_to_existing_',
        'sequence': 30,
        'defaults': {
            'only_config': True,
            'template_path': 'base_dj:discs/song_add_xmlids.tmpl',
            'has_records': False,
        },
    },
    'scratch_installed_addons': {
        'name': _('List installed addons'),
        'prefix': '',
        'sequence': 40,
        'defaults': {
            'only_config': True,
            'template_path': 'base_dj:discs/song_addons.tmpl',
            'model_id': 'xmlid:base.model_ir_module_module',
            'domain': '[("state", "=", "installed"), %s]' % ADDONS_NAME_DOMAIN,
            'has_records': True,
        },
    },
}

DEFAULT_PYTHON_CODE = """# Available variable:
#  - env: Odoo Environement
# You have to return a recordset named `records`.
# records = env[model].search([])
"""
