"""Tests of the powerTypes column map (tools/bh/powertypes.py). See docs/power-columns-11.00.md.

Run: python -I -m unittest discover -s tests   (from the repository root)
"""
import hashlib
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh import abc, movement, powertypes, swf  # noqa: E402

GAME = os.environ.get("BRAWLHALLA_DIR", r"C:\Program Files (x86)\Steam\steamapps\common\Brawlhalla")
HAVE_GAME = os.path.exists(os.path.join(GAME, "BrawlhallaAir.swf"))

# A made-up listing in the parser's shape: one scalar column, one list column and its vector fill.
FAKE = {
    0: ("getlocal", "32"), 2: ("pushstring", "'Speed'"), 4: ("ifne", "10"),
    8: ("getlocal", "4"), 10: ("getlocal", "30"), 12: ("initproperty", "_-aa"), 14: ("jump", "40"),
    18: ("getlocal", "32"), 20: ("pushstring", "'Hits'"), 22: ("ifne", "6"),
    26: ("split", ""), 28: ("setlocal", "7"),
    32: ("getlocal", "4"), 34: ("getlocal", "7"), 36: ("pushnull", ""), 38: ("getlocal", "4"),
    40: ("getproperty", "_-bb"), 42: ("getlocal", "43"), 44: ("getlocal", "49"),
    46: ("callpropvoid", "_-42F, 6"),
}


class Listing(unittest.TestCase):
    def test_blocks(self):
        cols = powertypes.columns_from_listing(FAKE)
        self.assertEqual(cols["Speed"], {"fields": ["_-aa"], "locals": []})
        self.assertEqual(cols["Hits"], {"fields": [], "locals": ["7"]})

    def test_vector_fill(self):
        self.assertEqual(powertypes.vector_fields(FAKE), {"7": "_-bb"})


class Cli(unittest.TestCase):
    def test_wrong_patch_exits_2(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "other.abc")
            with open(p, "wb") as f:
                f.write(b"not the pinned abc")
            out = subprocess.run([sys.executable, "-I", os.path.join(ROOT, "tools", "bht.py"), "power-columns", "--abc", p],
                                 capture_output=True, text=True)
        self.assertEqual(out.returncode, 2, out.stderr)


@unittest.skipUnless(HAVE_GAME, "Brawlhalla not installed")
class Game(unittest.TestCase):
    def test_known_columns(self):
        with open(os.path.join(GAME, "BrawlhallaAir.swf"), "rb") as f:
            main = swf.Swf(f.read())
        data = max(main.abc_blocks(), key=lambda b: len(b[1]))[1]
        if hashlib.sha256(data).hexdigest() != movement.ABC_1100:
            self.skipTest("pinned to patch 11.00")
        cmap = powertypes.column_map(abc.Abc(data))
        self.assertEqual(len(cmap), 171)
        self.assertEqual(cmap["VariableImpulse"], ["_-W1a"])
        self.assertEqual(cmap["FixedImpulse"], ["_-C7"])
        self.assertEqual(cmap["BaseDamage"], ["_-L69"])
        self.assertEqual(cmap["DIMaxAngle"], ["_-x1F"])
        self.assertEqual(cmap["FixedStunTime"], ["_-7Z", "_-T6p"])


if __name__ == "__main__":
    unittest.main()
