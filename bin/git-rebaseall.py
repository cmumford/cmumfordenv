#!/usr/bin/env python3

from __future__ import print_function

import argparse
import re
import subprocess
import sys

class Options(object):
  def __init__(self):
    self.noop = False
    self.verbosity = 0
    self.skip_branches = set()
    self.print_cmds = False
    self.force = False

  def parse(self):
    desc = """
    Rebase all branches in the current Git repo.
    """
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('-v', '--verbose', action='count',
                        help='Be verbose, can be used multiple times')
    parser.add_argument('-n', '--noop', action='store_true',
                        help="Don't do anything, print what would be done")
    parser.add_argument('-f', '--force', action='store_true',
                        help="Rebase anyway - even if not behind")
    parser.add_argument('-s', '--skip', action='append',
                        help="Branch name to skip")
    args = parser.parse_args()
    if args.verbose:
      self.verbosity = args.verbose
    if self.verbosity > 0:
      self.print_cmds = True
    if args.noop:
      self.noop = True
    if args.force:
      self.force = True
    if args.skip:
      for branch_name in args.skip:
        self.skip_branches.add(branch_name)

  @staticmethod
  def Parse():
    options = Options()
    options.parse()
    return options

class BranchInfo(object):
  def __init__(self, name, parent):
    assert name != parent
    self.name = name
    self.parent = parent
    self.rebased = False
    self.ahead = None
    self.behind = None

  def isLocalBranch(self):
    # TODO: Get origin names
    return not self.name.startswith('origin/')

class Git(object):
  def getRemotes(self):
    # TODO: Get the actual names
    return ['origin']

  def isRemoteBranch(self, branch):
    for remote in self.getRemotes():
      if branch.startswith(remote):
        return True
    return False

  @staticmethod
  def parseAheadBehind(info, items):
    for item in items.split(','):
      vals = item.strip().split()
      if len(vals) == 2:
        if vals[0] == 'ahead':
          info.ahead = int(vals[1])
        elif vals[0] == 'behind':
          info.behind = int(vals[1])

  def getBranches(self):
    branches = {}
    cmd = ['git', '--no-pager', 'branch', '--list', '-v', '-v']
    for line in subprocess.check_output(cmd).splitlines():
      line = line.decode('utf-8')
      if line.startswith('*'):
        line = line.lstrip('*')
      line = line.strip()
      m = re.search(r'^(\S+)\s+(\S+)\s+\[([^\]]+)\].*$', line)
      if m:
        branchName = m.group(1)
        items = m.group(3).split(':')
        parentBranchName = items[0]
        if parentBranchName == branchName:
          print("Branch is recursive: %s" % branchName, file=sys.stderr)
          branches[branchName] = BranchInfo(branchName, None)
          continue
        if parentBranchName not in branches:
          branches[parentBranchName] = BranchInfo(parentBranchName, None)
        if branchName in branches:
          info = branches[branchName]
          info.parent = parentBranchName
          assert parentBranchName != branchName
          if len(items) > 1:
            Git.parseAheadBehind(info, items[1])
        else:
          info = BranchInfo(branchName, parentBranchName)
          if len(items) > 1:
            Git.parseAheadBehind(info, items[1])
          branches[branchName] = info
    return branches

class Rebaser(object):
  def __init__(self, opts):
    self.options = opts
    self.git = Git()
    self.rebase_warned_branches = set()

  @staticmethod
  def isBranchOrParentBehind(branches, branch):
    while branch:
      if branch.behind:
        return True
      if branch.parent in branches:
        branch = branches[branch.parent]
      else:
        break
    return False

  def prune(self):
    branches = self.git.getBranches()
    for branch in branches:
      if branch.name in self.options.skip_branches:
        continue
      cmd = ['git', 'branch', '--set-upstream-to=%s' % up, branch.name]

  def rebase(self, branches, branch):
    #print("%s < %s" % (branch.name, branch.parent))
    if not branch.parent:
      if branch.name not in self.rebase_warned_branches:
        print("%s has no parent to rebase to" % branch.name, file=sys.stderr)
        self.rebase_warned_branches.add(branch.name)
      return;
    if branch.parent not in branches:
      # No parent then nothing on which to rebase
      print("%s is not a known branch" % branch.parent, file=sys.stderr)
      return
    parent = branches[branch.parent]
    self.rebase(branches, parent)
    if self.git.isRemoteBranch(branch.name):
      return
    if branch.rebased:
      return
    if branch.name in self.options.skip_branches:
      print('Skipping branch "%s"' % branch.name)
      return
    if not self.options.force and not Rebaser.isBranchOrParentBehind(branches, branch):
      print("Skipping rebase: %s is not behind %s" % (branch.name, branch.parent))
      return
    cmd = ['git', '--no-pager', 'checkout', branch.name]
    if self.options.print_cmds:
      print(' '.join(cmd))
    if not self.options.noop:
      subprocess.check_output(cmd)
    cmd = ['git', '--no-pager', 'rebase', parent.name]
    print("Rebasing %s onto %s" % (branch.name, parent.name))
    if self.options.print_cmds:
      print(' '.join(cmd))
    if not self.options.noop:
      try:
        subprocess.check_output(cmd)
      except subprocess.CalledProcessError as e:
        print("Error rebasing %s on %s" % (branch.name, parent.name),
              file=sys.stderr)
        print("Probably a conflict? Resolve and rerun.", file=sys.stderr)
        sys.exit(e.returncode)
    branch.rebased = True

  def run(self):
    branches = self.git.getBranches()
    for skip in self.options.skip_branches:
      if skip not in branches.keys():
        print("Can't skip branch \"%s\" - not a branch name" % skip,
              file=sys.stderr)
        sys.exit(2)

    for branch in branches:
      self.rebase(branches, branches[branch])

if __name__ == '__main__':
  rebaser = Rebaser(Options.Parse())
  rebaser.run()
