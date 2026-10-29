"""Tests of the input buffer transcription (tools/bh/input_buffer.py). See docs/input-buffer-11.00.md.

Run: python -I -m unittest discover -s tests   (from the repository root)
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh.input_buffer import buffered_presses, state_at  # noqa: E402

JUMP, LIGHT, HEAVY = 16, 128, 64


class StateAt(unittest.TestCase):
    def test_step_function(self):
        rec = [(100, 1), (200, 2)]
        self.assertEqual(state_at(rec, 50), 0)
        self.assertEqual(state_at(rec, 100), 1)
        self.assertEqual(state_at(rec, 199), 1)
        self.assertEqual(state_at(rec, 500), 2)


class Buffer(unittest.TestCase):
    def test_nothing_before_n_ticks(self):
        self.assertIsNone(buffered_presses([], 64))           # 64 < 5 * 16
        self.assertEqual(buffered_presses([], 80), {})

    def test_press_on_current_tick(self):
        self.assertEqual(buffered_presses([(1600, JUMP)], 1600), {"Jump": 1600})

    def test_press_is_buffered_for_four_ticks(self):
        rec = [(1600, JUMP)]
        self.assertEqual(buffered_presses(rec, 1600 + 3 * 16), {"Jump": 1600})   # i = 3 = n - 2
        self.assertEqual(buffered_presses(rec, 1600 + 4 * 16), {})               # i = 4 is only the "before" tick

    def test_held_key_is_not_a_new_press(self):
        rec = [(1000, JUMP)]
        self.assertEqual(buffered_presses(rec, 1600), {})

    def test_oldest_press_wins(self):
        rec = [(1568, JUMP), (1584, 0), (1600, JUMP)]
        self.assertEqual(buffered_presses(rec, 1600), {"Jump": 1568})

    def test_skip_current(self):
        rec = [(1600, LIGHT | HEAVY)]
        self.assertEqual(buffered_presses(rec, 1600, skip_current=True), {})
        self.assertEqual(buffered_presses(rec, 1616, skip_current=True), {"LightAttack": 1600, "HeavyAttack": 1600})

    def test_longer_window(self):
        rec = [(1600, JUMP)]
        self.assertEqual(buffered_presses(rec, 1600 + 7 * 16, n=9), {"Jump": 1600})


if __name__ == "__main__":
    unittest.main()
