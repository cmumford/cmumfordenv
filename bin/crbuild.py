#!/usr/bin/env python

import argparse
import copy
import json
import multiprocessing
import os
import pickle
import platform
import getpass
import re
import shutil
import subprocess
import sys
import time
from argparse import RawTextHelpFormatter
cmd_subfolder = os.path.realpath(os.path.abspath(os.path.join("tools", "valgrind", "asan")))
if cmd_subfolder not in sys.path:
  sys.path.insert(0, cmd_subfolder)
from third_party import asan_symbolize
from fsmounter import Mounter
from fsimage import Image

# python -m doctest -v crbuild.py

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

class BuildTypeItem(object):
  def __init__(self):
    self.done_for = set()
    self.auto_generated = False

  def WasDoneFor(self, build_type):
    return build_type in self.done_for

  def MarkDoneFor(self, build_type):
    self.done_for.add(build_type)

  def GetExePath(self, build_type):
    return 'chrome?'

class BuildTarget(BuildTypeItem):
  def __init__(self, name):
    super(BuildTarget, self).__init__()
    self.name = name
    self.title = ''
    self.built_for = set()

  def GetTargets(self):
    return [self]

class Commands(object):
  def __init__(self, args, name=''):
    self.args = args
    self.name = name

class Executable(BuildTypeItem):
  def __init__(self, name, build_targets, commands, options):
    super(Executable, self).__init__()
    self.name = name
    self.title = ''
    self.build_targets = build_targets
    self.commands = commands
    self.options = options
    self.type = 'normal'

  def PrintStep(self, cmd):
    if self.options.print_cmds:
      Options.OutputCommand("$ %s" % ' '.join(cmd))

  def GetExePath(self, build_type):
    # An executable "command" is just a list of parameters to pass to
    # launch the process. Which one is the "executable" is a little nebulous.
    # Our heuristic is the one that exists on disk, and is in the out dir.
    for cmd in self.GetCommands(build_type):
      if os.path.exists(cmd) and options.out_dir in cmd:
        return cmd
    return super(Executable, self).GetExePath()

  def GetCommandToRun(self):
    config_name = None
    if self.options.gyp.valgrind:
      config_name = 'valgrind'
    elif self.options.debugger:
      config_name = 'debug'
    elif self.options.asan:
      config_name = 'asan'

    for cmd in self.commands:
      if config_name:
        if config_name == cmd.name:
          return cmd
      elif cmd.name == 'normal':
        return cmd

    if config_name:
      print >> sys.stderr, "Couldn't find config %s for %s" % (config_name,
                                                               self.name)
      sys.exit(5)
    return self.commands[0]

  def GetCommands(self, build_type, extra_args = None, no_run_commands = None):
    xvfb = ["python", "testing/xvfb.py", "${out_dir}/${Build_type}"]
    bt_lowercase = build_type.lower()
    command = self.GetCommandToRun()
    cmd = copy.copy(command.args)
    if extra_args:
      cmd.extend(extra_args)
    if no_run_commands:
      for arg in no_run_commands:
        if arg in cmd:
          cmd.remove(arg)
    new_cmd = []
    for c in cmd:
      if c == '${xvfb}':
        new_cmd.extend(xvfb)
      else:
        new_cmd.append(c)
    cmd = new_cmd

    for idx in range(len(cmd)):
      cmd[idx] = cmd[idx].replace(r'${Build_type}', build_type)
      cmd[idx] = cmd[idx].replace(r'${build_type}', bt_lowercase)
      cmd[idx] = cmd[idx].replace(r'${jobs}', str(options.jobs))
      cmd[idx] = cmd[idx].replace(r'${out_dir}', str(options.out_dir))
      cmd[idx] = cmd[idx].replace(r'${root_dir}', str(options.root_dir))
      cmd[idx] = cmd[idx].replace(r'${layout_dir}', str(options.layout_dir))
      cmd[idx] = cmd[idx].replace(r'${user_data_img_dir}', str(options.user_data_img_dir))
      cmd[idx] = os.path.expandvars(cmd[idx])
    if self.options.run_args:
      cmd.extend(self.options.run_args)
    return cmd

  def Run(self, build_type, extra_args = None, no_run_commands = None):

    cmd = self.GetCommands(build_type, extra_args, no_run_commands)
    self.PrintStep(cmd)
    run_errors = []
    try:
      if not self.options.noop:
        if self.options.asan:
          asan_symbolize.demangle = True
          loop = asan_symbolize.SymbolizationLoop(binary_name_filter=asan_symbolize.fix_filename)
          p = subprocess.Popen(cmd, stderr=subprocess.PIPE)
          for line in iter(p.stderr.readline, ""):
            print >> sys.stderr, ''.join(loop.process_line(line))
          p.wait()
          if p.returncode:
            raise subprocess.CalledProcessError(returncode=p.returncode, cmd=cmd)
        else:
          subprocess.check_call(cmd)
      if extra_args == None:
        self.MarkDoneFor(build_type)
    except subprocess.CalledProcessError as e:
      run_errors.append(e)
    return run_errors

  def GetTargets(self):
    targets = []
    for target in self.build_targets:
      targets.extend(target.GetTargets())
    return targets

