#!/usr/bin/env python3

import os
import sys
import unittest

def GetAbsPathRelativeToThisFilesDir(rel_path):
  return os.path.abspath(os.path.join(os.path.dirname(__file__),
                         rel_path))

sys.path.append(GetAbsPathRelativeToThisFilesDir('..'))

from crbuild_lib import (command)

class TestCmd(unittest.TestCase):

  def test_to_string(self):
    self.assertEqual('foo bar', command.Cmd.list_to_string(['foo', 'bar'],
                                                           add_quotes=True))

  def test_to_string_with_quote(self):
    self.assertEqual('foo "bar baz"',
                     command.Cmd.list_to_string(['foo', 'bar baz'],
                                                add_quotes=True))

  def test_to_string_with_equals(self):
    self.assertEqual('foo bar=5', command.Cmd.list_to_string(['foo', 'bar=5'],
                                                             add_quotes=True))

  def test_to_string_with_equals_quoted(self):
    self.assertEqual('foo bar="with space"',
                     command.Cmd.list_to_string(['foo', 'bar=with space'],
                                                add_quotes=True))

  def test_to_string_with_equals_hyphens(self):
    self.assertEqual('foo bar="--bar_flag"',
                     command.Cmd.list_to_string(['foo', 'bar=--bar_flag'],
                                                add_quotes=True))
  def test_to_string_no_quote(self):
    self.assertEqual('foo bar baz',
                     command.Cmd.list_to_string(['foo', 'bar baz'],
                                                add_quotes=False))

  def test_to_string_with_equals_no_quote(self):
    self.assertEqual('foo bar=5', command.Cmd.list_to_string(['foo', 'bar=5'],
                                                             add_quotes=False))

  def test_to_string_with_equals_no_quote(self):
    self.assertEqual('foo bar=with space',
                     command.Cmd.list_to_string(['foo', 'bar=with space'],
                                                add_quotes=False))

  def test_to_string_with_equals_hyphens_no_quote(self):
    self.assertEqual('foo bar=--bar_flag',
                     command.Cmd.list_to_string(['foo', 'bar=--bar_flag'],
                                                add_quotes=False))

if __name__ == '__main__':
    unittest.main()


