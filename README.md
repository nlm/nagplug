Nagplug ![Build Status](https://img.shields.io/travis/nlm/nagplug.svg) ![GitHub release](https://img.shields.io/github/release/nlm/nagplug.svg) ![PyPI](https://img.shields.io/pypi/v/nagplug.svg) [![License: MIT](https://img.shields.io/github/license/nlm/parseable.svg)](https://opensource.org/licenses/MIT)
=======

A library to easily write Monitoring Plugins compliant with the
[monitoring plugins guidelines](https://www.monitoring-plugins.org/doc/guidelines.html)
using python.

This library was designed to be similar to Perl
[Monitoring::Plugin library](http://search.cpan.org/~nierlein/Monitoring-Plugin-0.39/lib/Monitoring/Plugin.pm).

Plugin Documentation
--------------------

You can access embedded plugin documentation using pydoc

    $ pydoc nagplug

Also, the `example.py` file gives a pretty good example of a simple plugin.

The nagplug library manages almost all the life of the plugin program,
from argument parsing to timeouts, exception handling, output formatting.

Using the library
-----------------

First, create an instance of a Plugin

```python
>>> from nagplug import Plugin, OK, WARNING, CRITICAL, UNKNOWN
>>> plugin = Plugin()

```

Then, you can add some arguments to parse from the command-line.
(Note that unless you use `add_stdargs=False` when calling Plugin(),
some default standard arguments will be added
(`--hostname`, `--timeout`, `--verbose` and `--version`).
`--help` is added by the underlying `argparse` module.)

```python
>>> plugin.add_arg('--max', required=True, type=int) # doctest: +ELLIPSIS
_StoreAction(...)
>>> plugin.add_arg('--value', required=True, type=int) # doctest: +ELLIPSIS
_StoreAction(...)
>>> args = plugin.parse_args('--max 3 --value 6'.split())
>>> print(args.max)
3
>>> print(args.value)
6

```

Any argument you can pass to `argparse.ArgumentParser.add_argument` can also
be passed to `nagplug.Plugin.add_arg`. See the `argparse` documentation to
see how it works and all the nice things you can do.

If you need to do advanced parsing, you can access the internal parser
using the `parser` attribute of the plugin.

```python
>>> # if you want to add subparsers, for example.
>>> sp = plugin.parser.add_subparsers()

```

For safety reasons, you might want your test to stop after a certain amount
of time, considering that it failed. By default it will use the value of
`args.timeout` set by the `--timeout` argument.

```python
>>> print(args.timeout)
30
>>> plugin.set_timeout()

```

Now let's say that you want to check if `value` is inferior to `max`,
returning an OK status if it's the case and critical if its is not.
You do the check, then add the result to the plugin.
At anytime, you can get the current plugin status via the `get_code()` method.

```python
>>> if args.value <= args.max:
...     plugin.add_result(OK, 'All Good !')
... else:
...     plugin.add_result(CRITICAL, 'Dammit !')
>>> plugin.get_code() == CRITICAL
True
>>> plugin.get_message()
'Dammit !'

```

You can add any number of results, the plugin will return the worst
recorded status:

```python
>>> plugin.add_result(OK, 'But... Other test worked !')
>>> plugin.get_code() == CRITICAL
True

```

When you're done, exit the plugin and return the final result
by calling the `finish` method:

```python
>>> plugin.finish() # doctest: +SKIP

```

Checking values against Thresholds
----------------------------------

Thresholds are useful for the user to express more complex value ranges
from the command line. The syntax is described in the
[threshold format specification](https://www.monitoring-plugins.org/doc/guidelines.html#THRESHOLDFORMAT).

The `check_threshold` function makes it easy to check values against thresholds.
It returns the code corresponding to the worst threshold matched.

```python
>>> from nagplug import Threshold
>>> warn_t = Threshold(':90')
>>> crit_t = Threshold(':95')
>>> plugin.check_threshold(56, warning=warn_t, critical=crit_t) == OK
True
>>> plugin.check_threshold(93, warning=warn_t, critical=crit_t) == WARNING
True
>>> plugin.check_threshold(97, warning=warn_t, critical=crit_t) == CRITICAL
True

```

Perfdata and Extended Data
--------------------------

Some monitoring systems can also do graphing.
These system use the
[performance data](https://www.monitoring-plugins.org/doc/guidelines.html#AEN201)
emitted by your plugin.

The `add_perfdata` method will make sure everything is well-formatted.
You must give at least a label and a value, but you can also add an
unit of measurement, minimum and maximum bounds, and thresholds.

```python
>>> plugin.add_perfdata('percent_used', 20, uom='%', minimum=0, maximum=100)
>>> plugin.add_perfdata('age_of_the_captain', 87)
>>> print(plugin.get_perfdata())
'percent_used'=20%;;;0;100 'age_of_the_captain'=87;;;;

```

Extended data can help you by having more details in your output,
while keeping the main status line short and clear.

```python
>>> plugin.add_extdata('This will be logged in the output')
>>> plugin.add_extdata('This will also be logged')
>>> print(plugin.get_extdata())
This will be logged in the output
This will also be logged

```

The `extdata_log_handler` method returns a convenient `LogHandler` for
Python's `logging` framework that registers all output logs as extdata.

```python
>>> import logging
>>> log = logging.getLogger()
>>> log.addHandler(plugin.extdata_log_handler())
>>> log.info('This log will be registered as extdata')
>>> log.debug('This one also')
>>> print(plugin.get_extdata())
This log will be registered as extdata
This one also
```
