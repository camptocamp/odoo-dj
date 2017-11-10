# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

# tnx to https://stackoverflow.com/questions/2028268/

import json
from pylint import epylint as lint


def run_pylint(filepath):
    """Run pylint on the given filepath and return json report."""
    cmd = '{} --output-format=json'.format(filepath)
    pylint_stdout, pylint_stderr = lint.py_run(cmd, return_std=True)
    out = pylint_stdout.read()
    if out:
        # something wrong to be linted
        return json.loads(out)
    return None
