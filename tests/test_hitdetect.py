"""Tests of the hit detection transcription (tools/bh/hitdetect.py). See docs/hit-detection-11.00.md.

Run: python -I -m unittest discover -s tests   (from the repository root)
"""
import hashlib
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh import abc, hitdetect, swf  # noqa: E402
from bh.hitdetect import (AREA_AT_OWNER, line_of_sight_blocked, skips_line_of_sight, HitRecord, deals_damage, records_after_pass, rehit_blocked, CLEAR, COLLIDER, area_center, capsule_of_box, capsules_touch,  # noqa: E402
                          frame_window, hit_capsule, hurtbox_capsule, hurtbox_frames, hurtbox_row,
                          point_segment_dist2, query_kind, row_values, segment_dist2, segments_cross,
                          target_method)

GAME = os.environ.get("BRAWLHALLA_DIR", r"C:\Program Files (x86)\Steam\steamapps\common\Brawlhalla")
HAVE_GAME = os.path.exists(os.path.join(GAME, "BrawlhallaAir.swf"))


class TargetMethod(unittest.TestCase):
    def test_values(self):
        self.assertEqual(target_method("Smash"), (8, False))
        self.assertEqual(target_method("PBAoE"), (1, False))
        self.assertEqual(target_method("Collider"), (13, False))
        self.assertEqual(target_method(""), (0, False))

    def test_smash_release_prefix(self):
        self.assertEqual(target_method("SmashRelease"), (1, True))
        self.assertEqual(target_method("SmashReleaseRangedAoE"), (5, True))
        self.assertEqual(target_method("SmashReleaseGroundCheckGrabHit"), (2, True))

    def test_kinds(self):
        self.assertEqual(query_kind(8), AREA_AT_OWNER)
        self.assertEqual(query_kind(0), CLEAR)
        self.assertEqual(query_kind(7), CLEAR)
        self.assertEqual(query_kind(13), COLLIDER)
        self.assertEqual(query_kind(99), CLEAR)


class Area(unittest.TestCase):
    def test_owner_offset_mirrors_x(self):
        self.assertEqual(area_center(8, 100.0, 50.0, 1, [0, 30], [0, -10], False), (130.0, 40.0))
        self.assertEqual(area_center(8, 100.0, 50.0, 1, [0, 30], [0, -10], True), (70.0, 40.0))

    def test_point(self):
        self.assertEqual(area_center(3, 0.0, 0.0, 0, [5], [5], False, point=(7.0, 8.0)), (7.0, 8.0))
        self.assertEqual(area_center(5, 0.0, 0.0, 0, [5], [6], False, point=(7.0, 8.0)), (12.0, 14.0))

    def test_collider(self):
        self.assertIsNone(area_center(13, 0.0, 0.0, 1, [0, 4], [0, 2], False, current_frame=1))
        self.assertEqual(area_center(13, 10.0, 10.0, 1, [1, 4], [1, 2], False, current_frame=0), (13.0, 11.0))

    def test_no_query(self):
        self.assertIsNone(area_center(12, 0.0, 0.0, 0, [0], [0], False))

    def test_frame_window(self):
        self.assertEqual(frame_window(None, 7), (7, 1))
        self.assertEqual(frame_window([0, (3 << 16) | 5], 1), (5, 3))


class Capsule(unittest.TestCase):
    def test_box_to_capsule(self):
        self.assertEqual(capsule_of_box(40.0, 100.0), ((0, -20.0), (0, -60.0), 20.0))
        self.assertEqual(capsule_of_box(100.0, 40.0), ((-30.0, -20.0), (60.0, 0), 20.0))

    def test_hit_capsule_is_centred(self):
        x, y, dx, dy, r = hit_capsule(0.0, 0.0, 50.0, 20.0)
        self.assertEqual((x, y, dx, dy, r), (-30.0, 0.0, 60.0, 0, 20.0))
        x, y, dx, dy, r = hit_capsule(0.0, 0.0, 20.0, 50.0)
        self.assertEqual((x, y, x + dx, y + dy, r), (0.0, 30.0, 0.0, -30.0, 20.0))

    def test_hurtbox_bottom_anchored(self):
        x, y, dx, dy, r = hurtbox_capsule(0.0, 0.0, 40.0, 100.0, 5.0, 0.0, False)
        self.assertEqual((x, y, y + dy, r), (5.0, -20.0, -80.0, 20.0))     # spans y in [-100, 0]
        self.assertEqual(hurtbox_capsule(0.0, 0.0, 40.0, 100.0, 5.0, 0.0, True)[0], -5.0)

    def test_geometry(self):
        self.assertTrue(segments_cross(0, 0, 2, 2, 0, 2, 2, 0))
        self.assertFalse(segments_cross(0, 0, 1, 0, 0, 1, 1, 1))      # parallel
        self.assertEqual(point_segment_dist2(0, 0, 10, 0, 5, 3), 9)
        self.assertEqual(point_segment_dist2(0, 0, 10, 0, -3, 4), 25)
        self.assertEqual(point_segment_dist2(0, 0, 10, 0, 13, 4), 25)
        self.assertEqual(point_segment_dist2(0, 0, 0, 0, 3, 4), 25)
        self.assertEqual(segment_dist2(0, 0, 10, 0, 0, 5, 10, 0), 25)

    def test_touch(self):
        a = (0.0, 0.0, 10.0, 0.0, 2.0)
        self.assertTrue(capsules_touch(a, (0.0, 4.0, 10.0, 0.0, 2.0)))      # distance 4 = 2 + 2
        self.assertFalse(capsules_touch(a, (0.0, 4.5, 10.0, 0.0, 2.0)))
        self.assertTrue(capsules_touch(a, (5.0, -5.0, 0.0, 10.0, 0.1)))     # crossing


