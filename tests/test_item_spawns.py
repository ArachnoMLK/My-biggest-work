"""Tests of tools/bh/item_spawns.py (ItemManager `_-E1V` spawns). Synthetic values only.
Run: python -I -m unittest discover -s tests"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh import item_spawns as s  # noqa: E402
from bh.prng import Well512  # noqa: E402

RATE = dict(s.RATE_DEFAULTS, f41=5, T2X=1000, E3k=3000, j5F=200, n1a=500, **{"41r": 2000})


class FakeRng:
    def __init__(self, values):
        self.values = list(values)

    def next_u32(self):
        return self.values.pop(0)


class ItemSpawns(unittest.TestCase):
    def test_parse_rates_inherit(self):
        xml = ('<R><ItemSpawnRateType SpawnRateName="A" InheritSpawnRate=""><SpawnRateID>1</SpawnRateID>'
               '<FixedTimeBetweenSpawns>7</FixedTimeBetweenSpawns><RoundUpMaxItemMultiplier>true'
               '</RoundUpMaxItemMultiplier></ItemSpawnRateType>'
               '<ItemSpawnRateType SpawnRateName="B" InheritSpawnRate="A"><SpawnRateID>2</SpawnRateID>'
               '<MaxItemCountMultiplier>0.5</MaxItemCountMultiplier></ItemSpawnRateType></R>')
        r = s.parse_rates(xml)
        self.assertEqual((r["B"]["T2X"], r["B"]["rL"], r["B"]["dD"], r["B"]["f41"]), (7, True, 0.5, 2))

    def test_parse_rule_sets(self):
        xml = ('<R><ItemSpawnRuleSetType RuleSetName="Template"><RuleSetID>0</RuleSetID></ItemSpawnRuleSetType>'
               '<ItemSpawnRuleSetType RuleSetName="X"><RuleSetID>3</RuleSetID><WeaponList>a,b</WeaponList>'
               '<Use1v1AndTeamInitialWeaponSpawns>true</Use1v1AndTeamInitialWeaponSpawns>'
               '</ItemSpawnRuleSetType></R>')
        r = s.parse_rule_sets(xml)
        self.assertEqual(list(r), [3])
        self.assertEqual((r[3]["weapons"], r[3]["init_63N"]), (["a", "b"], True))

    def test_level_lists_and_defaults(self):
        xml = ('<L><ItemSpawn X="1" Y="2" W="30"/><ItemInitSpawn X="5" Y="6"/><ItemSet X="0" Y="0"/>'
               '<TeamItemInitSpawn X="1" Y="1" W="9" H="9"/></L>')
        l = s.parse_level_spawns(xml)
        self.assertEqual(l["X69"][0]["h"], 10)
        self.assertEqual((l["i4e"][0]["w"], l["i4e"][0]["h"]), (50, 50))
        self.assertEqual(l["v3h"][0]["w"], 40)
        self.assertEqual(l["03f"][0]["w"], 9)

    def test_max_items(self):
        self.assertEqual(s.max_items(None, 2), 0)
        self.assertEqual(s.max_items(dict(RATE), 2), 100)
        self.assertEqual(s.max_items(dict(RATE, dD=0.75, **{"93K": 1}), 2), 2)
        self.assertEqual(s.max_items(dict(RATE, dD=0.75, rL=True, **{"93K": 1}), 2), 3)
        self.assertEqual(s.max_items(dict(RATE, **{"93K": 500}), 2), 100)

    def test_lane_due(self):
        # interval = 1000 + floor(1 * 3000 / 3) + (rand % 401) - 200; rand 200 -> 2000
        self.assertFalse(s.lane_due(3000, 0, RATE, 1000, 200, 3))
        self.assertTrue(s.lane_due(3001, 0, RATE, 1000, 200, 3))
        # count + 1 == max adds ExtraTimeBeforeMax: 1000 + 500 + 3000 + 0 - 200
        self.assertFalse(s.lane_due(5300, 2, RATE, 1000, 0, 3))
        self.assertTrue(s.lane_due(5301, 2, RATE, 1000, 0, 3))

    def test_gate(self):
        self.assertFalse(s.gate(5000, None, True, 16))
        self.assertFalse(s.gate(5000, RATE, True, 0))
        self.assertFalse(s.gate(2015, RATE, True, 16))
        self.assertTrue(s.gate(2016, RATE, True, 16))
        self.assertFalse(s.gate(5000, RATE, True, 16, w35=0x1000000))
        self.assertFalse(s.gate(5000, RATE, False, 16))

    def test_spawn_pos(self):
        sp = {"x": 10, "y": 20, "w": 100, "h": 10}
        x, y = s.spawn_pos(sp, (65535 << 16) | 0)
        self.assertEqual((x, y), (10, 30))

    def test_shuffle_sides(self):
        rng = Well512(7)
        sp = [{"x": float(i * 10), "w": 5.0} for i in range(6)]
        s.shuffle_spawns(rng, sp, True)
        self.assertEqual(sp[0]["x"], 0.0)
        self.assertEqual(sp[1]["x"], 50.0)

    def test_pick_single_type_no_draw(self):
        c = s.Counts()
        it = s.pick_type(FakeRng([]), [{"id": 4}], c, [])
        self.assertEqual(it["id"], 4)
        self.assertEqual(c.get(4), 2)

    def test_pick_weights(self):
        types = [{"id": 1}, {"id": 2}]
        c = s.Counts()
        c.set(1, 3)
        # counts 3 / 1, total 4, weights 1 / 3, r = draw % 4
        self.assertEqual(s.pick_type(FakeRng([0]), types, c, [])["id"], 1)
        c2 = s.Counts()
        c2.set(1, 3)
        self.assertEqual(s.pick_type(FakeRng([1]), types, c2, [])["id"], 2)
        self.assertEqual(c2.get(2), 2)

    def test_pick_sudden_death(self):
        self.assertIsNone(s.pick_type(FakeRng([]), [{"id": 1, "B24": True}], s.Counts(), [], True))

    def test_manager_first_spawn_init_points(self):
        level = {"X69": [{"x": 0, "y": 0, "w": 10, "h": 10, "j2X": 0}], "i4e": [
            {"x": 0, "y": 0, "w": 50, "h": 50}, {"x": 100, "y": 0, "w": 50, "h": 50}], "03f": [], "v3h": []}
        m = s.ItemManager(FakeRng([11, 22, 33]), level, 2)
        m.seed_lanes({"init_63N": True}, RATE, None, [{"id": 9}], [])
        self.assertEqual((m.a.rand, m.b.rand), (11, 22))
        m.tick(2016, 16, 0, 0)
        self.assertEqual([(i["x"], i["y"]) for i in m.spawned], [(25.0, 25.0), (125.0, 25.0)])
        self.assertEqual(m.a.base, 2016)
        self.assertEqual(m.a.rand, 11)     # no redraw on the first drop
        # next one due after 1000 + floor(3 x 3000 / 100) + (11 % 401) - 200 = 901 (max 100); count 2
        m.tick(2917, 16, 2, 0)
        self.assertEqual(len(m.spawned), 2)
        m.rng.values = [0, 0, 44]           # shuffle of 1 rect (1 draw), position draw, lane redraw
        m.tick(2918, 16, 2, 0)
        self.assertEqual(len(m.spawned), 3)
        self.assertEqual((m.cursor, m.a.rand, m.a.base), (1, 44, 2918))

if __name__ == "__main__":
    unittest.main()
