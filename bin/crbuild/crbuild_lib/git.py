#!/usr/bin/env python3

import os
import platform
import subprocess

def Path():
  if platform.system() == 'Windows':
    return os.path.expanduser(r'~\src\depot_tools\git.bat')
  return 'git'

def CurrentBranch():
  cmd = [Path(), 'rev-parse', '--abbrev-ref', 'HEAD']
  for line in subprocess.check_output(cmd).split():
    return line.strip()
  return None
