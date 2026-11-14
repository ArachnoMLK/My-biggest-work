"""Ground look-ahead and landing lock of a fighter on patch 11.00.

`Entity.Dash` #3132, `_-i4Z._-rU` #6334 (the attack pick) and, after a drop through a soft platform,
`Entity.Jump` #3052 do not only test the ground line `_-96f`: they first probe the map and, when a line is
close enough, **put the fighter on it** (`_-P5S` = 0, y = hit y - 1.01, `_-96f` = the line). So a dash or an
attack pressed a few ticks before the landing is the ground one.

- `Entity._-w4A(t, attack, dir)` #3012: the probe of a falling fighter (`fall_reach`, `fall_probe`).
- `Entity._-y1U(t, attack, dir)` #3005: `_-w4A`, then the snap (`fall_snap`).
- `Entity._-w4c(t, attack, light, dir)` #3004: the probe upward for a soft platform just above the feet, then
  the same snap (`rise_snap`).
- `Entity._-C54(t)` #3067: the landing lock (`landing_lock`), armed by `_-8i` on the landing step of a fighter
  that jumped (`landing_marks`: `_-322`, `_-t4D`, `_-96p()` / `_-C2N`).

Ray casts go through tools/bh/raycast.py. Anchors are (method id, offset, opname, operand text as printed by
`abc-disasm`). Static evidence only: nothing here was run in the game.
"""
from .air_move import BACK_OFF, STEP, steep
from .movement import ABC_1100, check, listing
from .raycast import OPT_SOFT_BOTH_SIDES, OPT_TWO_SIDED, ray_cast

REACH_TICKS = 7            # `Entity._-D4i` = 7 x `_-z2k._-Vj` (`_-y2E.init` #15351 @30098-30108)
REACH_TICKS_FAST = 5       # `Entity._-q1p` = 5 x `_-Vj` (@30115-30125): under `_-61h()` (fast fall)
REACH_CAP = 60.0           # `Entity._-L1Z` (script157.<init> #3173 @1903)
REACH_CAP_ATTACK = 100.0   # `Entity._-F38` (@1912): `_-w4A` called with its second argument (the attack pick)
SOFT_HOLD_MS = 64          # `_-w4A` @278-287, `_-w4c` @84-102: Drop held since `_-76H` + 64
RISE, RISE_LIGHT, RISE_DROPPED = -30.0, -50.0, -70.0   # `Entity._-K61`, `_-c4c`, `_-86j` (#3173 @1923-1943)
DROP_THROUGH_MS = 192      # `Entity._-k5G` (#3173 @1950): after `_-w3i`, the last drop through a soft platform
LANDING_LOCK_MS = 64       # `_-C54` #3067 @12
HARD, SOFT, DROP = 1, 2, 2  # line types `_-z2k` 1 / 2 (collision-11.00.md); the Drop key bit


def _cands(lines):
    if hasattr(lines, "candidates"):
        return lambda x, y, dy: lines.candidates(x, y, x, y + dy)
    return lambda x, y, dy: lines


def fall_reach(p5s, fast_fall, attack=False):
    """`_-w4A` @2-131: None unless `_-P5S` > 0; else `_-P5S` x 7 x 0.384 (5 x 0.384 under `_-61h()`), at most 60
    (100 with the second argument): the length of the probe below the feet."""
    if not p5s > 0:
        return None
    reach = p5s * ((REACH_TICKS_FAST if fast_fall else REACH_TICKS) * STEP)
    cap = REACH_CAP_ATTACK if attack else REACH_CAP
    return cap if reach > cap else reach


