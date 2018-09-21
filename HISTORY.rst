.. :changelog:

.. Template:

.. 0.0.1 (2016-05-09)
.. ++++++++++++++++++

.. **Features and Improvements**

.. **Bugfixes**

.. **Build**

.. **Documentation**

Release History
---------------

latest (unreleased)
+++++++++++++++++++

**Features and Improvements**

* Provide better error message on xmlid update fail

**Bugfixes**

**Build**

* Fix warning : `ir.actions.act_window.create() includes unknown fields: key2`

**Documentation**

0.4.0 (2017-11-16)
++++++++++++++++++

**Features and Improvements**

* Test xmlids generation (closes #28, addr #51)
* Add tests and improvements for settings song (fixes #95, addr #51)
* Include own `slugify` to not depend on `website` module
* `.gitignore` now ignores setuptools shadow folders (.eggs etc)
* [imp] handle record and field blacklist via equalizer
* Add pylint check to tests
* Add base tests \o/ and autopep8 (fixes #98, addresses #51)
* Add base tests for song (addresses #51)

**Bugfixes**

Fix and test res.users load ctx (closes #89, addr #51)
Fix and test defer parent output (fixes #86, addr #51)
Fix equalizer behavior
Fix users/partner export: ignore fields and admin records (fixes #97)
Fix sanity check: ignore xmlid check for transient model (fixes #96)


0.3.1 (2017-10-16)
++++++++++++++++++

A lot of core stuff, not tracked yet... Sorry :)
