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

def GetSourceRoot(dir_in_source_root):
  """Returns the absolute path to the chromium source root given a directory
  inside of that root."""
  candidate = dir_in_source_root
  fingerprints = ['chrome', 'net', 'v8', 'build', 'skia']
  while candidate and not all(
      [os.path.isdir(os.path.join(candidate, fp)) for fp in fingerprints]):
    candidate = os.path.dirname(candidate)
    if candidate == os.sep:
      sys.exit(1)
  return candidate

src_root_dir = GetSourceRoot(os.getcwd())
cmd_subfolder = os.path.realpath(os.path.abspath(os.path.join(src_root_dir,
                                                              'tools',
                                                              'valgrind',
                                                              'asan')))
if cmd_subfolder not in sys.path:
  sys.path.insert(0, cmd_subfolder)
from third_party import asan_symbolize
from fsmounter import Mounter
from fsimage import Image

# This allows us to run crbuild from any subdirectory within the chromium
# source directory. Necessary when building in a Vim terminal.
os.chdir(src_root_dir)

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

  def __str__(self):
    val = self.name
    if self.title:
      val += ' "%s"' % self.title
    if self.built_for:
      val += '[%s]' % ', '.join(self.built_for)
    return val

class Commands(object):
  def __init__(self, args, name=''):
    self.args = args
    self.name = name

  def __str__(self):
    val = 'args: [%s]' % ', '.join(self.args)
    if self.name:
      val += ' name:%s' % self.name
    return val

  def IsBlinkLayoutTest(self):
    return 'third_party/blink/tools/run_web_tests.py' in self.args


