#!/usr/bin/env python

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

if sys.platform == 'darwin':
    # On OSX run FileMerge directly as it blocks and opendiff does not
    cmd = ['/Developer/Applications/Utilities/FileMerge.app/Contents/MacOS/FileMerge',
           '-left', sys.argv[Params.BASE_PATH], '-right', sys.argv[Params.LOCAL_PATH]]
else:
    # Use meld
    if sys.platform == 'win32':
        meld_path = r"%s\Meld\meld\meld.exe" % os.environ['PROGRAMFILES(X86)']
    else:
        meld_path = 'meld'
    cmd = [meld_path, sys.argv[Params.BASE_PATH], sys.argv[Params.LOCAL_PATH]]

subprocess.check_call(cmd)
