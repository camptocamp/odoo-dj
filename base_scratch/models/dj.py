# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
from cStringIO import StringIO

import base64
import csv
import logging

from odoo import models, fields, api
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class Sample(models.Model):
    _name = 'dj.sample'

    dj_id = fields.Many2one('dj', required=True)
    model_id = fields.Many2one('ir.model', required=True)
    csv_path = fields.Char()
    domain = fields.Char(default="[]")
    field_list = fields.Char(help="List of field to export separated by ','")
    xmlid_fields = fields.Char(help="List of field to use to generate unique"
                                    " xmlid separated by ','")


    @api.model
    def eval_domain(self):
        return safe_eval(self.domain) or []

    @api.model
    def from_data(self, fields, rows):
        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)

        writer.writerow([name.encode('utf-8') for name in fields])

        for data in rows:
            row = []
            for d in data:
                if isinstance(d, unicode):
                    try:
                        d = d.encode('utf-8')
                    except UnicodeError:
                        pass
                if d is False: d = None

                # Spreadsheet apps tend to detect formulas on leading =, + and -
                if type(d) is str and d.startswith(('=', '-', '+')):
                    d = "'" + d

                row.append(d)
            writer.writerow(row)

        fp.seek(0)
        data = fp.read()
        fp.close()
        return data

    @api.multi
    def create_csv(self):
        # TODO create xmlid starting with __setup__
        # XXX detect auto generated xmlids

        items = self.env[self.model_id.model].search(self.eval_domain())
        field_names = ['id']
        field_names.extend([f.strip() for f in self.field_list.split(',')])
        export_data = items.export_data(field_names).get('datas',[])

        return self.from_data(field_names, export_data)



class DJ(models.Model):

    """Use disks to create songs from scratch and save it in compact format"""

    _name = 'dj'

    name = fields.Selection([])
    playlist = fields.One2many('dj.sample', 'dj_id')
    compact_disk = fields.Binary(
        help="Resulting Zip file with all songs and related files",
        attachment=True)
    album_title = fields.Char()

    @api.model
    def check_company_codename(self):
        """ Check company short codenames have been setup in multi company
        We need those to create unique codenames
        """
        Company = self.env['res.company']
        company_num = Company.search_count([])
        if company_num == 1:
            return
        companies = Company.search([('aka', '=', False)])
        if companies:
            raise # TODO missing aka

    @api.multi
    def get_all_tracks(self):
        self.ensure_one()
        files = []
        for sample in self.playlist:
            files.append((
                sample.csv_path,
                sample.create_csv()
            ))
        return files

    @api.multi
    def play(self):
        """ Return a zip file containing all required files """
        self.check_company_codename()
        for rec in self:
            files = rec.get_all_tracks()

            # TODO zip all files inside a zip with correct paths
            zip_file = base64.encodestring(files[0][1])
            rec.compact_disk = zip_file



