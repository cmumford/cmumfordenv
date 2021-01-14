#!/usr/bin/env python3

# This program strips the date/time info from the beginning of
# each log output line from a Chromium log. This is helpful
# when wanting to "diff" two logs.

import fileinput
import os
import platform
import re
import sys

reg = re.compile(r'^\[\d+:\d+:\d+/\d+.\d+:([^:]+):([^\]]+)\] (.*)')

class BadLogLine(Exception):
    pass


def SplitLogLine(line):
    """Split a log line into three components: level, source, and log message.

    >>> SplitLogLine('[16960:775:0114/114420.990441:INFO:CONSOLE(24)] "The text"')
    ('INFO', 'CONSOLE(24)', '"The text"')
    >>> SplitLogLine('[17035:775:0114/114423.284045:ERROR:bluetooth_remote_gatt_characteristic.cc(289)] BluetoothRemoteGATTCharacteristic::startNotifications')
    ('ERROR', 'bluetooth_remote_gatt_characteristic.cc(289)', 'BluetoothRemoteGATTCharacteristic::startNotifications')
    """
    m = reg.match(line)
    if m:
        return (m.group(1), m.group(2), m.group(3))
    raise BadLogLine()


if __name__ == "__main__":
    import doctest
    doctest.testmod()

    for line in fileinput.input():
        try:
            print('%s: %s: %s' % SplitLogLine(line))
        except BadLogLine:
            sys.stdout.write(line)
