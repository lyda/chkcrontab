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

"""Processes crontab files and try to catch common errors.

Parse crontab files and check each type of line for potential syntax errors.
Each line is classified as: comment / blank, variable assignment, standard
action line, @ extention action line, an unknown line.

Nothing is done for comment / blank lines.

Variable assignments are checked to make sure there's not a $ on the
right hand side.  If there is a warning is emitted.  It's a valid syntax
but is usually done in error.

Standard action lines are inspected to make sure the first 5 fields are valid
and within range.  The user name is checked.  The command is checked for bare
%'s.  The last two generate warnings as they can potentially be valid.  There
are some weird configurations of the first 5 fields that are valid but are
marked as errors.


A brief description of each class and function:

  Parsing cron time fields:
    FSM: Finite state machine class - used to parse crontab fields.
    Action*: Action functions for FSM transitions.
    InitCronFSM: Instatiate an FSM and create the grammar for crontab files.

  Checking cron time fields:
    CronTimeField: Used to check limits for a cron time field using an
      instance of the CronTimeFieldLimit class.
    CT*: Subclasses of CronTimeField representing each kind of cron time
      field.
    CronTimeFieldLimit: Limits for each time field position.
    InitCronTimeFieldLimits: Creates CronTimeFieldLimit instances for each
      cron time field position - hour, minute, etc.

  Parse each line:
    CronLine*: Classes that act on the parsed cron lines.
    CronLineTimeAction: Superclass for time/action cron lines.
      CronLineAt: Subclass that acts on @period timespec cron lines.
      CronLineTime: Subclass that acts on 5 field timespec cron lines.
    CronLineFactory: Creates a CronLine* instance to act on the parsed
                     cron line.

  Logging class to pretty-print output:
    LogCounter: A logging class that provides a summary of warnings and errors.

  Putting it all together:
    CheckCrontab: Checks the a crontab file.

"""

__author__ = 'lyda@google.com (Kevin Lyda)'

import copy
import os
import pwd
import re
import string
import sys


# The following usernames are created locally by packages.
USER_WHITELIST = set(('postgres', 'buildbot',
                     ))
# The following extensions imply further postprocessing or that the slack
# role was for a cron that allowed dots in cron scripts.
FILE_RE_WHITELIST = [re.compile(x) for x in
                     ('\.in$', '\.cron$', '\.disabled$')]


class FSM(object):
  """Finite State Machine.

  A simple FSM that is used to parse the time fields in a crontab file.
  """

  def __init__(self, data_out_init):
    """Creates FSM with the initial values for data_out.

    Args:
      data_out_init: Must be a dictionary object.
    """
    self.data_out_init = data_out_init
    self.states = {}
    self.end = {}

  def AddTransition(self, chars, state, action, next_state):
    """Adds a transition.

    Adds a transition based on a set of characters and the current state.
    If a given input char is found in chars and the FSM is currently in
    state, then action is performed and the FSM is set to the next_state.

    Args:
      chars: String of chars this transition applies to.
      state: State this transition applies to.
      action: Action to perform.  This is called with two arguments -
        the data_out variable and the input char.
      next_state: Set the FSM to this state once action is complete.
    """

    if state not in self.states:
      self.states[state] = {}
    self.states[state].update([(c, (action, next_state)) for c in chars])

  def AddEndState(self, state, action):
    """Handle the end state of the FSM.

    This specifies the action to perform when the FSM exhausts its
    data_in and is in state.

    Args:
      state: The state this applies to.
      action: The action to perform.  This is called with just the
        data_out variable.
    """
    self.end[state] = action

  def Run(self, data_in):
    """Run the FSM with the given data_in input.

    Touch each char of data_in with his noodley appendage.

    Args:
      data_in: The input data to parse.

    Returns:
      data_out: Whatever the actions have generated; usually a parse tree.

    Raises:
      LookupError: If no transition can be found, this is raised.
    """
    data_out = copy.deepcopy(self.data_out_init)
    cur_state = 'start'
    parsed = ''
    for c in data_in:
      (action, next_state) = self.states.get(cur_state, {}
                                            ).get(c, (None, None))
      if not action:
        data_out['parser_error'] = ('"%s[[%s]]%s"'
                                    % (parsed, c,
                                       data_in[len(parsed)+1:len(data_in)]))
        return data_out
      action(data_out, c)
      cur_state = next_state
      parsed += c
    if cur_state not in self.end:
      data_out['parser_error'] = '"%s" is incomplete' % parsed
      return data_out
    self.end[cur_state](data_out)
    return data_out


