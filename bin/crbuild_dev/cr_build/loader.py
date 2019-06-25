#!/usr/bin/env python3

import copy
import sys
import yaml

from .models import (Configuration, EnvVar, RunCommand, Target, TargetReference)

class LoadError(Exception):
  pass

class ConfigReader(object):
  @staticmethod
  def __parse_target_ref(config, target_ref_data):
    """Parse a dependent target and return a TargetReference which will
    reference an existing (or newly created) Target.

    target_ref_data can either be a string, or an object.
    """
    condition = None
    build_only = False
    if isinstance(target_ref_data, str):
      target_name = target_ref_data
    else:
      assert(len(target_ref_data) == 1)
      target_name = list(target_ref_data.keys())[0]
      if 'condition' in target_ref_data[target_name]:
        condition = target_ref_data[target_name]['condition']
      if 'build_only' in target_ref_data[target_name]:
        build_only = True

    if target_name in config.targets:
      target = config.targets[target_name]
    else:
      target = Target(target_name)
      target.explicit = False
      config.add_target(target)

    return TargetReference(target, condition, build_only)

  @staticmethod
  def __parse_run_command(config):
    run_command = RunCommand()
    if 'cmd' in config:
      if isinstance(config['cmd'], str):
        run_command.commands = [config['cmd']]
      else:
        run_command.commands = config['cmd']
    if 'args' in config:
      if isinstance(config['args'], str):
        run_command.args = [config['args']]
      else:
        run_command.args = config['args']
    if 'env' in config:
      e = config['env']
      assert(isinstance(e, dict))
      if 'name' not in e:
        raise Exception('Missing env name.')
      if 'value' not in e:
        raise Exception('Missing env value.')
      run_command.env_var = EnvVar(e['name'])
      if 'delim' in e:
        assert(isinstance(e['delim'], str))
        run_command.env_var.delim = e['delim']
      if isinstance(e['value'], str):
        run_command.env_var.values = [e['value']]
      else:
        run_command.env_var.values = e['value']
    return run_command

  def __parse_run_commands(config, target_config_data):
    run_commands = dict()

    for command_name in target_config_data.keys():
      assert(command_name not in run_commands)

      config = target_config_data[command_name]
      if not config:
        raise LoadError('Cannot find config "%s".' % command_name)
      if isinstance(config, list):
        run_commands[command_name] = [ConfigReader.__parse_run_command(c)
                                      for c in config]
      elif isinstance(config, dict):
        run_commands[command_name] = [ConfigReader.__parse_run_command(config)]
      else:
        raise Exception('Incorrect type')

    return run_commands

  def __add_upstream_target(config, target, upstream_target_name):
    if target.name == upstream_target_name or \
      upstream_target_name == '${self}':
      target.reference_self = True
    else:
      target.add_upstream_target(
          ConfigReader.__parse_target_ref(config, upstream_target_name))

  @staticmethod
  def __replace_executable_name(run_command, executable_name):
    cmds = run_command.commands.copy()
    run_command.commands = [cmd.replace('${executable_name}', executable_name)
                            for cmd in cmds]
    args = run_command.args.copy()
    run_command.args = [arg.replace('${executable_name}', executable_name)
                        for arg in args]

  def read(self, file_path):
    config = Configuration()
    with open(file_path, 'r') as stream:
      yml = yaml.safe_load(stream)
      for target_name in yml:
        target_params = yml[target_name]
        executable_names = None
        add_self_target = False
        if 'executable_names' in target_params:
          executable_names = target_params['executable_names']

        target = Target(target_name)
        if not executable_names:
          config.add_target(target)
        target.explicit = True
        if 'title' in target_params:
          target.title = target_params['title']

        if 'targets' in target_params:
          target.reference_self = False
          target_names = target_params['targets']
          if isinstance(target_names, str):
            if executable_names and target_names == '${self}':
              # Parsing a Target template for multiple executables. Add this
              # upstream target when the template is expanded below.
              add_self_target = True
            else:
              ConfigReader.__add_upstream_target(config, target, target_names)
          else:
            for up_target_name in target_names:
              if executable_names and up_target_name == '${self}':
                # See comment above.
                add_self_target = True
              else:
                ConfigReader.__add_upstream_target(config, target,
                                                   up_target_name)

        if 'configs' in target_params:
          target.run_commands = ConfigReader.__parse_run_commands(
              config, target_params['configs'])
          if not target.run_commands:
            raise Exception(
                str.format('Target {0} has configs section with no configs',
                           target_name))

        if add_self_target:
          target.reference_self = True

        if executable_names:
          for executable_name in executable_names:
            exe_target = copy.deepcopy(target)
            exe_target.name = executable_name
            exe_target.explicit = False
            for _, run_commands in exe_target.run_commands.items():
              for run_command in run_commands:
                ConfigReader.__replace_executable_name(run_command,
                                                       exe_target.name)
            config.add_target(exe_target)

    return config
