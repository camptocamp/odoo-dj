# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import http
from odoo.http import request
import os


class DJ(http.Controller):
    """Controller for dj tools."""

    def _make_download_headers(self, data, filename, content_type):
        return [
            ('Content-Disposition', 'attachment; filename=%s' % filename),
            ('Content-Type', '%s; charset=utf-8' % content_type),
            ('Content-Length', "%d" % len(data)),
            ('Pragma', "no-cache"),
            ('Cache-Control',
             'must-revalidate, \
                post-check=0, \
                pre-check=0, \
                public'),
            ('Expires', "0"),
        ]

    @http.route(
        '/dj/download/song/<model("dj.song"):song>',
        type='http', auth="user", website=False)
    def download_song(self, song, **kwargs):
        path, content = song.make_csv()
        filename = os.path.basename(path)
        headers = self._make_download_headers(content, filename, 'text/csv')
        return request.make_response(content, headers=headers)

    @http.route(
        '/dj/download/compilation/<model("dj.compilation"):compilation>',
        type='http', auth="user", website=False)
    def download_compilation(self, compilation, **kwargs):
        filename, content = compilation.burn()
        headers = self._make_download_headers(
            content, filename, 'application/zip')
        return request.make_response(content, headers=headers)
