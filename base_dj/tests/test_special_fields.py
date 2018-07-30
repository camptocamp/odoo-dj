# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from . common import BaseCompilationCase, load_filecontent
from .fake_models import TestFileFields
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

    TEST_MODELS_KLASSES = [TestFileFields, ]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_test_models()
        fixture = 'fixture_comp_special_fields'
        cls._load_xml('base_dj', 'tests/fixtures/%s.xml' % fixture)
        cls.comp = cls.env.ref('base_dj.test_comp_special')
        cls.model = cls.env['dj.test.filefields']

    def setUp(self):
        super().setUp()

        # Patch _existing_xids because the std one uses sql query
        # which works only when transaction is committed.
        # We don't really want to commit, so, let's rely on `self.env.ref`
        def _existing_xids(self):
            res = {}
            modname = self._dj_xmlid_export_module()
            for rec in self:
                xid = '{}.{}'.format(modname, rec._dj_xmlid_export_name())
                xid_rec = self.env.ref(xid, raise_if_not_found=False)
                if xid_rec:
                    res[rec.id] = (modname, rec._dj_xmlid_export_name())
            return res

        self.model._patch_method('_existing_xids', _existing_xids)
        self.addCleanup(self.model._revert_method, '_existing_xids')

    @classmethod
    def tearDownClass(cls):
        cls._teardown_models()
        super().tearDownClass()

    def test_burn_paths(self):
        self.model.create({
            'name': 'foo',
            'arch_db': XML,
            'some_html': HTML,
            'some_text': TXT,
            'some_image': IMAGE,
            'some_file': FILE,
        })
        tracks = self.comp.get_all_tracks(include_core=False)
        paths = sorted([x[0] for x in tracks])
        base_path = (
            # by default they are place aside the csv files
            # in a `binaries` sub folder
            'install/generated/dj_test/special_fields/'
            'binaries/dj.test.filefields'
        )
        expected = [
            'DEV_README.rst',
            base_path + '/__setup__.dj_test_filefields_foo__arch_db.xml',
            base_path + '/__setup__.dj_test_filefields_foo__some_file.txt',
            base_path + '/__setup__.dj_test_filefields_foo__some_html.html',
            base_path + '/__setup__.dj_test_filefields_foo__some_image.png',
            # CSV are detected as plain text
            base_path + '/__setup__.dj_test_filefields_foo__some_text.txt',
            'install/generated/dj_test/special_fields/dj.test.filefields.csv',  # noqa
            'songs/install/__init__.py',
            'songs/install/generated/__init__.py',
            'songs/install/generated/dj_test/__init__.py',
            'songs/install/generated/dj_test/special_fields.py',
        ]
        self.assertListEqual(paths, expected)

    def test_burn_paths_custom(self):
        self.model.create({
            'name': 'foo',
            'arch_db': XML,
            'some_html': HTML,
            'some_text': TXT,
            'some_image': IMAGE,
            'some_file': FILE,
        })
        # customize binaries path on the song
        self.comp.song_ids[0].binaries_path = '{data_mode}/foo/{model}'
        tracks = self.comp.get_all_tracks(include_core=False)
        paths = sorted([x[0] for x in tracks])
        base_path = 'install/foo/dj.test.filefields'
        expected = [
            'DEV_README.rst',
            base_path + '/__setup__.dj_test_filefields_foo__arch_db.xml',
            base_path + '/__setup__.dj_test_filefields_foo__some_file.txt',
            base_path + '/__setup__.dj_test_filefields_foo__some_html.html',
            base_path + '/__setup__.dj_test_filefields_foo__some_image.png',
            # CSV are detected as plain text
            base_path + '/__setup__.dj_test_filefields_foo__some_text.txt',
            'install/generated/dj_test/special_fields/dj.test.filefields.csv',  # noqa
            'songs/install/__init__.py',
            'songs/install/generated/__init__.py',
            'songs/install/generated/dj_test/__init__.py',
            'songs/install/generated/dj_test/special_fields.py',
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
        tracks = self.comp.get_all_tracks(include_core=False)
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
