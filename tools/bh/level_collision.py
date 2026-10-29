"""Static collision lines of a LevelDesc and the ray-cast candidate grid, patch 11.00.

See docs/hit-detection-11.00.md, section 7.2. Transcribes `_-139._-J1j` #5295 (one collision element ->
lines), `_-l49.static._-d1H` #1594 (curved element -> 4..10 lines), `_-R15.<init>` #1563 / `_-q3q` #1570
(line fields, normal), `_-139._-43i` #5309 -> `_-CX._-u2z` #1585 (grid insert), `_-CX.static._-a2E` #1587
(cell key), `_-A6B.static._-t2D` #1028 (cells crossed by a segment) and `_-CX._-936` #1582 (candidates).
Lines inside moving platforms are dynamic (`_-CX._-Z2B`) and are not built here. Static evidence only.
"""
import math
import re

from .movement import ABC_1100, check, listing
from .raycast import Line

CELL = 100
# Element name -> type flags, `_-i2H.static._-T5E` #858 (same table as tools/bh/collision.py, PR #20)
TYPES = {"HardCollision": 1, "SoftCollision": 2, "TriggerCollision": 4, "StickyCollision": 9,
         "NoSlideCollision": 17, "ItemIgnoreCollision": 49, "BouncyHardCollision": 65, "BouncySoftCollision": 66,
         "GameModeHardCollision": 129, "PressurePlateCollision": 257, "SoftPressurePlateCollision": 258,
         "BouncyNoSlideCollision": 81, "LavaCollision": 657, "MudCollision": 128}


def as3_round(x):
    """AS3 Math.round: floor(x + 0.5)."""
    return math.floor(x + 0.5)


def normalize_normal(nx, ny):
    """`_-q3q` #1570: the normal scaled to length 1 (Point.normalize(1); a zero vector stays zero)."""
    n = math.sqrt(nx * nx + ny * ny)
    if n == 0:
        return nx, ny
    return nx * (1 / n), ny * (1 / n)


def curve_lines(p1, p2, anchor, type_, team):
    """`_-l49._-d1H` #1594: a quadratic curve from p1 to p2 with control point `anchor`, as n straight lines.

    n = round((|p2.x - a.x| + |p1.x - a.x| + |p2.y - a.y| + |p1.y - a.y|) / 125), clamped to 4..10. Point i is
    (p1 + (a - p1) t) (1 - t) + (p2 + (a - p2)(1 - t)) t with t = i / n; each line runs left to right. No normal.
    """
    lx = abs(p2[0] - anchor[0]) + abs(p1[0] - anchor[0])
    ly = abs(p2[1] - anchor[1]) + abs(p1[1] - anchor[1])
    n = as3_round((lx + ly) / 125.0)
    if n < 4:
        n = 4
    elif n > 10:
        n = 10
    out = []
    px, py = p1
    for i in range(1, n + 1):
        t = i / n
        s = 1.0 - t
        qx = (p1[0] + (anchor[0] - p1[0]) * t) * s + (p2[0] + (anchor[0] - p2[0]) * s) * t
        qy = (p1[1] + (anchor[1] - p1[1]) * t) * s + (p2[1] + (anchor[1] - p2[1]) * s) * t
        if px <= qx:
            out.append(Line(px, py, qx, qy, type=type_, owner=team))
        else:
            out.append(Line(qx, qy, px, py, type=type_, owner=team))
        px, py = qx, qy
    return out


def _num(attrs, name):
    m = re.search(r'\b' + name + r'="([^"]*)"', attrs)
    return float(m.group(1)) if m else None


