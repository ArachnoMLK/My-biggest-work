"""Map ray cast on patch 11.00: `_-CX._-X2e` #1581, with `_-A6B._-PK` #1017 and `_-Q3r._-R5v` #6297.

See docs/hit-detection-11.00.md, section 7, and docs/collision-11.00.md (PR #20) for the line flags and
the candidate order of `_-CX._-936` #1582 (grid cells of 100, then dynamic lines). The caller passes the
candidates already in that order. The arithmetic follows the bytecode order (AS3 Numbers are IEEE doubles).
Anchors are (method id, offset, opname, operand text as printed by `abc-disasm`). Static evidence only.
"""
import math
from dataclasses import dataclass

from .movement import ABC_1100, check, listing

OPT_SOFT_BOTH_SIDES, OPT_SKIP_OWNED, OPT_FLOOR_ONLY, OPT_TWO_SIDED = 1, 2, 4, 8


@dataclass
class Line:
    """A collision line `_-R15`: start (startX, startY), end (`_-f1i`, `_-P2s`), normal `_-X3S` (or None),
    flags `type`, disabled `_-44f`, owner `_-r1H` (0 = none), `_-X1H` (meaning [H])."""
    sx: float
    sy: float
    ex: float
    ey: float
    type: int = 1
    normal: tuple = None
    disabled: bool = False
    owner: int = 0
    x1h: float = None


@dataclass
class RayHit:
    line: Line
    point: tuple            # parameter 5 (`_-S27`)
    remaining: tuple        # parameter 4 after the call: hit point - start
    normal: tuple           # parameter 7 (`_-a2m`, from `_-PK`)
    side: float             # parameter 8 .x


def side_of(px, py, sx, sy, dx, dy):
    """`_-A6B._-PK` #1017: unit normal (dy, -dx) / |d| (computed as (-dy, dx) * (-1 / |d|)) and the signed
    distance of (px, py) from the line along it. Returns (side, (nx, ny))."""
    nx, ny = -dy, dx
    n = math.sqrt(nx * nx + ny * ny)
    if n != 0:
        k = -1.0 / n
        nx = nx * k
        ny = ny * k
    return (px - sx) * nx + (py - sy) * ny, (nx, ny)


def segment_hit(x1, y1, x2, y2, x3, y3, x4, y4):
    """`_-Q3r._-R5v` #6297 with its output point: (x1 + ua (x2 - x1), y1 + ua (y2 - y1)), or None."""
    d = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
    if d == 0:
        return None
    inv = 1.0 / d
    ua = inv * ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3))
    ub = inv * ((x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3))
    if ua >= 0.0 and ua <= 1.0 and ub >= 0.0 and ub <= 1.0:
        return x1 + ua * (x2 - x1), y1 + ua * (y2 - y1)
    return None


def _one_sided_skip(line, dx, dy):
    """#1581 @525-801: with no option among 8 | 4 | 1, a line with a normal is passed through when the motion
    goes the way the normal points (same signs), i.e. when leaving through its back."""
    nx, ny = line.normal
    if line.sx == line.ex:
        return dx != 0 and (dx > 0) == (nx > 0)
    if line.sy == line.ey:
        return dy != 0 and (dy > 0) == (ny > 0)
    if dx == 0:
        return (dy > 0) == (ny > 0)
    if dy == 0:
        return (dx > 0) == (nx > 0)
    return (dy > 0) == (ny > 0) and (dx > 0) == (nx > 0)