class Executable(BuildTypeItem):
  def __init__(self, name, build_targets, commands, options):
    super(Executable, self).__init__()
    self.name = name
    self.title = ''
    self.build_targets = build_targets
    self.commands = commands
    self.options = options
    self.type = 'normal'

  def __str__(self):
    val = 'exe: %s' % self.name
    if self.title:
      val += ' "%s"' % self.title
    return val + ' targets:[%s], commands:[%s], type:%s' % \
        (', '.join([str(t) for t in self.build_targets]),
         ', '.join([str(c) for c in self.commands]), self.type)

  def PrintStep(self, cmd):
    if self.options.print_cmds:
      Options.OutputCommand("$ %s" % ' '.join(cmd))

  def GetExePath(self, build_type):
    # An executable "command" is just a list of parameters to pass to
    # launch the process. Which one is the "executable" is a little nebulous.
    # Our heuristic is the one that exists on disk, and is in the out dir.
    for cmd in self.GetCommands(build_type, self.GetBuildDir(build_type)):
      if os.path.exists(cmd) and options.out_dir in cmd:
        return cmd
    return super(Executable, self).GetExePath()

  def GetCommandToRun(self, config_name):
    cfg_name = None
    if self.options.buildopts.valgrind:
      cfg_name = 'valgrind'
    elif self.options.debugger:
      cfg_name = 'debug'
    elif self.options.buildopts.is_asan:
      cfg_name = 'asan'
    if config_name:
      cfg_name = config_name

    for cmd in self.commands:
      if cfg_name:
        if cfg_name == cmd.name:
          return cmd
      elif cmd.name == 'normal':
        return cmd

    if self.options.buildopts.is_asan:
      cfg_name = None
      for cmd in self.commands:
        if cfg_name:
          if cfg_name == cmd.name:
            return cmd
        elif cmd.name == 'normal':
          return cmd

    if cfg_name and cfg_name != 'normal':
      print >> sys.stderr, "Couldn't find config %s for %s" % (cfg_name,
                                                               self.name)
      sys.exit(5)
    return self.commands[0]

  def GetCommands(self, build_type, build_dir, extra_args = None,
                  no_run_commands = None, omit_xvfb = False,
                  config_name = None):
    xvfb = ["python", "testing/xvfb.py"]
    if False:
      debugger = ['gdb', '--tui']
    else:
      debugger = ['cgdb']
    # In chromium/3d074282ede build_dir was no longer a required arg.
    pass_out_dir = False
    if pass_out_dir:
      xvfb.append("${out_dir}/${Build_type}")
    command = self.GetCommandToRun(config_name)
    cmd = copy.copy(command.args)
    if self.options.use_rr:
      cmd = ['rr', 'record', '-n'] + cmd
    if extra_args:
      cmd.extend(extra_args)
    if no_run_commands:
      for arg in no_run_commands:
        if arg in cmd:
          cmd.remove(arg)
    if options.enable_network_service:
      if command.IsBlinkLayoutTest():
        cmd.append('--additional-driver-flag=--enable-features=NetworkService')
      else:
        cmd.append('--enable-features=NetworkService')

    def FilterArg(arg):
      if not options.test_jobs:
        arg = arg.replace('--test-launcher-jobs=${testjobs}', '')
      if platform.system() == 'Windows':
        arg = arg.replace('${HOME}', '${USERPROFILE}')
      return arg.replace(r'${Build_type}', build_type) \
                .replace(r'${build_type}', build_type.lower()) \
                .replace(r'${jobs}', str(options.jobs)) \
                .replace(r'${testjobs}', str(options.test_jobs)) \
                .replace(r'${out_dir}', str(options.out_dir)) \
                .replace(r'${Build_dir}', build_dir) \
                .replace(r'${root_dir}', str(options.root_dir)) \
                .replace(r'${layout_dir}', str(options.layout_dir)) \
                .replace(r'${user_data_img_dir}', str(options.user_data_img_dir))

    new_cmd = []
    for c in cmd:
      if c == r'${xvfb}':
        if not omit_xvfb:
          new_cmd.extend(xvfb)
      elif c == r'${debugger}':
        new_cmd.extend(debugger)
      else:
        new_cmd.append(os.path.expandvars(FilterArg(c)))
    if self.options.run_args:
      args = [os.path.expandvars(arg) for arg in self.options.run_args]
      new_cmd.extend(args)
    if self.options.gtest:
      new_cmd.append("--gtest_filter='%s'" % self.options.gtest)
    return new_cmd

  def IsGoogleTest(self, cmd):
    return self.type == 'gtest'

  def Run(self, build_type, build_dir, extra_args = None,
          no_run_commands = None):

    # See if this is a google-test based executable.
    add_single_process_tests = False
    raw_cmd = self.GetCommands(build_type, build_dir, extra_args,
                               no_run_commands, omit_xvfb=False,
                               config_name='normal')
    if self.IsGoogleTest(raw_cmd):
      tests = GoogleTest.GetAppTests(raw_cmd)
      if not tests:
        print '%sSkipping: %s (No matching tests)%s' % (bcolors.WARNING,
                                                        self.name,
                                                        bcolors.ENDC)
        return []
      if len(tests) == 1 and not '--single-process-tests' in raw_cmd:
        add_single_process_tests = True

    print 'Running "%s"...' % self.name
    omit_xvfb = not Options.ShouldUseXvfb()
    cmd = self.GetCommands(build_type, build_dir,
                           extra_args, no_run_commands,
                           omit_xvfb=omit_xvfb)
    if add_single_process_tests:
      cmd = [p for p in cmd if p.find('test-launcher-jobs') < 0]
    add_single_process_tests = False
    if add_single_process_tests:
      cmd.append('--single-process')
      cmd.append('--single-process-tests')
    self.PrintStep(cmd)
    run_errors = []
    try:
      if not self.options.noop:
        if self.options.buildopts.is_asan or self.options.buildopts.is_tsan:
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

  def Run(self, build_type, build_dir):
    self.MarkDoneFor(build_type)
    return self.executable.Run(build_type, build_dir,
                               self.args, self.no_run_commands)

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

  def Run(self, build_type, build_dir):
    errors = []
    for item in self.items:
      if isinstance(item, BuildTarget):
        continue
      if item.WasDoneFor(build_type):
        print 'Skipping "%s": already run' % item.name
      else:
        errors.extend(item.Run(build_type, build_dir))
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
    if op == '==' and os_name == self.options.buildopts.target_os:
      return True
    if op == '!=' and os_name != self.options.buildopts.target_os:
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
        Commands(['{debugger}', '--args'] + run_args, 'debug')
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
    if 'target_os' not in self.contents:
      raise 'No target_os in %s' % gclient_path
    self.target_os = self.contents['target_os']
    self.default_target_os = self.target_os[0]

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

class GoogleTest(object):
  @staticmethod
  def GetAppTests(cmd):
    cmd.append('--gtest_list_tests')
    current_class_name = None
    class_re = re.compile(r'^([^\.\s]+\.).*$')
    test_re = re.compile(r'^\s+(\S+).*$')
    test_names = []
    #Options.OutputCommand("$ %s" % ' '.join(cmd))
    for line in subprocess.check_output(cmd).splitlines():
      line = line.rstrip()
      if not len(line):
        continue
      m = class_re.match(line)
      if m:
        current_class_name = m.group(1)
        continue
      if not current_class_name:
        continue
      m = test_re.match(line)
      if m:
        test_names.append(current_class_name + m.group(1))
    return test_names

class Git(object):
  @staticmethod
  def Path():
    if platform.system() == 'Windows':
      return os.path.expanduser(r'~\depot_tools\git.bat')
    else:
      return 'git'

  @staticmethod
  def CurrentBranch():
    cmd = [Git.Path(), 'rev-parse', '--abbrev-ref', 'HEAD']
    for line in subprocess.check_output(cmd).split():
      return line.strip()
    return None

