#!/usr/bin/env python

import argparse
import copy
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from argparse import RawTextHelpFormatter

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

  def WasDoneFor(self, build_type):
    return build_type in self.done_for

  def MarkDoneFor(self, build_type):
    self.done_for.add(build_type)

class BuildTarget(BuildTypeItem):
  def __init__(self, name):
    super(BuildTarget, self).__init__()
    self.name = name
    self.title = ''
    self.built_for = set()

  def GetTargets(self):
    return [self]

class Commands(object):
  def __init__(self, args):
    self.args = args
    self.name = ''

class Executable(BuildTypeItem):
  def __init__(self, name, build_target, commands, options):
    super(Executable, self).__init__()
    self.name = name
    self.title = ''
    self.build_target = build_target
    self.commands = commands
    self.options = options
    self.type = 'normal'

  def PrintStep(self, cmd):
    if self.options.print_cmds:
      print "$ %s" % ' '.join(cmd)

  def GetCommandToRun(self):
    config_name = None
    if self.options.valgrind:
      config_name = 'valgrind'
    elif self.options.debugger:
      config_name = 'debug'

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

  def Run(self, build_type, extra_args = None):
    bt_lowercase = build_type.lower()
    command = self.GetCommandToRun()
    cmd = copy.copy(command.args)
    if extra_args:
      cmd.extend(extra_args)
    for idx in range(len(cmd)):
      cmd[idx] = cmd[idx].replace(r'${Build_type}', build_type)
      cmd[idx] = cmd[idx].replace(r'${build_type}', bt_lowercase)
      cmd[idx] = os.path.expandvars(cmd[idx])
    if options.run_args:
      cmd.extend(options.run_args)
    self.PrintStep(cmd)
    errors = []
    try:
      if not self.options.noop:
        subprocess.check_call(cmd)
      if extra_args == None:
        self.MarkDoneFor(build_type)
    except subprocess.CalledProcessError as e:
      errors.append(e)
    return errors

  def GetTargets(self):
    return self.build_target.GetTargets()

class Run(BuildTypeItem):
  def __init__(self, name, executable, args):
    super(Run, self).__init__()
    self.name = name
    self.title = ''
    self.executable = executable
    self.args = args

  def Run(self, build_type):
    self.MarkDoneFor(build_type)
    return self.executable.Run(build_type, self.args)

  def GetTargets(self):
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

  def ParseExecutable(self, exe_obj, exe_name):
    if 'target' in exe_obj:
      target_name = exe_obj['target']
    else:
      target_name = exe_name
    if target_name in self.target_names:
      target = self.target_names[target_name]
    else:
      target = self.CreateTarget(target_name)
    commands = Collections.ParseCommands(exe_obj, exe_name)
    executable = Executable(exe_name, target, commands, self.options)
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

  def GetItemNames(self):
    lines = []
    lines.append("Build target items:")
    for name in sorted(self.target_names.keys()):
      if self.target_names[name].title:
        lines.append("  %s : %s" % (name, self.target_names[name].title))
      else:
        lines.append("  %s" % name)

    lines.append("Executable items:")
    for name in sorted(self.exe_names.keys()):
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
        if 'executable' in run_obj:
          executable = self.exe_names[run_obj['executable']]
        else:
          executable = self.exe_names[run_name]
        run_args = []
        if 'args' in run_obj:
          run_args = run_obj['args']
        run = Run(run_name, executable, run_args)
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

class Options(object):
  def __init__(self):
    self.collections = Collections(self)
    self.collections.LoadDataFile()
    self.debug = False
    self.release = False
    self.gyp_defines = set(['disable_nacl=1'])
    if platform.system() == 'Windows':
      self.gyp_generators = 'ninja,msvs'
      # Should read in chromium.gyp_env and append to those values
      self.gyp_defines.add('component=shared_library')
    else:
      self.gyp_generators = 'ninja'
    self.verbosity = 0
    self.print_cmds = False
    self.noop = False
    self.gyp = False
    self.use_goma = True
    self.goma_path = os.path.join(os.path.expanduser('~'), 'goma')
    if not os.path.exists(self.goma_path):
      self.use_goma = False
    self.llvm_path = os.path.abspath(os.path.join('third_party', 'llvm-build',
                                                  'Release+Asserts', 'bin'))
    self.use_clang = True
    if not os.path.exists(self.llvm_path):
      self.use_clang = False
    self.clobber = False
    self.active_items = []
    self.valgrind = False
    self.debugger = False

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

  def Parse(self):
    desc = "A script to compile/test Chromium."
    parser = argparse.ArgumentParser(description=desc,
                                     formatter_class=RawTextHelpFormatter,
                                     epilog='\n'.join(self.collections.GetItemNames()))
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
    parser.add_argument('-a', '--run-arg', action='append',
                        help="Extra args to pass when *running* an executable.")
    parser.add_argument('-V', '--valgrind', action='store_true',
                        help="Build for Valgrind (memcheck) (default: %s)" % self.valgrind)
    parser.add_argument('-D', '--debugger', action='store_true',
                        help="Run the debug executable profile (default: %s)" % self.debugger)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--use-clang', action='store_true',
                        help="Use the clang compiler (default %s)" % self.use_clang)
    group.add_argument('--no-use-clang', action='store_true',
                        help="Use the clang compiler (default %s)" % (not self.use_clang))
    parser.add_argument('targets', metavar='TARGET', type=str, nargs='*',
                        help="""Target(s) to build/run. The target name can be one of the
predefined target/executable/run/collection items defined in
collections.json (see below). If not then it is assumed to be
a target defined in the gyp files.""")

    args = parser.parse_args()
    self.debug = args.debug
    self.release = args.release
    if not self.debug and not self.release:
      self.debug = True
    self.gyp = args.gyp
    self.clobber = args.clobber
    if self.clobber:
      self.gyp = True
    self.verbosity = args.verbose
    if self.verbosity > 0:
      self.print_cmds = True
    if args.noop:
      self.noop = True
      self.print_cmds = True
    for target_name in args.targets:
      if self.collections.GetItemName(target_name) == None:
        # Not one of our predefined meta-targets (AKA items), so assume this is
        # a real build target and create a definition for one in our system.
        self.collections.CreateTarget(target_name)
      self.active_items.append(target_name)
    if len(self.active_items) == 0:
      self.active_items.append(self.collections.default)
    if args.use_clang:
      self.use_clang = True
    elif args.no_use_clang:
      self.use_clang = False
    if self.use_clang and not os.path.exists(self.llvm_path):
      print >> sys.stderr, "Can't use clang (llvm path !exists)"
      self.use_clang = False
    if args.valgrind:
      self.valgrind = True
    if args.debugger:
      self.debugger = True

    self.run_args = args.run_arg

