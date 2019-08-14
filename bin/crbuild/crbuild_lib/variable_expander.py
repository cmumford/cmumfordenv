#!/usr/bin/env python3

import re
import os

class UnknownVariable(Exception):
  pass

class VariableExpander(object):
  var_re = re.compile(r'\${([^}]+)}')

  def __init__(self, options):
    self.options = options

  def __get_base_build_dir(self):
    '''Return the relative path to the build dir - e.g. out/Debug.'''
    buildopts = self.options.buildopts
    dir_name = 'Debug' if buildopts.is_debug else 'Release'
    if buildopts.is_asan:
      dir_name += '-asan'
    elif buildopts.is_tsan:
      dir_name += '-tsan'
    elif buildopts.is_lsan:
      dir_name += '-lsan'
    elif buildopts.is_msan:
      dir_name += '-msan'
    if buildopts.target_os != self.options.gclient.default_target_os:
      dir_name += '-%s' % buildopts.target_os
    if buildopts.is_official_build:
      dir_name = 'Official-' + dir_name
    if buildopts.target_cpu:
      dir_name += '-' + buildopts.target_cpu
    return dir_name

  def get_build_dir(self):
      '''Return the full path to the build dir - e.g. src/dir/out/Debug.'''
      return os.path.join(self.options.out_dir, self.__get_base_build_dir())

  def get_value(self, variable_name):
    '''Given a variable name return the variable value.

    The returned value will be either a string, or list of strings.

    Raise UnknownVariable exception for unknown variable name.'''
    if variable_name == 'out':
      return self.options.out_dir
    if variable_name == 'Build_type':
      return 'Debug' if self.options.buildopts.is_debug else 'Release'
    if variable_name == 'build_type':
      return 'debug' if self.options.buildopts.is_debug else 'release'
    if variable_name == 'jobs':
      return str(self.options.jobs)
    if variable_name == 'testjobs':
      return str(self.options.test_jobs)
    if variable_name == 'out_dir':
      return self.options.out_dir
    if variable_name == 'Build_dir':
      return self.get_build_dir()
    if variable_name == 'root_dir':
      return self.options.env.src_root_dir
    if variable_name == 'layout_dir':
      return self.options.layout_dir
    if variable_name == 'HOME':
      return os.path.expanduser('~')
    if variable_name == 'xvfb':
      if self.options.env.build_platform == 'linux':
        return ['python', 'testing/xvfb.py']
      else:
        return None
    raise UnknownVariable(variable_name)

  def expand_variables(self, value):
    '''Expand all variables contained within the supplied |value|.

    |value| can be a string or a list of strings.
    '''
    if isinstance(value, str):
      m = VariableExpander.var_re.search(value)
      while m:
        val = self.get_value(m.group(1))
        if isinstance(val, str):
          value = re.sub(VariableExpander.var_re, val, value, count=1)
        elif val is None:
          return None
        elif isinstance(val, list):
          # We can't handle a string like "${xvfb} foo" because that would
          # expand to "['python', 'testing/xvfb.py'] foo", nor is it correct
          # to expand ${xvfb} to "python testing/xvfb.py". This asserts that
          # the input is not a compound statement.
          assert(value == '${xvfb}')
          return val
        m = VariableExpander.var_re.search(value)
      return value
    assert(isinstance(value, list))
    expanded = []
    for item in value:
      e = self.expand_variables(item)
      if e is None:
        continue
      if isinstance(e, list):
        expanded.extend(e)
      else:
        expanded.append(e)
    return expanded

