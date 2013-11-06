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
    for key in sorted(self.shortcuts):
      print "%s -> %s" % (key, self.shortcuts[key])

  def getval(self, val):
    if val in self.shortcuts:
      val = os.path.expanduser(self.shortcuts[val])
      return os.path.expandvars(val)
    else:
      print >> sys.stderr, 'Unknown shortcut "%s"' % val
      sys.exit(1)

def main(argv):
  g = Go()
  if len(argv) == 2:
    print "%s" % g.getval(argv[1])
  else:
    g.do_print()

if __name__ == '__main__':
  main(sys.argv)
