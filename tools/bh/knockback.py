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
    """`_-26u._-M3e[11 + attacker._-P3I - victim._-92e]` (#1675 @592-640): attacker Strength level
    against victim Weight (Defense) level, both 0..11, so the index stays in 0..22. Out of range raises.
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
    """`1 + held / _-I6c * 0.25` (#1675 @1100-1116), applied to the damage and to the VariableImpulse part."""
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


def final_magnitude(u1x_value, fixed_impulse, item_part, variable_impulse, minimum=0.0, soft_flag=False,
                    di_case=False):
    """Length of the knockback point, `local 38` of #1675 @1198-1532.

    m = u1x_value + (FixedImpulse part `local 36` + item part `local 37`); when MinimumImpulse
    (`_-A6P`) != 0 and the VariableImpulse part (`local 35`) != 0, m is raised to at least MinimumImpulse;
    when the victim has the flag `Entity._-B6B` (`soft_flag`) and (VariableImpulse == 0 or the DI case
    local 39 holds), m *= 0.9. The power-specific factors of @1569-1638 are not modelled.
    """
    m = u1x_value + (fixed_impulse + item_part)
    if minimum != 0 and variable_impulse != 0 and m < minimum:
        m = float(minimum)
    if soft_flag and (variable_impulse == 0 or di_case):
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


def hitstun_ms(frames, minus5=False):
    """Hitstun given to `_-L3f`, `local 41` of #1675 @1785-1940: 16 * frames (power `_-T6p[i]`, else
    `_-7Z`); `minus5` is the case `_-g4i == 11`, damage > 0, `_-538 > 0`, local 15 == 1, which takes
    5 ms off a stun above 5."""
    stun = float(16 * frames)
    if minus5 and stun > 5:
        stun = stun - 5
    return stun


CAP_SQ = 62500.0        # Entity._-y4Q (250^2), the impulse cap of the step fold
TICK_FACTOR = 0.384     # _-z2k._-Vj (movement-11.00.md)
SOFT_DECAY = 8.5548     # #3001 @123, under Entity._-B6B without _-D3h


def knockback_decay(v1d, p5s, j1m, d4x, recovery, frozen=False, soft=False):
    """`Entity._-V12` #3001: one tick of knockback decay, run by `_-8i` in hitstun while v^2 >= 2500.

    When an overshoot component is past the cap (`_-J1m`^2 or `_-d4x`^2 > 62500) the overshoot vector
    decays, else the velocity does: its length drops by `decay * 0.384`, with decay = 0 when `_-050()`
    (`frozen`), 8.5548 under `_-B6B` without `_-D3h` (`soft`), else the Weight-family stat Recovery
    (`_-z2p`). Returns (v1d, p5s, j1m, d4x). AS3 Point.normalize keeps the direction (a negative length
    flips it, as here).
    """
    big = j1m * j1m > CAP_SQ or d4x * d4x > CAP_SQ
    decay = 0.0 if frozen else recovery
    if soft:
        decay = SOFT_DECAY
    x, y = (j1m, d4x) if big else (v1d, p5s)
    n = math.sqrt(x * x + y * y)
    length = n - decay * TICK_FACTOR
    if n > 0:
        x, y = x * length / n, y * length / n
    if big:
        return v1d, p5s, x, y
    return x, y, 0.0, 0.0


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
    "hit pass #1665: each queued hit _-P6X of _-T4G not yet done (_-fP) puts (_-X5n, _-d4V) in _-26u._-ba and calls _-76s": [
        (1665, 2048, "getproperty", "_-T4G"),
        (1665, 2069, "getproperty", "_-fP"),
        (1665, 2081, "getproperty", "_-ba"),
        (1665, 2087, "getproperty", "_-X5n"),
        (1665, 2105, "getproperty", "_-d4V"),
        (1665, 2185, "getproperty", "_-ba"),
        (1665, 2269, "callpropvoid", "_-76s, 21"),
    ],
    "direction source: _-F5N._-T5A gets it from _-JQ(...), Entity.OnHit normalises it to 1 into the _-P6X record": [
        (1731, 924, "callproperty", "_-JQ, 11"),
        (1731, 936, "setlocal", "32"),
        (1731, 3443, "getlocal", "32"),
        (1731, 3530, "callpropvoid", "_-5a::OnHit, 17"),
        (3042, 6, "constructprop", "_-P6X, 0"),
        (3042, 19, "pushbyte", "1"),
        (3042, 21, "callpropvoid", "normalize, 1"),
        (3042, 53, "initproperty", "_-X5n"),
        (3042, 65, "initproperty", "_-d4V"),
    ],
    "_-JQ start: (x, y) = power._-13F[i], power._-x45[i]; the attacker's keys add _-i2e[4|8] (sign by facing) and _-i2e[1|2]": [
        (1728, 194, "getproperty", "_-13F"),
        (1728, 210, "getproperty", "_-x45"),
        (1728, 225, "getproperty", "_-i2e"),
        (1728, 267, "pushbyte", "4"),
        (1728, 298, "pushbyte", "8"),
        (1728, 331, "pushbyte", "-1"),
        (1728, 341, "add_i", ""),
        (1728, 347, "pushbyte", "1"),
        (1728, 381, "pushbyte", "2"),
        (1728, 405, "add_i", ""),
    ],
    "hitstun: 16 * (power._-T6p[i] or _-7Z) ms, minus 5 in one case; passed to _-91G then _-L3f": [
        (1675, 1786, "getproperty", "_-T6p"),
        (1675, 1816, "getproperty", "_-7Z"),
        (1675, 1820, "pushbyte", "16"),
        (1675, 1822, "multiply_i", ""),
        (1675, 1824, "setlocal", "41"),
        (1675, 1874, "getproperty", "_-g4i"),
        (1675, 1877, "pushbyte", "11"),
        (1675, 1935, "pushbyte", "5"),
        (1675, 1938, "subtract", ""),
        (1675, 2182, "getlocal", "41"),
        (1677, 1446, "getlocal", "6"),
        (1670, 86, "getlocal_3", ""),
        (1670, 88, "initproperty", "_-v3y"),
    ],
    "_-04o is the replay's 9th settings u32 (damage_multiplier), read by _-I3W._-b2L; default 100": [
        (3876, 91, "callproperty", "_-a16, 0"),
        (3876, 96, "initproperty", "_-Z1I"),
        (3876, 105, "callproperty", "_-a16, 0"),
        (3876, 110, "initproperty", "_-04o"),
        (3861, 6, "pushbyte", "100"),
        (3861, 9, "initproperty", "_-04o"),
    ],
    "_-P3I / _-92e are the Strength / Weight stat levels (families 0 / 2 of _-C5c._-q2w), 5 by default; levels are 0..11": [
        (3049, 383, "pushbyte", "0"),
        (3049, 386, "getlocal", "5"),
        (3049, 388, "callproperty", "_-q2w, 2"),
        (3049, 425, "pushbyte", "2"),
        (3049, 428, "getlocal", "7"),
        (3049, 430, "callproperty", "_-q2w, 2"),
        (3049, 525, "getlocal", "5"),
        (3049, 527, "initproperty", "_-P3I"),
        (3049, 612, "getlocal", "7"),
        (3049, 614, "initproperty", "_-92e"),
        (3044, 63, "pushbyte", "11"),
        (3044, 298, "initproperty", "_-P3I"),
        (3044, 375, "initproperty", "_-92e"),
        (2887, 347, "initproperty", "_-P3I"),
        (2887, 356, "initproperty", "_-92e"),
    ],
    "powerTypes columns: VariableImpulse -> _-W1a, FixedImpulse -> _-C7, ImpulseOffsetX/Y -> _-13F/_-x45, FixedStunTime -> _-T6p, BaseDamage -> _-L69": [
        (6483, 11958, "getlocal", "7"),
        (6483, 11967, "getproperty", "_-W1a"),
        (6483, 12002, "getlocal", "8"),
        (6483, 12011, "getproperty", "_-C7"),
        (6483, 12214, "getproperty", "_-13F"),
        (6483, 12265, "getproperty", "_-x45"),
        (6483, 12290, "getproperty", "_-T6p"),
        (6483, 12365, "getlocal", "16"),
        (6483, 12369, "getproperty", "_-L69"),
        (1675, 477, "getproperty", "_-L69"),
    ],
    "powerTypes scalar columns: MinimumImpulse _-A6P, DIMaxAngle _-x1F, ImpulseOnHeavy _-4r, ItemSpeedDamage _-538, ItemSpeedImpulse _-w4x": [
        (6483, 7550, "pushstring", "'MinimumImpulse'"),
        (6483, 4254, "pushstring", "'DIMaxAngle'"),
        (6483, 6881, "pushstring", "'ImpulseOnHeavy'"),
        (6483, 7365, "pushstring", "'ItemSpeedDamage'"),
        (6483, 7391, "pushstring", "'ItemSpeedImpulse'"),
    ],
    "_-91G gates: Uninterruptable victim power -> no effect; impulses first; no stun or below InterruptThreshold -> no hitstun": [
        (1677, 853, "getproperty", "_-C5G"),
        (1677, 863, "returnvalue", ""),
        (1677, 942, "callpropvoid", "_-N5C::_-E1t, 2"),
        (1677, 1230, "getlocal", "6"),
        (1677, 1238, "pushstring", "'[CombatManager.as] Power '"),
        (1677, 1287, "getproperty", "_-i4o"),
        (1677, 1297, "getlocal", "13"),
        (1677, 1300, "getproperty", "_-ro"),
        (1677, 1303, "lessthan", ""),
        (1677, 1315, "getproperty", "_-ro"),
        (1677, 1323, "returnvalue", ""),
    ],
    "decay _-V12: big = overshoot^2 > _-y4Q; decay 0 / Recovery _-z2p / 8.5548; length - decay * 0.384; write back": [
        (3001, 24, "getproperty", "_-y4Q"),
        (3001, 61, "callproperty", "_-050, 0"),
        (3001, 81, "getproperty", "_-z2p"),
        (3001, 98, "getproperty", "_-B6B"),
        (3001, 114, "getproperty", "_-D3h"),
        (3001, 123, "pushdouble", "8.5548"),
        (3001, 231, "getproperty", "length"),
        (3001, 244, "getproperty", "_-Vj"),
        (3001, 249, "subtract", ""),
        (3001, 262, "callpropvoid", "normalize, 1"),
        (3001, 286, "initproperty", "_-J1m"),
        (3001, 304, "initproperty", "_-d4x"),
        (3001, 334, "callpropvoid", "_-N5C::_-E1t, 2"),
        (3001, 371, "initproperty", "_-J1m"),
        (3001, 380, "initproperty", "_-d4x"),
        (2984, 278, "setlocal_2", ""),
        (2984, 716, "callproperty", "_-5q, 0"),
        (2984, 731, "getproperty", "_-i4P"),
        (2984, 744, "getproperty", "_-83l"),
        (2984, 756, "callpropvoid", "_-V12, 0"),
        (15351, 30066, "pushdouble", "2500.0"),
        (15351, 30070, "initproperty", "_-i4P"),
        (2984, 2901, "initproperty", "_-J1m"),
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
