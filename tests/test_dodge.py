"""Tests of the commit part of Entity.Dodge (tools/bh/dodge.py). Synthetic values only.
Run: python -I -m unittest discover -s tests"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh.dodge import (clears_velocity, cooldown_ms, counter, dodge_over, facing, formula_mult, k64,  # noqa: E402
                      kind, landed_cooldown, neutral_push, pick, speed_x, speed_y, standard_flag, timers)


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
        self.assertEqual(counter(3 << 16 | 1, chained=False, has_dir_bits=True, airborne=False, f2b=True), 1 << 16 | 1)
        self.assertEqual(counter(3 << 16, chained=False, has_dir_bits=False, airborne=False, f2b=True), 0)
        self.assertEqual(counter(3 << 16, chained=True, has_dir_bits=True, airborne=True, f2b=True), 4 << 16 | 2)
        self.assertEqual(counter(3 << 16, chained=True, has_dir_bits=False, airborne=False, f2b=False), 4 << 16)
        self.assertEqual(counter(3 << 16, chained=False, has_dir_bits=True, airborne=False, f2b=True, e6p=True),
                         4 << 16 | 1)

    def test_kind(self):
        self.assertEqual([kind(d) for d in (0, 4, 8, 1, 2, 4 | 1, 8 | 2, 1 | 2)], [0, 1, 1, 2, 4, 3, 5, 2])

    def test_pick(self):
        rows = [{"DodgeName": "a", "Set": "Default", "kind": 1, "where": 1, "IsFast": False},
                {"DodgeName": "b", "Set": "Default", "kind": 1, "where": 3, "IsFast": False},
                {"DodgeName": "c", "Set": "Test", "kind": 1, "where": 3, "IsFast": False},
                {"DodgeName": "StandardSpot", "Set": "Default", "kind": 0, "where": 3, "IsFast": False}]
        self.assertEqual(pick(rows, 4, airborne=False, is_fast=False)["DodgeName"], "a")   # ground: mask 1
        self.assertEqual(pick(rows, 4, airborne=True, is_fast=False)["DodgeName"], "b")    # _-wn() (air): mask 2
        self.assertEqual(pick(rows, 8, airborne=True, is_fast=False, test_set=True)["DodgeName"], "c")
        self.assertEqual(pick(rows, 1, airborne=False, is_fast=False)["DodgeName"], "StandardSpot")
        self.assertEqual(pick(rows, 4, airborne=False, is_fast=True)["DodgeName"], "StandardSpot")


    def test_landed_cooldown(self):
        args = dict(airborne=False, r51=0, hitstun=False, a1h=False, q42=3, t=1240, i46=1000,
                    cooldown_landed=2, uy=100, c1d=50)
        self.assertEqual(landed_cooldown(500, **args), 182)
        self.assertEqual(landed_cooldown(150, **args), 150)
        self.assertEqual(landed_cooldown(500, **dict(args, t=1239)), 500)
        self.assertEqual(landed_cooldown(500, **dict(args, airborne=True)), 500)
        self.assertEqual(landed_cooldown(500, **dict(args, q42=0)), 500)

    def test_dodge_over(self):
        self.assertEqual(dodge_over(1000, True, 700, 300, 0), (True, True))
        self.assertEqual(dodge_over(999, True, 700, 300, 0), (False, False))
        self.assertEqual(dodge_over(1000, True, 700, 300, 889), (False, False))
        self.assertEqual(dodge_over(1000, True, 700, 300, 888), (True, True))
        self.assertEqual(dodge_over(1000, True, 0, 300, 0), (True, False))
        self.assertEqual(dodge_over(1000, False, 700, 300, 0), (False, False))

    def test_k64(self):
        self.assertEqual(k64(False, True, 10.0, 0.5, 20.0, 2.0), 5.0)
        self.assertEqual(k64(True, True, 10.0, 0.5, 20.0, 2.0), 40.0)
        self.assertEqual(k64(False, False, 10.0, 0.5, 20.0, 2.0), 40.0)

    def test_standard_flag(self):
        self.assertTrue(standard_flag(1064, True, 1000, 0))
        self.assertFalse(standard_flag(1065, True, 1000, 0))
        self.assertFalse(standard_flag(1000, False, 1000, 0))
        self.assertFalse(standard_flag(1000, True, 0, 0))
        self.assertFalse(standard_flag(1000, True, 1000, 1))

    def test_formula_mult(self):
        self.assertEqual(formula_mult("Other", 5.0, 10.0, 0), 1.0)
        self.assertEqual(formula_mult("MomentumHorizontal", -30.0, 10.0, 0), 0.75)
        self.assertAlmostEqual(formula_mult("StandardHorizontal", 10.0, 10.0, 8), 1.0)       # at k: x = 1
        self.assertAlmostEqual(formula_mult("StandardHorizontal", 20.0, 10.0, 8), 1.0)       # past k
        self.assertAlmostEqual(formula_mult("StandardHorizontal", 0.0, 10.0, 8), 0.6 + 0.25 * 0.4)   # x = 0.5
        self.assertAlmostEqual(formula_mult("StandardHorizontal", 10.0, 10.0, 4), 0.7 - 0.125 * 0.8)  # k = -10, x = 0
        self.assertAlmostEqual(formula_mult("StandardHorizontal", -20.0, 10.0, 4), 1.0)      # past -k on the left

    def test_speed_x(self):
        self.assertEqual(speed_x(2.0, 1.5, 0, 4, 9.0, 10.0), 3.0)
        self.assertEqual(speed_x(2.0, 1.5, 3.0, 0, 9.0, 10.0), 3.0)
        self.assertAlmostEqual(speed_x(2.0, 1.0, 3.0, 8, 1.0, 10.0), 2.0)            # r clamped to 0.33
        self.assertAlmostEqual(speed_x(2.0, 1.0, 3.0, 4, -9.0, 10.0), 6.0)           # r clamped to 0.57

    def test_speed_y(self):
        self.assertEqual(speed_y(2.0, 1.5, 0, 1, -30.0), 3.0)
        self.assertAlmostEqual(speed_y(2.0, 1.0, 3.0, 1, 10.0), 2.0)                 # up while falling: 0 -> 0.5
        self.assertAlmostEqual(speed_y(2.0, 1.0, 3.0, 1, -40.0), 6.0)                # r = 1 -> 0.75
        self.assertAlmostEqual(speed_y(2.0, 1.0, 3.0, 2, 42.0), 2.0 * (1.0 + 0.4 * 2.0))   # r = 0.6

    def test_cooldown(self):
        self.assertEqual(cooldown_ms(10, 4, True), 160)
        self.assertEqual(cooldown_ms(10, 4, False), 64)


if __name__ == "__main__":
    unittest.main()
