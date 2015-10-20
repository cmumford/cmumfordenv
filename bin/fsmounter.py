import os
import subprocess

class NoDirException(Exception):
  pass

class DirNotEmptyException(Exception):
  pass

class NoPassword(Exception):
  pass

class Mounter(object):
  def __init__(self):
    pass

  @staticmethod
  def IsDirEmpty(path):
    if not os.path.exists(path):
      raise NoDirException(path)
    return os.listdir(path) == []

  def GetMountedDevices(self):
    cmd = ['mount', '-l']
    dir_map = {}
    for line in subprocess.check_output(cmd).splitlines():
      items = line.split()
      if len(items) >= 3 and items[1] == 'on':
        dir_map[items[2]] = items[0]
    return dir_map

  def IsMounted(self, path):
    return path in self.GetMountedDevices()

  def MountImage(self, img_path, mount_dir, sudo_pwd):
    if not Mounter.IsDirEmpty(mount_dir):
      raise DirNotEmptyException(mount_dir)
    if not sudo_pwd:
      raise NoPassword('Must supply sudo password')
    cmd = ['sudo', '-S', 'mount', '-o', 'loop', img_path, mount_dir]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    p.communicate("%s\n" % sudo_pwd)
    if p.returncode:
      raise Exception('Mount failed', p.returncode)

  def Unmount(self, mount_dir, sudo_pwd, force=False):
    cmd = ['sudo', '-S', 'umount', mount_dir]
    if force:
      cmd.insert(3, '-l')
    print ' '.join(cmd)
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    p.communicate("%s\n" % sudo_pwd)
    if p.returncode:
      raise Exception('Call failed', p.returncode)
