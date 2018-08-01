# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import fields, models


class TestMixin(object):

    # generate xmlids
    # this is needed if you want to load data tied to a test model via xid
    _test_setup_gen_xid = False
    _test_teardown_no_delete = False

    @classmethod
    def _test_setup_model(cls, env):
        """Initialize it."""
        cls._build_model(env.registry, env.cr)
        env.registry.setup_models(env.cr)
        ctx = dict(env.context, update_custom_fields=True)
        if cls._test_setup_gen_xid:
            ctx['module'] = cls._module
        env.registry.init_models(env.cr, [cls._name], ctx)

    @classmethod
    def _test_teardown_model(cls, env):
        """Deinitialize it."""
        if not getattr(cls, '_test_teardown_no_delete', False):
            del env.registry.models[cls._name]
        env.registry.setup_models(env.cr)


class TestDefaults(models.Model, TestMixin):
    _name = 'dj.test.defaults'

    partner_id = fields.Many2one(
        string='The partner',
        comodel_name='res.partner',
    )


class TestFileFields(models.Model, TestMixin):
    _name = 'dj.test.filefields'
    _test_setup_gen_xid = True

    @property
    def _dj_file_fields_names(self):
        # arch_db is automatically added here
        base = list(super(TestFileFields, self)._dj_file_fields_names)
        return base + ['some_text', ]

    name = fields.Char()
    some_html = fields.Html()
    some_text = fields.Text()
    arch_db = fields.Text()
    some_image = fields.Binary()
    some_file = fields.Binary()
