#!/usr/bin/env python3

import copy
import os
import subprocess
import sys

from .command import Cmd
from .env import Env
from .gn import GN
from .models import Configuration
from .options import Options
from .stream_reader import StreamReader
from .variable_expander import VariableExpander

class Builder(object):
  def __init__(self, options, config):
    self.options = options
    self.config = config
    self.variable_expander = VariableExpander(options)
    self.__gn = GN(options.env, self.variable_expander)
    self.__set_env_vars()

  # Linking on Windows can sometimes fail with this error:
  #
  #   LNK1318: Unexpected PDB error; OK (0)
  #
  # This is caused by the Microsoft PDB Server running out of virtual address
  # space. As the PDB server will be automatically started when necessary
  # Killing this service fixes this problem.
  def __kill_pdb_server(self):
    assert self.options.buildopts.target_os == 'win'
    cmd = "taskkill /F /im mspdbsrv.exe"
    if self.options.print_cmds:
      Cmd.print_ok(cmd, env_vars=None, add_quotes=True)
    if not self.options.noop:
      os.system(cmd)

  @staticmethod
  def __prepend_to_path(path):
    os.environ['PATH'] = "%s%s%s" % (path, os.pathsep, os.environ['PATH'])

  @staticmethod
  def print_all_env_vars():
    for key in sorted(os.environ):
      print("%s=%s" % (key, os.environ[key]))

  def __set_env_vars(self):
    # Copy so as to not modify options
    gyp_defines = copy.copy(self.options.buildopts.gyp_defines)
    os.environ['GYP_GENERATORS'] = self.options.buildopts.gyp_generators
    if self.options.buildopts.use_clang:
      os.environ['CC'] = 'clang'
      os.environ['CXX'] = 'clang++'
      os.environ['builddir_name'] = 'llvm'
      assert os.path.exists(self.options.llvm_path)
      Builder.__prepend_to_path(self.options.llvm_path)
      gyp_defines.add('clang=1')
    if self.options.buildopts.valgrind:
      gyp_defines.add('build_for_tool=memcheck')
    # Must be prepended to PATH last
    if self.options.buildopts.use_goma:
      Builder.__prepend_to_path(self.options.buildopts.goma_dir)
    if 'GYP_DEFINES' in os.environ:
      for prev_val in os.environ['GYP_DEFINES'].split():
        gyp_defines.add(prev_val)
    if self.options.buildopts.use_goma:
        gyp_defines.add('win_z7=0')
    os.environ['GYP_DEFINES'] = ' '.join(gyp_defines)

    if self.options.verbosity > 0:
      if self.options.verbosity > 2:
        Builder.print_all_env_vars()
      else:
        print("Target OS: %s" % self.options.buildopts.target_os)
        print("Host OS: %s" % self.options.env.build_platform)
        print("Official: %s" % str(self.options.buildopts.is_official_build))
        print("GYP_DEFINES: %s" % os.environ['GYP_DEFINES'])
        print("GYP_GENERATORS: %s" % os.environ['GYP_GENERATORS'])
        print("PATH: %s" % os.environ['PATH'])
      print("Using %s %s goma" %  ('clang' if self.options.buildopts.use_clang else 'gcc',
                                   'with' if self.options.buildopts.use_goma else
                                   'without'))
    if len(self.options.buildopts.gyp_generator_flags):
      os.environ['GYP_GENERATOR_FLAGS'] = ' '.join(self.options.buildopts.gyp_generator_flags)
    if self.options.profile:
      os.environ['CPUPROFILE'] = self.options.profile_file

  # https://code.google.com/p/syzygy/wiki/SyzyASanBug
  def __instrument_SyzyASan(self, build_dir):
    syzygy_exes = os.path.join('third_party', 'syzygy', 'binaries', 'exe')
    instrument_exe = os.path.join(syzygy_exes, 'instrument.exe')
    input_chrome_dll = os.path.join(build_dir, 'chrome.dll')
    output_chrome_dll = os.path.join(build_dir, 'chrome_syzygy.dll')
    cmd = [instrument_exe,
           '--mode=asan',
           '--overwrite',
           '--input-image=%s' % input_chrome_dll,
           '--output-image=%s' % output_chrome_dll,
           '--debug-friendly']
    if self.options.print_cmds:
      Cmd.print_ok(cmd, env_vars=None, add_quotes=True)
    if not self.options.noop:
      if os.path.exists(output_chrome_dll):
        in_time = os.path.getmtime(input_chrome_dll)
        out_time = os.path.getmtime(output_chrome_dll)
        if out_time > in_time:
          print('No need to re Syzy chrome')
          return
        os.remove(output_chrome_dll)
      subprocess.check_call(cmd)
      shutil.copyfile(os.path.join(syzygy_exes, 'syzyasan_rtl.dll'),
                      os.path.join(build_dir, 'syzyasan_rtl.dll'))

  def __delete_dir(self, dir_path):
    if os.path.exists(dir_path):
      if self.options.print_cmds:
        Cmd.print_ok("Deleting %s" % dir_path, env_vars=None, add_quotes=True)
      if not self.options.noop:
        shutil.rmtree(dir_path)

  def clobber(self):
    print('Deleting intermediate files...')
    if os.path.exists(self.options.gyp_state_path):
      os.remove(self.options.gyp_state_path)
    self.__delete_dir(self.__build_dir())

  def __is_run_only(self, target_name):
    target = self.config.get_target(target_name)
    return target.run_only

  def __build(self, target_names):
    '''Build the specified GN target names.'''
    build_dir = self.__build_dir()
    cmd = ['ninja', '-C', build_dir, '-l', '40']
    if self.options.noop:
      cmd.insert(1, '-n')
    if self.options.verbosity > 1:
      cmd.insert(1, '-v')
    if self.options.buildopts.use_goma:
      if self.options.buildopts.target_os == 'mac':
        cmd[1:1] = ['-j', '100']
      else:
        cmd[1:1] = ['-j', '4096']
    if self.options.keep_going:
      cmd[1:1] = ['-k', '50000']
    if self.options.buildopts.is_asan:
      platform_dir = self.__build_dir()
      os.environ['CHROME_DEVEL_SANDBOX'] = os.path.join(platform_dir,
                                                        'chrome_sandbox')
    target_names_to_build = list(
        filter(lambda name: not self.__is_run_only(name), target_names))
    if not target_names_to_build:
      return []
    print('Building %s...' % target_names_to_build)
    cmd.extend(target_names_to_build)
    Cmd.print_ok(cmd, env_vars=None, add_quotes=True)
    try:
      subprocess.check_call(cmd)
      if (self.options.buildopts.is_asan and
          self.options.buildopts.target_os == 'win'):
        self.__instrument_SyzyASan(build_dir)
      return []
    except subprocess.CalledProcessError as e:
      return [e]

  def __run(self, run_command):
    try:
      cmd = self.variable_expander.expand_variables(run_command.cmd_line())
      if self.options.run_args:
        cmd.extend(self.options.run_args)
      if self.options.print_cmds:
        add_quotes = not run_command.shell
        if run_command.env_var:
          Cmd.print_ok(cmd, env_vars=run_command.env_var.cmd_line_str(),
                       add_quotes=add_quotes)
        else:
          Cmd.print_ok(cmd, env_vars=None, add_quotes=add_quotes)

      symbolize = self.options.buildopts.is_asan or \
          self.options.buildopts.is_tsan
      my_env = os.environ.copy()
      if run_command.env_var:
        my_env[run_command.env_var.name] = run_command.env_var.values_str()
      p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, shell=run_command.shell)
      stderr_symbolizer = StreamReader(p.stderr, sys.stderr,
                                       self.options.env.src_root_dir,
                                       symbolize)
      stdout_symbolizer = StreamReader(p.stdout, sys.stdout,
                                       self.options.env.src_root_dir,
                                       symbolize)
      p.wait()
      stderr_symbolizer.stop()
      stdout_symbolizer.stop()
      if p.returncode:
        raise subprocess.CalledProcessError(returncode=p.returncode, cmd=cmd)

      return []
    except subprocess.CalledProcessError as e:
      return [e]

  def __build_dir(self):
    return self.variable_expander.get_build_dir()

  def __need_to_re_gn(self):
    try:
      existing_args = self.__gn.get_args()
      preferred_args = self.__gn.build_args(self.options)
      return existing_args != preferred_args
    except IOError:
      # File not found (likely).
      return True

  def build(self):
    if self.options.buildopts.target_os == 'win':
      self.__kill_pdb_server()

    if self.options.clobber:
      self.clobber()

    if self.__need_to_re_gn():
      build_dir = self.__build_dir()
      if not os.path.isdir(build_dir):
        # This creates the directory.
        self.__gn.gen(self.options)
      self.__gn.put_args(self.__gn.build_args(self.options))
      self.__gn.gen(self.options)

    exceptions = []
    # TODO: Support multiple build targets and none (default) target.
    build_targets = self.config.get_build_targets(
        self.options.active_targets[0], self.options)
    if build_targets:
      exceptions.extend(self.__build(build_targets))
      if exceptions:
        return exceptions

    if not self.options.run_targets:
      return exceptions

    # Now run all executables
    for target_name in self.options.active_targets:
      for run_command in self.config.get_run_commands(target_name, self.options):
        exceptions.extend(self.__run(run_command))
      if self.options.profile:
        # TODO: Re-add support for profiling message.
        pass
    return exceptions