class Hurtbox(unittest.TestCase):
    def test_frames(self):
        self.assertEqual(hurtbox_frames(["1-3", "4"]), [1, 1, 1, 2])
        self.assertEqual(hurtbox_frames(["3-4"]), [None, None, 1, 1])

    def test_row(self):
        p6e = hurtbox_frames(["3-4", "5"])
        self.assertIsNone(hurtbox_row(p6e, 0))      # hole -> convert_u -> 0 -> DEFAULT
        self.assertEqual(hurtbox_row(p6e, 2), 0)
        self.assertEqual(hurtbox_row(p6e, 4), 1)
        self.assertIsNone(hurtbox_row(p6e, 5))      # past the end
        self.assertEqual(hurtbox_row(None, 9), 0)

    def test_short_lists_repeat_first(self):
        self.assertEqual(row_values([10, 20], 1), 20)
        self.assertEqual(row_values([10], 3), 10)


class Hit:
    type = 1


class Wall:
    """Ray caster for a vertical wall segment x = 50, y in [lo, hi]."""

    def __init__(self, lo, hi):
        self.lo, self.hi, self.calls = lo, hi, []

    def __call__(self, x, y, dx, dy, fa, fb):
        self.calls.append((x, y, dx, dy, fa, fb))
        if dx == 0 or not min(x, x + dx) <= 50 <= max(x, x + dx):
            return None
        t = (50 - x) / dx
        yy = y + t * dy
        return Hit() if self.lo <= yy <= self.hi else None


class LineOfSight(unittest.TestCase):
    def test_clear(self):
        w = Wall(-10, 10)
        self.assertFalse(line_of_sight_blocked(0, 50, 100, 50, 0, 0, w))
        self.assertEqual(w.calls[0][4:], (3, 11))

    def test_detour_over_a_short_wall(self):
        self.assertFalse(line_of_sight_blocked(0, 0, 100, 0, 0, 0, Wall(-10, 10)))

    def test_tall_wall_blocks(self):
        self.assertTrue(line_of_sight_blocked(0, 0, 100, 0, 0, 40, Wall(-1000, 1000)))

    def test_skip_and_corners(self):
        self.assertFalse(line_of_sight_blocked(0, 0, 100, 0, 0, 0, Wall(-1000, 1000), skip=True))
        self.assertTrue(line_of_sight_blocked(0, 0, 100, 0, 0, 0, Wall(-10, 10), around_corners=False))
        self.assertFalse(line_of_sight_blocked(0, 0, 100, 0, 0, 60, Wall(-10, 10), around_corners=False))

    def test_x28(self):
        self.assertEqual([g for g in range(15) if skips_line_of_sight(g)], [2, 3, 11])


class Rehit(unittest.TestCase):
    def test_record(self):
        r = HitRecord()
        r.set(7, 100, False)
        r.set(7, 200, False)
        self.assertEqual(r.last(7), 100)
        r.set(7, 300, True)
        self.assertEqual(r.last(7), 300)
        self.assertEqual(r.last(8), 0)

    def test_blocked(self):
        r = HitRecord()
        r.set(7, 100, True)
        self.assertFalse(rehit_blocked(None, 7, 0, 500))
        self.assertFalse(rehit_blocked(r, 8, 0, 500))
        self.assertTrue(rehit_blocked(r, 7, 0, 5000))       # once per cast
        self.assertTrue(rehit_blocked(r, 7, 200, 299))
        self.assertFalse(rehit_blocked(r, 7, 200, 300))

    def test_records(self):
        self.assertTrue(records_after_pass(1, False, 0, True))
        self.assertFalse(records_after_pass(1, True, 0, True))
        self.assertTrue(records_after_pass(1, True, 100, True))
        self.assertFalse(records_after_pass(0, False, 0, True))
        self.assertFalse(records_after_pass(1, False, 0, False))

    def test_deals_damage(self):
        self.assertTrue(deals_damage(1, 0, None, 0, 0))
        self.assertFalse(deals_damage(0, 0, None, 0, 1))
        self.assertTrue(deals_damage(0, 0, [0, 5], 1, 0))
        self.assertFalse(deals_damage(0, 0, [0, 5], 0, 1))
        self.assertTrue(deals_damage(0, 0, [0, 5], 2, 1))


@unittest.skipUnless(HAVE_GAME, "Brawlhalla not installed")
class Game(unittest.TestCase):
    def test_pins_hold(self):
        with open(os.path.join(GAME, "BrawlhallaAir.swf"), "rb") as f:
            main = swf.Swf(f.read())
        data = max(main.abc_blocks(), key=lambda b: len(b[1]))[1]
        sha = hashlib.sha256(data).hexdigest()
        if sha != hitdetect.ABC_1100:
            self.skipTest("hit detection anchors are pinned to patch 11.00")
        self.assertEqual(hitdetect.verify(abc.Abc(data), sha), [])


if __name__ == "__main__":
    unittest.main()
