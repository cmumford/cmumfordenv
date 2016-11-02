#!/usr/bin/env python

import argparse
import os
import platform
import re
import subprocess
import sys
import time

class Options(object):
  def __init__(self):
    self.noop = False
    self.verbosity = 0
    self.print_cmds = False
    self.max_files_to_edit = 200
    self.commit = None
    self.gui_editor = Options.CanDoGUI()
    self.branch = False

  @staticmethod
  def CanDoGUI():
    return 'DISPLAY' in os.environ

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
      if platform.system() == 'Darwin':
        return 'mvim'
      else:
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
  def Path():
    if platform.system() == 'Windows':
      return os.path.expanduser(r'~\depot_tools\git.bat')
    else:
      return 'git'

  @staticmethod
  def IsGitDir(dir):
    if not dir:
      return False
    git_dir = os.path.join(dir, '.git')
    if os.path.isdir(git_dir):
      return True
    parent_dir = os.path.abspath(os.path.join(dir, os.pardir))
    if parent_dir == dir:
      return False
    return Git.IsGitDir(parent_dir)

  @staticmethod
  def UseShell():
    # TODO: Figure out why Windows will only with with shell=True, and Linux
    # will only work with shell=False.
    return platform.system() == 'Windows'

  @staticmethod
  def GetBranches(print_cmds):
    branches = {}
    cmd = [Git.Path(), '--no-pager', 'branch', '--list', '-v', '-v']
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
    cmd = [Git.Path(), '--no-pager', 'status', '--porcelain']
    files = []
    p = re.compile(r'^[\sAM]+\s+(.*)$')
    if print_cmds:
      print ' '.join(cmd)
    for line in subprocess.check_output(cmd, shell=Git.UseShell()).splitlines():
      m = p.match(line)
      if m:
        files.append(m.group(1))
    return files

  @staticmethod
  def GetModifiedFilesInCommit(commit, print_cmds):
    cmd = [Git.Path(), '--no-pager', 'show', '--name-only', '--pretty=oneline',
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
  def GetModifiedFilesInBranch(branch, print_cmds, maxCommits):
    assert(branch.parent)
    cmd = [Git.Path(), '--no-pager', 'diff', '--name-only', branch.name, branch.parent]
    files = set()
    if print_cmds:
      print ' '.join(cmd)
    commitCount = 0
    for line in subprocess.check_output(cmd, shell=Git.UseShell()).splitlines():
      line.strip()
      commitCount += 1
      if commitCount >= maxCommits:
        break
      files.add(line)
    return files

  @staticmethod
  def GetModifiedFilesInCurrentBranch(print_cmds, maxCommits):
    branches = Git.GetBranches(print_cmds)
    for branchName in branches:
      branch = branches[branchName]
      if branch.isCurrent:
        return Git.GetModifiedFilesInBranch(branch, print_cmds, maxCommits)
    return set()

class G4:
  @staticmethod
  def GetModifiedFiles(maxCommits):
    files = []
    cmd = ['g4', 'status']
    commitCount = 0
    reg = re.compile(r'^//depot/google3/(.*)#\d+.*$')
    for line in subprocess.check_output(cmd, shell=Git.UseShell()).splitlines():
      m = reg.match(line)
      if m:
        files.append(m.group(1))
    return files

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

  def ShowFiles(self, files):
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
    cmd.extend(sorted(files, key=lambda fname: os.path.basename(fname.lower())))
    if self.options.print_cmds:
      print '\n   '.join(cmd)
    if not self.options.noop:
      if self.options.gui_editor:
        subprocess.Popen(cmd)
      else:
        subprocess.call(cmd)

  def RunGit(self):
    if self.options.commit:
      files = Git.GetModifiedFilesInCommit(self.options.commit,
                                           self.options.print_cmds)
    elif self.options.branch:
      files = Git.GetModifiedFilesInCurrentBranch(self.options.print_cmds,
                                                  self.options.max_files_to_edit)
    else:
      files = Git.GetModifiedFiles(self.options.print_cmds)
      if len(files) == 0:
        files = Git.GetModifiedFilesInCurrentBranch(self.options.print_cmds,
                                                    self.options.max_files_to_edit)

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
    cmd.extend(sorted(files, key=lambda fname: os.path.basename(fname.lower())))
    if self.options.print_cmds:
      print '\n   '.join(cmd)
    if not self.options.noop:
      if self.options.gui_editor:
        subprocess.Popen(cmd)
      else:
        subprocess.call(cmd)

  def RunG4(self):
    fnames = G4.GetModifiedFiles('.')
    self.ShowFiles(fnames)

  def Run(self):
    if Git.IsGitDir('.'):
      self.RunGit()
    else:
      self.RunG4()

if __name__ == '__main__':
  app = App(Options.Parse())
  app.Run()
