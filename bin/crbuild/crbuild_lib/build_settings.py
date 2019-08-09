#!/usr/bin/env python3

import json
import os
import pickle
from . import build_settings

class ClassJSONEncoder(json.JSONEncoder):
  def default(self, obj):
    if isinstance(obj, BuildSettings):
      return __remove_nulls(obj.__dict__)
    return super(ClassJSONEncoder, self).default(obj)

class BuildSettings(object):
  '''The settings used to build a set of Chromium targets.

  Think of this as a superset of those written to GN's args.gn file. Most
  of the setting values are duplicates of those in args.gn, but a few
  are specific to crbuild.
  '''

  def __init__(self, branch, target_os):
    self.branch = branch
    self.dcheck_always_on = True
    self.enable_callgrind = False
    self.enable_cros_assistant = False
    self.enable_ipc_fuzzer = False
    self.enable_profiling = False
    self.goma_dir = None
    self.gyp_defines = set()
    self.gyp_generator_flags = set()
    self.gyp_generators = 'ninja'
    self.is_asan = False
    self.is_cfi = False
    self.is_chrome_branded = False
    self.is_component_build = True
    self.is_debug = True
    self.is_lsan = False
    self.is_msan = False
    self.is_official_build = False
    self.is_tsan = False
    self.target_cpu = None
    self.use_clang = True
    self.use_goma = True
    self.use_libfuzzer = False
    self.use_rtti = False
    self.v8_enable_verify_heap = False
    self.valgrind = False
    self.__set_target_os(target_os)

  @property
  def target_os(self):
    return self.__target_os

  def __set_target_os(self, target_os):
    self.__target_os = target_os
    if self.__target_os == 'android':
      # https://sites.google.com/a/google.com/clank/engineering/sdk-build/working-with-monochrome
      self.android_sdk_release = 'p'
      self.use_signing_keys = True
      self.system_webview_package_name = 'com.google.android.webview'
      if not self.target_cpu:
        self.target_cpu = 'x86'
      self.use_rtti = None
      return
    self.android_sdk_release = None
    self.use_signing_keys = False
    self.system_webview_package_name = None
    self.target_cpu = None

  @target_os.setter
  def target_os(self, target_os):
    self.__set_target_os(target_os)

  def write(self, f):
    '''Serialize this object to the given file.

    Note: The file is *not* args.gn, but some other file that will contain
    a fully serialized instance of BuildSettings.
    '''
    pickle.dump(self, f)

  @staticmethod
  def read(f):
    '''Deserialize a BuildSettings object from the given file.

    Note: The file is *not* args.gn, but some other file that contains
    a fully serialized instance of BuildSettings.
    '''
    return pickle.load(f)

  def __ne__(self, other):
    if self.dcheck_always_on != other.dcheck_always_on:
      return True
    if self.is_asan != other.is_asan:
      return True
    if self.is_chrome_branded != other.is_chrome_branded:
      return True
    if self.is_component_build != other.is_component_build:
      return True
    if self.is_debug != other.is_debug:
      return True
    if self.enable_callgrind != other.enable_callgrind:
      return True
    if self.enable_profiling != other.enable_profiling:
      return True
    if self.is_cfi != other.is_cfi:
      return True
    if self.is_lsan != other.is_lsan:
      return True
    if self.is_msan != other.is_msan:
      return True
    if self.is_official_build != other.is_official_build:
      return True
    if self.is_tsan != other.is_tsan:
      return True
    if self.gyp_generator_flags != other.gyp_generator_flags:
      return True
    if self.gyp_defines != other.gyp_defines:
      return True
    if self.gyp_generators != other.gyp_generators:
      return True
    if self.use_clang != other.use_clang:
      return True
    if self.use_goma != other.use_goma:
      return True
    if self.goma_dir != other.goma_dir:
      return True
    if self.use_rtti != other.use_rtti:
      return True
    if self.use_libfuzzer != other.use_libfuzzer:
      return True
    if self.target_os != other.target_os:
      return True
    if self.target_cpu != other.target_cpu:
      return True
    if self.valgrind != other.valgrind:
      return True
    if self.v8_enable_verify_heap != other.v8_enable_verify_heap:
      return True
    if self.enable_ipc_fuzzer != other.enable_ipc_fuzzer:
      return True
    if hasattr(other, 'branch'):
      other_branch = other.branch
    else:
      other_branch = ''
    if hasattr(self, 'branch'):
      self_branch = self.branch
    else:
      self_branch = ''
    if self_branch != other_branch:
      return True
    return False

  def __eq__(self, other):
    return not self.__ne__(other)

  def __repr__(self):
    return json.dumps(__remove_nulls(self.__dict__), cls=ClassJSONEncoder)