class Builder:
  def __init__(self, options):
    self.options = options
    self.SetEnvVars()

  @staticmethod
  def PrependToPath(path):
    if platform.system() == 'Windows':
      path_delim = ';'
    else:
      path_delim = ':'
    os.environ['PATH'] = "%s%s%s" % (path, path_delim, os.environ['PATH'])

  def SetEnvVars(self):
    # Copy so as to not modify options
    gyp_defines = copy.copy(self.options.gyp_defines)
    os.environ['GYP_GENERATORS'] = self.options.gyp_generators
    if self.options.use_clang:
      os.environ['CC'] = 'clang'
      os.environ['CXX'] = 'clang++'
      os.environ['builddir_name'] = 'llvm'
      assert os.path.exists(self.options.llvm_path)
      Builder.PrependToPath(self.options.llvm_path)
      gyp_defines.add('clang=1')
    if self.options.valgrind:
      gyp_defines.add('build_for_tool=memcheck')
    # Must be prepended to PATH last
    if self.options.use_goma:
      Builder.PrependToPath(self.options.goma_path)
    if 'GYP_DEFINES' in os.environ:
      for prev_val in os.environ['GYP_DEFINES'].split():
        gyp_defines.add(prev_val)
    os.environ['GYP_DEFINES'] = ' '.join(gyp_defines)

    if self.options.verbosity > 0:
      print "GYP_DEFINES: %s" % os.environ['GYP_DEFINES']
      print "GYP_GENERATORS: %s" % os.environ['GYP_GENERATORS']
      print "PATH: %s" % os.environ['PATH']
      print "Using %s %s goma" %  ('clang' if self.options.use_clang else 'gcc',
                                   'with' if self.options.use_goma else
                                   'without')

  def PrintStep(self, cmd):
    if self.options.print_cmds:
      print "$ %s" % ' '.join(cmd)

  def Gyp(self):
    print "Gyp'ing..."
    cmd = ['python', os.path.join('build', 'gyp_chromium')]
    self.PrintStep(cmd)
    if not self.options.noop:
      subprocess.check_call(cmd)

  def DeleteDir(self, dir_path):
    if os.path.exists(dir_path):
      if self.options.print_cmds:
        print "Deleting %s" % dir_path
      if not self.options.noop:
        shutil.rmtree(dir_path)

  def Clobber(self, build_type):
    print "Deleting intermediate files..."
    self.DeleteDir(os.path.join('out', 'gypfiles'))
    self.DeleteDir(os.path.join('out', build_type))
    self.DeleteDir(os.path.join('out', '%s_x64' % build_type))

  def Build(self, build_type, target_names):
    print "Building %s..." % build_type
    assert build_type in ['Debug', 'Release']
    build_dir = os.path.join('out', build_type)
    cmd = ['ninja', '-C', build_dir]
    if self.options.noop:
      cmd.insert(1, '-n')
    if self.options.verbosity > 1:
      cmd.insert(1, '-v')
    if self.options.use_goma:
      cmd[1:1] = ['-j', '1000']
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

  def DoBuild(self):
    build_types = self.GetBuildTypes()

    if self.options.clobber:
      for build_type in build_types:
        self.Clobber(build_type)

    if self.options.gyp:
      self.Gyp()

    # Do all builds in one invocation for best performance
    collections = self.options.collections
    active_target_names = self.options.GetActiveTargets()
    errors = []
    for build_type in build_types:
      errors.extend(self.Build(build_type, active_target_names))
      for target_name in active_target_names:
        collections.MarkTargetBuilt(target_name, build_type)
    if len(errors):
      return errors

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
    return errors

def FormatDur(seconds):
  if seconds < 60:
    return "%d sec" % seconds
  if seconds < 3600:
    minutes = seconds / 60
    seconds -= minutes * 60
    return "%02d:%02d" % (minutes, seconds)
  hours = seconds / 3600
  seconds -= hours * 3600
  minutes = seconds / 60
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
      print >> sys.stderr, "%sFailed:%s %s, %s" % \
          (bcolors.FAIL, bcolors.ENDC, ' '.join(e.cmd), FormatDur(runtime))
    sys.exit(errors[0].returncode)