class Run(BuildTypeItem):
  def __init__(self, name, executable, targets, args, no_run_commands):
    super(Run, self).__init__()
    self.name = name
    self.title = ''
    self.executable = executable
    self.targets = targets
    self.args = args
    self.no_run_commands = no_run_commands

  def Run(self, build_type):
    self.MarkDoneFor(build_type)
    return self.executable.Run(build_type, self.args, self.no_run_commands)

  def GetTargets(self):
    if len(self.targets):
      return self.targets
    else:
      return self.executable.GetTargets()

class Collection(BuildTypeItem):
  def __init__(self, name, items):
    super(Collection, self).__init__()
    self.name = name
    self.title = ''
    self.items = items

  def Run(self, build_type):
    errors = []
    for item in self.items:
      if isinstance(item, BuildTarget):
        continue
      if item.WasDoneFor(build_type):
        print 'Skipping "%s": already run' % item.name
      else:
        errors.extend(item.Run(build_type))
    self.MarkDoneFor(build_type)
    return errors

  def GetTargets(self):
    targets = []
    for item in self.items:
      targets.extend(item.GetTargets())
    return targets

class Collections(object):
  def __init__(self, options):
    self.target_names = {}
    self.exe_names = {}
    self.run_names = {}
    self.collection_names = {}
    self.options = options
    self.default = None

  @staticmethod
  def GetDataFilePath():
    return os.path.join(os.path.dirname(__file__), 'collections.json')

  @staticmethod
  def ParseCommands(exe_obj, exe_name):
    if 'commands' in exe_obj:
      cmds = []
      args = copy.copy(exe_obj['commands'])
      for cmd in args:
        new_cmd = Collections.ParseCommands(cmd, exe_name)
        if 'name' in cmd:
          new_cmd[0].name = cmd['name']
        cmds.extend(new_cmd)
      return cmds
    else:
      command = copy.copy(exe_obj['command'])
      for idx in range(len(command)):
        command[idx] = command[idx].replace('${executable_name}', exe_name)
      return [Commands(command)]

  def GetTargets(self):
    targets = []
    for item in self.items:
      targets.extend(item.GetTargets())
    return targets

  def MarkTargetBuilt(self, target_name, build_type):
    self.target_names[target_name].MarkDoneFor(build_type)

  def CreateTarget(self, target_name):
    target = BuildTarget(target_name)
    self.target_names[target_name] = target
    return target

  # Target names are either "<target-name>" or "(<condition>)<target-name>"
  @staticmethod
  def ParseTargetName(target_str):
    reg = re.compile(r'^\(([^\)]+)\)\s*(.+)$')
    m = reg.match(target_str)
    if m:
      return (m.group(1), m.group(2))
    else:
      return (None, target_str)

  def ConditionTrue(self, condition):
    if condition == None:
      return True
    reg = re.compile('^OS([!=]=)[\'"](.*)[\'"]$')
    m = reg.match(condition)
    assert(m)
    op = m.group(1)
    os_name = m.group(2)
    if op == '==' and os_name == self.options.target_os:
      return True
    if op == '!=' and os_name != self.options.target_os:
      return True
    return False

  def ParseExecutable(self, exe_obj, exe_name):
    target_names = []
    if 'targets' in exe_obj:
      for target_name in exe_obj['targets']:
        (condition, tname) = Collections.ParseTargetName(target_name)
        if not self.ConditionTrue(condition):
          continue
        if tname == '${executable_name}':
          target_names.append(exe_name)
        else:
          target_names.append(tname)
    else:
      target_names.append(exe_name)
    targets = []
    for target_name in target_names:
      if target_name in self.target_names:
        targets.append(self.target_names[target_name])
      else:
        target = self.CreateTarget(target_name)
        target.auto_generated = True
        targets.append(target)
    commands = Collections.ParseCommands(exe_obj, exe_name)
    executable = Executable(exe_name, targets, commands, self.options)
    if 'type' in exe_obj:
      executable.type = exe_obj['type']
    if 'title' in exe_obj:
      executable.title = exe_obj['title']
    self.exe_names[exe_name] = executable

  def GetItemName(self, name):
    if name in self.collection_names:
      return self.collection_names[name]
    if name in self.run_names:
      return self.run_names[name]
    if name in self.exe_names:
      return self.exe_names[name]
    if name in self.target_names:
      return self.target_names[name]
    return None

  def GetTargetNames(self):
    return self.target_names.keys()

  def GetExecutableNames(self):
    return self.exe_names.keys()

  def GetRunNames(self):
    return self.run_names.keys()

  def GetCollectionNames(self):
    return self.collection_names.keys()

  def GetAllItemNames(self):
    items = self.GetTargetNames()
    items.extend(self.GetExecutableNames())
    items.extend(self.GetRunNames())
    items.extend(self.GetCollectionNames())
    items = list(set(items))
    return sorted(items)

  def GetItemNames(self, include_auto_generated):
    lines = []
    lines.append("Build target items:")
    for name in sorted(self.target_names.keys()):
      if not include_auto_generated and self.target_names[name].auto_generated:
        continue
      if self.target_names[name].title:
        lines.append("  %s : %s" % (name, self.target_names[name].title))
      else:
        lines.append("  %s" % name)

    lines.append("Executable items:")
    for name in sorted(self.exe_names.keys()):
      if not include_auto_generated and self.exe_names[name].auto_generated:
        continue
      if self.exe_names[name].title:
        lines.append("  %s : %s" % (name, self.exe_names[name].title))
      else:
        lines.append("  %s" % name)

    lines.append("Run items:")
    for name in sorted(self.run_names.keys()):
      if self.run_names[name].title:
        lines.append("  %s : %s" % (name, self.run_names[name].title))
      else:
        lines.append("  %s" % name)

    lines.append("Collection items:")
    for name in sorted(self.collection_names.keys()):
      if self.collection_names[name].title:
        lines.append("  %s : %s" % (name, self.collection_names[name].title))
      else:
        lines.append("  %s" % name)

    return lines

  def CreateStockExecutable(self, exe_name):
    run_args = ["${out_dir}/${Build_type}/%s" % exe_name]
    if exe_name not in self.target_names:
      target = self.CreateTarget(exe_name)
      target.auto_generated = True

    commands = [
        Commands(run_args, ''),
        Commands(['cgdb', '--args'] + run_args, 'debug')
    ]

    exe = Executable(exe_name, [self.target_names[exe_name]], commands, self.options)
    exe.auto_generated = True
    self.exe_names[exe_name] = exe
    return exe

  def LoadDataFile(self):
    file_path = Collections.GetDataFilePath()
    with open(file_path) as f:
      data = json.load(f)
      for target_obj in data['targets']:
        target = self.CreateTarget(target_obj['name'])
        if 'title' in target_obj:
          target.title = target_obj['title']
        self.target_names[target_obj['name']] = target
      for exe_obj in data['executables']:
        if 'name' in exe_obj:
          self.ParseExecutable(exe_obj, exe_obj['name'])
        else:
          for name in exe_obj['names']:
            self.ParseExecutable(exe_obj, name)
      for run_obj in data['runs']:
        run_name = run_obj['name']
        targets = []
        executable = None
        run_args = []
        no_commands = []
        if 'args' in run_obj:
          run_args = run_obj['args']
        if '-commands' in run_obj:
          no_commands = run_obj['-commands']
        if 'executable' in run_obj:
          executable = self.exe_names[run_obj['executable']]
        elif 'targets' in run_obj:
          for target_name in run_obj['targets']:
            if target_name in self.target_names:
              targets.append(self.target_names[target_name])
            else:
              target = self.CreateTarget(target_name)
              self.target_names[target_name] = target
              targets.append(target)
          executable = Executable('no_name', 'build_target',
                                  [Commands(run_args)], self.options)
        else:
          executable = self.exe_names[run_name]
        run = Run(run_name, executable, targets, run_args, no_commands)
        if 'title' in run_obj:
          run.title = run_obj['title']
        self.run_names[run_name] = run
      for collection_obj in data['collections']:
        collection_name = collection_obj['name']
        items = []
        if 'targets' in collection_obj:
          for target_name in collection_obj['targets']:
            items.append(self.target_names[target_name])
        if 'executables' in collection_obj:
          for exe_name in collection_obj['executables']:
            if exe_name not in self.exe_names:
              self.CreateStockExecutable(exe_name)
            items.append(self.exe_names[exe_name])
        if 'runs' in collection_obj:
          for run_name in collection_obj['runs']:
            items.append(self.run_names[run_name])
        collection = Collection(collection_name, items)
        if 'title' in collection_obj:
          collection.title = collection_obj['title']
        self.collection_names[collection_name] = collection
      if 'default' in data:
        self.default = data['default']
        if self.default not in self.GetAllItemNames():
          print 'Unknown default item "%s"' % self.default
          sys.exit(1)

