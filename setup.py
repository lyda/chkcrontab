#!/usr/bin/env python
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Installer for chkcrontab.

This installs the chkcrontab command and the crontab.check module.
"""

import os
import sys
from distutils import log
from distutils.core import setup
from distutils.core import Command
if sys.version_info < (2, 7):
  import unittest2 as unittest
else:
  import unittest

BASE_DIR = os.path.dirname(globals().get('__file__', os.getcwd()))


class TestCommand(Command):
  description = 'Runs all available tests.'
  user_options = [ ]

  def initialize_options(self):
    pass

  def finalize_options(self):
    pass

  def run(self):
    test_dir = os.path.join(BASE_DIR, 'tests')

    tests = unittest.TestLoader().discover(test_dir)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(tests)
    if not result.wasSuccessful():
      sys.exit(1)

class CleanCommand(Command):
  description = 'Remove all generated files.'
  user_options = [ ]

  def initialize_options(self):
    pass

  def finalize_options(self):
    pass

  def run(self):
    # Configure for this project.
    suffixes2del = [ 'MANIFEST', '.pyc' ]
    dirs2del = [ './build', './dist' ]
    dirs2ign = [ './.git' ]
    # End config.
    doomed = [ ]
    # Change to base dir.
    os.chdir(BASE_DIR)
    for root, dirs, files in os.walk('.'):
      # Handle root dirs.
      if root in dirs2ign:
        continue
      if root in dirs2del:
        doomed.append(root)
      # Handle files.
      for f in files:
        accused = os.path.join(root, f)
        for suffix in suffixes2del:
          if f.endswith(suffix):
            doomed.append(accused)
            break
        if accused not in doomed:
          for d2del in dirs2del:
            if accused.startswith(d2del):
              doomed.append(accused)
              break
      # Handle dirs.
      for d in dirs:
        accused = os.path.join(root, d)
        for d2ign in dirs2ign:
          if accused.startswith(d2ign):
            dirs.remove(d)
            break
        if d in dirs:
          for d2del in dirs2del:
            if accused.startswith(d2del):
              doomed.append(accused)
              break
    # Probably not required, but just to be safe.
    for accused in doomed:
      for d2ign in dirs2ign:
        if accused.startswith(d2ign):
          doomed.remove(accused)
          break
    doomed.sort(reverse=True)
    for accused in doomed:
      log.info('removing "%s"', os.path.normpath(accused))
      if not self.dry_run:
        try:
          os.unlink(accused)
        except:
          try:
            os.rmdir(accused)
          except:
            log.warn('unable to remove "%s"', os.path.normpath(accused))

setup(
    cmdclass={'test': TestCommand,
              'dist_clean': CleanCommand
             },
    name='chkcrontab',
    version='1.1',
    url='http://code.google.com/p/chkcrontab',
    author='Kevin Lyda',
    author_email='lyda@google.com',
    description='A tool to detect crontab errors',
    long_description=open('README').read(),
    py_modules=['chkcrontab_lib'],
    scripts=['chkcrontab.py'],
    keywords='check lint crontab',
    # See http://pypi.python.org/pypi?%3Aaction=list_classifiers
    license = 'Apache Software License',
    platforms = ['POSIX'],
    classifiers=['Development Status :: 5 - Production/Stable',
                 'Environment :: Console',
                 'License :: OSI Approved :: Apache Software License',
                 'Operating System :: POSIX',
                 'Programming Language :: Python :: 2.5',
                 'Programming Language :: Python :: 2.6',
                 'Programming Language :: Python :: 2.7',
                 'Topic :: Utilities',
                ],
)
