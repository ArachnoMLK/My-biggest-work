"""Tests of the replay setup for the harness (tools/bh/replay_setup.py) on a synthetic swz folder. Synthetic
values only. Run: python -I -m unittest discover -s tests"""
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh import replay_setup  # noqa: E402

FILES = {
    "Game.swz/HeroTypes.xml": ('<HeroTypes><HeroType HeroName="Template"><HeroID>0</HeroID></HeroType>'
                               '<HeroType HeroName="Alpha"><HeroID>7</HeroID></HeroType></HeroTypes>'),
    "Game.swz/RuneTypes.xml": ('<RuneTypes><RuneType RuneName="a0"><HeroName>Alpha</HeroName><RuneIndex>0</RuneIndex>'
                               '<Strength>1</Strength><Dexterity>1</Dexterity><Weight>1</Weight><Speed>2</Speed>'
                               '</RuneType></RuneTypes>'),
    "Game.swz/StatTypes.xml": ('<StatTypes><StatType StatName="Speed2"><RunSpeed>8.5</RunSpeed>'
                               '<Friction>2.0</Friction></StatType></StatTypes>'),
    "Game.swz/ScoringTypes.xml": '<ScoringTypes><ScoringType><ScoringID>2</ScoringID></ScoringType></ScoringTypes>',
    "Init.swz/LevelTypes.xml": ('<LevelTypes><LevelType LevelName="Flat"><LevelID>5</LevelID><LeftKill>200</LeftKill>'
                                '<RightKill>200</RightKill><TopKill>200</TopKill><BottomKill>200</BottomKill>'
                                '</LevelType></LevelTypes>'),
    "Dynamic.swz/LevelDesc_Flat.xml": (
        '<LevelDesc><CameraBounds X="-1000" Y="-600" W="2000" H="1500" />'
        '<HardCollision X1="-300" X2="300" Y="500" /><HardCollision X1="300" X2="-300" Y="600" />'
        '<HardCollision X="-300" Y1="500" Y2="600" /><HardCollision X="300" Y1="600" Y2="500" />'
        '<Respawn Initial="true" X="-200" Y="400" /><Respawn Initial="true" X="200" Y="400" /></LevelDesc>'),
}


def entity(eid, hero=7, stance=0):
    return {"id": eid, "heroes": [{"hero_id": hero, "stance": stance}]}


class ReplaySetup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        for rel, text in FILES.items():
            path = os.path.join(cls.tmp.name, *rel.split("/"))
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
        cls.swz = replay_setup.Swz(cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def rep(self, inputs=None, entities=None):
        return {"entities": entities or [entity(3), entity(1)], "level_id": 5, "random_seed": 99,
                "settings": {"scoring_type_id": 2}, "inputs": inputs or {}}

    def test_lookups(self):
        self.assertEqual(self.swz.names, {0: "Template", 7: "Alpha"})
        st = replay_setup.harness_stats(entity(1), self.swz.names, self.swz.stances, self.swz.stat_types)
        self.assertEqual((st["RunSpeed"], st["Friction"], st["AirFriction"]), (8.5, 2.0, 1.2))   # 1.2: default
        self.assertIsNone(replay_setup.harness_stats(entity(1, stance=3), self.swz.names, self.swz.stances,
                                                     self.swz.stat_types))

    def test_standing_fighters_never_ring_out(self):
        out = replay_setup.run(self.rep(), self.swz, ticks=400)
        self.assertEqual(list(out), [1, 3])
        self.assertEqual([(r["let_go"], r["kos"]) for r in out.values()], [([6000], []), ([6000], [])])

    def test_walking_off_the_ledge_rings_out_and_respawns(self):
        walk = [(0, 8)]   # MoveRight held from the start
        out = replay_setup.run(dict(self.rep({1: walk, 3: walk}), settings={"scoring_type_id": 2,
                                                                          "starting_lives": 3}), self.swz, ticks=2000)
        for r in out.values():
            self.assertTrue(r["kos"] and r["kos"][0] > 6000, r)
            self.assertGreaterEqual(len(r["let_go"]), 2, r)
            self.assertGreaterEqual(r["let_go"][1] - r["kos"][0], 4700)

    def test_skips(self):
        with self.assertRaises(ValueError):
            replay_setup.setup(self.rep(entities=[entity(1)]), self.swz)
        with self.assertRaises(ValueError):
            replay_setup.setup(dict(self.rep(), level_id=6), self.swz)
        with self.assertRaises(ValueError):
            replay_setup.setup(self.rep(entities=[entity(1), entity(2, stance=4)]), self.swz)


if __name__ == "__main__":
    unittest.main()
