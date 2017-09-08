# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import http
from odoo.http import request
import os
import mimetypes


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
        track = song.burn_track()
        if not track:
            return 'Sorry, nothing to view here.'
        path, content = track
        filename = os.path.basename(path)
        ctype = mimetypes.guess_type(filename)[0] or 'text/csv'
        headers = self._make_download_headers(content, filename, ctype)
        return request.make_response(content, headers=headers)

    @http.route(
        '/dj/download/compilation/<string:compilations>',
        type='http', auth="user", website=False)
    def download_compilation(self, compilation, **kwargs):
        mod_name = kwargs.get('dj_xmlid_module')
        xmlid_force = kwargs.get('dj_xmlid_force')
        filename, content = compilation.with_context(
            dj_xmlid_module=mod_name, dj_xmlid_force=xmlid_force).burn()
        headers = self._make_download_headers(
            content, filename, 'application/zip')
        return request.make_response(content, headers=headers)
