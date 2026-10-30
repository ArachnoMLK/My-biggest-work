"""Ground and dash jumps on patch 11.00: the grounded branch of `Entity.Jump` #3052.

See docs/movement-11.00.md (PR #16), which first read these values, and docs/hit-detection-11.00.md §7.4.
`_-i4Z._-51o` #6313 calls `owner.Jump(t)` on a fresh press of input bit 16 (input-buffer-11.00.md, PR #28,
for the 192 ms lock and the air-jump count). [V] unless marked [H]. `_-141()` is "held left"
(horizontal-11.00.md, PR #23).
"""
from .movement import ABC_1100

GROUND_IMPULSE = 57.0      # @643
GROUND_K = 0.86            # @579: when Jump's second argument is true (`Entity._-A2X` #3131)
DASH_IMPULSE = 170.0       # @698
DASH_WINDOW_MS = 160       # @84: `_-26T` + 160 > t
TAIL_SLOWDOWN = 4          # @1143 / @1173: `_-M3V` and |vx| > 4 -> |vx| -= 4
TAIL_BOOST_K = 0.5         # @1315: `_-84` += `_-13G` x 0.5
BOOST_13G = 30.0           # `_-13G` = `Entity._-32g` (Entity.<init> #2887 @149; 30.0 in #15351 @30045)
WALL_IMPULSE = 53.0        # `Entity._-S4O` (#15351 @30055), x k at @1623
WALL_PUSH = 48.0           # @1629 (local 11): added to `_-84`, away from the wall
WALL_AWAY_K = 0.9          # @1805 / @1893: the push is x 0.9 when the held side points away from it
AIR_IMPULSE = 57.0         # @2065
AIR_IMPULSE_SECOND = 65.0  # @2078: with Jump's second argument


def dash_window(t, dash_timer, ground, xb):
    """@75-127 (local 5): `_-26T` + 160 > t and (a ground line `_-96f` or `_-Xb` == 1)."""
    return dash_timer + DASH_WINDOW_MS > t and (ground is not None or xb == 1)


def ground_jump(t, dash_timer, ground, xb, a4a, second_arg=False):
    """@574-1048: the grounded branch, taken when `_-96f` is set or `_-Xb` == 1. Returns (a4a, p5s, ground,
    dash) after the jump, or None when the branch is not taken (the air jumps of @1545-, not transcribed).

    The impulse is 57 x k (k = 0.86 with the second argument, else 1), or 170 in the dash window. `_-P5S` is
    set to 0, `_-96f` to null, and `_-A4A` -= impulse; `step.fold_impulse` (PR #26) then folds `_-A4A` into
    `_-P5S`. [H] The dash branch also clamps `_-v1D` (@704-) and fires 'dash.Jump'; not modelled here.
    """
    if ground is None and xb != 1:
        return None
    k = GROUND_K if second_arg else 1.0
    impulse = GROUND_IMPULSE * k
    dash = dash_window(t, dash_timer, ground, xb)
    if dash:
        impulse = DASH_IMPULSE
    return a4a - impulse, 0.0, None, dash


def ground_tail(left, m3v, v1d, h84, max_speed, boost=BOOST_13G):
    """@1066-1537, after a ground jump, when `_-81n()` (a side held) or local 6 (the dash window with the
    `_-R5q._-66U` bits 4 / 8 matching the held side). `max_speed` is `_-K64()` (local 11). Returns (v1d, h84).

    Held left: with `_-M3V` and vx > 4, vx -= 4; else a positive vx becomes 0; else at or below -max_speed,
    `_-84` -= boost x 0.5. Held right is the mirror. [H] `_-84` is the horizontal impulse folded like `_-A4A`.
    """
    half = boost * TAIL_BOOST_K
    if left:
        if m3v and v1d > TAIL_SLOWDOWN:
            return v1d - TAIL_SLOWDOWN, h84
        if v1d > 0:
            return 0, h84
        if v1d <= -max_speed:
            return v1d, h84 - half
        return v1d, h84
    if m3v and v1d < -TAIL_SLOWDOWN:
        return v1d + TAIL_SLOWDOWN, h84
    if v1d < 0:
        return 0, h84
    if v1d >= max_speed:
        return v1d, h84 + half
    return v1d, h84


def wall_jump(r51, xb, a4a, h84, left, side_held, k=1.0):
    """@1545-2014: taken when `_-r51` != 0 or `_-Xb` == 2 (the grounded branch was not). Returns (a4a, p5s,
    v1d, h84, ground, flip) or None when the branch is not taken.

    `_-31A()` runs, `_-96f` = null, `_-A4A` -= 53 x k, `_-v1D` = 0 and `_-P5S` takes the value returned by that
    write [H: 0]. With no side held, `_-CV(_-r35())` runs (`flip`) [H: faces away from the wall]. Then `_-84`
    += 48 on a wall `_-r51` == 1 (x 0.9 when held left), else -= 48 (x 0.9 when held right).
    """
    if r51 == 0 and xb != 2:
        return None
    a4a -= WALL_IMPULSE * k
    if r51 == 1:
        h84 += WALL_PUSH * (WALL_AWAY_K if left else 1.0)
    else:
        h84 -= WALL_PUSH * (1.0 if left else WALL_AWAY_K)
    return a4a, 0.0, 0.0, h84, None, not side_held


