#!/usr/bin/env python3

import os
import sys
import unittest

def GetAbsPathRelativeToThisFilesDir(rel_path):
  return os.path.abspath(os.path.join(os.path.dirname(__file__),
                         rel_path))

sys.path.append(GetAbsPathRelativeToThisFilesDir('..'))

from crbuild_lib import (adb)

class TestAdb(unittest.TestCase):

  def test_default_constructor(self):
    device_info = adb.DeviceInfo('name', 27, 'x86', [])
    self.assertEqual('name', device_info.name)
    self.assertEqual(27, device_info.api_level)
    self.assertEqual('x86', device_info.cpu_abi)
    self.assertListEqual([], device_info.installed_packages)

  def test_cpu(self):
    device_info = adb.DeviceInfo('name', 27, 'arm64-v8', [])
    self.assertEqual('arm64', device_info.cpu())

if __name__ == '__main__':
    unittest.main()
