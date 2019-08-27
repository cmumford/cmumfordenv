#!/usr/bin/env python3

import multiprocessing
import platform

from .adb import Adb

class Env(object):
  '''Attributes of the environment (host, location, etc.).'''

  def __init__(self, src_root_dir, gclient_path, api_keys_path=None):
    """Constructor.

    gclient_path: full path to .gclient file.
    api_keys_path: full path to api_keys.txt file or None.
    """
    self.src_root_dir = src_root_dir
    self.gclient_path = gclient_path
    self.api_keys_path = api_keys_path
    self.num_cpus = multiprocessing.cpu_count()
    self.build_platform = Env.__get_build_platform()
    # None means the info hasn't been retrieved (using Adb). This allows tests
    # to set it, and if not set Adb will be used.
    self.__devices = None

  @property
  def android_devices(self):
    if self.__devices == None:
      self.__devices = Adb.get_device_info()
    return self.__devices

  @android_devices.setter
  def android_devices(self, info):
    self.__devices = info

  @staticmethod
  def __get_build_platform():
    '''Return the name of the platform on which the build is running.

    This uses the same names used by GN - not Python.
    '''
    p = platform.system()
    if p == 'Windows':
      return 'win'
    if p == 'Linux':
      return 'linux'
    if p == 'Darwin':
      return 'mac'
    raise Exception('Unknown platform: ' + p)
