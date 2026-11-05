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



status_helpers = [n for n in node.body if isinstance(n, ast.FunctionDef)
                  and n.name == 'connection_status']
exec(compile(ast.Module(body=status_helpers, type_ignores=[]),
             '<status-helpers>', 'exec'), namespace)
connection_status = namespace['connection_status']


class CompactCardTests(unittest.TestCase):
    def test_connection_status_from_bluez(self):
        self.assertEqual(connection_status({'connected': True}), '✓ Connected')
        self.assertEqual(connection_status({'connected': False}), '✕ Disconnected')
        self.assertEqual(connection_status({}), '✕ Disconnected')

    def test_redundant_rows_are_absent(self):
        app = next(n for n in node.body if isinstance(n, ast.ClassDef)
                   and n.name == 'App')
        render = next(n for n in app.body if isinstance(n, ast.FunctionDef)
                      and n.name == 'render_structure')
        literals = [n.value for n in ast.walk(render)
                    if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        for removed in ('Connection', 'Bluetooth battery', 'NTAPP connection',
                        'Last action'):
            self.assertNotIn(removed, literals)

    def test_individual_battery_and_controls_remain(self):
        app = next(n for n in node.body if isinstance(n, ast.ClassDef)
                   and n.name == 'App')
        render = next(n for n in app.body if isinstance(n, ast.FunctionDef)
                      and n.name == 'render_structure')
        literals = [n.value for n in ast.walk(render)
                    if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        for required in ('Left earbud', 'Right earbud', 'Charging case',
                         'ANC / Transparency', 'Low latency / Gaming mode'):
            self.assertIn(required, literals)

# Pure device filtering and battery fallback logic (no GTK required).
device_helpers = [n for n in node.body if isinstance(n, ast.FunctionDef)
                  and n.name in ('connected_audio_devices', 'show_battery_fallback')]
exec(compile(ast.Module(body=device_helpers, type_ignores=[]),
             '<device-helpers>', 'exec'), namespace)
connected_audio_devices = namespace['connected_audio_devices']
show_battery_fallback = namespace['show_battery_fallback']


class DeviceSelectionTests(unittest.TestCase):
    def test_show_only_connected_earbuds(self):
        devices = [{'address': '1', 'connected': True},
                   {'address': '2', 'connected': False},
                   {'address': '3', 'connected': True}]
        self.assertEqual([d['address'] for d in connected_audio_devices(devices)],
                         ['1', '3'])

    def test_no_connected_devices(self):
        self.assertEqual(connected_audio_devices([{'connected': False}]), [])

    def test_switcher_is_conditional(self):
        app = next(n for n in node.body if isinstance(n, ast.ClassDef)
                   and n.name == 'App')
        render = next(n for n in app.body if isinstance(n, ast.FunctionDef)
                      and n.name == 'render_structure')
        checks = [n for n in ast.walk(render) if isinstance(n, ast.Compare)]
        self.assertTrue(any(isinstance(op, ast.Gt) and any(
            isinstance(const, ast.Constant) and const.value == 1
            for const in cmp.comparators) for cmp in checks for op in cmp.ops))


class BatteryFallbackTests(unittest.TestCase):
    def test_fallback_only_when_all_components_missing(self):
        self.assertTrue(show_battery_fallback({}, 95))
        self.assertTrue(show_battery_fallback({'left': None, 'right': None, 'case': None}, 95))
        self.assertFalse(show_battery_fallback({'left': {'percent': 72}}, 95))
        self.assertFalse(show_battery_fallback({'right': {'percent': 0}}, 95))
        self.assertFalse(show_battery_fallback({'case': {'percent': 20}}, 95))

    def test_no_fallback_when_bluez_battery_is_missing(self):
        self.assertFalse(show_battery_fallback({}, None))
        self.assertFalse(show_battery_fallback({}, 'unknown'))

    def test_partial_component_reading_hides_fallback(self):
        self.assertFalse(show_battery_fallback({'left': {'percent': 50},
                                                'right': None, 'case': None}, 80))


if __name__=='__main__':
    unittest.main()
