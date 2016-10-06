# -*- coding: utf-8 -*-
"""

A Nagios-plugin-guidelines-compliant plugin creation library
Copyright (C) 2014 Nicolas Limage

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

Official Nagios Plugins Guidelines can be found here:
http://nagios-plugins.org/doc/guidelines.html

"""

from __future__ import print_function
import sys
import os
import signal
import re
import argparse
import traceback


OK = 0
WARNING = 1
CRITICAL = 2
UNKNOWN = 3
_CODES_STR = ['OK', 'WARNING', 'CRITICAL', 'UNKNOWN']


class ArgumentParserError(Exception):
    pass


class ThrowingArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise ArgumentParserError(message)


class Plugin(object):
    """ The main Plugin class, used for all later operations """

    def __init__(self, name=os.path.basename(sys.argv[0]), version=None,
                 add_stdargs=True, catch_exceptions=True):
        """
        initialize the plugin object

        arguments:
            name: the name of the plugin, as used in the auto-generated help
            version: an optional version of your plugin
            add_stdargs: add hostname, timeout, verbose and version (default)
            catch_exceptions: gracefully catch exceptions
        """
        self._name = name
        self._args = None
        self._timeout = 10
        self._results = []
        self._perfdata = []
        self._extdata = []
        self._timeout_delay = None
        self._timeout_code = None
        if version is None:
            version = "undefined"
        if catch_exceptions is True:
            sys.excepthook = self._excepthook
        self._parser = ThrowingArgumentParser()
        if add_stdargs:
            self.parser.add_argument("-H", "--hostname",
                                     help="hostname", metavar="HOSTNAME")
            self.parser.add_argument("-t", "--timeout", help="timeout",
                                     metavar="TIMEOUT", default=30, type=int)
            self.parser.add_argument("-v", "--verbose",
                                     help="increase verbosity",
                                     action="count", default=0)
            self.parser.add_argument("-V", "--version", help="show version",
                                     action="version",
                                     version=name + " " + str(version))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.finish()

    # Properties

    @property
    def parser(self):
        """
        the plugin's internal argparse parser,
        so you can do some more advanced stuff
        """
        return self._parser

    @property
    def name(self):
        """
        this plugin's name
        """
        return self._name

    @property
    def args(self):
        """
        the parsed arguments, as a convenience shortcut

        returns:
            the result of the previous parse_args call,
            or None if arguments have not yet been parsed
        """
        return self._args

    @property
    def results(self):
        """
        the list of results

        returns:
            the list of all result objects from add_result calls
        """
        return self._results

    # Exception hook

    def _excepthook(self, etype, evalue, trace):
        """
        internal exception hook
        """
        if etype == ArgumentParserError:
            self.exit(code=CRITICAL,
                      message='error: {0}'.format(evalue),
                      extdata=self.parser.format_usage())
        else:
            self.exit(code=UNKNOWN,
                      message='Uncaught exception: {0} - {1}'
                              .format(etype.__name__, evalue),
                      extdata=''.join(traceback.format_tb(trace)))

    # Timeout handling

    def _timeout_handler(self, signum, frame):
        """
        internal timeout handler
        """
        msgfmt = 'plugin timed out after {0} seconds'
        self.exit(code=self._timeout_code,
                  message=msgfmt.format(self._timeout_delay))

    def set_timeout(self, timeout=None, code=None):
        """
        set the timeout for plugin operations
        when timeout is reached, exit properly with nagios-compliant output

        arguments:
            timeout: timeout in seconds
            code: exit status code
        """
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
        """
        manual exit from the plugin

        arguments:
            code: exit status code
            message: a short, one-line message to display
            perfdata: perfdata, if any
            extdata: multi-line message to give more details
        """
        code = UNKNOWN if code is None else int(code)
        message = "" if message is None else str(message)
        perfdata = "" if perfdata is None else str(perfdata)
        extdata = "" if extdata is None else str(extdata)
        print("{0} {1} - {2} | {3}".format(self.name.upper(),
                                           _CODES_STR[code],
                                           message, perfdata))
        if extdata:
            print(extdata)
        sys.exit(code)

    def die(self, message):
        """
        manual exit to use in case of internal error
        always return UNKNOWN status

        arguments:
            message: a short, one-line message to display
        """
        self.exit(code=UNKNOWN, message=message)

    def finish(self, code=None, message=None, perfdata=None, extdata=None):
        """
        exit when using internal function to add results
        automatically generates output, but each parameter can be overriden

        all parameters are optional

        arguments:
            code: exit status code
            message: a short, one-line message to display
            perfdata: perfdata, if any
            extdata: multi-line message to give more details
        """
        if code is None:
            code = self.get_code()
        if message is None:
            message = self.get_message(msglevels=[code])
        if perfdata is None:
            perfdata = self.get_perfdata()
        if extdata is None:
            extdata = self.get_extdata()
        self.exit(code=code, message=message,
                  perfdata=perfdata, extdata=extdata)

    # Argument Parsing

    def add_arg(self, *args, **kwargs):
        """
        add an argument for argument parsing
        transmitted to internal argparse
        see argparse documentation for details

        arguments:
            same as argparse.add_argument

        returns:
            the parser object for convenience
        """
        return self.parser.add_argument(*args, **kwargs)

    def parse_args(self, arguments=None):
        """
        parses the arguments from command-line

        arguments:
            optional argument list to parse

        returns:
            a dictionnary containing the arguments
        """
        self._args = self.parser.parse_args(arguments)
        return self.args

    # Threshold

    @staticmethod
    def check_threshold(value, warning=None, critical=None):
        """
        checks a value against warning and critical thresholds
        threshold syntax: https://nagios-plugins.org/doc/guidelines.html

        arguments:
            value: the value to check
            warning: warning threshold
            critical: critical threshold

        returns:
            the result status of the check
        """
        if critical is not None:
            if not isinstance(critical, Threshold):
                critical = Threshold(critical)
            if not critical.check(value):
                return CRITICAL
        if warning is not None:
            if not isinstance(warning, Threshold):
                warning = Threshold(warning)
            if not warning.check(value):
                return WARNING
        return OK

    # Results Handling

    def add_result(self, code, message=None):
        """
        add a result to the internal result list

        arguments:
            same arguments as for Result()
        """
        self._results.append(Result(code, message))

    def get_code(self):
        """
        the final code for multi-checks

        arguments:
            the worst-case code from all added results,
            or UNKNOWN if none were added
        """
        code = UNKNOWN
        for result in self._results:
            if code == UNKNOWN or (result.code < UNKNOWN
                                   and result.code > code):
                code = result.code
        return code

    def get_message(self, msglevels=None, joiner=None):
        """
        the final message for mult-checks

        arguments:
            msglevels: an array of all desired levels (ex: [CRITICAL, WARNING])
            joiner: string used to join all messages (default: ', ')

        returns:
            one-line message created with input results
            or None if there are none
        """
        messages = []
        if joiner is None:
            joiner = ', '
        if msglevels is None:
            msglevels = [OK, WARNING, CRITICAL]
        for result in self._results:
            if result.code in msglevels:
                messages.append(result.message)
        return joiner.join([msg for msg in messages if msg])

    # Perfdata

    def add_perfdata(self, *args, **kwargs):
        """
        add a perfdata to the internal perfdata list

        arguments:
            the same arguments as for Perfdata()
        """
        self._perfdata.append(Perfdata(*args, **kwargs))

    def get_perfdata(self):
        """
        the final string for perf data

        returns:
            the well-formatted perfdata string
        """
        return ' '.join([str(x) for x in self._perfdata])

    # Extended Data

    def add_extdata(self, message):
        """
        add extended data to the internal extdata list

        arguments:
            message: a free-form string
        """
        self._extdata.append(str(message))

    def get_extdata(self):
        """
        the final string for external data
        returns:
            the extended data string
        """
        return '\n'.join(self._extdata)


