"""Tests of the LevelDesc collision lines and grid (tools/bh/level_collision.py). See docs/hit-detection-11.00.md.

Run: python -I -m unittest discover -s tests   (from the repository root)
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh.hitdetect import line_of_sight_blocked, map_ray  # noqa: E402
from bh.level_collision import Grid, cell_key, cells, curve_lines, element_lines, static_lines  # noqa: E402


class Cells(unittest.TestCase):
    def test_horizontal(self):
        self.assertEqual(cells(10, 10, 250, 10), [(0, 0), (100, 0), (200, 0)])

    def test_vertical(self):
        self.assertEqual(cells(10, 10, 10, 250), [(0, 0), (0, 100), (0, 200)])

    def test_diagonal_down(self):
        self.assertEqual(cells(10, 250, 250, 10), [(0, 200), (0, 100), (100, 100), (100, 0), (200, 0)])

    def test_negative_coordinates(self):
        self.assertEqual(cells(-150, -50, -20, -50), [(-200, -100), (-100, -100)])

    def test_key(self):
        self.assertEqual(cell_key(0, 0), (16000 << 16) | 16000)
        self.assertEqual(cell_key(-100, 200), (15999 << 16) | 16002)


class Elements(unittest.TestCase):
    def test_line_and_swap(self):
        (ln,) = element_lines("HardCollision", ' X1="300" X2="100" Y1="5" Y2="7" Team="2"')
        self.assertEqual((ln.sx, ln.sy, ln.ex, ln.ey, ln.type, ln.owner), (100.0, 7.0, 300.0, 5.0, 1, 2))
        self.assertIsNone(ln.normal)

    def test_x_y_shortcuts_and_pairs(self):
        (ln,) = element_lines("SoftCollision", ' X="50" Y1="0" Y2="80"')
        self.assertEqual((ln.sx, ln.ex, ln.sy, ln.ey, ln.type), (50.0, 50.0, 0.0, 80.0, 2))
        (ln,) = element_lines("HardCollision", ' X1="10" Y1="0" Y2="80"')          # X2 missing: X stays 0
        self.assertEqual((ln.sx, ln.ex), (0.0, 0.0))

    def test_normal(self):
        (ln,) = element_lines("HardCollision", ' X1="0" X2="10" Y="0" NormalY="-3"')
        self.assertEqual(ln.normal, (0.0, -1.0))

    def test_curve(self):
        out = curve_lines((0.0, 0.0), (100.0, 0.0), (50.0, -50.0), 1, 0)
        self.assertEqual(len(out), 4)                     # round(200 / 125) = 2 -> at least 4
        self.assertEqual((out[0].sx, out[-1].ex), (0.0, 100.0))
        self.assertTrue(all(ln.sx <= ln.ex for ln in out))
        self.assertEqual(len(curve_lines((0.0, 0.0), (2000.0, 0.0), (1000.0, -900.0), 1, 0)), 10)

    def test_unknown_and_dynamic(self):
        xml = ('<LevelDesc><HardCollision X1="0" X2="10" Y="0"/><DynamicCollision X="5">'
               '<HardCollision X1="0" X2="10" Y="0"/></DynamicCollision><Foo/></LevelDesc>')
        self.assertEqual(len(static_lines(xml)), 1)


class GridOrder(unittest.TestCase):
    def test_candidates_keep_cell_then_insertion_order(self):
        a = element_lines("HardCollision", ' X1="10" X2="250" Y="10"')[0]
        b = element_lines("HardCollision", ' X1="110" X2="120" Y="20"')[0]
        g = Grid([a, b])
        self.assertEqual(g.candidates(0, 150, 150, 150), [])
        self.assertEqual(g.candidates(0, 10, 150, 10), [a, a, b])      # no de-duplication

    def test_line_of_sight_on_grid(self):
        g = Grid(element_lines("HardCollision", ' X="50" Y1="-1000" Y2="1000"'))
        self.assertTrue(line_of_sight_blocked(0, 0, 100, 0, 0, 40, map_ray(g, 1)))
        self.assertFalse(line_of_sight_blocked(0, 0, 40, 0, 0, 40, map_ray(g, 1)))


if __name__ == "__main__":
    unittest.main()
