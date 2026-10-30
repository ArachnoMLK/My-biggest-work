"""Tests of the 1v1 match start (tools/bh/match_start.py). Synthetic values only.
Run: python -I -m unittest discover -s tests"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh.match_start import one_v_one, r_at_match_start  # noqa: E402
from bh.prng import Well512, shuffle  # noqa: E402
from bh.respawn_points import parse_respawns  # noqa: E402

XML = ('<LevelDesc><Respawn X="300" Y="0" /><Respawn Initial="true" X="-200" Y="0" />'
       '<Respawn Initial="true" X="200" Y="0" /><Respawn ExpandedInit="true" X="-600" Y="0" />'
       '<Respawn X="0" Y="-50" /></LevelDesc>')


class MatchStart(unittest.TestCase):
    def test_four_draws_and_extreme_points(self):
        points = parse_respawns(XML)
        rng = Well512(12345)
        placed, g5x = one_v_one(rng, ["a", "b"], points)
        ref = Well512(12345)
        order = shuffle(ref, ["a", "b"])                                  # draws 1-2
        self.assertEqual([f for f, _ in placed], order)
        self.assertEqual([(p["x"], p["y"]) for _, p in placed], [(-200.0, 0.0), (200.0, 0.0)])   # Initial ends
        self.assertEqual(g5x, [ref.next_u32() % 4, ref.next_u32() % 4])  # draws 3-4, n = 4 points without ExpandedInit
        self.assertEqual(rng.getstate(), ref.getstate())

    def test_sort_mode_keeps_order_and_two_draws(self):
        rng, ref = Well512(7), Well512(7)
        placed, g5x = one_v_one(rng, ["a", "b"], parse_respawns(XML), sort_mode=True)
        self.assertEqual([f for f, _ in placed], ["a", "b"])
        self.assertEqual(g5x, [ref.next_u32() % 4, ref.next_u32() % 4])

    def test_too_few_candidates(self):
        placed, g5x = one_v_one(Well512(1), ["a", "b"], parse_respawns('<Respawn X="0" Y="0" />'))
        self.assertEqual([p for _, p in placed], [None, None])            # `_-N4x()`
        self.assertTrue(all(0 <= v < 1 for v in g5x))

    def test_r_at_match_start(self):
        rng, c56 = r_at_match_start(-5, 2)                                  # header seed read as i32
        ref = Well512(4294967291)
        self.assertEqual(c56, [ref.next_u32() % 2, ref.next_u32() % 2])
        self.assertEqual(rng.getstate(), ref.getstate())


if __name__ == "__main__":
    unittest.main()
