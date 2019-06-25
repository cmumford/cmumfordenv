#!/usr/bin/env python3

import os
import sys
import unittest

def GetAbsPathRelativeToThisFilesDir(rel_path):
  return os.path.abspath(os.path.join(os.path.dirname(__file__),
                         rel_path))

sys.path.append(GetAbsPathRelativeToThisFilesDir('..'))

from cr_build import (loader)

class TestLoader(unittest.TestCase):

  def test_loading_no_error(self):
    reader = loader.ConfigReader()
    reader.read('test_config.yml')

if __name__ == '__main__':
    unittest.main()
