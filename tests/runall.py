#!/usr/bin/python
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

"""Run ***ALL*** the testorz!!!"""

import os
import sys
if sys.version_info < (2, 7):
  import unittest2 as unittest
else:
  import unittest

BASE_PATH = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(BASE_PATH, '..'))

if __name__ == '__main__':
  test_dir = os.path.dirname(globals().get('__file__', os.getcwd()))

  tests = unittest.TestLoader().discover(test_dir)
  runner = unittest.TextTestRunner(verbosity=2)
  result = runner.run(tests)
  if not result.wasSuccessful():
    sys.exit(1)
