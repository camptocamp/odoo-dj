# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import csv
from cStringIO import StringIO
from contextlib import contextmanager


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
