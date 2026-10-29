"""Tests of the movement-step evidence (tools/bh/step.py). See docs/entity-step-11.00.md.

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
from bh import abc, step, swf  # noqa: E402
from bh.step import clamp, fold_impulse, speed_cap  # noqa: E402

GAME = os.environ.get("BRAWLHALLA_DIR", r"C:\Program Files (x86)\Steam\steamapps\common\Brawlhalla")
HAVE_GAME = os.path.exists(os.path.join(GAME, "BrawlhallaAir.swf"))


class SpeedCap(unittest.TestCase):
    def test_cap_values(self):
        self.assertEqual(speed_cap(), 1000.0)
        self.assertEqual(speed_cap(power_active=True), 3000.0)
        self.assertEqual(speed_cap(flags=524288), 1000.0 / 3)
        self.assertEqual(speed_cap(True, 524288 | 1), 1000.0)

    def test_clamp(self):
        self.assertEqual(clamp(1200.0, 1000.0), 1000.0)
        self.assertEqual(clamp(-1200.0, 1000.0), -1000.0)
        self.assertEqual(clamp(1000.0, 1000.0), 1000.0)


class Fold(unittest.TestCase):
    def test_zero_impulse_keeps_velocity(self):
        self.assertEqual(fold_impulse(300.0, 0.0), (300.0, None))  # no cap without an impulse

    def test_impulse_adds(self):
        self.assertEqual(fold_impulse(0.0, -57.0), (-57.0, None))  # grounded jump after P5S = 0
        self.assertEqual(fold_impulse(10.0, -57.0), (-47.0, None))

    def test_cap_is_250_with_sign_and_overshoot(self):
        self.assertEqual(fold_impulse(100.0, 200.0), (250.0, 300.0))
        self.assertEqual(fold_impulse(-100.0, -200.0), (-250.0, -300.0))

    def test_exactly_250_is_not_capped(self):
        self.assertEqual(fold_impulse(50.0, 200.0), (250.0, None))  # ifngt: s*s > 62500 is strict


class Cli(unittest.TestCase):
    def test_wrong_patch_exits_2(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "other.abc")
            with open(p, "wb") as f:
                f.write(b"not the pinned abc")
            out = subprocess.run([sys.executable, "-I", os.path.join(ROOT, "tools", "bht.py"), "step-verify", "--abc", p],
                                 capture_output=True, text=True)
        self.assertEqual(out.returncode, 2, out.stderr)
        self.assertIn("no step anchors", out.stdout)


@unittest.skipUnless(HAVE_GAME, "Brawlhalla not installed")
class Game(unittest.TestCase):
    def test_pins_hold(self):
        with open(os.path.join(GAME, "BrawlhallaAir.swf"), "rb") as f:
            main = swf.Swf(f.read())
        data = max(main.abc_blocks(), key=lambda b: len(b[1]))[1]
        sha = hashlib.sha256(data).hexdigest()
        if sha != step.ABC_1100:
            self.skipTest("step anchors are pinned to patch 11.00")
        self.assertEqual(step.verify(abc.Abc(data), sha), [])


if __name__ == "__main__":
    unittest.main()
