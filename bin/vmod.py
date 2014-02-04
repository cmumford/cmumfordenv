#!/usr/bin/env python

import argparse
import os
import platform
import re
import subprocess
import time

class Options(object):
  def __init__(self):
    self.noop = False
    self.verbosity = 0
    self.print_cmds = False
    self.max_files_to_edit = 30
    self.commit = None
    self.gui_editor = False
    self.branch = False

  def parse(self):
    desc = """
    Open all modified files for editing.
    """
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('-v', '--verbose', action='count',
                        help='Be verbose, can be used multiple times')
    parser.add_argument('-n', '--noop', action='store_true',
                        help="Don't do anything, print what would be done")
    parser.add_argument('-b', '--branch', action='store_true',
                        help="Open files modified by any commit in this branch")
    parser.add_argument('-g', '--gui', action='store_true',
                        default=self.gui_editor,
                        help="Use GUI editor. default:%s" % self.gui_editor)
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
    if args.gui:
      self.gui_editor = args.gui
    if args.branch:
      self.branch = args.branch

  def GetEditorPath(self):
    # This assumes that VIM's executables are in the path.
    if self.gui_editor:
      return 'gvim'
    else:
      return 'vim'

  @staticmethod
  def Parse():
    options = Options()
    options.parse()
    return options

class BranchInfo(object):
  def __init__(self, name, parent, isCurrent):
    self.name = name
    self.parent = parent
    self.isCurrent = isCurrent

class Git:
  @staticmethod
  def UseShell():
    # TODO: Figure out why Windows will only with with shell=True, and Linux
    # will only work with shell=False.
    return platform.system() == 'Windows'

  @staticmethod
  def GetBranches(print_cmds):
    branches = {}
    cmd = ['git', '--no-pager', 'branch', '--list', '-v', '-v']
    if print_cmds:
      print ' '.join(cmd)
    for line in subprocess.check_output(cmd).splitlines():
      isCurrent = line.startswith('*')
      if isCurrent:
        line = line.lstrip('*')
      line = line.strip()
      m = re.search(r'^(\S+)\s+(\S+)\s+\[([^\]]+)\].*$', line)
      if m:
        branchName = m.group(1)
        items = m.group(3).split(':')
        parentBranchName = items[0]
        if parentBranchName not in branches:
          branches[parentBranchName] = BranchInfo(parentBranchName, None, False)
        if branchName in branches:
          info = branches[branchName]
          info.parent = parentBranchName
          info.isCurrent = isCurrent
        else:
          branches[branchName] = BranchInfo(branchName, parentBranchName, isCurrent)
    return branches

  @staticmethod
  def GetModifiedFiles(print_cmds):
    cmd = ['git', '--no-pager', 'status', '--porcelain']
    files = []
    p = re.compile(r'^[\sA]M\s+(.*)$')
    if print_cmds:
      print ' '.join(cmd)
    for line in subprocess.check_output(cmd, shell=Git.UseShell()).splitlines():
      m = p.match(line)
      if m:
        files.append(m.group(1))
    return files

  @staticmethod
  def GetModifiedFilesInCommit(commit, print_cmds):
    cmd = ['git', '--no-pager', 'show', '--name-only', '--pretty=oneline',
           commit]
    files = []
    line_no = 0
    if print_cmds:
      print ' '.join(cmd)
    for line in subprocess.check_output(cmd, shell=Git.UseShell()).splitlines():
      line_no += 1
      if line_no == 1:
        continue
      line.strip()
      files.append(line)
    return files

  @staticmethod
  def GetModifiedFilesInBranch(branch, print_cmds):
    assert(branch.parent)
    cmd = ['git', '--no-pager', 'log', '--name-only', '--pretty=oneline',
           branch.name, '--not', branch.parent]
    files = set()
    if print_cmds:
      print ' '.join(cmd)
    maxCommits = 30
    commitCount = 0
    commit_re = re.compile(r'^[0-9a-f]{40}\s.*$')
    for line in subprocess.check_output(cmd, shell=Git.UseShell()).splitlines():
      line.strip()
      if commit_re.match(line):
        commitCount += 1
        if commitCount >= maxCommits:
          break
      else:
        files.add(line)
    return files

  @staticmethod
  def GetModifiedFilesInCurrentBranch(print_cmds):
    branches = Git.GetBranches(print_cmds)
    for branchName in branches:
      branch = branches[branchName]
      if branch.isCurrent:
        return Git.GetModifiedFilesInBranch(branch, print_cmds)
    return set()

class App:
  def __init__(self, options):
    self.options = options

  @staticmethod
  def FilterExisting(files):
    existing_files = []
    filtered_files = []
    for f in files:
      if os.path.exists(f):
        existing_files.append(f)
      else:
        filtered_files.append(f)
    return (existing_files, filtered_files)

  def Run(self):
    if self.options.commit:
      files = Git.GetModifiedFilesInCommit(self.options.commit,
                                           self.options.print_cmds)
    elif self.options.branch:
      files = Git.GetModifiedFilesInCurrentBranch(self.options.print_cmds)
    else:
      files = Git.GetModifiedFiles(self.options.print_cmds)
      if len(files) == 0:
        files = Git.GetModifiedFilesInCurrentBranch(self.options.print_cmds)

    (files, filtered) = App.FilterExisting(files)
    if len(files) == 0:
      print "No modified files to open"
      return
    if len(filtered):
      for f in filtered:
        print "Doesn't exist: %s" % f
      time.sleep(2);  # Give user a chance to read message.
    if len(files) > self.options.max_files_to_edit:
      print "You have %d files, but will only edit %d of them" % \
          (len(files), self.options.max_files_to_edit)
      files = files[:self.options.max_files_to_edit]
    cmd = [self.options.GetEditorPath()]
    cmd.extend(sorted(files))
    if self.options.print_cmds:
      print ' '.join(cmd)
    if not self.options.noop:
      if self.options.gui_editor:
        subprocess.Popen(cmd)
      else:
        subprocess.call(cmd)

if __name__ == '__main__':
  app = App(Options.Parse())
  app.Run()
