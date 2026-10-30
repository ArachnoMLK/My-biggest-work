"""Tests of the per-tick harness (tools/bh/harness.py) on a synthetic map. Synthetic values only.
Run: python -I -m unittest discover -s tests"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh import harness, smoke  # noqa: E402

FLAT = ('<LevelDesc><HardCollision X1="-1000" X2="1000" Y="500" /><HardCollision X1="1000" X2="-1000" Y="900" />'
        '<HardCollision X="-1000" Y1="500" Y2="900" /><HardCollision X="1000" Y1="900" Y2="500" />'
        '<Respawn X="0" Y="0" /></LevelDesc>')


def landed(inputs, ticks=200):
    f = harness.Fighter(0.0, 0.0)
    tr = harness.run(f, smoke.map_grid(FLAT), inputs, ticks)
    return f, tr


class Harness(unittest.TestCase):
    def test_falls_and_stands(self):
        f, tr = landed(lambda i: (False, False, False), 100)
        self.assertIsNotNone(f.ground)
        self.assertAlmostEqual(f.y, 500.0 - 1.01)
        self.assertEqual(f.events[0][1][0], "land")

    def test_ground_jump_after_the_squat(self):
        f, tr = landed(lambda i: (False, False, i == 80))
        kinds = [e for _, e in f.events]
        self.assertEqual(kinds[1:3], [("press", "squat"), ("release", "ground")])
        self.assertEqual(f.events[2][0] - f.events[1][0], 32)          # 2 ticks of squat
        self.assertFalse(tr[80][3])                                     # tick 81: still on the ground
        self.assertTrue(tr[81][3])                                      # tick 82: airborne
        self.assertAlmostEqual(tr[80][2] - tr[81][2], (57.0 - 3.75 * 0.384) * 0.384)
        self.assertEqual(kinds[-1][0], "land")
        self.assertAlmostEqual(f.y, 500.0 - 1.01)

    def test_air_jumps_counted(self):
        presses = {80, 100, 110, 120}
        f, tr = landed(lambda i: (False, False, i in presses), 300)
        kinds = [e[1] for _, e in f.events if e[0] in ("press", "release")]
        self.assertEqual(kinds, ["squat", "ground", "squat", "air", "squat", "air", "squat", None])
        self.assertEqual(f.air_used, 0)                                 # reset on landing [H]

    def test_walk_right(self):
        f, tr = landed(lambda i: (False, i > 60, False), 120)
        self.assertGreater(f.x, 0.0)
        self.assertIsNotNone(f.ground)
        self.assertAlmostEqual(f.v1d, harness.DEFAULT_STATS["RunSpeed"])   # held at the max

    def test_walk_off_a_ledge_to_a_bottom_ko(self):
        ledge = ('<LevelDesc><HardCollision X1="-50" X2="50" Y="500" /><HardCollision X1="50" X2="-50" Y="600" />'
                 '<HardCollision X="-50" Y1="500" Y2="600" /><HardCollision X="50" Y1="600" Y2="500" />'
                 '<Respawn X="0" Y="0" /></LevelDesc>')
        cam = (-400.0, -400.0, 400.0, 600.0)
        kill = {"LeftKill": 100, "RightKill": 100, "TopKill": 100, "BottomKill": 100,
                "HardLeftKill": False, "HardRightKill": False, "SoftTopKill": False}
        f = harness.Fighter(0.0, 0.0)
        tr = harness.run(f, smoke.map_grid(ledge), lambda i: (False, i > 60, False), 600,
                         bounds=(cam, kill), stop_on_ko=True)
        kos = [e for _, e in f.events if e[0] == "ko"]
        self.assertEqual(len(kos), 1)
        self.assertEqual(f.a3d, kos[0][1])
        self.assertGreater(f.y, 700.0)                                  # past bottom + BottomKill
        self.assertGreater(f.x, 50.0)                                   # off the right edge

    def test_wall_contact_and_wall_jump(self):
        block = ('<HardCollision X1="200" X2="260" Y="-300" /><HardCollision X="260" Y1="-300" Y2="500" />'
                 '<HardCollision X1="260" X2="200" Y="500" /><HardCollision X="200" Y1="500" Y2="-300" />')
        grid = smoke.map_grid(FLAT.replace('<Respawn X="0"', block + '<Respawn X="0"'))
        f = harness.Fighter(0.0, 0.0)
        tr = harness.run(f, grid, lambda i: (False, 60 < i < 150, i in (70, 85, 150)), 160)
        kinds = [e for _, e in f.events if e[0] != "wall"]
        self.assertEqual(kinds[-2:], [("press", "squat"), ("release", "wall")])
        self.assertIn(("wall", 2), [e for _, e in f.events])            # the wall is right of the feet
        i = [t for t, _, _, _ in tr].index(f.events[-1][0])
        self.assertLess(tr[i][1], tr[i - 1][1])                         # pushed away from the wall
        self.assertLess(tr[i][2], tr[i - 1][2])                         # and up
        self.assertIsNone(f.ground)                                     # a wall never stays in _-96f


if __name__ == "__main__":
    unittest.main()
