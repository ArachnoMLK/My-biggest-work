"""Tests of the respawn point lists (tools/bh/respawn_points.py) on synthetic LevelDescs. Synthetic values only.
Run: python -I -m unittest discover -s tests"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh.respawn_points import candidates, compare, lists, parse_respawns  # noqa: E402

XML = ('<LevelDesc><Respawn X="30" Y="5" /><Respawn Initial="true" X="-10" Y="0" />'
       '<Respawn ExpandedInit="TRUE" X="0" Y="0" /><Respawn Initial="True" X="30" Y="-5" />'
       '<Respawn Initial="yes" X="50" Y="0" /></LevelDesc>')


def xs(points):
    return [(p["x"], p["y"]) for p in points]


class RespawnPoints(unittest.TestCase):
    def test_parse(self):
        p = parse_respawns(XML, dx=1.0, dy=2.0)
        self.assertEqual(xs(p)[0], (31.0, 7.0))
        self.assertEqual([q["initial"] for q in p], [False, True, False, True, False])   # "yes" is not TRUE
        self.assertEqual([q["expanded"] for q in p], [False, False, True, False, False])

    def test_lists_sorted_by_x_then_y(self):
        all_points, normal, initial = lists(parse_respawns(XML))
        self.assertEqual(xs(all_points), [(-10, 0), (0, 0), (30, -5), (30, 5), (50, 0)])
        self.assertEqual(xs(normal), [(-10, 0), (30, -5), (30, 5), (50, 0)])          # no ExpandedInit
        self.assertEqual(xs(initial), [(-10, 0), (30, -5)])

    def test_static_before_platform(self):
        a = {"x": 0, "y": 0, "platform": None}
        b = {"x": 0, "y": 0, "platform": 3}
        c = {"x": 0, "y": 0, "platform": 4}
        self.assertEqual((compare(a, b), compare(b, a), compare(b, c), compare(a, dict(a))), (-1, 1, -1, 0))

    def test_candidates(self):
        p = parse_respawns(XML)
        self.assertEqual(len(candidates(p, 2, True)), 2)       # the Initial list is long enough
        self.assertEqual(len(candidates(p, 3, True)), 4)       # too short: the normal list
        self.assertEqual(len(candidates(p, 2, False)), 4)      # not spawned: the normal list
        self.assertEqual(len(candidates(p, 5, True)), 5)       # normal list too short: every point
        self.assertEqual(len(candidates(p, 5, True, f3o=True)), 4)


if __name__ == "__main__":
    unittest.main()
