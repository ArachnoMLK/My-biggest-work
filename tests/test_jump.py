"""Tests of the ground and dash jumps (tools/bh/jump.py). Synthetic values only.
Run: python -I -m unittest discover -s tests"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh.jump import air_jump, dash_window, ground_jump, ground_tail, wall_jump  # noqa: E402


class Jump(unittest.TestCase):
    def test_ground_jump(self):
        g = object()
        self.assertEqual(ground_jump(1000, 0, g, 0, 0.0), (-57.0, 0.0, None, False))
        self.assertAlmostEqual(ground_jump(1000, 0, g, 0, 0.0, second_arg=True)[0], -57.0 * 0.86)
        self.assertIsNone(ground_jump(1000, 0, None, 0, 0.0))                 # in the air: other branches
        self.assertEqual(ground_jump(1000, 0, None, 1, 0.0)[0], -57.0)          # _-Xb == 1 counts as grounded

    def test_dash_jump(self):
        g = object()
        self.assertTrue(dash_window(1000, 900, g, 0))
        self.assertFalse(dash_window(1060, 900, g, 0))                          # 900 + 160 > 1060 is false
        self.assertEqual(ground_jump(1000, 900, g, 0, 5.0), (5.0 - 170.0, 0.0, None, True))

    def test_ground_tail(self):
        self.assertEqual(ground_tail(True, True, 6.0, 0.0, 10.0), (2.0, 0.0))     # _-M3V: |vx| -= 4
        self.assertEqual(ground_tail(True, False, 6.0, 0.0, 10.0), (0, 0.0))      # moving against the held side
        self.assertEqual(ground_tail(True, False, -10.0, 1.0, 10.0), (-10.0, -14.0))  # at max: -= 30 x 0.5
        self.assertEqual(ground_tail(True, False, -5.0, 1.0, 10.0), (-5.0, 1.0))
        self.assertEqual(ground_tail(False, True, -6.0, 0.0, 10.0), (-2.0, 0.0))
        self.assertEqual(ground_tail(False, False, 12.0, 0.0, 10.0), (12.0, 15.0))

    def test_wall_jump(self):
        self.assertIsNone(wall_jump(0, 0, 0.0, 0.0, False, False))
        self.assertEqual(wall_jump(1, 0, 0.0, 0.0, False, True), (-53.0, 0.0, 0.0, 48.0, None, False))
        self.assertAlmostEqual(wall_jump(1, 0, 0.0, 0.0, True, True)[3], 48.0 * 0.9)
        self.assertEqual(wall_jump(2, 0, 0.0, 0.0, True, False)[3:], (-48.0, None, True))
        self.assertAlmostEqual(wall_jump(2, 0, 0.0, 0.0, False, True)[3], -48.0 * 0.9)
        self.assertAlmostEqual(wall_jump(0, 2, 0.0, 0.0, False, True, k=0.86)[0], -53.0 * 0.86)

    def test_air_jump(self):
        self.assertIsNone(air_jump(2, 2, 0.0, 0.0, False, False, 8.0))
        self.assertEqual(air_jump(0, 2, 1.0, 3.0, False, False, 8.0), (-56.0, 0.0, 3.0, 1))
        self.assertAlmostEqual(air_jump(1, 2, 0.0, 0.0, False, False, 8.0, k=0.86, second_arg=True)[0], -65.0 * 0.86)
        self.assertEqual(air_jump(0, 2, 0.0, 12.0, True, True, 8.0)[2], 8.0)     # held left: a rightward vx is capped at max
        self.assertEqual(air_jump(0, 2, 0.0, -12.0, True, True, 8.0)[2], -12.0)  # a leftward vx is kept
        self.assertEqual(air_jump(0, 2, 0.0, -12.0, False, True, 8.0)[2], -8.0)


if __name__ == "__main__":
    unittest.main()
