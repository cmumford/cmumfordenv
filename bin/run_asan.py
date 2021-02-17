#!/usr/bin/env python

import argparse
import glob
import os
import shutil
import subprocess
import sys

class RunType:
  official_asan = 1
  local_asan = 2
  local_build = 3

class Options:
  def __init__(self):
    self.noop = False
    self.print_cmds = False
    if self.noop:
      self.print_cmds = True
    self.build_type = 'Release'
    self.debugger = False
    self.runType = RunType.local_build
    # Looks like drive letters are required in order for the --allow-file-access-from-files
    # flag to work (needs verification)
    download_dir = os.path.join('C:', os.environ['HOMEPATH'], 'Downloads')
    self.asan_dir=os.path.join(download_dir, 'asan-win32-release-254060')
    self.asan_dir=os.path.join(download_dir, 'asan-win32-release')
    self.test_file=os.path.join(download_dir,
      "C--clusterfuzz-slave-bot-inputs-5030444563169280/fuzz-crossfuzz-1377525766.html")
    self.test_file=os.path.join(download_dir,
      "C--clusterfuzz-slave-bot-inputs-fuzz-crossfuzz-1377525766/fuzz-crossfuzz-1377525766.html")
    self.profile_dir=r'C:\tmp\user_profile_chrome.exe_0'

  def IsASAN(self):
    return self.runType != RunType.local_build

  def Parse(self):
    desc = "A script run ASAN builds."
    epilog="""At the moment this script isn't generalized enough and will need to
    be tweaked the next time it is run. Probably need to add asan_dir and
    test_file parameters. It might be possible to come up with a ASAN configuration
    for crbuild and do away with this file.

    Before running the locally built ASAN Chromium you need to build it:
    crbuild -r -A All_syzygy

    Runnng the local-build type is just equivalent to running chrome out of the
    out dir.
    """
    parser = argparse.ArgumentParser(description=desc, epilog=epilog)
    parser.add_argument('-d', '--debug', action='store_true',
                        help='Do a debug build (default: %s)' % self.build_type)
    parser.add_argument('-D', '--debugger', action='store_true',
                        help='Run under the debugger. Default: %s' % self.debugger)
    parser.add_argument('-v', '--verbose', action='count',
                        help='Be verbose, can be used multiple times')
    parser.add_argument('-n', '--noop', action='store_true',
                        help="Don't do anything, print what would be done")
    parser.add_argument('-t', '--type', dest='type', action='store',
                          choices=['official-asan','local-asan','local-build'],
                          help='What kind of Chrome build to run. Default local-build')

    args = parser.parse_args()
    if args.debug:
      self.build_type = 'Debug'
    else:
      self.build_type = 'Release'
    if args.debugger:
      self.debugger = True
    if args.verbose:
      self.print_cmds = True
    if args.noop:
      self.noop = True
      self.print_cmds = True
    if args.type == 'local-build':
      self.runType = RunType.local_build
    elif args.type == 'local-asan':
      self.runType = RunType.local_asan
    elif args.type == 'official-asan':
      self.runType = RunType.official_asan
    self.platform_dir=os.path.join('D:\\', 'src', 'out', self.build_type)
    return self

options = Options().Parse()

SYZYGY_ASAN_OPTIONS = [
  "--exit_on_failure",
  "--minidump_on_failure",
  "--quarantine_size=104857600",
  "--trailer_padding_size=32"
]
os.environ['SYZYGY_ASAN_OPTIONS'] = ' '.join(SYZYGY_ASAN_OPTIONS)

if options.runType==RunType.official_asan:
  syzygy_dir = os.path.join(options.asan_dir, 'syzygy')
  files = glob.iglob(os.path.join(syzygy_dir, "*.*"))
  for file in files:
    if os.path.isfile(file):
      if options.print_cmds:
        print "%s -> %s" % (file, options.asan_dir)
      if not options.noop:
        shutil.copy2(file, options.asan_dir)
  chrome_exe=os.path.join(options.asan_dir, 'chrome.exe')
else:
  if options.runType==RunType.local_asan:
    cmd = ["C:/Program Files/7-Zip/7z.exe",
           "e",
           os.path.join(options.platform_dir, 'syzygy', 'chrome.7z'),
           "-y",
           "-o%s" % options.asan_dir]
    chrome_dll_pdb = os.path.join(options.platform_dir, 'syzygy', 'chrome.dll.pdb')
    if options.print_cmds:
      print ' '.join(cmd)
      print "%s -> %s" % (chrome_dll_pdb, options.asan_dir)
    if not options.noop:
      shutil.copy2(chrome_dll_pdb, options.asan_dir)
    chrome_exe=os.path.join(options.asan_dir, 'chrome.exe')
  elif options.runType==RunType.local_build:
    chrome_exe=os.path.join(options.platform_dir, 'chrome.exe')

if options.print_cmds:
  print "rm -rf %s" % options.profile_dir
if not options.noop:
  shutil.rmtree(options.profile_dir, True)

chrome_cmd = [chrome_exe, '--allow-file-access-from-files', '--disable-popup-blocking',
        '--js-flags=--expose_gc', '--user-data-dir=%s' % options.profile_dir, options.test_file]

if options.debugger:
  chrome_cmd.insert(1, '--disable-gpu-watchdog')
  cmd = ['windbg', '-o', '-G']
  if options.IsASAN():
    cmd.extend(['-c', '.ocommand ASAN'])
elif options.runType == RunType.local_build:
  cmd = []
else:
  cmd = [os.path.join(options.asan_dir, 'agent_logger.exe'),
         '--unique-instance-id',
         r'-minidump-dir=C:\tmp',
         'start',
         '--']

cmd.extend(chrome_cmd)

if options.print_cmds:
  print ' '.join(cmd)
if not options.noop:
  subprocess.check_call(cmd, shell=True)
