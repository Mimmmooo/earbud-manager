"""Pure UI decision logic (importing UI requires GI from system Python)."""
import sys
import pathlib
import types
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1] / 'src'
sys.path.insert(0, str(ROOT))

# GTK unavailable in some CI hosts; only load the pure helper function via AST.
import ast
source = (ROOT / 'earbuds_manager.py').read_text()
node = ast.parse(source)
fn = next(n for n in node.body if isinstance(n, ast.FunctionDef) and n.name=='battery_summary')
namespace={}
exec(compile(ast.Module(body=[fn],type_ignores=[]),'<helpers>','exec'),namespace)
battery_summary=namespace['battery_summary']

class BatterySummaryTests(unittest.TestCase):
    def test_lower_earbud(self):
        self.assertEqual(battery_summary({'left':{'percent':85},'right':{'percent':60}},95), '60% (lowest earbud)')
    def test_single_earbud(self):
        self.assertEqual(battery_summary({'left':{'percent':79}},95), '79% (lowest earbud)')
    def test_bluez_fallback(self):
        self.assertEqual(battery_summary({},95), '95%')
    def test_missing(self):
        self.assertEqual(battery_summary({},None), 'Not reported')


# More pure functions, extracted without loading GTK.
helpers = [n for n in node.body if isinstance(n, ast.FunctionDef)
           and n.name in ('validate_device_name', 'known_cmf')]
exec(compile(ast.Module(body=helpers, type_ignores=[]), '<helpers>', 'exec'), namespace)
validate_device_name = namespace['validate_device_name']
known_cmf = namespace['known_cmf']


class RenameValidationTests(unittest.TestCase):
    def test_trim_spaces_and_keep_unicode(self):
        self.assertEqual(validate_device_name('  আমার Buds  '), 'আমার Buds')

    def test_reject_empty_or_long_name(self):
        for name in (' ', 'x' * 65):
            with self.assertRaises(ValueError):
                validate_device_name(name)

    def test_reject_line_breaks_and_controls(self):
        for name in ('First\nSecond', 'Test\x00Name', 'A\tB'):
            with self.assertRaises(ValueError):
                validate_device_name(name)

    def test_custom_bluez_alias_does_not_hide_cmf_controls(self):
        device = {'name': 'Ayon Earbuds', 'original_name': 'CMF Buds 2', 'uuids': []}
        self.assertTrue(known_cmf(device))

    def test_unknown_device_not_treated_as_cmf(self):
        device = {'name': 'Other Headphones', 'original_name': '', 'uuids': []}
        self.assertFalse(known_cmf(device))


if __name__=='__main__':
    unittest.main()