def air_jump(used, allowed, a4a, v1d, left, side_held, max_speed, k=1.0, second_arg=False):
    """@2018-2423: taken when `_-P5Y()` < `_-56T()` [H: air jumps used < allowed]. Returns (a4a, p5s, v1d,
    used) or None when no air jump is left (then local 12 = `_-e3e` & `Entity._-8` != 0 and `_-I5A` = 0).

    `_-31A()` runs, the impulse is 57 x k (65 x k with the second argument), `_-P5S` = 0, `_-A4A` -= impulse,
    `_-k1j(_-P5Y() + 1)`. With a side held, vx is capped at `_-K64(false)` on the side opposite to the held one
    (held left: vx > max becomes max; held right: vx < -max becomes -max), the other side untouched.
    """
    if not used < allowed:
        return None
    impulse = (AIR_IMPULSE_SECOND if second_arg else AIR_IMPULSE) * k
    if side_held:
        if left and v1d > max_speed:
            v1d = max_speed
        elif not left and v1d < -max_speed:
            v1d = -max_speed
    return a4a - impulse, 0.0, v1d, used + 1


ANCHORS = {ABC_1100: {
    "Entity.Jump grounded branch: dash window _-26T + 160 > t and (_-96f or _-Xb == 1); 57 x (0.86 | 1) or 170; _-P5S = 0, _-96f = null, _-A4A -= impulse": [
        (3052, 80, "getproperty", "_-26T"),
        (3052, 84, "pushuint", "160"),
        (3052, 99, "getproperty", "_-96f"),
        (3052, 116, "getproperty", "_-Xb"),
        (3052, 579, "pushdouble", "0.86"),
        (3052, 586, "pushdouble", "1.0"),
        (3052, 596, "getproperty", "_-96f"),
        (3052, 622, "iffalse", "919"),
        (3052, 643, "pushdouble", "57.0"),
        (3052, 653, "iffalse", "228"),
        (3052, 698, "pushdouble", "170.0"),
        (3052, 989, "pushbyte", "0"),
        (3052, 991, "callpropvoid", "_-N5C::_-E1t, 2"),
        (3052, 1003, "initproperty", "_-96f"),
        (3052, 1020, "getproperty", "_-A4A"),
        (3052, 1031, "subtract", ""),
        (3052, 1048, "callpropvoid", "_-N5C::_-E1t, 2"),
    ],
    "Entity.Jump ground tail @1066-1537: _-81n or local 6; _-141 sides; _-M3V and |vx| > 4 -> -= 4; else vx -> 0; at -/+ _-K64, _-84 -/+= _-13G x 0.5": [
        (3052, 1070, "callproperty", "_-81n, 0"),
        (3052, 1090, "callproperty", "_-K64, 0"),
        (3052, 1102, "callproperty", "_-141, 0"),
        (3052, 1117, "getproperty", "_-M3V"),
        (3052, 1143, "pushbyte", "4"),
        (3052, 1175, "subtract", ""),
        (3052, 1218, "ifngt", "22"),
        (3052, 1234, "pushbyte", "0"),
        (3052, 1264, "ifnle", "56"),
        (3052, 1311, "getproperty", "_-13G"),
        (3052, 1315, "pushdouble", "0.5"),
        (3052, 1319, "subtract", ""),
        (3052, 1391, "add", ""),
        (3052, 1435, "ifnlt", "22"),
        (3052, 1480, "ifnge", "57"),
        (3052, 1535, "add", ""),
    ],
    "Entity.Jump wall jump @1545-2014: _-r51 != 0 or _-Xb == 2; _-96f = null; _-A4A -= _-S4O (53) x k; _-v1D = 0; _-84 +/-= 48 (x 0.9 away); 'jump.Wall'": [
        (3052, 1550, "getproperty", "_-r51"),
        (3052, 1571, "pushbyte", "2"),
        (3052, 1576, "iffalse", "438"),
        (3052, 1583, "callpropvoid", "_-31A, 0"),
        (3052, 1612, "initproperty", "_-96f"),
        (3052, 1619, "getproperty", "_-S4O"),
        (3052, 1629, "pushdouble", "48.0"),
        (3052, 1659, "subtract", ""),
        (3052, 1692, "pushbyte", "0"),
        (3052, 1694, "callproperty", "_-N5C::_-E1t, 2"),
        (3052, 1711, "getproperty", "_-P5S"),
        (3052, 1745, "callpropvoid", "_-CV, 1"),
        (3052, 1758, "pushbyte", "1"),
        (3052, 1805, "pushdouble", "0.9"),
        (3052, 1836, "add", ""),
        (3052, 1893, "pushdouble", "0.9"),
        (3052, 1917, "subtract", ""),
        (3052, 2005, "pushstring", "'jump.Wall'"),
    ],
    "Entity.Jump air jump @2018-2455: _-P5Y() < _-56T(); 57 x k or 65 x k (second argument); _-P5S = 0; _-A4A -= impulse; _-k1j(_-P5Y() + 1); clamp vx to _-K64(false); 'jump.Air'": [
        (3052, 2022, "callproperty", "_-P5Y, 0"),
        (3052, 2031, "callproperty", "_-56T, 0"),
        (3052, 2037, "iffalse", "386"),
        (3052, 2065, "pushdouble", "57.0"),
        (3052, 2078, "pushdouble", "65.0"),
        (3052, 2098, "pushbyte", "0"),
        (3052, 2129, "subtract", ""),
        (3052, 2172, "pushbyte", "1"),
        (3052, 2176, "callpropvoid", "_-k1j, 1"),
        (3052, 2221, "callproperty", "_-K64, 1"),
        (3052, 2262, "ifngt", "18"),
        (3052, 2308, "ifnlt", "19"),
        (3052, 2414, "pushstring", "'jump.Air'"),
        (3052, 2437, "getproperty", "_-8"),
        (3052, 2455, "initproperty", "_-I5A"),
    ],
}}
