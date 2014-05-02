#!/usr/bin/env python

import os
import subprocess
import sys

if sys.platform == 'darwin':
    # On OSX run FileMerge directly as it blocks and opendiff does not
    os.system('/Developer/Applications/Utilities/FileMerge.app/Contents/MacOS/FileMerge -left "%s" -right "%s"' % (sys.argv[2], sys.argv[5]))
elif sys.platform == 'win32':
    meld_path = r"%s\Meld\meld\meld.exe" % os.environ['PROGRAMFILES(X86)']
    subprocess.check_call([meld_path, sys.argv[2], sys.argv[5]])
else:
    os.system('meld "%s" "%s"' % (sys.argv[2], sys.argv[5]))
