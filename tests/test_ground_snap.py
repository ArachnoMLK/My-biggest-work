"""Tests of the ground look-ahead and the landing lock (tools/bh/ground_snap.py). Synthetic values only.
Run: python -I -m unittest discover -s tests"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh.dodge import dash_blocked, dash_try, gates  # noqa: E402
from bh.ground_snap import (fall_probe, fall_reach, fall_snap, jump_snap, landing_lock, landing_marks,  # noqa: E402
                            rise_snap)
from bh.raycast import Line  # noqa: E402


def floor(y, type_=1, x0=-1000, x1=1000):
    return Line(x0, y, x1, y, type=type_, normal=(0.0, -1.0))


class Reach(unittest.TestCase):
    def test_only_when_falling(self):
        self.assertIsNone(fall_reach(0.0, False))
        self.assertIsNone(fall_reach(-5.0, False))

    def test_seven_ticks_capped(self):
        self.assertAlmostEqual(fall_reach(10.0, False), 10.0 * 7 * 0.384)
        self.assertAlmostEqual(fall_reach(10.0, True), 10.0 * 5 * 0.384)       # fast fall: 5 ticks
        self.assertEqual(fall_reach(40.0, False), 60.0)                        # 107.52 -> 60
        self.assertEqual(fall_reach(40.0, False, attack=True), 100.0)          # the attack pick: 100
        self.assertAlmostEqual(fall_reach(30.0, True, attack=True), 57.6)


class FallSnap(unittest.TestCase):
    def test_hard_floor_within_reach(self):
        f = floor(100)
        y, line = fall_snap([f], 1, 1000, 0.0, 80.0, 20.0, False)             # reach 53.76, floor 20 below
        self.assertIs(line, f)
        self.assertAlmostEqual(y, 100 - 1.01)

    def test_out_of_reach(self):
        self.assertIsNone(fall_snap([floor(100)], 1, 1000, 0.0, 30.0, 20.0, False))    # 70 below, reach 53.76
        self.assertIsNone(fall_snap([floor(100)], 1, 1000, 0.0, 80.0, 0.0, False))     # not falling
        self.assertIsNone(fall_snap([floor(100)], 1, 1000, 0.0, 80.0, -3.0, False))

    def test_cap(self):
        f = floor(100)
        self.assertIsNone(fall_snap([f], 1, 1000, 0.0, 30.0, 60.0, False))            # 70 below, cap 60
        self.assertIsNotNone(fall_snap([f], 1, 1000, 0.0, 30.0, 60.0, False, attack=True))   # cap 100

    def test_soft_floor_at_half_reach(self):
        soft = floor(100, type_=2)
        self.assertIsNotNone(fall_snap([soft], 1, 1000, 0.0, 80.0, 20.0, False))       # 20 below, half reach 26.88
        self.assertIsNone(fall_snap([soft], 1, 1000, 0.0, 70.0, 20.0, False))          # 30 below

    def test_soft_floor_and_held_drop(self):
        soft = floor(100, type_=2)
        args = ([soft], 1, 1000, 0.0, 80.0, 20.0, False)
        self.assertIsNone(fall_snap(*args, attack=True, dir=2, h76=900))               # Drop held >= 64 ms
        self.assertIsNotNone(fall_snap(*args, attack=True, dir=2, h76=960))            # 40 ms: still snaps
        self.assertIsNotNone(fall_snap(*args, attack=False, dir=2, h76=900))           # the dash / jump call
        self.assertIsNotNone(fall_snap([floor(100)], 1, 1000, 0.0, 80.0, 20.0, False, attack=True, dir=2, h76=0))

    def test_hard_wins_over_soft(self):
        hard, soft = floor(100), floor(90, type_=2)
        self.assertIs(fall_probe([soft, hard], 1, 1000, 0.0, 80.0, 20.0, False).line, hard)

    def test_steep_line(self):
        steep = Line(-100, 0, 100, 400, type=1, normal=(0.894, -0.447))                # |nx / ny| = 2
        self.assertIsNone(fall_snap([steep], 1, 1000, 0.0, 190.0, 20.0, False))


class RiseSnap(unittest.TestCase):
    def test_soft_platform_above_the_feet(self):
        soft = floor(100, type_=2)
        y, line = rise_snap([soft], 1, 1000, 0.0, 120.0, -10.0, 0)                     # feet 20 below it
        self.assertIs(line, soft)
        self.assertAlmostEqual(y, 100 - 1.01)
        self.assertIsNone(rise_snap([soft], 1, 1000, 0.0, 140.0, -10.0, 0))            # 40 below: reach 30
        self.assertIsNotNone(rise_snap([soft], 1, 1000, 0.0, 140.0, -10.0, 0, light=True))   # reach 50
        self.assertIsNone(rise_snap([floor(100)], 1, 1000, 0.0, 120.0, -10.0, 0))      # hard lines are not probed

    def test_after_a_drop_through(self):
        soft = floor(100, type_=2)
        self.assertIsNotNone(rise_snap([soft], 1, 1000, 0.0, 160.0, 10.0, 900))        # 900 + 192 >= 1000: reach 70
        self.assertIsNone(rise_snap([soft], 1, 1000, 0.0, 160.0, 10.0, 800))

    def test_attack_with_held_drop(self):
        soft = floor(100, type_=2)
        self.assertIsNone(rise_snap([soft], 1, 1000, 0.0, 120.0, 10.0, 0, attack=True, dir=2, h76=900))
        self.assertIsNotNone(rise_snap([soft], 1, 1000, 0.0, 120.0, -10.0, 0, attack=True, dir=2, h76=900))  # rising
        self.assertIsNotNone(rise_snap([soft], 1, 1000, 0.0, 120.0, 10.0, 900, attack=True, dir=2, h76=900))  # dropped

    def test_jump_snap(self):
        soft, hard = floor(100, type_=2), floor(100)
        self.assertIsNone(jump_snap([hard], 1, 1000, 0.0, 80.0, 20.0, False, 0, 0))    # no recent drop through
        self.assertIs(jump_snap([soft], 1, 1000, 0.0, 120.0, 20.0, False, 900, 0)[1], soft)   # `_-w4c`
        self.assertIs(jump_snap([hard], 1, 1000, 0.0, 80.0, 20.0, False, 900, 0)[1], hard)    # then `_-y1U`


class Landing(unittest.TestCase):
    def test_lock(self):
        self.assertTrue(landing_lock(1048, 1000, False, 0))
        self.assertFalse(landing_lock(1064, 1000, False, 0))                           # t < _-t4D + 64
        self.assertFalse(landing_lock(1016, 1000, True, 0))                            # airborne
        self.assertFalse(landing_lock(1016, 1000, False, 1))                           # on a wall

    def test_marks(self):
        # landing after a jump: _-322 and _-t4D, the jumped flag cleared
        self.assertEqual(landing_marks(1000, True, False, True, 0, 500, 0, 0), (1000, 1000, 500, False))
        # with a pending jump (_-Xb): _-I5A + 64
        self.assertEqual(landing_marks(1000, True, False, True, 1, 500, 0, 0), (1000, 1000, 564, False))
        # landing without a jump (walked off a ledge): _-322 only
        self.assertEqual(landing_marks(1000, True, False, False, 1, 500, 0, 0), (1000, 0, 500, False))
        # standing: nothing but the flag
        self.assertEqual(landing_marks(1000, False, False, True, 0, 500, 7, 9), (7, 9, 500, False))
        # in the air: nothing
        self.assertEqual(landing_marks(1000, True, True, True, 0, 500, 7, 9), (7, 9, 500, True))


class DashGate(unittest.TestCase):
    def test_350(self):
        free = dict(move_locked=False, p50=False, t26=0, e3=0, power=False, r51=0, xb=0, c54=False)
        self.assertFalse(dash_blocked(1000, **free))
        for k, v in (("move_locked", True), ("p50", True), ("t26", 900), ("e3", 900), ("power", True), ("r51", 1),
                     ("xb", 1), ("c54", True)):
            self.assertTrue(dash_blocked(1000, **dict(free, **{k: v})), k)
        self.assertFalse(dash_blocked(1000, **dict(free, t26=888)))                    # 888 + 112 > 1000 is false
        self.assertFalse(dash_blocked(1000, **dict(free, e3=900), e3_counts=False))
        # after a dodge: _-H2b + _-Uy + ToDashDelay x 16 > t
        self.assertTrue(dash_blocked(1000, **free, h2b=600, uy=200, to_dash_delay=13))   # 600 + 200 + 208 = 1008
        self.assertFalse(dash_blocked(1008, **free, h2b=600, uy=200, to_dash_delay=13))
        self.assertFalse(dash_blocked(1000, **free, h2b=600, uy=200, to_dash_delay=None))

    def test_dash_try_matches_gates(self):
        # `gates` returns None for "not d350 and dash_ok" exactly where the dash try is reached; compare it with
        # a run where the dash is refused (d350), over a grid of inputs
        import itertools
        n = 0
        for (dir, c, hit, air, locked, lchain, h2b, w14, r26) in itertools.product(
                (0, 1, 2, 4, 6, 8, 10, 5), (False, True), (0, 950, 990), (False, True), (False, True),
                (False, True), (0, 800), (0, 800), (False, True)):
            args = (1000, dir, c, hit, air, locked, lchain, h2b, w14, 0, r26, 0)
            tail = (False, 0, 0, False, None)                  # grounded false, `_-VE`, `_-532`, `_-n3h`, no chase
            with_dash = gates(*args, False, True, *tail)
            without = gates(*args, True, False, *tail)
            want = dash_try(1000, dir, c, hit, air, locked, lchain, h2b, w14, r26)
            if without is not None:                            # else `not go` hides the difference
                self.assertEqual(with_dash is None, want, args)
                n += 1
            elif want:
                self.assertIsNone(with_dash)
        self.assertGreater(n, 100)


if __name__ == "__main__":
    unittest.main()
