#!/usr/bin/env python3

import copy
import json
import re

class DataError(Exception):
  pass

class NotFound(Exception):
  pass

class NoDefaultRunCommand(Exception):
  pass

def remove_nulls(d):
  return {k: v for k, v in d.items() if v is not None}

class ClassJSONEncoder(json.JSONEncoder):
  def default(self, obj):
    if isinstance(obj, Target):
      return remove_nulls(obj.__dict__)
    elif isinstance(obj, TargetReference):
      return remove_nulls(obj.__dict__)
    elif isinstance(obj, EnvVar):
      return remove_nulls(obj.__dict__)
    elif isinstance(obj, RunCommand):
      return remove_nulls(obj.__dict__)
    return super(ClassJSONEncoder, self).default(obj)

class EnvVar(object):
  def __init__(self, name):
    self.name = name
    self.delim = ':'
    self.values = []

  def values_str(self):
    return self.delim.join(self.values)

  def cmd_line_str(self):
    if not self.values:
      return None
    if ' ' in self.name:
      return '"%s"="%s"' % (self.name, self.values_str())
    else:
      return '%s="%s"' % (self.name, self.values_str())

  def __repr__(self):
    return json.dumps(self.__dict__, cls=ClassJSONEncoder)

class RunCommand(object):
  '''The command and arguments when running an executable.'''
  def __init__(self):
    self.commands = []
    self.args = []
    self.env_var = None
    self.shell = False

  def cmd_line(self):
    if self.commands:
      cmd = self.commands.copy()
    else:
      cmd = []
    if self.args:
      cmd.extend(self.args)
    return cmd

  def __repr__(self):
    return json.dumps(self.__dict__, cls=ClassJSONEncoder)

class TargetReference(object):
  reg = re.compile('^OS==(.*)$')

  def __init__(self, target, condition, build_only):
    self.target = target
    self.condition = condition
    self.build_only = build_only

  def condition_met(self, options):
    if not self.condition:
      return True
    m = TargetReference.reg.match(self.condition)
    assert(m)
    if m:
      os = m.group(1).strip()
      return os == options.buildopts.target_os
    return False

  def __repr__(self):
    return json.dumps(remove_nulls(self.__dict__), cls=ClassJSONEncoder)

class Target(object):
  def __init__(self, target_name):
    self.name = target_name
    self.title = None             # The target title to display in help.
    self.upstream_targets = None  # List of TargetReference
    self.run_commands = None      # Dictionary of lists of RunCommand objects.
    self.explicit = None          # True if explicitly defined in config file.
    self.reference_self = True
    self.executable_names = None
    self.run_only = False

  def get_build_targets(self, options):
    '''Given a Target.name return an array of GN build targets.

    Will also return all dependent (upstream) targets.
    '''
    targets = set()
    if self.upstream_targets:
      for upstream_ref in self.upstream_targets:
        if upstream_ref.condition_met(options):
          targets = targets.union(
              upstream_ref.target.get_build_targets(options))
    if self.reference_self:
      targets = targets.union(set((self.name, )))

    return targets

  def __get_run_commands(self, options):
    if options.buildopts.is_asan and 'asan' in self.run_commands:
      return self.run_commands['asan']
    if options.profile and 'profile' in self.run_commands:
      return self.run_commands['profile']
    if options.run_debugger and 'debug' in self.run_commands:
      return self.run_commands['debug']
    if 'default' not in self.run_commands:
      raise NoDefaultRunCommand(
          str.format('Target {0} has no default run command', self.name))
    return self.run_commands['default']

  def get_run_commands(self, options):
    '''Return a list of commands to be executed for this Target and for the
    given options.'''

    run_commands = []
    if self.upstream_targets:
      for target_ref in self.upstream_targets:
        if target_ref.build_only:
          continue
        run_commands.extend(
            target_ref.target.get_run_commands(options))

    if not run_commands and not self.run_commands:
      # Not an error, not all targets are runnable.
      return []

    if options.gtest:
      for run_command in run_commands:
        run_command.args.append('--gtest_filter=%s' % options.gtest)

    if run_commands:
      if not self.run_commands:
        return run_commands
      try:
        # Add add the supplemental arguments to each run command.
        supplemental_run_commands = self.__get_run_commands(options)
        assert(len(supplemental_run_commands) == 1)
        # Can add supplemental args, but not a command.
        assert(supplemental_run_commands[0].args)
        assert(not supplemental_run_commands[0].commands)
        cmds = []
        for run_command in run_commands:
          cmd_copy = copy.copy(run_command)
          cmd_copy.args.extend(supplemental_run_commands[0].args)
          cmds.append(cmd_copy)
        return cmds
      except NoDefaultRunCommand:
        # No error, just no supplemental args.
        pass
    else:
      run_commands = self.__get_run_commands(options)

    return run_commands

  def __depends_on_target(self, target):
    if target is self:
      return True
    if not self.upstream_targets:
      return False
    for target_ref in self.upstream_targets:
      if target_ref.target.__depends_on_target(target):
        return True
    return False

  def add_upstream_target(self, target_ref):
    if self.__depends_on_target(target_ref.target):
      raise CustomError(str.format('Target "{0}" already depends on "{1}"',
                                   self.name, target_ref.target.name))
    if self.upstream_targets == None:
      self.upstream_targets = []
    self.upstream_targets.append(target_ref)

  def __repr__(self):
    return json.dumps(remove_nulls(self.__dict__), cls=ClassJSONEncoder)

class Configuration(object):
  def __init__(self):
    self.targets = dict()  # Dictionary of Targets

  def add_target(self, target):
    if target.name in self.targets:
      raise DataError('Target name "%s" already exists.' % target.name)
    self.targets[target.name] = target

  def get_build_targets(self, target_name, options):
    '''Given a Target.name return an array of GN build targets.

    Will also return all dependent (upstream) targets.
    '''
    for _, target in self.targets.items():
      if target_name == target.name:
        return target.get_build_targets(options)
    return set()

  def get_target(self, target_name):
    if target_name not in self.targets:
      raise NotFound(target_name)
    return self.targets[target_name]

  def get_run_commands(self, target_name, options):
    '''Given a target name return the RunCommand (execute).

    Note: This function *will not* expand variables - that is the
    responsibility of the caller.
    '''
    return self.get_target(target_name).get_run_commands(options)

  def __repr__(self):
    return json.dumps(remove_nulls(self.__dict__), cls=ClassJSONEncoder)
