
import argparse
import os
import sys
import subprocess

def GetDocumentsPath():
  return os.path.join(os.getenv('USERPROFILE'), 'Documents')

def CaptureFilePath():
  return os.path.join(GetDocumentsPath(), 'bth_hci.etl')

# Path to Data file readable by Wireshark protocol analyzers.
def PCapFilePath():
  return os.path.join(GetDocumentsPath(), 'bth_hci.pcap')

def BTLEParsePath():
  return os.path.join(os.getenv('ProgramFiles(x86)'), 'Windows Kits', '10',
        'Tools', 'x64', 'Bluetooth', 'BETLParse', 'btetlparse.exe')

def StartCapture():
  print('Starting capture')
  cmd = ['logman', 'create', 'trace', 'bth_hci', '-ow', '-o', CaptureFilePath(),
    '-p', '{8a1f9517-3a8c-4a9e-a018-4f17a200f277}', '0xffffffffffffffff',
    '0xff', '-nb', '16', '16', '-bs', '1024', '-mode', 'Circular', '-f',
    'bincirc', '-max', '4096', '-ets']
  subprocess.check_call(cmd)
  print('Capturing to "%s"' % CaptureFilePath())

def StopCapture():
  cmd = ['logman', 'stop', 'bth_hci', '-ets']

  print('Capture stopped. Capture file: "%s"' % CaptureFilePath())
  print('  file size: %d bytes' % os.path.getsize(CaptureFilePath()))

# https://docs.microsoft.com/en-us/windows-hardware/drivers/bluetooth/testing-btp-tools-btetlparse
def ParseCapture():
  cmd = [BTLEParsePath(), '-pcap', PCapFilePath(), CaptureFilePath()]
  subprocess.check_call(cmd)

def main():
  parser = argparse.ArgumentParser(description='Control Bluetooth packet logging.')
  subparsers = parser.add_subparsers(dest='cmd', help='sub-command help')

  parser_start = subparsers.add_parser('start', help='Start capturing')
  parser_stop = subparsers.add_parser('stop', help='Stop capturing')
  parser_parse = subparsers.add_parser('parse', help='Parse capture log')

  args = parser.parse_args(sys.argv[-1:])

  if args.cmd == 'start':
    StartCapture()
  elif args.cmd == 'stop':
    StopCapture()
  elif args.cmd == 'parse':
    ParseCapture()

if __name__ == '__main__':
  main()