def ActionTime(data_out, c):
  data_out['time'] += c


def ActionStar(data_out, c):
  data_out['time'] = c


def ActionDash(data_out, unused_c):
  data_out['range'] = data_out['time']
  data_out['time'] = ''


def ActionStep(data_out, c):
  data_out['step'] += c


def ActionNoop(unused_data_out, unused_c):
  pass


def ActionTimeComma(data_out, unused_c=''):
  data_out['cron_times'].append(CTTime(int(data_out['time'])))
  data_out['time'] = ''


def ActionStarComma(data_out, unused_c=''):
  data_out['cron_times'].append(CTStar())
  data_out['time'] = ''


def ActionStarStepComma(data_out, unused_c=''):
  data_out['cron_times'].append(CTStarStep(int(data_out['step'])))
  data_out['time'] = ''
  data_out['step'] = ''


def ActionTextComma(data_out, unused_c=''):
  data_out['cron_times'].append(CTText(data_out['time']))
  data_out['time'] = ''


def ActionRangeComma(data_out, unused_c=''):
  data_out['cron_times'].append(CTRange(int(data_out['range']),
                                        int(data_out['time'])))
  data_out['range'] = ''
  data_out['time'] = ''


def ActionTextRangeComma(data_out, unused_c=''):
  data_out['cron_times'].append(CTTextRange(data_out['range'],
                                            data_out['time']))
  data_out['range'] = ''
  data_out['time'] = ''


def ActionRangeStepComma(data_out, unused_c=''):
  data_out['cron_times'].append(CTRangeStep(int(data_out['range']),
                                            int(data_out['time']),
                                            int(data_out['step'])))
  data_out['range'] = ''
  data_out['time'] = ''
  data_out['step'] = ''


def ActionTextRangeStepComma(data_out, unused_c=''):
  data_out['cron_times'].append(CTTextRangeStep(data_out['range'],
                                                data_out['time'],
                                                int(data_out['step'])))
  data_out['range'] = ''
  data_out['time'] = ''
  data_out['step'] = ''


