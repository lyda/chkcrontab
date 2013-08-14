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

"""Test for chkcrontab_lib."""

__author__ = 'lyda@google.com (Kevin Lyda)'

import os
import re
import string
import sys

if sys.version_info < (2, 7):
  import unittest2 as unittest
else:
  import unittest
import chkcrontab_lib as check

BASE_PATH = os.path.dirname(__file__)

##### Tests for FSM


def Flds(field, parsed_fields):
  return [field,
          {'cron_times': parsed_fields}]


def EFlds(field, parsed_fields):
  return [field,
          {'parser_error': 'An error',
           'cron_times': parsed_fields}]


class FSMUnitTest(unittest.TestCase):

  def setUp(self):
    self.fsm = check.InitCronFSM()

  def RunFSMOnFields(self, fields):
    for field, check_parsed_fields in fields:
      try:
        parsed_fields = self.fsm.Run(field)
      except ValueError:
        self.fail('Unexpected error parsing "%s"' % field)
      if 'parser_error' in parsed_fields:
        self.assertTrue('parser_error' in check_parsed_fields,
                        'Unexpected parser error: %s' %
                        parsed_fields['parser_error'])
      elif 'parser_error' in check_parsed_fields:
        self.assertTrue('parser_error' in parsed_fields,
                        'Expected parser error: %s' %
                        check_parsed_fields['parser_error'])
      self.assertEquals(len(parsed_fields['cron_times']),
                        len(check_parsed_fields['cron_times']),
                        'Expected to find %d fields not %d'
                        % (len(check_parsed_fields['cron_times']),
                           len(parsed_fields['cron_times'])))
      for i in range(min(len(parsed_fields['cron_times']),
                         len(check_parsed_fields['cron_times']))):
        self.assertEquals(parsed_fields['cron_times'][i].Kind,
                          check_parsed_fields['cron_times'][i][0],
                          'Parser detected "%s" field not "%s"'
                          % (parsed_fields['cron_times'][i].Kind,
                             check_parsed_fields['cron_times'][i][0]))
        self.assertEquals('%s' % parsed_fields['cron_times'][i],
                          check_parsed_fields['cron_times'][i][1],
                          'Parser found "%s" not "%s"'
                          % (parsed_fields['cron_times'][i],
                             check_parsed_fields['cron_times'][i][1]))

  def testSimpleStars(self):
    self.RunFSMOnFields([Flds('*', [['star', '*']]),
                         Flds('*/2', [['star_step', '*/2']]),
                         EFlds('*-*', []),
                        ])

  def testSimpleTime(self):
    self.RunFSMOnFields([Flds('3', [['time', '3']]),
                         EFlds('5/2', []),
                         Flds('1-9', [['range', '1-9']]),
                         Flds('11-49/2', [['range_step', '11-49/2']]),
                        ])

  def testSimpleText(self):
    self.RunFSMOnFields([Flds('mon', [['text', 'mon']]),
                         Flds('mon-fri', [['text_range', 'mon-fri']]),
                         Flds('mon-fri/2', [['text_range_step', 'mon-fri/2']]),
                         EFlds('mon/2', []),
                        ])

  def testSimpleErrors(self):
    self.RunFSMOnFields([EFlds('m2', []),
                         EFlds('2m', []),
                         EFlds('2*', []),
                         EFlds('*2', []),
                         EFlds('*m', []),
                         EFlds('m*', []),
                        ])

  def testSimplePunctErrors(self):
    self.RunFSMOnFields([EFlds('-', []),
                         EFlds(',', []),
                         EFlds('/', []),
                         EFlds('*/tue', []),
                         EFlds('*/,', []),
                         EFlds('*//2', []),
                        ])

  def testComplexErrors(self):
    self.RunFSMOnFields([EFlds('1-55,34//3,6-9', [['range', '1-55']]),
                         EFlds('5-mon', []),
                         EFlds('mon-78', []),
                         EFlds('1-2-3', []),
                         EFlds('1-20/2/3', []),
                         EFlds('23,**,33', [['time', '23']]),
                        ])

  def testComplex(self):
    self.RunFSMOnFields([Flds('mon,tue,thu', [['text', 'mon'],
                                              ['text', 'tue'],
                                              ['text', 'thu'],
                                             ]),
                         Flds('mon,3,*,*/2,mon-fri,1-2,3-4/2',
                              [['text', 'mon'],
                               ['time', '3'],
                               ['star', '*'],
                               ['star_step', '*/2'],
                               ['text_range', 'mon-fri'],
                               ['range', '1-2'],
                               ['range_step', '3-4/2'],
                              ]),
                        ])


