"""Tests of tools/bh/pickup.py (`_-F5N._-N5R` item choice). Synthetic values only.
Run: python -I -m unittest discover -s tests"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh import pickup  # noqa: E402

CRATE = {"name": "WeaponCrate", "E2E": True, "G3X": True, "r5R": True, "w2s": 40.0, "S2O": 40.0}
BOMB = {"name": "Bomb", "w2s": 20.0, "S2O": 20.0}
SWORD = {"name": "Sword", "G3X": True, "r5R": False, "w2s": 10.0, "S2O": 10.0}
HERO = {"mBaseWeapon1": "Hammer", "mBaseWeapon2": "Sword"}


def item(t, x, y, **kw):
    return dict({"type": t, "x": x, "y": y, "state": 0}, **kw)


class Pickup(unittest.TestCase):
    def test_priorities(self):
        self.assertEqual([pickup.type_priority(t) for t in (CRATE, BOMB, {"name": "BouncyBomb"},
                                                              {"name": "XBrawlballY"})], [6, 8, 7, 1])

    def test_box_edges(self):
        self.assertTrue(pickup.in_box(item(CRATE, 170, 0), 0, 0))      # 170 - 20 = 150: edge counts
        self.assertFalse(pickup.in_box(item(CRATE, 170.5, 0), 0, 0))
        self.assertTrue(pickup.in_box(item(CRATE, 270, 0, state=3), 0, 0))

    def test_lowest_priority_then_nearest(self):
        items = [item(BOMB, 10, 0), item(CRATE, 100, 0), item(CRATE, 50, 0)]
        self.assertIs(pickup.choose(items, 0, 1, 0, 0, HERO), items[2])

    def test_thrown_first_unless_a3(self):
        items = [item(CRATE, 0, 0), item(BOMB, 100, 0, state=1)]
        self.assertIs(pickup.choose(items, 0, 1, 0, 0, HERO), items[1])
        self.assertIs(pickup.choose(items, 0, 1, 0, 0, HERO, a3=True), items[0])

    def test_weapon_rules(self):
        self.assertIsNotNone(pickup.choose([item(SWORD, 0, 0)], 0, 1, 0, 0, HERO))
        self.assertIsNone(pickup.choose([item(SWORD, 0, 0)], 0, 1, 0, 0, {"mBaseWeapon1": "Bow"}))
        self.assertIsNone(pickup.choose([item(CRATE, 0, 0, claimed_by=2)], 0, 1, 0, 0, HERO))
        self.assertIsNone(pickup.choose([item(CRATE, 0, 0, dropped_by=1, dropped_at=100)], 150, 1, 0, 0, HERO))
        self.assertIsNotNone(pickup.choose([item(CRATE, 0, 0, dropped_by=1, dropped_at=100)], 164, 1, 0, 0, HERO))

    def test_opponent_near_blocks_crates_without_a2(self):
        items = [item(CRATE, 0, 0)]
        self.assertIsNone(pickup.choose(items, 0, 1, 0, 0, HERO, a2=False, opponent_near=True))
        self.assertIsNotNone(pickup.choose(items, 0, 1, 0, 0, HERO, a2=True, opponent_near=True))

    def test_pickable(self):
        self.assertFalse(pickup.pickable(item(dict(BOMB, p5R=True), 0, 0), 0))
        self.assertFalse(pickup.pickable(item(BOMB, 0, 0, state=5), 0))
        self.assertTrue(pickup.pickable(item(BOMB, 0, 0, state=3, b37=10, e4u=5), 15))
        self.assertFalse(pickup.pickable(item(BOMB, 0, 0, state=3, b37=10, e4u=5), 14))


if __name__ == "__main__":
    unittest.main()
