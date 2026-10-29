"""Damage and knockback force of a hit on patch 11.00: `_-26u._-76s` #1675 and `_-26u._-u1x` #1674.

See docs/knockback-11.00.md. The functions transcribe the arithmetic in bytecode order (AS3 Numbers are
IEEE doubles, like Python floats); field names are the obfuscated ones, their meanings are [H].
Anchors are (method id, offset, opname, operand text as printed by `abc-disasm`); branch operands are
relative. Static evidence only; nothing is executed.
"""
import math

from .movement import ABC_1100, check, listing

# _-26u._-M3e, script92.<init> #1679 @59-131: multiplier by stat difference, index 11 + a - b
STAT_TABLE = (0.8349, 0.8384, 0.8437, 0.851, 0.8604, 0.8719, 0.8857, 0.9022, 0.9215, 0.9439, 0.9699, 1,
              1.031, 1.0594, 1.0852, 1.1084, 1.129, 1.1469, 1.1623, 1.1751, 1.1853, 1.1928, 1.1978)
STAT_CENTER = 11


def stat_multiplier(attacker_p3i, victim_92e):
    """`_-26u._-M3e[11 + attacker._-P3I - victim._-92e]` (#1675 @592-640). Out of range raises.

    In AS3 an index outside the array reads `undefined`, which becomes NaN; no clamp is in the code.
    """
    i = STAT_CENTER + attacker_p3i - victim_92e
    if not 0 <= i < len(STAT_TABLE):
        raise IndexError(f"stat index {i} outside _-M3e")
    return STAT_TABLE[i]


def hit_damage(base, charge, p538, n_r, l_a, o3t, attacker_45j=None, stat=1.0, victim_w22=0):
    """Damage of a hit, `local 28` of #1675 @480-704, before the match setting of @1152-1174.

    base = the power's damage entry; extra = charge * `_-538`, and when non-zero extra - 50 * `_-538`,
    at least 1; then * weapon `_-nR` * victim `_-lA` / `_-o3t`; * attacker `_-45J` (when the attacker is
    an Entity); * `stat` (the `_-M3e` entry, see stat_multiplier; skipped when 0); a negative result is
    kept above -victim `_-W22` (truncated to int).
    """
    d = base
    e = charge * p538
    if e != 0:
        e = e - 50 * p538
        if e < 1.0:
            e = 1.0
    d = d + e
    d = d * (n_r * l_a / o3t)
    if attacker_45j is not None:
        d = d * attacker_45j
    if stat != 0:
        d = d * stat
    if d < 0:
        floor = int(-1 * victim_w22)
        if not floor < d:
            d = float(floor)
    return d


def charged_scale(held, i6c):
    """`1 + held / _-I6c * 0.25` (#1675 @1100-1116), applied to damage and to the fixed force."""
    return 1 + held / i6c * 0.25


def knockback_force(force, damage, victim_w22, victim_w3f, attacker_g4s, victim_13t, victim_p1r,
                    attacker_z4f=1.0, same_team=False, mode5=False):
    """`_-26u._-u1x(power, attacker, victim, force, damage)` #1674: the knockback magnitude.

    d = (victim `_-W22` + victim `_-w3F` + damage) / 100, or (50 + `_-w3F` + damage) / 100 when the
    scoring rule `_-U6g == 5`; force * 0.75 against a team mate; then
    max(force * (d + d * (d / 2)) * attacker `_-Kc._-G4s` * `_-z4f` / victim `_-Kc._-13t` - victim `_-P1r`, 0).
    `attacker_z4f` is used only when the attacker is an Entity and the power is not `_-Rc` / `_-d6x`.
    """
    if mode5:
        d = (50 + victim_w3f + damage) / 100
    else:
        d = (victim_w22 + victim_w3f + damage) / 100
    if same_team:
        force = force * 0.75
    f = force * (d + d * (d / 2)) * attacker_g4s * attacker_z4f / victim_13t
    return max(f - victim_p1r, 0)


