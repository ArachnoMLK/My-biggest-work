"""Tests of the powerTypes cell expansion (tools/bh/power_data.py). See docs/hit-detection-11.00.md, 1.2.

Synthetic cells only; no game values. Run: python -I -m unittest discover -s tests
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh.power_data import cast_steps, expand, parse_float, parse_int, power_steps  # noqa: E402


class Parse(unittest.TestCase):
    def test_numbers(self):
        self.assertEqual(parse_int("12abc"), 12)
        self.assertIsNone(parse_int("x"))
        self.assertEqual(parse_float("2.5e1z"), 25.0)


class CastTime(unittest.TestCase):
    def test_steps(self):
        self.assertEqual(cast_steps("3,2:2,4@1"), ([3, 2, 0, 0, 4], [(0, 1), (1, 3), (4, 1)]))
        self.assertEqual(cast_steps(""), ([0], [(0, 1)]))


class Expand(unittest.TestCase):
    def test_kinds(self):
        self.assertEqual(expand(["5"], 0, 3), ([5, 5, 5], 15.0, None))
        self.assertEqual(expand(["t9"], 0, 3), ([3, 3, 3], 9.0, None))
        self.assertEqual(expand(["1|2"], 0, 3)[0], [1, 2, 1])
        self.assertEqual(expand(["0~10"], 0, 3)[0], [0, 5, 10])
        self.assertEqual(expand(["4&6"], 0, 2), ([4, 6], 0, 2))
        self.assertEqual(expand(["1", "2"], 1, 1)[0], [2])
        self.assertEqual(expand([], 0, 2)[0], [0, 0])

    def test_row(self):
        row = {"CastTime": "2,1:1", "AoERadiusX": "10&20,30", "CenterOffsetX": "1&2,5", "BaseDamage": "3,t4"}
        out = power_steps(row)
        self.assertEqual(out["CastTime"], [2, 1, 0])
        self.assertEqual(out["AoERadiusY"], [10, 20, 30, 30])             # falls back to AoERadiusX
        self.assertEqual(out["CenterOffsetX"], [1, 2, 5, 5])
        self.assertEqual(out["q24"], [(2 << 16) | 0, (1 << 16) | 2, (1 << 16) | 3])
        self.assertIsNone(power_steps({"CastTime": "1,1", "AoERadiusX": "5"})["q24"])
        self.assertEqual(out["D6M"], 7.0)


if __name__ == "__main__":
    unittest.main()
