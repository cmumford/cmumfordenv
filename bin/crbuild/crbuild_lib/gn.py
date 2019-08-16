#!/usr/bin/env python3

import os
import re
import subprocess

from .env import Env
from .command import Cmd

class GN(object):
  '''This module is for interacting with GN.'''

  def __init__(self, environ, varexp):
    self.__env = environ
    self.__variable_expander = varexp

  def args_path(self):
    return os.path.join(self.__variable_expander.get_build_dir(), 'args.gn')

  @staticmethod
  def __read_file(f):
    '''Read all the arguments from an open file returning a dictionary
    containing the file contents.'''
    args = {}
    for line in f.readlines():
      line = line.strip()
      if re.match('^#', line):
        continue
      vals = line.strip().split('=')
      if len(vals) == 2:
        args[vals[0].strip()] = vals[1].strip()
    return args

  def get_args(self, all_args=False):
    '''Read all the options from an open file and return a dictionary containing
    the file contents.

    if |all_args| is true then will also return all default GN settings.'''
    if all_args:
      args = {}
      cmd = ['gn', 'args', self.__variable_expander.get_build_dir(),
             '--list', '--short']
      for line in subprocess.check_output(cmd).splitlines():
        vals = line.strip().split(b'=')
        if len(vals) == 2:
          args[vals[0].strip()] = vals[1].strip()
      return args
    with open(self.args_path(), 'r') as f:
      return GN.__read_file(f)

  def build_args(self, options):
    '''Given a BuildSettings instance populate a dictionary containing all
    the GN arguments.'''
    build_settings = options.buildopts
    args = {
      'dcheck_always_on': str(build_settings.dcheck_always_on).lower()
    }
    if build_settings.is_asan:
      args['is_asan'] = str(build_settings.is_asan).lower()
    args['is_chrome_branded'] = str(build_settings.is_chrome_branded).lower()
    args['is_clang'] = str(build_settings.use_clang).lower()
    args['is_component_build'] = str(build_settings.is_component_build).lower()
    args['is_debug'] = str(build_settings.is_debug).lower()
    if build_settings.is_lsan:
      args['is_lsan'] = str(build_settings.is_lsan).lower()
    if build_settings.is_msan:
      args['is_msan'] = str(build_settings.is_msan).lower()
    args['is_official_build'] = str(build_settings.is_official_build).lower()
    if build_settings.is_tsan:
      args['is_tsan'] = str(build_settings.is_tsan).lower()
    args['target_os'] = '"%s"' % build_settings.target_os
    if build_settings.target_cpu:
      args['target_cpu'] = '"%s"' % build_settings.target_cpu
    args['use_goma'] = str(build_settings.use_goma).lower()
    if build_settings.use_libfuzzer:
      args['use_libfuzzer'] = str(build_settings.use_libfuzzer).lower()
    if self.__env.build_platform == 'win':
      args['is_win_fastlink'] = str(build_settings.use_goma).lower()
      args['symbol_level'] = '2' if build_settings.is_official_build else '1'
    if build_settings.enable_profiling:
      args['enable_profiling'] = 'true'
    if build_settings.enable_cros_assistant:
      args['enable_cros_assistant'] = 'true'
    if build_settings.enable_callgrind:
      args['enable_callgrind'] = 'true'
    if build_settings.use_goma:
      args['goma_dir'] = '"%s"' % build_settings.goma_dir
    if build_settings.is_asan or build_settings.is_tsan:
      args['symbol_level'] = '1'
      if not build_settings.is_tsan:
        args['enable_full_stack_frames_for_profiling'] = 'true'
      args['strip_absolute_paths_from_debug_symbols'] = 'true'
    if (build_settings.use_libfuzzer or
        build_settings.is_asan or
        build_settings.is_tsan or
        build_settings.is_tsan):
      args['enable_nacl'] = 'false'
    # All of a sudden all nacl builds started failing, so just disabled for
    # all platforms (5/4/2019).
    args['enable_nacl'] = 'false'
    if build_settings.target_os == 'chromeos' and \
        self.__env.api_keys_path and \
        os.path.exists(self.__env.api_keys_path):
      with open(self.__env.api_keys_path) as f:
        supplimental_args = GN.__read_file(f)
      for k in supplimental_args:
        args[k] = supplimental_args[k]
    if build_settings.is_cfi and not build_settings.is_official_build:
      args['is_cfi'] = 'true'
      args['use_cfi_cast'] = 'true'
      args['use_cfi_diag'] = 'true'
      args['use_thin_lto'] = 'true'
      # args['strip_absolute_paths_from_debug_symbols'] = 'true'
    # Setting android_sdk_release is probably unnecessary.
    if build_settings.android_sdk_release:
      args['android_sdk_release'] = \
          str.format('"{0}"', build_settings.android_sdk_release)
    if build_settings.system_webview_package_name:
      args['system_webview_package_name'] = \
          '"%s"' % build_settings.system_webview_package_name
    if build_settings.use_signing_keys:
      args['use_signing_keys'] = 'true'
    if build_settings.use_rtti != None:
      args['use_rtti'] = str(build_settings.use_rtti).lower()
    if build_settings.enable_ipc_fuzzer != None:
      args['enable_ipc_fuzzer'] = str(build_settings.enable_ipc_fuzzer).lower()
    if build_settings.v8_enable_verify_heap != None:
      args['v8_enable_verify_heap'] = \
          str(build_settings.v8_enable_verify_heap).lower()
    return args

  def put_args(self, args):
    args_fname = self.args_path()
    if not os.path.exists(args_fname):
      open(args_fname, 'a').close() # Create empty file
    existing_args = self.get_args()
    existing_args.update(args)
    with open(self.args_path(), 'w') as f:
      print('# Build arguments go here. Examples:', file=f)
      print('#   is_component_build = true', file=f)
      print('#   is_debug = false', file=f)
      print('# See "gn args <out_dir> --list" for available build arguments.',
            file=f)
      print('', file=f)
      for arg in sorted(args):
        print("%s = %s" % (arg, args[arg]), file=f)

  def gen(self, options):
    cmd = ['gn', 'gen', self.__variable_expander.get_build_dir()]
    if options.print_cmds:
      Cmd.print_ok(cmd, env_vars=None, add_quotes=True)
    if options.noop:
      return
    # If build_dir doesn't exist then Windows fails with default shell=False
    shell = self.__env.build_platform == 'win'
    subprocess.check_call(cmd, shell=shell)
