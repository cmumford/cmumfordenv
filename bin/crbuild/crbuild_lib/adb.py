#!/usr/bin/env python3

import subprocess

class Adb(object):

  releases = {
      29: ('Q', '10'),
      28: ('Pie', '9'),
      27: ('Oreo', '8.1'),
      26: ('Oreo', '8.0'),
      25: ('Nougat', '7.1'),
      24: ('Nougat', '7.0'),
      23: ('Marshmallow', '6.0'),
      22: ('Lollipop', '5.1'),
      21: ('Lollipop', '5.0'),

      19: ('KitKat', '4.4-4.444'),
      18: ('Jelly Bean', '4.3.X'),
      17: ('Jelly Bean', '4.2.X'),
      16: ('Jelly Bean', '4.1.X'),
  }

  @staticmethod
  def __path():
    return 'adb'

  @staticmethod
  def os_release(device = None):
    cmd = [Adb.__path(), 'shell', 'getprop', 'ro.build.version.release']
    if device:
      cmd = [cmd[0]] + ['-s', device] + cmd[1:]
    for line in subprocess.check_output(cmd).splitlines():
      return int(line.strip())
    return None

  @staticmethod
  def api_level(device = None):
    cmd = [Adb.__path(), 'shell', 'getprop', 'ro.build.version.sdk']
    if device:
      cmd = [cmd[0]] + ['-s', device] + cmd[1:]
    for line in subprocess.check_output(cmd).splitlines():
      return int(line.strip())
    return None

  @staticmethod
  def cpu_abi(device = None):
    cmd = [Adb.__path(), 'shell', 'getprop', 'ro.product.cpu.abi']
    if device:
      cmd = [cmd[0]] + ['-s', device] + cmd[1:]
    for line in subprocess.check_output(cmd).splitlines():
      return line.strip().decode('utf-8')
    return None

  @staticmethod
  def get_installed_packages(device = None):
    if device:
      cmd = str.format(
          "adb -s {0} shell 'pm list packages -f' | sed -e 's/.*=//' | sort",
          device)
    else:
      cmd = "adb shell 'pm list packages -f' | sed -e 's/.*=//' | sort"

    packages = []
    for line in subprocess.check_output(cmd, shell=True).splitlines():
      packages.append(line.strip().decode('utf-8'))
    return packages

  @staticmethod
  def has_gms(device = None):
    return 'com.google.android.gms' in Adb.get_installed_packages(device)

  @staticmethod
  def api_level_to_letter(api_level):
    return Adb.releases[api_level][0][0]

  @staticmethod
  def devices():
    """Return a map of device name to type."""
    cmd = [Adb.__path(), 'devices']
    devices = {}
    for line in subprocess.check_output(cmd).splitlines():
      items = line.strip().split()
      if len(items) == 2:
        devices[items[0].decode('utf-8')] = items[1].decode('utf-8')
    return devices
