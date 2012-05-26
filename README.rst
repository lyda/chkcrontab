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

Unit tests are run on `Travis`_ for all supported python versions.

The main site for this is on code.google.com with a backup site at
github. Use whichever is convenient, the maintainer will push
accepted patches to both.

* http://code.google.com/p/chkcrontab/
* http://github.com/lyda/chkcrontab/

.. _`Travis`: http://travis-ci.org/