def InitCronFSM():
  """Initialise the FSM with the rules for a cron time field.

  Returns:
    An initialised finite state machine.
  """
  fsm = FSM(dict({'time': '',
                  'range': '',
                  'step': '',
                  'cron_times': []}))

  # Case: *
  fsm.AddTransition('*', 'start', ActionStar, 'star')
  fsm.AddTransition('*', 'next', ActionStar, 'star')
  fsm.AddEndState('star', ActionStarComma)
  fsm.AddTransition(',', 'star', ActionStarComma, 'next')
  # Case: */<number>
  fsm.AddTransition('/', 'star', ActionNoop, 'start_star_step')
  fsm.AddTransition(string.digits, 'start_star_step', ActionStep, 'star_step')
  fsm.AddTransition(string.digits, 'star_step', ActionStep, 'star_step')
  fsm.AddEndState('star_step', ActionStarStepComma)
  fsm.AddTransition(',', 'star_step', ActionStarStepComma, 'next')

  # Case: <number>
  fsm.AddTransition(string.digits, 'start', ActionTime, 'time')
  fsm.AddTransition(string.digits, 'next', ActionTime, 'time')
  fsm.AddTransition(string.digits, 'time', ActionTime, 'time')
  fsm.AddEndState('time', ActionTimeComma)
  fsm.AddTransition(',', 'time', ActionTimeComma, 'next')
  # Case: <number>-<number>
  fsm.AddTransition('-', 'time', ActionDash, 'start_range')
  fsm.AddTransition(string.digits, 'start_range', ActionTime, 'range')
  fsm.AddTransition(string.digits, 'range', ActionTime, 'range')
  fsm.AddEndState('range', ActionRangeComma)
  fsm.AddTransition(',', 'range', ActionRangeComma, 'next')
  # Case: <number>-<number>/<number>
  fsm.AddTransition('/', 'range', ActionNoop, 'start_range_step')
  fsm.AddTransition(string.digits, 'start_range_step',
                    ActionStep, 'range_step')
  fsm.AddTransition(string.digits, 'range_step', ActionStep, 'range_step')
  fsm.AddEndState('range_step', ActionRangeStepComma)
  fsm.AddTransition(',', 'range_step', ActionRangeStepComma, 'next')

  # Case: <text>
  fsm.AddTransition(string.letters, 'start', ActionTime, 'text')
  fsm.AddTransition(string.letters, 'next', ActionTime, 'text')
  fsm.AddTransition(string.letters, 'text', ActionTime, 'text')
  fsm.AddEndState('text', ActionTextComma)
  fsm.AddTransition(',', 'text', ActionTextComma, 'next')
  # Case: <text>-<text>
  fsm.AddTransition('-', 'text', ActionDash, 'start_text_range')
  fsm.AddTransition(string.letters, 'start_text_range', ActionTime,
                    'text_range')
  fsm.AddTransition(string.letters, 'text_range', ActionTime, 'text_range')
  fsm.AddEndState('text_range', ActionTextRangeComma)
  fsm.AddTransition(',', 'text_range', ActionTextRangeComma, 'next')
  # Case: <text>-<text>/<text>
  fsm.AddTransition('/', 'text_range', ActionNoop, 'start_text_range_step')
  fsm.AddTransition(string.digits, 'start_text_range_step', ActionStep,
                    'text_range_step')
  fsm.AddTransition(string.digits, 'text_range_step', ActionStep,
                    'text_range_step')
  fsm.AddEndState('text_range_step', ActionTextRangeStepComma)
  fsm.AddTransition(',', 'text_range_step', ActionTextRangeStepComma, 'next')

  return fsm


class CronTimeField(object):
  """CronTimeField superclass for various time specifiers in cron fields."""

  def __init__(self):
    pass

  def __str__(self):
    return self._text

  @property
  def kind(self):
    return self._kind

  @property
  def start(self):
    return self._start

  @property
  def end(self):
    return self._end

  @property
  def step(self):
    return self._step

  def CheckLowStep(self, diagnostics, cron_time_field):
    if self._step < 1:
      diagnostics.append('%d is too low for field "%s" (%s)'
                         % (self._step, cron_time_field.name, self))

  def CheckHighStep(self, diagnostics, cron_time_field):
    if self._step > self._end:
      diagnostics.append('the step (%d) is greater than the last number'
                         ' (%d) in field "%s" (%s)'
                         % (self._step, self._end,
                            cron_time_field.name, self))

  def CheckLowNum(self, diagnostics, time_field, cron_time_field):
    if time_field < cron_time_field.min_time:
      diagnostics.append('%d is too low for field "%s" (%s)'
                         % (time_field, cron_time_field.name, self))

  def CheckHighNum(self, diagnostics, time_field, cron_time_field):
    if time_field > cron_time_field.max_time:
      diagnostics.append('%d is too high for field "%s" (%s)'
                         % (time_field, cron_time_field.name, self))

  def CheckRange(self, diagnostics, cron_time_field):
    if self._start > self._end:
      diagnostics.append('%d is greater than %d in field "%s" (%s)'
                         % (self._start, self._end, cron_time_field.name,
                            self))

  def CheckValidText(self, diagnostics, time_field, cron_time_field):
    if time_field.lower() not in cron_time_field.valid_text:
      diagnostics.append('%s is not valid for field "%s" (%s)'
                         % (time_field, cron_time_field.name, self))


class CTTime(CronTimeField):
  """CronTimeField subclass for <number>."""

  def __init__(self, start_time):
    """Initialize CTRange with start_time."""
    CronTimeField.__init__(self)
    self._kind = 'time'
    self._start = start_time
    self._text = '%d' % start_time

  def GetDiagnostics(self, cron_time_field):
    diagnostics = []
    self.CheckLowNum(diagnostics, self._start, cron_time_field)
    self.CheckHighNum(diagnostics, self._start, cron_time_field)
    return diagnostics


