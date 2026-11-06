"""Tests of the animation frame table (tools/bh/anim_frames.py). Synthetic values only.
Run: python -I -m unittest discover -s tests"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh.anim_frames import cast_keys, frame_at, frame_table, key_entry, key_frame, key_step  # noqa: E402
from bh.power_data import parse_int  # noqa: E402


def table(keys=None, a2=(), wj=0, rec=0, mod=1.0, gate=False, fixed=0, end=0, start=0, cur=0, keep=False,
          loop=None):
    return frame_table(start, cur, keep, keys, list(a2), wj, rec, mod, gate, fixed, end, loop)


class Keys(unittest.TestCase):
    def test_entry(self):
        e = key_entry(3, 12)
        self.assertEqual((key_step(e), key_frame(e)), (3, 12.0))
        e = key_entry(3, 12, True)
        self.assertEqual((key_step(e), key_frame(e)), (3, 12.99))
        self.assertIsNone(key_entry(-1, 4))
        self.assertIsNone(key_entry(2, 0))

    def test_cast_markers(self):
        keys = cast_keys("3@2,4:2@5-9,6", parse_int)
        self.assertEqual([(key_step(e), key_frame(e)) for e in keys], [(0, 2.0), (1, 5.0), (3, 9.99)])
        self.assertEqual(cast_keys("5,6", parse_int), [])


class Table(unittest.TestCase):
    def test_no_keys(self):
        self.assertEqual(table(end=6), {0: 0, 3: 1})               # 0.384 frames per tick from frame 1

    def test_keys_ramp(self):
        keys = [key_entry(0, 1), key_entry(1, 5)]
        self.assertEqual(table(keys, a2=[3, 2], end=8), {0: 0, 4: 2, 5: 4})

    def test_end_key_keeps_fraction(self):
        keys = [key_entry(0, 1), key_entry(1, 3, True)]
        t = table(keys, a2=[2, 2], end=5)
        self.assertEqual((t[3], t[4]), (1, 2.99))

    def test_key_in_recovery(self):
        keys = [key_entry(0, 1), key_entry(1, 14)]
        # step 1 is past CastTime: 10 recovery ticks + 2 fixed = 12 ticks, from tick 3
        t = table(keys, a2=[2], rec=10, fixed=2, end=15)
        self.assertEqual((t[3], t[14]), (1, 13))         # the ramp ends on key - 1
        t = table(keys, a2=[2], rec=10, mod=1.5, gate=True, fixed=2, end=20)   # floor(15) + 2 = 17 ticks
        self.assertEqual(max(k for k in t if t[k] == 13), 19)

    def test_loop_during_cast(self):
        self.assertEqual(table(wj=10, end=12, loop=(2, 3)), {0: 0, 3: 1, 6: 2, 11: 3})

    def test_recover_mod_slows(self):
        self.assertEqual(table(wj=2, rec=5, mod=2.0, gate=True, end=6), {0: 0, 4: 1})
        self.assertEqual(table(wj=2, rec=5, mod=2.0, gate=False, end=6), {0: 0, 3: 1})

    def test_keep_anim(self):
        t = table(cur=5, keep=True, end=2)                         # starts at 5 + 0.384 + 1
        self.assertEqual(t, {0: 5, 1: 6})

    def test_frame_at(self):
        t = {0: 0, 3: 1}
        self.assertEqual(frame_at(t, 2, 7), 7)
        self.assertEqual(frame_at(t, 3, 7), 1)
        self.assertEqual(frame_at(t, 0, 7), 7)


if __name__ == "__main__":
    unittest.main()
