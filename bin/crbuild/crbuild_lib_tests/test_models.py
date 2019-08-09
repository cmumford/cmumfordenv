#!/usr/bin/env python3

import os
import sys
import unittest

def GetAbsPathRelativeToThisFilesDir(rel_path):
  return os.path.abspath(os.path.join(os.path.dirname(__file__),
                         rel_path))

sys.path.append(GetAbsPathRelativeToThisFilesDir('..'))

from crbuild_lib import (env, loader, models, options, variable_expander)

class TestLoader(unittest.TestCase):

  @staticmethod
  def __read_config():
    return loader.ConfigReader().read('test_config.yml')

  def __create_options(self):
    return options.Options(
        env.Env(os.getcwd(), GetAbsPathRelativeToThisFilesDir('gclient.txt')),
        models.Configuration())

  def test_get_target_meta(self):
    '''Get a "meta" target - a name that exists only in the config file.'''
    config = TestLoader.__read_config()
    target = config.get_target('tests-all')
    self.assertEqual(target.name, 'tests-all')

  def test_get_target_list_expand(self):
    '''Get a target expanded from a target list.

    Many of the GN targets have identical attributes (ways to build/run) and
    are defined with a list of GN targets to which they all apply. The loader
    should expand these to one Target for each GN target name.'''
    config = TestLoader.__read_config()
    target = config.get_target('base_unittests')
    self.assertEqual(target.name, 'base_unittests')

  def test_get_target_with_default(self):
    target = models.Target('target-name')
    targets = target.get_build_targets(self.__create_options())
    self.assertSetEqual(targets, set(('target-name', )))

  def test_get_target_with_reference(self):
    parent_target = models.Target('parent-name')
    child_target = models.Target('child-name')

    parent_target.add_upstream_target(models.TargetReference(child_target,
                                                             None,
                                                             False))
    parent_target.reference_self = False

    config = models.Configuration()
    config.add_target(child_target)
    config.add_target(parent_target)

    targets = config.get_build_targets('parent-name', self.__create_options())
    self.assertSetEqual(targets, set(('child-name',)),
                        'Unexpected target sets')

  def test_get_targets_references_self(self):
    config = TestLoader.__read_config()
    build_targets = config.get_build_targets('content_browsertests_apk',
                                             self.__create_options())
    expected_targets = set((
        'content_browsertests_apk',
        'forwarder2',
    ))
    self.assertSetEqual(build_targets, expected_targets,
                        'Unexpected build targets')

  def test_get_targets_from_template(self):
    config = TestLoader.__read_config()
    opts = self.__create_options()
    opts.buildopts.target_os = 'linux'
    build_targets = config.get_build_targets('base_unittests', opts)
    expected_targets = set((
        'base_unittests',
        'xdisplaycheck',
    ))
    self.assertSetEqual(build_targets, expected_targets,
                        'Unexpected build targets')

    # Windows should not have xdisplaycheck as it is Linux-only.
    opts.buildopts.target_os = 'win'
    build_targets = config.get_build_targets('base_unittests', opts)
    expected_targets = set((
        'base_unittests',
    ))
    self.assertSetEqual(build_targets, expected_targets,
                        'Unexpected build targets')

  def test_get_targets_several_levels(self):
    config = TestLoader.__read_config()
    opts = self.__create_options()
    opts.buildopts.target_os = 'linux'
    build_targets = config.get_build_targets('tests-all', opts)
    expected_targets = set((
      'base_unittests',
      'blink_platform_unittests',
      'browser_tests',
      'cc_unittests',
      'components_unittests',
      'content_browsertests',
      'content_unittests',
      'crypto_unittests',
      'env_chromium_unittests',
      'extensions_unittests',
      'interactive_ui_tests',
      'leveldb_service_unittests',
      'net_unittests',
      'services_unittests',
      'storage_unittests',
      'unit_tests',
      'url_unittests',
      'xdisplaycheck',
    ))
    self.assertSetEqual(build_targets, expected_targets,
                        'Unexpected build targets')

  def test_get_target_not_found(self):
    config = TestLoader.__read_config()
    with self.assertRaises(models.NotFound):
      config.get_target('non-extent-target')

  def test_get_run_command_with_config(self):
    opts = self.__create_options()
    opts.buildopts.target_os = 'linux'

    # The default config
    config = TestLoader.__read_config()
    actual_cmds = [cmd.cmd_line() for cmd in
                   config.get_run_commands('devchrome', opts)]
    expected_cmds = [['${Build_dir}/chrome',
                      '--user-data-dir=${HOME}/.chrome_dev']]
    self.assertListEqual(expected_cmds, actual_cmds)

    # The ASan config
    opts.buildopts.is_asan = True
    actual_cmd = [cmd.cmd_line() for cmd in
                  config.get_run_commands('devchrome', opts)]
    expected_cmd = [['${Build_dir}/chrome',
                     '--allow-file-access-from-files',
                     '--disable-click-to-play',
                     '--disable-hang-monitor',
                     '--disable-metrics',
                     '--disable-popup-blocking',
                     '--disable-prompt-on-repost',
                     '--enable-experimental-extension-apis',
                     '--user-data-dir=${HOME}/.chrome_asan',
                     ]]

    self.assertListEqual(expected_cmd, actual_cmd)

  def test_get_run_command_with_upstream_target(self):
    opts = self.__create_options()
    opts.buildopts.target_os = 'linux'
    config = TestLoader.__read_config()

    actual_cmd = [cmd.cmd_line() for cmd in
                  config.get_run_commands('webkit_unit_tests-idb', opts)]
    expected_cmd = [['${Build_dir}/webkit_unit_tests',
                     '--brave-new-test-launcher',
                     '--test-launcher-jobs=${testjobs}',
                     '--gtest_filter=:*IDB*:',
                     ]]

    self.assertListEqual(expected_cmd, actual_cmd)

  def test_single_target_with_multiple_run_commands(self):
    opts = self.__create_options()
    opts.buildopts.target_os = 'linux'

    # The default config
    config = TestLoader.__read_config()
    actual_cmds = [cmd.cmd_line() for cmd in
                   config.get_run_commands('monochrome_apk', opts)]
    expected_cmds = [
        ['${Build_dir}/bin/monochrome_apk', 'install'],
        ['${Build_dir}/bin/monochrome_apk', 'set-webview-provider'],
    ]
    self.assertListEqual(expected_cmds, actual_cmds)

  def test_build_only(self):
    config = TestLoader.__read_config()
    opts = self.__create_options()
    opts.buildopts.target_os = 'linux'
    actual_cmds = [cmd.cmd_line() for cmd in
                   config.get_run_commands('system_webview_uninstall', opts)]
    expected_cmds = [
        ['${Build_dir}/bin/system_webview_apk', 'uninstall'],
    ]
    self.assertListEqual(expected_cmds, actual_cmds)

  def test_env_vars(self):
    config = TestLoader.__read_config()
    opts = self.__create_options()
    opts.buildopts.is_asan = True
    opts.buildopts.is_debug = False
    opts.buildopts.target_os = 'linux'
    run_commands = config.get_run_commands('devchrome', opts)
    self.assertEqual(1, len(run_commands))
    rc = run_commands[0]
    self.assertEqual('ASAN_OPTIONS', rc.env_var.name)
    self.assertEqual(':', rc.env_var.delim)
    self.assertListEqual(['alloc_dealloc_mismatch=0',
                          'allocator_may_return_null=0',
                          'allow_user_segv_handler=0'], rc.env_var.values)
    self.assertEqual('alloc_dealloc_mismatch=0:' \
                     'allocator_may_return_null=0:' \
                     'allow_user_segv_handler=0',
                     rc.env_var.values_str())
    self.assertEqual('ASAN_OPTIONS="alloc_dealloc_mismatch=0:' \
                     'allocator_may_return_null=0:' \
                     'allow_user_segv_handler=0"', rc.env_var.cmd_line_str())

if __name__ == '__main__':
    unittest.main()

