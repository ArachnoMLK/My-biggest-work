"""Tests of the KO bounds test (tools/bh/ko.py). See docs/ko-11.00.md.

The pure tests pin the branch structure of `ko_mask` (read from #3596) on made-up bounds; no game
values are used. The game test checks the bytecode pins against the installed patch and is skipped
without an install.

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
from bh import abc, ko, swf  # noqa: E402
from bh.ko import BOTTOM, LEFT, RIGHT, TOP, ko_mask  # noqa: E402

GAME = os.environ.get("BRAWLHALLA_DIR", r"C:\Program Files (x86)\Steam\steamapps\common\Brawlhalla")
HAVE_GAME = os.path.exists(os.path.join(GAME, "BrawlhallaAir.swf"))

CAM = (0.0, 0.0, 1000.0, 600.0)  # left, top, right, bottom: made-up, not a real map


def kill(**over):
    k = {"LeftKill": 100, "RightKill": 100, "TopKill": 100, "BottomKill": 100,
         "HardLeftKill": False, "HardRightKill": False, "SoftTopKill": False}
    k.update(over)
    return k


class Mask(unittest.TestCase):
    def test_inside_is_zero(self):
        self.assertEqual(ko_mask(500, 300, CAM, kill(), False, True), 0)

    def test_soft_sides_get_200_more(self):
        # lines at -100 / 1100; not exact -> -300 / 1300
        self.assertEqual(ko_mask(-250, 300, CAM, kill(), False, False), 0)
        self.assertEqual(ko_mask(-301, 300, CAM, kill(), False, False), LEFT)
        self.assertEqual(ko_mask(1301, 300, CAM, kill(), False, False), RIGHT)
        self.assertEqual(ko_mask(-101, 300, CAM, kill(), True, False), LEFT)
        self.assertEqual(ko_mask(1101, 300, CAM, kill(), True, False), RIGHT)

    def test_hard_side_has_no_margin(self):
        self.assertEqual(ko_mask(-101, 300, CAM, kill(HardLeftKill=True), False, False), LEFT)
        self.assertEqual(ko_mask(1101, 300, CAM, kill(HardLeftKill=True), False, False), 0)
        self.assertEqual(ko_mask(1101, 300, CAM, kill(HardRightKill=True), False, False), RIGHT)

    def test_lines_are_strict(self):
        self.assertEqual(ko_mask(-100, 300, CAM, kill(), True, False), 0)
        self.assertEqual(ko_mask(500, 700, CAM, kill(), True, False), 0)
        self.assertEqual(ko_mask(500, -100, CAM, kill(), True, False), 0)

    def test_bottom_has_no_margin_and_combines_with_a_side(self):
        self.assertEqual(ko_mask(500, 700.5, CAM, kill(), False, False), BOTTOM)
        self.assertEqual(ko_mask(-400, 800, CAM, kill(), False, False), LEFT | BOTTOM)

    def test_top_needs_exact_or_top_allowed(self):
        self.assertEqual(ko_mask(500, -150, CAM, kill(), False, False), 0)
        self.assertEqual(ko_mask(500, -150, CAM, kill(), True, False), TOP)
        self.assertEqual(ko_mask(500, -150, CAM, kill(), False, True), TOP)

    def test_top_returns_early(self):
        # past the top and the left line: only TOP, as #3596 returns 1 before the side tests
        self.assertEqual(ko_mask(-5000, -150, CAM, kill(), True, False), TOP)

    def test_soft_top_kill_adds_a_far_top_line(self):
        self.assertEqual(ko_mask(500, -301, CAM, kill(SoftTopKill=True), False, False), TOP)
        self.assertEqual(ko_mask(500, -299, CAM, kill(SoftTopKill=True), False, False), 0)
        self.assertEqual(ko_mask(500, -301, CAM, kill(), False, False), 0)

    def test_left_wins_over_right(self):
        # unreachable with sane bounds, but #3596 tests right only in the else branch
        k = kill(LeftKill=0, RightKill=0, HardLeftKill=True, HardRightKill=True)
        self.assertEqual(ko_mask(500, 300, (600.0, 0.0, 400.0, 600.0), k, False, False), LEFT)


class Cli(unittest.TestCase):
    def test_wrong_patch_exits_2(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "other.abc")
            with open(p, "wb") as f:
                f.write(b"not the pinned abc")
            out = subprocess.run([sys.executable, "-I", os.path.join(ROOT, "tools", "bht.py"), "ko-verify", "--abc", p],
                                 capture_output=True, text=True)
        self.assertEqual(out.returncode, 2, out.stderr)
        self.assertIn("no KO anchors", out.stdout)


@unittest.skipUnless(HAVE_GAME, "Brawlhalla not installed")
class Game(unittest.TestCase):
    def test_pins_hold(self):
        with open(os.path.join(GAME, "BrawlhallaAir.swf"), "rb") as f:
            main = swf.Swf(f.read())
        data = max(main.abc_blocks(), key=lambda b: len(b[1]))[1]
        sha = hashlib.sha256(data).hexdigest()
        if sha != ko.ABC_1100:
            self.skipTest("KO anchors are pinned to patch 11.00")
        self.assertEqual(ko.verify(abc.Abc(data), sha), [])


if __name__ == "__main__":
    unittest.main()