def final_magnitude(u1x_value, c7_part, variable, fixed, a6p=0.0, soft_flag=False, di_case=False):
    """Length of the knockback point, `local 38` of #1675 @1198-1532.

    m = u1x_value + (c7_part + variable); when `power._-A6P != 0` and fixed != 0, m is raised to at
    least `_-A6P`; when the victim has the flag `Entity._-B6B` (`soft_flag`) and (fixed == 0 or the
    DI case local 39 holds), m *= 0.9. The power-specific factors of @1569-1638 are not modelled.
    """
    m = u1x_value + (c7_part + variable)
    if a6p != 0 and fixed != 0 and m < a6p:
        m = float(a6p)
    if soft_flag and (fixed == 0 or di_case):
        m = m * 0.9
    return m


PI2 = math.pi * 2           # _-A6B.PI2 = Math.PI * 2, set in _-y2E.init #15351 @12002-12012
DI_LIMIT = 0.8              # #1664 @344, unless power._-x1F != Number.MAX_VALUE


def as3_round(x):
    """AS3 `Math.round`: halves go up (floor(x + 0.5)), unlike Python's round."""
    return math.floor(x + 0.5)


def _milli(x):
    return as3_round(x * 1000.0) / 1000.0


def atan2_netsafe(y, x):
    """`_-A6B.atan2_netsafe(y, x)` #1098: unit vector and result rounded to 1/1000."""
    r = math.sqrt(x * x + y * y)
    if not r > 0:
        return 0.0
    return _milli(math.atan2(_milli(y / r), _milli(x / r)))


def octant_angle(y, x):
    """`_-A6B._-75B(y, x)` #1084: the angle of a key direction, from a fixed list (eps 1e-6)."""
    if y < -1e-06:
        return -0.785 if x > 1e-06 else (-2.356 if x < -1e-06 else -1.571)
    if y > 1e-06:
        return 0.785 if x > 1e-06 else (2.356 if x < -1e-06 else 1.571)
    return 3.142 if x < -1e-06 else 0.0


def _wrap_round(a):
    k = int(math.floor(a / PI2))
    return _milli(a - k * PI2)


def cos_netsafe(a):
    """`_-A6B._-K6l(a)` #1094: angle wrapped by PI2 and rounded, cosine rounded, both to 1/1000."""
    return _milli(math.cos(_wrap_round(a)))


def sin_netsafe(a):
    """`_-A6B._-b4l(a)` #1093: as cos_netsafe with sine."""
    return _milli(math.sin(_wrap_round(a)))


def key_vector(keys):
    """`_-26u._-Cg` as #1664 @30-172 sets it: x -1 Left (4) / +1 Right (8), y -1 Up (1) / +1 Drop (2)."""
    x = -1 if keys & 4 else (1 if keys & 8 else 0)
    y = -1 if keys & 1 else (1 if keys & 2 else 0)
    return x, y


def directional_influence(px, py, keys, limit=DI_LIMIT):
    """`_-26u._-e4x(point, keys, power)` #1664: the knockback direction after a held direction.

    Returns the new (x, y) direction (its length is set later by normalize). Within `limit` radians
    of the held direction the point becomes the key vector itself; otherwise it turns by `limit`
    toward it.
    """
    if px == 0 and py == 0:
        return px, py
    cx, cy = key_vector(keys)
    if cx == 0 and cy == 0:
        return px, py
    a = atan2_netsafe(py, px)
    b = octant_angle(cy, cx)
    diff = b - a
    if diff > math.pi:
        diff = diff - math.pi * 2
    elif diff < -math.pi:
        diff = diff + math.pi * 2
    if abs(diff) < limit:
        return float(cx), float(cy)
    ang = a + limit if diff > 0 else a - limit
    return cos_netsafe(ang), sin_netsafe(ang)


