#!/usr/bin/env python

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

  def parse(self):
    desc = """
    Rebase all branches in the current Git repo.
    """
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('-v', '--verbose', action='count',
                        help='Be verbose, can be used multiple times')
    parser.add_argument('-n', '--noop', action='store_true',
                        help="Don't do anything, print what would be done")
    parser.add_argument('-s', '--skip', action='append',
                        help="Branch name to skip")
    args = parser.parse_args()
    self.verbosity = args.verbose
    if self.verbosity > 0:
      self.print_cmds = True
    if args.noop:
      self.noop = True
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

  def getBranches(self):
    branches = {}
    cmd = ['git', '--no-pager', 'branch', '--list', '-v', '-v']
    for line in subprocess.check_output(cmd).splitlines():
      if line.startswith('*'):
        line = line.lstrip('*')
      line = line.strip()
      m = re.search(r'^(\S+)\s+(\S+)\s+\[([^\]]+)\].*$', line)
      if m:
        print line
        branchName = m.group(1)
        items = m.group(3).split(':')
        parentBranchName = items[0]
        if parentBranchName == branchName:
          print >> sys.stderr, "Branch is recursive: %s" % branchName
          branches[branchName] = BranchInfo(branchName, None)
          continue
        if parentBranchName not in branches:
          branches[parentBranchName] = BranchInfo(parentBranchName,None)
        if branchName in branches:
          info = branches[branchName]
          info.parent = parentBranchName
          assert parentBranchName != branchName
        else:
          branches[branchName] = BranchInfo(branchName, parentBranchName)
    return branches

class Rebaser(object):
  def __init__(self, opts):
    self.options = opts
    self.git = Git()

  def rebase(self, branches, branch):
    #print "%s < %s" % (branch.name, branch.parent)
    if branch.parent not in branches:
      # No parent then nothing on which to rebase
      return
    parent = branches[branch.parent]
    self.rebase(branches, parent)
    if self.git.isRemoteBranch(branch.name):
      return
    if branch.rebased:
      return
    if branch.name in self.options.skip_branches:
      print 'Skipping branch "%s"' % branch.name
      return
    cmd = ['git', '--no-pager', 'checkout', branch.name]
    if self.options.print_cmds:
      print ' '.join(cmd)
    if not self.options.noop:
      subprocess.check_output(cmd)
    cmd = ['git', '--no-pager', 'rebase', parent.name]
    print "Rebasing %s onto %s" % (branch.name, parent.name)
    if self.options.print_cmds:
      print ' '.join(cmd)
    if not self.options.noop:
      try:
        subprocess.check_output(cmd)
      except subprocess.CalledProcessError as e:
        print >> sys.stderr, "Error rebasing %s on %s" % (branch.name,
                                                          parent.name)
        print >> sys.stderr, "Probably a conflict? Resolve and rerun."
        sys.exit(e.returncode)
    branch.rebased = True

  def run(self):
    branches = self.git.getBranches()
    for skip in self.options.skip_branches:
      if skip not in branches.keys():
        print >> sys.stderr, "Can't skip branch \"%s\" - not a branch name" % skip
        sys.exit(2)

    for branch in branches:
      self.rebase(branches, branches[branch])

if __name__ == '__main__':
  rebaser = Rebaser(Options.Parse())
  rebaser.run()
