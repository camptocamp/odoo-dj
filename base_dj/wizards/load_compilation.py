# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import models, fields, api, exceptions, _
import zipfile
import os
import csv
import codecs
from io import StringIO


def csv_unireader(f, encoding="utf-8", **fmtparams):
    data = csv.reader(
        codecs.iterencode(codecs.iterdecode(f, encoding), "utf-8"), **fmtparams
    )
    for row in data:
        yield [e.decode("utf-8") for e in row]


def read_csv(data, dialect='excel', encoding='utf-8', **fmtparams):
    rows = csv_unireader(data, encoding=encoding, **fmtparams)
    header = next(rows)
    return header, list(rows)


# TODO: fix it or trash it
class LoadCompilation(models.TransientModel):
    """Import compilations."""

    _name = 'dj.load.compilation.wiz'
    _description = 'DJ Load selected compilation wizard'

    name = fields.Char()
    zip_file = fields.Binary(
        required=True,
    )

    def _get_model_from_filename(self, orig):
        fname, ext = os.path.splitext(os.path.basename(orig))
        return fname.split('-')[-1]

    def read_csvs(self):
        res = {}
        zipdata = StringIO()
        zipdata.write(self.zip_file.decode('base64'))
        with zipfile.ZipFile(zipdata) as zf:
            for filename in zf.namelist():
                if filename.endswith('.csv'):
                    model_name = self._get_model_from_filename(filename)
                    # read the file
                    with zf.open(filename) as of:
                        res[model_name] = of.readlines()
        return res

    _dj_model_load_order = (
        'dj.genre', 'dj.compilation', 'dj.song', 'dj.song.dependency'
    )

    @api.multi
    def action_load(self):
        self.ensure_one()
        res = {}
        files = self.read_csvs()
        for model_name in self._dj_model_load_order:
            if model_name not in files:
                raise exceptions.UserError(
                    _('%s csv file missing!') % model_name)
            header, rows = read_csv(files[model_name])
            res[model_name] = self.env[model_name].load(header, rows)
        comp_id = res['dj.compilation']['ids'][0]
        if self.name:
            self.env['dj.compilation'].browse(comp_id).name = self.name
        action = self.env.ref('base_dj.action_dj_compilation').copy_data()[0]
        action['res_id'] = comp_id
        return action
