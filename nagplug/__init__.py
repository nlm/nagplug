"""
A Nagios-plugin-guidelines-compliant plugin creation library

The MIT License (MIT)

Copyright (C) 2014-2022 Nicolas Limage

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

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
import logging
import typing


OK: int = 0
WARNING: int = 1
CRITICAL: int = 2
UNKNOWN: int = 3
_CODES_STR: typing.List[str] = ['OK', 'WARNING', 'CRITICAL', 'UNKNOWN']


class ArgumentParserError(Exception):
    pass


class ThrowingArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> typing.NoReturn:
        raise ArgumentParserError(message)


class NagplugLoggingHandler(logging.StreamHandler):
    def __init__(self, plugin):
        self.plugin = plugin
        super(NagplugLoggingHandler, self).__init__()

    def emit(self, record):
        message = self.format(record)
        self.plugin.add_extdata(message)

        
class Plugin:
    """ The main Plugin class, used for all later operations """

    def __init__(self, name: str = os.path.basename(sys.argv[0]), version: str = None,
                 add_stdargs: bool = True, catch_exceptions: bool = True) -> None:
        """
        initialize the plugin object

        arguments:
            name: the name of the plugin, as used in the auto-generated help
            version: an optional version of your plugin
            add_stdargs: add hostname, timeout, verbose and version (default)
            catch_exceptions: gracefully catch exceptions
        """
        self._name: str = name
        self._args: typing.Optional[argparse.Namespace] = None
        self._timeout: int = 10
        self._results: typing.List["Result"] = []
        self._perfdata: typing.List["Perfdata"] = []
        self._extdata: typing.List[str] = []
        self._timeout_delay: typing.Optional[int] = None
        self._timeout_code: typing.Optional[int] = None
        if version is None:
            version = "undefined"
        if catch_exceptions is True:
            sys.excepthook = self._excepthook
        self._parser: ThrowingArgumentParser = ThrowingArgumentParser()
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

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.finish()

    # Properties

    @property
    def parser(self) -> "ThrowingArgumentParser":
        """
        the plugin's internal argparse parser,
        so you can do some more advanced stuff
        """
        return self._parser

    @property
    def name(self) -> str:
        """
        this plugin's name
        """
        return self._name

    @property
    def args(self) -> typing.Optional[argparse.Namespace]:
        """
        the parsed arguments, as a convenience shortcut

        returns:
            the result of the previous parse_args call,
            or None if arguments have not yet been parsed
        """
        return self._args

    @property
    def results(self) -> typing.List["Result"]:
        """
        the list of results

        returns:
            the list of all result objects from add_result calls
        """
        return self._results

    # Exception hook

    def _excepthook(self, etype, evalue, trace) -> None:
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

    def _timeout_handler(self, signum, frame) -> None:
        """
        internal timeout handler
        """
        msgfmt = 'plugin timed out after {0} seconds'
        self.exit(code=self._timeout_code,
                  message=msgfmt.format(self._timeout_delay))

    def set_timeout(self, timeout: int = None, code: int = None) -> None:
        """
        set the timeout for plugin operations
        when timeout is reached, exit properly with nagios-compliant output

        arguments:
            timeout: timeout in seconds
            code: exit status code
        """
        if timeout is None:
            timeout = self.args.timeout if self.args and self.args.timeout else 10
        if code is None:
            code = UNKNOWN
        self._timeout_delay = timeout
        self._timeout_code = code
        signal.signal(signal.SIGALRM, self._timeout_handler)
        signal.alarm(timeout)

    # Exit Codes

    def exit(self, code: int = None, message: str = None, perfdata=None, extdata=None) -> None:
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

    def die(self, message: str) -> None:
        """
        manual exit to use in case of internal error
        always return UNKNOWN status

        arguments:
            message: a short, one-line message to display
        """
        self.exit(code=UNKNOWN, message=message)

    def finish(self, code: int = None, message: str = None, perfdata: str = None, extdata: str = None) -> None:
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

    def add_arg(self, *args, **kwargs) -> argparse.Action:
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

    def parse_args(self, arguments: typing.Sequence[str] = None) -> typing.Optional[argparse.Namespace]:
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
    def check_threshold(
        value,
        warning: typing.Union[str, "Threshold"] = None,
        critical: typing.Union[str, "Threshold"] = None
    ):
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

    def add_result(self, code: int, message: str = None):
        """
        add a result to the internal result list

        arguments:
            same arguments as for Result()
        """
        self._results.append(Result(code, message))

    def get_code(self) -> int:
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

    def get_message(self, msglevels: typing.List[int] = None, joiner: str = None) -> str:
        """
        the final message for mult-checks

        arguments:
            msglevels: an array of all desired levels (ex: [CRITICAL, WARNING])
            joiner: string used to join all messages (default: ', ')

        returns:
            one-line message created with input results
            or None if there are none
        """
        messages: typing.List[str] = []
        if joiner is None:
            joiner = ', '
        if msglevels is None:
            msglevels = [OK, WARNING, CRITICAL]
        for result in self._results:
            if result.code in msglevels:
                messages.append(result.message)
        return joiner.join([msg for msg in messages if msg])

    # Perfdata

    def add_perfdata(self, *args, **kwargs) -> None:
        """
        add a perfdata to the internal perfdata list

        arguments:
            the same arguments as for Perfdata()
        """
        self._perfdata.append(Perfdata(*args, **kwargs))

    def get_perfdata(self) -> str:
        """
        the final string for perf data

        returns:
            the well-formatted perfdata string
        """
        return ' '.join([str(x) for x in self._perfdata])

    # Extended Data

    def add_extdata(self, message: str) -> None:
        """
        add extended data to the internal extdata list

        arguments:
            message: a free-form string
        """
        self._extdata.append(str(message))

    def get_extdata(self) -> str:
        """
        the final string for extended data
        returns:
            the extended data string
        """
        return '\n'.join(self._extdata)
    
    # Logging

    def extdata_log_handler(self) -> "NagplugLoggingHandler":
        """
        a convenience log handler for extdata
        returns:
            NagplugLoggingHandler linked to this instance
        """
        return NagplugLoggingHandler(self)


class Result:
    """
    Object representing a result
    """

    def __init__(self, code: int, message: str = None) -> None:
        """
        initialize a result object

        arguments:
            code: the status code
            message: the status message
        """
        self.code: int = code
        self.codestr: str = _CODES_STR[code]
        self.message: str = message or ''

    def __repr__(self) -> str:
        return '{0} - {1}'.format(self.codestr, self.message)


class ParseError(RuntimeError):
    """ legacy, for compatibility purposes """
    pass


class Threshold:
    """ object to represent thresholds """

    def __init__(self, threshold: str) -> None:
        """
        initializes a new Threshold Object

        arguments:
            threshold: string describing the threshold
                (see https://nagios-plugins.org/doc/guidelines.html)
        """
        self._threshold: str = threshold
        self._min: float = 0
        self._max: float = 0
        self._inclusive: bool = False
        self._parse(threshold)

    def _parse(self, threshold: str) -> None:
        """
        internal threshold string parser

        arguments:
            threshold: string describing the threshold
        """
        match = re.search(r'^(@?)((~|\d*|\-\d*):)?(\d*|\-\d*)$', threshold)

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

    def check(self, value: typing.Union[int, float]) -> bool:
        """
        check if a value is correct according to threshold

        arguments:
            value: the value to check
        """
        if self._inclusive:
            return False if self._min <= value <= self._max else True
        else:
            return False if value > self._max or value < self._min else True

    def __repr__(self) -> str:
        return '{0}({1})'.format(self.__class__.__name__, self._threshold)

    def __str__(self) -> str:
        return self._threshold


class Perfdata:
    """ object to represent performance data """

    def __init__(self, label: str, value: str, uom: str = None,
                 warning: str = None, critical: str = None, minimum: str = None, maximum: str = None) -> None:
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
        self.label: str = label
        self.value = value
        self.uom: typing.Optional[str] = uom
        self.warning: typing.Optional[str] = warning
        self.critical: typing.Optional[str] = critical
        self.minimum: typing.Optional[str] = minimum
        self.maximum: typing.Optional[str] = maximum

    def __str__(self) -> str:
        return '\'{label}\'={value}{uom};{warn};{crit};{mini};{maxi}'.format(
            label=self.label,
            value=self.value,
            uom=self.uom if self.uom is not None else '',
            warn=self.warning if self.warning is not None else '',
            crit=self.critical if self.critical is not None else '',
            mini=self.minimum if self.minimum is not None else '',
            maxi=self.maximum if self.maximum is not None else '',
        )

    def __repr__(self) -> str:
        return "%s(%s)" % (self.__class__.__name__, self.label)
