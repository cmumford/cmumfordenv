import subprocess

class Image(object):
  @staticmethod
  def Create(path, fs_block_size, fs_num_blocks):
    cmd = ['dd', 'if=/dev/zero', 'of=%s' % path,
           'bs=%d' % fs_block_size, 'count=%d' % fs_num_blocks]
    subprocess.check_call(cmd)
    cmd = ['/sbin/mkfs', '-t', 'ext4', '-F', '-q', path]
    subprocess.check_call(cmd)