def fall_probe(lines, team, t, x, y, p5s, fast_fall, attack=False, dir=0, h76=0):
    """`Entity._-w4A(t, attack, dir)` #3012: the RayHit of the line a falling fighter is about to land on, or None.

    A ray of `fall_reach` straight down from the feet against the hard lines (`_-X2e(team, x, y, (0, reach), out,
    null, null, null, 1, 0)`, @137-221); if none, half that length against the soft lines (mask 2, @299-400),
    unless attack with Drop in `dir` and t >= `_-76H` + 64 (@246-298). A steep line (`_-S1A`) gives None."""
    reach = fall_reach(p5s, fast_fall, attack)
    if reach is None:
        return None
    cands = _cands(lines)
    hit = ray_cast(cands(x, y, reach), team, x, y, 0.0, reach, HARD, 0)
    if hit is None:
        if attack and dir & DROP and t >= h76 + SOFT_HOLD_MS:
            return None
        half = reach * 0.5
        hit = ray_cast(cands(x, y, half), team, x, y, 0.0, half, SOFT, 0)
        if hit is None:
            return None
    if steep(hit.line):
        return None
    return hit


def fall_snap(lines, team, t, x, y, p5s, fast_fall, attack=False, dir=0, h76=0):
    """`Entity._-y1U(t, attack, dir)` #3005: with a `fall_probe` hit, `_-P5S` = 0, the fighter goes to
    (x, hit y - 1.01) (`_-x1M`) and `_-96f` = the line. Returns (y, line), or None for `false` (nothing written).
    The airborne flag `_-wn()` is not touched here: `_-8i` updates it on its next run (`landing_marks`)."""
    hit = fall_probe(lines, team, t, x, y, p5s, fast_fall, attack, dir, h76)
    if hit is None:
        return None
    return hit.point[1] - BACK_OFF, hit.line


def rise_snap(lines, team, t, x, y, p5s, w3i, attack=False, light=False, dir=0, h76=0):
    """`Entity._-w4c(t, attack, light, dir)` #3004: a soft platform just above the feet.

    dropped = `_-w3i` + 192 >= t. Not dropped, attack, `_-P5S` > 0, Drop in `dir` and t >= `_-76H` + 64: false.
    Else a ray straight up from the feet, 70 after a drop through, else 50 with `light`, else 30, against the
    soft lines with options 1 | 8 (`_-X2e(team, x, y, (0, -n), out, null, null, null, 2, 9)`, @183-272); with a
    hit, the same writes as `fall_snap`. Returns (y, line) or None."""
    dropped = w3i + DROP_THROUGH_MS >= t
    if not dropped and attack and p5s > 0 and dir & DROP and t >= h76 + SOFT_HOLD_MS:
        return None
    dy = RISE_DROPPED if dropped else (RISE_LIGHT if light else RISE)
    hit = ray_cast(_cands(lines)(x, y, dy), team, x, y, 0.0, dy, SOFT, OPT_SOFT_BOTH_SIDES | OPT_TWO_SIDED)
    if hit is None:
        return None
    return hit.point[1] - BACK_OFF, hit.line


def jump_snap(lines, team, t, x, y, p5s, fast_fall, w3i, keys, h76=0):
    """`Entity.Jump` #3052 @324-388, on its squat path only: within 192 ms of `_-w3i`, `_-w4c(t, false, false,
    keys)`, then `_-y1U(t, false)` when `_-96f` is still null. Returns (y, line) or None. [H] `ground` already
    set is the caller's business (the bytecode calls `_-w4c` whatever `_-96f` is)."""
    if not w3i + DROP_THROUGH_MS >= t:
        return None
    r = rise_snap(lines, team, t, x, y, p5s, w3i, False, False, keys, h76)
    if r is None:
        r = fall_snap(lines, team, t, x, y, p5s, fast_fall)
    return r


def landing_lock(t, t4d, airborne, r51):
    """`Entity._-C54(t)` #3067: t < `_-t4D` + 64 and not `_-wn()`, with no wall contact (`_-r51` == 0).
    While it holds: no jump (`_-H5F` #3065 @134), no dodge (`IsDodgeLocked` #3075 @198), no dash (`_-350` #3076
    @198), and `_-i4Z._-51o` #6313 @596 puts it in local 15 (no dodge, no attack on that pass)."""
    if t < t4d + LANDING_LOCK_MS and not airborne:
        return r51 == 0
    return False


