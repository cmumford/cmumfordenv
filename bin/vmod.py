#!/usr/bin/env python

import argparse
import os
import re
import subprocess

class Options(object):
  def __init__(self):
    self.noop = False
    self.verbosity = 0
    self.print_cmds = False
    self.max_files_to_edit = 30
    self.commit = None

  def parse(self):
    desc = """
    Open all modified files for editing.
    """
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('-v', '--verbose', action='count',
                        help='Be verbose, can be used multiple times')
    parser.add_argument('-n', '--noop', action='store_true',
                        help="Don't do anything, print what would be done")
    parser.add_argument('commit', metavar='COMMIT', type=str, nargs='?',
                                         help='Open files in COMMIT in editor')
    args = parser.parse_args()
    self.verbosity = args.verbose
    if args.commit:
      self.commit = args.commit
    if self.verbosity > 0:
      self.print_cmds = True
    if args.noop:
      self.noop = True
      self.print_cmds = True

  @staticmethod
  def Parse():
    options = Options()
    options.parse()
    return options

class Git:
  @staticmethod
  def GetModifiedFiles():
    cmd = ['git', '--no-pager', 'status', '--porcelain']
    files = []
    p = re.compile(r'^\s*M\s+(.*)$')
    for line in subprocess.check_output(cmd).splitlines():
      m = p.match(line)
      if m:
        files.append(m.group(1))
    return files

  @staticmethod
  def GetModifiedFilesInCommit(commit):
    cmd = ['git', '--no-pager', 'show', '--name-only', '--pretty=oneline',
           commit]
    files = []
    line_no = 0
    for line in subprocess.check_output(cmd).splitlines():
      line_no += 1
      if line_no == 1:
        continue
      line.strip()
      files.append(line)
    return files

class App:
  def __init__(self, options):
    self.options = options

  @staticmethod
  def FilterExisting(files):
    existing_files = []
    for f in files:
      if os.path.exists(f):
        existing_files.append(f)
    return existing_files

  def Run(self):
    if self.options.commit:
      files = App.FilterExisting(Git.GetModifiedFilesInCommit(self.options.commit))
    else:
      files = App.FilterExisting(Git.GetModifiedFiles())
    if len(files) == 0:
      print "No modified files to open"
      return
    if len(files) > self.options.max_files_to_edit:
      print "You have %d files, but will only edit %d of them" % \
          (len(files), self.options.max_files_to_edit)
      files=files[:self.options.max_files_to_edit]
    cmd = ['vim']
    cmd.extend(files)
    if self.options.print_cmds:
      print ' '.join(cmd)
    if not self.options.noop:
      subprocess.call(cmd)

if __name__ == '__main__':
  app = App(Options.Parse())
  app.Run()
