#!/usr/bin/env python3

import os
import sys
import tempfile
import unittest

def GetAbsPathRelativeToThisFilesDir(rel_path):
  return os.path.abspath(os.path.join(os.path.dirname(__file__),
                         rel_path))

sys.path.append(GetAbsPathRelativeToThisFilesDir('..'))

from crbuild_lib import (build_settings)

class TestBuildSettings(unittest.TestCase):

  def test_equality(self):
    one = build_settings.BuildSettings('master', 'linux')
    two = build_settings.BuildSettings('master', 'linux')
    self.assertEqual(one, two)

  def test_inequality(self):
    one = build_settings.BuildSettings('master', 'linux')
    two = build_settings.BuildSettings('master', 'linux')
    two.goma_dir = 'non/default/dir'
    self.assertNotEqual(one, two)

  def test_write_read(self):
    settings = build_settings.BuildSettings('master', 'linux')
    tmp = tempfile.NamedTemporaryFile(delete=True)
    settings.write(tmp)
    tmp.flush()

    with open(tmp.name, 'rb') as f:
      read_settings = build_settings.BuildSettings.read(f)
      self.assertEqual(settings.goma_dir, read_settings.goma_dir)

if __name__ == '__main__':
    unittest.main()