class GClient(object):
  def __init__(self, gclient_path):
    self.contents = GClient.Read(gclient_path)

  @staticmethod
  def Read(gclient_path):
    result = {}
    with open(gclient_path, 'r') as f:
      try:
        exec(f.read(), {}, result)
      except SyntaxError, e:
        e.filename = os.path.abspath(gclient_path)
        raise
    return result

  def GetTargetOS(self):
    if 'target_os' in self.contents:
      if len(self.contents['target_os']) > 1:
        print "Multiple target OS's: using the first"
      return self.contents['target_os'][0]

class Git(object):
  @staticmethod
  def CurrentBranch():
    cmd = ['git', 'rev-parse', '--abbrev-ref', 'HEAD']
    for line in subprocess.check_output(cmd).split():
      return line.strip()
    return None

##
# Values in this class affect how build_gyp generates makefiles.
class GypValues(object):
  def __init__(self, gyp_env_path, branch):
    self.gyp_generator_flags = set()
    self.gyp_defines = set()
    gyp_env = GypValues.ReadGypEnv(gyp_env_path)
    self.target_os = GypValues.GetTargetOS(gyp_env)
    self.SetDefaultGypGenerator(self.target_os)
    self.use_clang = True
    self.use_goma = True
    self.valgrind = False
    self.branch = branch

  def SetDefaultGypGenerator(self, target_os):
    if target_os == 'win':
      self.gyp_generators = 'ninja,msvs'
    else:
      self.gyp_generators = 'ninja'

  @staticmethod
  def ExtractOSValue(env_val):
    """Extract the OS name from the GYP_DEFINES value.
    >>> GypValues.ExtractOSValue("chromeos=1")
    'chromeos'
    >>> GypValues.ExtractOSValue("OS=linux")
    'linux'
    >>> GypValues.ExtractOSValue("some-other=value")
    """
    if env_val == 'chromeos=1':
      return 'chromeos'
    vals = env_val.split('=')
    if len(vals) == 2 and vals[0] == 'OS':
      return vals[1]
    return None

  @staticmethod
  def GetTargetOS(gyp_env_contents):
    if not gyp_env_contents:
      return None
    for env in gyp_env_contents:
      if env == 'GYP_DEFINES':
        for val in gyp_env_contents[env].split():
          os = GypValues.ExtractOSValue(val)
          if os:
            return os
    return None

  @staticmethod
  def ReadGypEnv(gyp_env_path):
    if not os.path.exists(gyp_env_path):
      return
    file_data = {}
    with open(gyp_env_path, 'rU') as f:
      try:
        file_data = eval(f.read(), {'__builtins__': None}, None)
      except SyntaxError, e:
        e.filename = os.path.abspath(gyp_env_path)
        raise
    return file_data

  def WriteToFile(self, fname):
    with open(fname, 'w') as f:
      pickle.dump(self, f)

  @staticmethod
  def ReadFromFile(fname):
    with open(fname, 'r') as f:
      return pickle.load(f)

  def __ne__(self, other):
    if self.gyp_generator_flags != other.gyp_generator_flags:
      return True
    if self.gyp_defines != other.gyp_defines:
      return True
    if self.gyp_generators != other.gyp_generators:
      return True
    if self.use_clang != other.use_clang:
      return True
    if self.use_goma != other.use_goma:
      return True
    if self.valgrind != other.valgrind:
      return True
    if hasattr(other, 'branch'):
      other_branch = other.branch
    else:
      other_branch = ''
    if hasattr(self, 'branch'):
      self_branch = self.branch
    else:
      self_branch = ''
    if self_branch != other_branch:
      return True
    return False