class CTRange(CronTimeField):
  """CronTimeField subclass for <number>-<number>."""

  def __init__(self, start_time, end_time):
    """Initialize CTRange with start_time and end_time."""
    CronTimeField.__init__(self)
    self._kind = 'range'
    self._start = start_time
    self._end = end_time
    self._text = '%d-%d' % (start_time, end_time)

  def GetDiagnostics(self, cron_time_field):
    diagnostics = []
    self.CheckRange(diagnostics, cron_time_field)
    self.CheckLowNum(diagnostics, self._start, cron_time_field)
    self.CheckHighNum(diagnostics, self._end, cron_time_field)
    return diagnostics


class CTRangeStep(CronTimeField):
  """CronTimeField subclass for <number>-<number>/<number>."""

  def __init__(self, start_time, end_time, step_count):
    """Initialize CTRangeStep with start_time, end_time and step_count."""
    CronTimeField.__init__(self)
    self._kind = 'range_step'
    self._start = start_time
    self._end = end_time
    self._step = step_count
    self._text = '%d-%d/%d' % (start_time, end_time, step_count)

  def GetDiagnostics(self, cron_time_field):
    diagnostics = []
    self.CheckRange(diagnostics, cron_time_field)
    self.CheckLowNum(diagnostics, self._start, cron_time_field)
    self.CheckHighNum(diagnostics, self._end, cron_time_field)
    self.CheckLowStep(diagnostics, cron_time_field)
    self.CheckHighStep(diagnostics, cron_time_field)
    self.CheckHighNum(diagnostics, self._step, cron_time_field)
    return diagnostics


class CTStar(CronTimeField):
  """CronTimeField subclass for *."""

  def __init__(self):
    """Initialize CTStar."""
    CronTimeField.__init__(self)
    self._kind = 'star'
    self._text = '*'

  def GetDiagnostics(self, unused_cron_time_field):
    return []


def ChkCTStarOnly(cron_time_field):
  """Checks if a crontab field is only a *.

  Args:
    cron_time_field: Parsed cron time field to check.

  Returns:
    True if there's only a * in this field.
  """
  if not cron_time_field:
    return True
  if len(cron_time_field) == 1 and cron_time_field[0].kind == 'star':
    return True
  return False


class CTStarStep(CronTimeField):
  """CronTimeField subclass for */<number>."""

  def __init__(self, step_count):
    """Initialize CTStarStep with step_count."""
    CronTimeField.__init__(self)
    self._kind = 'star_step'
    self._step = step_count
    self._text = '*/%d' % step_count

  def GetDiagnostics(self, cron_time_field):
    diagnostics = []
    self.CheckLowStep(diagnostics, cron_time_field)
    self.CheckHighNum(diagnostics, self._step, cron_time_field)
    return diagnostics


class CTText(CronTimeField):
  """CronTimeField subclass for <text>."""

  def __init__(self, start_time):
    """Initialize CTText with start_time."""
    CronTimeField.__init__(self)
    self._kind = 'text'
    self._start = start_time
    self._text = '%s' % start_time

  def GetDiagnostics(self, cron_time_field):
    diagnostics = []
    self.CheckValidText(diagnostics, self._start, cron_time_field)
    return diagnostics


class CTTextRange(CronTimeField):
  """CronTimeField subclass for <text>-<text>."""

  def __init__(self, start_time, end_time):
    """Initialize CTTextRange with start_time and end_time."""
    CronTimeField.__init__(self)
    self._kind = 'text_range'
    self._start = start_time
    self._end = end_time
    self._text = '%s-%s' % (start_time, end_time)

  def GetDiagnostics(self, cron_time_field):
    diagnostics = []
    self.CheckValidText(diagnostics, self._start, cron_time_field)
    self.CheckValidText(diagnostics, self._end, cron_time_field)
    return diagnostics


