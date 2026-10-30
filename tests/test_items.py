"""Tests of the thrown item motion (tools/bh/items.py). Synthetic values only.
Run: python -I -m unittest discover -s tests"""
import math
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh.items import (ITEM_DEFAULTS, after_sweep, bounce, expired, impact, item_type, sweep, sweep_mask,  # noqa: E402
                      target_gate, velocity)
from bh.raycast import Line  # noqa: E402


class Ground:
    def __init__(self, ny):
        self.normal = (0.0, ny)


class Motion(unittest.TestCase):
    def test_air_friction_and_gravity(self):
        lu, vy, mv = velocity(100.0, 0.0, 0.0, 0.0, None, ITEM_DEFAULTS, thrown=False, o2o=False)
        self.assertAlmostEqual(lu, 100.0 - 0.15 * 0.384)
        self.assertAlmostEqual(vy, 3.75 * 0.384)
        self.assertAlmostEqual(mv[0], lu * 0.384)
        self.assertAlmostEqual(mv[1], vy * 0.384)

    def test_ground_friction_stops_and_rests(self):
        g = Ground(-1.0)
        lu, vy, mv = velocity(-0.5, 0.0, 0.0, 0.0, g, ITEM_DEFAULTS, thrown=False, o2o=False)
        self.assertEqual((lu, vy), (0.0, 0.0))                 # friction ate the speed; at rest: no gravity
        self.assertAlmostEqual(mv[1], 2.02)
        lu, vy, _ = velocity(0.0, 0.0, 0.0, 0.0, Ground(-0.8), ITEM_DEFAULTS, thrown=False, o2o=False)
        self.assertAlmostEqual(vy, 3.75 * 0.384)               # a slope: gravity still applies

    def test_cap_and_thrown_gravity(self):
        item = dict(ITEM_DEFAULTS, OY=1.0)
        lu, vy, _ = velocity(340.0, 349.0, 50.0, 50.0, None, item, thrown=True, o2o=False)
        self.assertEqual(lu, 350.0)
        self.assertAlmostEqual(vy, 350.0 + 1.0 * 0.384)        # cap before gravity
        _, vy, _ = velocity(0.0, 0.0, 0.0, 0.0, None, item, thrown=True, o2o=True)
        self.assertAlmostEqual(vy, 3.75 * 0.384)
        _, vy, _ = velocity(0.0, 5.0, 0.0, 0.0, None, item, thrown=False, o2o=False, bg=True)
        self.assertEqual(vy, 5.0)

    def test_mask_and_expiry(self):
        self.assertEqual(sweep_mask(True, 1, 1000, 1064, 0, False, 3.75, False), 1)
        self.assertEqual(sweep_mask(True, 1, 1000, 1065, 0, False, 3.75, False), 3)
        self.assertEqual(sweep_mask(False, 0, 0, 0, 1, True, 3.75, False), 1)
        self.assertEqual(sweep_mask(False, 1, 0, 0, 0, False, 0, True), 1)
        self.assertTrue(expired(2001, 1000, 1000))
        self.assertFalse(expired(2000, 1000, 1000))
        self.assertFalse(expired(99999, 0, 0))

    def test_item_type_cells(self):
        r = item_type({"Friction": "1.5", "PathType": "Rocket", "PathLength": "900", "ForceNoHitstop": "TRUE"})
        self.assertEqual((r["T2P"], r["z4P"], r["G6o"], r["T30"], r["h5M"]), (1.5, 3, 900, True, 0.15))
        self.assertEqual(item_type({"PathType": "Other"})["z4P"], 0)


def cand(**kw):
    c = {"bit": 4, "entity": True, "hitstun": False, "overlap": True}
    c.update(kw)
    return c