class Options(object):
  def __init__(self):
    self.root_dir = os.path.abspath('.')
    try:
      self.gclient = GClient(self.GetGClientPath())
    except:
      print >> sys.stderr, "ERROR: %s" % self.GetGClientPath()
      print >> sys.stderr, "Are you running from the chrome/src dir?"
      sys.exit(8)
    self.gyp = GypValues(self.GetGypEnvPath(), Git.CurrentBranch())
    self.target_os = self.gyp.target_os
    if not self.target_os:
      # Not specified in chromium.gyp_env file (which is OK) so see if it's
      # in the .gclient file
      self.target_os = self.gclient.GetTargetOS()
      if not self.target_os:
        # Not in .gcient either (also OK), so default to the host OS
        self.target_os = Options.GetHostOS()
      self.gyp.SetDefaultGypGenerator(self.target_os)
    self.collections = Collections(self)
    self.collections.LoadDataFile()
    self.use_gn = False
    self.keep_going = False
    self.debug = False
    self.release = False
    self.user_data_in_image = False
    self.desired_root_path = os.path.join(os.path.expanduser('~'),
                                          'chrome_img_dir')
    self.user_data_img_dir = os.path.join(self.desired_root_path, 'user_data')
    self.img_block_size = 512
    self.img_num_blocks = 50*1024*1024/self.img_block_size
    self.sudo_pwd = None
    self.chromeos_build = 'link'
    self.shared_libraries = True
    self.gyp.gyp_defines.add('disable_nacl=1')
    if self.target_os == 'linux':
      self.gyp.gyp_defines.add('linux_use_debug_fission=0')
    if (self.target_os == 'win' or self.target_os == 'linux') and \
        self.shared_libraries:
      # Should read in chromium.gyp_env and append to those values
      self.gyp.gyp_defines.add('component=shared_library')
    self.verbosity = 0
    self.print_cmds = True
    self.noop = False
    self.regyp = False
    self.goma_path = os.path.join(os.path.expanduser('~'), 'goma')
    if not os.path.exists(self.goma_path):
      self.gyp.use_goma = False
    self.llvm_path = os.path.abspath(os.path.join('third_party', 'llvm-build',
                                                  'Release+Asserts', 'bin'))
    if not os.path.exists(self.llvm_path):
      self.gyp.use_clang = False
    self.clobber = False
    self.active_items = []
    self.debugger = False
    if self.target_os == 'chromeos':
      self.out_dir = 'out_%s' % self.chromeos_build
    else:
      self.out_dir = 'out'
    self.run_args = None
    self.layout_dir = os.path.join(self.root_dir, 'third_party', 'WebKit', 'LayoutTests')
    self.gyp_state_path = os.path.abspath(os.path.join(self.root_dir, '.GYP_STATE'))
    if self.target_os == 'android':
      self.gyp.use_goma = False
      self.gyp.use_clang = False
    self.jobs = multiprocessing.cpu_count()
    self.asan = False
    self.profile = False
    self.profile_file = "/tmp/cpuprofile"
    self.run_targets = True

  @staticmethod
  def OutputColor():
    if platform.system() == 'Windows':
      return False
    else:
      return sys.stdout.isatty()

  @staticmethod
  def OutputCommand(cmd):
    if type(cmd) is list:
      str_cmd = ' '.join(cmd)
    else:
      assert type(cmd) is str or type(cmd) is unicode
      str_cmd = cmd
    if Options.OutputColor():
      print "%s%s%s" % (bcolors.OKBLUE, str_cmd, bcolors.ENDC)
    else:
      print str_cmd

  def PromptForPassword(self):
    self.sudo_pwd = getpass.getpass('Please enter your sudo password (for mount): ')

  def GetActiveTargets(self):
    targets = set()
    for item_name in self.active_items:
      item = self.collections.GetItemName(item_name)
      if item == None:
        print >> sys.stderr, 'Cannot find item "%s"' % item_name
        sys.exit(1)
      for target in item.GetTargets():
        targets.add(target.name)
    return list(targets)

  def GetTopDir(self):
    return os.path.abspath(os.path.join(self.root_dir, '..'))

  def GetGClientPath(self):
    return os.path.join(self.GetTopDir(), '.gclient')

  def GetGypEnvPath(self):
    return os.path.join(self.GetTopDir(), 'chromium.gyp_env')

  # The "host" OS is the one on which the build is taking place.
  @staticmethod
  def GetHostOS():
    if platform.system() == 'Windows':
      return 'win'
    elif platform.system() == 'Linux':
      return 'linux'
    elif platform.system() == 'Darwin':
      return 'mac'
    print >> sys.stderr, "Unknown platform: '%s'" % platform.system()
    sys.exit(1)

  # crbuild -d [<target1>..<targetn>] -- <run_arg1>, <run_argn>
  # argparse can't deal with multiple positional arguments. So before we parse
  # argv we strip off the "bare double dash" args which we pass to an executable
  # *if* we wind up running one.
  def StripRunPositionalArgs(self):
    if '--' in sys.argv:
      positional_start_idx = sys.argv.index('--')
      self.run_args = sys.argv[positional_start_idx+1:]
      sys.argv = sys.argv[:positional_start_idx]

  def Parse(self):
    desc = "A script to compile/test Chromium."
    parser = argparse.ArgumentParser(description=desc,
                                     formatter_class=RawTextHelpFormatter,
                                     epilog='\n'.join(self.collections.GetItemNames(False)))
    parser.add_argument('-d', '--debug', action='store_true',
                        help='Do a debug build (default: debug)')
    parser.add_argument('-r', '--release', action='store_true',
                        help='Do a release build (default: debug)')
    parser.add_argument('-g', '--gyp', action='store_true',
                        help='Re-gyp before building')
    parser.add_argument('-v', '--verbose', action='count',
                        help='Be verbose, can be used multiple times')
    parser.add_argument('-c', '--clobber', action='store_true',
                        help='Delete out dir before building')
    parser.add_argument('-n', '--noop', action='store_true',
                        help="Don't do anything, print what would be done")
    parser.add_argument('-R', '--no-run', action='store_true',
                        help="Do not run targets after building.")
    parser.add_argument('-A', '--asan', action='store_true',
                        help="Do a SyzyASan build")
    parser.add_argument('-p', '--profile', action='store_true',
                        help="Profile the executable")
    parser.add_argument('-j', '--jobs',
                        help="Num jobs when both building & running")
    parser.add_argument('-V', '--valgrind', action='store_true',
                        help="Build for Valgrind (memcheck) (default: %s)" % self.gyp.valgrind)
    parser.add_argument('-D', '--debugger', action='store_true',
                        help="Run the debug executable profile (default: %s)" % self.debugger)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--use-clang', action='store_true',
                        help="Use the clang compiler (default %s)" % self.gyp.use_clang)
    group.add_argument('--no-use-clang', action='store_true',
                        help="Use the clang compiler (default %s)" % (not self.gyp.use_clang))
    parser.add_argument('targets', metavar='TARGET', type=str, nargs='*',
                        help="""Target(s) to build/run. The target name can be one of the
predefined target/executable/run/collection items defined in
collections.json (see below). If not then it is assumed to be
a target defined in the gyp files.""")

    self.StripRunPositionalArgs()
    args = parser.parse_args()
    self.debug = args.debug
    self.release = args.release
    if not self.debug and not self.release:
      self.debug = True
    self.regyp = args.gyp
    self.clobber = args.clobber
    if self.clobber:
      self.regyp = True
    self.verbosity = args.verbose
    if args.noop:
      self.noop = True
    if args.no_run:
      self.run_targets = False
    for target_name in args.targets:
      if self.collections.GetItemName(target_name) == None:
        # Not one of our predefined meta-targets (AKA items), so assume this is
        # a real build target and create a definition for one in our system.
        self.collections.CreateTarget(target_name)
      self.active_items.append(target_name)
    if len(self.active_items) == 0:
      self.active_items.append(self.collections.default)
    if args.use_clang:
      self.gyp.use_clang = True
    elif args.no_use_clang:
      self.gyp.use_clang = False
    if self.gyp.use_clang and not os.path.exists(self.llvm_path):
      print >> sys.stderr, "Can't use clang (llvm path !exists)"
      self.gyp.use_clang = False
    if args.valgrind:
      self.gyp.valgrind = True
    if args.debugger:
      self.debugger = True
    if args.jobs:
      self.jobs = args.jobs
    if args.asan:
      self.asan = True
      if self.target_os == 'linux':
        if args.no_use_clang:
          print >> sys.stderr, "ASAN *is* clang to don't tell me not to use it."
        self.out_dir = 'out_asan'
        self.gyp.gyp_defines.add('asan=1')
        self.gyp.gyp_defines.add('clang=1')
        self.gyp.gyp_defines.add('use_allocator=none')
        self.gyp.gyp_defines.add('enable_ipc_fuzzer=1')
        self.gyp.gyp_defines.add('release_extra_cflags="-g -O1 -fno-inline-functions -fno-inline"')
        self.gyp.gyp_generator_flags.add("output_dir=%s" % self.out_dir)
      elif self.target_os == 'win':
        self.gyp.gyp_defines.add('syzyasan=1')
        self.gyp.gyp_defines.add('chrome_multiple_dll=0')
        self.gyp.gyp_generators = 'ninja'
        # According to docs SyzyASAN not yet compatible shared library.
        self.gyp.gyp_defines.remove('component=shared_library')
        if 'disable_nacl=1' in self.gyp.gyp_defines:
          self.gyp.gyp_defines.remove('disable_nacl=1')
      elif self.target_os == 'android':
        self.gyp.gyp_defines.add('asan=1')
        if self.shared_libraries:
          self.gyp.gyp_defines.add('component=shared_library')
      elif platform.system() == 'mac':
        self.gyp.gyp_defines.add('asan=1')
        self.gyp.gyp_defines.add('target_arch=x64')
        self.gyp.gyp_defines.add('host_arch=x64')
    self.gyp.gyp_defines.add('OS=%s' % self.target_os)
    if args.profile:
      self.profile = True
      self.gyp.gyp_defines.add('profiling=1')

