"""Tests of the static PRNG draw-order evidence (tools/bh/prng_order.py). See docs/prng-order-11.00.md.

The pure tests feed `verify` a stub ABC/lister to prove that a changed operand, a missing method, a new
referencing method, a changed slot type and an unpinned hash are all reported. The game test checks the
pins against the installed patch and is skipped without an install.

Run: python -I -m unittest discover -s tests   (from the repository root)
"""
import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh import abc, prng_order, swf  # noqa: E402

GAME = os.environ.get("BRAWLHALLA_DIR", r"C:\Program Files (x86)\Steam\steamapps\common\Brawlhalla")
HAVE_GAME = os.path.exists(os.path.join(GAME, "BrawlhallaAir.swf"))
SHA = prng_order.ABC_1100


def pinned_listings():
    """{method: {offset: (op, text)}} holding exactly the pinned anchors (what a matching ABC would show)."""
    out = {}
    for anchors in prng_order.ANCHORS[SHA].values():
        for m, off, op, text in anchors:
            out.setdefault(m, {})[off] = (op, text)
    return out


class Stubbed(unittest.TestCase):
    """verify() with listing/referencing/slot_type replaced, so no game bytes are needed."""

    def run_verify(self, listings, refs=None, slots=None):
        refs = refs if refs is not None else {k: set(v) for k, v in prng_order.REFERENCES[SHA].items()}
        slot_map = slots if slots is not None else {(c, s): t for c, s, t in prng_order.SLOTS[SHA]}
        with patch.object(prng_order, "listing", lambda _abc, m: listings.get(m, {})), \
                patch.object(prng_order, "referencing", lambda _abc, names: {n: refs.get(n, set()) for n in names}), \
                patch.object(prng_order, "slot_type", lambda _abc, c, s: slot_map.get((c, s))):
            return prng_order.verify(None, SHA)

    def test_all_pins_hold(self):
        self.assertEqual(self.run_verify(pinned_listings()), [])

    def test_changed_operand_is_reported(self):
        lists = pinned_listings()
        lists[13733][433] = ("callproperty", "_-X9z, 0")  # draw replaced by another call
        bad = self.run_verify(lists)
        self.assertEqual(len(bad), 1)
        self.assertIn("#13733 @433", bad[0])
        self.assertIn("_-X9z", bad[0])

    def test_changed_opcode_is_reported(self):
        lists = pinned_listings()
        lists[3624][119] = ("pushint", "2048")  # replay start no longer sets 1024
        self.assertTrue(any("#3624 @119" in line for line in self.run_verify(lists)))

    def test_missing_method_reports_every_anchor(self):
        lists = pinned_listings()
        n = len(lists.pop(5809))
        bad = self.run_verify(lists)
        self.assertEqual(len(bad), n)
        self.assertTrue(all("#5809" in line and "found None" in line for line in bad))

    def test_new_reference_is_reported(self):
        refs = {k: set(v) for k, v in prng_order.REFERENCES[SHA].items()}
        refs["_-Y15"].add(3336)  # e.g. the taunt pick moved into the scheduler
        bad = self.run_verify(pinned_listings(), refs=refs)
        self.assertEqual(bad, ["references of _-Y15: want [10946], found [3336, 10946]"])

    def test_changed_slot_type_is_reported(self):
        slots = {(c, s): t for c, s, t in prng_order.SLOTS[SHA]}
        slots[("_-h3U", "_-O4t")] = "_-99"
        self.assertEqual(self.run_verify(pinned_listings(), slots=slots),
                         ["slot _-h3U._-O4t: want _-z1C, found _-99"])

    def test_unpinned_hash_is_rejected(self):
        self.assertIsNone(prng_order.verify(None, "0" * 64))


class Cli(unittest.TestCase):
    def test_wrong_patch_exits_2(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "other.abc")
            with open(p, "wb") as f:
                f.write(b"not the pinned abc")
            out = subprocess.run([sys.executable, "-I", os.path.join(ROOT, "tools", "bht.py"),
                                  "prng-order-verify", "--abc", p], capture_output=True, text=True)
        self.assertEqual(out.returncode, 2, out.stderr)
        self.assertIn("no draw-order anchors", out.stdout)


@unittest.skipUnless(HAVE_GAME, "Brawlhalla not installed")
class Game(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(GAME, "BrawlhallaAir.swf"), "rb") as f:
            main = swf.Swf(f.read())
        data = max(main.abc_blocks(), key=lambda b: len(b[1]))[1]
        cls.sha = hashlib.sha256(data).hexdigest()
        cls.abc = abc.Abc(data)

    def test_pins_hold(self):
        if self.sha != SHA:
            self.skipTest("draw-order anchors are pinned to patch 11.00")
        self.assertEqual(prng_order.verify(self.abc, self.sha), [])

    def test_one_pass_references_match_callers_of(self):
        names = {"_-44D", "_-Y15", "_-O3d"}
        got = prng_order.referencing(self.abc, names)
        for n in names:
            self.assertEqual(got[n], set(abc.callers_of(self.abc, n)), n)


if __name__ == "__main__":
    unittest.main()
