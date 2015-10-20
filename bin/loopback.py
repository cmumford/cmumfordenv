import re

# The number of loopback devices is a system limit
max_num_loopback_devs = 8

class Loopback(object):
  def __init__(self):
    self.loop_re = re.compile(r'^/dev/loop(\d+)\b')
    self.loop_path_re = re.compile(r'.*/ldb_endurance_(\d+)$')
    self.possible_fds = set(range(max_num_loopback_devs))

  def GetUsedDevices(self):
    fds = {}
    with open ('/proc/mounts', 'r') as f:
      for line in f.readlines():
        items = line.strip().split()
        if items:
          m = self.loop_re.match(items[0])
          if m:
            fds[int(m.group(1))] = items[1]
    return fds

  # Could replace with call to 'losetup --find', but that requires sudo
  def GetFirstUnusedDevice(self):
    devs = self.GetUsedDevices()
    unused_fds = self.possible_fds - set(devs.keys())
    if unused_fds:
      return '/dev/loop%d' % unused_fds.pop()
    else:
      return None

  def IsMounted(self, identifier):
    with self.lock:
      for loop_id, path in self.GetUsedDevices().iteritems():
        m = self.loop_path_re.match(path.strip())
        if m:
          if m.group(1) == identifier:
            return True
      return False
