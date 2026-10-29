"""Moving platforms on patch 11.00: key frames -> one position per frame -> position at time t -> dynamic lines.

See docs/hit-detection-11.00.md, section 7.3. Transcribes `_-139._-Jb` #5298 (key frame walk, Phases),
`_-A2j.static._-71C` #6032 / `_-A2j._-yo` #6031 (key frames), `_-139._-Y61` #5299 (per-frame points),
`_-A6B._-D2g` #1131 (easing), `_-A6B._-K6l` / `_-b4l` #1094 / #1093 (rounded cos / sin),
`MovingPlatform._-V39` / `_-I4v` #6016 / #6018 (time -> frame -> position), `MovingPlatform._-D19` #6027
and `_-Y3I` #6014 (lines follow the platform). Arithmetic in bytecode order. Static evidence only.
"""
import math
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from .level_collision import as3_round, element_lines
from .movement import ABC_1100, check, listing

PI2, PI1_2, PI3_2 = math.pi * 2, math.pi * 0.5, math.pi * 1.5   # `_-y2E.init` #15351 @11998-12050
DEFAULT_EASE_POWER = 2                                         # `_-139._-N1f`


@dataclass
class KeyFrame:
    """`_-A2j(x, y, _-C6A frame, rotation, _-JO has centre, _-M5g cx, _-z4Z cy, _-C60 ease in, _-Z4j ease out,
    _-o2m power, _-Qp respawn off)` (#6029)."""
    x: float
    y: float
    frame: int
    rotation: float = 0.0
    has_center: bool = False
    cx: float = 0.0
    cy: float = 0.0
    ease_in: bool = False
    ease_out: bool = False
    power: int = DEFAULT_EASE_POWER
    respawn_off: bool = False

    def hold(self, frame):
        """`_-yo(f)` #6031: same x, y, rotation at frame f (f == -1 keeps the frame); no centre, no easing."""
        return KeyFrame(self.x, self.y, self.frame if frame == -1 else frame, self.rotation)


def _f(node, name, default):
    v = node.get(name)
    return float(v) if v is not None else default


def _b(node, name, default):
    v = node.get(name)
    return v.upper() == "TRUE" if v is not None else default


def key_frame(node, has_center, cx, cy, ease_in, ease_out, power, frame_offset):
    """`_-71C` #6032: one KeyFrame element; missing attributes take the enclosing defaults.
    The frame is FrameNum (default 0) + frame_offset; a CenterX or CenterY turns the centre on."""
    frame = int(node.get("FrameNum", "0")) + frame_offset
    has_c = has_center or node.get("CenterX") is not None or node.get("CenterY") is not None
    return KeyFrame(_f(node, "X", 0.0), _f(node, "Y", 0.0), frame, _f(node, "Rotation", 0.0), has_c,
                    _f(node, "CenterX", cx), _f(node, "CenterY", cy), _b(node, "EaseIn", ease_in),
                    _b(node, "EaseOut", ease_out), int(node.get("EasePower", power)), _b(node, "RespawnOff", False))


def walk(node, out, has_center, cx, cy, ease_in, ease_out, power, phase_start=0, index=0):
    """`_-Jb` #5298. A KeyFrame is appended; the first key frame of a Phase with StartFrame > 0, when it starts
    later than the Phase and the previous key frame differs (x, y or rotation), is preceded by a hold of the
    previous one at the Phase start. A Phase walks its children with phase_start = its StartFrame (default 0)."""
    if node.tag == "KeyFrame":
        kf = key_frame(node, has_center, cx, cy, ease_in, ease_out, power, phase_start)
        if phase_start > 0 and index == 0 and kf.frame > phase_start and out:
            last = out[-1]
            if last.x != kf.x or last.y != kf.y or last.rotation != kf.rotation:
                out.append(last.hold(phase_start))
        out.append(kf)
    elif node.tag == "Phase":
        start = int(node.get("StartFrame", "0"))
        for i, child in enumerate(node):
            walk(child, out, has_center, cx, cy, ease_in, ease_out, power, start, i)


