# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from psycopg2 import IntegrityError
from odoo import api, models, tools, _
from odoo.exceptions import ValidationError
import io
import os
import codecs
import logging
import mimetypes
import hashlib
import uuid

from ..utils import is_xml, to_str, is_string, follow_record_field
from ..slugifier import slugify

ODOO_DATA_PATH = os.getenv('ODOO_DATA_PATH', '').rstrip('/')
_logger = logging.getLogger(__file__)


def encode64(content):
    return codecs.encode(content, 'base64')


def decode64(content):
    return codecs.decode(content, 'base64')


class Base(models.AbstractModel):

    _inherit = 'base'

    @staticmethod
    def _hash_them(atuple):
        """Return always the same hashed string for given tuple."""
        # TODO: get a shorter but still unique hash
        # Maybe using `hashids` lib?
        return hashlib.md5(str(atuple).encode()).hexdigest()

    def _dj_xmlid_export_module(self):
        """Customize module name for dj compilation.

        By default is `__setup__` but you can force it via
        `dj_xmlid_module` context var.
        """
        return self.env.context.get('dj_xmlid_module') or '__setup__'

    @tools.ormcache('self', 'key')
    def _dj_global_config(self, key=None):
        """Retrieve default global config for xmlid fields."""
        config = self.env['dj.equalizer'].search([
            ('model', '=', self._name),
        ], limit=1)
        return config.get_conf(key)

    @tools.ormcache('self')
    def _dj_xmlid_export_name(self):
        """Customize xmlid name for dj compilation.

        You can specify field names by model name
        into context variable `dj_xmlid_fields_map`
        to be used for xmlid generation.
        Strings will be normalized.
        """
        name = [
            self._table, str(self.id),
            uuid.uuid4().hex[:8],
        ]  # std odoo default
        mapping = self.env.context.get('dj_xmlid_fields_map') or {}
        global_config = self._dj_global_config()
        xmlid_fields = (mapping.get(self._name, []) or
                        global_config.get('xmlid_fields', []))
        if not xmlid_fields and 'name' in self:
            # No specific configuration: we assume we can use name as default
            xmlid_fields.append('name')
        if xmlid_fields:
            name = [self._table, ]
            if global_config.get('xmlid_table_name'):
                name = [global_config['xmlid_table_name'], ]
            xmlid_fields_name = []
            for key in xmlid_fields:
                if '.' in key:
                    val = follow_record_field(self, key)
                elif self[key]:
                    val = self[key]
                else:
                    continue
                value = to_str(val, safe=True)
                if isinstance(value, str):
                    value = slugify(value).replace('-', '_')
                elif isinstance(value, models.BaseModel):
                    value = slugify(value.display_name).replace('-', '_')
                elif isinstance(value, (int, float)):
                    value = str(value)
                xmlid_fields_name.append(value)
            if global_config.get('xmlid_policy') == 'hash':
                # sometime this is the only way to get unique xmlids
                # (ir.default for instance).
                name.append(self._hash_them(tuple(xmlid_fields_name)))
            else:
                name.extend(xmlid_fields_name)
        if (self.env.context.get('dj_multicompany') and
                'company_id' in self and self.company_id.aka):
            # discriminate by company `aka` code
            name.insert(0, self.company_id.normalized_aka())
        return '_'.join(name)

    def _dj_export_xmlid(self):
        """Shortcut to force dj xmlid generation on 1 record."""
        self.ensure_one()
        res = self.with_context(dj_export=1)._BaseModel__ensure_xml_id()
        # we get a generator w/ tuple(record, xid)
        return tuple(res)[0][1]

    _dj_replaceable_modnames = (
        '__sample__', '__setup__', '__test__',
        '__import__', '__export__',
    )

    def _existing_xids(self):
        """Retrieve existing XIDs (and make testing possible).

        This method - not surprisingly - is not in odoo core.
        The piece of code here is inside the biiiig `__ensure_xml_id` method
        .
        This makes impossible to test XIDs generation precisely
        as the XIDs are not actually committed so the query won't return XIDs
        and when you call it twice it gets buggy:

        the `copy_from` will find them and raise a constrain error
        for duplicated keys.

        So, here we keep the original code, in tests we mock this
        to retrieve XIDs via `env.ref`.
        """
        query = """
            SELECT res_id, module, name
            FROM ir_model_data
            WHERE model = %s AND res_id in %s
        """
        cr = self.env.cr
        cr.execute(query, (self._name, tuple(self.ids)))
        return {
            res_id: (module, name)
            for res_id, module, name in cr.fetchall()
        }

    def _BaseModel__ensure_xml_id(self, skip=False):
        """Customize xmlid creation.

        Barely copied from `odoo.models` and hacked a bit.
        """
        if not self.env.context.get('dj_export'):
            return super()._BaseModel__ensure_xml_id()

        if skip:
            return ((record, None) for record in self)

        if not self:
            return iter([])

        if not self._is_an_ordinary_table():
            raise Exception(
                "You can not export the column ID of model %s, because the "
                "table %s is not an ordinary table."
                % (self._name, self._table))

        modname = self._dj_xmlid_export_module()

        xids = self._existing_xids()

        def to_xid(record_id):
            (module, name) = xids[record_id]
            return ('%s.%s' % (module, name)) if module else name

        def make_xid(r):
            # call `_dj_xmlid_export_name` and keep the context
            # which is very important for xid policy
            return r.with_context(self.env.context)._dj_xmlid_export_name()

        def is_missing(r):
            if not self.env.context.get('dj_xmlid_force'):
                return r.id not in xids
            # in case we are re-generating xids
            # replace only xids w/ replaceable mod names
            xid_modname = xids.get(r.id, ('', ''))[0]
            replaceable = xid_modname in self._dj_replaceable_modnames
            return (
                not xid_modname or replaceable and
                to_xid(r.id) != '{}.{}'.format(modname, make_xid(r))
            )

        # create missing xml ids
        missing = self.filtered(lambda r: is_missing(r))

        if not missing:
            return (
                (record, to_xid(record.id))
                for record in self
            )
        xids.update(
            (r.id, (modname, r._dj_xmlid_export_name())) for r in missing
        )
        # you can generate one shot xids and not store them
        # so you don't pollute your db and maybe fix some csv
        if not self.env.context.get('dj_xmlid_skip_create'):
            fields = ['module', 'model', 'name', 'res_id']
            try:
                self.env.cr.copy_from(io.StringIO(
                    u'\n'.join(
                        u"%s\t%s\t%s\t%d" % (
                            modname,
                            record._name,
                            xids[record.id][1],
                            record.id,
                        )
                        for record in missing
                    )),
                    table='ir_model_data',
                    columns=fields,
                )
            except IntegrityError:
                raise ValidationError(_(
                    "Writing xmlids for %s failed."
                    " Probably your xmlids aren't unique."
                    " Ids in the query: %s"
                ) % (self._name, missing.ids))
            self.env['ir.model.data'].invalidate_cache(fnames=fields)
        return (
            (record, to_xid(record.id))
            for record in self
        )

    def _BaseModel__export_xml_id(self):
        # OLD method used until this change
        # https://github.com/odoo/odoo/pull/22493
        # The new implementation is much more eficient.
        _logger.warn(
            'DEPRECATED: `__export_xml_id` has been removed. '
            'You should upgrade your odoo code base to this commit: '
            '46ce6c0144694da05b9313182f706e2aa0ffaa4b'
        )
        return super()._BaseModel__export_xml_id()

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        """Handle special fields value for dj export."""
        res = super(Base, self).read(fields=fields, load=load)
        if (not self.env.context.get('dj_export') or
                self.env.context.get('dj_skip_file_handling')):
            return res
        self._dj_handle_special_fields_read(res, _fields=fields)
        return res

    def _dj_handle_special_fields_read(self, records, _fields=None):
        if self.env.context.get('dj_read_skip_special_fields'):
            return
        if not records:
            return
        if _fields is None:
            _fields = list(records[0].keys())
        for fname, info in self._dj_special_fields(_fields):
            self._dj_handle_file_field_read(fname, info, records)

    # you can customized this per-model
    _dj_file_fields_types = ('html', 'binary', )
    _dj_file_fields_names = ('arch_db', )
    _dj_path_prefix = 'dj_path:'

    def _dj_special_fields(self, _fields=None):
        """Retrieve valid special fields' names for current export."""
        # In export mode we can have all model's fields here
        # BUT we don't want to handle file fields
        # if they are not requested for export.
        # This make sure that if we export a model in more than one compilation
        # we won't have duplicated files if not needed.
        whitelist = []
        if self.env.context.get('dj_export'):
            whitelist = self.env.context.get('dj_export_model_fields', [])
        res = []
        fields_info = self.fields_get(_fields)
        for fname, info in fields_info.items():
            if whitelist and fname not in whitelist:
                continue
            if self._dj_is_file_field(fname, info):
                res.append((fname, info))
        return res

    def _dj_is_file_field(self, fname, info):
        return (info['type'] in self._dj_file_fields_types or
                fname in self._dj_file_fields_names)

    def _dj_handle_file_field_read(self, fname, info, records):
        for rec in records:
            ob = self.browse(rec['id'])
            self.invalidate_cache([fname])
            if rec[fname]:
                rec[fname] = self._dj_file_to_path(ob, fname, info)

    def _dj_file_to_path(self, rec, fname, info=None, bare_path=False):
        info = info or self.fields_get([fname])[fname]
        xmlid = rec._dj_export_xmlid()
        path = '{prefix}{binaries_path}/{xmlid}__{fname}'
        bin_path = self.env.context.get('dj_export_binaries_path', 'binaries')
        export_lang = self.env.context.get('dj_export_lang', '')
        if export_lang:
            path += '_{lang}'
        path += '.{ext}'
        ext, _ = self._dj_guess_filetype(fname, rec, info=info)
        res = path.format(
            prefix=self._dj_path_prefix if not bare_path else '',
            binaries_path=bin_path,
            xmlid=xmlid, fname=fname,
            lang=export_lang, ext=ext)
        if fname == 'arch_db' and not bare_path:
            return '<odoo><path>' + res + '</path></odoo>'
        return res

    def _dj_guess_filetype(self, fname, record, info=None):
        record = record.with_context(dj_skip_file_handling=True)
        content = record[fname]
        if fname == 'arch_db':
            return 'xml', content
        info = info or self.fields_get([fname])[fname]
        if info['type'] == 'html':
            return 'html', content
        # guess filename from mimetype
        if is_xml(content):
            return 'xml', content
        if info['type'] == 'binary':
            content = decode64(content)
        elif info['type'] == 'text':
            content = encode64(content.encode('utf-8'))
        mime = tools.mimetypes.guess_mimetype(content)
        if mime:
            if mime == 'text/plain':
                # TODO: any better option?
                # `guess_extension` works very randomly here.
                # Let's stick to txt for now.
                ext = 'txt'
            else:
                # remove dot
                ext = mimetypes.guess_extension(mime)
                if ext:
                    ext = ext[1:]
                else:
                    # lookup for a default fallback
                    ext = self._dj_default_mimetype_ext_mapping.get(
                        mime, 'unknown')
            # HACK: even w/ libmagic installed, for JPGs we get randomly:
            # `jpe`, `jpg`, `jpeg`, even if we use `strict=True`.
            # We MUST have always the same one
            # otherwise on each export we get different results and
            # more image files.
            if ext in ('jpe', 'jpeg'):
                ext = 'jpg'
            return ext, content
        return 'unknown', content

    _dj_default_mimetype_ext_mapping = {
        'image/x-icon': 'ico'
    }

    def _dj_file_content_to_fs(self, fname, record, info=None):
        """Convert values to file system value.

        Called by `_handle_special_fields` when song's data is prepared.
        """
        _, content = self._dj_guess_filetype(fname, record)
        return content

    @api.multi
    def write(self, vals):
        self._dj_handle_special_fields_write(vals)
        return super(Base, self).write(vals)

    def _dj_handle_special_fields_write(self, vals):
        if not vals:
            return
        for fname, info in self._dj_special_fields(list(vals.keys())):
            if vals[fname]:
                self._dj_handle_file_field_write(fname, info, vals)

    def _dj_handle_file_field_write(self, fname, info, vals):
        self.invalidate_cache([fname])
        vals[fname] = self._dj_path_to_file(fname, info, vals[fname])

    def _dj_path_to_file(self, fname, info, path):
        # special case: xml validation is done for fields like `arch_db`
        # so we need to wrap/unwrap w/ <odoo/> tag
        if not is_string(path):
            return path
        path = to_str(path)
        path = path.replace('<odoo><path>', '').replace('</path></odoo>', '')
        if not path.startswith(self._dj_path_prefix):
            return path
        path = path[len(self._dj_path_prefix):]
        base_path = ODOO_DATA_PATH
        abs_path = os.path.join(base_path, path)
        read_mode = 'r'
        if info['type'] == 'binary':
            read_mode = 'rb'
        with open(abs_path, read_mode) as ff:
            content = ff.read()
            if info['type'] == 'binary':
                content = encode64(content)
            return content

    @api.model
    def create(self, vals):
        self._dj_handle_special_fields_write(vals)
        return super(Base, self).create(vals)