class GN(object):
  @staticmethod
  def ArgsFName(build_dir):
    return os.path.join(build_dir, 'args.gn')

  @staticmethod
  def ArgsSupplemental():
    return os.path.join(os.path.dirname(os.path.realpath(__file__)),
                        'api_keys.txt')

  @staticmethod
  def ReadFile(f):
    args = {}
    for line in f.readlines():
      line = line.strip()
      if re.match('^#', line):
        continue
      vals = line.strip().split('=')
      if len(vals) == 2:
        args[vals[0].strip()] = vals[1].strip()
    return args

  @staticmethod
  def GetArgs(build_dir, all_args=False):
    if all_args:
      args = {}
      cmd = ['gn', 'args', build_dir, '--list', '--short']
      for line in subprocess.check_output(cmd).splitlines():
        vals = line.strip().split('=')
        if len(vals) == 2:
          args[vals[0].strip()] = vals[1].strip()
      return args
    return GN.ReadFile(open(GN.ArgsFName(build_dir)))

  @staticmethod
  def BuildArgs(options):
    args = {}
    args['dcheck_always_on'] = str(options.buildopts.dcheck_always_on).lower()
    if options.buildopts.is_asan:
      args['is_asan'] = str(options.buildopts.is_asan).lower()
    args['is_chrome_branded'] = str(options.buildopts.is_chrome_branded).lower()
    args['is_clang'] = str(options.buildopts.use_clang).lower()
    args['is_component_build'] = str(options.buildopts.is_component_build).lower()
    args['is_debug'] = str(options.buildopts.is_debug).lower()
    if options.buildopts.is_lsan:
      args['is_lsan'] = str(options.buildopts.is_lsan).lower()
    if options.buildopts.is_msan:
      args['is_msan'] = str(options.buildopts.is_msan).lower()
    args['is_official_build'] = str(options.buildopts.is_official_build).lower()
    if options.buildopts.is_tsan:
      args['is_tsan'] = str(options.buildopts.is_tsan).lower()
    args['target_os'] = '"%s"' % options.buildopts.target_os
    args['use_goma'] = str(options.buildopts.use_goma).lower()
    if options.buildopts.use_libfuzzer:
      args['use_libfuzzer'] = str(options.buildopts.use_libfuzzer).lower()
    if platform.system() == 'Windows':
      args['is_win_fastlink'] = str(options.buildopts.use_goma).lower()
      args['symbol_level'] = '2' if options.buildopts.is_official_build else '1'
    if options.buildopts.enable_profiling:
      args['enable_profiling'] = 'true'
    if options.buildopts.enable_cros_assistant:
      args['enable_cros_assistant'] = 'true'
    if options.buildopts.enable_callgrind:
      args['enable_callgrind'] = 'true'
    if options.buildopts.use_goma:
      args['goma_dir'] = '"%s"' % options.goma_path
    if options.buildopts.is_asan or options.buildopts.is_tsan:
      args['symbol_level'] = '1'
      if not options.buildopts.is_tsan:
        args['enable_full_stack_frames_for_profiling'] = 'true'
      args['strip_absolute_paths_from_debug_symbols'] = 'true'
    if (options.buildopts.use_libfuzzer or
        options.buildopts.is_asan or
        options.buildopts.is_tsan or
        options.buildopts.is_tsan):
      args['enable_nacl'] = 'false'
    # All of a sudden all nacl builds started failing, so just disabled for
    # all platforms (5/4/2019).
    args['enable_nacl'] = 'false'
    if os.path.exists(GN.ArgsSupplemental()):
      supplimental_args = GN.ReadFile(open(GN.ArgsSupplemental()))
      for k in supplimental_args:
        args[k] = supplimental_args[k]
    if options.buildopts.is_cfi and not options.buildopts.is_official_build:
      args['is_cfi'] = 'true'
      args['use_cfi_cast'] = 'true'
      args['use_cfi_diag'] = 'true'
      args['use_thin_lto'] = 'true'
      # args['strip_absolute_paths_from_debug_symbols'] = 'true'
    return args

  @staticmethod
  def PutArgs(build_dir, args):
    args_fname = GN.ArgsFName(build_dir)
    if not os.path.exists(args_fname):
      open(args_fname, 'a').close() # Create empty file
    existing_args = GN.GetArgs(build_dir)
    existing_args.update(args)
    with open(GN.ArgsFName(build_dir), 'w') as f:
      print >> f, '# Build arguments go here. Examples:'
      print >> f, '#   is_component_build = true'
      print >> f, '#   is_debug = false'
      print >> f, '# See "gn args <out_dir> --list" for available build arguments.'
      print >> f
      for arg in sorted(args):
        print >> f, "%s = %s" % (arg, args[arg])

  @staticmethod
  def Gen(build_dir, options):
    cmd = ['gn', 'gen', build_dir]
    if options.print_cmds:
      Options.OutputCommand(' '.join(cmd))
    if options.noop:
      return
    # If build_dir doesn't exist then Windows fails with default shell=False
    subprocess.check_call(cmd, shell=platform.system() == 'Windows')

