# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import odoo
import logging

logger = logging.getLogger(__name__)


logger.info('Patching `Selection.convert_to_export`')
odoo.fields.Selection.orig_convert_to_export = \
    odoo.fields.Selection.convert_to_export


def Selection__convert_to_export(self, value, record):
    """We want to export the real value of the field, not display value."""
    if not record.env.context.get('dj_export'):
        return self.orig_convert_to_export(value, record)
    return value if value else ''

# XXX: this bit is not used at all by `export_data`
# as m2m values are forced already to xmlid
# while o2m are forced to follow values.
# Not sure we don't need this somewhere else though.
logger.info('Patching `_RelationalMulti.convert_to_export`')
odoo.fields._RelationalMulti.orig_convert_to_export = \
    odoo.fields._RelationalMulti.convert_to_export


def _RelationalMulti__convert_to_export(self, value, record):
    """We want to export the xmldids, not display value."""
    if not record.env.context.get('dj_export'):
        return self.orig_convert_to_export(value, record)
    return ','.join([x._export_xml_id() for x in value])

odoo.fields._RelationalMulti.convert_to_export = \
    _RelationalMulti__convert_to_export
