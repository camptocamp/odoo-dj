# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
from cStringIO import StringIO

import base64
import csv
import logging
import zipfile
import io

from odoo import models, fields, api
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class Sample(models.Model):
    _name = 'dj.sample'

    name = fields.Char(compute='_compute_sample_name')
    dj_id = fields.Many2one('dj', required=True)
    model_id = fields.Many2one('ir.model', required=True)
    csv_path = fields.Char()
    domain = fields.Char(default="[]")
    field_list = fields.Char(help="List of field to export separated by ','")
    xmlid_fields = fields.Char(help="List of field to use to generate unique"
                                    " xmlid separated by ','")


    @api.one
    @api.depends('model_id.model')
    def _compute_sample_name(self):
        self.name = (self.model_id.model or '').replace('.', '_')

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
        if 'company_id' in self.model_id.field_id.mapped('name'):
            field_names.append('company_id')
        export_data = items.export_data(field_names).get('datas',[])

        return self.from_data(field_names, export_data)



class DJ(models.Model):

    """Use discs to create songs from scratch and save it in compact format"""

    _name = 'dj'

    name = fields.Selection([])
    playlist = fields.One2many('dj.sample', 'dj_id')
    compact_disc = fields.Binary(
        help="Resulting Zip file with all songs and related files",
        attachment=True)
    album_title = fields.Char(default='out.zip')

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
        """ Return all csv generated from dj.samples """
        self.ensure_one()
        files = []
        for sample in self.playlist:
            files.append((
                sample.csv_path,
                sample.create_csv()
            ))
        return files

    @api.multi
    def get_beats(self):
        """ Return list of variable for Jinja

        Get name model and path of playlist

        To be inherited
        """
        return {'samples': self.playlist}

    @api.multi
    def play(self):
        """ Return a zip file containing all required files """
        self.check_company_codename()
        for rec in self:
            files = rec.get_all_tracks()
            in_mem_zip = io.BytesIO()
            with zipfile.ZipFile(in_mem_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                for filepath, data in files:
                    zf.writestr(filepath, data)
            in_mem_zip.seek(0)
            zip_file = base64.encodestring(in_mem_zip.read())
            rec.compact_disc = zip_file



