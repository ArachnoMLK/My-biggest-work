"""Tests of the horizontal movement (tools/bh/horizontal.py). Synthetic values only.
Run: python -I -m unittest discover -s tests"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh.horizontal import (acceleration, apply_acceleration, apply_friction, friction_value,  # noqa: E402
                           max_speed, reversal_factor)


class Horizontal(unittest.TestCase):
    def test_max_speed(self):
        self.assertEqual(max_speed(10.0, 8.0, False), 10.0)
        self.assertEqual(max_speed(10.0, 8.0, True), 8.0)
        self.assertAlmostEqual(max_speed(10.0, 8.0, False, w47=True), 11.6)

    def test_friction_choice(self):
        self.assertEqual(friction_value(1000, False, 2.0, 0.5), 2.0)
        self.assertEqual(friction_value(1000, True, 2.0, 0.5), 0.5)
        self.assertEqual(friction_value(1000, False, 2.0, 0.5, dash_timer=400), 5.655)    # 400 + 640 >= 1000
        self.assertEqual(friction_value(1100, True, 2.0, 0.5, dash_timer=400), 0.5)       # window over
        self.assertEqual(friction_value(1000, False, 2.0, 0.5, power={"7E": True}), 4.013)
        self.assertEqual(friction_value(1000, True, 2.0, 0.5, power={"y25": True}), 2.0)
        self.assertEqual(friction_value(1000, False, 2.0, 0.5, hitstun=True, surface=4), 4.0)
        self.assertEqual(friction_value(1000, False, 2.0, 0.5, surface=4, vx=3.0), 9.0)
        self.assertEqual(friction_value(1000, False, 2.0, 0.5, surface=4, vx=-3.0), 3.25)

    def test_friction_application(self):
        self.assertAlmostEqual(apply_friction(10.0, 2.0), 10.0 - 0.768)
        self.assertAlmostEqual(apply_friction(-10.0, 2.0), -10.0 + 0.768)
        self.assertEqual(apply_friction(0.5, 2.0), 0.0)

    def test_acceleration(self):
        self.assertEqual(acceleration(False, 3.0, 2.0, vmax=10.0), (3.0, 10.0))
        self.assertEqual(acceleration(True, 3.0, 2.0, mode_boost=True, vmax=10.0), (2.5, 12.5))
        self.assertAlmostEqual(reversal_factor(-25.0), 0.5)
        self.assertEqual(reversal_factor(80.0), 0.0)
        self.assertAlmostEqual(apply_acceleration(0.0, False, 10.0, 20.0), 3.84)
        self.assertEqual(apply_acceleration(19.0, False, 10.0, 20.0), 20.0)       # clamped at the max
        self.assertEqual(apply_acceleration(30.0, False, 10.0, 20.0), 30.0)       # above the max: untouched
        self.assertAlmostEqual(apply_acceleration(0.0, True, 10.0, 20.0), -3.84)


if __name__ == "__main__":
    unittest.main()
