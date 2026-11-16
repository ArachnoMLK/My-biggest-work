"""Tests of the KO oracle (tools/bh/oracle.py). See docs/oracle-ko.md.

Run: python -I -m unittest discover -s tests   (from the repository root)
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh.oracle import compare, ko_ticks  # noqa: E402


class KoTicks(unittest.TestCase):
    def test_sorted_oldest_first_in_ticks(self):
        rep = {"kos": [(2, 4800), (1, 1600)]}  # stored newest-first, as in the corpus
        self.assertEqual(ko_ticks(rep), [(100, 1), (300, 2)])

    def test_no_kos(self):
        self.assertEqual(ko_ticks({}), [])
        self.assertEqual(ko_ticks({"kos": []}), [])

    def test_non_tick_time_is_rejected(self):
        with self.assertRaises(ValueError):
            ko_ticks({"kos": [(1, 1601)]})


class Compare(unittest.TestCase):
    def test_match(self):
        self.assertEqual(compare([(300, 2), (100, 1)], [(100, 1), (300, 2)]), [])

    def test_wrong_tick_is_one_missing_one_unexpected(self):
        self.assertEqual(compare([(101, 1)], [(100, 1)]),
                         ["missing    tick 100 victim 1", "unexpected tick 101 victim 1"])

    def test_repeated_kos_count(self):
        self.assertEqual(compare([(100, 1)], [(100, 1), (100, 1)]), ["missing    tick 100 victim 1"])


if __name__ == "__main__":
    unittest.main()
