#!/usr/bin/env python

import argparse
import requests
import sys

class Options(object):
  def __init__(self):
    self.os = 'chrome'
    self.version_major = None

  def Parse(self):
    desc = "A script to Retrieve information about Chrome releases."
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('--version', required=True,
                        help='The Chrome version')
    parser.add_argument('--os',
                        help='"chrome" or "chromeos"')
    args = parser.parse_args()
    self.version_major = args.version
    if args.os:
      os = args.os.lower()
      if os == 'chrome' or os == 'cr':
        self.os = os
      elif os == 'chromeos' or os == 'cros':
        self.os = 'chromeos'
      else:
        print >> sys.stderr, 'Invalid OS: "%s"' % args.os

def FindChromeOS(version_major):
  print "For Chrome OS: %s" % version_major
  r = requests.get('http://cros-omahaproxy.appspot.com/history')
  for line in r.content.splitlines():
    line = line.strip()
    items = line.split(',')
    if len(items) != 6:
      continue
    (timestamp,chromeos_version,chrome_version,appid,track,hardware) = items
    v = chrome_version.split('.')
    if v[0] == version_major and track == 'stable-channel':
      print "%s shipped on %s" % (chrome_version, timestamp)

def FindChrome(version_major):
  print "For Chrome: %s" % version_major
  r = requests.get('http://omahaproxy.appspot.com/history')
  for line in r.content.splitlines():
    line = line.strip()
    items = line.split(',')
    if len(items) != 4:
      continue
    (os,channel,version,timestamp) = items
    v = version.split('.')
    if v[0] == version_major and channel == 'stable':
      print "%s shipped on %s" % (version, timestamp)


if __name__ == '__main__':
  options = Options()
  options.Parse()
  if options.os == 'chrome':
    FindChrome(options.version_major)
  elif options.os == 'chromeos':
    FindChromeOS(options.version_major)
  else:
    assert "Incorrect OS"