def element_lines(tag, attrs):
    """`_-139._-J1j` #5295 for one collision element: its lines (empty for an unknown element name).

    X / Y set both ends; otherwise X1 and X2 (Y1 and Y2) are used only when both exist; missing values stay 0. The ends are swapped so that
    start.x <= end.x. Team -> owner `_-r1H`. AnchorX + AnchorY -> curve_lines; otherwise one line, with a
    normal (NormalX, NormalY; a missing one is 0) normalised by `_-q3q` when either is present.
    """
    if tag not in TYPES:
        return []
    type_ = TYPES[tag]
    x, y = _num(attrs, "X"), _num(attrs, "Y")
    x1 = x2 = y1 = y2 = 0.0
    if x is not None:
        x1 = x2 = x
    elif _num(attrs, "X1") is not None and _num(attrs, "X2") is not None:
        x1, x2 = _num(attrs, "X1"), _num(attrs, "X2")
    if y is not None:
        y1 = y2 = y
    elif _num(attrs, "Y1") is not None and _num(attrs, "Y2") is not None:
        y1, y2 = _num(attrs, "Y1"), _num(attrs, "Y2")
    p1, p2 = (x1, y1), (x2, y2)
    if p1[0] > p2[0]:
        p1, p2 = p2, p1
    team = int(_num(attrs, "Team") or 0)
    ax, ay = _num(attrs, "AnchorX"), _num(attrs, "AnchorY")
    if ax is not None and ay is not None:
        return curve_lines(p1, p2, (ax, ay), type_, team)
    line = Line(p1[0], p1[1], p2[0], p2[1], type=type_, owner=team)
    nx, ny = _num(attrs, "NormalX"), _num(attrs, "NormalY")
    if nx is not None or ny is not None:
        line.normal = normalize_normal(nx or 0.0, ny or 0.0)
    return [line]


def static_lines(xml):
    """Lines of every collision element of a LevelDesc outside DynamicCollision and MovingPlatform blocks (those
    are dynamic, `_-Z2B`), in file order. [H] that file order is the insertion order of `_-139._-21A`."""
    xml = re.sub(r"<(DynamicCollision|MovingPlatform)\b.*?</\1>", "", xml, flags=re.S)
    out = []
    for tag, attrs in re.findall(r"<(\w+Collision)\b([^>]*)/?>", xml):
        out.extend(element_lines(tag, attrs))
    return out


def cells(x0, y0, x1, y1, cell=CELL):
    """`_-A6B._-t2D` #1028: the cells (corner x, corner y) crossed by a segment, in visiting order.

    The segment is made shallow (x and y swapped when |dy| > |dx|), oriented left to right, mirrored when it
    goes down, and walked column by column with at most one step per column.
    """
    dy, dx = abs(y1 - y0), abs(x1 - x0)
    steep = dy > dx
    if steep:
        x0, y0 = y0, x0
        x1, y1 = y1, x1
    if x0 > x1:
        x0, x1 = x1, x0
        y0, y1 = y1, y0
    neg = y1 < y0
    if neg:
        y1, y0 = -y1, -y0
    inv = 1.0 / cell
    ox = math.floor(x0 * inv) * cell
    oy = math.floor(y0 * inv) * cell
    x0, y0, x1, y1 = x0 - ox, y0 - oy, x1 - ox, y1 - oy
    with_slope = x1 - x0 != 0
    slope = (y1 - y0) / (x1 - x0) if with_slope else math.nan
    icpt = y0 - slope * x0
    raw = []
    cx = cy = 0
    while x1 >= cx:
        raw.append((cx, cy))
        cx = cx + cell
        xe = cx if cx < x1 else x1
        yv = slope * xe + icpt
        if yv >= cy + cell:
            cy = cy + cell
            raw.append((cx - cell, cy))
    out = []
    for rx, ry in raw:
        X, Y = rx + ox, ry + oy
        if neg:
            Y = -Y - cell
        if steep:
            X, Y = Y, X
        out.append((X, Y))
    return out


def cell_key(cx, cy):
    """`_-CX._-a2E` #1587: ((floor(cx + 0.01) * 0.01 + 16000) << 16) | (floor(cy + 0.01) * 0.01 + 16000)."""
    i = int(math.floor(cx + 0.01) * 0.01) + 16000
    j = int(math.floor(cy + 0.01) * 0.01) + 16000
    return ((i << 16) | j) & 0xFFFFFFFF


