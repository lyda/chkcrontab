==========
chkcrontab
==========

-----------------
Crontab lint tool
-----------------

:Author:         Kevin Lyda <lyda@google.com>
:Manual section: 1
:Manual group:   Utilities


Synopsis
--------
**chkcrontab** *file*

Description
-----------
The **chkcrontab** command provides a command line tool to check the
correctness of system crontab files like ``/etc/crontab`` or the
files in ``/etc/cron.d``.

The following check are run against the given crontab file.

* File name is a valid cron file name.
* Variable assignments do not have ``$``'s in right hand side.
* Confirms that ``@`` specifiers are valid.
* Confirms that users exist on the system (or NIS or LDAP).
* Validates the basic syntax of cron job lines.
* Validates that each time field is within limits.
* Checks that ranges and sequences are not used for the "day of
  week" and "month" fields.
* Reports any bare ``%`` in a command.


Bugs
----
Quite possibly. Report them via the issue tracker at the project
website:

http://code.google.com/p/chkcrontab/issues/list

See Also
--------
**lint** (1)

Resources
---------
Project website: http://code.google.com/p/chkcrontab

Copying
-------
Copyright (C) 2012 Kevin Lyda.
Licensed under the Apache License, Version 2.0
