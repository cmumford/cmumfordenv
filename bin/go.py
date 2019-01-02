#!/usr/bin/env python

from __future__ import print_function

import os
import sys

class NoRootException(Exception):
  """Thrown when the Chromium root directory cannot be determined."""
  pass

class BadLength(Exception):
  """Thrown when value length != 2."""
  pass

class BadValue(Exception):
  pass

class Go:
  root_variable_name = '$CRROOT'

  @staticmethod
  def is_chrome_root_dir(dir_path):
    required_items = [
      '.git',
      'chrome',
      'content',
      'components',
      'android_webview',
      'DEPS',
    ]
    for d in required_items:
      if not os.path.exists(os.path.join(dir_path, d)):
        return False
    return True

  @staticmethod
  def get_chrome_dir(some_chrome_dir):
    """Given a *possible* subdirectory of the chromium source tree return
    the actual root Chromium directory."""
    while True:
      if (Go.is_chrome_root_dir(some_chrome_dir)):
        return some_chrome_dir
      p = os.path.dirname(some_chrome_dir)
      if not p or p is some_chrome_dir:
        return None
      some_chrome_dir = p

  @staticmethod
  def ParseLine(line):
    """Parse a line like this:

    'shortcut, value'

      -- or --

    'shortcut, [value1, value2]'

    into:

    ('shortcut', 'value')

      -- or --

    ('shortcut', ['value1', ('value2']


    >>> Go.ParseLine('shortcut, value')
    ('shortcut', 'value')
    >>> Go.ParseLine('  shortcut  , value  ')
    ('shortcut', 'value')
    >>> Go.ParseLine('shortcut, (  value1,   value2  )')
    ('shortcut', ['value1', 'value2'])
    >>> Go.ParseLine('$HOME, value')
    ('$HOME', 'value')
    >>> Go.ParseLine('shortcut value')
    (None, None)
    >>> Go.ParseLine('shortcut, (value1,$CRROOT)')
    Traceback (most recent call last):
     ...
    BadValue
    >>> Go.ParseLine('shortcut, (  value1,   value2, value3  )')
    Traceback (most recent call last):
     ...
    BadLength: shortcut
    """
    comma_idx = line.find(',')
    if comma_idx is -1:
      return (None, None)
    shortcut = line[:comma_idx].strip()
    value = line[comma_idx+1:].strip()
    if value[0] == '(' or value[0] == '[':
      values = value[1:-1].split(',')
      if len(values) != 2:
        raise BadLength(shortcut)
      if Go.root_variable_name in values[1]:
        raise BadValue()
      return (shortcut, [v.strip() for v in values])
    return (shortcut, value)

  def __init__(self, cwd):
    self.shortcuts = {}
    self.chromium_root_dir = Go.get_chrome_dir(cwd)
    with open(os.path.expanduser('~/.goshortcuts')) as f:
      for line in f:
        (shortcut, values) = Go.ParseLine(line)
        if not shortcut:
          continue
        self.shortcuts[shortcut] = values
    if not self.chromium_root_dir:
      # Can't determine Chromium root directory based on current directory
      # so see if there is a shortcut with a value of $CRROOT and use it's
      # second value.
      for shortcut in self.shortcuts:
        value = self.shortcuts[shortcut]
        if isinstance(value, list) and value[0] == Go.root_variable_name:
          self.chromium_root_dir = value[1]
    if not self.chromium_root_dir:
      print(str.format('Cannot find suitable value for "{0}"',
                       Go.root_variable_name),
            file=sys.stderr)
      sys.exit(2)

  def do_print(self):
    # TODO: Don't hard-code the string length
    for key in sorted(self.shortcuts):
      value = self.shortcuts[key]
      print(str.format("{0:8s} -> {1:s}", key, value),
            file=sys.stderr)
      expanded = self.getval(key)
      userval = expanded.replace(os.path.expanduser('~'), '~', 1)
      if (isinstance(value, str) and userval != value) or isinstance(value, list):
        print(str.format("              {0}", userval), file=sys.stderr)

  def expand_value(self, value):
    assert isinstance(value, str)
    if Go.root_variable_name in value:
      if not self.root_variable_name:
        raise NoRootException
      value = value.replace(Go.root_variable_name, self.chromium_root_dir)
    return os.path.expanduser(os.path.expandvars(value))

  def getval(self, shortcut):
    if shortcut in self.shortcuts:
      value = self.shortcuts[shortcut]
      if isinstance(value, str):
        return self.expand_value(value)
      try:
        return self.expand_value(value[0])
      except NoRootException:
        return self.expand_value(value[1])
    else:
      print(str.format('Unknown shortcut "{0}"', shortcut), file=sys.stderr)
      sys.exit(3)

if __name__ == '__main__':
  import doctest
  doctest.testmod()
  cwd = os.path.abspath(os.getcwd())
  g = Go(cwd)
  if len(sys.argv) == 2:
    print(str.format("{0}", g.getval(sys.argv[1])))
  else:
    g.do_print()
    sys.exit(1)
