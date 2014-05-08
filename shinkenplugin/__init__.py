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
  def __init__(self, name=os.path.basename(sys.argv[0])):
    self.args = None
    self.results = []
    self.name = name
    self.parser = argparse.ArgumentParser()
    self.parser.add_argument('-t', help="timeout", default=10)

  def __timeout(self, signum, frame):
    self.exit(UNKNOWN, "Timeout after %d seconds" % self.delay)

  def set_timeout(self, delay):
    self.delay = delay
    signal.signal(signal.SIGALRM, self.__timeout)
    signal.alarm(delay)

# Argument Parsing

  def add_arg(self, *args, **kwargs):
    return self.parser.add_argument(*args, **kwargs)

  def parse_args(self):
    self.args = self.parser.parse_args()

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

  def __repr__(self):
    return "%s(min=%s,max=%s)" % (self.__class__.__name__, str(self.min), str(self.max))

# Results Handling

  def add_result(self, result):
    self.results.append(result)

  def check_results(self, join=" ", default=UNKNOWN):
    messages = { OK: [], WARNING: [], CRITICAL: [], UNKNOWN: [] }
    code = None
    if not self.results:
      return Result(default, "")
    for result in self.results:
      if result.message:
        messages[result.code].append(result.message)
      if code == UNKNOWN or (result.code < UNKNOWN and result.code > code):
        code = result.code
    return Result(code, join.join(messages[code]))

# Exit Codes

  def exit(self, result):
    print "%s %s - %s" % (self.name.upper(), result.codestr, result.message)
    sys.exit(result.code)

  def die(self, message):
    self.__exit(Result(UNKNOWN, message))


"""Class for Threshold"""
class Threshold:
  
  def __init__(self, min=None, max=None):
    self.min = min
    self.max = max


""" Class for Results """
class Result:

  codes = [ "OK", "WARNING", "CRITICAL", "UNKNOWN" ]

  def __init__(self, code, message):
    self.code = code
    self.codestr = self.codes[code]
    self.message = message

  def __repr__(self):
    return "%s - %s" % (self.codestr, self.message)