def landing_marks(t, was_airborne, airborne, jumped, xb, i5a, t322, t4d):
    """`Entity._-8i` #2984 @13130-13519, after the move: local 37 = `_-wn()` before `_-v2J(_-96f == null)`
    (@13130-13169). On the ground afterwards: when local 37 (the landing step) `_-322` = t and, with `_-96p()`
    (the flag `_-C1J`, set by `Jump` #3052 @507-512 on every jump that leaves the ground or the air),
    `_-t4D` = t and a pending jump (`_-Xb` != 0) gets `_-I5A` + 64; then `_-C2N(false)` on every grounded step.
    Returns (`_-322`, `_-t4D`, `_-I5A`, jumped)."""
    if airborne:
        return t322, t4d, i5a, jumped
    if was_airborne:
        t322 = t
        if jumped:
            t4d = t
            if xb != 0:
                i5a = i5a + LANDING_LOCK_MS
    return t322, t4d, i5a, False


ANCHORS = {ABC_1100: {
    "_-w4A fall probe: P5S > 0; reach = P5S x (_-61h ? _-q1p : _-D4i), capped by _-L1Z (arg 2: _-F38); hard ray (mask 1, options 0); else soft ray at half (mask 2) unless arg 2 with Drop and t >= _-76H + 64; _-S1A -> null": [
        (3012, 21, "ifnle", "6"),
        (3012, 48, "findproperty", "_-61h"),
        (3012, 66, "getproperty", "_-q1p"),
        (3012, 77, "getproperty", "_-D4i"),
        (3012, 80, "multiply", ""),
        (3012, 93, "getproperty", "_-F38"),
        (3012, 105, "getproperty", "_-L1Z"),
        (3012, 115, "ifngt", "5"),
        (3012, 131, "getlocal", "4"),
        (3012, 216, "pushbyte", "1"),
        (3012, 219, "pushbyte", "0"),
        (3012, 221, "callproperty", "_-X2e, 10"),
        (3012, 255, "pushbyte", "2"),
        (3012, 278, "getproperty", "_-76H"),
        (3012, 282, "pushbyte", "64"),
        (3012, 308, "pushdouble", "0.5"),
        (3012, 311, "multiply", ""),
        (3012, 395, "pushbyte", "2"),
        (3012, 398, "pushbyte", "0"),
        (3012, 400, "callproperty", "_-X2e, 10"),
        (3012, 433, "getproperty", "_-S1A"),
    ],
    "_-w4A constants: _-D4i = 7 x _-Vj, _-q1p = 5 x _-Vj, _-L1Z = 60, _-F38 = 100": [
        (15351, 30098, "pushbyte", "7"),
        (15351, 30103, "getproperty", "_-Vj"),
        (15351, 30107, "multiply", ""),
        (15351, 30108, "initproperty", "_-D4i"),
        (15351, 30115, "pushbyte", "5"),
        (15351, 30120, "getproperty", "_-Vj"),
        (15351, 30124, "multiply", ""),
        (15351, 30125, "initproperty", "_-q1p"),
        (3173, 1903, "pushdouble", "60.0"),
        (3173, 1905, "initproperty", "_-L1Z"),
        (3173, 1912, "pushdouble", "100.0"),
        (3173, 1915, "initproperty", "_-F38"),
    ],
    "_-y1U snap: _-w4A(t, arg 2, arg 3); null -> false; P5S = 0, _-x1M(x, _-IV.y - 1.01), _-96f = the line": [
        (3005, 8, "callproperty", "_-w4A, 3"),
        (3005, 29, "ifne", "2"),
        (3005, 47, "pushbyte", "0"),
        (3005, 49, "callpropvoid", "_-N5C::_-E1t, 2"),
        (3005, 78, "getproperty", "_-IV"),
        (3005, 85, "pushdouble", "1.01"),
        (3005, 88, "subtract", ""),
        (3005, 89, "callpropvoid", "_-x1M, 2"),
        (3005, 97, "getlocal", "4"),
        (3005, 99, "initproperty", "_-96f"),
    ],
    "_-w4c rise snap: dropped = _-w3i + _-k5G >= t; arg 2, P5S > 0, Drop, t >= _-76H + 64 -> false; ray up _-86j / _-c4c (arg 3) / _-K61, mask 2, options 1 | 8; same writes": [
        (3004, 2, "findproperty", "_-w3i"),
        (3004, 12, "getproperty", "_-k5G"),
        (3004, 19, "greaterequals", ""),
        (3004, 59, "pushbyte", "0"),
        (3004, 61, "greaterthan", ""),
        (3004, 70, "pushbyte", "2"),
        (3004, 97, "pushbyte", "64"),
        (3004, 102, "greaterequals", ""),
        (3004, 120, "getproperty", "_-36K"),
        (3004, 127, "getproperty", "_-86j"),
        (3004, 147, "getproperty", "_-36K"),
        (3004, 154, "getproperty", "_-c4c"),
        (3004, 169, "getproperty", "_-36K"),
        (3004, 176, "getproperty", "_-K61"),
        (3004, 262, "pushbyte", "2"),
        (3004, 265, "pushbyte", "1"),
        (3004, 268, "pushbyte", "8"),
        (3004, 271, "bitor", ""),
        (3004, 272, "callproperty", "_-X2e, 10"),
        (3004, 311, "pushbyte", "0"),
        (3004, 313, "callpropvoid", "_-N5C::_-E1t, 2"),
        (3004, 345, "getproperty", "y"),
        (3004, 349, "pushdouble", "1.01"),
        (3004, 352, "subtract", ""),
        (3004, 353, "callpropvoid", "_-x1M, 2"),
        (3004, 361, "getlocal", "6"),
        (3004, 363, "initproperty", "_-96f"),
    ],
    "_-w4c constants: _-K61 = -30, _-c4c = -50, _-86j = -70, _-k5G = 192": [
        (3173, 1923, "pushdouble", "-30.0"),
        (3173, 1925, "initproperty", "_-K61"),
        (3173, 1932, "pushdouble", "-50.0"),
        (3173, 1934, "initproperty", "_-c4c"),
        (3173, 1941, "pushdouble", "-70.0"),
        (3173, 1943, "initproperty", "_-86j"),
        (3173, 1950, "pushuint", "192"),
        (3173, 1952, "initproperty", "_-k5G"),
    ],
    "Dash: local 3 = _-y1U(t, false), else with a side local 6 = _-w4c(t, false, false, dir), both before the _-96f test; local 18 = (local 6 and P5S < 0) or local 3 (speed gate 7, else 15)": [
        (3132, 134, "pushfalse", ""),
        (3132, 135, "callproperty", "_-y1U, 2"),
        (3132, 144, "pushtrue", ""),
        (3132, 152, "getlocal", "4"),
        (3132, 159, "findproperty", "_-w4c"),
        (3132, 163, "pushfalse", ""),
        (3132, 164, "pushfalse", ""),
        (3132, 166, "callproperty", "_-w4c, 4"),
        (3132, 176, "pushtrue", ""),
        (3132, 180, "findproperty", "_-96f"),
        (3132, 191, "ifeq", "1239"),
        (3132, 622, "getlocal", "6"),
        (3132, 629, "getlocal", "7"),
        (3132, 633, "lessthan", ""),
        (3132, 640, "getlocal_3", ""),
        (3132, 651, "pushdouble", "7.0"),
        (3132, 657, "pushdouble", "15.0"),
    ],
    "_-rU attack pick: air offset 3 (0 under the cancel); in the air without arg 3, _-y1U(t, true, dir) -> ground slot, local 14; with Drop, _-w4c(t, true, arg 4 == 0, dir) the same; local 14 -> _-C2N(false); _-C5S false with local 14 -> P5S, y and _-96f put back": [
        (6334, 112, "callproperty", "_-wn, 0"),
        (6334, 122, "getlocal_3", ""),
        (6334, 128, "pushbyte", "3"),
        (6334, 141, "getlocal", "5"),
        (6334, 147, "pushbyte", "0"),
        (6334, 165, "getlocal_3", ""),
        (6334, 180, "pushtrue", ""),
        (6334, 183, "callproperty", "_-y1U, 3"),
        (6334, 197, "pushbyte", "0"),
        (6334, 413, "pushbyte", "2"),
        (6334, 447, "getlocal_3", ""),
        (6334, 462, "pushtrue", ""),
        (6334, 465, "pushbyte", "0"),
        (6334, 467, "equals", ""),
        (6334, 470, "callproperty", "_-w4c, 4"),
        (6334, 484, "pushbyte", "0"),
        (6334, 606, "getlocal", "14"),
        (6334, 618, "pushfalse", ""),
        (6334, 619, "callpropvoid", "_-C2N, 1"),
        (6334, 729, "getlocal", "14"),
        (6334, 757, "getlocal", "9"),
        (6334, 759, "callpropvoid", "_-N5C::_-E1t, 2"),
        (6334, 785, "getlocal", "11"),
        (6334, 787, "callpropvoid", "_-N5C::_-E1t, 2"),
        (6334, 797, "getlocal", "12"),
        (6334, 799, "initproperty", "_-96f"),
    ],
    "Jump squat path: within _-k5G of _-w3i, _-w4c(t, false, false, keys) then _-y1U(t, false) if _-96f is null; the jump path sets _-C2N(true)": [
        (3052, 324, "findproperty", "_-w3i"),
        (3052, 334, "getproperty", "_-k5G"),
        (3052, 341, "greaterequals", ""),
        (3052, 350, "pushfalse", ""),
        (3052, 351, "pushfalse", ""),
        (3052, 364, "callpropvoid", "_-w4c, 4"),
        (3052, 379, "ifne", "9"),
        (3052, 387, "pushfalse", ""),
        (3052, 388, "callpropvoid", "_-y1U, 2"),
        (3052, 511, "pushtrue", ""),
        (3052, 512, "callpropvoid", "_-C2N, 1"),
    ],
    "_-C54 landing lock: t < _-t4D + 64 and not _-wn() -> _-r51 == 0, else false; read by _-51o local 15, IsDodgeLocked": [
        (3067, 4, "findproperty", "_-t4D"),
        (3067, 12, "pushbyte", "64"),
        (3067, 17, "lessthan", ""),
        (3067, 26, "callproperty", "_-wn, 0"),
        (3067, 37, "findproperty", "_-r51"),
        (3067, 47, "equals", ""),
        (6313, 596, "callproperty", "_-C54, 1"),
        (3075, 198, "callproperty", "_-C54, 1"),
    ],
    "_-8i landing marks: local 37 = _-wn() before _-v2J(_-96f == null); grounded: with local 37 _-322 = t and, with _-96p(), _-t4D = t (_-Xb != 0: _-I5A + 64); then _-C2N(false); _-96p reads _-C1J, _-C2N writes it": [
        (2984, 13133, "callproperty", "_-wn, 0"),
        (2984, 13139, "setlocal", "37"),
        (2984, 13163, "pushnull", ""),
        (2984, 13168, "equals", ""),
        (2984, 13169, "callpropvoid", "_-v2J, 1"),
        (2984, 13430, "callproperty", "_-wn, 0"),
        (2984, 13440, "getlocal", "37"),
        (2984, 13446, "findproperty", "_-322"),
        (2984, 13451, "initproperty", "_-322"),
        (2984, 13458, "callproperty", "_-96p, 0"),
        (2984, 13467, "findproperty", "_-t4D"),
        (2984, 13472, "initproperty", "_-t4D"),
        (2984, 13480, "getproperty", "_-Xb"),
        (2984, 13505, "pushbyte", "64"),
        (2984, 13510, "initproperty", "_-I5A"),
        (2984, 13518, "pushfalse", ""),
        (2984, 13519, "callpropvoid", "_-C2N, 1"),
        (2936, 6, "getproperty", "_-C1J"),
        (2894, 2, "findproperty", "_-C1J"),
        (2894, 6, "findproperty", "_-W2b"),
        (2894, 9, "getlocal_1", ""),
        (2894, 15, "initproperty", "_-C1J"),
    ],
    "_-D1o: at t == _-t4D (outside _-Ep) the cosmetic power PowerType._-65Q (LandingRecoverCloud) is spawned": [
        (3165, 11, "pushbyte", "0"),
        (3165, 19, "findproperty", "_-t4D"),
        (3165, 27, "equals", ""),
        (3165, 41, "getproperty", "_-65Q"),
        (3165, 50, "callpropvoid", "_-33h, 3"),
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
