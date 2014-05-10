# ShinkenPlugin
# A Nagios-plugin-guidelines-compliant plugin creation library
# Copyright (C) 2014 Nicolas Limage
# 
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import sys
import os
import signal
import re
import string
import argparse

"""Standart Nagios Return Codes"""
OK = 0
WARNING = 1
CRITICAL = 2
UNKNOWN = 3

class Plugin:

  """Shinken Plugin Base Class"""
  def __init__(self, name=os.path.basename(sys.argv[0]), version=None):
    self.name = name
    self._timeout = 10
    self.args = None
    self._results = []
    self._perfdata = []
    if version is None:
      version = "undefined"
    self.parser = argparse.ArgumentParser()
    self.parser.add_argument("-H", "--hostname", help="hostname", metavar="HOSTNAME")
    self.parser.add_argument("-t", "--timeout", help="timeout", metavar="TIMEOUT", default=10, nargs=1, type=int)
    self.parser.add_argument("-v", "--verbose", help="increase verbosity", action="count")
    self.parser.add_argument("-V", "--version", help="show version", action="version", version=name + " " + str(version))

# Timeout handling

  def _timeout_handler(self, signum, frame):
    self.exit(UNKNOWN, "plugin timed out after %d seconds" % self.timeout)

  def set_timeout(self, timeout=None, code=None):
    if timeout is None:
      timeout = 10
    if code is None:
      code = UNKNOWN
    self._timeout_delay = timeout
    self._timeout_code = code
    signal.signal(signal.SIGALRM, self._timeout_handler)
    signal.alarm(timeout)

# Exit Codes

  def _exit(self, result, perfdatastr):
    print "%s %s - %s | %s" % (self.name.upper(), result.codestr, result.message, perfdatastr)
    sys.exit(result.code)

  def exit(self, code, message, perfdata=None):
    self._exit(Result(code, message), "" if perfdata is None else str(perfdata))

  def die(self, message):
    self._exit(Result(UNKNOWN, message), "")

# Argument Parsing

  def add_arg(self, *args, **kwargs):
    return self.parser.add_argument(*args, **kwargs)

  def parse_args(self):
    self.args = self.parser.parse_args()
    self.timeout = self.args.timeout
    return self.args

# Threshold

  def check_threshold(self, value, warning=None, critical=None):
    if critical is not None:
      if not Threshold(critical).check(value):
        return CRITICAL
    if warning is not None:
      if not Threshold(warning).check(value):
        return WARNING
    return OK

# Results Handling

  def add_result(self, *args, **kwargs):
    self._results.append(Result(*args, **kwargs))

#  def get_result(self, joiner=None, default=None, msglevels=None):
#    messages = { OK: [], WARNING: [], CRITICAL: [], UNKNOWN: [] }
#    code = UNKNOWN
#    if joiner is None:
#      joiner = ", "
#    if default is None:
#      default = UNKNOWN
#    if not self._results:
#      return Result(default, "")
#    for result in self._results:
#      if result.message:
#        messages[result.code].append(result.message)
#      if code == UNKNOWN or (result.code < UNKNOWN and result.code > code):
#        code = result.code
#    return Result(code, joiner.join(messages[code]))

  def get_code(self):
    code = UNKNOWN
    for result in self._results:
      if code == UNKNOWN or (result.code < UNKNOWN and result.code > code):
        code = result.code
    return code

  def get_message(self, msglevels=None, joiner=None):
    messages = []
    if joiner is None:
      joiner = ", "
    if msglevels is None:
      msglevels = [ OK, WARNING, CRITICAL ]
    for result in self._results:
      if result.code in msglevels:
        messages.append(result.message)
    if not messages:
      return None
    return joiner.join(messages)

# Perfdata

  def add_perfdata(self, *args, **kwargs):
    self._perfdata.append(Perfdata(*args, **kwargs))

  def get_perfdata(self):
    print self._perfdata
    return " ".join(self._perfdata)

""" Class for Results """
class Result:

  _codes = [ "OK", "WARNING", "CRITICAL", "UNKNOWN" ]

  def __init__(self, code, message):
    self.code = code
    self.codestr = self._codes[code]
    self.message = message

  def __repr__(self):
    return "%s - %s" % (self.codestr, self.message)

class ParseError(RuntimeError):
  pass

"""Class for Threshold"""
class Threshold:
  
  """ Creates a new Threshold Object """
  def __init__(self, threshold):
    self._threshold = threshold
    self._min = 0
    self._max = 0
    self._inclusive = False
    self._parse(threshold)

  def _parse(self, threshold):
    m = re.search('^(@?)((~|\d*):)?(\d*)$', threshold)

    if not m:
      raise ParseError("Error parsing Threshold: " + threshold)

    if m.group(1) == '@':
      self._inclusive = True

    if m.group(3) == '~':
      self._min = float("-inf")
    elif m.group(3):
      self._min = float(m.group(3))
    else:
      self._min = float(0)

    if m.group(4):
      self._max = float(m.group(4))
    else:
      self._max = float("inf")

    if self._max < self._min:
      raise ValueError("Max must be superior to min")
    
  """ Checks if value is correct according to threshold """
  def check(self, value):
    if self._inclusive:
      return False if self._min <= value <= self._max else True
    else:
      return False if value > self._max or value < self._min else True

  """ Gives a representation of the Threshold Object """
  def __repr__(self):
    return "%s(%s)" % (self.__class__.__name__, self._threshold)

  def __str__(self):
    return self._threshold


""" Class for Perfdata """
class Perfdata:

  def __init__(self, label, value, uom=None, warning=None, critical=None, min=None, max=None):
    self.label = label
    self.value = value
    self.uom = uom
    self.warning = warning
    self.critical = critical
    self.min = min
    self.max = max

  def __str__(self):
    return "'%s'=%s%s;%s;%s;%s;%s" % (
      self.label, self.value,
      self.uom if self.uom is not None else "",
      self.warning if self.warning is not None else "",
      self.critical if self.critical is not None else "",
      self.min if self.min is not None else "",
      self.max if self.max is not None else ""
    )

  def __repr__(self):
    return "%s(%s)" % (self.__class__.__name__, self.label)

