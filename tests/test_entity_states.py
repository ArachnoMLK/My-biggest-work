"""Tests of the fighter state map (tools/bh/entity_states.py). Run: python -I -m unittest discover -s tests"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh.entity_states import STATES, handler  # noqa: E402


class States(unittest.TestCase):
    def test_table(self):
        self.assertEqual(sorted(STATES), [0, 2, 3, 4, 5, 6, 7, 8, 9])
        self.assertIsNone(handler(1))
        self.assertIsNone(handler(10))
        self.assertEqual(handler(9)[0], "respawning")


if __name__ == "__main__":
    unittest.main()
