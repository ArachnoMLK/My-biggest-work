"""Tests of tools/bh/power_pick.py (slot -> power, `_-F5N._-42t`). Synthetic values only.
Run: python -I -m unittest discover -s tests"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh.power_pick import power_name, redirect  # noqa: E402

HERO = {"mBaseWeapon1": 4, "mBaseWeapon2": 5, "mSpecialPower1": "N1", "mSpecialPower2": "N2",
        "mSpecialPower1_Forward": "S1", "mSpecialPower2_Down": "D2"}


class PowerPick(unittest.TestCase):
    def test_signatures(self):
        w1 = {"id": 4, "slots": ["a%d" % i for i in range(12)]}
        w2 = {"id": 5, "slots": ["b%d" % i for i in range(12)]}
        self.assertEqual(power_name(11, HERO, w1), "N1")
        self.assertEqual(power_name(11, HERO, w2), "N2")
        self.assertEqual(power_name(7, HERO, w1), "S1")
        self.assertEqual(power_name(7, HERO, w2), "b7")
        self.assertEqual(power_name(8, HERO, w2), "D2")
        self.assertEqual(power_name(3, HERO, w1), "a3")
        self.assertIsNone(power_name(11, HERO, {"id": 9, "slots": w1["slots"]}))
        self.assertEqual(power_name(11, HERO, {"id": 9, "slots": w1["slots"]}, zombie=True), "a8")
        self.assertIsNone(power_name(14, HERO, w1))

    def test_redirect(self):
        table = {"P": {"PowerName": "P", "GCVersion": "PG", "MomentumVersion": "PM"},
                 "PG": {"PowerName": "PG"}, "PM": {"PowerName": "PM"}, "P_TESTFEATURE": {"PowerName": "PT"}}
        look = table.get
        self.assertEqual(redirect(table["P"], look)["PowerName"], "P")
        self.assertEqual(redirect(table["P"], look, gc=True)["PowerName"], "PG")
        self.assertEqual(redirect(table["P"], look, test_set=True)["PowerName"], "PT")
        self.assertEqual(redirect(table["P"], look, vx=-60.0, facing_left=True)["PowerName"], "PM")
        self.assertEqual(redirect(table["P"], look, vx=-60.0, facing_left=False)["PowerName"], "P")
        self.assertEqual(redirect(table["P"], look, vx=59.0)["PowerName"], "P")


if __name__ == "__main__":
    unittest.main()
