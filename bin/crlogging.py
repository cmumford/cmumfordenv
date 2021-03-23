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


# TODO: Investigate switching to https://pypi.org/project/clrprint/
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'


def SplitLogLine(line):
    """Split a log line into three components: level, source, and log message.

    >>> SplitLogLine('[16960:775:0114/114420.990441:INFO:CONSOLE(24)] "The text"')
    ('INFO', 'CONSOLE(24)', '"The text"')
    >>> SplitLogLine('[17035:775:0114/114423.284045:ERROR:bluetooth_remote_gatt_characteristic.cc(289)] BluetoothRemoteGATTCharacteristic::startNotifications')
    ('ERROR', 'bluetooth_remote_gatt_characteristic.cc(289)', 'BluetoothRemoteGATTCharacteristic::startNotifications')
    >>> SplitLogLine('Not a line')
    Traceback (most recent call last):
     ...
    BadLogLine
    >>> SplitLogLine('')
    Traceback (most recent call last):
     ...
    BadLogLine
    >>> SplitLogLine(None)
    Traceback (most recent call last):
     ...
    TypeError: expected string or buffer
    """
    m = reg.match(line)
    if m:
        return (m.group(1), m.group(2), m.group(3))
    raise BadLogLine()

def CreateColorizedLogLine(line, highlight_text=None):
    try:
        (log_level, source, message) = SplitLogLine(line)
        start_color = ''
        end_color = ''
        if (log_level == 'ERROR'):
            log_level = 'E'
            start_color = bcolors.FAIL
            end_color = bcolors.ENDC
        elif (log_level == 'WARNING'):
            log_level = 'W'
            start_color = bcolors.WARNING
            end_color = bcolors.ENDC
        elif (log_level == 'INFO'):
            log_level = 'I'
            start_color = bcolors.OKGREEN
            end_color = bcolors.ENDC
        if highlight_text and highlight_text in message:
            start_color = bcolors.OKBLUE
        return '%s%s> %s: %s%s' % (start_color, log_level, source, message,
                                   end_color)
    except BadLogLine:
        return line

def PrintColorizedLogLines(lines, highlight_text=None):
    for line in lines:
        print(CreateColorizedLogLine(line, highlight_text))

if __name__ == "__main__":
    import doctest
    doctest.testmod()

    PrintColorizedLogLines(fileinput.input(), 'XXX')
