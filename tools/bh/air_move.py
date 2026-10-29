"""Free move of a fighter against the map on patch 11.00: the sweep phase of `Entity._-8i` #2984 @6620-8865.

See docs/hit-detection-11.00.md, section 7.4. One step moves the fighter's feet point (`_-11W`, `_-75K`) by
U = (x step, `_-P5S` x 0.384, + 2.02 on y while on a ground line). Three map sweeps choose the nearest stop:
the feet, the head (120 above) and, during some attacks, a raised point; a ceiling check may then cancel the
x part. The fighter is placed at the stop, the stop line becomes the ground line `_-96f`, and the fighter is
backed off 1.01 from it. What the step does next with `_-96f` (walls `_-r51`, landing, @8869-) is not here.
Arithmetic in bytecode order; ray casts through tools/bh/raycast.py. Static evidence only.
"""
import math
from dataclasses import dataclass, field

from .movement import ABC_1100, check, listing
from .raycast import ray_cast

STEP = 0.384          # `_-z2k._-Vj`
GROUND_PUSH = 2.02    # @6704: extra y while a ground line is set
HEAD = 120.0          # @6960: height of the head sweep
SMALL = 1.02          # `Entity._-u4H` (script157.<init> @1970)
BACK_OFF = 1.01       # @7778 / @8754: Point.normalize(1.01)
NO_SLIDE = 16         # `_-z2k._-x1z`


@dataclass
class MoveResult:
    x: float
    y: float
    ground: object = None             # `_-96f` after the step (the line that stopped the move, or None)
    head_stop: bool = False           # local 29: the stop came from the head or attack sweep
    ceilings: list = field(default_factory=list)   # `_-u3j`: lines found by the ceiling check


def _length(v):
    return math.sqrt(v[0] * v[0] + v[1] * v[1])


def _normalize(v, k):
    n = _length(v)
    if n == 0:
        return v
    return v[0] * (k / n), v[1] * (k / n)


def _cast(cands, team, x, y, d, mask):
    """A 10-argument `_-X2e(team, x, y, d, out, null, null, null, mask, 0)`: (hit line or None, remaining d)."""
    hit = ray_cast(cands(x, y, d), team, x, y, d[0], d[1], mask, 0, 0)
    return (None, d) if hit is None else (hit.line, hit.remaining)


def _back_off(line, mv):
    """@7544-7770 / @8508-8757: along -normal when the line is hard and the move is tiny (|x|, |y| <= 1.02),
    else along the move; length 1.01."""
    tiny = line.type & 1 and -SMALL <= mv[0] <= SMALL and -SMALL <= mv[1] <= SMALL
    v = (-line.normal[0], -line.normal[1]) if tiny else mv
    return _normalize(v, BACK_OFF)


def air_move(lines, team, x, y, x_step, p5s, on_ground, drop_through=False, attack_rise=None):
    """One free move. `lines` is a list in candidate order or a level_collision.Grid.

    mask = hard only when dropping through a soft platform (local 3 = 1, @1780-1791), else hard | soft.
    `attack_rise` is the power's `_-V67` when `_-wn()` and it is non-zero (@7134-7191), else None.
    """
    if hasattr(lines, "candidates"):
        def cands(cx, cy, d):
            return lines.candidates(cx, cy, cx + d[0], cy + d[1])
    else:
        def cands(cx, cy, d):
            return lines
    mask = 1 if drop_through else 1 | 2
    u = (x_step, p5s * STEP + (GROUND_PUSH if on_ground else 0.0))
    head_stop = False
    hit, mv = _cast(cands, team, x, y, u, mask)                         # feet, @6896
    head, nv = _cast(cands, team, x, y - HEAD, u, 1)                    # head, @6999
    if head is not None and _length(nv) < _length(mv):
        mv = nv
        if head.normal[1] >= 0:
            hit, head_stop = head, True
    if attack_rise is not None:                                        # raised attack point, @7339
        arm, wv = _cast(cands, team, x, y - HEAD - attack_rise, u, NO_SLIDE)
        if arm is not None and arm.normal[1] > 0 and _length(wv) < _length(mv):
            mv, hit, head_stop = wv, arm, True
    px, py = x + mv[0], y + mv[1]
    if hit is not None:
        b = _back_off(hit, mv)
        px, py = px - b[0], py - b[1]
    ceilings = []
    roof, _ = _cast(cands, team, px, py, (0.0, -HEAD), 1)               # ceiling check, @7905
    if roof is not None:
        ceilings.append(roof)
        u0 = (0.0, u[1])
        head_stop = False
        hit, mv = _cast(cands, team, x, y, u0, mask)                    # @8106
        head, nv = _cast(cands, team, x, y - HEAD, u0, 1)               # @8209
        if head is not None and _length(nv) < _length(mv):
            mv = (mv[0], nv[1])
            hit, head_stop = head, True
    x, y = x + mv[0], y + mv[1]                                         # @8302-8408
    if hit is not None:                                                # `_-96f = l17`, @8481-8865
        b = _back_off(hit, mv)
        x, y = x - b[0], y - b[1]
    return MoveResult(x, y, hit, head_stop, ceilings)


ANCHORS = {ABC_1100: {
    "_-8i free move: U = (local12, P5S * Vj (+ 2.02 on ground)); sweeps feet (mask local3), head -120 (mask 1), attack -120 - V67 (mask x1z)": [
        (2984, 6667, "getproperty", "_-Vj"),
        (2984, 6704, "pushdouble", "2.02"),
        (2984, 6893, "getlocal_3", ""),
        (2984, 6896, "callproperty", "_-X2e, 10"),
        (2984, 6960, "pushdouble", "120.0"),
        (2984, 6994, "pushbyte", "1"),
        (2984, 6999, "callproperty", "_-X2e, 10"),
        (2984, 7050, "lessthan", ""),
        (2984, 7110, "getproperty", "y"),
        (2984, 7183, "getproperty", "_-V67"),
        (2984, 7334, "getproperty", "_-x1z"),
        (2984, 7339, "callproperty", "_-X2e, 10"),
        (2984, 7379, "greaterthan", ""),
        (2984, 1780, "setlocal_3", ""),
        (2984, 1791, "setlocal_3", ""),
    ],
    "_-8i back-off 1.01 (-normal when hard and |move| <= u4H = 1.02); ceiling check (0, -120) mask 1, redo with x = 0; _-96f = stop line": [
        (2984, 7579, "getproperty", "_-u4H"),
        (2984, 7778, "pushdouble", "1.01"),
        (2984, 7781, "callpropvoid", "normalize, 1"),
        (2984, 7843, "pushdouble", "-120.0"),
        (2984, 7905, "callproperty", "_-X2e, 10"),
        (2984, 7938, "callpropvoid", "http://adobe.com/AS3/2006/builtin::push, 1"),
        (2984, 7953, "initproperty", "x"),
        (2984, 8106, "callproperty", "_-X2e, 10"),
        (2984, 8209, "callproperty", "_-X2e, 10"),
        (2984, 8286, "initproperty", "y"),
        (2984, 8353, "callpropvoid", "_-N5C::_-E1t, 2"),
        (2984, 8486, "initproperty", "_-96f"),
        (2984, 8754, "pushdouble", "1.01"),
        (2984, 8865, "callpropvoid", "_-N5C::_-E1t, 2"),
        (2984, 8886, "initproperty", "_-r51"),
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
