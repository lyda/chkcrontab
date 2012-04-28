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

from distutils.core import setup

setup(
    name='chkcrontab',
    version='1.0',
    url='http://code.google.com/p/chkcrontab',
    author='Kevin Lyda',
    author_email='lyda@google.com',
    description='A tool to detect crontab errors',
    long_description=open('README').read(),
    py_modules=['chkcrontab_lib'],
    scripts=['chkcrontab.py'],
    keywords='check lint crontab',
    # See http://pypi.python.org/pypi?%3Aaction=list_classifiers
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
