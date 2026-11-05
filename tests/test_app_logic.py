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

if __name__=='__main__':
    unittest.main()