class Gates(unittest.TestCase):
    def test_first_contact_hits(self):
        self.assertEqual(target_gate(cand(), ITEM_DEFAULTS, 1100, 1000, 10.0, 0.0, 0, 0), (True, 0))

    def test_grace_after_throw(self):
        self.assertEqual(target_gate(cand(), ITEM_DEFAULTS, 1031, 1000, 10.0, 0.0, 0, 0), (False, 4))
        self.assertEqual(target_gate(cand(), ITEM_DEFAULTS, 1040, 1000, 1.0, 10.0, 0, 0), (False, 4))  # 64 on y
        self.assertTrue(target_gate(cand(hitstun=True), ITEM_DEFAULTS, 1001, 1000, 1.0, 0.0, 0, 0)[0])

    def test_contact_and_repeats(self):
        self.assertEqual(target_gate(cand(), ITEM_DEFAULTS, 1100, 1000, 1.0, 0.0, 0, 4), (False, 4))
        self.assertEqual(target_gate(cand(overlap=False), ITEM_DEFAULTS, 1100, 1000, 1.0, 0.0, 0, 6), (False, 2))
        self.assertFalse(target_gate(cand(), ITEM_DEFAULTS, 1100, 1000, 1.0, 0.0, 4, 0)[0])        # already hit
        rep = dict(ITEM_DEFAULTS, A4s=True)
        self.assertTrue(target_gate(cand(), rep, 1100, 1000, 1.0, 0.0, 4, 0)[0])
        self.assertFalse(target_gate(cand(), rep, 1100, 1000, 1.0, 0.0, -1, 0)[0])

    def test_other_gates(self):
        st = dict(ITEM_DEFAULTS, N59=True)
        self.assertFalse(target_gate(cand(), st, 1100, 1000, 1.0, 0.0, 0, 0)[0])
        self.assertFalse(target_gate(cand(thrower_stunned_by=True), ITEM_DEFAULTS, 1100, 1000, 1.0, 0.0, 0, 0)[0])
        self.assertTrue(target_gate(cand(thrower_stunned_by=True), ITEM_DEFAULTS, 1400, 1000, 1.0, 0.0, 0, 0)[0])
        self.assertEqual(target_gate(cand(catch=True, catch_dir=False), ITEM_DEFAULTS, 1100, 1000, 1.0, 0.0, 0, 0),
                         (False, 4))
        boom = dict(ITEM_DEFAULTS, z4P=1)
        self.assertEqual(target_gate(cand(u4b=900), boom, 1500, 1000, 1.0, 0.0, 0, 4), (True, 0))   # re-armed
        self.assertEqual(target_gate(cand(u4b=1200), boom, 1500, 1000, 1.0, 0.0, 0, 4), (False, 4))

class Sweep(unittest.TestCase):
    FLOOR = Line(-100.0, 50.0, 100.0, 50.0, 1, (0.0, -1.0))

    def test_lands_on_floor(self):
        x, y, g, head = sweep([self.FLOOR], 0, 0.0, 0.0, (0.0, 60.0), 3, 20)
        self.assertIs(g, self.FLOOR)
        self.assertFalse(head)
        self.assertAlmostEqual(y, 50.0 - 1.01)

    def test_free_and_no_geometry(self):
        self.assertEqual(sweep([self.FLOOR], 0, 0.0, 0.0, (0.0, 10.0), 3, 20)[:3], (0.0, 10.0, None))
        self.assertEqual(sweep([self.FLOOR], 0, 0.0, 0.0, (0.0, 60.0), 3, 20, no_geometry=True)[:3],
                         (0.0, 60.0, None))

    def test_item_ignore_lines_are_skipped(self):
        ign = Line(-100.0, 50.0, 100.0, 50.0, 1 | 32, (0.0, -1.0))
        self.assertIsNone(sweep([ign], 0, 0.0, 0.0, (0.0, 60.0), 3, 20)[2])

    def test_top_cast_stops_on_a_wall(self):
        wall = Line(10.0, -30.0, 10.0, -5.0, 1, (-1.0, 0.0))      # only the top (y - 20) reaches it
        x, y, g, head = sweep([wall], 0, 0.0, 0.0, (20.0, 0.0), 3, 20)
        self.assertIs(g, wall)
        self.assertTrue(head)
        self.assertAlmostEqual(x, 10.0 - 1.01)

