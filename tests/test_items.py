"""Tests of the thrown item motion (tools/bh/items.py). Synthetic values only.
Run: python -I -m unittest discover -s tests"""
import math
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh.items import (ITEM_DEFAULTS, after_sweep, bounce, expired, ground_walk, impact, item_type, sweep,  # noqa: E402
                      sweep_mask, wall_slide, linear_path, rocket_path, ease_22h, atan2_netsafe, boomerang_path, rocket_homing, lerp, throw_speed, throw_vector, throw_start, impact_special, throw_spawn,
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

class ItemWalk(unittest.TestCase):
    FLOOR = Line(0.0, 100.0, 300.0, 100.0, 1, (0.0, -1.0))
    WALL = Line(150.0, 0.0, 150.0, 100.0, 1, (-1.0, 0.0))

    def test_step_is_not_reduced(self):
        x, y, g, step, lu, vy, kinds = ground_walk([self.FLOOR], 0, 50.0, 98.99, self.FLOOR, 10.0, 3, 26.0, 0.0,
                                                   ITEM_DEFAULTS)
        self.assertAlmostEqual(x, 60.0)
        self.assertEqual((step, kinds), (10.0, []))                # the full step is used again by the free move

    def test_wall_bounces_back(self):
        x, y, g, step, lu, vy, kinds = ground_walk([self.FLOOR, self.WALL], 0, 140.0, 98.99, self.FLOOR, 20.0, 3,
                                                   52.0, 0.0, ITEM_DEFAULTS)
        self.assertAlmostEqual(x, 150.0 - 1.01)
        self.assertEqual((g, step, kinds), (self.WALL, -20.0, ["bounce"]))
        self.assertAlmostEqual(lu, -52.0 * 0.6)

    def test_not_on_a_floor(self):
        self.assertEqual(ground_walk([], 0, 1.0, 2.0, None, 5.0, 3, 0.0, 0.0, ITEM_DEFAULTS)[:4], (1.0, 2.0, None, 5.0))

class WallSlide(unittest.TestCase):
    def test_slides_down_to_the_floor(self):
        floor = Line(0.0, 100.0, 300.0, 100.0, 1, (0.0, -1.0))
        x, y, lu = wall_slide([floor], 0, 10.0, 90.0, 30.0, 0.0, 3, 0)
        self.assertEqual((x, lu), (10.0, 0.0))
        self.assertAlmostEqual(y, 100.0 - 1.01)
        self.assertEqual(wall_slide([], 0, 10.0, 0.0, 5.0, 2.0, 3, 0), (10.0, 3.0, 0.0))

class Paths(unittest.TestCase):
    def test_ease_and_atan2(self):
        self.assertEqual(ease_22h(True, False, 0, 2000), 0.0)
        self.assertEqual(ease_22h(True, False, 2000, 2000), 1.0)
        self.assertEqual(ease_22h(True, True, 1500, 3000), 0.5)
        self.assertEqual(ease_22h(False, False, 1000, 1000), 1.0)
        self.assertEqual(atan2_netsafe(0.0, 0.0), 0.0)
        self.assertEqual(atan2_netsafe(1.0, 1.0), 0.785)
        self.assertEqual(atan2_netsafe(0.0, -5.0), 3.142)

    def test_linear_keeps_launch_speed(self):
        lu, vy = linear_path(3.0, 4.0, (0.0, 10.0))
        self.assertAlmostEqual(lu, 6.0)
        self.assertAlmostEqual(vy, 8.0)
        self.assertEqual(linear_path(0.0, 0.0, (1.0, 1.0)), (0.0, 0.0))

    def test_rocket_accelerates(self):
        self.assertEqual(rocket_path(1000, 1000, (100.0, 0.0), False), (25.0, 0.0))     # 0.25 at launch
        self.assertEqual(rocket_path(3000, 1000, (100.0, 0.0), False), (150.0, 0.0))    # 1.5 after 2 s
        lu, vy = rocket_path(1000, 1000, (100.0, 0.0), True)                           # no wobble before 500 ms
        self.assertAlmostEqual(lu, 25.0)
        self.assertAlmostEqual(vy, 0.0)

class Boomerang(unittest.TestCase):
    def test_turn_moves_hits_to_contact(self):
        r = boomerang_path(1100, 1000, 0, (10.0, 0.0), -1.0, 0.0, 50.0, 0.0, (0.0, 0.0), False, 4, 1)
        self.assertEqual((r[2], r[3], r[4], r[5]), (1100, 0, 5, False))

    def test_pull_and_cap(self):
        lu, vy, turned, io, x5g, removed = boomerang_path(1200, 1000, 0, (10.0, 0.0), 10.0, 0.0, 100.0, 0.0,
                                                          (0.0, 0.0), False, 0, 0)
        self.assertAlmostEqual(lu, 10.0 - 100.0 * 10.0 * 0.05333333333333334 / 100.0)
        self.assertFalse(removed)
        lu, vy, *_ = boomerang_path(1200, 1000, 0, (10.0, 0.0), 0.0, -10.0, 0.0, 100.0, (0.0, 0.0), False, 0, 0)
        self.assertAlmostEqual(math.hypot(lu, vy), 10.0)                       # capped at |launch|
        self.assertEqual(boomerang_path(1200, 1000, 0, (10.0, 0.0), 10.0, 0.0, 100.0, 0.0, (0.0, 0.0), True,
                                        0, 0)[0], 10.0)                         # wobble: 1800 ms delay

    def test_removed_back_behind_or_without_thrower(self):
        self.assertTrue(boomerang_path(2000, 1000, 1500, (10.0, 0.0), -10.0, 0.0, -5.0, 0.0, (0.0, 0.0), False,
                                       0, 0)[5])
        self.assertTrue(boomerang_path(1100, 1000, 0, (10.0, 0.0), 10.0, 0.0, 5.0, 0.0, (0.0, 0.0), False, 0, 0,
                                       thrower_gone=True)[5])

class RocketHoming(unittest.TestCase):
    FIGHTERS = [(1, 0, 100.0, 0.0), (2, 0, 30.0, 0.0), (3, 3, 1.0, 0.0)]     # id 3 is knocked out (state 3)

    def test_slows_then_locks_nearest(self):
        lu, vy, tid, turned = rocket_homing(1500, 1000, 10.0, 0.0, (10.0, 0.0), 0.0, 0.0, 0, 0, self.FIGHTERS)
        self.assertEqual((lu, tid), (lerp(10.0, 0, 0.25), 0))
        lu, vy, tid, turned = rocket_homing(2001, 1000, 10.0, 0.0, (10.0, 0.0), 0.0, 0.0, 0, 0, self.FIGHTERS)
        self.assertEqual((lu, tid, turned), (10.0, 2, 2001))

    def test_lerp_toward_target(self):
        lu, vy, tid, turned = rocket_homing(3000, 1000, 0.0, 0.0, (0.0, 10.0), 0.0, 0.0, 2, 2001, self.FIGHTERS)
        self.assertAlmostEqual(lu, 0.1)                                      # 1 % of 10 toward +x
        self.assertEqual(tid, 2)
        self.assertEqual(rocket_homing(3000, 1000, 1.0, 2.0, (0.0, 10.0), 0.0, 0.0, 3, 5, self.FIGHTERS),
                         (1.0, 2.0, 0, 0))                                   # target knocked out: dropped

    def test_steer_turns_at_most_1_8_degrees(self):
        lu, vy, tid, turned = rocket_homing(2500, 1000, 0.0, -10.0, (10.0, 0.0), 0.0, 0.0, 2, 2000,
                                            self.FIGHTERS, steer=True)
        ang = math.atan2(vy, lu)
        self.assertAlmostEqual(ang, -math.pi / 2 + math.pi / 100, places=2)   # -90 deg turned 1.8 deg toward 0
        self.assertAlmostEqual(math.hypot(lu, vy), 10.0 * 0.25, places=2)      # min(500 / 1000, 1) / 2

class Throw(unittest.TestCase):
    def test_speed(self):
        self.assertEqual(throw_speed(0, False), 75.0)
        self.assertAlmostEqual(throw_speed(500, True), 55.0 * 1.4)
        self.assertAlmostEqual(throw_speed(5000, False), 75.0 * 1.8)          # charge capped at 1000

    def test_vector(self):
        x, y = throw_vector(0, 0, False, ITEM_DEFAULTS, None, 0.0, 0.0)       # facing right, y = -0.1
        n = math.hypot(1.0, -0.1)
        self.assertAlmostEqual(x, 75.0 / n)
        self.assertAlmostEqual(y, -0.1 * 75.0 / n)
        self.assertEqual(throw_vector(0, 1, True, ITEM_DEFAULTS, None, 4.0, 8.0), (4.0, -55.0 + 2.0))   # up
        prox = dict(ITEM_DEFAULTS, r58=True)
        x, y = throw_vector(0, 2, False, prox, 1, 0.0, 0.0)                    # down from a hard floor: dropped
        self.assertLess(y, 0)
        self.assertEqual(throw_vector(0, 2, False, prox, 2, 0.0, 0.0), (0.0, 55.0))   # soft floor: allowed

    def test_start(self):
        st = throw_start((10.0, -2.0), dict(ITEM_DEFAULTS, I2d=1.5, z4P=1), 3, 1, 2500, 9000)
        self.assertEqual((st["Lu"], st["33c"], st["launch"]), (15.0, -3.0, (15.0, -3.0)))
        self.assertEqual((st["W6M"], st["BG"], st["state"], st["O13"]), (True, True, 1, 9000))

class SpecialImpact(unittest.TestCase):
    def test_cases(self):
        self.assertEqual(impact_special(100, 1, ITEM_DEFAULTS, 1, 0, 0, 0), {})
        weapon = dict(ITEM_DEFAULTS, G3X=True)
        self.assertEqual(impact_special(100, 657, weapon, 1, 4, 0, 0), {"state": 6, "l45": 367})
        self.assertEqual(impact_special(100, 657, weapon, 1, 0, 0, 0), {})           # has not hit anyone
        boom = dict(ITEM_DEFAULTS, Q3g=True, o3Y="Boom")
        self.assertEqual(impact_special(500, 1, boom, 1, 0, 0, 0),
                         {"expire": True, "power": "Boom", "late_flag": True})
        self.assertEqual(impact_special(500, 1, boom, 0, 0, 0, 0), {})               # not thrown, not armed
        self.assertEqual(impact_special(500, 1, boom, 1, 0, 0, 0, thrower=False), {"expire": True})
        tele = dict(ITEM_DEFAULTS, **{"76N": "Teleport", "o3Y": "Tp"})
        self.assertTrue(impact_special(100, 1, tele, 1, 0, 0, 0)["teleport_thrower"])

class ThrowSpawn(unittest.TestCase):
    def test_spawn(self):
        floor = Line(-100.0, 50.0, 100.0, 50.0, 1, (0.0, -1.0))
        self.assertEqual(throw_spawn([floor], 0, 0.0, 0.0, False, 200), (0.0, -30.0))   # on the ground
        self.assertEqual(throw_spawn([floor], 0, 0.0, 0.0, True, 60), (0.0, -60.0))     # h < 0
        self.assertEqual(throw_spawn([floor], 0, 0.0, 0.0, True, 160), (0.0, 40.0))     # room below
        self.assertEqual(throw_spawn([floor], 0, 0.0, 0.0, True, 200), (0.0, -30.0))    # the floor is in the way

if __name__ == "__main__":
    unittest.main()
