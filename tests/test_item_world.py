"""Tests of tools/bh/item_world.py (harness glue for item spawns and pick-ups). Synthetic values only.
Run: python -I -m unittest discover -s tests"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh import item_world  # noqa: E402
from bh.item_spawns import RATE_DEFAULTS  # noqa: E402
from bh.smoke import map_grid  # noqa: E402

CSV = ("itemTypes\n"
       "ItemName,ItemID,Weapon,WeaponCrate,TestFeature,RemoveDuringSuddenDeath,Height,Width,Spawnable\n"
       "Crate,3,TRUE,TRUE,FALSE,FALSE,40,40,TRUE\n"
       "Bomb,4,FALSE,FALSE,FALSE,FALSE,20,20,TRUE\n")
LEVEL = '<L><ItemInitSpawn X="0" Y="-200"/><ItemSpawn X="-50" Y="-300" W="100"/></L>'
FLOOR = ('<L><HardCollision X1="-500" Y1="0" X2="500" Y2="0"/><HardCollision X1="500" Y1="0" X2="500" Y2="100"/>'
         '<HardCollision X1="500" Y1="100" X2="-500" Y2="100"/><HardCollision X1="-500" Y1="100" X2="-500" Y2="0"/></L>')


class ItemWorld(unittest.TestCase):
    def world(self, c56=(0, 1)):
        types = item_world.item_types(CSV)
        rate = dict(RATE_DEFAULTS, f41=1, name="R", **{"41r": 100, "93K": 1})   # at most one item
        rules = {2: {"weapons": ["Crate"], "gadgets": [], "init_63N": True}}
        settings = {"item_spawn_ruleset_id": 2, "weapon_spawn_rate_id": 1, "gadget_spawn_rate_id": 0}
        grid = map_grid(FLOOR)
        return item_world.World(5, settings, {"R": rate}, rules, types, LEVEL, grid, 2, c56)

    def test_types(self):
        t = item_world.item_types(CSV)
        self.assertEqual((t["Crate"]["id"], t["Crate"]["E2E"], t["Crate"]["G3X"]), (3, True, True))
        self.assertFalse(t["Bomb"]["G3X"])

    def test_first_drop_falls_and_picks(self):
        w = self.world()
        w.tick(112, 16, [None, None])           # 16 + 100 > 112: gate closed
        self.assertEqual(w.live, [])
        w.tick(116, 16, [None, None])
        self.assertEqual(len(w.live), 1)        # the ItemInitSpawn rect, at its centre
        for k in range(200):
            w.tick(132 + 16 * k, 16, [None, None])
        self.assertLessEqual(abs(w.live[0]["y"]), 1.5)   # rests on the floor (y = 0, 1.01 back-off)
        self.assertIsNone(w.pick_up(0, 1, 300, 0, {}))
        self.assertEqual(w.pick_up(0, 1, 40, -10, {})["name"], "Crate")
        self.assertEqual(w.live, [])

    def test_crate_weapon_parity(self):
        w = self.world(c56=(0, 1))
        hero = {"mBaseWeapon1": "A", "mBaseWeapon2": "B"}
        self.assertEqual([w.crate_weapon(0, hero), w.crate_weapon(0, hero), w.crate_weapon(1, hero)], ["A", "B", "B"])


if __name__ == "__main__":
    unittest.main()