##
# Values in this class affect how build_gyp generates makefiles.
class BuildSettings(object):
  def __init__(self, gyp_env_path, branch, target_os):
    self.gyp_generator_flags = set()
    self.gyp_defines = set()
    gyp_env = BuildSettings.ReadGypEnv(gyp_env_path)
    self.target_os = target_os
    self.SetDefaultGypGenerator(self.target_os)
    self.branch = branch
    self.dcheck_always_on = True
    self.enable_callgrind = False
    self.enable_profiling = False
    self.enable_cros_assistant = False
    self.is_asan = False
    self.is_cfi = False
    self.is_chrome_branded = False
    self.is_component_build = True
    self.is_debug = True
    self.is_lsan = False
    self.is_msan = False
    self.is_official_build = False
    self.is_tsan = False
    self.use_clang = True
    self.use_goma = True
    self.use_libfuzzer = False
    self.valgrind = False
    self.target_cpu = None

  def SetDefaultGypGenerator(self, target_os):
    self.gyp_generators = 'ninja'

  @staticmethod
  def ExtractOSValue(env_val):
    """Extract the OS name from the GYP_DEFINES value.
    >>> BuildSettings.ExtractOSValue("chromeos=1")
    'chromeos'
    >>> BuildSettings.ExtractOSValue("OS=linux")
    'linux'
    >>> BuildSettings.ExtractOSValue("some-other=value")
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
          os = BuildSettings.ExtractOSValue(val)
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
    if self.dcheck_always_on != other.dcheck_always_on:
      return True
    if self.is_asan != other.is_asan:
      return True
    if self.is_chrome_branded != other.is_chrome_branded:
      return True
    if self.is_component_build != other.is_component_build:
      return True
    if self.is_debug != other.is_debug:
      return True
    if self.enable_callgrind != other.enable_callgrind:
      return True
    if self.enable_profiling != other.enable_profiling:
      return True
    if self.is_cfi != other.is_cfi:
      return True
    if self.is_lsan != other.is_lsan:
      return True
    if self.is_msan != other.is_msan:
      return True
    if self.is_official_build != other.is_official_build:
      return True
    if self.is_tsan != other.is_tsan:
      return True
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
    if self.use_libfuzzer != other.use_libfuzzer:
      return True
    if self.target_os != other.target_os:
      return True
    if self.target_cpu != other.target_cpu:
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
    self.root_dir = src_root_dir
    try:
      self.gclient = GClient(self.GetGClientPath())
    except:
      print >> sys.stderr, "ERROR: %s" % self.GetGClientPath()
      print >> sys.stderr, "Are you running from the chrome/src dir?"
      sys.exit(8)
    self.buildopts = BuildSettings(self.GetGypEnvPath(), Git.CurrentBranch(),
                                   self.gclient.default_target_os)
    self.collections = Collections(self)
    self.collections.LoadDataFile()
    self.use_gn = True
    self.keep_going = False
    self.user_data_in_image = False
    self.desired_root_path = os.path.join(os.path.expanduser('~'),
                                          'chrome_img_dir')
    self.user_data_img_dir = os.path.join(self.desired_root_path, 'user_data')
    self.img_block_size = 512
    self.img_num_blocks = 50*1024*1024/self.img_block_size
    self.sudo_pwd = None
    self.enable_network_service = False
    self.buildopts.gyp_defines.add('disable_nacl=1')
    self.verbosity = 0
    self.print_cmds = True
    self.noop = False
    self.regyp = False
    self.goma_path = os.path.join(os.path.expanduser('~'), 'goma')
    if self.buildopts.use_goma:
      self.buildopts.use_goma = self.CanUseGoma()
    self.llvm_path = os.path.abspath(os.path.join('third_party', 'llvm-build',
                                                  'Release+Asserts', 'bin'))
    if not os.path.exists(self.llvm_path):
      self.buildopts.use_clang = False
    self.clobber = False
    self.active_items = []
    self.debugger = False
    self.out_dir = 'out'
    self.use_rr = False
    self.run_args = None
    self.layout_dir = os.path.join(self.root_dir, 'third_party', 'WebKit',
                                   'LayoutTests')
    self.gyp_state_path = os.path.abspath(os.path.join(self.root_dir,
                                                       '.GYP_STATE'))
    self.jobs = int(multiprocessing.cpu_count() * 120 / 100)
    self.test_jobs = self.jobs
    self.profile = False
    # https://chromium.googlesource.com/chromium/src/+/master/docs/profiling.md
    self.heap_profiling = False
    self.profile_file = "/tmp/cpuprofile"
    self.run_targets = True
    self.gtest = None

  def IsGomaRunning(self):
    if not os.path.exists(self.goma_path):
      print "Can't find goma at %s" % self.goma_path
      return False
    return True

  def CanUseGoma(self):
    return self.IsGomaRunning()

  @staticmethod
  def CanDoGUI():
    return 'DISPLAY' in os.environ

  @staticmethod
  def ShouldUseXvfb():
    return Options.GetHostOS() == 'linux'

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
    self.sudo_pwd = getpass.getpass('Please enter your sudo'
                                    ' password (for mount): ')

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

  @staticmethod
  def str2bool(v):
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
      return True
    if v.lower() in ('no', 'false', 'f', 'n', '0'):
      return False
    raise argparse.ArgumentTypeError('Boolean value expected.')

  @staticmethod
  def FixupGoogleTestFilterArgs(val):
    """Parse the --gtest options for --gtest_filter.
    >>> Options.FixupGoogleTestFilterArgs(None) is None
    True
    >>> Options.FixupGoogleTestFilterArgs('') is None
    True
    >>> Options.FixupGoogleTestFilterArgs("foobar")
    ':foobar:'
    >>> Options.FixupGoogleTestFilterArgs(":foobar")
    ':foobar:'
    >>> Options.FixupGoogleTestFilterArgs(":foobar:")
    ':foobar:'
    """
    # prefix/suffixing tests with ':' shouldn't be necessary according to
    # https://github.com/google/googletest/blob/master/googletest/docs/V1_7_AdvancedGuide.md#running-a-subset-of-the-tests
    # but experimentation indicates otherwise.
    if val == None:
      return None
    if val.strip() == '':
      return None
    ret = val
    if not ret.startswith(':'):
      ret = ':' + ret
    if not ret.endswith(':'):
      ret = ret + ':'
    return ret

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
    parser.add_argument('-N', '--s13n', action='store_true',
                        help="Enable the network service")
    parser.add_argument('-R', '--no-run', action='store_true',
                        help="Do not run targets after building.")
    parser.add_argument('--cfi',
                        type=Options.str2bool, nargs='?',
                        const=True, default=self.buildopts.is_cfi,
                        help="Do a CFI build (release only) (default: %s)." % \
                        self.buildopts.is_cfi)
    parser.add_argument('-A', '--asan', action='store_true',
                        help="Do a SyzyASan build")
    parser.add_argument('-t', '--tsan', action='store_true',
                        help="Do a TSan build")
    parser.add_argument('-l', '--lsan', action='store_true',
                        help="Do a LSan build")
    parser.add_argument('-m', '--msan', action='store_true',
                        help="Do a MSan build")
    parser.add_argument('-C', '--component',
                        type=Options.str2bool, nargs='?',
                        const=True, default=self.buildopts.is_component_build,
                        help="Do a component build (default: %s)." % \
                        self.buildopts.is_component_build)
    parser.add_argument('--dcheck',
                        type=Options.str2bool, nargs='?',
                        const=True, default=self.buildopts.dcheck_always_on,
                        help="Always enable DCHECK (default: %s)." % \
                        self.buildopts.dcheck_always_on)
    parser.add_argument('--official',
                        type=Options.str2bool, nargs='?',
                        const=True, default=self.buildopts.is_official_build,
                        help="Do an official (default: %s)." % \
                        self.buildopts.is_official_build)
    parser.add_argument('--branded',
                        type=Options.str2bool, nargs='?',
                        const=True, default=self.buildopts.is_chrome_branded,
                        help="Do a Chrome branded build (default: %s)." % \
                        self.buildopts.is_chrome_branded)
    parser.add_argument('--goma',
                        type=Options.str2bool, nargs='?',
                        const=True, default=self.buildopts.use_goma,
                        help="Use goma for building (default: %s)." % \
                        self.buildopts.use_goma)
    parser.add_argument('--os', type=str, nargs=1, help='The target OS')
    parser.add_argument('--cpu', type=str, nargs=1, help='The target CPU '
                                                         'architecture')
    parser.add_argument('-p', '--profile', action='store_true',
                        help="Profile the executable")
    parser.add_argument('-j', '--jobs',
                        help="Num jobs when both building & running")
    parser.add_argument('--rr', action='store_true',
                        help="Record app using rr (https://rr-project.org/)")
    parser.add_argument('--fuzzer', action='store_true',
                        help="Do a fuzzer build (implies asan).")
    parser.add_argument('-V', '--valgrind', action='store_true',
                        help="Build for Valgrind (memcheck) (default: %s)" % self.buildopts.valgrind)
    parser.add_argument('-D', '--debugger', action='store_true',
                        help="Run the debug executable profile (default: %s)" % self.debugger)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--use-clang', action='store_true',
                        help="Use the clang compiler (default %s)" % self.buildopts.use_clang)
    group.add_argument('--no-use-clang', action='store_true',
                        help="Use the clang compiler (default %s)" % (not self.buildopts.use_clang))
    parser.add_argument('--gtest', type=str,
                        help="The string to pass to the --gtest_filter parameter.")
    parser.add_argument('targets', metavar='TARGET', type=str, nargs='*',
                        help="""Target(s) to build/run. The target name can be one of the