def ease(ease_in, ease_out, power, num, den):
    """`_-A6B._-D2g` #1131: eased progress of frame `num` out of `den`."""
    both = ease_in and ease_out
    t = num / (den / 2 if both else den)
    s = 0 if power == 2 else 1
    k = 1.0
    if both:
        s += 1
        ease_in = t < 1
        k = 0.5
    if ease_in:
        t = math.pow(t, power)
    elif ease_out:
        if power == 2:
            t = (t - s) * (t - s - 2) - s
        elif power > 2:
            t = ((power & 1) << s) + math.pow(t - s, power) - s
        if power & 1 == 0:
            k = -k
    return k * t


def _round_trig(fn, a):
    """`_-K6l` / `_-b4l`: angle reduced to [0, 2 pi), rounded to 1/1000, then cos / sin rounded to 1/1000."""
    r = a - math.floor(a / PI2) * PI2
    r = as3_round(r * 1000.0) / 1000.0
    return as3_round(fn(r) * 1000.0) / 1000.0


def cos_r(a):
    return _round_trig(math.cos, a)


def sin_r(a):
    return _round_trig(math.sin, a)


def _axis_angle(x, y, cx, cy):
    """#5299 @862-904: the angle of a key frame around the centre, only on the axes."""
    if x == cx:
        return PI1_2 if y > cy else PI3_2
    return math.pi if x < cx else 0


def frame_points(kfs, num_frames, off_x, off_y):
    """`_-Y61` #5299 @571-1494: (points `_-M4l`, origins `_-w2m`, rotations `_-o2k`, respawn-off `_-P1K`).

    Frames run from 1. Key frame i covers frames up to the next key frame's frame (the last one wraps to the
    first, up to num_frames + 1). Linear or eased progress; with a centre, an arc on the axes of the centre
    with radii |x0 - x1| and |y0 - y1|. Coordinates are rounded to 1/100; points add the platform offset.
    """
    pts, origins, rots, off = [], [], [], []
    cx = cy = 0.0
    f = 1
    n = len(kfs)
    for i, kf in enumerate(kfs):
        if kf.has_center:
            cx, cy = kf.cx, kf.cy
        if i == n - 1:
            nxt, end = kfs[0], num_frames + 1
        else:
            nxt = kfs[i + 1]
            end = nxt.frame
        a0 = a1 = 0
        if kf.has_center:
            a0 = _axis_angle(kf.x, kf.y, cx, cy)
            if nxt.x == cx:
                a1 = PI1_2 if nxt.y > cy else PI3_2
            elif nxt.x < cx:
                a1 = math.pi
            else:
                a1 = PI2 if a0 == PI3_2 else 0
            if a0 == 0 and a1 == PI3_2:
                a0 = PI2
        off_x = as3_round(off_x * 100.0) / 100.0
        off_y = as3_round(off_y * 100.0) / 100.0
        while f < end:
            if not kf.ease_in and not kf.ease_out:
                e = (f - kf.frame) / (end - kf.frame)
            else:
                e = ease(kf.ease_in, kf.ease_out, kf.power, f - kf.frame, end - kf.frame)
            r = 1 - e
            if kf.has_center:
                ang = a0 * r + a1 * e
                px = as3_round((cx + abs(kf.x - nxt.x) * cos_r(ang)) * 100.0) / 100.0
                py = as3_round((cy + abs(kf.y - nxt.y) * sin_r(ang)) * 100.0) / 100.0
            else:
                px = as3_round((kf.x * r + nxt.x * e) * 100.0) / 100.0
                py = as3_round((kf.y * r + nxt.y * e) * 100.0) / 100.0
            pts.append((px + off_x, py + off_y))
            origins.append((px, py))
            rots.append(kf.rotation * (1 - e) + nxt.rotation * e)
            off.append(kf.respawn_off)
            f += 1
    return pts, origins, rots, off


def frame_at(t, n, start_frame, slow_mult, match_start=0):
    """`MovingPlatform._-V39` #6016: fractional frame at time t (ms); match_start = `_-N1k._-n4k`."""
    tt = t - match_start if t >= match_start else t
    period = 1000 * (n / 60) * slow_mult
    m = math.fmod(tt * 0.05, period)
    return start_frame + m / period * n


