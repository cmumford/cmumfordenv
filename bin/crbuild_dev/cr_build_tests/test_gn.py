#!/usr/bin/env python3

import os
import sys
import unittest

def GetAbsPathRelativeToThisFileDir(rel_path):
  return os.path.abspath(os.path.join(os.path.dirname(__file__),
                         rel_path))

sys.path.append(GetAbsPathRelativeToThisFileDir('..'))

from cr_build.env import Env
from cr_build.gn import GN
from cr_build.models import Configuration
from cr_build.options import Options
from cr_build.variable_expander import VariableExpander

class TestGN(unittest.TestCase):

  def __create_options(self):
    return Options(
        Env(os.path.dirname(__file__),
            GetAbsPathRelativeToThisFileDir('gclient.txt'),
            GetAbsPathRelativeToThisFileDir('api_keys.txt')),
        Configuration())

  def test_cpu_count(self):
    opts = self.__create_options()
    exp = VariableExpander(opts)
    gn = GN(opts.env, exp)
    gn.get_args()

  def test_api_keys(self):
    opts = self.__create_options()
    # Linux doesn't add the API keys.
    opts.buildopts.target_os = 'linux'
    exp = VariableExpander(opts)
    gn = GN(opts.env, exp)
    args_dict = gn.build_args(opts)
    self.assertFalse('the_api_key' in args_dict)

    # Chrome OS *does* add the API keys.
    opts.buildopts.target_os = 'chromeos'
    exp = VariableExpander(opts)
    gn = GN(opts.env, exp)
    args_dict = gn.build_args(opts)
    self.assertEqual('"the_api_key"', args_dict['google_api_key'])

if __name__ == '__main__':
    unittest.main()