class Impact(unittest.TestCase):
    FLOOR = Line(-100.0, 50.0, 100.0, 50.0, 1, (0.0, -1.0))
    WALL = Line(10.0, 0.0, 10.0, 50.0, 1, (-1.0, 0.0))

    def test_bounce_on_floor_and_wall(self):
        self.assertEqual(bounce(self.FLOOR, 3.0, 20.0, 0.6, 2.5), (3.0, -12.0))
        self.assertEqual(bounce(self.WALL, 20.0, 3.0, 0.6, 2.5), (-12.0, 3.0))
        bouncy = Line(-100.0, 50.0, 100.0, 50.0, 65, (0.0, -1.0))
        self.assertEqual(bounce(bouncy, 0.0, 20.0, 0.6, 2.5), (0.0, -16.0))      # (1 + 0.6) / 2

    def test_bounce_on_slope(self):
        n = (0.6, -0.8)
        slope = Line(0.0, 100.0, 80.0, 40.0, 1, n)
        lu, vy = bounce(slope, 0.0, 10.0, 0.5, 2.5)
        d = 10.0 * -0.8
        ux, uy = d * 0.6, d * -0.8
        wx, wy = -ux, 10.0 - uy
        k = (math.hypot(wx, wy) - 2.5) / math.hypot(wx, wy)
        self.assertAlmostEqual(lu, wx * k - ux * 0.5)
        self.assertAlmostEqual(vy, wy * k - uy * 0.5)

    def test_impact_kinds(self):
        self.assertEqual(impact(0.0, 4.0, self.FLOOR, ITEM_DEFAULTS)[2], "stop")
        self.assertEqual(impact(0.0, 5.0, self.FLOOR, ITEM_DEFAULTS), (0.0, -3.0, "bounce"))
        self.assertEqual(impact(1.0, 1.0, self.WALL, ITEM_DEFAULTS)[2], "bounce")
        strict = dict(ITEM_DEFAULTS, o1l=1)
        self.assertEqual(impact(20.0, 0.0, self.WALL, strict)[2], "stick")      # head-on: cos = -1
        self.assertEqual(impact(20.0, 20.0, self.WALL, strict)[2], "bounce")    # glancing: cos = -0.707
        self.assertEqual(impact(-20.0, 0.0, Line(10.0, 0.0, 10.0, 50.0, 1, (1.0, 0.0)), strict)[2], "stick")
        floors = dict(ITEM_DEFAULTS, o1l=2)
        self.assertEqual(impact(20.0, 0.0, self.WALL, floors, can_stick=True)[2], "bounce")
        self.assertEqual(impact(0.0, 20.0, self.FLOOR, floors, can_stick=True)[2], "stick")

    def test_after_sweep(self):
        self.assertEqual(after_sweep(0.0, 20.0, self.FLOOR, ITEM_DEFAULTS, 0), (0.0, -12.0, 0, "bounce"))
        self.assertEqual(after_sweep(0.0, 0.0, self.FLOOR, ITEM_DEFAULTS, 2), (0.0, 0.0, 0, None))
        self.assertEqual(after_sweep(0.0, 20.0, self.FLOOR, ITEM_DEFAULTS, 1)[2], 0)     # 144 <= 2500: rests
        self.assertEqual(after_sweep(60.0, 0.0, self.FLOOR, ITEM_DEFAULTS, 1)[2], 1)     # 3600 > 2500
        self.assertEqual(after_sweep(0.0, 3.0, self.FLOOR, ITEM_DEFAULTS, 3), (0.0, 0.0, 3, None))
        self.assertEqual(after_sweep(1.0, 1.0, None, ITEM_DEFAULTS, 0), (1.0, 1.0, 0, None))

    def test_stick_flags_cell(self):
        self.assertEqual(item_type({"ConditionalStickToWalls": "STRICT_ANGLE|FLOORS_ONLY"})["o1l"], 3)
        self.assertEqual(item_type({"Elasticity": "0.25", "AlwaysArmed": "true"})["7c"], 0.25)

if __name__ == "__main__":
    unittest.main()
