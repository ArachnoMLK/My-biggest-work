"""Tests of the per-tick harness (tools/bh/harness.py) on a synthetic map. Synthetic values only.
Run: python -I -m unittest discover -s tests"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh import harness, smoke  # noqa: E402
from bh.respawn_points import parse_respawns  # noqa: E402
from bh.spawn_bot import DROP_SPEED, DROP_SPEED_FAST, F_SPAWNED, respawn_ms, scoring_rules  # noqa: E402

FLAT = ('<LevelDesc><HardCollision X1="-1000" X2="1000" Y="500" /><HardCollision X1="1000" X2="-1000" Y="900" />'
        '<HardCollision X="-1000" Y1="500" Y2="900" /><HardCollision X="1000" Y1="900" Y2="500" />'
        '<Respawn X="0" Y="0" /></LevelDesc>')


def landed(inputs, ticks=200):
    f = harness.Fighter(0.0, 0.0)
    tr = harness.run(f, smoke.map_grid(FLAT), inputs, ticks)
    return f, tr


class Harness(unittest.TestCase):
    def test_falls_and_stands(self):
        f, tr = landed(lambda i: (False, False, False), 100)
        self.assertIsNotNone(f.ground)
        self.assertAlmostEqual(f.y, 500.0 - 1.01)
        self.assertEqual(f.events[0][1][0], "land")

    def test_ground_jump_after_the_squat(self):
        f, tr = landed(lambda i: (False, False, i == 80))
        kinds = [e for _, e in f.events]
        self.assertEqual(kinds[1:3], [("press", "squat"), ("release", "ground")])
        self.assertEqual(f.events[2][0] - f.events[1][0], 32)          # 2 ticks of squat
        self.assertFalse(tr[80][3])                                     # tick 81: still on the ground
        self.assertTrue(tr[81][3])                                      # tick 82: airborne
        self.assertAlmostEqual(tr[80][2] - tr[81][2], (57.0 - 3.75 * 0.384) * 0.384)
        self.assertEqual(kinds[-1][0], "land")
        self.assertAlmostEqual(f.y, 500.0 - 1.01)

    def test_air_jumps_counted(self):
        presses = {80, 100, 110, 120}
        f, tr = landed(lambda i: (False, False, i in presses), 300)
        kinds = [e[1] for _, e in f.events if e[0] in ("press", "release")]
        self.assertEqual(kinds, ["squat", "ground", "squat", "air", "squat", "air", "squat", None])
        self.assertEqual(f.air_used, 0)                                 # reset on landing [H]

    def test_walk_right(self):
        f, tr = landed(lambda i: (False, i > 60, False), 120)
        self.assertGreater(f.x, 0.0)
        self.assertIsNotNone(f.ground)
        self.assertAlmostEqual(f.v1d, harness.DEFAULT_STATS["RunSpeed"])   # held at the max

    def test_walk_off_a_ledge_to_a_bottom_ko(self):
        ledge = ('<LevelDesc><HardCollision X1="-50" X2="50" Y="500" /><HardCollision X1="50" X2="-50" Y="600" />'
                 '<HardCollision X="-50" Y1="500" Y2="600" /><HardCollision X="50" Y1="600" Y2="500" />'
                 '<Respawn X="0" Y="0" /></LevelDesc>')
        cam = (-400.0, -400.0, 400.0, 600.0)
        kill = {"LeftKill": 100, "RightKill": 100, "TopKill": 100, "BottomKill": 100,
                "HardLeftKill": False, "HardRightKill": False, "SoftTopKill": False}
        f = harness.Fighter(0.0, 0.0)
        tr = harness.run(f, smoke.map_grid(ledge), lambda i: (False, i > 60, False), 600,
                         bounds=(cam, kill), stop_on_ko=True)
        kos = [e for _, e in f.events if e[0] == "ko"]
        self.assertEqual(len(kos), 1)
        self.assertEqual(f.a3d, kos[0][1])
        self.assertGreater(f.y, 700.0)                                  # past bottom + BottomKill
        self.assertGreater(f.x, 50.0)                                   # off the right edge

    def test_wall_contact_and_wall_jump(self):
        block = ('<HardCollision X1="200" X2="260" Y="-300" /><HardCollision X="260" Y1="-300" Y2="500" />'
                 '<HardCollision X1="260" X2="200" Y="500" /><HardCollision X="200" Y1="500" Y2="-300" />')
        grid = smoke.map_grid(FLAT.replace('<Respawn X="0"', block + '<Respawn X="0"'))
        f = harness.Fighter(0.0, 0.0)
        tr = harness.run(f, grid, lambda i: (False, 60 < i < 150, i in (70, 85, 150)), 160)
        kinds = [e for _, e in f.events if e[0] != "wall"]
        self.assertEqual(kinds[-2:], [("press", "squat"), ("release", "wall")])
        self.assertIn(("wall", 2), [e for _, e in f.events])            # the wall is right of the feet
        i = [t for t, _, _, _ in tr].index(f.events[-1][0])
        self.assertLess(tr[i][1], tr[i - 1][1])                         # pushed away from the wall
        self.assertLess(tr[i][2], tr[i - 1][2])                         # and up
        self.assertIsNone(f.ground)                                     # a wall never stays in _-96f

    def test_air_side_dodge_pushes_then_exits(self):
        row = {"DodgeName": "side", "DodgeID": 2, "Set": "Default", "kind": 1, "where": 3, "IsFast": False,
               "Duration": 4, "Recover": 2, "SpeedXMult": 1.0, "SpeedXMaxMult": 0.0, "SpeedYMult": 1.0,
               "SpeedYMaxMult": 0.0, "AccelXMult": 0.5, "AccelYMult": 0.0, "Cooldown": 10, "CooldownGround": 5,
               "CooldownLanded": 3, "ExitX": 0.5, "ExitBackX": 0.25, "ExitY": 0.5, "ExitBackY": 0.25}
        rows = [row, dict(row, DodgeName="StandardSpot", DodgeID=1, kind=0)]
        f, grid = harness.Fighter(0.0, -400.0), smoke.map_grid(FLAT)
        ev = harness.tick(f, 1000, grid, False, True, False, 0, None, True, 8, rows)
        self.assertEqual(ev[0], ("dodge", "side"))
        self.assertTrue(f.e6p)
        self.assertEqual((f.h2b, f.uy, f.c1d, f.y1f), (1000, 64, 32, 256))
        y = f.y
        for t in range(1016, 1096, 16):                      # timer end at 1000 + 64 + 32
            harness.tick(f, t, grid, False, True, False, 0, None, False, 8, rows)
            self.assertTrue(f.e6p)
            self.assertEqual((f.v1d, f.p5s, f.y), (30.0, 0.0, y))   # 60 x 1 x 0.5, no gravity while dodging
        harness.tick(f, 1096, grid, False, True, False, 0, None, False, 8, rows)
        self.assertFalse(f.e6p)
        self.assertTrue(f.u5e)
        self.assertEqual((f.t5l, f.wl), (1.0, 1.0))

    def test_attack_slot_and_gravity_cancel(self):
        row = {"DodgeName": "spot", "DodgeID": 1, "Set": "Default", "kind": 0, "where": 3, "IsFast": False,
               "Duration": 20, "Recover": 0, "CancelStart": 2, "CancelLimit": 10}
        f, grid = harness.Fighter(0.0, -400.0), smoke.map_grid(FLAT)
        ev = harness.tick(f, 1000, grid, light_press=True)
        self.assertEqual(ev[0][0], "attack")
        self.assertEqual(ev[0][2], False)
        air_slot = ev[0][1]
        harness.tick(f, 1016, grid, dodge_press=True, dodge_rows=[row])
        self.assertTrue(f.e6p)
        ev = harness.tick(f, 1016 + 48, grid, light_press=True)
        self.assertEqual(ev[0][2], True)                      # inside 1016 + 32 .. 1016 + 160
        self.assertNotEqual(ev[0][1], air_slot)               # a ground move in the air

    def test_attack_names_the_power(self):
        f = harness.Fighter(0.0, -400.0, moves={"hero": {"mBaseWeapon1": "Sword"},
                                                 "weapon": {"id": "Unarmed", "slots": [None, "UJab"] + [None] * 19}})
        ev = harness.tick(f, 1000, smoke.map_grid(FLAT), light_press=True, keys=0)
        self.assertEqual(ev[0][0], "attack")
        self.assertEqual(len(ev[0]), 4)
        f.moves["weapon"]["slots"] = ["J"] * 21
        f.moves["powers"] = {"J": {"PowerName": "J", "MomentumVersion": "JM"}, "JM": {"PowerName": "JM"}}
        f.v1d = 70.0
        ev = harness.tick(f, 1016, smoke.map_grid(FLAT), light_press=True, keys=0)
        self.assertEqual(ev[0][3], "JM")                      # |vx| >= 60 toward the facing (right)

    def test_power_steps_fire_on_their_ticks(self):
        powers = {"J": {"PowerName": "J", "CastTime": "2,3"}}
        f = harness.Fighter(0.0, -400.0, moves={"hero": {}, "weapon": {"id": "Unarmed", "slots": ["J"] * 21},
                                                 "powers": powers})
        grid, fired = smoke.map_grid(FLAT), []
        for i in range(8):
            t = 1600 + 16 * i
            ev = harness.tick(f, t, grid, light_press=(i == 0))
            fired += [(i, e[2]) for e in ev if e[0] == "step"]
        self.assertEqual(fired, [(2, 0), (5, 1)])             # step 0 after 2 ticks, step 1 three ticks later
        self.assertIsNone(f.power)

    def test_step_hits(self):
        from bh.power_data import power_steps
        row = {"PowerName": "J", "CastTime": "1", "TargetMethod": "PBAoE", "AoERadiusX": "20", "AoERadiusY": "20",
               "CenterOffsetX": "50", "CenterOffsetY": "0"}
        f = harness.Fighter(0.0, 0.0)
        f.power = {"name": "J", "steps": power_steps(row), "g4i": 1, "hit": set()}
        box = {"Width": [40], "Height": [80], "OffsetX": [0], "OffsetY": [0]}
        self.assertEqual(harness.step_hits(f, 0, harness.Fighter(60.0, 20.0), box), 0)
        self.assertIsNone(harness.step_hits(f, 0, harness.Fighter(300.0, 20.0), box))
        f.facing_left = True                                  # the offset is mirrored
        self.assertIsNone(harness.step_hits(f, 0, harness.Fighter(60.0, 20.0), box))
        self.assertEqual(harness.step_hits(f, 0, harness.Fighter(-60.0, 20.0), box), 0)

    def test_apply_hit(self):
        from bh.power_data import power_steps
        row = {"PowerName": "J", "CastTime": "1", "BaseDamage": "10", "VariableImpulse": "20", "FixedImpulse": "5",
               "ImpulseOffsetX": "3", "ImpulseOffsetY": "-4", "FixedStunTime": "6"}
        f, v = harness.Fighter(0.0, 0.0), harness.Fighter(50.0, 0.0)
        f.power = {"name": "J", "steps": power_steps(row), "g4i": 1, "hit": set()}
        dmg, m = harness.apply_hit(f, v, 0, 1000)
        d = 10 / 100
        self.assertEqual(dmg, 10)
        self.assertAlmostEqual(m, 20 * (d + d * (d / 2)) + 5)
        self.assertAlmostEqual(v.h84, 0.6 * m)
        self.assertAlmostEqual(v.a4a, -0.8 * m)
        self.assertEqual((v.w22, v.stun_until), (10, 1096))
        v.air_used = v.air_allowed
        harness.apply_hit(f, v, 0, 1200)
        self.assertEqual(v.air_used, v.air_allowed - 1)       # a hit gives one air jump back
        ev = harness.tick(v, 1016, smoke.map_grid(FLAT), jump_press=True)
        self.assertFalse(any(e[0] == "press" for e in ev))    # inputs are off in hitstun

    def test_cast_impulse(self):
        f = harness.Fighter(0.0, 0.0, v1d=3.0, p5s=4.0)
        harness.cast_impulse(f, {"CastImpulseX": "12", "CastImpulseY": "2147483647"})
        self.assertEqual((f.v1d, f.p5s), (12.0, 4.0))
        f.facing_left = True
        harness.cast_impulse(f, {"CastImpulseX": "12", "CastImpulseY": "-30"})
        self.assertEqual((f.v1d, f.p5s), (-12.0, -30.0))

    def test_fire_impulse(self):
        f = harness.Fighter(0.0, 0.0, v1d=3.0, p5s=4.0)
        harness.fire_impulse(f, {"FireImpulseX": "5,7", "FireImpulseY": "-20"}, 1)
        self.assertEqual((f.v1d, f.p5s), (7.0, -20.0))
        f.facing_left = True
        harness.fire_impulse(f, {"FireImpulseX": "5,7"}, 3)
        self.assertEqual((f.v1d, f.p5s), (-5.0, -20.0))

    def test_knockback_decay_in_hitstun(self):
        f = harness.Fighter(0.0, -400.0, v1d=60.0, p5s=0.0, stun_until=2000)
        f.stats["Recovery"] = 10.0
        harness.tick(f, 1000, smoke.map_grid(FLAT))
        self.assertAlmostEqual(f.v1d, 60.0 - 10.0 * 0.384)      # no friction, the decay instead

    def test_move_lock_of_a_power(self):
        powers = {"J": {"PowerName": "J", "CastTime": "5"}, "M": {"PowerName": "M", "CastTime": "5", "AllowMove": "TRUE"}}
        grid = smoke.map_grid(FLAT)
        for name, moves in (("J", False), ("M", True)):
            f = harness.Fighter(0.0, -400.0, moves={"hero": {}, "weapon": {"id": "U", "slots": [name] * 21},
                                                     "powers": powers})
            harness.tick(f, 1600, grid, light_press=True)
            self.assertEqual(harness.move_locked(f), not moves)
            v = f.v1d
            harness.tick(f, 1616, grid, right=True)
            self.assertEqual(f.v1d > v, moves)                # right is ignored while move-locked

    def test_inputs_from_records(self):
        records = [(0, 0), (1000, 8), (1290, 8 | 16), (1400, 8), (1500, 4 | 16)]   # synthetic key words
        inputs = harness.from_records(records)
        self.assertEqual(inputs(10), (False, False, False))             # t = 160
        self.assertEqual(inputs(63), (False, True, False))              # t = 1008: MoveRight
        self.assertEqual(inputs(81), (False, True, True))               # t = 1296: jump edge
        self.assertEqual(inputs(82), (False, True, False))              # t = 1312: still held, no new press
        self.assertEqual(inputs(94), (True, False, True))               # t = 1504: MoveLeft and a new press
        f, tr = landed(inputs, 120)
        self.assertEqual([e for _, e in f.events][1:3], [("press", "squat"), ("release", "ground")])
        self.assertEqual(f.events[1][0], 1296)


class MatchStart(unittest.TestCase):
    XML = ('<LevelDesc><Respawn Initial="true" X="-200" Y="100" /><Respawn Initial="true" X="200" Y="100" />'
           '<Respawn X="0" Y="0" /></LevelDesc>')

    def run_start(self, spawned):
        return harness.match_start([{"id": 9}, {"id": 4}], 12345, parse_respawns(self.XML), (-500, -300, 1000),
                                   spawned=spawned)

    def test_spawned_drone_lets_go_in_state_0(self):
        out = self.run_start(True)
        self.assertEqual([e["id"] for e, _, _, _ in out], [4, 9])
        self.assertEqual(sorted(f.x for _, f, _, _ in out), [-200.0, 200.0])
        trip = respawn_ms(F_SPAWNED, scoring_rules({}, n4k=16))
        for _, f, t, state in out:
            self.assertEqual((f.y, f.p5s, state), (100.0, DROP_SPEED, 0))
            self.assertTrue(272 + trip <= t <= 272 + trip + 3 * 16, t)

    def test_not_spawned_lets_go_in_state_5(self):
        trip = respawn_ms(0, scoring_rules({}, n4k=16))
        for _, f, t, state in self.run_start(False):
            self.assertEqual((f.y, f.p5s, state), (100.0, DROP_SPEED_FAST, 5))
            self.assertTrue(272 + trip <= t <= 272 + trip + 3 * 16, t)

    def test_no_point_gives_none(self):
        out = harness.match_start([{"id": 1}, {"id": 2}], 1,
                                  parse_respawns('<LevelDesc><Respawn X="0" Y="0" /></LevelDesc>'), (0, 0, 100))
        self.assertEqual([f for _, f, _, _ in out], [None, None])

class Play(unittest.TestCase):
    XML = ('<LevelDesc><HardCollision X1="-300" X2="300" Y="500" /><HardCollision X1="300" X2="-300" Y="600" />'
           '<HardCollision X="-300" Y1="500" Y2="600" /><HardCollision X="300" Y1="600" Y2="500" />'
           '<Respawn Initial="true" X="-200" Y="400" /><Respawn Initial="true" X="200" Y="400" />'
           '<Respawn X="0" Y="400" /></LevelDesc>')
    CAM = (-1000.0, -600.0, 1000.0, 900.0)
    KILL = {"LeftKill": 200, "RightKill": 200, "TopKill": 200, "BottomKill": 200,
            "HardLeftKill": False, "HardRightKill": False, "SoftTopKill": False}

    def play(self, inputs, lives=3, ticks=3000):
        return harness.play([{"id": 2}, {"id": 1}], 7, parse_respawns(self.XML), (-1000, -600, 2000),
                            smoke.map_grid(self.XML), (self.CAM, self.KILL), {}, inputs, lives=lives, ticks=ticks)

    def test_walker_loses_its_lives_and_is_eliminated(self):
        out = self.play({1: [(0, 8)]}, lives=2)
        walker, still = out[1], out[2]
        self.assertEqual(len(walker["kos"]), 2)
        self.assertEqual(len(walker["let_go"]), 2)              # the match start, then one respawn
        self.assertGreaterEqual(walker["let_go"][1] - walker["kos"][0], 4700)   # not-spawned trip
        self.assertEqual((still["kos"], still["let_go"]), ([], [6000]))

    def test_respawn_uses_the_shared_counter(self):
        out = self.play({1: [(0, 8)], 2: [(0, 4)]}, lives=3, ticks=1200)
        self.assertTrue(out[1]["kos"] and out[2]["kos"])


if __name__ == "__main__":
    unittest.main()