class CTTextRangeStep(CronTimeField):
  """CronTimeField subclass for <text>-<text>."""

  def __init__(self, start_time, end_time, step_count):
    """Initialize CTTextRangeStep with start_time, end_time and step_count."""
    CronTimeField.__init__(self)
    self._kind = 'text_range_step'
    self._start = start_time
    self._end = end_time
    self._step = step_count
    self._text = '%s-%s/%s' % (start_time, end_time, step_count)

  def GetDiagnostics(self, cron_time_field):
    diagnostics = []
    self.CheckValidText(diagnostics, self._start, cron_time_field)
    self.CheckValidText(diagnostics, self._end, cron_time_field)
    self.CheckLowStep(diagnostics, cron_time_field)
    self.CheckHighNum(diagnostics, self._step, cron_time_field)
    return diagnostics


class CronTimeFieldLimit(object):
  """Class to represent the limits of a crontab time field."""

  def __init__(self, min_time, max_time, valid_text):
    """Initialise the limits."""
    self.min_time = min_time
    self.max_time = max_time
    self.valid_text = valid_text

  def _GetName(self):
    return self._name

  def _SetName(self, name):
    self._name = name

  name = property(_GetName, _SetName,
                  doc="""Gets or Sets the name of this field.""")


def InitCronTimeFieldLimits():
  """Instantiate the CronTimeField objects for the five cron time fields.

  Returns:
    A tuple of 5 instantiated CronTimeField objects for minute, hour,
    day of month, month and day of week.
  """
  cron_time_field_limits = {
      'minute': CronTimeFieldLimit(0, 59, []),
      'hour': CronTimeFieldLimit(0, 23, []),
      'day of month': CronTimeFieldLimit(1, 31, []),
      'month': CronTimeFieldLimit(1, 12,
                                  ['jan', 'feb', 'mar', 'apr',
                                   'may', 'jun', 'jul', 'aug',
                                   'sep', 'oct', 'nov', 'dec']),
      'day of week': CronTimeFieldLimit(0, 7,
                                        ['sun', 'mon', 'tue', 'wed',
                                         'thu', 'fri', 'sat'])
      }
  for field_name in cron_time_field_limits:
    cron_time_field_limits[field_name].name = field_name
  return cron_time_field_limits


class CronLineEmpty(object):
  """For empty lines."""

  def ValidateAndLog(self, log):
    pass


class CronLineChkCrontabCmd(object):
  """For chkcrontab command lines."""

  def __init__(self, command, msg_kind):
    self.command = command
    self.msg_kind = msg_kind

  def ValidateAndLog(self, log):
    """Validates a chkcrontab command line and logs any errors and warnings.

    Args:
      log: A LogCounter instance to record issues.
    """
    if not log.ValidMsgKind(self.msg_kind):
      log.LineError(log.MSG_CHKCRONTAB_ERROR,
                    '"%s" is an unknown error message.' % self.msg_kind)
    if self.command == 'disable-msg':
      log.Ignore(self.msg_kind)
    elif self.command == 'enable-msg':
      log.Unignore(self.msg_kind)
    else:
      log.LineError(log.MSG_CHKCRONTAB_ERROR,
                    'Invalid chkcrontab command - must be'
                    ' enable-msg or disable-msg.')


class CronLineComment(object):
  """For Comment lines."""

  def ValidateAndLog(self, log):
    pass


class CronLineAssignment(object):
  """For var assignment lines."""

  def __init__(self, variable):
    self.variable = variable

  def ValidateAndLog(self, log):
    """Validates an assignment line and logs any errors and warnings.

    Args:
      log: A LogCounter instance to record issues.
    """
    # An assignment like /^FOO=\s*$/ will trigger a "bad minute" error.
    if not self.variable.strip(string.whitespace):
      log.LineError(log.MSG_QUOTE_VALUES,
                    'Variable assignments in crontabs must contain'
                    ' non-whitespace characters (try quotes).')
    # Warn when FOO=$BAR as users expect shell-like behaviour.
    if '$' in self.variable:
      log.LineWarn(log.MSG_SHELL_VAR,
                   'Variable assignments in crontabs are not like shell.'
                   '  $VAR is not expanded.')
    # TODO(lyda): Possible additions:
    #             * Check for backticks.
    #             Possible collective additions:
    #             * Make sure MAILTO is set.
    #             * Make sure PATH is set.


