"""Tests of the falling smoke test (tools/bh/smoke.py) on synthetic maps.
Run: python -I -m unittest discover -s tests"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh import smoke  # noqa: E402

FLAT = ('<LevelDesc><HardCollision X1="-1000" X2="1000" Y="500" /><HardCollision X1="1000" X2="-1000" Y="900" />'
        '<HardCollision X="-1000" Y1="500" Y2="900" /><HardCollision X="1000" Y1="900" Y2="500" />'
        '<Respawn X="0" Y="0" /><Respawn ExpandedInit="true" X="20" Y="-300" /></LevelDesc>')
SOFT = '<LevelDesc><SoftCollision X1="-200" X2="200" Y="100" /><Respawn X="0" Y="0" /></LevelDesc>'
EMPTY = '<LevelDesc><Respawn X="0" Y="0" /></LevelDesc>'
MOVING = '<LevelDesc><MovingPlatform PlatID="1"><HardCollision X1="-9" X2="9" Y="9" /></MovingPlatform>' \
         '<Respawn X="0" Y="0" /></LevelDesc>'


class Fall(unittest.TestCase):
    def test_respawns(self):
        self.assertEqual(smoke.respawns(FLAT), [(0.0, 0.0), (20.0, -300.0)])

    def test_lands_on_flat_ground(self):
        ticks, r = smoke.fall(smoke.map_grid(FLAT), 0.0, 0.0)
        self.assertIsNotNone(r)
        self.assertGreater(ticks, 1)
        self.assertEqual(r.ground.sy, 500.0)
        self.assertAlmostEqual(r.y, 500.0 - 1.01)
        self.assertEqual(smoke.check_landing(r)[0], "flat")
        self.assertAlmostEqual(smoke.check_landing(r)[1], 0.0)

    def test_soft_platform_from_above(self):
        ticks, r = smoke.fall(smoke.map_grid(SOFT), 0.0, 0.0)
        self.assertIsNotNone(r)
        self.assertAlmostEqual(r.y, 100.0 - 1.01)

    def test_no_ground(self):
        self.assertEqual(smoke.fall(smoke.map_grid(EMPTY), 0.0, 0.0, max_ticks=50), (50, None))

    def test_run_counts(self):
        c = smoke.run([FLAT, EMPTY, MOVING], max_ticks=200)
        self.assertEqual((c["maps"], c["respawns"], c["contact"], c["within_1e-6"]), (3, 4, 2, 2))
        self.assertEqual((c["no_contact"], c["no_contact_dynamic_map"]), (2, 1))


if __name__ == "__main__":
    unittest.main()
