# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from . common import BaseCompilationCase, load_filecontent
import codecs
from lxml import etree

HTML = """
<div id="yo">
<h1>HTML here dude!</h1>
</div>
"""

XML = """
<odoo>

  <record model="res.company" id="base.main_company">
    <field name="aka">djc</field>
  </record>

</odoo>
"""

TXT = """
A bunch
of lines.
One after another.
"""
TXT_RAW = codecs.encode(TXT.encode('utf-8'), 'base64')

IMAGE_RAW = load_filecontent(
    'base_dj', 'tests/binaries/oca_logo.png', mode='rb')
IMAGE = codecs.encode(IMAGE_RAW, 'base64')
FILE_RAW = load_filecontent(
    'base_dj', 'tests/binaries/dummy.csv', mode='rb')
FILE = codecs.encode(FILE_RAW, 'base64')


class SpecialFieldsCase(BaseCompilationCase):
    """Test special fields handling.

    We consider "special fields" the ones that are of type `binary`, `html`
    or `text`. he latter works if specified via:
        `_dj_file_fields_types` or `_dj_file_fields_names`

    On export we:

    * check the content type
    * export the content as an external file (inside /binaries folder)
    * set the path of the file instead of the value

    On import we convert it back to the original field content.

    Note about path value:

    * it starts with `dj_path:` prefix
    * it's wrapped inside `<odoo><path></path></odoo>` tags
      as for some fields (like arch_db in views) there's a check
      to make sure it contains XML.
    """

    @classmethod
    def setUpClass(cls):
        super(SpecialFieldsCase, cls).setUpClass()
        fixture = 'fixture_comp_special_fields'
        cls._load_xml('base_dj', 'tests/fixtures/%s.xml' % fixture)
        cls.comp = cls.env.ref('base_dj.test_comp_special')
        cls.model = cls.env['dj.test.filefields']

    def test_burn_paths(self):
        self.model.create({
            'name': 'foo',
            'arch_db': XML,
            'some_html': HTML,
            'some_text': TXT,
            'some_image': IMAGE,
            'some_file': FILE,
        })
        tracks = self.comp.get_all_tracks()
        paths = sorted([x[0] for x in tracks])
        expected = [
            'DEV_README.rst',
            'data/binaries/__setup__.dj_test_filefields_foo__arch_db.xml',
            'data/binaries/__setup__.dj_test_filefields_foo__some_file.txt',
            'data/binaries/__setup__.dj_test_filefields_foo__some_html.html',
            'data/binaries/__setup__.dj_test_filefields_foo__some_image.png',
            # CSV are detected as plain text
            'data/binaries/__setup__.dj_test_filefields_foo__some_text.txt',
            'data/install/generated/dj_test/dj.test.filefields.csv',
            'songs/install/generated/__init__.py',
            'songs/install/generated/dj_test_special_fields.py'
        ]
        self.assertListEqual(paths, expected)

    def test_burn_contents(self):
        self.model.create({
            'name': 'foo',
            'arch_db': XML,
            'some_html': HTML,
            'some_text': TXT,
            'some_image': IMAGE,
            'some_file': FILE,
        })
        tracks = self.comp.get_all_tracks()
        contents = {}
        for path, content in tracks:
            if 'binaries' in path:
                contents[path.split('foo__')[-1]] = content
        self.assertXMLEqual(
            etree.fromstring(contents['arch_db.xml']),
            etree.fromstring(XML)
        )
        self.assertXMLEqual(
            etree.fromstring(contents['some_html.html']),
            etree.fromstring(HTML)
        )
        self.assertEqual(contents['some_text.txt'], TXT_RAW)
        self.assertEqual(contents['some_image.png'], IMAGE_RAW)
        self.assertEqual(contents['some_file.txt'], FILE_RAW)
