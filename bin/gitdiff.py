#!/usr/bin/python

import sys
import os

isMac = sys.platform == 'darwin'
if isMac:
    # Run FileMerge directly as it blocks and opendiff does not
    os.system('/Developer/Applications/Utilities/FileMerge.app/Contents/MacOS/FileMerge -left "%s" -right "%s"' % (sys.argv[2], sys.argv[5]))
else:
    os.system('meld "%s" "%s"' % (sys.argv[2], sys.argv[5]))