class Builder:
  def __init__(self, options):
    self.options = options
    self.SetEnvVars()

  # Linking on Windows can sometimes fail with this error:
  # LNK1318: Unexpected PDB error; OK (0)
  # This is caused by the Microsoft PDB Server running out of virtual address
  # space. Killing this service fixes this problem.
  def KillPdbServer(self):
    assert self.options.target_os == 'win'
    cmd = "taskkill /F /im mspdbsrv.exe"
    if self.options.print_cmds:
      Options.OutputCommand(cmd)
    if not self.options.noop:
      os.system(cmd)

  @staticmethod
  def PrependToPath(path):
    os.environ['PATH'] = "%s%s%s" % (path, os.pathsep, os.environ['PATH'])

  @staticmethod
  def PrintAllEnvVars():
    for key in sorted(os.environ):
      print "%s=%s" % (key, os.environ[key])

  # The mounted filesystem (initially empty) is root.root, so create a
  # subdirectory writable by me.
  def CreateUserDataDir(self, path, user, group):
    if not os.path.exists(path):
      cmd = ['sudo', '-S', 'mkdir', path]
      p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
      p.communicate("%s\n" % self.options.sudo_pwd)
      if p.returncode:
        raise Exception('Unable to create %s' % path, p.returncode)
    cmd = ['sudo', '-S', '/bin/chown', '%s.%s' % (user, group), path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    p.communicate("%s\n" % self.options.sudo_pwd)
    if p.returncode:
      raise Exception('Unable to change owner of %s' % path, p.returncode)

  def CreateAndMountDiskImage(self):
    if not os.path.exists(self.options.desired_root_path):
      os.mkdir(self.options.desired_root_path)
    mounter = Mounter()
    if not mounter.IsMounted(self.options.desired_root_path):
      image_path = os.path.join(os.path.expanduser('~'), 'chrome_tst.img')
      if not os.path.exists(image_path):
        image_creator = Image()
        image_creator.Create(image_path, self.options.img_block_size,
                             self.options.img_num_blocks)
      if not self.options.sudo_pwd:
        self.options.PromptForPassword()
      mounter.MountImage(image_path, self.options.desired_root_path,
                         self.options.sudo_pwd)
    if not os.path.exists(self.options.user_data_img_dir):
      user = getpass.getuser()
      group = 'eng'
      self.CreateUserDataDir(self.options.user_data_img_dir, user, group)

  def SetEnvVars(self):
    # Copy so as to not modify options
    gyp_defines = copy.copy(self.options.gyp.gyp_defines)
    os.environ['GYP_GENERATORS'] = self.options.gyp.gyp_generators
    if self.options.gyp.use_clang:
      os.environ['CC'] = 'clang'
      os.environ['CXX'] = 'clang++'
      os.environ['builddir_name'] = 'llvm'
      assert os.path.exists(self.options.llvm_path)
      Builder.PrependToPath(self.options.llvm_path)
      gyp_defines.add('clang=1')
    if self.options.gyp.valgrind:
      gyp_defines.add('build_for_tool=memcheck')
    # Must be prepended to PATH last
    if self.options.gyp.use_goma:
      Builder.PrependToPath(self.options.goma_path)
    if 'GYP_DEFINES' in os.environ:
      for prev_val in os.environ['GYP_DEFINES'].split():
        gyp_defines.add(prev_val)
    os.environ['GYP_DEFINES'] = ' '.join(gyp_defines)

    if self.options.verbosity > 0:
      if self.options.verbosity > 2:
        Builder.PrintAllEnvVars()
      else:
        print "Target OS: %s" % self.options.target_os
        print "Host OS: %s" % Options.GetHostOS()
        print "GYP_DEFINES: %s" % os.environ['GYP_DEFINES']
        print "GYP_GENERATORS: %s" % os.environ['GYP_GENERATORS']
        print "PATH: %s" % os.environ['PATH']
      print "Using %s %s goma" %  ('clang' if self.options.gyp.use_clang else 'gcc',
                                   'with' if self.options.gyp.use_goma else
                                   'without')
    if len(self.options.gyp.gyp_generator_flags):
      os.environ['GYP_GENERATOR_FLAGS'] = ' '.join(self.options.gyp.gyp_generator_flags)
    if self.options.profile:
      os.environ['CPUPROFILE'] = self.options.profile_file

  def PrintStep(self, cmd):
    if self.options.print_cmds:
      Options.OutputCommand("$ %s" % ' '.join(cmd))

  def GN(self, build_dir):
    cmd = ['gn', 'gen', build_dir]
    if self.options.print_cmds:
      Options.OutputCommand(' '.join(cmd))
    if self.options.noop:
      return
    subprocess.check_call(cmd)

  def Gyp(self):
    print "Gyp'ing..."
    if self.options.target_os == 'android' or self.options.target_os == 'chromeos':
      cmd = ['gclient', 'runhooks']
    else:
      cmd = ['python', os.path.join('build', 'gyp_chromium')]
    self.PrintStep(cmd)
    if not self.options.noop:
      if os.path.exists(self.options.gyp_state_path):
        os.remove(self.options.gyp_state_path)
      subprocess.check_call(cmd)
    if self.options.verbosity > 1:
      print "Writing GYP state to %s" % self.options.gyp_state_path
    self.options.gyp.WriteToFile(self.options.gyp_state_path)

  def DeleteDir(self, dir_path):
    if os.path.exists(dir_path):
      if self.options.print_cmds:
        Options.OutputCommand("Deleting %s" % dir_path)
      if not self.options.noop:
        shutil.rmtree(dir_path)

  def Clobber(self, build_type):
    print "Deleting intermediate files..."
    if os.path.exists(self.options.gyp_state_path):
      os.remove(self.options.gyp_state_path)
    self.DeleteDir(os.path.join(self.options.out_dir, 'gypfiles'))
    self.DeleteDir(os.path.join(self.options.out_dir, build_type))
    self.DeleteDir(os.path.join(self.options.out_dir, '%s_x64' % build_type))

  def Build(self, build_type, target_names):
    print "Building %s..." % build_type
    assert build_type in ['Debug', 'Release']
    build_dir = os.path.join(self.options.out_dir, build_type)
    cmd = ['ninja', '-C', build_dir]
    if self.options.noop:
      cmd.insert(1, '-n')
    if self.options.verbosity > 1:
      cmd.insert(1, '-v')
    if self.options.gyp.use_goma:
      if self.options.target_os == 'mac':
        cmd[1:1] = ['-j', '100']
      else:
        cmd[1:1] = ['-j', '4000']
    if self.options.keep_going:
      cmd[1:1] = ['-k', '50000']
    if self.options.asan:
      platform_dir = os.path.join(self.options.root_dir,
                                  self.options.out_dir,
                                  build_type)
      os.environ['CHROME_DEVEL_SANDBOX'] = os.path.join(platform_dir,
                                                        'chrome_sandbox')
    cmd.extend(target_names)
    self.PrintStep(cmd)
    try:
      subprocess.check_call(cmd)
      return []
    except subprocess.CalledProcessError as e:
      return [e]

  def GetBuildTypes(self):
    build_types = []
    if self.options.debug:
      build_types.append('Debug')
    if self.options.release:
      build_types.append('Release')
    return build_types

  def NeedToReGyp(self):
    if self.options.use_gn:
      return False
    if self.options.regyp:
      print "Must regyp"
      return True
    try:
      if not os.path.exists(self.options.out_dir):
        return True
      current_gyp = GypValues.ReadFromFile(self.options.gyp_state_path)
      if current_gyp != self.options.gyp:
        if self.options.print_cmds:
          print "Gyp related values have changed, need to regyp"
        return True
      else:
        return False
    except IOError as e:
      if self.options.print_cmds:
        print "Can't get current state, need to regyp"
      return True

  def DoBuild(self):
    build_types = self.GetBuildTypes()

    if self.options.target_os == 'win':
      self.KillPdbServer()

    if self.options.clobber:
      for build_type in build_types:
        self.Clobber(build_type)

    if self.NeedToReGyp():
      self.Gyp()

    # Do all builds in one invocation for best performance
    collections = self.options.collections
    active_target_names = self.options.GetActiveTargets()
    errors = []
    for build_type in build_types:
      if self.options.use_gn:
        self.GN(os.path.join(self.options.out_dir, build_type))
      errors.extend(self.Build(build_type, active_target_names))
      for target_name in active_target_names:
        collections.MarkTargetBuilt(target_name, build_type)
    if len(errors):
      return errors

    if not self.options.run_targets:
      return errors

    if self.options.user_data_in_image:
      self.CreateAndMountDiskImage()

    # Now run all executables
    for build_type in build_types:
      for item_name in self.options.active_items:
        item = collections.GetItemName(item_name)
        print 'Running "%s"...' % item.name
        if isinstance(item, BuildTarget):
          continue
        if item.WasDoneFor(build_type):
          print 'Skipping "%s": already run' % item_name
        else:
          errors.extend(item.Run(build_type))
          if self.options.profile:
            print 'View profile results via "pprof --gv %s %s"' % \
                (item.GetExePath(build_type), self.options.profile_file)
    return errors

def FormatDur(seconds):
  if seconds < 60:
    return "%d sec" % seconds
  if seconds < 3600:
    minutes = int(seconds / 60)
    seconds -= minutes * 60
    return "%02d:%02d" % (minutes, seconds)
  hours = int(seconds / 3600)
  seconds -= hours * 3600
  minutes = int(seconds / 60)
  seconds -= minutes * 60
  return "%02d:%02d:%02d" % (hours, minutes, seconds)

if __name__ == '__main__':
  start = time.time()
  options = Options()
  options.Parse()
  builder = Builder(options)
  errors = builder.DoBuild()
  runtime = time.time() - start
  if len(errors) == 0:
    print "All tasks completed successfully: %s" % FormatDur(runtime)
  else:
    for e in errors:
      if Options.OutputColor():
        beginError = bcolors.FAIL
        endError = bcolors.ENDC
      else:
        beginError = ''
        endError = ''
      print >> sys.stderr, "%sFailed:%s %s, %s" % \
        (beginError, endError, ' '.join(e.cmd), FormatDur(runtime))
    sys.exit(errors[0].returncode)
