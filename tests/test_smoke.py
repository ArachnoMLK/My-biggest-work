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

PLATFORM = ('<LevelDesc NumFrames="8"><MovingPlatform PlatID="1" X="0" Y="0"><Animation>'
            '<KeyFrame FrameNum="1" X="0" Y="0"/><KeyFrame FrameNum="5" X="20" Y="0"/></Animation></MovingPlatform>'
            '<DynamicCollision PlatID="1" X="0" Y="0"><HardCollision X1="-200" X2="200" Y="300"/>'
            '<HardCollision X1="200" X2="-200" Y="340"/><HardCollision X="-200" Y1="300" Y2="340"/>'
            '<HardCollision X="200" Y1="340" Y2="300"/></DynamicCollision>'
            '<Respawn X="0" Y="0" /></LevelDesc>')


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

    def test_stands_still_after_landing(self):
        grid = smoke.map_grid(FLAT)
        ticks, r = smoke.fall(grid, 0.0, 0.0)
        kept, drift, _ = smoke.stand(grid, r, ticks)
        self.assertEqual(kept, 60)
        self.assertLessEqual(drift, 1e-9)

    def test_soft_platform_from_above(self):
        ticks, r = smoke.fall(smoke.map_grid(SOFT), 0.0, 0.0)
        self.assertIsNotNone(r)
        self.assertAlmostEqual(r.y, 100.0 - 1.01)

    def test_no_ground(self):
        self.assertEqual(smoke.fall(smoke.map_grid(EMPTY), 0.0, 0.0, max_ticks=50), (50, None))

    def test_moving_platform(self):
        grid, movers = smoke.map_grid(PLATFORM, True)
        self.assertEqual(len(movers), 1)
        ticks, r = smoke.fall(grid, 0.0, 0.0, movers=movers)
        self.assertIsNotNone(r)
        self.assertAlmostEqual(r.y, 300.0 - 1.01)
        self.assertAlmostEqual(smoke.check_landing(r)[1], 0.0)
        self.assertIsNone(smoke.fall(smoke.map_grid(PLATFORM), 0.0, 0.0, max_ticks=200)[1])   # static only
        c = smoke.run([PLATFORM], with_platforms=True)
        self.assertEqual((c["contact"], c["within_1e-6"]), (1, 1))
        self.assertEqual((c["stand_moving"], c["stand_moving_same_height"], c["stand_60_on_ground"]), (1, 1, 1))

    def test_item_falls_and_rests(self):
        from bh import items
        xml = FLAT.replace('<Respawn X="0" Y="0" />', '<ItemSpawn X="-10" Y="0" W="20" H="10" /><ItemInitSpawn X="5" Y="2" />')
        self.assertEqual(smoke.item_spawns(xml), [(0.0, 5.0), (5.0, 2.0)])
        r = smoke.item_fall(smoke.map_grid(xml), 0.0, 5.0, items.ITEM_DEFAULTS)
        self.assertGreater(r["contact"], 1)
        self.assertAlmostEqual(r["err"], 0.0)
        self.assertGreater(r["bounces"], 0)                      # it lands faster than 5: it bounces first
        self.assertIsNotNone(r["settled"])
        self.assertTrue(r["still"])
        c = smoke.run_items([xml], items.ITEM_DEFAULTS)
        self.assertEqual((c["spawn_points"], c["contact"], c["on_line_1e-6"], c["settled"], c["still_60"]),
                         (2, 2, 2, 2, 2))

    def test_walk(self):
        grid = smoke.map_grid(FLAT)
        ticks, r = smoke.fall(grid, 0.0, 0.0)
        self.assertEqual(smoke.walk(grid, r, 6.0), ("walked", 0.0))
        block = ('<HardCollision X1="200" X2="260" Y="400" /><HardCollision X="260" Y1="400" Y2="500" />'
                 '<HardCollision X1="260" X2="200" Y="500" /><HardCollision X="200" Y1="500" Y2="400" />')
        walled = smoke.map_grid(FLAT.replace('<Respawn X="0"', block + '<Respawn X="0"'))
        ticks, r = smoke.fall(walled, 0.0, 0.0)
        self.assertEqual(smoke.walk(walled, r, 30.0)[0], "wall")         # a closed block standing on the floor at x = 200
        ledge = '<LevelDesc><HardCollision X1="-50" X2="50" Y="500" /><HardCollision X1="50" X2="-50" Y="600" />'                 '<HardCollision X="-50" Y1="500" Y2="600" /><HardCollision X="50" Y1="600" Y2="500" />'                 '<Respawn X="0" Y="0" /></LevelDesc>'
        c = smoke.run_walk([ledge])
        self.assertEqual((c["walks"], c["left"], c["height_kept_1e-6"]), (2, 2, 2))

    def test_run_counts(self):
        c = smoke.run([FLAT, EMPTY, MOVING], max_ticks=200)
        self.assertEqual((c["maps"], c["respawns"], c["contact"], c["within_1e-6"]), (3, 4, 2, 2))
        self.assertEqual((c["no_contact"], c["no_contact_dynamic_map"]), (2, 1))


if __name__ == "__main__":
    unittest.main()