ANCHORS = {ABC_1100: {
    "_-u1x: z4f factor, d = (W22 + w3F + damage) / 100 (50 instead of W22 when _-U6g == 5)": [
        (1674, 85, "getproperty", "_-z4f"),
        (1674, 92, "pushdouble", "1.0"),
        (1674, 111, "getproperty", "_-U6g"),
        (1674, 114, "pushbyte", "5"),
        (1674, 123, "getproperty", "_-W22"),
        (1674, 127, "getproperty", "_-w3F"),
        (1674, 132, "getlocal", "5"),
        (1674, 136, "pushbyte", "100"),
        (1674, 138, "divide", ""),
        (1674, 146, "pushbyte", "50"),
        (1674, 158, "pushbyte", "100"),
    ],
    "_-u1x: team mate x 0.75, F = force * (d + d * (d / 2)) * G4s * z4f / 13t, max(F - P1r, 0)": [
        (1674, 179, "getproperty", "_-25G"),
        (1674, 201, "pushdouble", "0.75"),
        (1674, 210, "getlocal", "9"),
        (1674, 216, "pushbyte", "2"),
        (1674, 218, "divide", ""),
        (1674, 219, "multiply", ""),
        (1674, 220, "add", ""),
        (1674, 222, "multiply", ""),
        (1674, 227, "getproperty", "_-G4s"),
        (1674, 239, "getproperty", "_-13t"),
        (1674, 242, "divide", ""),
        (1674, 253, "getproperty", "_-P1r"),
        (1674, 260, "callproperty", "max, 2"),
        (1674, 265, "returnvalue", ""),
    ],
    "_-76s damage: base + charge extra, * nR * lA / o3t, * 45J, * _-M3e[11 + P3I - 92e], floor at -W22": [
        (1675, 488, "setlocal", "28"),
        (1675, 493, "getproperty", "_-538"),
        (1675, 510, "pushbyte", "50"),
        (1675, 523, "pushdouble", "1.0"),
        (1675, 549, "getproperty", "_-nR"),
        (1675, 554, "getproperty", "_-lA"),
        (1675, 560, "getproperty", "_-o3t"),
        (1675, 584, "getproperty", "_-45J"),
        (1675, 592, "pushbyte", "11"),
        (1675, 608, "getproperty", "_-P3I"),
        (1675, 622, "getproperty", "_-92e"),
        (1675, 634, "getproperty", "_-M3e"),
        (1675, 646, "setlocal", "31"),
        (1675, 660, "multiply", ""),
        (1675, 672, "pushbyte", "-1"),
        (1675, 676, "getproperty", "_-W22"),
    ],
    "_-76s force: W1a[i] (+ _-4r), variable part * w4x * 0.5, charge 1 + held / I6c * 0.25, damage * _-04o / 100, then _-u1x": [
        (1675, 921, "getproperty", "_-W1a"),
        (1675, 943, "getproperty", "_-4r"),
        (1675, 952, "getproperty", "_-C7"),
        (1675, 1038, "getproperty", "_-w4x"),
        (1675, 1046, "pushdouble", "0.5"),
        (1675, 1054, "getproperty", "_-h5f"),
        (1675, 1078, "getproperty", "_-w46"),
        (1675, 1105, "getproperty", "_-I6c"),
        (1675, 1109, "pushdouble", "0.25"),
        (1675, 1136, "pushdouble", "1.25"),
        (1675, 1164, "getproperty", "_-04o"),
        (1675, 1168, "pushdouble", "100.0"),
        (1675, 1188, "add", ""),
        (1675, 1192, "callproperty", "_-u1x, 5"),
    ],
    "magnitude = _-u1x(...) + (C7 part + variable), floor _-A6P, x 0.9 under _-B6B; the point local 7 is normalised to it": [
        (1675, 1198, "setlocal", "38"),
        (1675, 1202, "getlocal", "36"),
        (1675, 1204, "getlocal", "37"),
        (1675, 1206, "add", ""),
        (1675, 1208, "add", ""),
        (1675, 1216, "getproperty", "_-A6P"),
        (1675, 1229, "getlocal", "35"),
        (1675, 1255, "getproperty", "_-A6P"),
        (1675, 1274, "initproperty", "_-B2Q"),
        (1675, 1494, "getproperty", "_-B6B"),
        (1675, 1527, "pushdouble", "0.9"),
        (1675, 1640, "getlocal", "7"),
        (1675, 1642, "getlocal", "38"),
        (1675, 1644, "callpropvoid", "normalize, 1"),
        (1675, 2179, "getlocal", "7"),
    ],
    "directional influence: when allowed and 32 ms after _-R5q._-c3J, a held direction (_-66U & 15) calls _-e4x on the point": [
        (1675, 1288, "getproperty", "_-a60"),
        (1675, 1313, "getproperty", "_-x1F"),
        (1675, 1366, "callpropvoid", "_-N6u, 2"),
        (1675, 1375, "getproperty", "_-M6J"),
        (1675, 1393, "getproperty", "_-m1t"),
        (1675, 1415, "getproperty", "_-c3J"),
        (1675, 1420, "pushbyte", "32"),
        (1675, 1435, "getproperty", "_-66U"),
        (1675, 1439, "pushbyte", "15"),
        (1675, 1480, "callpropvoid", "_-e4x, 3"),
    ],
    "_-e4x: key vector, netsafe angles, wrap to (-pi, pi], limit 0.8 (or _-x1F), snap or turn by the limit": [
        (1664, 31, "pushbyte", "4"),
        (1664, 50, "pushbyte", "-1"),
        (1664, 61, "pushbyte", "8"),
        (1664, 104, "pushbyte", "1"),
        (1664, 134, "pushbyte", "2"),
        (1664, 229, "callproperty", "atan2_netsafe, 2"),
        (1664, 263, "callproperty", "_-75B, 2"),
        (1664, 276, "subtract", ""),
        (1664, 286, "getproperty", "PI"),
        (1664, 344, "pushdouble", "0.8"),
        (1664, 351, "getproperty", "_-x1F"),
        (1664, 375, "callproperty", "abs, 1"),
        (1664, 434, "add", ""),
        (1664, 447, "subtract", ""),
        (1664, 458, "callproperty", "_-K6l, 1"),
        (1664, 474, "callproperty", "_-b4l, 1"),
    ],
    "netsafe trig: inputs and results rounded to 1/1000; PI2 = Math.PI * 2": [
        (1098, 12, "callproperty", "sqrt, 1"),
        (1098, 42, "pushdouble", "1000.0"),
        (1098, 104, "callproperty", "atan2, 2"),
        (1098, 122, "callproperty", "round, 1"),
        (1084, 1, "pushdouble", "-1e-06"),
        (1084, 16, "pushdouble", "-0.785"),
        (1084, 32, "pushdouble", "-2.356"),
        (1084, 39, "pushdouble", "-1.571"),
        (1084, 94, "pushdouble", "3.142"),
        (1094, 9, "getproperty", "PI2"),
        (1094, 14, "callproperty", "floor, 1"),
        (1094, 62, "callproperty", "cos, 1"),
        (1093, 62, "callproperty", "sin, 1"),
        (15351, 12006, "getproperty", "PI"),
        (15351, 12009, "pushbyte", "2"),
        (15351, 12012, "initproperty", "PI2"),
    ],
    "_-26u._-M3e: 23 stat multipliers, 1 at index 11": [
        (1679, 63, "pushdouble", "0.8349"),
        (1679, 91, "pushdouble", "0.9699"),
        (1679, 94, "pushbyte", "1"),
        (1679, 96, "pushdouble", "1.031"),
        (1679, 126, "pushdouble", "1.1978"),
        (1679, 129, "newarray", "23"),
        (1679, 131, "initproperty", "_-M3e"),
    ],
    "the hit _-91G gets the knockback point; it is written into the one-tick impulses _-84 / _-A4A": [
        (1675, 2205, "callproperty", "_-91G, 11"),
        (1677, 932, "getproperty", "_-84"),
        (1677, 951, "getproperty", "_-A4A"),
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
