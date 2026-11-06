"""Tests of the KO bounds data (tools/bh/level_bounds.py). Synthetic values only.
Run: python -I -m unittest discover -s tests"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh import ko, level_bounds  # noqa: E402

TYPES = ('<LevelTypes><LevelType LevelName="A"><LevelID>1</LevelID><LeftKill>100</LeftKill><RightKill>100'
         '</RightKill><TopKill>100</TopKill><BottomKill>100</BottomKill><HardLeftKill>true</HardLeftKill>'
         '</LevelType><LevelType LevelName="B"><LevelID>2</LevelID></LevelType></LevelTypes>')
DESC = ('<LevelDesc><CameraBounds X="-500" Y="-300" W="1000" H="600" />'
        '<HardCollision X1="-100" X2="100" Y="0" /><HardCollision X1="100" X2="-100" Y="50" />'
        '<HardCollision X="-100" Y1="0" Y2="50" /><HardCollision X="100" Y1="50" Y2="0" />'
        '<Respawn X="0" Y="-100" /><Respawn X="300" Y="-100" /></LevelDesc>')


class Bounds(unittest.TestCase):
    def test_parse(self):
        k = level_bounds.level_kills(TYPES)
        self.assertEqual((k["A"]["LeftKill"], k["A"]["HardLeftKill"], k["A"]["SoftTopKill"]), (100, True, False))
        self.assertEqual(k["B"]["BottomKill"], 0)
        self.assertEqual(level_bounds.camera_bounds(DESC), (-500.0, -300.0, 500.0, 300.0))

    def test_run(self):
        c = level_bounds.run([("A", DESC)], level_bounds.level_kills(TYPES))
        self.assertEqual((c["respawns"], c["respawns_inside"]), (2, 2))
        self.assertEqual((c["falls_without_ground"], c["falls_to_bottom_ko"]), (1, 1))   # x = 300 has no floor

    def test_fall_to_ko(self):
        k = level_bounds.level_kills(TYPES)["A"]
        tick, mask = level_bounds.fall_to_ko([], 300.0, -100.0, (-500.0, -300.0, 500.0, 300.0), k)
        self.assertEqual(mask, ko.BOTTOM)
        self.assertGreater(tick, 1)


if __name__ == "__main__":
    unittest.main()
