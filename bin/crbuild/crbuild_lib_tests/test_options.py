#!/usr/bin/env python3

import os
import sys
import tempfile
import unittest

def GetAbsPathRelativeToThisFileDir(rel_path):
  return os.path.abspath(os.path.join(os.path.dirname(__file__),
                         rel_path))

sys.path.append(GetAbsPathRelativeToThisFileDir('..'))

from crbuild_lib import (adb, env, models, options)

class TestOptions(unittest.TestCase):

  @staticmethod
  def __create_env(gclient_path=GetAbsPathRelativeToThisFileDir('gclient.txt')):
    environ = env.Env(os.getcwd(), gclient_path)
    environ.android_devices = {
        'phonyarm': adb.DeviceInfo('phonyarm', 28,
                                   'arm64-v8a',
                                   ['com.android.webview'])}
    return environ

  @staticmethod
  def __create_opts():
    return options.Options(TestOptions.__create_env(), models.Configuration())

  def test_loading_no_error(self):
    self.assertEqual(options.Options.fixup_google_test_filter_args(None),
                     None)
    self.assertEqual(options.Options.fixup_google_test_filter_args(''),
                     None)
    self.assertEqual(options.Options.fixup_google_test_filter_args('foobar'),
                     ':foobar:')
    self.assertEqual(options.Options.fixup_google_test_filter_args(':foobar'),
                     ':foobar:')
    self.assertEqual(options.Options.fixup_google_test_filter_args(':foobar:'),
                     ':foobar:')

  def test_only_targets(self):
    opts = TestOptions.__create_opts()
    opts.parse(['the_target'])
    self.assertListEqual(opts.active_targets, ['the_target'])
    self.assertEqual(None, opts.run_args)

  def test_os(self):
    opts = TestOptions.__create_opts()
    opts.parse(['--os=android', '--cpu=arm64'])
    self.assertEqual('android', opts.buildopts.target_os)

  def test_default_target_os(self):
    opts = TestOptions.__create_opts()
    opts.parse(['all'])
    # The default target OS is the first one in the gclient file.
    self.assertEqual('linux', opts.buildopts.target_os)

    tmp_file = tempfile.NamedTemporaryFile(mode='w')
    tmp_file.write('target_os = ["android", "chromeos", "linux"]')
    tmp_file.flush()
    opts = options.Options(TestOptions.__create_env(tmp_file.name),
                           models.Configuration())
    opts.parse(['--cpu=arm64', 'all'])
    self.assertEqual('android', opts.buildopts.target_os)

  def test_invalid_os(self):
    opts = TestOptions.__create_opts()
    with self.assertRaises(options.InvalidOption):
      opts.parse(['--os=unknownOS'])

  def test_invalid_cpu(self):
    opts = TestOptions.__create_opts()
    with self.assertRaises(options.InvalidOption):
      opts.parse(['--cpu=unknownCPU'])

  def test_debug_and_release(self):
    opts = TestOptions.__create_opts()
    with self.assertRaises(options.InvalidOption):
      opts.parse(['--debug', '--release'])

  def test_extra_args(self):
    opts = TestOptions.__create_opts()
    opts.parse(['--os=linux', '-A', '-r', 'first', 'second', '--',
                'http://localhost:8000/index.html', 'last'])
    self.assertTrue(opts.buildopts.is_asan)
    self.assertFalse(opts.buildopts.is_debug)
    self.assertListEqual(opts.active_targets, ['first', 'second'])
    self.assertListEqual(opts.run_args, ['http://localhost:8000/index.html',
                                         'last'])

if __name__ == '__main__':
    unittest.main()
