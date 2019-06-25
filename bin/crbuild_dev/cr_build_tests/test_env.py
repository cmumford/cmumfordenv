#!/usr/bin/env python3

import os
import sys
import unittest

def GetAbsPathRelativeToThisFileDir(rel_path):
  return os.path.abspath(os.path.join(os.path.dirname(__file__),
                         rel_path))

sys.path.append(GetAbsPathRelativeToThisFileDir('..'))

from cr_build import (env)

class TestEnv(unittest.TestCase):

  def test_cpu_count(self):
    environ = env.Env(os.getcwd(),
                      GetAbsPathRelativeToThisFileDir('gclient.txt'))
    self.assertGreater(environ.num_cpus, 0)

if __name__ == '__main__':
    unittest.main()
