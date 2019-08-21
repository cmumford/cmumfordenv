#!/usr/bin/env python3

import os
import sys
import tempfile
import unittest

def GetAbsPathRelativeToThisFileDir(rel_path):
  return os.path.abspath(os.path.join(os.path.dirname(__file__),
                         rel_path))

sys.path.append(GetAbsPathRelativeToThisFileDir('..'))

from crbuild_lib import (env, models, options, variable_expander)

class TestVariableExpander(unittest.TestCase):

  def __create_opts(self, build_platform='linux'):
    environ = env.Env(os.getcwd(),
                      GetAbsPathRelativeToThisFileDir('gclient.txt'))
    environ.build_platform = build_platform
    return options.Options(environ, models.Configuration())

  def test_default_options(self):
    opts = self.__create_opts()
    exp = variable_expander.VariableExpander(opts)
    self.assertEqual(exp.get_value('out'), 'out')
    self.assertEqual(exp.get_value('Build_type'), 'Debug')
    self.assertEqual(exp.get_value('build_type'), 'debug')
    self.assertGreater(exp.get_value('jobs'), '0')
    self.assertGreater(exp.get_value('testjobs'), '0n')
    self.assertEqual(exp.get_value('out_dir'), 'out')
    build_dir = exp.get_value('Build_dir')
    self.assertEqual(os.path.basename(build_dir), 'Debug')
    self.assertEqual(exp.get_value('root_dir'), opts.env.src_root_dir)
    self.assertEqual(exp.get_value('layout_dir'), opts.layout_dir)
    self.assertEqual(exp.get_value('HOME'), os.path.expanduser('~'))
    self.assertEqual(exp.get_value('android_device'), None)
    self.assertEqual(exp.get_value('run_args'), None)

  def test_build_dir(self):
    opts = self.__create_opts()
    exp = variable_expander.VariableExpander(opts)

    # The build platform and target OS are the same so we don't expect
    # to see the OS in the directory name.
    opts.buildopts.target_os = 'linux'
    self.assertEqual(os.path.basename(exp.get_value('Build_dir')),
                     'Debug')

    opts.buildopts.target_cpu = 'x86'
    self.assertEqual(os.path.basename(exp.get_value('Build_dir')),
                     'Debug-x86')

    opts.buildopts.is_official_build = True
    self.assertEqual(os.path.basename(exp.get_value('Build_dir')),
                     'Official-Debug-x86')

    opts.buildopts.is_debug = False
    opts.buildopts.is_asan = True
    self.assertEqual(os.path.basename(exp.get_value('Build_dir')),
                     'Official-Release-asan-x86')

  def test_build_dir_android(self):
    # Android is a special case where we always want to see the CPU
    # type, but only the platform name when it's not the default.
    tmp_file = tempfile.NamedTemporaryFile(mode='w')
    tmp_file.write('target_os = ["android", "chromeos", "linux"]')
    tmp_file.flush()
    environ = env.Env(os.getcwd(), tmp_file.name)
    environ.build_platform = 'linux'
    opts = options.Options(environ, models.Configuration())
    exp = variable_expander.VariableExpander(opts)
    opts.buildopts.target_os = 'android'

    # Default CPU type should be None so no cpu appended to dir.
    self.assertEqual(os.path.basename(exp.get_value('Build_dir')),
                     'Debug')

    opts.buildopts.target_cpu = 'arm'
    self.assertEqual(os.path.basename(exp.get_value('Build_dir')),
                     'Debug-arm')

    opts.buildopts.target_cpu = 'x86'
    self.assertEqual(os.path.basename(exp.get_value('Build_dir')),
                     'Debug-x86')

    # Now as the non-default platform.
    tmp_file = tempfile.NamedTemporaryFile(mode='w')
    tmp_file.write('target_os = ["chromeos", "android", "linux"]')
    tmp_file.flush()
    environ = env.Env(os.getcwd(), tmp_file.name)
    environ.build_platform = 'linux'
    opts = options.Options(environ, models.Configuration())
    exp = variable_expander.VariableExpander(opts)
    opts.buildopts.target_os = 'android'

    # Default CPU type should be None.
    self.assertEqual(os.path.basename(exp.get_value('Build_dir')),
                     'Debug-android')

    opts.buildopts.target_cpu = 'arm'
    self.assertEqual(os.path.basename(exp.get_value('Build_dir')),
                     'Debug-android-arm')

    opts.buildopts.target_cpu = 'x86'
    self.assertEqual(os.path.basename(exp.get_value('Build_dir')),
                     'Debug-android-x86')

  def test_unknown_variable(self):
    opts = self.__create_opts()
    exp = variable_expander.VariableExpander(opts)
    with self.assertRaises(variable_expander.UnknownVariable):
      exp.get_value('<unknown>')

  def test_expand_variables(self):
    opts = self.__create_opts()
    exp = variable_expander.VariableExpander(opts)
    self.assertEqual(exp.expand_variables('${Build_type}'), 'Debug')
    self.assertEqual(exp.expand_variables('${Build_type}:${build_type}'),
                     'Debug:debug')

  def test_xvfb(self):
    opts = self.__create_opts('linux')
    exp = variable_expander.VariableExpander(opts)
    self.assertListEqual(exp.get_value('xvfb'), ['python', 'testing/xvfb.py'])

    opts = self.__create_opts('win')
    exp = variable_expander.VariableExpander(opts)
    self.assertEqual(exp.get_value('xvfb'), None)

    opts = self.__create_opts('linux')
    exp = variable_expander.VariableExpander(opts)
    self.assertListEqual(exp.expand_variables(['${xvfb}']),
                         ['python', 'testing/xvfb.py'])
    self.assertListEqual(exp.expand_variables(['${xvfb}', 'one', 'two']),
                         ['python', 'testing/xvfb.py', 'one', 'two'])

    opts = self.__create_opts('win')
    exp = variable_expander.VariableExpander(opts)
    #self.assertEqual(exp.expand_variables(['${xvfb}']), None)
    self.assertListEqual(exp.expand_variables(['${xvfb}', 'one', 'two']),
                         ['one', 'two'])

  def test_run_args(self):
    opts = self.__create_opts('linux')
    exp = variable_expander.VariableExpander(opts)
    self.assertListEqual(exp.expand_variables(['${run_args}', 'one', 'two']),
                         ['one', 'two'])

    opts.run_args = ['--pre', 'foo']
    self.assertListEqual(exp.expand_variables(['${run_args}', 'one', 'two']),
                         ['--pre', 'foo', 'one', 'two'])

if __name__ == '__main__':
    unittest.main()
