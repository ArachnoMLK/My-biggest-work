"""Self-tests. Tests that need the game or replays are skipped when they are not installed.

Run: python -I -m unittest discover -s tests   (from the repository root)
"""
import hashlib
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh import abc, movement, render, replay, swf, swz  # noqa: E402

GAME = os.environ.get("BRAWLHALLA_DIR", r"C:\Program Files (x86)\Steam\steamapps\common\Brawlhalla")
REPLAYS = os.environ.get("BRAWLHALLA_REPLAYS", os.path.join(os.path.expanduser("~"), "BrawlhallaReplays"))
HAVE_GAME = os.path.exists(os.path.join(GAME, "BrawlhallaAir.swf"))
HAVE_REPLAYS = os.path.isdir(REPLAYS) and any(f.endswith(".replay") for f in os.listdir(REPLAYS))


class Pure(unittest.TestCase):
    def test_prng_is_deterministic(self):
        a, b = swz.SwzRandom(1234), swz.SwzRandom(1234)
        self.assertEqual([a.next() for _ in range(50)], [b.next() for _ in range(50)])

    def test_bitreader(self):
        r = replay.BitReader(bytes([0b10110000, 0xFF]))
        self.assertEqual((r.bit(), r.bits(3), r.bits(4), r.bits(8)), (1, 0b011, 0, 0xFF))

    def test_presses_are_rising_edges(self):
        recs = [(0, 0), (16, 1 << 4), (32, 1 << 4), (48, 0), (64, 1 << 4)]
        self.assertEqual(render.presses(recs, (4,)), [16, 64])

    def test_decode_branches(self):
        code = bytes([0x10, 0x00, 0x00, 0x00, 0x47])  # jump +0 ; returnvoid
        ins = abc.decode(code)
        self.assertEqual([n for _, n, _ in ins], ["jump", "returnvoid"])
        self.assertEqual(abc.branch_targets(ins, len(code)), ([4], []))

    def test_anchor_check_reports_mismatches(self):
        lists = {1: {0: ("pushbyte", "16"), 2: ("add", "")}}
        good, wrong = (1, 0, "pushbyte", "16"), (1, 2, "subtract", "")
        self.assertEqual(movement.check([good, wrong, (9, 0, "add", "")], lambda m: lists.get(m, {})),
                         [(wrong, ("add", "")), ((9, 0, "add", ""), None)])


@unittest.skipUnless(HAVE_GAME, "Brawlhalla not installed")
class Game(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        main = swf.Swf(open(os.path.join(GAME, "BrawlhallaAir.swf"), "rb").read())
        cls.abc_bytes = max(main.abc_blocks(), key=lambda b: len(b[1]))[1]
        cls.abc = abc.Abc(cls.abc_bytes)

    def test_every_method_decodes(self):
        rep = abc.validate(self.abc)
        self.assertEqual(rep["errors"], [])
        self.assertEqual(rep["bad_branches"], 0)

    def test_member_refs_agree_with_callers(self):
        m = next(b["method"] for b in self.abc.bodies if len(b["code"]) > 40)
        refs = abc.member_refs(self.abc, m)
        self.assertTrue(refs["members"])
        (_, full), _ = next(iter(refs["members"].items()))
        short = full.rsplit("::", 1)[-1].rsplit(".", 1)[-1]
        self.assertIn(m, abc.callers_of(self.abc, short))

    def test_movement_anchors_hold(self):
        anchors = movement.ANCHORS.get(hashlib.sha256(self.abc_bytes).hexdigest())
        if anchors is None:
            self.skipTest("no movement anchors for this patch")
        self.assertEqual(movement.check(anchors, lambda m: movement.listing(self.abc, m)), [])

    def test_swz_key_is_in_uint_pool(self):
        data = open(os.path.join(GAME, "Init.swz"), "rb").read()
        key = swz.find_key(data, candidates=self.abc.uints[1:])
        self.assertIsNotNone(key)
        self.assertGreater(len(list(swz.iter_entries(data, key))), 0)


@unittest.skipUnless(HAVE_REPLAYS, "no replay folder")
class Replays(unittest.TestCase):
    def test_some_replays_parse(self):
        files = sorted(f for f in os.listdir(REPLAYS) if f.endswith(".replay"))[-20:]
        for f in files:
            rep = replay.parse(open(os.path.join(REPLAYS, f), "rb").read())
            self.assertIn(rep["version"], replay.PATCHES)
            for lst in rep["inputs"].values():
                self.assertTrue(all(ts % 16 == 0 for ts, _ in lst))


if __name__ == "__main__":
    unittest.main()
