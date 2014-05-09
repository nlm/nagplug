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
    self.timeout = 10
    self.args = None
    self.results = []
    self.perfdata = []
    if version is None:
      version = "undefined"
    self.parser = argparse.ArgumentParser()
    self.parser.add_argument("-H", "--hostname", help="hostname", metavar="HOSTNAME")
    self.parser.add_argument("-t", "--timeout", help="timeout", metavar="TIMEOUT", default=10, nargs=1, type=int)
    self.parser.add_argument("-v", "--verbose", help="increase verbosity", action="count")
    self.parser.add_argument("-V", "--version", help="show version", action="version", version=name + " " + str(version))

  def _timeout(self, signum, frame):
    self.exit(UNKNOWN, "Timeout after %d seconds" % self.timeout)

  def set_timeout(self, timeout=None):
    if timeout is None:
      timeout = 10
    self.timeout = timeout
    signal.signal(signal.SIGALRM, self._timeout)
    signal.alarm(timeout)

# Argument Parsing

  def add_arg(self, *args, **kwargs):
    return self.parser.add_argument(*args, **kwargs)

  def parse_args(self):
    self.args = self.parser.parse_args()
    self.timeout = self.args.timeout

# Threshold

  def check_threshold(self, value, warning=None, critical=None):

    if critical is not None:
      if not isinstance(critical, Threshold):
        raise TypeError()
      if critical.min is not None and value < critical.min:
        return CRITICAL
      if critical.max is not None and value > critical.max:
        return CRITICAL

    if warning is not None:
      if not isinstance(warning, Threshold):
        raise TypeError()
      if warning.min is not None and value < warning.min:
        return WARNING
      if warning.max is not None and value > warning.max:
        return WARNING

    return OK

# Results Handling

  def add_result(self, result):
    self.results.append(result)

  def get_result(self, joiner=None, default=None, msglevels=None):
    messages = { OK: [], WARNING: [], CRITICAL: [], UNKNOWN: [] }
    code = UNKNOWN
    if joiner is None:
      joiner = ", "
    if default is None:
      default = UNKNOWN
    if not self.results:
      return Result(default, "")
    for result in self.results:
      if result.message:
        messages[result.code].append(result.message)
      if code == UNKNOWN or (result.code < UNKNOWN and result.code > code):
        code = result.code
    return Result(code, joiner.join(messages[code]))

  def get_code(self):
    code = UNKNOWN
    for result in self.results:
      if code == UNKNOWN or (result.code < UNKNOWN and result.code > code):
        code = result.code
    return code

  def get_messages(self, msglevels, joiner=None):
    messages = []
    if joiner is None:
      joiner = ", "
    for result in self.results:
      if result.code in msglevels:
        messages.append(result.message)
    if not messages:
      return None
    return joiner.join(messages)

# Perfdata

  def add_perfdata(self, perfdata):
    self.perfdata.append(perfdata)

  def get_perfdata(self):
    pass
    #XXX: do the perfdata stuff

# Exit Codes

  def _exit(self, result, perfdatastr):
    print "%s %s - %s | %s" % (self.name.upper(), result.codestr, result.message, perfdatastr)
    sys.exit(result.code)

  def exit(self, code, message, perfdata=None)
    self._exit(Result(code, message), "" if perfdata is None else str(perfdata))

  def die(self, message):
    self._exit(Result(UNKNOWN, message), "")


"""Class for Threshold"""
class Threshold:
  
  #def __init__(self, threshold):
  def __init__(self, min=None, max=None):
    ## XXX: add parser
    self.min = min
    self.max = max

  """ Gives a representation of the Threshold Object """
  def __repr__(self):
    return "%s(min=%s,max=%s)" % (self.__class__.__name__, str(self.min), str(self.max))

""" Class for Results """
class Result:

  _codes = [ "OK", "WARNING", "CRITICAL", "UNKNOWN" ]

  def __init__(self, code, message):
    self.code = code
    self.codestr = self._codes[code]
    self.message = message

  def __repr__(self):
    return "%s - %s" % (self.codestr, self.message)


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

