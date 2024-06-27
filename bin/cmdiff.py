#!/usr/bin/env python3

import sys
import errno
import subprocess
import time
import tempfile

# cmdiff.py is a utility to repeatedly run the given command looking for
# new output. If the command produces different output then diff will
# be run to show the difference between the new and prior output.
#
# Example use:
#   cmdiff.py ls -l '/dev/cu*'
#   cmdiff.py lsusb


def print_diff(base: bytes, other: bytes) -> None:
    with tempfile.NamedTemporaryFile() as base_file:
        base_file.write(base)
        base_file.flush()
        with tempfile.NamedTemporaryFile() as other_file:
            other_file.write(other)
            other_file.flush()
            cmd = ['diff', base_file.name, other_file.name]
            subprocess.run(cmd)


def main(args: list):
    if (len(args) < 1):
        print("usage: cmdiff <command> [args]")
        sys.exit(errno.EINVAL)

    cmd = ["bash", "-c", " ".join(args)]
    result = subprocess.run(cmd,
                            capture_output=True,
                            shell=False,
                            check=False)
    previous_output = result.stdout
    while (True):
        time.sleep(1.0)
        r = subprocess.run(cmd,
                           capture_output=True,
                           shell=False,
                           check=False)
        current_output = r.stdout
        if previous_output != current_output:
            print_diff(previous_output, current_output)
            previous_output = current_output


if __name__ == '__main__':
    if False:
        cmd = ["bash", "-c", "ls -l /dev"]
        print(cmd)
        print()

        r = subprocess.check_output(cmd)
        print('CHECK_OUTPUT:')
        print(r.decode())
        # sys.exit(0)
        result = subprocess.run(cmd,
                                capture_output=True,
                                shell=False,
                                check=False)
        print('RUN')
        print(result.stdout.decode())
        sys.exit(0)
    main(sys.argv[1:])
