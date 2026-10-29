"""Self-tests. Tests that need the game or replays are skipped when they are not installed.

Run: python -I -m unittest discover -s tests   (from the repository root)
"""
import hashlib
import os
import sys
import unittest
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh import abc, movement, render, replay, swf, swz  # noqa: E402

GAME = os.environ.get("BRAWLHALLA_DIR", r"C:\Program Files (x86)\Steam\steamapps\common\Brawlhalla")
REPLAYS = os.environ.get("BRAWLHALLA_REPLAYS", os.path.join(os.path.expanduser("~"), "BrawlhallaReplays"))
HAVE_GAME = os.path.exists(os.path.join(GAME, "BrawlhallaAir.swf"))
HAVE_REPLAYS = os.path.isdir(REPLAYS) and any(f.endswith(".replay") for f in os.listdir(REPLAYS))
SAMPLE = 20  # supported replays parsed by the integration test


def read(path):
    with open(path, "rb") as fh:
        return fh.read()


def replay_version(raw):
    """Format number of a .replay (first u32 of the decoded stream), inflating only 4 bytes."""
    head = zlib.decompressobj().decompress(raw, 4)
    if len(head) < 4:
        raise replay.FormatError("replay shorter than its version field")
    return int.from_bytes(bytes(b ^ k for b, k in zip(head, replay.KEY)), "big")


def supported_sample(items, limit=SAMPLE):
    """Take the first `limit` (name, raw) items whose format is in replay.PATCHES.

    Returns (picked, skipped) where skipped counts the unsupported formats seen on the way.
    Supported files are returned whatever their content: parse errors must still fail the test.
    """
    picked, skipped = [], {}
    for name, raw in items:
        if len(picked) >= limit:
            break
        v = replay_version(raw)
        if v in replay.PATCHES:
            picked.append((name, raw))
        else:
            skipped[v] = skipped.get(v, 0) + 1
    return picked, skipped


def replay_files(folder):
    """(name, raw) of every .replay of a folder, last name first (lazy, one file open at a time)."""
    for f in sorted((f for f in os.listdir(folder) if f.endswith(".replay")), reverse=True):
        yield f, read(os.path.join(folder, f))


def fake_replay(version, payload=b""):
    """Synthetic encoded stream: version u32 + payload, XOR-keyed and zlib-compressed. No game content."""
    plain = version.to_bytes(4, "big") + payload
    return zlib.compress(bytes(b ^ replay.KEY[i & 63] for i, b in enumerate(plain)))


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

    def test_replay_version_matches_parser_reader(self):
        raw = fake_replay(271, bytes(range(40)))
        self.assertEqual(replay_version(raw), 271)
        self.assertEqual(replay.BitReader(replay.decode_bytes(raw)).u32(), 271)

    def test_sample_mixed_formats(self):
        items = [(f"r{i}", fake_replay(v)) for i, v in enumerate([257, 271, 300, 265, 248, 271])]
        picked, skipped = supported_sample(items, limit=2)
        self.assertEqual([n for n, _ in picked], ["r1", "r3"])
        self.assertEqual(skipped, {257: 1, 300: 1})  # stops once the sample is full

    def test_sample_unsupported_only(self):
        picked, skipped = supported_sample([("a", fake_replay(257)), ("b", fake_replay(257)), ("c", fake_replay(260))])
        self.assertEqual((picked, skipped), ([], {257: 2, 260: 1}))

    def test_sampled_supported_replay_still_fails_to_parse(self):
        picked, _ = supported_sample([("broken", fake_replay(271))])
        self.assertEqual(len(picked), 1)  # selection does not hide a broken supported file
        with self.assertRaises((EOFError, replay.FormatError)):
            replay.parse(picked[0][1])


@unittest.skipUnless(HAVE_GAME, "Brawlhalla not installed")
class Game(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        main = swf.Swf(read(os.path.join(GAME, "BrawlhallaAir.swf")))
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
        data = read(os.path.join(GAME, "Init.swz"))
        key = swz.find_key(data, candidates=self.abc.uints[1:])
        self.assertIsNotNone(key)
        self.assertGreater(len(list(swz.iter_entries(data, key))), 0)


@unittest.skipUnless(HAVE_REPLAYS, "no replay folder")
class Replays(unittest.TestCase):
    def test_some_replays_parse(self):
        # Only formats of replay.PATCHES are supported; older ones in the folder are not sampled.
        picked, skipped = supported_sample(replay_files(REPLAYS))
        if not picked:
            self.skipTest(f"no replay in supported formats {min(replay.PATCHES)}-{max(replay.PATCHES)}; "
                          f"unsupported formats seen: {dict(sorted(skipped.items()))}")
        for i, (_, raw) in enumerate(picked):
            with self.subTest(sample=i, version=replay_version(raw)):  # no file names: they hold player names
                rep = replay.parse(raw)
                self.assertIn(rep["version"], replay.PATCHES)
                for lst in rep["inputs"].values():
                    self.assertTrue(all(ts % 16 == 0 for ts, _ in lst))


if __name__ == "__main__":
    unittest.main()
