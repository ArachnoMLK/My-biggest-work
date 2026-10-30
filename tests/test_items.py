"""Tests of the thrown item motion (tools/bh/items.py). Synthetic values only.
Run: python -I -m unittest discover -s tests"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh.items import ITEM_DEFAULTS, expired, item_type, sweep_mask, velocity  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
