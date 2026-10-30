"""Tests of the input buffer transcription (tools/bh/input_buffer.py). See docs/input-buffer-11.00.md.

Run: python -I -m unittest discover -s tests   (from the repository root)
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh.input_buffer import (attack_slot, buffered_presses, chain_allowed, first_jump_allowed,  # noqa: E402
                             state_at)

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


class Guards(unittest.TestCase):
    def test_attack_slots(self):
        # ground light: down, neutral, side; air light; ground heavy; air heavy
        self.assertEqual([attack_slot(k) for k in (2, 0, 4)], [3, 1, 2])
        self.assertEqual([attack_slot(k, air=True) for k in (2, 0, 8)], [6, 4, 5])
        self.assertEqual([attack_slot(k, heavy=True) for k in (2, 0, 4)], [8, 11, 7])
        self.assertEqual([attack_slot(k, heavy=True, air=True) for k in (2, 0, 4)], [10, 9, 9])

    def test_attack_direction_priority(self):
        self.assertEqual(attack_slot(2 | 4), attack_slot(2))           # Drop beats side
        self.assertEqual(attack_slot(4 | 32), attack_slot(0))          # bit 32 beats side
        self.assertEqual(attack_slot(1 | 4), attack_slot(4))           # bit 1 alone does not
        self.assertEqual(attack_slot(1), attack_slot(0))

    def test_first_jump_lock(self):
        self.assertTrue(first_jump_allowed(1600, 0))
        self.assertFalse(first_jump_allowed(1600 + 192, 1600))
        self.assertTrue(first_jump_allowed(1600 + 208, 1600))

    def test_chain_needs_300_ms(self):
        self.assertFalse(chain_allowed(1600 + 288, 1600))
        self.assertTrue(chain_allowed(1600 + 304, 1600))
        self.assertTrue(chain_allowed(1600, 1616))                      # unsigned wrap


if __name__ == "__main__":
    unittest.main()
