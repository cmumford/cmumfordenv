#!/usr/bin/env python

import os
import sys

class Go:
  def __init__(self):
    self.shortcuts = {}
    with open(os.path.expanduser('~/.goshortcuts')) as f:
      for line in f:
        items = line.split(',')
        if len(items) == 2:
          self.shortcuts[items[0].strip()] = items[1].strip()

  def do_print(self):
    # TODO: Don't hard-code the string length
    for key in sorted(self.shortcuts):
      print >> sys.stderr, "%8s -> %s" % (key, self.shortcuts[key])

  def getval(self, val):
    if val in self.shortcuts:
      val = os.path.expanduser(self.shortcuts[val])
      return os.path.expandvars(val)
    else:
      print >> sys.stderr, 'Unknown shortcut "%s"' % val
      sys.exit(1)

if __name__ == '__main__':
  g = Go()
  if len(sys.argv) == 2:
    print "%s" % g.getval(sys.argv[1])
  else:
    g.do_print()
    print '.'
