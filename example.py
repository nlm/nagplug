#!/usr/bin/env python

import shinkenplugin

if __name__ == "__main__":
    sp = shinkenplugin.Plugin()
    sp.add_arg('-w', '--warning', nargs=1, metavar="THRESHOLD", type=str)
    sp.add_arg('-c', '--critical', nargs=1, metavar="THRESHOLD", type=str)
    sp.add_arg('--value', nargs=1, required=1, metavar="VALUE", type=int)
    sp.parse_args()
    sp.set_timeout()

    value = sp.args.value[0]
    t_warn = sp.args.warning[0]
    t_crit = sp.args.critical[0]

    code = sp.check_threshold(value, warning=t_warn, critical=t_crit)
    sp.add_result(code, "value=%d" % value)
    sp.add_perfdata("value", value, warning=t_warn, critical=t_crit, minimum=0, maximum=100)
    if sp.args.verbose > 2:
        sp.add_extdata("value has been determined to be %d" % (value))

    sp.finish()
