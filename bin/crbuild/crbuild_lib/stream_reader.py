#!/usr/bin/env python3

import os
import sys
from threading import Thread

class StreamReader:

  def __init__(self, in_stream, out_stream, src_root_dir, symbolize):
    """
    in_stream: the stream to read (e.g. p.stderr, etc.)
    out_stream: the stream to write (e.g. sys.stderr, etc.)
    """
    self._continue = True
    if symbolize:
      cmd_subfolder = os.path.realpath(
          os.path.abspath(os.path.join(src_root_dir,
                                       'tools', 'valgrind', 'asan')))
      if cmd_subfolder not in sys.path:
        sys.path.insert(0, cmd_subfolder)
      from third_party import asan_symbolize

    def _run(in_stream, out_stream, symbolize):
      """
      Demangle lines from |in_stream| and write to |out_stream|.
      """

      if symbolize:
        asan_symbolize.demangle = True
        loop = asan_symbolize.SymbolizationLoop(
            binary_name_filter=asan_symbolize.fix_filename)
      while self._continue:
        line = in_stream.readline()
        if not line:
          return
        if symbolize:
          line = ''.join(loop.process_line(line.decode('utf-8')))
        print(line.rstrip().decode('utf-8'), file=out_stream)

    self._thread = Thread(target=_run, args=(in_stream, out_stream, symbolize))
    self._thread.daemon = True
    self._thread.start()

  def stop(self):
    self._continue = False
    self._thread.join()
