"""Tests of the damage / knockback transcription (tools/bh/knockback.py). See docs/knockback-11.00.md.

Run: python -I -m unittest discover -s tests   (from the repository root)
"""
import hashlib
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh import abc, knockback, swf  # noqa: E402
from bh.knockback import (STAT_TABLE, as3_round, atan2_netsafe, charged_scale, directional_influence,  # noqa: E402
                          final_magnitude, hit_damage, hitstun_ms, key_vector, knockback_decay, knockback_force,
                          octant_angle,
                          stat_multiplier)

GAME = os.environ.get("BRAWLHALLA_DIR", r"C:\Program Files (x86)\Steam\steamapps\common\Brawlhalla")
HAVE_GAME = os.path.exists(os.path.join(GAME, "BrawlhallaAir.swf"))


class Stat(unittest.TestCase):
    def test_table_shape(self):
        self.assertEqual(len(STAT_TABLE), 23)
        self.assertEqual(STAT_TABLE[11], 1)
        self.assertEqual(list(STAT_TABLE), sorted(STAT_TABLE))

    def test_index(self):
        self.assertEqual(stat_multiplier(5, 5), 1)
        self.assertEqual(stat_multiplier(6, 5), 1.031)
        self.assertEqual(stat_multiplier(0, 11), 0.8349)
        with self.assertRaises(IndexError):
            stat_multiplier(0, 12)


class Damage(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(hit_damage(10.0, 0, 0.0, 1.0, 1.0, 1.0), 10.0)

    def test_charge_extra_is_at_least_one(self):
        self.assertEqual(hit_damage(10.0, 10, 1.0, 1.0, 1.0, 1.0), 11.0)    # 10 - 50 -> 1
        self.assertEqual(hit_damage(10.0, 60, 1.0, 1.0, 1.0, 1.0), 20.0)    # 60 - 50 = 10

    def test_zero_stat_entry_is_skipped(self):
        self.assertEqual(hit_damage(10.0, 0, 0.0, 1.0, 1.0, 1.0, stat=0), 10.0)

    def test_heal_floor(self):
        self.assertEqual(hit_damage(-50.0, 0, 0.0, 1.0, 1.0, 1.0, victim_w22=20), -20.0)
        self.assertEqual(hit_damage(-5.0, 0, 0.0, 1.0, 1.0, 1.0, victim_w22=20), -5.0)


class Force(unittest.TestCase):
    def test_formula(self):
        # d = (100 + 0 + 0) / 100 = 1 -> force * 1.5
        self.assertEqual(knockback_force(20.0, 0.0, 100, 0, 1.0, 1.0, 0.0), 30.0)

    def test_team_and_floor(self):
        self.assertEqual(knockback_force(20.0, 0.0, 100, 0, 1.0, 1.0, 0.0, same_team=True), 22.5)
        self.assertEqual(knockback_force(20.0, 0.0, 100, 0, 1.0, 1.0, 40.0), 0)

    def test_mode5_uses_50(self):
        self.assertEqual(knockback_force(20.0, 0.0, 999, 0, 1.0, 1.0, 0.0, mode5=True),
                         knockback_force(20.0, 0.0, 50, 0, 1.0, 1.0, 0.0))

    def test_charge(self):
        self.assertEqual(charged_scale(0, 400), 1)
        self.assertEqual(charged_scale(400, 400), 1.25)


class Magnitude(unittest.TestCase):
    def test_sum_floor_and_soft(self):
        self.assertEqual(final_magnitude(30.0, 5.0, 2.0, 1.0), 37.0)
        self.assertEqual(final_magnitude(30.0, 5.0, 2.0, 1.0, minimum=50.0), 50.0)
        self.assertEqual(final_magnitude(30.0, 5.0, 2.0, 0.0, minimum=50.0), 37.0)   # no floor without VariableImpulse
        self.assertEqual(final_magnitude(30.0, 5.0, 5.0, 0.0, soft_flag=True), 36.0)


class Influence(unittest.TestCase):
    def test_as3_round(self):
        self.assertEqual([as3_round(v) for v in (2.5, -2.5, 0.4999, -0.5)], [3, -2, 0, 0])

    def test_netsafe_atan2(self):
        self.assertEqual(atan2_netsafe(0.5, 1.0), 0.464)
        self.assertEqual(atan2_netsafe(0.0, 0.0), 0.0)

    def test_keys(self):
        self.assertEqual(key_vector(4 | 1), (-1, -1))
        self.assertEqual(key_vector(8 | 2), (1, 1))
        self.assertEqual(octant_angle(-1, 1), -0.785)
        self.assertEqual(octant_angle(0, -1), 3.142)

    def test_snap_inside_limit(self):
        self.assertEqual(directional_influence(1.0, 0.5, 8), (1.0, 0.0))

    def test_turn_by_limit(self):
        self.assertEqual(directional_influence(1.0, 0.0, 1), (0.697, -0.717))   # up: turn by -0.8 rad

    def test_no_keys_or_no_point(self):
        self.assertEqual(directional_influence(1.0, 0.0, 0), (1.0, 0.0))
        self.assertEqual(directional_influence(0.0, 0.0, 8), (0.0, 0.0))


class Hitstun(unittest.TestCase):
    def test_frames_to_ms(self):
        self.assertEqual(hitstun_ms(12), 192.0)
        self.assertEqual(hitstun_ms(12, minus5=True), 187.0)
        self.assertEqual(hitstun_ms(0, minus5=True), 0.0)


class Decay(unittest.TestCase):
    def test_velocity_decays_when_not_big(self):
        v1d, p5s, j, d = knockback_decay(100.0, 0.0, 0.0, 0.0, recovery=50.0)
        self.assertAlmostEqual(v1d, 100.0 - 50.0 * 0.384)
        self.assertEqual((p5s, j, d), (0.0, 0.0, 0.0))

    def test_overshoot_decays_when_big(self):
        out = knockback_decay(250.0, 0.0, 400.0, 0.0, recovery=50.0)
        self.assertEqual(out[:2], (250.0, 0.0))
        self.assertAlmostEqual(out[2], 400.0 - 19.2)

    def test_soft_and_frozen(self):
        self.assertEqual(knockback_decay(100.0, 0.0, 0.0, 0.0, 50.0, frozen=True)[0], 100.0)
        self.assertAlmostEqual(knockback_decay(100.0, 0.0, 0.0, 0.0, 50.0, frozen=True, soft=True)[0],
                               100.0 - 8.5548 * 0.384)


class Cli(unittest.TestCase):
    def test_wrong_patch_exits_2(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "other.abc")
            with open(p, "wb") as f:
                f.write(b"not the pinned abc")
            out = subprocess.run([sys.executable, "-I", os.path.join(ROOT, "tools", "bht.py"), "knockback-verify", "--abc", p],
                                 capture_output=True, text=True)
        self.assertEqual(out.returncode, 2, out.stderr)
        self.assertIn("no knockback anchors", out.stdout)


@unittest.skipUnless(HAVE_GAME, "Brawlhalla not installed")
class Game(unittest.TestCase):
    def test_pins_hold(self):
        with open(os.path.join(GAME, "BrawlhallaAir.swf"), "rb") as f:
            main = swf.Swf(f.read())
        data = max(main.abc_blocks(), key=lambda b: len(b[1]))[1]
        sha = hashlib.sha256(data).hexdigest()
        if sha != knockback.ABC_1100:
            self.skipTest("knockback anchors are pinned to patch 11.00")
        self.assertEqual(knockback.verify(abc.Abc(data), sha), [])


if __name__ == "__main__":
    unittest.main()
