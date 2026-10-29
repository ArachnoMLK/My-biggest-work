"""Tests of the fighter state map (tools/bh/entity_states.py). Run: python -I -m unittest discover -s tests"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh.entity_states import STATES, handler, respawn_index  # noqa: E402


class States(unittest.TestCase):
    def test_table(self):
        self.assertEqual(sorted(STATES), [0, 2, 3, 4, 5, 6, 7, 8, 9])
        self.assertIsNone(handler(1))
        self.assertIsNone(handler(10))
        self.assertEqual(handler(9)[0], "respawning")


class Respawn(unittest.TestCase):
    def test_rotation(self):
        c = [5, 9]
        self.assertEqual(respawn_index(c, 0, 4, False), 2)          # 6 % 4
        self.assertEqual(respawn_index(c, 0, 4, False), 3)
        self.assertEqual(c, [7, 9])

    def test_team_halves(self):
        c = [0, 0]
        self.assertEqual(respawn_index(c, 1, 6, True), 1)           # 1 % 3
        self.assertEqual(respawn_index(c, 2, 6, True), 1 + 3)       # 1 % 3 + 3
        self.assertEqual(respawn_index(c, 2, 5, True), 0 + 3)       # 2 % 2 + ceil(2.5)


if __name__ == "__main__":
    unittest.main()
