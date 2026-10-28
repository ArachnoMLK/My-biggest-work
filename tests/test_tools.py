"""Self-tests. Tests that need the game or replays are skipped when they are not installed.

Run: python -I -m unittest discover -s tests   (from the repository root)
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh import abc, replay, swf, swz  # noqa: E402

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

    def test_decode_branches(self):
        code = bytes([0x10, 0x00, 0x00, 0x00, 0x47])  # jump +0 ; returnvoid
        ins = abc.decode(code)
        self.assertEqual([n for _, n, _ in ins], ["jump", "returnvoid"])
        self.assertEqual(abc.branch_targets(ins, len(code)), ([4], []))


@unittest.skipUnless(HAVE_GAME, "Brawlhalla not installed")
class Game(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        main = swf.Swf(open(os.path.join(GAME, "BrawlhallaAir.swf"), "rb").read())
        cls.abc = abc.Abc(max(main.abc_blocks(), key=lambda b: len(b[1]))[1])

    def test_every_method_decodes(self):
        rep = abc.validate(self.abc)
        self.assertEqual(rep["errors"], [])
        self.assertEqual(rep["bad_branches"], 0)

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
