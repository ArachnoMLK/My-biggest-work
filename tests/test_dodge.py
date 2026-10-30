"""Tests of the commit part of Entity.Dodge (tools/bh/dodge.py). Synthetic values only.
Run: python -I -m unittest discover -s tests"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh.dodge import (attack_air_offset, cancel_end, cancel_flags, clears_velocity, cooldown_ms,  # noqa: E402
                      counter, dash, dodge_over, ease, exit_speed, exit_velocity, facing, formula_mult, k64, kind,
                      landed_cooldown, moves, neutral_push, pick, push, side_latch, speed_x, speed_y, standard_flag,
                      timers)


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

    def test_moves(self):
        self.assertFalse(moves(0, 1))
        self.assertTrue(moves(0, 2))
        self.assertTrue(moves(1, 1))

    def test_ease(self):
        self.assertEqual(ease("None", 1100, 1000, 300, 100), 1.0)
        self.assertAlmostEqual(ease("EaseHorizontal", 1080, 1000, 300, 100), 1.5)
        self.assertAlmostEqual(ease("EaseHorizontal", 1100, 1000, 300, 100), 1 - 0.25 / 3)

    def test_push(self):
        args = dict(t=1000, h2b=1000, e3e=0, moving=True, t5l=0.5, wl=0.25, ax_mult=2.0, ay_mult=1.0,
                    ax_formula="", ay_formula="", uy=100, c1d=100)
        self.assertEqual(push(o5c=4, **args), (-60.0, 15.0))
        self.assertEqual(push(o5c=8, **args), (60.0, 15.0))
        self.assertEqual(push(o5c=1, **args), (0.0, 15.0))
        self.assertIsNone(push(o5c=8, **dict(args, t=999)))
        self.assertIsNone(push(o5c=8, **dict(args, e3e=4096)))
        self.assertIsNone(push(o5c=8, **dict(args, moving=False)))

    def test_side_latch(self):
        self.assertEqual(side_latch(False, False, 4), (True, True))
        self.assertEqual(side_latch(True, True, 4), (True, True))
        self.assertEqual(side_latch(True, True, 8), (True, False))
        self.assertEqual(side_latch(True, False, 8), (True, False))
        self.assertEqual(side_latch(False, True, 12), (False, True))

    def test_exit_speed(self):
        self.assertEqual(exit_speed(60.0), 60.0)
        self.assertEqual(exit_speed(30.0), 41.25)

    def test_exit_velocity(self):
        k = dict(a=30.0, moving=True, l4a=False, g5e=False, t5l=2.0, exit_x=0.5, exit_back_x=0.25,
                 exit_y=0.5, exit_back_y=0.25)
        self.assertEqual(exit_velocity(5.0, 0.0, held=0, **k), (41.25, 0.0, None))
        self.assertEqual(exit_velocity(5.0, 0.0, held=4, **k), (20.625, 0.0, True))
        self.assertEqual(exit_velocity(-5.0, 0.0, held=4, **k), (-82.5, 0.0, True))
        self.assertEqual(exit_velocity(0.0, 8.0, held=1, **k), (0.0, 2.0, None))
        self.assertEqual(exit_velocity(0.0, -8.0, held=0, **k), (0.0, -4.0, None))
        self.assertEqual(exit_velocity(5.0, 8.0, held=0, **dict(k, l4a=True, g5e=True)), (20.625, 4.0, True))
        self.assertEqual(exit_velocity(5.0, 8.0, held=0, **dict(k, moving=False)), (5.0, 4.0, None))

    def test_dash(self):
        base = dict(t=1000, dir=0, y1u=False, w4c=False, grounded=True, held=0, held_left=False,
                    facing_left=False, ve=0, v22=0, r3l=0, t5z=False, m3v=False, k1k=0, d532=0, e3=0, m3h=False,
                    vx=0.0, vy=0.0, l3a=0, t26=0, w47=False)
        self.assertIsNone(dash(**dict(base, grounded=False)))
        w = dash(**base)
        self.assertEqual((w["_-L3a"], w["dir_left"], w["_-t5z"], w["_-v3x"]), (1, False, True, 1000))
        self.assertEqual(dash(**dict(base, y1u=True))["_-L3a"], 6)  # kind 2 is not reached
        self.assertIsNone(dash(**dict(base, k1k=950)))
        # a fresh Left press without _-t5z, right after a tap: the dash turns (kind 3)
        w = dash(**dict(base, dir=4, held=4, ve=950))
        self.assertEqual((w["_-L3a"], w["dir_left"]), (3, False))
        self.assertEqual(dash(**dict(base, dir=4, held=4, ve=950, vx=20.0))["_-L3a"], 7)
        self.assertIsNone(dash(**dict(base, dir=4, held=4, ve=950, l3a=3, t26=400)))
        self.assertEqual(dash(**dict(base, dir=4, held=4, ve=950, l3a=3, t26=300))["_-L3a"], 3)
        w = dash(**dict(base, m3v=True, w47=True))
        self.assertEqual((w["_-L3a"], w["_-K1k"], w["_-w47"]), (4, 1000, False))
        self.assertEqual(dash(**dict(base, m3v=True, l3a=7))["_-L3a"], 5)
        w = dash(**dict(base, dir=4, held=4, w4c=True, vy=-1.0, ve=950))
        self.assertEqual((w["_-L3a"], w["dir_left"]), (6, True))

    def test_cancel_flags(self):
        k = dict(t=1100, in_dodge=True, f2b=False, light=1090, heavy=0, taunt=0, pickup=0, dodge_press=0, h2b=1000,
                 chase_ok=False, move_no_chain=False, o5c=0, cancel_start=4, cancel_limit=8)
        self.assertEqual(cancel_flags(**k), (True, True, False))
        self.assertEqual(cancel_flags(**dict(k, t=1063)), (False, False, False))
        self.assertEqual(cancel_flags(**dict(k, t=1129)), (False, False, False))
        self.assertEqual(cancel_flags(**dict(k, in_dodge=False)), (False, False, False))
        self.assertEqual(cancel_flags(**dict(k, move_no_chain=True)), (False, False, False))
        self.assertEqual(cancel_flags(**dict(k, f2b=True, o5c=4)), (True, False, False))
        self.assertEqual(cancel_flags(**dict(k, f2b=True, dodge_press=1050, chase_ok=True)), (False, False, True))

    def test_attack_air_offset(self):
        self.assertEqual(attack_air_offset(True, False, False, False), (3, False))
        self.assertEqual(attack_air_offset(True, False, True, False), (0, False))
        self.assertEqual(attack_air_offset(False, True, False, True), (3, False))
        self.assertEqual(attack_air_offset(True, False, False, True), (0, True))
        self.assertEqual(attack_air_offset(False, False, False, True), (0, False))

    def test_cancel_end(self):
        k = dict(t5l=1.0, wl=0.5, ax_mult=0.5, ay_mult=1.0, o5c=4, gc=False, uy=96, cooldown=10, airborne=True)
        self.assertEqual(cancel_end(40.0, -50.0, **k), {"_-T2R": 0, "_-v1D": -30.0, "_-P5S": 30.0})
        self.assertEqual(cancel_end(20.0, 10.0, **k), {"_-T2R": 0})
        self.assertEqual(cancel_end(80.0, 0.0, **dict(k, ax_mult=2.0, o5c=8))["_-v1D"], 60.0)
        w = cancel_end(0.0, 0.0, **dict(k, gc=True))
        self.assertEqual((w["_-a1h"], w["_-y1F"], w["power_I2g_or_2"]), (True, 256, True))

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
