"""Tests of the free-move sweep phase (tools/bh/air_move.py). See docs/hit-detection-11.00.md, section 7.4.

Run: python -I -m unittest discover -s tests   (from the repository root)
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh.air_move import MoveResult, air_move, respond, steep  # noqa: E402
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


if __name__ == "__main__":
    unittest.main()
