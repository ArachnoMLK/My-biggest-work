"""Tests of the free-move sweep phase (tools/bh/air_move.py). See docs/hit-detection-11.00.md, section 7.4.

Run: python -I -m unittest discover -s tests   (from the repository root)
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh.air_move import MoveResult, WallState, air_move, respond, steep, wall_contact  # noqa: E402
from bh.raycast import Line  # noqa: E402


def floor(y, type_=1):
    return Line(-1000, y, 1000, y, type=type_, normal=(0.0, -1.0))


class Free(unittest.TestCase):
    def test_no_hit(self):
        r = air_move([], 1, 0.0, 0.0, 5.0, 10.0, False)
        self.assertEqual((r.x, r.y, r.ground), (5.0, 3.84, None))

    def test_land_on_floor(self):
        f = floor(100)
        r = air_move([f], 1, 0.0, 50.0, 0.0, 200.0, False)
        self.assertIs(r.ground, f)
        self.assertAlmostEqual(r.y, 100 - 1.01)

    def test_drop_through_soft(self):
        soft = floor(100, type_=2)
        self.assertIs(air_move([soft], 1, 0.0, 50.0, 0.0, 200.0, False).ground, soft)
        self.assertIsNone(air_move([soft], 1, 0.0, 50.0, 0.0, 200.0, False, drop_through=True).ground)

    def test_wall(self):
        wall = Line(50, -500, 50, 500, type=1, normal=(-1.0, 0.0))
        r = air_move([wall], 1, 0.0, 0.0, 60.0, 0.0, False)
        self.assertAlmostEqual(r.x, 50 - 1.01)

    def test_head_bump(self):
        ceiling = Line(-1000, -130, 1000, -130, type=1, normal=(0.0, 1.0))
        r = air_move([ceiling], 1, 0.0, 0.0, 0.0, -100.0, False)
        self.assertTrue(r.head_stop)
        self.assertAlmostEqual(r.y, -10 + 1.01)

    def test_ground_push(self):
        self.assertAlmostEqual(air_move([], 1, 0.0, 0.0, 0.0, 0.0, True).y, 2.02)


class Respond(unittest.TestCase):
    def test_wall_slide_keeps_falling(self):
        wall = Line(50, -500, 50, 500, type=1, normal=(-1.0, 0.0))
        r = air_move([wall], 1, 0.0, 0.0, 60.0, 20 / 0.384, False)
        out = respond([wall], 1, r, 20 / 0.384, 60.0)
        self.assertEqual(out.kind, "wall")
        self.assertAlmostEqual(out.y, r.y + (r.wanted[1] - r.move[1]))
        self.assertGreater(out.y, r.y)

    def test_ceiling_stops_rising(self):
        ceiling = Line(-1000, -130, 1000, -130, type=1, normal=(0.0, 1.0))
        r = air_move([ceiling], 1, 0.0, 0.0, 0.0, -100.0, False)
        out = respond([ceiling], 1, r, -100.0, 0.0)
        self.assertEqual((out.kind, out.p5s), ("ceiling", 0))

    def test_steep_slope_slides(self):
        g = Line(0, 0, 30, -100, type=1, normal=(-0.9578, -0.2873))
        self.assertTrue(steep(g))
        r = MoveResult(10.0, -20.0, g, False, [], (0.0, 5.0), (0.0, 20.0), 3)
        out = respond([], 1, r, 50.0, 0.0)
        self.assertEqual((out.kind, out.v1d), ("slope", -15.0))
        self.assertAlmostEqual(out.x, 10 - 15 * 30 / (30 ** 2 + 100 ** 2) ** 0.5)
        self.assertAlmostEqual(out.y, -20 + 15 * 100 / (30 ** 2 + 100 ** 2) ** 0.5)

    def test_floor_is_other(self):
        f = floor(100)
        r = air_move([f], 1, 0.0, 50.0, 0.0, 200.0, False)
        self.assertEqual(respond([f], 1, r, 200.0, 0.0).kind, "other")


class Wall(unittest.TestCase):
    WALL = Line(50, 0, 50, 500, type=1, normal=(-1.0, 0.0))     # top at y = 0
    TOP = Line(50, 0, 300, 0, type=1, normal=(0.0, -1.0))

    def test_ledge_assist(self):
        ws = WallState(t=1000, can_cling=True, t46=False, r51_before=0, f84q=10.0)
        x, y, p5s, v1d, r51, _, _, mantled = wall_contact([self.WALL, self.TOP], 1, 48.99, 40.0, self.WALL, 0.0, 0.0, ws)
        self.assertTrue(mantled)
        self.assertIsNone(r51)
        self.assertLess(y, 0)                       # standing on the top
        self.assertAlmostEqual(p5s, 10.0 * 0.384)

    def test_first_contact_stops_fall(self):
        ws = WallState(t=1000, can_cling=False, t46=False, r51_before=2, f84q=10.0)
        _, _, p5s, v1d, r51, _, _, _ = wall_contact([self.WALL], 1, 48.99, 300.0, self.WALL, 50.0, 0.0, ws)
        self.assertEqual(r51, 2)
        self.assertLess(p5s, 50.0)                  # damped: 50 - (10 + 0) * 0.85 * 0.384
        self.assertAlmostEqual(p5s, 50 - 10 * 0.85 * 0.384)
        self.assertEqual(v1d, 10.0)                 # pushed toward the wall on its right

    def test_sticky_hold(self):
        sticky = Line(50, 0, 50, 500, type=9, normal=(-1.0, 0.0))
        ws = WallState(t=1000, can_cling=False, t46=False, r51_before=2, g1t=True, y1l=3000)
        _, _, p5s, _, _, g1t, y1l, _ = wall_contact([sticky], 1, 48.99, 300.0, sticky, 40.0, 0.0, ws)
        self.assertEqual((p5s, g1t, y1l), (0, True, 3000))


if __name__ == "__main__":
    unittest.main()