class CTFUnitTest(unittest.TestCase):

  def setUp(self):
    self.cron_time_fields = check.InitCronTimeFieldLimits()
    self.fsm = check.InitCronFSM()

  def FieldTest(self, field_name, field_count, field_data, field_errors):
    parsed = self.fsm.Run(field_data)
    self.assertEquals(field_count, len(parsed['cron_times']),
                      'Found %d fields not %d fields.'
                      % (len(parsed['cron_times']), field_count))
    actual_field_errors = []
    for field_action in parsed['cron_times']:
      actual_field_errors.extend(field_action.
                                 GetDiagnostics(self.
                                                cron_time_fields[field_name]))
    self.assertEquals(field_errors, len(actual_field_errors),
                      'Error list was: %s'
                      % ('\n[\'' + '\',\n \''.join(actual_field_errors)
                         + '\']\n'))

  def testMinute(self):
    self.FieldTest('minute', 6, '0,1,30,59,60,61',
                   1 +  # for 60
                   1)   # for 61
    self.FieldTest('minute', 3, '0-59,0-60,0-61',
                   1 +  # for 60 in 0-60
                   1)   # for 61 in 0-61
    self.FieldTest('minute', 4, '0-5/10,0-10/5,0-33/60,0-61/60',
                   1 +  # for 10 > 5 in 0-5/10
                   2 +  # for 33 > 60 and 60 in 0-33/60
                   2)   # for 61 and 60 in 0-61/60
    self.FieldTest('minute', 3, 'mon,mon-fri,mon-fri/3',
                   1 +  # for mon in mon
                   2 +  # for mon and frin in mon-fri
                   2)   # for mon and frin in mon-fri/3

  def testHour(self):
    self.FieldTest('hour', 6, '0,1,12,23,24,25',
                   1 +  # for 24 in 24
                   1)   # for 25 in 25
    self.FieldTest('hour', 7, '0-12,1-12,12-13,12-1,23-24,24-30,25-1',
                   1 +  # for 12 > 1 in 12-1
                   1 +  # for 24 in 23-24
                   1 +  # for 30 in 23-30
                   1)   # for 25 > 1 in 25-1
    self.FieldTest('hour', 6, '0-12/2,1-3/0,12-13/14,12-1/2,23-24/25,24-30/2',
                   1 +  # for 0 in 1-3/0
                   1 +  # for 14 in 12-13/14
                   2 +  # for 12 > 1 and 2 > 1 in 12-1/2
                   3 +  # for 24 and 25 and 25 > 24 in 23-24/25
                   1)   # for 24 in 24-30/2

  def testDayOfMonth(self):
    self.FieldTest('day of month', 6, '0,0001,15,31,32,33',
                   1 +  # for 0 in 0
                   1 +  # for 32 in 32
                   1)   # for 33 in 33
    self.FieldTest('day of month', 7, '0-15,1-15,15-16,15-1,31-32,32-30,33-1',
                   1 +  # for 0 in 0-15
                   1 +  # for 15 > 1 in 15-1
                   1 +  # for 32 in 31-32
                   1 +  # for 30 in 31-30
                   1)   # for 33 > 1 in 33-1
    self.FieldTest('day of month', 6,
                   '0-14/2,1-3/0,14-16/17,14-1/2,31-32/33,32-30/2',
                   1 +  # for 0 in 0-14/2
                   1 +  # for 0 in 1-3/0
                   1 +  # for 17 in 14-16/17
                   2 +  # for 14 > 1 and 2 > 1 in 14-1/2
                   3 +  # for 32 and 33 and 33 > 32 in 31-32/33
                   1)   # for 32 in 32-30/2

  def testMonth(self):
    self.FieldTest('month', 6, '0,1,7,12,13,14',
                   1 +  # for 0 in 0
                   1 +  # for 13 in 13
                   1)   # for 14 in 14
    self.FieldTest('month', 7, '0-7,1-7,7-8,7-1,12-13,13-10,14-1',
                   1 +  # for 0 in 0-7
                   1 +  # for 7 > 1 in 7-1
                   1 +  # for 13 in 12-13
                   1 +  # for 10 in 12-10
                   1)   # for 14 > 1 in 14-1
    self.FieldTest('month', 6, '0-12/2,1-3/0,4-8/9,14-1/2,12-13/14,13-10/2',
                   1 +  # for 0 in 0-14/2
                   1 +  # for 0 in 1-3/0
                   1 +  # for 9 in 4-8/9
                   2 +  # for 14 > 1 and 2 > 1 in 14-1/2
                   3 +  # for 13 and 14 and 14 > 13 in 12-13/14
                   1)   # for 13 in 13-10/2

  def testDayOfWeek(self):
    self.FieldTest('day of week', 6, '0,1,4,7,8,9',
                   1 +  # for 8 in 8
                   1)   # for 9 in 9
    self.FieldTest('day of week', 7, '0-4,1-4,4-5,4-1,7-8,8-7,9-1',
                   1 +  # for 4 > 1 in 4-1
                   1 +  # for 8 in 7-8
                   1 +  # for 7 in 7-7
                   1)   # for 9 > 1 in 9-1
    self.FieldTest('day of week', 6, '0-3/2,1-3/0,3-5/6,3-1/2,7-8/9,8-7/2',
                   1 +  # for 0 in 1-3/0
                   1 +  # for 6 in 3-5/6
                   2 +  # for 3 > 1 and 2 > 1 in 3-1/2
                   3 +  # for 8 and 9 and 9 > 8 in 7-8/9
                   1)   # for 8 in 8-7/2