class CronLineTimeAction(object):
  """Checks cron lines that specify a time and an action.

  Must be used as a subclass - subclass must implement _CheckTimeField.
  """

  def __init__(self, time_field, user, command):
    self.time_field = time_field
    self.user = user
    self.command = command

  def ValidateAndLog(self, log):
    """Validates an @ time spec line and logs any errors and warnings.

    Args:
      log: A LogCounter instance to record issues.
    """
    self._CheckTimeField(log)

    # User checks.
    if self.user in USER_WHITELIST:
      return
    elif len(self.user) > 31:
      log.LineError(log.MSG_INVALID_USER, 'Username too long "%s"' % self.user)
    elif self.user.startswith('-'):
      log.LineError(log.MSG_INVALID_USER, 'Invalid username "%s"' % self.user)
    elif re.search(r'[\s!"#$%&\'()*+,/:;<=>?@[\\\]^`{|}~]', self.user):
      log.LineError(log.MSG_INVALID_USER, 'Invalid username "%s"' % self.user)
    else:
      try:
        pwd.getpwnam(self.user)
      except KeyError:
        log.LineWarn(log.MSG_USER_NOT_FOUND,
                     'User "%s" not found.' % self.user)

    # Command checks.
    if self.command.startswith('%') or re.search(r'[^\\]%', self.command):
      log.LineWarn(log.MSG_BARE_PERCENT, 'A bare % is a line break in'
                   ' crontab and is commonly not intended.')


class CronLineAt(CronLineTimeAction):
  """For cron lines specified with @ time specs."""

  def _CheckTimeField(self, log):
    """Checks the @ time field.

    Args:
      log: A LogCounter instance to record issues.
    """
    valid_at_periods = ('reboot', 'yearly', 'annually', 'monthly',
                        'weekly', 'daily', 'midnight', 'hourly')
    if self.time_field not in valid_at_periods:
      log.LineError(log.MSG_INVALID_AT,
                    'Invalid @ directive "%s"' % self.time_field)


class CronLineTime(CronLineTimeAction):
  """For cron lines specified with 5 field time specs."""

  def _CheckTimeField(self, log):
    """Validates a 5 field time spec line and logs any errors and warnings.

    Args:
      log: A LogCounter instance to record issues.
    """
    cron_time_field_names = ('minute', 'hour', 'day of month',
                             'month', 'day of week')
    cron_time_field_limits = InitCronTimeFieldLimits()
    fsm = InitCronFSM()

    # Check the first five fields individually.
    parsed_cron_time_fields = {}
    for field in cron_time_field_names:
      parsed_cron_time_fields[field] = fsm.Run(self.time_field[field])
      if 'parser_error' in parsed_cron_time_fields[field]:
        log.LineError(log.MSG_FIELD_PARSE_ERROR,
                      'Failed to fully parse "%s" field here: %s'
                      % (field,
                         parsed_cron_time_fields[field]['parser_error']))
      # Check the time field according to the cron_time_fields[field] rules.
      for cron_time in parsed_cron_time_fields[field]['cron_times']:
        for line_error in (cron_time.
                           GetDiagnostics(cron_time_field_limits[field])):
          log.LineError(log.MSG_FIELD_VALUE_ERROR, line_error)

    # Check the first five fields collectively.
    if ChkCTStarOnly(parsed_cron_time_fields['minute']['cron_times']):
      if not ChkCTStarOnly(parsed_cron_time_fields['hour']['cron_times']):
        log.LineWarn(log.MSG_HOURS_NOT_MINUTES,
                     'Cron will run this every minute for the hours set.')


class CronLineUnknown(object):
  """For unrecognised cron lines."""

  def ValidateAndLog(self, log):
    log.LineError(log.MSG_LINE_ERROR, 'Failed to parse line.')


