==========
chkcrontab
==========
.. image:: https://gitlab.ie.suberic.net/kevin/chkcrontab/badges/master/build.svg
   :target: https://gitlab.ie.suberic.net/kevin/chkcrontab/commits/master
   :alt: Home build status

.. image:: https://gitlab.ie.suberic.net/kevin/chkcrontab/badges/master/coverage.svg
   :target: https://gitlab.ie.suberic.net/kevin/chkcrontab/commits/master
   :alt: Home coverage status

.. image:: https://travis-ci.org/lyda/chkcrontab.png?branch=master
   :target: https://travis-ci.org/lyda/chkcrontab
   :alt: Build status

Crontab linter
==============
chkcrontab is a script to check crontab files like those in
``/etc/cron.d`` and ``/etc/crontab``.  It tries to catch glaring
errors and warn on suspect lines in a crontab file.  Some valid
lines will generate warnings.  Certain silly yet valid crontab lines
will generate errors as well.

Run this by doing::

    chkcrontab crontab_file

Errors will cause a non-zero exit code.  Warnings alone will not.

To see sample output for a bad crontab, run the following::

  ./chkcrontab ./tests/test_crontab

See the ``./tests/test_crontab.disable`` crontab for how to disable
warnings and errors.

Output Description
~~~~~~~~~~~~~~~~~~

The output of ``chkcrontab`` is described on the `CheckCrontab`_
wiki page. A link to it appears in the output if there were any
warnings or errors. It also suggests ways to fix the reported
issues.

Contributions
=============
Contributions are welcome! Please add unit tests for new features
or bug fixes.  To run all the unit tests run ``./setup test``.
If you have `tox`_ installed, just run ``tox``.

You can review `coverage`_ of added tests by running
``coverage run setup.py test`` and then running
``coverage report -m``.

Note that tests are run on `Travis`_ for all supported python
versions whenever the tree on github is pushed to.

The packaged version is available via ``pip`` or ``easy_install``
as ``chkcrontab``. The project page is on `pypi`_:

The source code is available in the following locations:

* Gitlab: https://gitlab.com/lyda/chkcrontab
* Github: https://github.com/lyda/chkcrontab
* Bitbucket: https://bitbucket.org/lyda/chkcrontab/
* Sourceforge: https://sourceforge.net/p/chkcrontab

Pull requests on any of those platforms or emailed patches are fine.
Opening issues on gitlab or github is easiest, but I'll check any
of them.

Packaging
=========

For rpm distributions, ``./setup.py bdist --formats=rpm`` should make an
rpm but currently dies due to not finding the chkcrontab.1 man page.

For Debian distributions there's an additional tool that might work.

Dockerfile
==========

To use it with docker, just run
``docker run -it --rm -v "$PWD":/usr/src/myapp -w /usr/src/myapp numerea/chkcrontab:1.7 chkcrontab ./path/to/crontab``

TODO
====
* Look for duplicate entries. Puppet sometimes loads up crontabs
  with dups.
* Check for backticks. (why?)
* Make sure MAILTO and PATH are set (perhaps others?).
* Add tests for command line.
* Enable it to parse user crontabs: 
  https://github.com/lyda/chkcrontab/issues/12
* Make "acceptable filenames" a configurable thing:
  https://github.com/lyda/chkcrontab/issues/4
* Packaging: https://github.com/lyda/chkcrontab/issues/13

Credits
=======
- `Kevin Lyda`_: Who got burned one too many times by broken crontabs.

.. _`tox`: https://pypi.python.org/pypi/tox
.. _`coverage`: https://pypi.python.org/pypi/coverage
.. _`Travis`: https://travis-ci.org/lyda/chkcrontab
.. _`Kevin Lyda`: https://github.com/lyda
.. _`CheckCrontab`: http://goo.gl/7XS9q
.. _`pypi`: https://pypi.python.org/pypi/chkcrontab
