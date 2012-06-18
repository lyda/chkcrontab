#!/bin/sh

# code quality reports

# Lint
for f in chkcrontab chkcrontab_lib.py; do
  pylint --rcfile=.pylintrc $f
  /bin/echo -n "Completed '$f'.  Next..."
  read dummy
done

# Coverage
coverage run ./setup.py test
coverage html --include=chkcrontab,chkcrontab_lib.py
open htmlcov/index.html
