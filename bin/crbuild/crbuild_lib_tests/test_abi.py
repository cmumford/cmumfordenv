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

  def test_to_string(self):
    self.assertEqual('P', adb.Adb.api_level_to_letter(28))

if __name__ == '__main__':
    unittest.main()
