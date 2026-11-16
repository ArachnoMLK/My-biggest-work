"""Tests of the moving platform transcription (tools/bh/platforms.py). See docs/hit-detection-11.00.md, 7.3.

Run: python -I -m unittest discover -s tests   (from the repository root)
"""
import os
import sys
import unittest
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh.platforms import (PI1_2, KeyFrame, bind, cos_r, dynamic_lines, ease, frame_at, frame_points, move,  # noqa: E402
                          parse_platforms, position, sin_r, walk)


class Ease(unittest.TestCase):
    def test_quadratic(self):
        self.assertEqual(ease(True, False, 2, 1, 2), 0.25)
        self.assertEqual(ease(False, True, 2, 1, 2), 0.75)
        self.assertEqual(ease(True, True, 2, 1, 4), 0.125)
        self.assertEqual(ease(True, True, 2, 3, 4), 0.875)

    def test_cubic_out(self):
        self.assertAlmostEqual(ease(False, True, 3, 1, 2), 1 - 0.5 ** 3)

    def test_rounded_trig(self):
        self.assertEqual(cos_r(0), 1.0)
        self.assertEqual(sin_r(PI1_2), 1.0)
        self.assertEqual(cos_r(PI1_2), 0.0)


class Frames(unittest.TestCase):
    def test_linear_and_wrap(self):
        pts, origins, _, _ = frame_points([KeyFrame(0, 0, 1), KeyFrame(100, 0, 5)], 8, 10, 0)
        self.assertEqual([p[0] for p in pts], [10, 35, 60, 85, 110, 85, 60, 35])
        self.assertEqual(origins[1], (25.0, 0.0))

    def test_phase_hold(self):
        anim = ET.fromstring('<Animation><KeyFrame FrameNum="1" X="0" Y="0"/><Phase StartFrame="10">'
                             '<KeyFrame FrameNum="5" X="50" Y="0"/></Phase></Animation>')
        out = []
        for child in anim:
            walk(child, out, False, 0.0, 0.0, False, False, 2)
        self.assertEqual([(k.frame, k.x) for k in out], [(1, 0.0), (10, 0.0), (15, 50.0)])

    def test_time_to_frame(self):
        self.assertAlmostEqual(frame_at(1000, 8, 0, 1.0), 3.0)
        self.assertAlmostEqual(frame_at(1000 + 500, 8, 0, 1.0, match_start=500), 3.0)
        pts = [(float(i), 0.0) for i in range(8)]
        self.assertEqual(position(pts, 3.0), (3.0, 0.0))
        self.assertEqual(position(pts, 7.5), (3.5, 0.0))            # 7 -> 0 wraps


class Level(unittest.TestCase):
    XML = ('<LevelDesc NumFrames="8"><MovingPlatform PlatID="1" X="10" Y="0"><Animation>'
           '<KeyFrame FrameNum="1" X="0" Y="0"/><KeyFrame FrameNum="5" X="100" Y="0"/></Animation></MovingPlatform>'
           '<DynamicCollision PlatID="1" X="10" Y="5"><HardCollision X1="0" X2="20" Y="0"/></DynamicCollision>'
           '</LevelDesc>')

    def test_platform_and_lines(self):
        (p,) = parse_platforms(self.XML)
        self.assertEqual(len(p.points), 8)
        lines = dynamic_lines(self.XML)["1"]
        self.assertEqual((lines[0].sx, lines[0].ex, lines[0].sy), (10.0, 30.0, 5.0))
        bind(lines, p.points[0])
        move(lines, p.points[4])                                     # platform at x = 110
        self.assertEqual((lines[0].sx, lines[0].ex, lines[0].x1h), (110.0, 130.0, 10.0))

    def test_missing_space_between_attributes(self):
        (p,) = parse_platforms(self.XML.replace('PlatID="1" X="10"', 'PlatID="1"X="10"'))
        self.assertEqual(p.points[0], (10.0, 0.0))


class Carry(unittest.TestCase):
    def test_clamp(self):
        from bh.platforms import clamp
        self.assertEqual((clamp(0, 10, 5), clamp(0, 10, -1), clamp(10, 0, 11), clamp(10, 0, 3)), (5, 0, 10, 3))

    def test_offset_of_moved_lines(self):
        from bh.platforms import bind, carry_offset, move
        from bh.raycast import Line
        floor = Line(0.0, 100.0, 50.0, 100.0, 1, (0.0, -1.0))
        wall = Line(50.0, 100.0, 50.0, 150.0, 1, (1.0, 0.0))
        static = Line(0.0, 0.0, 9.0, 0.0, 1, (0.0, -1.0))
        bind([floor, wall], (0.0, 0.0))
        move([floor, wall], (3.0, -2.0))
        self.assertEqual(carry_offset([floor]), (3.0, -2.0))
        self.assertEqual(carry_offset([wall]), (3.0, 0.0))          # vertical: no y part
        self.assertEqual(carry_offset([static, None]), (0.0, 0.0))  # not dynamic
        self.assertEqual(carry_offset([floor], conveyor=lambda ln: (7.0, 0.0)), (7.0, 0.0))

    def test_carry_stops_at_a_wall(self):
        from bh.platforms import carry
        from bh.raycast import Line
        wall = Line(10.0, -200.0, 10.0, 50.0, 1, (-1.0, 0.0))
        self.assertEqual(carry(lambda *a: [], 0, 0.0, 0.0, (4.0, 0.0), None), (4.0, 0.0))
        x, y = carry(lambda *a: [wall], 0, 0.0, 0.0, (20.0, 0.0), None)
        self.assertAlmostEqual(x, 10.0 - 1.01)
        self.assertEqual(y, 0.0)

if __name__ == "__main__":
    unittest.main()
