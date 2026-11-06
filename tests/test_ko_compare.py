"""Tests of the plan step 5 comparison (tools/bh/ko_compare.py). Synthetic values only.
Run: python -I -m unittest discover -s tests"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh import ko_compare  # noqa: E402


class KoCompareTest(unittest.TestCase):
    def test_pressed_before_is_strict(self):
        recs = [(0, 0), (160, 128), (176, 0)]
        self.assertTrue(ko_compare.pressed_before(recs, ko_compare.HIT_KEYS, 176))
        self.assertFalse(ko_compare.pressed_before(recs, ko_compare.HIT_KEYS, 160))
        self.assertFalse(ko_compare.pressed_before([(0, 4 | 8 | 16)], ko_compare.HIT_KEYS, 999))

    def test_hit_keys(self):
        self.assertEqual(ko_compare.HIT_KEYS, 128 | 64 | 512)
        self.assertTrue(ko_compare.UNMODELLED_KEYS & 256)

    def test_first_ko(self):
        self.assertIsNone(ko_compare.first_ko({"kos": []}))
        self.assertEqual(ko_compare.first_ko({"kos": [(2, 3200), (1, 1600)]}), (1, 1600))

    def test_classify(self):
        self.assertEqual(ko_compare.classify([], 1600), "none predicted")
        self.assertEqual(ko_compare.classify([1600, 9000], 1600), "exact")
        self.assertEqual(ko_compare.classify([1616], 1600), "off by one tick")
        self.assertEqual(ko_compare.classify([1584], 1600), "off by one tick")
        self.assertEqual(ko_compare.classify([800], 1600), "early")
        self.assertEqual(ko_compare.classify([3200], 1600), "late")

    def test_check_skips_other_versions_and_no_ko(self):
        c = ko_compare.check([{"version": 270}, {"version": 271, "kos": [], "entities": []}], swz=None)
        self.assertEqual(dict(c), {"skipped (no KO)": 1})

    def test_check_skips_when_opponent_attacked(self):
        rep = {"version": 271, "kos": [(1, 1600)], "entities": [{"id": 1}, {"id": 2}],
               "inputs": {2: [(0, 0), (800, 128)]}}
        self.assertEqual(dict(ko_compare.check([rep], swz=None)), {"skipped (opponent attacked first)": 1})


if __name__ == "__main__":
    unittest.main()