def position(points, frame):
    """`MovingPlatform._-I4v` #6018: linear blend between point k and k + 1 (both modulo the count)."""
    k = math.floor(frame + 1e-07)
    p1 = points[(k + 1) % len(points)]
    p2 = points[k % len(points)]
    a = frame - k
    return p1[0] * a + p2[0] * (1 - a), p1[1] * a + p2[1] * (1 - a)


@dataclass
class Platform:
    plat_id: str
    points: list
    start_frame: int
    slow_mult: float

    def at(self, t, match_start=0):
        return position(self.points, frame_at(t, len(self.points), self.start_frame, self.slow_mult, match_start))


def parse_platforms(xml):
    """Every MovingPlatform of a LevelDesc: Animation key frames expanded to per-frame points.

    Defaults come from the LevelDesc root (NumFrames, default 0; SlowMult, default 1.0) and the Animation
    (CenterX / CenterY / EaseIn / EaseOut / EasePower). The platform offset is its X / Y [H: the sprite position
    that `MovingPlatform.<init>` passes to `_-Y61`]. Phase / KeyFrame order is file order.
    """
    root = ET.fromstring(re.sub(r'(="[^"]*")(?=[A-Za-z_])', lambda m: m.group(1) + ' ', xml))   # some files miss the space between attributes
    lv_frames = int(root.get("NumFrames", "0"))
    lv_slow = float(root.get("SlowMult", "1.0"))
    out = []
    for mp in root.iter("MovingPlatform"):
        anim = mp.find("Animation")
        if anim is None:
            continue
        has_c = anim.get("CenterX") is not None or anim.get("CenterY") is not None
        kfs = []
        for child in anim:
            walk(child, kfs, has_c, _f(anim, "CenterX", 0.0), _f(anim, "CenterY", 0.0), _b(anim, "EaseIn", False),
                 _b(anim, "EaseOut", False), int(anim.get("EasePower", DEFAULT_EASE_POWER)))
        if not kfs:
            continue
        n = int(anim.get("NumFrames", lv_frames))
        pts = frame_points(kfs, n, _f(mp, "X", 0.0), _f(mp, "Y", 0.0))[0]
        out.append(Platform(mp.get("PlatID"), pts, int(anim.get("StartFrame", "0")), _f(anim, "SlowMult", lv_slow)))
    return out


def dynamic_lines(xml):
    """{PlatID: [Line]} of the DynamicCollision blocks: children + the block's X / Y (#5293 @1525-1694).

    Lines whose PlatID has no animated MovingPlatform stay where they are parsed (`_-Y3I` returns early when
    `_-M4l` is empty)."""
    out = {}
    for blk in re.finditer(r"<DynamicCollision\b([^>]*)>(.*?)</DynamicCollision>", xml, flags=re.S):
        head, body = blk.group(1), blk.group(2)
        pid = re.search(r'PlatID="([^"]*)"', head)
        bx = float(re.search(r'\bX="([^"]*)"', head).group(1))
        by = float(re.search(r'\bY="([^"]*)"', head).group(1))
        lines = []
        for tag, attrs in re.findall(r"<(\w+Collision)\b([^>]*)/?>", body):
            for ln in element_lines(tag, attrs):
                ln.sx, ln.ex, ln.sy, ln.ey = ln.sx + bx, ln.ex + bx, ln.sy + by, ln.ey + by
                lines.append(ln)
        out.setdefault(pid.group(1) if pid else None, []).extend(lines)
    return out


def bind(lines, first_point):
    """`MovingPlatform._-D19` #6027: base offsets of each line from the platform's first point `_-M4l[0]`."""
    for ln in lines:
        ln.base = (ln.sx - first_point[0], ln.sy - first_point[1], ln.ex - first_point[0], ln.ey - first_point[1])


def move(lines, pos):
    """`MovingPlatform._-Y3I` #6014 @145-337: keep the previous start in `_-X1H` / `_-q1k`, then place each line
    at its base + the platform position."""
    for ln in lines:
        ln.x1h, ln.q1k = ln.sx, ln.sy
        bx, by, ex, ey = ln.base
        ln.sx, ln.sy, ln.ex, ln.ey = bx + pos[0], by + pos[1], ex + pos[0], ey + pos[1]