predefined target/executable/run/collection items defined in
collections.json (see below). If not then it is assumed to be
a target defined in the gyp files.""")

    self.StripRunPositionalArgs()
    args = parser.parse_args()
    if args.debug and args.release:
      print >> sys.stderr, "Can only do debug OR release, not both."
      sys.exit(1)
    if args.debug:
      self.buildopts.is_debug = True
    elif args.release:
      self.buildopts.is_debug = False
    self.regyp = args.gyp
    self.clobber = args.clobber
    if self.clobber:
      self.regyp = True
    self.verbosity = args.verbose
    self.buildopts.dcheck_always_on = args.dcheck
    self.buildopts.is_chrome_branded = args.branded
    self.buildopts.is_component_build = args.component
    self.buildopts.is_official_build = args.official
    self.buildopts.use_goma = args.goma
    if self.buildopts.is_official_build and self.buildopts.is_component_build:
      print >> sys.stderr, 'Official builds cannot be component builds.'
      sys.exit(1)
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
      self.buildopts.use_clang = True
    elif args.no_use_clang:
      self.buildopts.use_clang = False
    if self.buildopts.use_clang and not os.path.exists(self.llvm_path):
      print >> sys.stderr, "Can't use clang (llvm path !exists)"
      self.buildopts.use_clang = False
    if args.valgrind:
      self.buildopts.valgrind = True
    if args.debugger:
      self.debugger = True
    if args.jobs:
      self.jobs = args.jobs
    if args.fuzzer:
      self.buildopts.use_libfuzzer = True
      self.buildopts.is_asan = True
    if args.lsan or args.asan:
      self.buildopts.is_lsan = True
      self.buildopts.is_asan = True
    if args.s13n:
      self.enable_network_service = True
    if args.msan:
      self.buildopts.is_msan = True
    if args.rr:
      self.use_rr = True
    self.buildopts.is_cfi = args.cfi
    if self.buildopts.is_cfi:
      if self.buildopts.is_debug:
        print >> sys.stderr, 'CFI build is release build only.'
        sys.exit(1)
      if self.buildopts.is_component_build:
        print >> sys.stderr, 'CFI build is static build only.'
        sys.exit(1)
    if args.os:
      self.buildopts.target_os = args.os[0]
      print "Target OS is now", self.buildopts.target_os
      if self.buildopts.target_os not in self.gclient.target_os:
        print >> sys.stderr, '%s must be one of %s' % \
            (self.buildopts.target_os, self.gclient.target_os)
    if args.cpu:
      self.buildopts.target_cpu = args.cpu[0]
      valid_cpus = ('x86', 'x64', 'arm', 'arm64', 'mipsel', 'mips64el')
      if not self.buildopts.target_cpu in valid_cpus:
        print >> sys.stderr, '"%s" is not a valid CPU. Must be one of %s' \
            % (self.buildopts.target_cpu, valid_cpus)
        sys.exit(1)
    if self.buildopts.target_os == 'linux':
      self.buildopts.gyp_defines.add('linux_use_debug_fission=0')
    if ((self.buildopts.target_os == 'win' or
         self.buildopts.target_os == 'linux') and
        self.buildopts.is_component_build):
      # Should read in chromium.gyp_env and append to those values
      self.buildopts.gyp_defines.add('component=shared_library')
    if args.tsan:
      self.buildopts.is_tsan = True
      self.buildopts.is_component_build = False
      # Apparently TSan supports goma now.
      #self.buildopts.use_goma = False
    if self.buildopts.is_asan:
      self.buildopts.is_component_build = False
      if self.buildopts.target_os == 'linux':
        if args.no_use_clang:
          print >> sys.stderr, "ASan *is* clang to don't tell me not to use it."
        self.buildopts.gyp_defines.add('asan=1')
        self.buildopts.gyp_defines.add('lsan=1')
        self.buildopts.gyp_defines.add('clang=1')
        self.buildopts.gyp_defines.add('use_allocator=none')
        self.buildopts.gyp_defines.add('enable_ipc_fuzzer=1')
        self.buildopts.gyp_defines.add('release_extra_cflags="-g -O1 '
                                       '-fno-inline-functions -fno-inline"')
        self.buildopts.gyp_generator_flags.add("output_dir=%s" % self.out_dir)
      elif self.buildopts.target_os == 'win':
        self.buildopts.gyp_defines.add('syzyasan=1')
        self.buildopts.gyp_defines.add('win_z7=1')
        self.buildopts.gyp_defines.add('chromium_win_pch=0')
        self.buildopts.gyp_defines.add('chrome_multiple_dll=0')
        self.buildopts.gyp_generators = 'ninja'
        # According to docs SyzyASan not yet compatible shared library.
        if 'component=shared_library' in self.buildopts.gyp_defines:
          self.buildopts.gyp_defines.remove('component=shared_library')
        self.buildopts.gyp_defines.add('component=static_library')
        if 'disable_nacl=1' in self.buildopts.gyp_defines:
          self.buildopts.gyp_defines.remove('disable_nacl=1')
      elif self.buildopts.target_os == 'android':
        self.buildopts.gyp_defines.add('asan=1')
        if self.buildopts.is_component_build:
          self.buildopts.gyp_defines.add('component=shared_library')
      elif platform.system() == 'mac':
        self.buildopts.gyp_defines.add('asan=1')
        self.buildopts.gyp_defines.add('target_arch=x64')
        self.buildopts.gyp_defines.add('host_arch=x64')
    self.buildopts.gyp_defines.add('OS=%s' % self.buildopts.target_os)
    if options.heap_profiling:
      if not self.buildopts.is_debug:
        print >> sys.stderr, 'Heap profiling requires a debug build.'
        sys.exit(1)
      self.buildopts.enable_profiling = True
      self.buildopts.enable_callgrind = True
    if args.profile:
      self.profile = True
      self.buildopts.gyp_defines.add('profiling=1')
    if self.buildopts.is_asan and self.buildopts.is_debug:
      print >> sys.stderr, "ASan only works on a release build."
      sys.exit(1)
    if self.buildopts.is_msan and self.buildopts.is_debug:
      print >> sys.stderr, "MSan only works on a release build."
      sys.exit(1)
    if self.buildopts.is_tsan and self.buildopts.is_debug:
      print >> sys.stderr, "TSan only works on a release build."
      sys.exit(1)
    if self.buildopts.is_tsan and self.buildopts.is_asan:
      print >> sys.stderr, "Can't do both TSan and ASan builds."
      sys.exit(1)
    self.gtest = Options.FixupGoogleTestFilterArgs(args.gtest)

class Builder:
  def __init__(self, options):
    self.options = options
    self.SetEnvVars()

  # Linking on Windows can sometimes fail with this error:
  # LNK1318: Unexpected PDB error; OK (0)
  # This is caused by the Microsoft PDB Server running out of virtual address
  # space. Killing this service fixes this problem.
  def KillPdbServer(self):
    assert self.options.buildopts.target_os == 'win'
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
    gyp_defines = copy.copy(self.options.buildopts.gyp_defines)
    if False and self.options.buildopts.is_asan:
      os.environ['ASAN_OPTIONS'] = 'detect_leaks=1'
    os.environ['GYP_GENERATORS'] = self.options.buildopts.gyp_generators
    if self.options.buildopts.use_clang:
      os.environ['CC'] = 'clang'
      os.environ['CXX'] = 'clang++'
      os.environ['builddir_name'] = 'llvm'
      assert os.path.exists(self.options.llvm_path)
      Builder.PrependToPath(self.options.llvm_path)
      gyp_defines.add('clang=1')
    if self.options.buildopts.valgrind:
      gyp_defines.add('build_for_tool=memcheck')
    # Must be prepended to PATH last
    if self.options.buildopts.use_goma:
      Builder.PrependToPath(self.options.goma_path)
    if 'GYP_DEFINES' in os.environ:
      for prev_val in os.environ['GYP_DEFINES'].split():
        gyp_defines.add(prev_val)
    if self.options.buildopts.use_goma:
        gyp_defines.add('win_z7=0')
    os.environ['GYP_DEFINES'] = ' '.join(gyp_defines)

    if self.options.verbosity > 0:
      if self.options.verbosity > 2:
        Builder.PrintAllEnvVars()
      else:
        print "Target OS: %s" % self.options.buildopts.target_os
        print "Host OS: %s" % Options.GetHostOS()
        print "Official: %s" % str(self.options.buildopts.is_official_build)
        print "GYP_DEFINES: %s" % os.environ['GYP_DEFINES']
        print "GYP_GENERATORS: %s" % os.environ['GYP_GENERATORS']
        print "PATH: %s" % os.environ['PATH']
      print "Using %s %s goma" %  ('clang' if self.options.buildopts.use_clang else 'gcc',
                                   'with' if self.options.buildopts.use_goma else
                                   'without')
    if len(self.options.buildopts.gyp_generator_flags):
      os.environ['GYP_GENERATOR_FLAGS'] = ' '.join(self.options.buildopts.gyp_generator_flags)
    if self.options.profile:
      os.environ['CPUPROFILE'] = self.options.profile_file

  def PrintStep(self, cmd):
    if self.options.print_cmds:
      Options.OutputCommand("$ %s" % ' '.join(cmd))

  # https://code.google.com/p/syzygy/wiki/SyzyASanBug
  def Instrument_SyzyASan(self, build_dir):
    syzygy_exes = os.path.join('third_party', 'syzygy', 'binaries', 'exe')
    instrument_exe = os.path.join(syzygy_exes, 'instrument.exe')
    input_chrome_dll = os.path.join(build_dir, 'chrome.dll')
    output_chrome_dll = os.path.join(build_dir, 'chrome_syzygy.dll')
    cmd = [instrument_exe,
           '--mode=asan',
           '--overwrite',
           '--input-image=%s' % input_chrome_dll,
           '--output-image=%s' % output_chrome_dll,
           '--debug-friendly']
    if self.options.print_cmds:
      Options.OutputCommand(cmd)
    if not self.options.noop:
      if os.path.exists(output_chrome_dll):
        in_time = os.path.getmtime(input_chrome_dll)
        out_time = os.path.getmtime(output_chrome_dll)
        if out_time > in_time:
          print "No need to re Syzy chrome"
          return
        os.remove(output_chrome_dll)
      subprocess.check_call(cmd)
      shutil.copyfile(os.path.join(syzygy_exes, 'syzyasan_rtl.dll'),
                      os.path.join(build_dir, 'syzyasan_rtl.dll'))

  def Gyp(self):
    print "Gyp'ing..."
    if self.options.buildopts.target_os in ('android', 'chromeos'):
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
    self.options.buildopts.WriteToFile(self.options.gyp_state_path)

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
    self.DeleteDir(os.path.join(self.GetBuildDir(build_type)))
    self.DeleteDir(os.path.join(self.options.out_dir, '%s_x64' % build_type))

  def Build(self, build_type, target_names):
    print "Building %s..." % build_type
    build_dir = self.GetBuildDir(build_type)
    cmd = ['ninja', '-C', build_dir, '-l', '40']
    if self.options.noop:
      cmd.insert(1, '-n')
    if self.options.verbosity > 1:
      cmd.insert(1, '-v')
    if self.options.buildopts.use_goma:
      if self.options.buildopts.target_os == 'mac':
        cmd[1:1] = ['-j', '100']
      else:
        cmd[1:1] = ['-j', '4096']
    if self.options.keep_going:
      cmd[1:1] = ['-k', '50000']
    if self.options.buildopts.is_asan:
      platform_dir = os.path.join(self.options.root_dir,
                                  self.GetBuildDir(build_type))
      os.environ['CHROME_DEVEL_SANDBOX'] = os.path.join(platform_dir,
                                                        'chrome_sandbox')
    cmd.extend(target_names)
    self.PrintStep(cmd)
    try:
      subprocess.check_call(cmd)
      if (self.options.buildopts.is_asan and
          self.options.buildopts.target_os == 'win'):
        self.Instrument_SyzyASan(build_dir)
      return []
    except subprocess.CalledProcessError as e:
      return [e]

  def GetBuildTypes(self):
    build_types = []
    if self.options.buildopts.is_debug:
      build_types.append('Debug')
    else:
      if self.options.buildopts.is_asan:
        build_types.append('asan')
      elif self.options.buildopts.is_tsan:
        build_types.append('tsan')
      elif self.options.buildopts.is_lsan:
        build_types.append('lsan')
      elif self.options.buildopts.is_msan:
        build_types.append('msan')
      else:
        build_types.append('Release')
    return build_types

  def GetBaseBuildDir(self, build_type):
    """Return the relative path to the build dir - e.g. out/Debug."""
    assert build_type in ['Debug', 'Release', 'asan', 'tsan', 'lsan', 'msan']
    dir_name = build_type
    if self.options.buildopts.target_os != self.options.gclient.default_target_os:
      dir_name += '-%s' % self.options.buildopts.target_os
    if self.options.buildopts.is_official_build:
      dir_name = 'Official-' + dir_name
    if self.options.buildopts.target_cpu:
      dir_name += '-' + self.options.buildopts.target_cpu

    return dir_name

  def GetBuildDir(self, build_type):
    """Return the full path to the build dir - e.g. src/dir/out/Debug."""
    return os.path.join(self.options.out_dir, self.GetBaseBuildDir(build_type))

  def NeedToReGyp(self):
    if self.options.use_gn:
      return False
    if self.options.regyp:
      print "Must regyp"
      return True
    try:
      if not os.path.exists(self.options.out_dir):
        return True
      current_gyp = BuildSettings.ReadFromFile(self.options.gyp_state_path)
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

  def NeedToReGN(self, build_type):
    if self.options.use_gn:
      try:
        existing_args = GN.GetArgs(self.GetBuildDir(build_type))
        preferred_args = GN.BuildArgs(self.options)
        return existing_args != preferred_args
      except IOError:
        # File not found (likely).
        return True
    return False

  def DoBuild(self):
    build_types = self.GetBuildTypes()

    if self.options.buildopts.target_os == 'win':
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
      if self.NeedToReGN(build_type):
        build_dir = self.GetBuildDir(build_type)
        if not os.path.isdir(build_dir):
          # This creates the directory.
          GN.Gen(build_dir, self.options)
        GN.PutArgs(build_dir, GN.BuildArgs(self.options))
        GN.Gen(build_dir, self.options)
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
        if isinstance(item, BuildTarget):
          continue
        if item.WasDoneFor(build_type):
          print 'Skipping "%s": already run' % item_name
        else:
          errors.extend(item.Run(build_type, self.GetBuildDir(build_type)))
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
