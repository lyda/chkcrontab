==========
chkcrontab
==========
.. image:: https://secure.travis-ci.org/lyda/chkcrontab.png
   :target: https://secure.travis-ci.org/lyda/chkcrontab
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

The main site for this is on code.google.com with a backup site at
github. Use whichever is convenient, the maintainer will push
accepted patches to both.

* http://code.google.com/p/chkcrontab/
* http://github.com/lyda/chkcrontab/

TODO
====
* Look for duplicate entries. Puppet sometimes loads up crontabs
  with dups.
* Check for backticks. (why?)
* Make sure MAILTO and PATH are set (perhaps others?)

Credits
=======
- `Kevin Lyda`_: Who got burned one too many times by broken crontabs.

.. _`tox`: http://pypi.python.org/pypi/tox
.. _`coverage`: http://pypi.python.org/pypi/coverage
.. _`Travis`: http://travis-ci.org/#!/lyda/chkcrontab
.. _`Kevin Lyda`: https://github.com/lyda
