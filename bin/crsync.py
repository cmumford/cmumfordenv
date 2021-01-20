#!/usr/bin/env python3

import os
import platform
import subprocess
import sys


# TODO: Investigate switching to https://pypi.org/project/clrprint/
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'


class Cmd(object):
    '''Simple wrapper for executing and printing commands.'''
    @staticmethod
    def _item_to_string(item, add_quotes, quote_flags):
        assert (isinstance(item, str))
        equals_idx = item.find('=')
        if equals_idx != -1:
            lhs = item[:equals_idx]
            rhs = item[equals_idx + 1:]
            return '%s=%s' % (Cmd._item_to_string(lhs, add_quotes, False),
                              Cmd._item_to_string(rhs, add_quotes, True))

        if not add_quotes:
            return item
        if ' ' in item or '*' in item or (quote_flags and '--' in item):
            return '"%s"' % item
        return item

    @staticmethod
    def _ok_color():
        if platform.system() == 'Windows':
            return bcolors.HEADER
        return bcolors.OKBLUE

    @staticmethod
    def _info_color():
        return bcolors.OKGREEN

    @staticmethod
    def list_to_string(cmd, add_quotes):
        assert (isinstance(cmd, list))
        return ' '.join([
            Cmd._item_to_string(i, add_quotes=add_quotes, quote_flags=False)
            for i in cmd
        ])

    @staticmethod
    def _print(cmd, env_vars, color, add_quotes):
        '''Print the command to stdout in the specified color (if able to).

        May supply a string or list of strings.'''
        if (isinstance(cmd, list)):
            str_cmd = Cmd.list_to_string(cmd, add_quotes)
        else:
            assert isinstance(cmd, str) or isinstance(cmd, unicode)
            str_cmd = cmd
        if env_vars:
            str_cmd = env_vars + ' ' + str_cmd
        if Cmd._can_output_color():
            print("%s%s%s" % (color, str_cmd, bcolors.ENDC))
        else:
            print(str_cmd)

    @staticmethod
    def print_ok(cmd, env_vars=None, add_quotes=True):
        '''Print the OK command to stdout.

        May supply a string of list of strings.'''
        Cmd._print(cmd, env_vars, Cmd._ok_color(), add_quotes)

    @staticmethod
    def print_info(cmd, env_vars=None, add_quotes=True):
        '''Print the OK command to stdout.

        May supply a string of list of strings.'''
        Cmd._print(cmd, env_vars, Cmd._info_color(), add_quotes)

    @staticmethod
    def print_error(cmd, env_vars=None, add_quotes=True):
        '''Print the error command to stdout.

        May supply a string of list of strings.
        |env_vars| is a printable string that would appear on the command-line
        such as 'FOO="bar" BAZ="45"'.
        '''
        if isinstance(cmd, list):
            cmd = ['Failed: '] + cmd
        else:
            cmd = 'Failed: ' + cmd
        Cmd._print(cmd, env_vars, bcolors.FAIL, add_quotes)

    @staticmethod
    def _can_output_color():
        return sys.stdout.isatty()


def GetChromiumSrcDir():
    # TODO: source ~/.goshortcuts to get this path.
    if platform.system() == 'Windows':
        return r'D:\chromium\src'
    return os.path.expanduser('~/src/chromium/src')


def DepotToolsPath():
    return os.path.expanduser('~/src/depot_tools')


def GitPath():
    if platform.system() == 'Windows':
        return os.path.join(DepotToolsPath(), 'git.bat')
    return os.path.join(DepotToolsPath(), 'bootstrap-3.8.0.chromium.8_bin',
                        'git', 'bin', 'git')


def GClientPath():
    if platform.system() == 'Windows':
        return os.path.join(DepotToolsPath(), 'gclient.bat')
    return os.path.join(DepotToolsPath(), 'gclient')


def GitBranchExists(branch_name, src_dir):
    try:
        cmd = [
            GitPath(), 'show-ref', '--verify', '--quiet',
            'refs/heads/%s' % branch_name
        ]
        subprocess.check_call(cmd, cwd=src_dir)
        return True
    except subprocess.CalledProcessError:
        return False


def RunCmd(cmd, working_dir):
    Cmd.print_ok(cmd)
    subprocess.check_call(cmd, cwd=working_dir)


def UpdateChromium(src_dir):
    Cmd.print_info('Fetching source from Chromium origin.')
    RunCmd([GitPath(), 'fetch', 'origin'], working_dir=src_dir)
    if not GitBranchExists('master', src_dir):
        Cmd.print_info('Creating master branch.')
        RunCmd([
            GitPath(), 'checkout', '-b', 'master', '--track', 'origin/master'
        ],
               working_dir=src_dir)
    Cmd.print_info('Checking out master branch.')
    RunCmd([GitPath(), 'checkout', 'master'], working_dir=src_dir)
    Cmd.print_info('Rebasing master branch.')
    RunCmd([GitPath(), 'rebase', 'origin/master'], working_dir=src_dir)


def GClientSync(src_dir):
    Cmd.print_info('Syncing all Chromium dependencies.')
    RunCmd([GClientPath(), 'sync'], working_dir=src_dir)


if __name__ == '__main__':
    chromium_src_dir = GetChromiumSrcDir()
    UpdateChromium(chromium_src_dir)
    GClientSync(chromium_src_dir)
