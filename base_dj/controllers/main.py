# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import http
from odoo.http import request
import os
import mimetypes
from ..utils import string_to_list


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
        path, content = track[0]
        filename = os.path.basename(path)
        ctype = mimetypes.guess_type(filename)[0] or 'text/csv'
        headers = self._make_download_headers(content, filename, ctype)
        return request.make_response(content, headers=headers)

    @http.route(
        '/dj/download/compilation/<string:compilation_ids>',
        type='http', auth="user", website=False)
    def download_compilation(self, compilation_ids, **kwargs):
        """Burn one or more compilations at once.

        `compilations` string can be an ID or a list of IDs separated by comma.
        """
        ids = string_to_list(compilation_ids, modifier=int)
        records = request.env['dj.compilation'].browse(ids)
        burn_options = (
            'dj_xmlid_module',
            'dj_xmlid_force',
            'dj_xmlid_skip_create'
        )
        ctx = {k: kwargs.get(k) for k in burn_options}
        filename, content = records.with_context(**ctx).burn()
        headers = self._make_download_headers(
            content, filename, 'application/zip')
        return request.make_response(content, headers=headers)
