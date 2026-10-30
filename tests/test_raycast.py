"""Tests of the map ray cast transcription (tools/bh/raycast.py). See docs/hit-detection-11.00.md, section 7.

Run: python -I -m unittest discover -s tests   (from the repository root)
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh.hitdetect import line_of_sight_blocked, map_ray  # noqa: E402
from bh.raycast import OPT_SOFT_BOTH_SIDES, OPT_TWO_SIDED, Line, ray_cast, segment_hit, side_of  # noqa: E402


def wall(x, lo, hi, type_=1, normal=None):
    return Line(x, lo, x, hi, type=type_, normal=normal)


def floor(y, lo, hi, type_=1):
    return Line(lo, y, hi, y, type=type_, normal=(0, -1))


class Basics(unittest.TestCase):
    def test_side(self):
        side, n = side_of(0, -5, -10, 0, 20, 0)
        self.assertEqual(n, (-0.0, -1.0))
        self.assertEqual(side, 5.0)

    def test_segment_hit(self):
        self.assertEqual(segment_hit(0, 0, 10, 0, 5, -5, 5, 5), (5.0, 0.0))
        self.assertIsNone(segment_hit(0, 0, 10, 0, 0, 1, 10, 1))

    def test_zero_direction(self):
        self.assertIsNone(ray_cast([wall(5, -5, 5)], 0, 0, 0, 0, 0, 1))


class Cast(unittest.TestCase):
    def test_nearest_wins(self):
        a, b = wall(8, -5, 5), wall(4, -5, 5)
        hit = ray_cast([a, b], 0, 0, 0, 10, 0, 1, OPT_TWO_SIDED)
        self.assertIs(hit.line, b)
        self.assertEqual(hit.point, (4.0, 0.0))
        self.assertEqual(hit.remaining, (4.0, 0.0))

    def test_equal_distance_later_wins(self):
        a, b = wall(5, -5, 5), wall(5, -1, 1)
        self.assertIs(ray_cast([a, b], 0, 0, 0, 10, 0, 1, OPT_TWO_SIDED).line, b)

    def test_filters(self):
        w = wall(5, -5, 5, type_=1)
        self.assertIsNone(ray_cast([w], 0, 0, 0, 10, 0, 2, OPT_TWO_SIDED))           # mask
        w.owner = 3
        self.assertIsNone(ray_cast([w], 3, 0, 0, 10, 0, 1, OPT_TWO_SIDED))           # own line
        self.assertIsNotNone(ray_cast([w], 4, 0, 0, 10, 0, 1, OPT_TWO_SIDED))
        self.assertIsNone(ray_cast([w], 4, 0, 0, 10, 0, 1, OPT_TWO_SIDED | 2))       # option 2
        self.assertIsNone(ray_cast([Line(5, -5, 5, 5, type=33)], 0, 0, 0, 10, 0, 1, OPT_TWO_SIDED, 32))

    def test_one_sided(self):
        w = wall(5, -5, 5, normal=(1, 0))      # faces +x: moving along +x leaves it (passed), against it blocks
        self.assertIsNone(ray_cast([w], 0, 0, 0, 10, 0, 1))
        self.assertIsNotNone(ray_cast([w], 0, 10, 0, -10, 0, 1))
        self.assertIsNotNone(ray_cast([w], 0, 0, 0, 10, 0, 1, OPT_TWO_SIDED))

    def test_soft_from_below(self):
        f = floor(0, -10, 10, type_=2)
        self.assertIsNone(ray_cast([f], 0, 0, 5, 0, -10, 1 | 2, OPT_TWO_SIDED))     # side < 0
        self.assertIsNotNone(ray_cast([f], 0, 0, 5, 0, -10, 1 | 2, OPT_TWO_SIDED | OPT_SOFT_BOTH_SIDES))
        self.assertIsNotNone(ray_cast([f], 0, 0, -5, 0, 10, 1 | 2, OPT_TWO_SIDED))  # from above


class LineOfSightOnMap(unittest.TestCase):
    def test_soft_platform_does_not_block(self):
        ray = map_ray([floor(0, -50, 50, type_=2)], 1)
        self.assertFalse(line_of_sight_blocked(0, -20, 0, 20, 0, 0, ray))

    def test_hard_wall_blocks(self):
        ray = map_ray([wall(50, -1000, 1000)], 1)
        self.assertTrue(line_of_sight_blocked(0, 0, 100, 0, 0, 40, ray))

    def test_small_block_is_passed_by_detour(self):
        ray = map_ray([wall(50, -10, 10)], 1)
        self.assertFalse(line_of_sight_blocked(0, 0, 100, 0, 0, 0, ray))


if __name__ == "__main__":
    unittest.main()
