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

# Official Nagios Plugins Guidelines can be found here:
# http://nagios-plugins.org/doc/guidelines.html

import sys
import os
import signal
import re
import argparse


""" Standard Nagios Return Codes """
OK = 0
WARNING = 1
CRITICAL = 2
UNKNOWN = 3
_CODES_STR = [ "OK", "WARNING", "CRITICAL", "UNKNOWN" ]


""" Shinken Plugin Base Class """
class Plugin:

    def __init__(self, name=os.path.basename(sys.argv[0]), version=None):
        self.name = name
        self.args = None
        self._timeout = 10
        self._results = []
        self._perfdata = []
        self._extdata = []
        self._timeout_delay = None
        self._timeout_code = None
        if version is None:
            version = "undefined"
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument("-H", "--hostname", help="hostname", metavar="HOSTNAME")
        self.parser.add_argument("-t", "--timeout", help="timeout", metavar="TIMEOUT", default=10, nargs=1, type=int)
        self.parser.add_argument("-v", "--verbose", help="increase verbosity", action="count")
        self.parser.add_argument("-V", "--version", help="show version", action="version", version=name + " " + str(version))

# Timeout handling

    def _timeout_handler(self, signum, frame):
        self.exit(code=self._timeout_code, message="plugin timed out after %d seconds" % self._timeout_delay)

    def set_timeout(self, timeout=None, code=None):
        if timeout is None:
            timeout = self.args.timeout if self.args.timeout else 10
        if code is None:
            code = UNKNOWN
        self._timeout_delay = timeout
        self._timeout_code = code
        signal.signal(signal.SIGALRM, self._timeout_handler)
        signal.alarm(timeout)

# Exit Codes

    def exit(self, code=None, message=None, perfdata=None, extdata=None):
        code = UNKNOWN if code is None else int(code)
        message = "" if message is None else str(message)
        perfdata = "" if perfdata is None else str(perfdata)
        extdata = "" if extdata is None else str(extdata)
        print "%s %s - %s | %s" % (self.name.upper(), _CODES_STR[code] , message, perfdata)
        if extdata:
            print extdata
        sys.exit(code)

    def die(self, message):
        self.exit(code=UNKNOWN, message=message)

    def finish(self, code=None, message=None, perfdata=None, extdata=None):
        if code is None:
            code = self.get_code()
        if message is None:
            message = self.get_message(msglevels=[code])
        if perfdata is None:
            perfdata = self.get_perfdata()
        if extdata is None:
            extdata = self.get_extdata()
        self.exit(code=code, message=message, perfdata=perfdata, extdata=extdata)

# Argument Parsing

    def add_arg(self, *args, **kwargs):
        return self.parser.add_argument(*args, **kwargs)

    def parse_args(self):
        self.args = self.parser.parse_args()
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
        return " ".join(map(str, self._perfdata))

# Extended Data

    def add_extdata(self, message):
        self._extdata.append(str(message))

    def get_extdata(self):
        return "\n".join(self._extdata)


""" Class for Results """
class Result:

    def __init__(self, code, message):
        self.code = code
        self.codestr = _CODES_STR[code]
        self.message = message

    def __repr__(self):
        return "%s - %s" % (self.codestr, self.message)


""" Class for Parsing Errors """
class ParseError(RuntimeError):
    pass


""" Class for Thresholds """
class Threshold:
  
    """ Initializes a new Threshold Object """
    def __init__(self, threshold):
        self._threshold = threshold
        self._min = 0
        self._max = 0
        self._inclusive = False
        self._parse(threshold)

    """ Parse a threshold string """
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
            raise ParseError("max must be superior to min")
    
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

    def __init__(self, label, value, uom=None, warning=None, critical=None, minimum=None, maximum=None):
        self.label = label
        self.value = value
        self.uom = uom
        self.warning = warning
        self.critical = critical
        self.minimum = minimum
        self.maximum = maximum

    def __str__(self):
        return "'%s'=%s%s;%s;%s;%s;%s" % (
            self.label, self.value,
            self.uom if self.uom is not None else "",
            self.warning if self.warning is not None else "",
            self.critical if self.critical is not None else "",
            self.minimum if self.minimum is not None else "",
            self.maximum if self.maximum is not None else ""
        )

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self.label)

