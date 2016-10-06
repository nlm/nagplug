import unittest
from nagplug import Plugin, Threshold, ArgumentParserError
from nagplug import OK, WARNING, CRITICAL, UNKNOWN


class TestParsing(unittest.TestCase):

    def test_parse(self):
        plugin = Plugin()
        plugin.add_arg('-e', '--test', action='store_true')
        args = plugin.parser.parse_args(['-e'])
        self.assertTrue(args.test)

    def test_parse_threshold_string(self):
        plugin = Plugin()
        plugin.add_arg('-w', '--warning-threshold')
        plugin.add_arg('-c', '--critical-threshold')
        args = plugin.parse_args(['-w', '10:20', '-c', '0:40'])
        self.assertEqual(OK, plugin.check_threshold(15,
                                                    args.warning_threshold,
                                                    args.critical_threshold))

    def test_parse_threshold_native(self):
        plugin = Plugin()
        plugin.add_arg('-w', '--warning-threshold', type=Threshold)
        plugin.add_arg('-c', '--critical-threshold', type=Threshold)
        args = plugin.parse_args(['-w', '10:20', '-c', '0:40'])
        self.assertEqual(OK, plugin.check_threshold(15,
                                                    args.warning_threshold,
                                                    args.critical_threshold))

    def test_parse_exceptions(self):
        plugin = Plugin()
        plugin.add_arg('test')
        self.assertRaises(ArgumentParserError, plugin.parse_args, [])

    def test_parse_exceptions(self):
        plugin = Plugin()
        plugin.add_arg('threshold', type=Threshold)
        self.assertRaises(ArgumentParserError, plugin.parse_args, [])


class TestThreshold(unittest.TestCase):

    def test_threshold_parseerror(self):
        self.assertRaises(ValueError, Threshold, ("helloworld"))

    def test_threshold_valueerror(self):
        self.assertRaises(ValueError, Threshold, ("10:2"))

    def test_theshold_simple_neg(self):
        self.assertFalse(Threshold("10").check(-1))

    def test_theshold_simple_over(self):
        self.assertFalse(Threshold("10").check(11))

    def test_theshold_simple_zero(self):
        self.assertTrue(Threshold("10").check(0))

    def test_theshold_simple_upperbound(self):
        self.assertTrue(Threshold("10").check(10))

    def test_theshold_simple_inside(self):
        self.assertTrue(Threshold("10").check(5))

    def test_threshold_range_one(self):
        self.assertTrue(Threshold("10:10").check(10))

    def test_threshold_range_lowerbound(self):
        self.assertTrue(Threshold("10:20").check(10))

    def test_threshold_range_inside(self):
        self.assertTrue(Threshold("10:20").check(15))

    def test_threshold_range_upperbound(self):
        self.assertTrue(Threshold("10:20").check(20))

    def test_threshold_range_lower(self):
        self.assertFalse(Threshold("10:20").check(9))

    def test_threshold_range_upper(self):
        self.assertFalse(Threshold("10:20").check(21))

    def test_threshold_invert_bound(self):
        self.assertFalse(Threshold("@10").check(10))

    def test_threshold_invert_range(self):
        self.assertFalse(Threshold("@10:20").check(10))

    def test_threshold_invert_upper(self):
        self.assertFalse(Threshold("@:20").check(10))

    def test_threshold_openrange_simple(self):
        self.assertTrue(Threshold("10:").check(20))

    def test_threshold_openrange_inside(self):
        self.assertTrue(Threshold(":10").check(5))

    def test_threshold_openrange_over(self):
        self.assertFalse(Threshold(":10").check(20))

    def test_threshold_openrange_neg(self):
        self.assertTrue(Threshold("~:10").check(-1))

    def test_threshold_openrange_neg_over(self):
        self.assertFalse(Threshold("~:10").check(11))


class TestCode(unittest.TestCase):

    def test_simple_default(self):
        plugin = Plugin()
        self.assertEqual(plugin.get_code(), UNKNOWN)

    def test_simple_ok(self):
        plugin = Plugin()
        plugin.add_result(OK, 'OK')
        self.assertEqual(plugin.get_code(), OK)

    def test_simple_warning(self):
        plugin = Plugin()
        plugin.add_result(WARNING, 'WARNING')
        self.assertEqual(plugin.get_code(), WARNING)

    def test_simple_critical(self):
        plugin = Plugin()
        plugin.add_result(CRITICAL, 'CRITICAL')
        self.assertEqual(plugin.get_code(), CRITICAL)

    def test_simple_owc(self):
        plugin = Plugin()
        plugin.add_result(OK, 'OK')
        plugin.add_result(WARNING, 'WARNING')
        plugin.add_result(CRITICAL, 'CRITICAL')
        self.assertEqual(plugin.get_code(), CRITICAL)

    def test_simple_ow(self):
        plugin = Plugin()
        plugin.add_result(OK, 'OK')
        plugin.add_result(WARNING, 'WARNING')
        self.assertEqual(plugin.get_code(), WARNING)

    def test_simple_cw(self):
        plugin = Plugin()
        plugin.add_result(CRITICAL, 'OK')
        plugin.add_result(WARNING, 'WARNING')
        plugin.add_result(WARNING, 'WARNING')
        plugin.add_result(WARNING, 'WARNING')
        plugin.add_result(WARNING, 'UNKNOWN')
        self.assertEqual(plugin.get_code(), CRITICAL)


class TestMessage(unittest.TestCase):

    def test_simple_default(self):
        plugin = Plugin()
        self.assertEqual(plugin.get_message(), '')

    def test_simple_ok(self):
        plugin = Plugin()
        plugin.add_result(OK, 'OK')
        self.assertEqual(plugin.get_message(), 'OK')

    def test_simple_owc(self):
        plugin = Plugin()
        plugin.add_result(OK, 'OK')
        plugin.add_result(WARNING, 'WARNING')
        plugin.add_result(CRITICAL, 'CRITICAL')
        self.assertEqual(plugin.get_message(joiner=', '),
                         ', '.join(['OK', 'WARNING', 'CRITICAL']))

    def test_simple_owc_level(self):
        plugin = Plugin()
        plugin.add_result(OK, 'OK')
        plugin.add_result(WARNING, 'WARNING')
        plugin.add_result(CRITICAL, 'CRITICAL')
        self.assertEqual(plugin.get_message(joiner=', ', msglevels=[WARNING]),
                         ', '.join(['WARNING']))


class TestExtData(unittest.TestCase):

    def test_simple(self):
        plugin = Plugin()
        plugin.add_extdata('OK')
        plugin.add_extdata('hey!')
        plugin.add_extdata('STUFF')
        self.assertEqual(plugin.get_extdata(),
                         '\n'.join(['OK', 'hey!', 'STUFF']))


if __name__ == '__main__':
    unittest.main()
