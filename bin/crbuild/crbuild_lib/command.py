#!/usr/bin/env python3

import platform
import sys

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

class Cmd(object):
  '''Simple wrapper for executing and printing commands.'''


  @staticmethod
  def __item_to_string(item, quote_flags):
    assert(isinstance(item, str))
    vals = item.split('=')
    if len(vals) > 2:
      raise Exception('Too many equals: ' + item)
    if len(vals) == 2:
      return '%s=%s' % (Cmd.__item_to_string(vals[0], False),
                        Cmd.__item_to_string(vals[1], True))
    if ' ' in item or '*' in item or (quote_flags and '--' in item):
      return '"%s"' % item
    return item

  @staticmethod
  def list_to_string(cmd):
    assert(isinstance(cmd, list))
    return ' '.join([Cmd.__item_to_string(i, False) for i in cmd])

  @staticmethod
  def __print(cmd, env_vars, color):
    '''Print the command to stdout in the specified color (if able to).

    May supply a string of list of strings.'''
    if (isinstance(cmd, list)):
      str_cmd = Cmd.list_to_string(cmd)
    else:
      assert isinstance(cmd, str) or isinstance(cmd, unicode)
      str_cmd = cmd
    if env_vars:
      str_cmd = env_vars + ' ' + str_cmd
    if Cmd.__can_output_color():
      print("%s%s%s" % (color, str_cmd, bcolors.ENDC))
    else:
      print(str_cmd)

  @staticmethod
  def print_ok(cmd, env_vars):
    '''Print the OK command to stdout.

    May supply a string of list of strings.'''
    Cmd.__print(cmd, env_vars, bcolors.OKBLUE)

  @staticmethod
  def print_error(cmd, env_vars):
    '''Print the error command to stdout.

    May supply a string of list of strings.
    |env_vars| is a printable string that would appear on the command-line
    such as 'FOO="bar" BAZ="45"'.
    '''
    if isinstance(cmd, list):
      cmd = ['Failed: '] + cmd
    else:
      cmd = 'Failed: ' + cmd
    Cmd.__print(cmd, env_vars, bcolors.FAIL)

  @staticmethod
  def __can_output_color():
    if platform.system() == 'Windows':
      return False
    else:
      return sys.stdout.isatty()
