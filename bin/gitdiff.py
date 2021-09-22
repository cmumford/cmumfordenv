#!/usr/bin/env python

from __future__ import print_function

import os
import subprocess
import sys

class Params:
  PROG = 0
  FILE_PATH = 1
  BASE_PATH = 2
  BASE_HASH = 3
  BASE_MODE = 4
  LOCAL_PATH = 5
  LOCAL_HASH = 6
  LOCAL_MODE = 7

def GetPossibleMeldPaths():
  if sys.platform == 'darwin':
    return [
      '/usr/local/bin/meld',
      '/Applications/Meld.app/Contents/MacOS/Meld'
    ]
  if sys.platform == 'win32':
    return [
      os.path.join(os.environ['PROGRAMFILES(X86)'], 'Meld', 'meld', 'meld.exe'),
      os.path.join(os.environ['PROGRAMFILES(X86)'], 'Meld', 'meld.exe')
    ]
  return []

def GetMeldPath():
  for p in GetPossibleMeldPaths():
    if os.path.exists(p):
      return p
  # Assume Meld is in the PATH.
  return 'meld'

cmd = [GetMeldPath(), sys.argv[Params.BASE_PATH], sys.argv[Params.LOCAL_PATH]]

subprocess.check_call(cmd)