class CronLineFactory(object):
  """Classify a line in a cron field by what type of line it is."""

  def __init__(self):
    pass

  def ParseLine(self, line):
    """Classify a line.

    Args:
      line: The line to classify.

    Returns:
      A CronLine* class (must have a ValidateAndLog method).
    """
    chkcrontab_cmd = re.compile('##*\s*chkcrontab:\s*(.*)=(.*)')
    assignment_line_re = re.compile('[a-zA-Z_][a-zA-Z0-9_]*\s*=(.*)')
    at_line_re = re.compile('@(\S+)\s+(\S+)\s+(.*)')
    cron_time_field_re = '[\*0-9a-zA-Z,/-]+'
    time_field_job_line_re = re.compile(
        '^\s*(%s)\s+(%s)\s+(%s)\s+(%s)\s+(%s)\s+(\S+)\s+(.*)' %
        (cron_time_field_re, cron_time_field_re, cron_time_field_re,
         cron_time_field_re, cron_time_field_re))

    if not line:
      return CronLineEmpty()

    if line.startswith('#'):
      match = chkcrontab_cmd.match(line)
      if match:
        return CronLineChkCrontabCmd(match.groups()[0], match.groups()[1])
      else:
        return CronLineComment()

    match = assignment_line_re.match(line)
    if match:
      return CronLineAssignment(match.groups()[0])

    match = at_line_re.match(line)
    if match:
      return CronLineAt(match.groups()[0], match.groups()[1],
                        match.groups()[2])

    # Is this line a cron job specifier?
    match = time_field_job_line_re.match(line)
    if match:
      field = {
          'minute': match.groups()[0],
          'hour': match.groups()[1],
          'day of month': match.groups()[2],
          'month': match.groups()[3],
          'day of week': match.groups()[4],
          }
      return CronLineTime(field, match.groups()[5], match.groups()[6])

    return CronLineUnknown()


class LogMsgKindNotFound(Exception):
  pass