class Grid:
    """`_-CX` buckets `_-S4a` (cell key -> lines in insertion order) and the dynamic list `_-82D`."""

    def __init__(self, lines=(), dynamic=()):
        self.buckets = {}
        self.dynamic = list(dynamic)
        for ln in lines:
            self.insert(ln)

    def insert(self, line):
        """`_-u2z` #1585: append the line to the bucket of every cell its segment crosses."""
        for cx, cy in cells(line.sx, line.sy, line.ex, line.ey):
            self.buckets.setdefault(cell_key(cx, cy), []).append(line)

    def candidates(self, x0, y0, x1, y1):
        """`_-936` #1582: bucket members of the cells crossed by the ray, then every dynamic line; no
        de-duplication, no sort."""
        out = []
        for cx, cy in cells(x0, y0, x1, y1):
            out.extend(self.buckets.get(cell_key(cx, cy), ()))
        out.extend(self.dynamic)
        return out


ANCHORS = {ABC_1100: {
    "_-J1j: X / X1 / X2, Y / Y1 / Y2, swap so start.x <= end.x, Flag, Team, Anchor curve or one _-R15, Normal": [
        (5295, 325, "pushstring", "'X'"),
        (5295, 395, "pushstring", "'X1'"),
        (5295, 421, "pushstring", "'X2'"),
        (5295, 689, "pushstring", "'Flag'"),
        (5295, 742, "getproperty", "_-c1N"),
        (5295, 894, "setlocal", "9"),
        (5295, 902, "setlocal", "10"),
        (5295, 916, "pushstring", "'Team'"),
        (5295, 978, "pushstring", "'AnchorX'"),
        (5295, 1098, "callpropvoid", "_-d1H, 7"),
        (5295, 1189, "constructprop", "_-R15, 5"),
        (5295, 1226, "pushstring", "'NormalX'"),
        (5295, 1326, "pushbyte", "0"),
        (5295, 1387, "initproperty", "_-X3S"),
        (5295, 1393, "callpropvoid", "_-q3q, 0"),
    ],
    "_-R15.<init>(start, end, type, flag _-Z2Y, team _-r1H); _-q3q normalises the normal": [
        (1563, 17, "initproperty", "startX"),
        (1563, 39, "initproperty", "_-f1i"),
        (1563, 50, "initproperty", "_-P2s"),
        (1563, 58, "initproperty", "type"),
        (1563, 67, "initproperty", "_-Z2Y"),
        (1563, 76, "initproperty", "_-r1H"),
        (1570, 30, "callpropvoid", "normalize, 1"),
        (1570, 92, "pushdouble", "1.6666666666666667"),
    ],
    "_-d1H: n = round(manhattan / 125) in 4..10, quadratic points, lines left to right": [
        (1594, 129, "pushdouble", "125.0"),
        (1594, 133, "callproperty", "round, 1"),
        (1594, 143, "pushbyte", "4"),
        (1594, 163, "pushbyte", "10"),
        (1594, 267, "pushdouble", "1.0"),
        (1594, 485, "constructprop", "_-R15, 5"),
        (1594, 526, "constructprop", "_-R15, 5"),
    ],
    "_-43i -> _-u2z: static lines into cells of 100 (_-t2D), bucket per _-a2E key; dynamic via _-Z2B": [
        (5309, 23, "callpropvoid", "_-Z2B, 1"),
        (5309, 50, "callpropvoid", "_-u2z, 1"),
        (1585, 60, "pushbyte", "100"),
        (1585, 62, "callproperty", "_-t2D, 7"),
        (1585, 123, "callproperty", "_-a2E, 2"),
        (1585, 252, "callpropvoid", "http://adobe.com/AS3/2006/builtin::push, 1"),
        (1587, 5, "pushdouble", "0.01"),
        (1587, 46, "pushint", "16000"),
        (1587, 50, "pushbyte", "16"),
        (1587, 52, "lshift", ""),
        (1582, 66, "callproperty", "_-t2D, 7"),
        (1582, 254, "getproperty", "_-82D"),
    ],
    "_-t2D: steep swap, left to right, mirror when going down, origin cell, one step per column": [
        (1028, 72, "greaterthan", ""),
        (1028, 139, "lessthan", ""),
        (1028, 159, "pushdouble", "1.0"),
        (1028, 176, "callproperty", "floor, 1"),
        (1028, 239, "divide", ""),
        (1028, 293, "add", ""),
        (1028, 336, "add", ""),
        (1028, 359, "subtract", ""),
        (1028, 450, "negate", ""),
        (1028, 453, "subtract", ""),
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