def ray_cast(lines, owner, x, y, dx, dy, mask, options=0, excluded=0, ignore=None, collect=None):
    """`_-CX._-X2e(owner, x, y, dir, out, ignore, normal, side, mask, options, ?, excluded, collect)` #1581.

    Returns a RayHit or None. Every accepted hit shortens the ray (when `collect` is None), so the result is
    the nearest hit; equal distances go to the later candidate (the test is inclusive). With `collect` (a
    list), every hit line is appended once and the ray is not shortened.
    """
    if dx == 0 and dy == 0:
        return None
    ex, ey = x + dx, y + dy
    rx, ry = dx, dy
    best = None
    for ln in lines:
        if ln.type & mask == 0 or ln.disabled:
            continue
        if ln.owner != 0 and ln.owner == owner:
            continue
        if ln.type & excluded != 0:
            continue
        if options & OPT_SKIP_OWNED and ln.owner != 0:
            continue
        if ln is ignore:
            continue
        prev = best.line if best else None
        if (prev is not None and prev.normal is not None and prev.normal[1] == -1 and prev.type & 1
                and ln.type & 2 and ln.normal is not None and ln.normal[1] == -1 and prev.sy == ln.sy
                and collect is None and ln.x1h == ln.sx):
            continue
        if options & (OPT_TWO_SIDED | OPT_FLOOR_ONLY | OPT_SOFT_BOTH_SIDES) == 0 and ln.normal is not None:
            if _one_sided_skip(ln, dx, dy):
                continue
        side, normal = side_of(x, y, ln.sx, ln.sy, ln.ex - ln.sx, ln.ey - ln.sy)
        if not (side >= 0.0 or mask & 2 == 0 or ln.type & 2 == 0 or options & OPT_SOFT_BOTH_SIDES):
            continue
        p = segment_hit(x, y, ex, ey, ln.sx, ln.sy, ln.ex, ln.ey)
        if p is None:
            continue
        best = RayHit(ln, p, (rx, ry), normal, side)
        if collect is None:
            ex, ey = p
            rx, ry = ex - x, ey - y
            best.remaining = (rx, ry)
        elif ln not in collect:
            collect.append(ln)
    if best is not None and options & OPT_FLOOR_ONLY:
        nx, ny = best.line.normal
        if ((ny < 0 and dy < 0 and ry > dy) or (ny > 0 and dy > 0 and ry < dy)
                or (nx < 0 and dx < 0 and rx > dx) or (nx > 0 and dx > 0 and rx < dx)):
            return None
    return best


ANCHORS = {ABC_1100: {
    "_-X2e: zero direction -> null; candidates from _-936; filters mask (param 9), _-44f, owner, excluded (param 12), option 2, ignore": [
        (1581, 110, "callproperty", "_-936, 5"),
        (1581, 166, "getproperty", "type"),
        (1581, 170, "getlocal", "9"),
        (1581, 186, "getproperty", "_-44f"),
        (1581, 200, "getproperty", "_-r1H"),
        (1581, 234, "getlocal", "12"),
        (1581, 252, "pushbyte", "2"),
        (1581, 286, "getlocal", "6"),
    ],
    "_-X2e: hard-then-soft floor exception, one-sided test unless options 8 | 4 | 1": [
        (1581, 319, "getproperty", "_-X3S"),
        (1581, 346, "pushbyte", "-1"),
        (1581, 466, "getproperty", "_-X1H"),
        (1581, 487, "pushbyte", "8"),
        (1581, 490, "pushbyte", "4"),
        (1581, 494, "pushbyte", "1"),
        (1581, 532, "getproperty", "_-f1i"),
        (1581, 596, "getproperty", "_-P2s"),
    ],
    "_-X2e: side _-PK >= 0 unless soft line, soft mask and no option 1; _-R5v on the shortened ray": [
        (1581, 850, "callproperty", "_-PK, 7"),
        (1581, 863, "pushdouble", "0.0"),
        (1581, 906, "pushbyte", "1"),
        (1581, 925, "getlocal", "19"),
        (1581, 927, "getlocal", "20"),
        (1581, 956, "callproperty", "_-R5v, 9"),
        (1581, 972, "setlocal", "18"),
        (1581, 1061, "setlocal", "19"),
        (1581, 1075, "setlocal", "20"),
        (1581, 1114, "callpropvoid", "http://adobe.com/AS3/2006/builtin::push, 1"),
    ],
    "_-X2e: option 4 drops the result by normal / direction / remaining; outputs point, remaining vector": [
        (1581, 1130, "pushbyte", "4"),
        (1581, 1214, "setlocal", "18"),
        (1581, 1429, "initproperty", "x"),
        (1581, 1454, "initproperty", "x"),
        (1581, 1468, "returnvalue", ""),
    ],
    "_-PK: normal (-dy, dx) * (-1 / |d|), side = (p - s) . n": [
        (1017, 5, "negate", ""),
        (1017, 30, "callproperty", "sqrt, 1"),
        (1017, 47, "pushdouble", "-1.0"),
        (1017, 52, "divide", ""),
        (1017, 101, "subtract", ""),
        (1017, 124, "returnvalue", ""),
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


def count(sha):
    """Number of anchors pinned for an ABC."""
    return sum(len(a) for a in ANCHORS[sha].values())
