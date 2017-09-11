# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import csv
import io
import zipfile
import time
import datetime
from cStringIO import StringIO
from contextlib import contextmanager

from odoo.addons.website.models.website import slugify


def create_zipfile(files):
    in_mem_zip = io.BytesIO()
    with zipfile.ZipFile(in_mem_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for filepath, data in files:
            # File "/usr/lib/python2.7/zipfile.py", line 1247, in writestr
            # TypeError: 'unicode' does not have the buffer interface
            if isinstance(data, unicode):
                data = data.encode('utf-8')
            # use info to keep date and set permissions
            info = zipfile.ZipInfo(
                filepath, date_time=time.localtime(time.time()))
            # set proper permissions
            info.external_attr = 0644 << 16L
            zf.writestr(info, data)
    in_mem_zip.seek(0)
    return in_mem_zip


def make_title(name, mode):
    dt = datetime.datetime.now().strftime('%Y%m%d_%H%M')
    return '{}_{}-{}.zip'.format(
        slugify(name).replace('-', '_'),
        mode, dt)


def csv_from_data(fields, rows):
    """Copied from std odoo export in controller."""
    fp = StringIO()
    writer = csv.writer(fp, quoting=csv.QUOTE_ALL)

    writer.writerow([name.encode('utf-8') for name in fields])

    for data in rows:
        row = []
        for i, col in enumerate(data):
            if isinstance(col, unicode):
                try:
                    col = col.encode('utf-8')
                except UnicodeError:
                    pass
            if col is False:
                col = None

            # ---- START CHANGE ----
            # Here we remove this feature as csv with negative values
            # are unimportable with an additional quote
            # ----------------------

            # # Spreadsheet apps
            # # tend to detect formulas on leading =, + and -
            # if type(col) is str and col.startswith(('=', '-', '+')):
            #     col = "'" + col
            # ----- END CHANGE -----

            row.append(col)
        writer.writerow(row)

    fp.seek(0)
    data = fp.read()
    fp.close()
    return data


@contextmanager
def force_company(env, company_id):
    user_company = env.user.company_id
    env.user.update({'company_id': company_id})
    try:
        yield
    finally:
        env.user.update({'company_id': user_company})
