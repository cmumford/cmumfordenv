#!/usr/bin/env python3

import os
import sys
import time

from crbuild_lib import (Builder, Cmd, ConfigReader, Env, Options)

def get_config_file_path():
  """Return the path to this application's configuration file."""
  return os.path.join(os.path.dirname(__file__), 'config.yml')

def get_source_root(dir_in_source_root):
  """Returns the absolute path to the chromium source root given a directory
  inside of that root."""
  candidate = dir_in_source_root
  fingerprints = ['chrome', 'net', 'v8', 'build', 'skia']
  while candidate and not all(
      [os.path.isdir(os.path.join(candidate, fp)) for fp in fingerprints]):
    candidate = os.path.dirname(candidate)
    if candidate == os.sep:
      raise Exception('Not a Chrome (sub)directory: %s' % dir_in_source_root)
  return candidate

def get_gclient_path(src_root_dir):
  '''Return the absolute path to the .gclient file.'''
  return os.path.abspath(os.path.join(src_root_dir, '..', '.gclient'))

def get_api_keys_path():
  '''Return the absolute path to the api_keys.txt file.'''
  return os.path.abspath(os.path.join(os.path.dirname(__file__),
                                      'api_keys.txt'))

def format_duration(seconds):
  if seconds < 60:
    return "%d sec" % seconds
  if seconds < 3600:
    minutes = int(seconds / 60)
    seconds -= minutes * 60
    return "%02d:%02d" % (minutes, seconds)
  hours = int(seconds / 3600)
  seconds -= hours * 3600
  minutes = int(seconds / 60)
  seconds -= minutes * 60
  return "%02d:%02d:%02d" % (hours, minutes, seconds)

if __name__ == '__main__':
  try:
    start = time.time()

    reader = ConfigReader()
    config = reader.read(get_config_file_path())

    src_root_dir = get_source_root(os.getcwd())
    options = Options(Env(src_root_dir,
                          get_gclient_path(src_root_dir),
                          get_api_keys_path()),
                      config)
    options.parse(sys.argv[1:])

    builder = Builder(options, config)
    errors = builder.build()

    runtime = time.time() - start
    if not errors:
      print()
      print(str.format("All tasks completed successfully. Duration: {0}",
                       format_duration(runtime)))
      sys.exit(0)

    # Print errors and exit.
    for e in errors:
      Cmd.print_error(e.cmd, env_vars=None, add_quotes=False)

    print()
    print(str.format("Run duration: {0}", format_duration(runtime)))

    sys.exit(errors[0].returncode)
  except Exception as e:
    raise e
    #print(str.format('Exception: {0}', str(e)), file=sys.stderr)
