"""Tests of the respawn drone (tools/bh/spawn_bot.py). Synthetic values only.
Run: python -I -m unittest discover -s tests"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh.spawn_bot import (CARRY, COME_DOWN, DROP, IDLE, F_MODE, F_SPAWNED, F_TIMED, Drone,  # noqa: E402
                          carry_ms, come_down_ms, drop_anim_scale, drop_ms, timing_flags)

RULES = {"F3O": False, "Ac": False, "K2V": True, "o2N": 100, "j57": 200, "C18": 50,
         "timed_until": None, "n4k": 0}


def fighter():
    return {"x": 5.0, "y": 5.0, "state": 3, "vy": 0.0, "spawned": True}


class Durations(unittest.TestCase):
    def test_flags(self):
        self.assertEqual(timing_flags(True, True, 10, 10), F_SPAWNED | F_MODE | F_TIMED)
        self.assertEqual(timing_flags(False, False, 9, 10), 0)
        self.assertEqual(timing_flags(False, False, None, 10), 0)

    def test_scoring_fields(self):
        self.assertEqual(come_down_ms(F_SPAWNED, RULES), 100)
        self.assertEqual(carry_ms(F_SPAWNED, RULES), 200)
        self.assertEqual(drop_ms(F_SPAWNED, RULES), 50)

    def test_long_cases(self):
        r = dict(RULES, K2V=False)
        self.assertEqual(come_down_ms(F_SPAWNED, r), 2000)
        self.assertEqual(carry_ms(F_TIMED, r), 3000)
        self.assertEqual(come_down_ms(F_TIMED, r), 100)        # _-H6B tests only bit 1
        r = dict(RULES, timed_until=6000, n4k=0)
        self.assertEqual(come_down_ms(F_TIMED, r), 2000)       # the match-start case
        self.assertEqual(carry_ms(F_TIMED, r), 3000)

    def test_ac_and_f3o(self):
        r = dict(RULES, Ac=True)
        self.assertEqual((come_down_ms(0, r), carry_ms(0, r), drop_ms(0, r)), (1500, 2500, 700))
        self.assertEqual(drop_ms(F_MODE, r), 50)
        r = dict(RULES, F3O=True)
        self.assertEqual((come_down_ms(0, r), carry_ms(0, r)), (1000, 2000))
        self.assertEqual(drop_anim_scale(700), 1.0)
        self.assertEqual(drop_anim_scale(350), 2.0)


class Phases(unittest.TestCase):
    def test_instant(self):
        f = fighter()
        d = Drone(f)
        d.place(0, (40.0, 30.0), standalone=False, w35=16, f3o=False, camera=(0, 0, 100))
        self.assertEqual((f["state"], f["x"], f["y"], d.phase), (0, 40.0, 30.0, IDLE))

    def test_not_spawned_keeps_fighter(self):
        f = dict(fighter(), spawned=False)
        d = Drone(f)
        d.place(0, (40.0, 30.0), standalone=True, w35=0, f3o=False, camera=(0, 0, 100))
        self.assertEqual((f["x"], f["state"], d.phase), (5.0, 3, COME_DOWN))
        d.place(0, None, standalone=True, w35=0, f3o=False, camera=(0, 0, 100))
        self.assertEqual(d.to_x, 40.0)

    def test_full_path(self):
        f = fighter()
        d = Drone(f)
        d.place(0, (80.0, 30.0), standalone=False, w35=0, f3o=False, camera=(0, 10, 100))
        self.assertEqual((f["x"], f["y"]), (100, -190))            # right edge, 200 above the top
        args = (F_SPAWNED, RULES, 1, False)
        d.tick(1, *args)                                           # phase 1 starts
        self.assertEqual((d.phase, d.start), (COME_DOWN, 1))
        d.tick(101, *args)                                         # 101 is not > 1 + 100
        self.assertEqual(d.phase, COME_DOWN)
        d.tick(102, *args)                                         # -> phase 2 starts the same tick
        self.assertEqual((d.phase, d.start, f["state"]), (CARRY, 102, 3))
        d.tick(202, *args)                                         # halfway, ease out power 3
        self.assertAlmostEqual(f["x"], 100 + (1 - 0.125) * (80 - 100))
        d.tick(303, *args)                                         # arrival -> phase 3, held still
        self.assertEqual((d.phase, f["x"], f["y"], f["state"]), (DROP, 80.0, 30.0, 4))
        d.tick(352, *args)
        self.assertEqual(f["state"], 4)
        d.tick(353, *args)                                         # 303 + 50 <= 353: let go
        self.assertEqual((d.phase, f["state"], f["vy"]), (IDLE, 0, 30.0))

    def test_drop_variants(self):
        f = dict(fighter(), spawned=False)
        d = Drone(f)
        d.phase = DROP
        d.tick(10, 0, RULES, 3, False)
        d.tick(60, 0, RULES, 3, False)
        self.assertEqual((f["vy"], d.fast_drop, f["state"]), (70.0, True, 5))
        f = dict(fighter(), held_bit=True)
        d = Drone(f)
        d.phase = DROP
        d.tick(10, 0, RULES, 1, False)
        d.tick(60, 0, RULES, 1, False)
        self.assertEqual(f["state"], 5)


class Scoring(unittest.TestCase):
    def test_defaults_and_cells(self):
        from bh.spawn_bot import respawn_ms, scoring_rules
        r = scoring_rules({})
        self.assertEqual((r["o2N"], r["j57"], r["C18"], r["K2V"], r["Ac"]), (1500, 2500, 700, False, False))
        self.assertEqual(respawn_ms(F_SPAWNED, r), 2000 + 3000 + 700)      # long case: spawned, no K2V
        self.assertEqual(respawn_ms(0, r), 1500 + 2500 + 700)
        r = scoring_rules({"FetchDuration": "100", "RespawnDuration": "200", "DropDuration": "30",
                           "RespawnTimesForRounds": "true"})
        self.assertEqual(respawn_ms(F_SPAWNED, r), 330)
        r = scoring_rules({"RespawnTimesOnlyForSpecialEntities": "TRUE"})
        self.assertEqual(respawn_ms(F_MODE, r), 1500 + 2500 + 700)
        self.assertEqual(respawn_ms(0, dict(r, K2V=True)), 1500 + 2500 + 700)

if __name__ == "__main__":
    unittest.main()
