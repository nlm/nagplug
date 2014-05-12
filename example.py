#!/usr/bin/env python
""" Shinkenplugin example plugin """

import shinkenplugin

def main():

    # Create a new shinkenplugin.Plugin instance
    sp = shinkenplugin.Plugin()

    # Add some arguments to parse
    sp.add_arg('-w', '--warning', metavar="THRESHOLD", type=str,
        help="Warning Threshold, see https://nagios-plugins.org/doc/guidelines.html#THRESHOLDFORMAT")
    sp.add_arg('-c', '--critical', metavar="THRESHOLD", type=str,
        help="Warning Threshold, see https://nagios-plugins.org/doc/guidelines.html#THRESHOLDFORMAT")
    sp.add_arg('--value', required=1, metavar="VALUE", type=int)

    # Parse the arguments
    sp.parse_args()

    # Set plugin timeout
    sp.set_timeout()

    # Get values and thresholds from command line
    value = sp.args.value
    t_warn = sp.args.warning
    t_crit = sp.args.critical

    # Check value against thresholds
    code = sp.check_threshold(value, warning=t_warn, critical=t_crit)

    # Add result to the stack
    sp.add_result(code, "value=%d" % value)

    # Add some performance data to the stack
    sp.add_perfdata("value", value, warning=t_warn, critical=t_crit, minimum=0, maximum=100)

    # Add some extra data if needed
    if sp.args.verbose > 2:
        sp.add_extdata("value has been determined to be %d" % (value))

    # Exit printing the conclusions in a nagios-plugin compliant way
    sp.finish()


if __name__ == "__main__":
    main()
