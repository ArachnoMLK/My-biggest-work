"""Tests of the commit part of Entity.Dodge (tools/bh/dodge.py). Synthetic values only.
Run: python -I -m unittest discover -s tests"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh.dodge import clears_velocity, counter, facing, neutral_push, timers  # noqa: E402


class Dodge(unittest.TestCase):
    def test_facing(self):
        self.assertTrue(facing(4, False))
        self.assertFalse(facing(8, True))
        self.assertTrue(facing(4 | 8, False))          # Left is tested first
        self.assertEqual(facing(1, "keep"), "keep")
        self.assertEqual(facing(0, "keep"), "keep")

    def test_timers(self):
        d = timers(1000, 10, 5, True, 32)
        self.assertEqual(d, {"_-H2b": 1000, "_-Uy": 160, "_-C1d": 80, "_-T2R": 1160, "_-G6S": 1240, "_-y1F": 272})
        self.assertIsNone(timers(1000, 10, 5, False, 0)["_-G6S"])

    def test_timers_chain_cap(self):
        self.assertEqual(timers(1000, 10, 5, False, 0, chain_end=1500)["_-y1F"], 500)
        self.assertEqual(timers(1000, 10, 5, False, 0, chain_end=1100)["_-y1F"], 240)

    def test_velocity(self):
        self.assertTrue(clears_velocity(4, False))
        self.assertTrue(clears_velocity(0, True))
        self.assertFalse(clears_velocity(0, False))
        self.assertEqual(neutral_push(7.5, 4), -7.5)
        self.assertEqual(neutral_push(7.5, 0), 7.5)

    def test_counter(self):
        self.assertEqual(counter(3 << 16 | 1, chained=False, has_dir_bits=True, grounded=False, f2b=True), 1 << 16 | 1)
        self.assertEqual(counter(3 << 16, chained=False, has_dir_bits=False, grounded=False, f2b=True), 0)
        self.assertEqual(counter(3 << 16, chained=True, has_dir_bits=True, grounded=True, f2b=True), 4 << 16 | 2)
        self.assertEqual(counter(3 << 16, chained=True, has_dir_bits=False, grounded=False, f2b=False), 4 << 16)
        self.assertEqual(counter(3 << 16, chained=False, has_dir_bits=True, grounded=False, f2b=True, e6p=True),
                         4 << 16 | 1)


if __name__ == "__main__":
    unittest.main()
