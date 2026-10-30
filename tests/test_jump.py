"""Tests of the ground and dash jumps (tools/bh/jump.py). Synthetic values only.
Run: python -I -m unittest discover -s tests"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh.jump import dash_window, ground_jump  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