class Result(object):
    """
    Object representing a result
    """

    def __init__(self, code, message=None):
        """
        initialize a result object

        arguments:
            code: the status code
            message: the status message
        """
        self.code = code
        self.codestr = _CODES_STR[code]
        self.message = message

    def __repr__(self):
        return '{0} - {1}'.format(self.codestr, self.message)


class ParseError(RuntimeError):
    """ legacy, for compatibility purposes """
    pass


class Threshold(object):
    """ object to represent thresholds """

    def __init__(self, threshold):
        """
        initializes a new Threshold Object

        arguments:
            threshold: string describing the threshold
                (see https://nagios-plugins.org/doc/guidelines.html)
        """
        self._threshold = threshold
        self._min = 0
        self._max = 0
        self._inclusive = False
        self._parse(threshold)

    def _parse(self, threshold):
        """
        internal threshold string parser

        arguments:
            threshold: string describing the threshold
        """
        match = re.search(r'^(@?)((~|\d*):)?(\d*)$', threshold)

        if not match:
            raise ValueError('Error parsing Threshold: {0}'.format(threshold))

        if match.group(1) == '@':
            self._inclusive = True

        if match.group(3) == '~':
            self._min = float('-inf')
        elif match.group(3):
            self._min = float(match.group(3))
        else:
            self._min = float(0)

        if match.group(4):
            self._max = float(match.group(4))
        else:
            self._max = float('inf')

        if self._max < self._min:
            raise ValueError('max must be superior to min')

    def check(self, value):
        """
        check if a value is correct according to threshold

        arguments:
            value: the value to check
        """
        if self._inclusive:
            return False if self._min <= value <= self._max else True
        else:
            return False if value > self._max or value < self._min else True

    def __repr__(self):
        return '{0}({1})'.format(self.__class__.__name__, self._threshold)

    def __str__(self):
        return self._threshold


class Perfdata(object):
    """ object to represent performance data """

    def __init__(self, label, value, uom=None,
                 warning=None, critical=None, minimum=None, maximum=None):
        """
        initalize the object
        most arguments refer to :
        https://nagios-plugins.org/doc/guidelines.html#AEN200

        arguments:
            label: name of the performance data element
            value: value of the element
            uom: unit of mesurement
            warning: the warning threshold string
            critical: the critical threshold string
            minimum: minimum value (usually for graphs)
            maximum: maximul value (usually for graphs)
        """
        self.label = label
        self.value = value
        self.uom = uom
        self.warning = warning
        self.critical = critical
        self.minimum = minimum
        self.maximum = maximum

    def __str__(self):
        return '\'{label}\'={value}{uom};{warn};{crit};{mini};{maxi}'.format(
            label=self.label,
            value=self.value,
            uom=self.uom if self.uom is not None else '',
            warn=self.warning if self.warning is not None else '',
            crit=self.critical if self.critical is not None else '',
            mini=self.minimum if self.minimum is not None else '',
            maxi=self.maximum if self.maximum is not None else '',
        )

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self.label)