ANCHORS = {ABC_1100: {
    "_-Jb: KeyFrame via _-71C (hold of the previous frame at a Phase start), Phase StartFrame recursion": [
        (5298, 86, "pushstring", "'KeyFrame'"),
        (5298, 112, "callproperty", "_-71C, 8"),
        (5298, 152, "getproperty", "_-C6A"),
        (5298, 266, "callproperty", "_-yo, 1"),
        (5298, 293, "pushstring", "'Phase'"),
        (5298, 312, "pushstring", "'StartFrame'"),
        (5298, 426, "callpropvoid", "_-Jb, 10"),
        (6032, 160, "getlocal", "8"),
        (6032, 162, "add_i", ""),
        (6032, 605, "constructprop", "_-A2j, 11"),
        (6029, 25, "initproperty", "_-C6A"),
        (6029, 60, "initproperty", "_-JO"),
        (6029, 87, "initproperty", "_-o2m"),
    ],
    "_-Y61: frames from 1, last key frame wraps to NumFrames + 1, ease _-D2g, arcs K6l / b4l, round 1/100": [
        (5299, 557, "callproperty", "_-o35, 9"),
        (5299, 591, "pushbyte", "1"),
        (5299, 781, "add_i", ""),
        (5299, 887, "setlocal", "40"),
        (5299, 1079, "pushdouble", "100.0"),
        (5299, 1191, "callproperty", "_-D2g, 5"),
        (5299, 1277, "callproperty", "_-K6l, 1"),
        (5299, 1315, "callproperty", "_-b4l, 1"),
        (5299, 1424, "constructprop", "flash.geom::Point, 2"),
        (5299, 1572, "initproperty", "_-t4q"),
        (5299, 1639, "initproperty", "_-d5L"),
        (5293, 245, "initproperty", "_-66g"),
        (5293, 577, "initproperty", "_-36m"),
    ],
    "_-D2g easing; _-K6l / _-b4l rounded trig; PI2 / PI1_2 / PI3_2": [
        (1131, 17, "pushbyte", "2"),
        (1131, 77, "pushdouble", "0.5"),
        (1131, 95, "callproperty", "pow, 2"),
        (1131, 159, "lshift", ""),
        (1131, 198, "negate", ""),
        (1094, 40, "pushdouble", "1000.0"),
        (1094, 62, "callproperty", "cos, 1"),
        (1093, 62, "callproperty", "sin, 1"),
        (15351, 12012, "initproperty", "PI2"),
        (15351, 12031, "initproperty", "PI1_2"),
        (15351, 12050, "initproperty", "PI3_2"),
    ],
    "_-V39 / _-I4v: frame = start + ((t - n4k) * 0.05 % (1000 * n / 60 * SlowMult)) / period * n; blend k, k + 1": [
        (6016, 9, "getproperty", "_-n4k"),
        (6016, 36, "pushint", "1000"),
        (6016, 40, "pushbyte", "60"),
        (6016, 55, "pushdouble", "0.05"),
        (6016, 61, "modulo", ""),
        (6018, 47, "pushdouble", "1e-07"),
        (6018, 78, "modulo", ""),
    ],
    "_-D19 / _-Y3I: line base = start - _-M4l[0]; each update X1H = old start, start = base + position": [
        (6027, 115, "subtract", ""),
        (6027, 120, "initproperty", "_-t5b"),
        (6027, 203, "initproperty", "_-l2Q"),
        (6014, 96, "callproperty", "_-I4v, 3"),
        (6014, 182, "initproperty", "_-X1H"),
        (6014, 266, "initproperty", "startX"),
        (6014, 337, "initproperty", "_-P2s"),
        (7436, 253, "callproperty", "_-Y3I, 1"),
        (5293, 1664, "callpropvoid", "_-J1j, 5"),
    ],
}}


def verify(abc, sha):
    """Problems as text lines (empty = every pin holds). None if the ABC is not pinned."""
    if sha not in ANCHORS:
        return None
    bad = []
    lists = {}

    def lister(m):
        if m not in lists:
            lists[m] = listing(abc, m)
        return lists[m]
    for group, anchors in ANCHORS[sha].items():
        for (m, off, op, text), found in check(anchors, lister):
            bad.append(f"anchor [{group}] #{m} @{off}: want {op} {text}".rstrip() + f", found {found}")
    return bad