class MockLogCounter(object):
  def __init__(self):
    self._error_msg = ''
    self._warn_msg = ''

  def LineError(self, unused_msg_kind, message):
    self._error_msg = message

  def LineWarn(self, unused_msg_kind, message):
    self._warn_msg = message

  def __getattr__(self, attr):
    return attr

  @property
  def error_msg(self):
    return self._error_msg

  @property
  def warn_msg(self):
    return self._warn_msg


class CheckClassifierUnitTest(unittest.TestCase):
  #TODO(lyda): Write test cases for these.
  pass


class CheckCrontabUnitTest(unittest.TestCase):

  def __init__(self, *args):
    unittest.TestCase.__init__(self, *args)
    self._fail_pat = re.compile('FAIL ([0-9]+)')
    self._warn_pat = re.compile('WARN ([0-9]+)')

  def GetExpWFRs(self, test_file):
    exp_warn = exp_fail = 0
    for line in open(test_file):
      m = self._warn_pat.search(line)
      if m:
        exp_warn += int(m.groups()[0])
      m = self._fail_pat.search(line)
      if m:
        exp_fail += int(m.groups()[0])
    if exp_fail:
      exp_rc = 2
    elif exp_warn:
      exp_rc = 1
    else:
      exp_rc = 0
    return (exp_warn, exp_fail, exp_rc)

  def CheckACrontab(self, crontab, whitelisted_users=None):
    log = check.LogCounter()
    crontab_file = os.path.join(BASE_PATH, crontab)
    (exp_warn, exp_fail, exp_rc) = self.GetExpWFRs(crontab_file)
    self.assertEquals(check.check_crontab(crontab_file, log, whitelisted_users), exp_rc,
                      'Failed to return %d for crontab errors.' % exp_rc)
    self.assertEquals(log.warn_count, exp_warn,
                      'Found %d warns not %d.' % (log.warn_count, exp_warn))
    self.assertEquals(log.error_count, exp_fail,
                      'Found %d errors not %d.' % (log.error_count, exp_fail))

  def testCheckBadCrontab(self):
    self.CheckACrontab('test_crontab')

  def testCheckWarnCrontab(self):
    self.CheckACrontab('test_crontab.warn')

  def testCheckWarnWithDisablesCrontab(self):
    self.CheckACrontab('test_crontab.no-warn')

  def testCheckBadWithDisablesCrontab(self):
    self.CheckACrontab('test_crontab.disable')

  def testCheckWarnWithWhitelistedUser(self):
    self.CheckACrontab('test_crontab.whitelist', ['not_a_user'])


if __name__ == '__main__':
  result = unittest.main()
  if not result.wasSuccessful():
    sys.exit()
