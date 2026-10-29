"""Tests of the power step timeline (tools/bh/power_timeline.py). See docs/hit-detection-11.00.md, section 1.

Run: python -I -m unittest discover -s tests   (from the repository root)
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh.power_timeline import Timeline, schedule, tick_index  # noqa: E402


class Timing(unittest.TestCase):
    def test_tick_index(self):
        self.assertEqual(tick_index(0), 0)
        self.assertEqual(tick_index(31), 1)
        self.assertEqual(tick_index(32), 2)

    def test_steps(self):
        # CastTime 2, 3, 0, 4: step 0 at start + 2, step 1 three ticks later, step 2 one tick later (0 -> 1)
        self.assertEqual(schedule([2, 3, 0, 4], 10, 20), [(12, 0), (15, 1), (16, 2), (20, 3)])

    def test_last_step_stays(self):
        tl = Timeline([1], 0)
        self.assertEqual(tl.update(0), None)
        self.assertEqual(tl.update(1), 0)
        self.assertTrue(tl.done)
        self.assertEqual(tl.update(2), None)

    def test_cap(self):
        tl = Timeline([1, 1, 1], 0, cap=1)
        fired = [tl.update(k) for k in range(5)]
        self.assertEqual([f for f in fired if f is not None], [0, 1])


if __name__ == "__main__":
    unittest.main()