# TODO(lyda): Revisit this.  A possible alternative is:
# MessageCollector - has a collection of messages; methods for printing
# and summarising them.
# Message - super-class for message objects.
# MessageExampleError - a class for EXAMPLE_ERROR - the __init__ method
# would take the args to fill the string.  The MsgKind method would
# generate a string off the class name.  And there would be a __str__
# method obviously.
class LogCounter(object):
  """A log class that collects stats on warnings and errors.

  This log class collects stats on the number of warnings and errors.
  It also has some methods for queueing up warnings and errors and then
  emiting them with the relevant line_no and line.
  """

  _msg_kinds = set(('BARE_PERCENT',
                    'CHKCRONTAB_ERROR',
                    'FIELD_PARSE_ERROR',
                    'FIELD_VALUE_ERROR',
                    'INVALID_AT',
                    'INVALID_USER',
                    'LINE_ERROR',
                    'QUOTE_VALUES',
                    'SHELL_VAR',
                    'USER_NOT_FOUND',
                    'HOURS_NOT_MINUTES'))

  def __init__(self):
    """Inits LogCounter."""
    self._error_count = 0
    self._warn_count = 0
    self._ignored = set()
    self._line_errors = []
    self._line_warns = []

  def Ignore(self, msg_kind):
    """Start ignoring a category of message.

    Args:
      msg_kind: The category of message.
    """
    self._ignored.add(msg_kind)

  def Unignore(self, msg_kind):
    """Stop ignoring a category of message.

    Args:
      msg_kind: The category of message.
    """
    self._ignored.discard(msg_kind)

  def ValidMsgKind(self, msg_kind):
    """Check that msg_kind is a valid error.

    Args:
      msg_kind: The category of message.

    Returns:
      True if it's valid.
      False if not valid.
    """
    return msg_kind in self._msg_kinds

  def __getattr__(self, msg_kind):
    """Return value for msg_kind.

    Args:
      msg_kind: The category of message.

    Returns:
      String for msg_kind if valid.

    Raises:
      LogMsgKindNotFound: Raised if not a valid log message.
    """
    if msg_kind.startswith('MSG_'):
      if msg_kind[4:] in self._msg_kinds:
        return msg_kind[4:]
    raise LogMsgKindNotFound()

  def Warn(self, message):
    """Print warning.

    Immediately print warning message.  Increment warning counter.

    Args:
      message: The message to print as a warning.
    """
    print('W:', message)
    self._warn_count += 1

  def LineWarn(self, msg_kind, line_warn):
    """Queue warning.

    Queue a warning message to print later.  Increment warning counter.

    Args:
      msg_kind: The category of message.
      line_warn: The message to queue as a warning.
    """
    if msg_kind not in self._ignored:
      self._line_warns.append('%s: %s' % (msg_kind, line_warn))
      self._warn_count += 1

  def Error(self, message):
    """Print error.

    Immediately print error message.  Increment error counter.

    Args:
      message: The message to print as a error.
    """
    print('E:', message)
    self._error_count += 1

  def LineError(self, msg_kind, line_error):
    """Queue error.

    Queue a error message to print later.  Increment error counter.

    Args:
      msg_kind: The category of message.
      line_error: The message to queue as a error.
    """
    if msg_kind not in self._ignored:
      self._line_errors.append('%s: %s' % (msg_kind, line_error))
      self._error_count += 1

  def Emit(self, line_no, line):
    """Print queued warnings and errors.

    Print the queued warnings and errors if they exist.  Reset queues.
    Prefix all this with the relevant context - line_no and line.

    Args:
      line_no: Line number these queued warnings and errors apply to.
      line: Line these queued warnings and errors apply to.
    """
    if self._line_errors or self._line_warns:
      spacer = ' ' * len('%d' % line_no)
      line_error_fmt = 'e: %s  %%s' % spacer
      line_warn_fmt = 'w: %s  %%s' % spacer
      if self._line_errors:
        print('E: %d: %s' % (line_no, line))
      else:
        print('W: %d: %s' % (line_no, line))
      for line_error in self._line_errors:
        print(line_error_fmt % line_error)
      for line_warn in self._line_warns:
        print(line_warn_fmt % line_warn)
      self._line_errors = []
      self._line_warns = []

  def Summary(self):
    """Print summary of all warnings and errors.

    Print the warning and error counts if they exist.

    Returns:
      2: If there were any errors.
      1: If there were any warnings but no errors.
      0: If there were no errors or warnings.
    """
    more_info = 'See http://goo.gl/7XS9q for more info.'
    if self._error_count > 0:
      print('E: There were %d errors and %d warnings.'
            % (self._error_count, self._warn_count))
      print(more_info)
      return 2
    elif self._warn_count > 0:
      print('W: There were %d warnings.' % self._warn_count)
      print(more_info)
      return 1
    else:
      return 0

  @property
  def warn_count(self):
    """Accessor method for the warning count."""
    return self._warn_count

  @property
  def error_count(self):
    """Accessor method for the error count."""
    return self._error_count


def CheckCrontab(crontab_file, log):
  """Check a crontab file.

  Checks crontab_file for a variety of errors or potential errors.  This only
  works with the crontab format found in /etc/crontab and /etc/cron.d.

  Args:
    crontab_file: Name of the crontab file to check.
    log: A LogCounter object.

  Returns:
    0 if there were no errors.
    >0 if there were errors.
    Note: warnings alone will not yield a non-zero exit code.
  """

  # Check if the file even exists.
  if not os.path.exists(crontab_file):
    return log.Summary()

  # Check the file name.
  if re.search('[^A-Za-z0-9_-]', os.path.basename(crontab_file)):
    in_whitelist = False
    for pattern in FILE_RE_WHITELIST:
      if pattern.search(os.path.basename(crontab_file)):
        in_whitelist = True
        break
    if not in_whitelist:
      log.Warn('Cron will not process this file - its name must match'
               ' [A-Za-z0-9_-]+ .')

  line_no = 0
  cron_line_factory = CronLineFactory()
  for line in open(crontab_file, 'r'):
    line = line.strip()
    line_no += 1

    cron_line = cron_line_factory.ParseLine(line)
    cron_line.ValidateAndLog(log)

    log.Emit(line_no, line)

  # Summarize the log messages if there were any.
  return log.Summary()


def main():
  log = LogCounter()
  if len(sys.argv) != 2:
    log.Error('Must provide a crontab file to check.')
  print('Checking correctness of %s' % sys.argv[1])
  return CheckCrontab(sys.argv[1], log)


if __name__ == '__main__':
  sys.exit(main())
