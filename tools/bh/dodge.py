"""The commit part of `Entity.Dodge` #3125 on patch 11.00: what a dodge writes on the fighter the tick it starts.

See docs/hit-detection-11.00.md §10.2. `_-i4Z._-51o` #6313 @2418-2433 calls `owner.Dodge(t, keys & 15, held)`
on a buffered DodgeDash (256) press (input-buffer-11.00.md, PR #28). This module transcribes the writes made
once Dodge has decided to dodge (@1024-2288). The gates before it (@0-1022: `IsDodgeLocked`, the chained
dodge `_-26R`, `Dash`, the ground `_-96f`) are in `gates`. The motion during the dodge is
in the dodge state of `Entity._-8i` and is not transcribed yet.

Names: `dir` is Dodge's second argument (`keys & 15`: Up 1, Drop 2, Left 4, Right 8). `_-wn()` is called
`airborne` here: `_-26O` maps it to the DodgeTypes mask 2, the value of 'Air' (#2768 @312-323) [V]. The DodgeType is
`_-h3i._-26O(dir, airborne, local 8, team flag 64, local 10)`, a row of DodgeTypes.xml (`_-h3i._-i32`).
[V] unless marked [H].
"""
import xml.etree.ElementTree as ET

from .movement import ABC_1100

FRAME_MS = 16              # @1491 / @1507: `mDuration` and `_-53o` are in frames, x 16
LEFT, RIGHT = 4, 8         # dir bits, @1101 / @1127
COUNT_SHIFT = 16           # `_-6K` >>> 16 is a dodge counter, the low 16 bits a kind (@1708-1873)
LOW_MASK = 65535


def facing(dir, current):
    """@1100-1164: `_-n3h` = true with Left, false with Right, else `_-r35()` (`current`)."""
    if dir & LEFT:
        return True
    if dir & RIGHT:
        return False
    return current


def timers(t, duration_frames, recover_frames, has_t3v, z4s, chain_end=0):
    """@1482-1705: the dodge timers, as a dict.

    `_-Uy` = mDuration x 16, `_-C1d` = `_-53o` x 16, `_-T2R` = t + `_-Uy`, `_-G6S` = t + `_-Uy` + `_-C1d` (only
    with the type's `_-t3v`, else None = left as it was), `_-y1F` = `_-Uy` + `_-Z4S(type, ...)` + `_-C1d`.
    `chain_end` is local 5 (`_-H2b` + `_-y1F` of the dodge being chained, set @241-258; 0 otherwise): when it
    is set and t + `_-y1F` < it, `_-y1F` = chain_end − t, so a chained dodge never ends before the previous one.
    `_-H2b` = t (@1084-1089). [H] `_-Z4S` is an extra recovery in ms; not read yet.
    """
    uy = duration_frames * FRAME_MS
    c1d = recover_frames * FRAME_MS
    y1f = uy + z4s + c1d
    if chain_end and t + y1f < chain_end:
        y1f = chain_end - t
    return {"_-H2b": t, "_-Uy": uy, "_-C1d": c1d, "_-T2R": t + uy,
            "_-G6S": t + uy + c1d if has_t3v else None, "_-y1F": y1f}


def clears_velocity(dir, airborne):
    """@1876-1937: with a direction or in the air (`_-wn()`), `_-P5S` and `_-v1D` are set to 0. A neutral ground dodge
    keeps them (after the `_-v1D` = ±`_-K64` write of @1290-1446 when the type has `_-t3v` and `_-a5a`)."""
    return dir != 0 or airborne


def neutral_push(k64, dir):
    """@1407-1446: the value written to `_-v1D` when the type has `_-t3v` and `_-a5a` != 0: `_-K64(...)`, negated
    when `_-O5C` (= dir) has Left. [H] It survives only when `clears_velocity` is false, so with dir == 0."""
    return -k64 if dir & LEFT else k64


def counter(k6, chained, has_dir_bits, airborne, f2b, e6p=False):
    """`_-6K` after the dodge (@499-520, @1708-1873). The count is `_-6K` >>> 16.

    @499: without `_-E6P()` and not chained (local 7), the count is cleared first. Then the low half is
    reset: when `_-f2b()`, a chained dodge with a direction (local 15) sets it to 2 in the air, else 1; a
    fresh dodge on the ground (not `_-wn()`) with a direction sets it to 1. If the low half is then non-zero or the dodge is chained,
    the count is the old count + 1; otherwise `_-6K` stays 0 (count lost). [H] `_-f2b`, `_-E6P` meanings.
    """
    if not e6p and not chained:
        k6 &= LOW_MASK
    count = k6 >> COUNT_SHIFT
    k6 = 0
    if f2b:
        if chained:
            if has_dir_bits:
                k6 = 2 if airborne else 1
        elif not airborne and has_dir_bits:
            k6 = 1
    if k6 != 0 or chained:
        k6 = ((count + 1) << COUNT_SHIFT) | (k6 & LOW_MASK)
    return k6


# DodgeTypes.xml columns (`_-h3i._-I6L` #2768) -> fields used here.
COLUMNS = {"DodgeName": "_-86E", "DodgeID": "_-B3q", "Set": "_-p1r", "Air/Ground/Both": "_-6H",
           "direction (Neutral, Side, Up, Down, SideUp, SideDown)": "_-h2L", "IsFast": "_-t3v",
           "Duration": "mDuration", "Recover": "_-53o", "SpeedXMult": "_-a5a", "Cooldown": "_-p2U",
           "CooldownGround": "_-S6E", "CooldownLanded": "_-T2A",
           "AccelXFormula": "_-K35", "AccelXMult": "_-r4O", "AccelYFormula": "_-F5s", "AccelYMult": "_-k4q",
           "ExitBackX": "_-i16", "ExitBackY": "_-73o", "ExitX": "_-05s", "ExitY": "_-LX", "PostDodge": "_-f6R",
           "CancelLimit": "_-GX", "CancelStart": "_-M4L", "StartInvuln": "_-553"}
KIND_SIDE, KIND_UP, KIND_DOWN = 1, 2, 4           # @660-742: Neutral 0, Side 1, Up 2, Down 4, SideUp 3, SideDown 5
WHERE_GROUND, WHERE_AIR, WHERE_BOTH = 1, 2, 3     # @357-369 / @312-323; Both = `_-h3i._-I6u` = 1 | 2 (#15351 @27965-27972)
FALLBACK = "StandardSpot"                         # @1526-1539: the row named StandardSpot is `_-h3i._-Z6`


def kind(dir):
    """`_-26O` #2770 @11-89: Side when Left or Right, then Up (1) wins over Drop (2)."""
    k = KIND_SIDE if dir & (LEFT | RIGHT) else 0
    if dir & 1:
        k |= KIND_UP
    elif dir & 2:
        k |= KIND_DOWN
    return k


def pick(rows, dir, airborne, is_fast, test_set=False):
    """`_-h3i._-26O` #2770: the first row of `_-w14` (file order [H]) with Set == "Test" / "Default",
    direction == kind(dir), Air/Ground/Both covering the fighter (2 when `_-wn()`, i.e. in the air, else 1) and IsFast ==
    is_fast; else the StandardSpot row. Rows are dicts with the keys "Set", "kind", "where", "IsFast", "DodgeName".
    In Dodge, `test_set` is the team flag 64 (`_-N1k._-d3Y._-Z2Y` & 64) and `is_fast` is its local 8."""
    want_set = "Test" if test_set else "Default"
    k = kind(dir)
    mask = WHERE_AIR if airborne else WHERE_GROUND
    for r in rows:
        if r["Set"] == want_set and r["kind"] == k and r["where"] & mask and bool(r["IsFast"]) == bool(is_fast):
            return r
    return next((r for r in rows if r.get("DodgeName") == FALLBACK), None)


UINT_COLUMNS = ("CancelLimit", "CancelStart", "Cooldown", "CooldownGround", "CooldownLanded", "DodgeID",
                "Duration", "FromBackDashDelay", "FromDashDelay", "PostDodge", "Recover", "StartInvuln",
                "ToDashDelay")                                   # `_-N2e._-vD` -> convert_u
FLOAT_COLUMNS = ("AccelXMult", "AccelYMult", "ExitBackX", "ExitBackY", "ExitX", "ExitY", "SpeedXMaxMult",
                 "SpeedXMult", "SpeedYMaxMult", "SpeedYMult")  # `_-N2e._-U13` -> convert_d
DIRECTIONS = {"Neutral": 0, "Side": KIND_SIDE, "Up": KIND_UP, "Down": KIND_DOWN,
              "SideUp": KIND_SIDE | KIND_UP, "SideDown": KIND_SIDE | KIND_DOWN}
AIR_TYPES = {"Ground": WHERE_GROUND, "Air": WHERE_AIR, "Both": WHERE_BOTH}


def parse_types(xml_text):
    """DodgeTypes.xml as `_-h3i._-i32` #2767 / `_-I6L` #2768 load it: one row per DodgeType child, in file
    order [H: `_-ET()` iterates in document order]. Unsigned columns are ints, the Mult / Exit columns floats,
    IsFast is TRUE / FALSE (`_-Qr`, [H] case-insensitive), the rest strings; Direction -> "kind", AirType ->
    "where". A row with DodgeID 0 (the Template) is dropped (@1450-1462); "StandardSpot" is the fallback
    `_-Z6`. Returns (rows = `_-w14`, {DodgeID: row} = `_-Z4V`, a later duplicate id wins)."""
    rows, by_id = [], {}
    for node in ET.fromstring(xml_text):
        r = {"DodgeName": node.get("DodgeName")}
        for c in node:
            text = (c.text or "").strip()
            if c.tag in UINT_COLUMNS:
                r[c.tag] = int(float(text)) & 0xFFFFFFFF if text else 0
            elif c.tag in FLOAT_COLUMNS:
                r[c.tag] = float(text) if text else 0.0
            elif c.tag == "IsFast":
                r[c.tag] = text.upper() == "TRUE"
            else:
                r[c.tag] = text
        if "Direction" in r:
            r["kind"] = DIRECTIONS[r["Direction"]]
        if "AirType" in r:
            r["where"] = AIR_TYPES[r["AirType"]]
        if not r.get("DodgeID"):
            continue
        by_id[r["DodgeID"]] = r
        rows.append(r)
    return rows, by_id


STANDARD_WINDOW_MS = 64    # `_-h3i._-M4C` (script148.<init> #2774 @186-189)


def standard_flag(t, airborne, i5a, p5y):
    """`_-h3i._-B15` #2771 @73-142 (local 7, the `_-K64` argument): `_-wn()`, `_-I5A` != 0, `_-P5Y()` == 0 and
    `_-I5A` + 64 >= t (a jump squat started within 64 ms)."""
    return airborne and i5a != 0 and p5y == 0 and i5a + STANDARD_WINDOW_MS >= t


def k64(flag, airborne, z2v, u5j, m1u, o4k):
    """`Entity._-K64(flag)` #3093: AirRunSpeed (`_-z2v`) x `_-Kc._-u5j` when `_-wn()` and not flag, else
    RunSpeed (`_-M1U`) x `_-Kc._-04K`: the same products as the `_-8i` max speeds (horizontal.py), without
    the x 1.16 of `_-w47`. So the StandardHorizontal flag (a fresh jump squat) uses the ground speed."""
    if airborne and not flag:
        return z2v * u5j
    return m1u * o4k


LANDED_DELAY_MS = 240      # `Entity._-l2o` (script157.<init> #3173 @882)
DASH_HOLD_MS = 112         # `Entity._-y4m` (script157.<init> #3173 @800)


def landed_cooldown(y1f, airborne, r51, hitstun, a1h, q42, t, i46, cooldown_landed, uy, c1d):
    """`Entity._-t1A(t, a)` #2992 @40-230, run each tick from `_-8i` @2659: on the ground (not `_-wn()`), off a
    wall (`_-r51` == 0), not in hitstun (`_-5q()`), `_-a1h` clear, with a DodgeType (`_-Q42` != 0) and
    t >= `_-46I` + 240, `_-y1F` is capped to CooldownLanded (`_-T2A`) x 16 + `_-Uy` + `_-C1d`. [H] `_-a1h`."""
    if not airborne and r51 == 0 and not hitstun and not a1h and q42 != 0 and t >= i46 + LANDED_DELAY_MS:
        cap = cooldown_landed * FRAME_MS + uy + c1d
        if y1f > cap:
            return cap
    return y1f


def dodge_over(t, u5e, h2b, y1f, e3):
    """`_-t1A` @233-349: with `_-u5E()`, `_-H2b` + `_-y1F` <= t and not within 112 ms of `_-3E` (local 5,
    `_-3E` + 112 > t), the dodge is over: `_-Kc._-MX(PowerType._-Z32)` when `_-H2b` > 0, `_-H2b` = 0, then
    `_-51c(false, true)`. Returns (over, calls_mx). [H] `_-u5E()`, `_-3E` (also read by Dash), `_-MX`, `_-51c`."""
    over = bool(u5e) and h2b + y1f <= t and not (e3 + DASH_HOLD_MS > t)
    return over, over and h2b > 0


FLAG_24F = 4096            # `Entity._-24F` (script157.<init> #3173 @1165): an `_-e3e` bit that stops the push


def moves(h2l, where):
    """`_-t1A` @367-400 (local 6): false only for a Neutral (`_-h2L` == 0) ground-only (`_-6H` == 1) type."""
    return not (h2l == 0 and where == WHERE_GROUND)


def ease(formula, t, h2b, uy, c1d):
    """`_-h3i._-I5a(t, formula, fighter)` #2772: "EaseHorizontal": e = (t - `_-H2b`) / (`_-Uy` + `_-C1d`),
    1 + 2.5 e while e < 0.25, else 1 - e / 3; anything else: 1. [H] the uint wrap of t < `_-H2b` is not
    reached: the caller runs only from `_-H2b` on."""
    if formula != "EaseHorizontal":
        return 1.0
    e = ((t - h2b) & 0xFFFFFFFF) / float((uy + c1d) & 0xFFFFFFFF)
    return 1 + e * 2.5 if e < 0.25 else 1 - e / 3


def push(t, h2b, e3e, moving, t5l, wl, ax_mult, ay_mult, ax_formula, ay_formula, uy, c1d, o5c):
    """`_-t1A` @1854-2097, the tick of a dodge still under way (`_-H2b` + `_-Uy` + `_-C1d` > t): from t >= `_-H2b`
    with the `_-e3e` bit 4096 clear and a moving type, `_-v1D` = `_-P5S` = 0, then the impulses
    `_-84` = ±60 `_-T5L` AccelXMult ease(AccelXFormula) (negative with Left in `_-O5C`, 0 without a side) and
    `_-A4A` = 60 `_-WL` AccelYMult ease(AccelYFormula). Returns None when nothing is written, else (`_-84`, `_-A4A`). `_-8i` calls `_-t1A` @2659, before its
    impulse folds (x @2790-2965, y @4217-4395; `step.fold_impulse` on integration), so the push lands this tick."""
    if t < h2b or e3e & FLAG_24F or not moving:
        return None
    vx = 60.0 * t5l * ax_mult * ease(ax_formula, t, h2b, uy, c1d)
    vy = 60.0 * wl * ay_mult * ease(ay_formula, t, h2b, uy, c1d)
    return (-vx if o5c & LEFT else vx if o5c & RIGHT else 0.0), vy


def side_latch(l4a, g5e, held):
    """`_-t1A` @2101-2300 (same gate as `push`, any type): only Left held (`_-R5q._-66U`) with `_-l4A` or
    `_-g5E` clear sets both true; else only Right held with `_-l4A` clear or `_-g5E` set sets `_-l4A` = true,
    `_-g5E` = false. Returns (`_-l4A`, `_-g5E`). [H] the side pressed during the dodge, for its end."""
    if (not l4a or not g5e) and held & LEFT and not held & RIGHT:
        return True, True
    if (not l4a or g5e) and held & RIGHT and not held & LEFT:
        return True, False
    return l4a, g5e


UP, DROP = 1, 2


def exit_speed(a):
    """`_-t1A` @618-648: a + (60 - a) x 1.5 x (a / 60)^2, a = the max speed of the move step (`_-8i` local 7,
    `horizontal` max speed, x 1.25 under the `_-H1g._-m47` gate @2018-2052)."""
    m = a / 60.0
    m = m * m
    return a + (60.0 - a) * m * 1.5


def exit_velocity(vx, vy, a, moving, held, l4a, g5e, t5l, exit_x, exit_back_x, exit_y, exit_back_y):
    """`_-t1A` @568-1846, the tick the dodge timer ends (`_-H2b` + `_-Uy` + `_-C1d` <= t) when `_-u5E()` is false.

    vx = `_-v1D`, vy = `_-P5S`, held = `_-R5q._-66U`. In order: a moving vx (!= 0) becomes ±exit_speed(a) (its
    sign) for a moving type; with a side held or `_-l4A` clear, a moving type's vx going right without Right
    held (left without Left held) is x ExitBackX when the other side is held, else x ExitX, and only Left
    (only Right) held faces left (right) through `_-CV`; with `_-l4A` set and no side held, a moving type's vx
    is x ExitBackX when it goes the latched way (right with `_-g5E`, left without) [H], else x ExitX, then
    `_-CV(_-g5E)`; a moving type's vx is x `_-T5L`. vy going down without Drop (up without Up) is x ExitBackY
    with the other key held, else x ExitY, for any type. Then `_-51c(true, false)`, `_-T5L` = `_-WL` = 1 and
    `_-w47` = false when `_-141()` != `_-n3h`. Returns (vx, vy, cv) with cv the `_-CV` argument or None.
    [H] `_-CV` sets the facing (true = left)."""
    if (vx > 0 or vx < 0) and moving:
        m = exit_speed(a)
        vx = -m if vx < 0 else m
    cv = None
    if held & (LEFT | RIGHT) or not l4a:
        if vx > 0 and not held & RIGHT and moving:
            vx *= exit_back_x if held & LEFT else exit_x
        elif vx < 0 and not held & LEFT and moving:
            vx *= exit_back_x if held & RIGHT else exit_x
        if held & LEFT and not held & RIGHT:
            cv = True
        elif held & RIGHT and not held & LEFT:
            cv = False
    else:
        if moving:
            vx *= exit_back_x if (vx > 0 and g5e) or (vx < 0 and not g5e) else exit_x
        cv = g5e
    if moving:
        vx *= t5l
    if vy > 0 and not held & DROP:
        vy *= exit_back_y if held & UP else exit_y
    elif vy < 0 and not held & UP:
        vy *= exit_back_y if held & DROP else exit_y
    return vx, vy, cv


DASH_TAP_MS = 192          # Entity.Dash #3132 @510-542: three side taps within 192 ms of each other
DASH_WINDOW_MS = 80        # @399, local 17; 160 with side + Drop (@393) or within 160 ms of `_-K1k` (@411-421)
DASH_WINDOW_LONG_MS = 160
DASH_REPEAT_MS = 96        # @799: a dash that keeps its side needs t >= `_-K1k` + 96
DASH_TURN_LOCK_MS = 640    # @764-772: `_-26T` + 320 + 320
DASH_SPEED_TURN, DASH_SPEED_TURN_FAST = 15.0, 7.0   # @651-657, local 19


def dash(t, dir, y1u, w4c, grounded, held, held_left, facing_left, ve, v22, r3l, t5z, m3v, k1k, d532, e3, m3h,
         vx, vy, l3a, t26, w47):
    """`Entity.Dash(t, dir)` #3132, called by Dodge (@416) with `dir` = `keys & 15`. Returns None for false
    (nothing written), else the writes as a dict (`dir_left` is the `_-CV` / `_-q2o` argument, local 16).

    y1u = `_-y1U(t, false)` (local 3); w4c = `_-w4c(t, false, false, dir)`, only called with a side in dir and
    y1u false (local 6). Not grounded (`_-96f` null): false. held = `_-R5q._-66U`, held_left = `_-141()`,
    facing_left = `_-r35()`; ve / v22 / r3l = `_-VE` / `_-V22` / `_-r3L`, the last side-tap times (newest first,
    shifted with t in locals only when the press turns the held side, without `_-t5z`). The dash goes left
    (local 13) with Left held, or facing left without Right. local 16 starts as the facing, then: within the
    window (80, 160 with side + Drop or after `_-K1k` + 160) of `_-532` or `_-3E` it is `_-M3h`; else three taps
    192 ms apart without `_-M3V` turn it to the dash side (the other side with Drop); else without `_-t5z` and
    `_-M3V`, within the window of the last tap it is the other side. local 18 = (w4c and vy < 0) or y1u (speed
    gate 7, else 15); without w4c it is cleared when local 16 differs from the dash side, and when set local 16
    is the dash side. A turn (local 16 != dash side) in kind 3 / 7 with `_-M3V` or before `_-26T` + 640: false; a
    non-turn before `_-K1k` + 96: false. Kind `_-L3a`: turn with |vx| >= gate 7; local 18 6; turn with `_-M3V`
    7; turn 3; `_-M3V` after 3 / 7 5; `_-M3V` 4 (`_-K1k` = t when `_-w47`, `_-w47` = false); y1u 2; else 1.
    Then `_-CV` / `_-q2o`(local 16), `_-v3x` = t, `_-P50` = true, `_-M3V` = false, `_-t5z` = true, `_-Q3q()`,
    `_-G6S` = 0, `_-K53._-p3c` + 1. Kind 2 is never reached: y1u sets local 18, which gives 6 or is cleared
    on a turn. The 'dash.Forward' / 'dash.Back' cue and the `_-O2r` record are not
    transcribed. [H] meanings of the kinds, `_-y1U`, `_-w4c`, `_-532`, `_-M3h`, `_-K1k`, `_-26T`."""
    side = dir & (LEFT | RIGHT) != 0
    drop = dir & DROP != 0
    if y1u:
        w4c = False
    elif not side:
        w4c = False
    if not grounded:
        return None
    left = held & LEFT != 0 or (facing_left and not held & RIGHT)
    if not t5z and side and left != held_left:
        ve, v22, r3l = t, ve, v22
    out = facing_left
    window = DASH_WINDOW_LONG_MS if side and drop else DASH_WINDOW_MS
    if k1k + DASH_WINDOW_LONG_MS > t:
        window = DASH_WINDOW_LONG_MS
    if d532 + window > t or e3 + window > t:
        out = m3h
    elif (not m3v and side and r3l > 0 and v22 + DASH_TAP_MS >= ve and r3l + DASH_TAP_MS >= v22
          and ve + DASH_TAP_MS >= t):
        out = (not left) if drop else left
    elif not t5z and not m3v and ve + window > t:
        out = not left
    fast = (w4c and vy < 0) or bool(y1u)
    gate = DASH_SPEED_TURN_FAST if fast else DASH_SPEED_TURN
    if not w4c and out != left:
        fast = False
    if fast:
        out = left
    turn = out != left
    if turn and l3a in (3, 7) and (m3v or t26 + DASH_TURN_LOCK_MS > t):
        return None
    if not turn and k1k + DASH_REPEAT_MS > t:
        return None
    w = {}
    if turn and abs(vx) >= gate:
        kind = 7
    elif fast:
        kind = 6
    elif turn and m3v:
        kind = 7
    elif turn:
        kind = 3
    elif m3v and l3a in (3, 7):
        kind = 5
    elif m3v:
        if w47:
            w["_-K1k"] = t
        w["_-w47"] = False
        kind = 4
    elif y1u:
        kind = 2
    else:
        kind = 1
    w.update({"_-L3a": kind, "dir_left": out, "_-v3x": t, "_-P50": True, "_-M3V": False, "_-t5z": True,
              "_-G6S": 0})
    return w


def cancel_flags(t, in_dodge, f2b, light, heavy, taunt, pickup, dodge_press, h2b, chase_ok, move_no_chain, o5c,
                 cancel_start, cancel_limit):
    """`_-i4Z._-51o` #6313 @1989-2342 (input buffer, PR #28): the dodge-cancel flags (local 32, 33, 34).

    in_dodge = local 36 = `_-E6P()` with a DodgeType (`_-Q42`); nothing is set otherwise. light / heavy / taunt
    / pickup / dodge_press are the buffered press times (locals 18, 20, 22, 26, 23; 0 = none); f2b = `_-f2b()`
    (local 37); chase_ok = `_-26R(t)`, called only when f2b and a dodge press newer than `_-H2b`: then local 34
    (chase dodge) and nothing else. Else local 38 = f2b with light, heavy, taunt or pick-up; local 39 = light,
    heavy or taunt, with no running single-part move (move_no_chain = local 10) or a taunt alone, and without
    local 38 or with `_-O5C` == 0. With 38 or 39, inside `_-H2b` + 16 CancelStart <= t <= `_-H2b` + 16
    CancelLimit: local 32, and local 33 with 39. Returns (32, 33, 34). [H] `_-f2b`, `_-26R`."""
    if not in_dodge:
        return False, False, False
    if f2b and dodge_press != 0 and dodge_press > h2b and chase_ok:
        return False, False, True
    l38 = f2b and (light | heavy | taunt | pickup) != 0
    l39 = ((light | heavy | taunt) != 0 and (not move_no_chain or (taunt != 0 and (light | heavy) == 0))
           and (not l38 or o5c == 0))
    if (l39 or l38) and h2b + cancel_start * FRAME_MS <= t <= h2b + cancel_limit * FRAME_MS:
        return True, l39, False
    return False, False, False


CANCEL_CAP = 60.0          # `Entity._-bC` #3041 @83-107


def cancel_end(vx, vy, t5l, wl, ax_mult, ay_mult, o5c, gc, uy, cooldown, airborne):
    """`Entity._-bC(t, gc)` #3041, called by `_-rU` when a move starts in the cancel window (gc = local 33).
    With no DodgeType (`_-Q42`) it returns at once (not modelled here). cx = min(60 `_-T5L` AccelXMult, 60), cy = min(60 `_-WL`
    AccelYMult, 60); |vx| > |cx|: vx = ±cx by `_-O5C` (Left -, Right +, else 0); |vy| > |cy|: vy = cy (no sign).
    `_-w5G(false)`, `_-T2R` = 0, `_-51c(true, true)`. With gc: `_-a1h` = true (so `landed_cooldown` no longer
    caps), `_-y1F` = `_-Uy` + Cooldown x 16, and in the air the running power's `_-I2g` |= 2. Returns a dict."""
    cx = 60.0 * t5l * ax_mult
    if cx > CANCEL_CAP:
        cx = CANCEL_CAP
    cy = 60.0 * wl * ay_mult
    if cy > CANCEL_CAP:
        cy = CANCEL_CAP
    w = {"_-T2R": 0}
    if abs(vx) > abs(cx):
        w["_-v1D"] = -cx if o5c & LEFT else cx if o5c & RIGHT else 0.0
    if abs(vy) > abs(cy):
        w["_-P5S"] = cy
    if gc:
        w["_-a1h"] = True
        w["_-y1F"] = uy + cooldown * FRAME_MS
        w["power_I2g_or_2"] = bool(airborne)
    return w


AIR_OFFSET = 3             # `_-i4Z._-rU` #6334 @128: the air moves are 3 slots after the ground ones


def attack_air_offset(airborne, jump_flag, cancel, y1u):
    """`_-i4Z._-rU(t, dir, jump, 0, cancel, window)` #6334 @105-200: the slot offset (local 15) is 3 when
    `_-wn()` or the jump flag, then 0 with `cancel` (local 33 of #6313): **the gravity cancel**, an attack in the
    cancel window of a dodge takes a ground move even in the air. Else, in the air without the jump flag, when
    y1u = `_-y1U(t, true, dir)`, the offset is 0 too and local 14 is set (`_-P5S`, `_-75K` and `_-96f` are put
    back if `_-C5S` fails, @729-799). Returns (offset, local 14). [H] `_-y1U` (a ground probe)."""
    off = AIR_OFFSET if airborne or jump_flag else 0
    if cancel:
        off = 0
    if off != 0 and not jump_flag and y1u:
        return 0, True
    return off, False


MOVE_DODGE_MS = 192        # `Entity._-84e` (script157.<init> #3173 @812)


def c2e(t, dir, d532, m3h, grounded):
    """`Entity._-C2E(t, dir)` #3073 (Dodge local 4): false once `_-532` + 192 < t (`_-532` = the start of the last
    move / pick-up), with Left and `_-M3h` clear or Right and `_-M3h` set, with dir 0, or with Drop alone on the
    ground; else true. [H] a dodge out of a move that just started."""
    if d532 + MOVE_DODGE_MS < t:
        return False
    if (dir & LEFT and not m3h) or (dir & RIGHT and m3h):
        return False
    if dir == 0 or (grounded and dir == DROP):
        return False
    return True


LOCK_X2C = 9               # IsDodgeLocked #3075 @216: `_-x2C` >= 9 locks when nothing else does


def is_dodge_locked(move_locked, u5e, flag, e6p, power, r51, area, xb, c54, x2c):
    """`Entity.IsDodgeLocked(t, flag=false)` #3075: true when `IsMoveLocked(t)`, `_-u5E()` (cooldown running) and
    not flag, `_-E6P()` (dodging), a power runs (`_-Kc._-o3I`), on a wall (`_-r51`), the `_-N1k._-I1f._-12J(1,
    _-M43, _-E3d, _-25G)` area test, a pending jump (`_-Xb`) or `_-C54(t)`; else `_-x2C` >= 9. Each test is
    made only while the earlier ones are false. [H] `_-12J`, `_-x2C`."""
    if move_locked or (u5e and not flag) or e6p or power or r51 != 0 or area or xb != 0 or c54:
        return True
    return x2c >= LOCK_X2C


def flags_51c(a, b, a1h, k6):
    """`Entity._-51c(a, b)` #3027: `_-E5I(a)` (so `_-u5E()` = a, the cooldown flag `_-l4c`), `_-Kc._-53P` = 0,
    `_-a1h` = false unless a, `_-6K` = 0 with b. `_-E6P()` is the other flag, `_-y1o`, written by `_-w5G`
    (#2899): true at the dodge commit (#3125 @1080), false at the timer end. Returns (u5e, a1h, k6)."""
    return a, (a1h if a else False), (0 if b else k6)


HIT_LOCK_MS, HIT_LOCK_AIR_MS = 64, 96   # Dodge @57-101: `_-46I` + 64 (local 11), in the air `_-46I` + 96 (local 12)


def gates(t, dir, c2e, i46, airborne, locked, locked_chain, h2b, w14, y1f, r26, o5c, d350, dash_ok, grounded,
          ve, d532, n3h, chase_h2l):
    """`Entity.Dodge(t, dir, held)` #3125 @0-1022: what happens before the DodgeType is picked.

    Callee results are passed in; each is read only where the bytecode calls it: locked = `IsDodgeLocked(t)`,
    locked_chain = `IsDodgeLocked(t, c2e)` (chain test), r26 = `_-26R(t)` (when not chained), d350 = `_-350(t)`
    and dash_ok = `Dash(t, dir)` (dash try). c2e = `_-C2E(t, dir)` (local 4); chase_h2l is the current DodgeType's
    direction kind (`_-Q42` row `_-h2L`, None without one). Returns None for `return false`, else a dict:
    `dir` (a ground dodge after the hit lock becomes 0), `is_fast` (local 8, the IsFast column wanted by
    `pick`), `chain_end` (local 5, for `timers`), `chained` (local 7, the chase dodge), `chase_dir` (local 9),
    `w14` (`_-14W` = t or None), `e28` (`_-Kc._-53P` = `_-Kc._-e28`), `clear_vx` (`_-v1D` = 0).

    Order: local 11 = `_-46I` + 64 > t, local 12 = airborne and `_-46I` + 96 > t; local 13 = neither, with dir
    Left+Drop or Right+Drop. Not locked: go. Else with c2e, `_-H2b` != `_-14W`, `_-H2b` != 0 and not
    locked_chain: chain_end = `_-H2b` + `_-y1F`, `_-14W` = t, go. Else with r26: chained, chase_dir = `_-O5C`, go.
    local 14 = neither 11 nor 12, and not (go with c2e or chained). With 13 or 14 and a side / Drop in dir:
    not d350 and dash_ok -> false; else with 14 on the ground -> false. Not go -> false. Then (the `_-6K` clear
    is `counter`): local 15 = dir != 0 without both Left and Right in chase_dir | dir. Chained with 15 ->
    is_fast; else c2e and (airborne, `_-VE` <= `_-532`, or dir not Up / Drop alone) -> is_fast and e28; else on
    the ground without 11: a chained side dodge without 15 clears vx, and dir = 0. Chained with an Up / Down
    current type: is_fast is cleared by `_-VE` > `_-H2b`, by a side against the facing `_-n3h`, or by Up type
    with Drop / Down type with Up. [H] meanings of `_-C2E`, `IsDodgeLocked`, `_-26R`, `_-VE`, `_-e28`."""
    l11 = i46 + HIT_LOCK_MS > t
    l12 = airborne and i46 + HIT_LOCK_AIR_MS > t
    l13 = not l11 and not l12 and dir in (LEFT | DROP, RIGHT | DROP)
    go = chained = False
    chain_end = chase_dir = 0
    w = None
    if not locked:
        go = True
    elif c2e and h2b != w14 and h2b != 0 and not locked_chain:
        chain_end, w, go = h2b + y1f, t, True
    elif r26:
        chained, chase_dir, go = True, o5c, True
    l14 = not l11 and not l12 and not (go and (c2e or chained))
    if l13 or l14:
        if dir & (LEFT | RIGHT | DROP):
            if not d350 and dash_ok:
                return None
            if l14 and grounded:
                return None
    if not go:
        return None
    both = chase_dir | dir
    l15 = dir != 0 and (not both & LEFT or not both & RIGHT)
    is_fast = e28 = clear_vx = False
    if chained and l15:
        is_fast = True
    elif c2e and (airborne or ve <= d532 or (dir != UP and dir != DROP)):
        is_fast = e28 = True
    elif not airborne and not l11:
        if chained and not l15 and dir & (LEFT | RIGHT):
            clear_vx = True
        dir = 0
    if chained and chase_h2l is not None and chase_h2l & (KIND_UP | KIND_DOWN):
        if (ve > h2b or (not n3h and dir & LEFT) or (n3h and dir & RIGHT)
                or (chase_h2l == KIND_UP and dir == DROP) or (chase_h2l == KIND_DOWN and dir == UP)):
            is_fast = False
    return {"dir": dir, "is_fast": is_fast, "chain_end": chain_end, "chained": chained, "chase_dir": chase_dir,
            "w14": w, "e28": e28, "clear_vx": clear_vx}


def formula_mult(formula, vx, k64, dir):
    """`_-h3i._-B15(t, formula, fighter)` #2771: the speed multiplier of a SpeedX / SpeedY formula.

    "StandardHorizontal": k = `_-K64(standard_flag)` (negated with Left), span = |2 k|; unless vx is already
    past k on k's side, d = min(|k - vx|, span), else d = 0; x = 1 - d / span; 0.6 + 0.4 x^2 when x >= 0.5,
    else 0.7 + 0.8 (x - 0.5)^3. "MomentumHorizontal": (1 + |vx| / 60) / 2. Anything else: 1. vx is `_-v1D`.
    [H] span == 0 divides by zero as in AS3 (inf / NaN); not reached with a running fighter.
    """
    if formula == "StandardHorizontal":
        span = abs(k64 * 2)
        k = -k64 if dir & LEFT else k64
        d = 0.0
        if not ((k < 0 and vx < k) or (k > 0 and vx > k)):
            d = min(abs(k - vx), span)
        x = 1 - d / span
        if x >= 0.5:
            return 0.6 + x * x * 0.4
        y = x - 0.5
        return 0.7 + y * y * y * 0.8
    if formula == "MomentumHorizontal":
        return (1 + abs(vx) / 60.0) / 2
    return 1.0


def speed_x(base, a5a, e2a, dir, vx, z2v):
    """`_-h3i._-F6w(t, fighter)` #2763 -> `_-T5L`. base = formula_mult(SpeedXFormula, ...). With Left / Right
    and SpeedXMaxMult (`_-E2A`) != 0: r = |vx| / `_-z2v` clamped to [0.33, 0.57], r = (r - 0.33) /
    0.23999999999999994, base x (SpeedXMult + r (SpeedXMaxMult - SpeedXMult)); else base x SpeedXMult (`_-a5a`)."""
    if dir & (LEFT | RIGHT) and e2a != 0:
        r = min(max(abs(vx) / z2v, 0.33), 0.57)
        r = (r - 0.33) / 0.23999999999999994
        return base * (a5a + r * (e2a - a5a))
    return base * a5a


def speed_y(base, eu, d1a, dir, vy):
    """`_-h3i._-S6F(t, fighter)` #2762 -> `_-WL`. With Up / Drop and SpeedYMaxMult (`_-D1A`) != 0: with Up,
    r = min(vy, 0) / -40, else r = max(vy, 0) / 70; r clamped to [0.5, 0.75], r = (r - 0.5) / 0.25, base x
    (SpeedYMult + r (SpeedYMaxMult - SpeedYMult)); else base x SpeedYMult (`_-EU`). vy is `_-P5S`."""
    if dir & 3 and d1a != 0:
        r = min(vy, 0.0) / -40.0 if dir & 1 else max(vy, 0.0) / 70.0
        r = min(max(r, 0.5), 0.75)
        r = (r - 0.5) / 0.25
        return base * (eu + r * (d1a - eu))
    return base * eu


def cooldown_ms(cooldown, cooldown_ground, air_or_wall):
    """`Entity._-Z4S(type, flag)` #3109: (flag ? Cooldown : CooldownGround) x 16, in `_-y1F`. Dodge passes
    `_-wn()` or `_-r51` != 0 or (IsFast and `_-64H`) (@1562-1618)."""
    return (cooldown if air_or_wall else cooldown_ground) * FRAME_MS


ANCHORS = {ABC_1100: {
    "Entity.Dodge gates: _-C2E(t, dir), _-46I + 64 / + 96 windows, IsDodgeLocked(t), chained dodge (_-H2b, _-14W, _-y1F), _-26R, Dash": [
        (3125, 23, "callproperty", "_-C2E, 2"),
        (3125, 63, "pushbyte", "64"),
        (3125, 93, "pushbyte", "96"),
        (3125, 156, "callproperty", "IsDodgeLocked, 1"),
        (3125, 230, "callproperty", "IsDodgeLocked, 2"),
        (3125, 252, "getproperty", "_-y1F"),
        (3125, 279, "callproperty", "_-26R, 1"),
        (3125, 416, "callproperty", "Dash, 2"),
        (3125, 132, "equals", ""),
        (3125, 195, "getproperty", "_-14W"),
        (3125, 264, "initproperty", "_-14W"),
        (3125, 295, "getproperty", "_-O5C"),
        (3125, 398, "callproperty", "_-350, 1"),
        (3125, 452, "getproperty", "_-96f"),
        (3125, 468, "returnvalue", ""),
        (3125, 477, "returnvalue", ""),
        (3125, 555, "pushbyte", "8"),
        (3125, 584, "setlocal", "8"),
        (3125, 617, "getproperty", "_-VE"),
        (3125, 625, "getproperty", "_-532"),
        (3125, 677, "getproperty", "_-e28"),
        (3125, 681, "initproperty", "_-53P"),
        (3125, 762, "callpropvoid", "_-N5C::_-E1t, 2"),
        (3125, 769, "setlocal_2", ""),
        (3125, 842, "getproperty", "_-h2L"),
        (3125, 875, "getproperty", "_-H2b"),
        (3125, 898, "getproperty", "_-n3h"),
        (3125, 963, "getproperty", "_-h2L"),
        (3125, 1022, "setlocal", "8"),
    ],
    "Entity.Dodge commit: DodgeType _-h3i._-26O(dir, _-wn(), l8, team flag 64, l10); _-H2b = t; _-O5C = dir; _-n3h from Left / Right / _-r35()": [
        (3125, 1052, "pushbyte", "64"),
        (3125, 1062, "callproperty", "_-26O, 5"),
        (3125, 1089, "initproperty", "_-H2b"),
        (3125, 1097, "initproperty", "_-O5C"),
        (3125, 1118, "initproperty", "_-n3h"),
        (3125, 1144, "initproperty", "_-n3h"),
        (3125, 1159, "callproperty", "_-r35, 0"),
    ],
    "Entity.Dodge timers: _-Uy = mDuration x 16, _-C1d = _-53o x 16, _-T2R = t + _-Uy, _-G6S (with _-t3v), _-y1F = _-Uy + _-Z4S + _-C1d, capped by the chain end": [
        (3125, 1487, "getproperty", "mDuration"),
        (3125, 1491, "pushbyte", "16"),
        (3125, 1495, "initproperty", "_-Uy"),
        (3125, 1503, "getproperty", "_-53o"),
        (3125, 1511, "initproperty", "_-C1d"),
        (3125, 1526, "initproperty", "_-T2R"),
        (3125, 1559, "initproperty", "_-G6S"),
        (3125, 1636, "callproperty", "_-Z4S, 2"),
        (3125, 1651, "initproperty", "_-y1F"),
        (3125, 1684, "lessthan", ""),
        (3125, 1705, "initproperty", "_-y1F"),
    ],
    "Entity.Dodge velocity: _-v1D = +-_-K64 (_-t3v, _-a5a); _-P5S = 0 and _-v1D = 0 when _-O5C != 0 or _-wn()": [
        (3125, 1304, "getproperty", "_-a5a"),
        (3125, 1399, "callproperty", "_-K64, 1"),
        (3125, 1439, "negate", ""),
        (3125, 1446, "callpropvoid", "_-N5C::_-E1t, 2"),
        (3125, 1914, "getproperty", "_-P5S"),
        (3125, 1919, "callpropvoid", "_-N5C::_-E1t, 2"),
        (3125, 1932, "getproperty", "_-v1D"),
        (3125, 1937, "callpropvoid", "_-N5C::_-E1t, 2"),
    ],
    "DodgeType pick _-h3i._-26O: kind Side 1 | Up 2 / Down 4; mask 2 (Air) when _-wn() else 1 (Ground); Set 'Test' : 'Default'; first row of _-w14 matching _-p1r, _-h2L, _-6H, _-t3v; else _-Z6": [
        (2770, 18, "pushbyte", "4"),
        (2770, 44, "pushbyte", "1"),
        (2770, 70, "pushbyte", "2"),
        (2770, 96, "pushbyte", "2"),
        (2770, 103, "pushbyte", "1"),
        (2770, 115, "pushstring", "'Test'"),
        (2770, 123, "pushstring", "'Default'"),
        (2770, 142, "getproperty", "_-w14"),
        (2770, 192, "getproperty", "_-p1r"),
        (2770, 208, "getproperty", "_-h2L"),
        (2770, 226, "getproperty", "_-6H"),
        (2770, 245, "getproperty", "_-t3v"),
        (2770, 273, "getproperty", "_-Z6"),
    ],
    "DodgeTypes.xml parser _-h3i._-I6L: Air 2, Ground 1, Both _-I6u; Neutral 0, Side 1, Up 2, Down 4; IsFast, Set, Duration, Recover, SpeedXMult; StandardSpot -> _-Z6": [
        (2768, 312, "pushstring", "'Air'"),
        (2768, 320, "pushbyte", "2"),
        (2768, 345, "getproperty", "_-I6u"),
        (2768, 357, "pushstring", "'Ground'"),
        (2768, 366, "pushbyte", "1"),
        (2768, 618, "pushstring", "'Down'"),
        (2768, 627, "pushbyte", "4"),
        (2768, 648, "pushbyte", "0"),
        (2768, 668, "pushbyte", "1"),
        (2768, 739, "pushbyte", "2"),
        (2768, 1055, "initproperty", "_-t3v"),
        (2768, 1148, "initproperty", "_-p1r"),
        (2768, 1526, "pushstring", "'StandardSpot'"),
        (2768, 1539, "initproperty", "_-Z6"),
        (15351, 27965, "pushbyte", "1"),
        (15351, 27968, "pushbyte", "2"),
        (15351, 27972, "initproperty", "_-I6u"),
    ],
    "Dodge speeds: _-T5L = type._-F6w(t, this), _-WL = type._-S6F(t, this); _-B15 formula (StandardHorizontal, MomentumHorizontal); _-M4C = 64": [
        (3125, 1457, "callproperty", "_-F6w, 2"),
        (3125, 1462, "initproperty", "_-T5L"),
        (3125, 1473, "callproperty", "_-S6F, 2"),
        (3125, 1478, "initproperty", "_-WL"),
        (2771, 35, "pushstring", "'StandardHorizontal'"),
        (2771, 127, "getproperty", "_-M4C"),
        (2771, 147, "callproperty", "_-K64, 1"),
        (2771, 157, "pushbyte", "2"),
        (2771, 302, "pushdouble", "0.5"),
        (2771, 309, "pushdouble", "0.6"),
        (2771, 317, "pushdouble", "0.4"),
        (2771, 339, "pushdouble", "0.7"),
        (2771, 350, "pushdouble", "0.8"),
        (2771, 364, "pushstring", "'MomentumHorizontal'"),
        (2771, 393, "pushdouble", "60.0"),
        (2774, 186, "pushbyte", "64"),
        (2774, 189, "initproperty", "_-M4C"),
    ],
    "Dodge speed multipliers: _-F6w |vx| / _-z2v in [0.33, 0.57] toward _-E2A; _-S6F vy / -40 or / 70 in [0.5, 0.75] toward _-D1A; _-Z4S Cooldown / CooldownGround x 16": [
        (2763, 13, "findproperty", "_-W5m"),
        (2763, 52, "getproperty", "_-E2A"),
        (2763, 87, "getproperty", "_-z2v"),
        (2763, 96, "pushdouble", "0.57"),
        (2763, 115, "pushdouble", "0.33"),
        (2763, 134, "pushdouble", "0.23999999999999994"),
        (2763, 144, "getproperty", "_-a5a"),
        (2762, 16, "findproperty", "_-E3y"),
        (2762, 57, "getproperty", "_-D1A"),
        (2762, 74, "getproperty", "_-P5S"),
        (2762, 116, "pushdouble", "-40.0"),
        (2762, 141, "pushdouble", "70.0"),
        (2762, 149, "pushdouble", "0.75"),
        (2762, 168, "pushdouble", "0.5"),
        (2762, 187, "pushdouble", "0.25"),
        (3109, 6, "getproperty", "_-p2U"),
        (3109, 15, "getproperty", "_-S6E"),
        (3109, 22, "pushbyte", "16"),
        (3093, 6, "callproperty", "_-wn, 0"),
        (3093, 16, "getlocal_1", ""),
        (3093, 17, "not", ""),
        (3093, 26, "getproperty", "_-z2v"),
        (3093, 39, "multiply", ""),
        (3093, 35, "getproperty", "_-u5j"),
        (3093, 48, "getproperty", "_-M1U"),
        (3093, 57, "getproperty", "_-04K"),
        (3093, 60, "multiply", ""),
    ],
    "Entity.Dodge counter _-6K: count >>> 16 cleared unless _-E6P() or chained; low half 2 / 1 under _-f2b(); count + 1": [
        (3125, 483, "callproperty", "_-E6P, 0"),
        (3125, 515, "pushint", "65535"),
        (3125, 1716, "urshift", ""),
        (3125, 1727, "initproperty", "_-6K"),
        (3125, 1733, "callproperty", "_-f2b, 0"),
        (3125, 1769, "pushbyte", "2"),
        (3125, 1776, "pushbyte", "1"),
        (3125, 1860, "lshift", ""),
        (3125, 1873, "initproperty", "_-6K"),
    ],
    "Entity._-t1A prelude: CooldownLanded cap of _-y1F after _-46I + 240; dodge over at _-H2b + _-y1F unless _-3E + 112 > t": [
        (2984, 2659, "callpropvoid", "_-t1A, 2"),
        (2992, 89, "callproperty", "_-wn, 0"),
        (2992, 104, "getproperty", "_-r51"),
        (2992, 120, "callproperty", "_-5q, 0"),
        (2992, 135, "getproperty", "_-a1h"),
        (2992, 148, "getproperty", "_-Q42"),
        (2992, 165, "getproperty", "_-46I"),
        (2992, 172, "getproperty", "_-l2o"),
        (2992, 178, "greaterequals", ""),
        (2992, 185, "getproperty", "_-T2A"),
        (2992, 189, "pushbyte", "16"),
        (2992, 220, "greaterthan", ""),
        (2992, 230, "initproperty", "_-y1F"),
        (2992, 236, "getproperty", "_-3E"),
        (2992, 243, "getproperty", "_-y4m"),
        (2992, 249, "greaterthan", ""),
        (2992, 259, "callproperty", "_-u5E, 0"),
        (2992, 287, "lessequals", ""),
        (2992, 312, "greaterthan", ""),
        (2992, 326, "getproperty", "_-Z32"),
        (2992, 329, "callpropvoid", "_-MX, 1"),
        (2992, 340, "initproperty", "_-H2b"),
        (2992, 349, "callpropvoid", "_-51c, 2"),
        (3173, 800, "pushbyte", "112"),
        (3173, 803, "initproperty", "_-y4m"),
        (3173, 882, "pushuint", "240"),
        (3173, 885, "initproperty", "_-l2o"),
    ],
    "Entity._-t1A dodge tick: moving unless Neutral ground-only; _-84 / _-A4A = 60 x _-T5L / _-WL x AccelMult x _-I5a ease; side latch _-l4A / _-g5E": [
        (2992, 373, "getproperty", "_-h2L"),
        (2992, 386, "getproperty", "_-6H"),
        (2992, 428, "iffalse", "1422"),
        (2992, 1863, "greaterequals", ""),
        (2992, 1878, "getproperty", "_-24F"),
        (2992, 1892, "iffalse", "205"),
        (2992, 1910, "callpropvoid", "_-N5C::_-E1t, 2"),
        (2992, 1928, "callpropvoid", "_-N5C::_-E1t, 2"),
        (2992, 1932, "pushdouble", "60.0"),
        (2992, 1942, "getproperty", "_-r4O"),
        (2992, 1950, "pushdouble", "60.0"),
        (2992, 1962, "getproperty", "_-k4q"),
        (2992, 1977, "getproperty", "_-K35"),
        (2992, 1981, "callproperty", "_-I5a, 3"),
        (2992, 1998, "getproperty", "_-F5s"),
        (2992, 2002, "callproperty", "_-I5a, 3"),
        (2992, 2021, "getproperty", "_-84"),
        (2992, 2045, "negate", ""),
        (2992, 2091, "getproperty", "_-A4A"),
        (2984, 2794, "getproperty", "_-84"),
        (2984, 4228, "getproperty", "_-A4A"),
        (2992, 2188, "initproperty", "_-l4A"),
        (2992, 2197, "initproperty", "_-g5E"),
        (2992, 2291, "initproperty", "_-l4A"),
        (2992, 2300, "initproperty", "_-g5E"),
        (2772, 20, "pushstring", "'EaseHorizontal'"),
        (2772, 29, "getproperty", "_-H2b"),
        (2772, 61, "pushdouble", "0.25"),
        (2772, 72, "pushdouble", "2.5"),
        (2772, 88, "pushbyte", "3"),
        (2768, 149, "pushstring", "'AccelXFormula'"),
        (2768, 182, "pushstring", "'AccelXMult'"),
        (2768, 202, "initproperty", "_-r4O"),
        (2768, 245, "pushstring", "'AccelYMult'"),
        (2768, 265, "initproperty", "_-k4q"),
        (3173, 1165, "pushint", "4096"),
        (3173, 1167, "initproperty", "_-24F"),
    ],
    "Entity._-t1A timer end: PostDodge _-f6R; exit speed a + (60 - a) 1.5 (a/60)^2; ExitX / ExitBackX by held side or latch; x _-T5L; ExitY / ExitBackY; _-T5L = _-WL = 1": [
        (2992, 436, "callpropvoid", "_-w5G, 1"),
        (2992, 541, "getproperty", "_-f6R"),
        (2992, 550, "initproperty", "_-f6R"),
        (2992, 557, "callproperty", "_-u5E, 0"),
        (2992, 619, "pushdouble", "60.0"),
        (2992, 641, "pushdouble", "1.5"),
        (2992, 675, "pushbyte", "-1"),
        (2992, 683, "iffalse", "18"),
        (2992, 718, "pushbyte", "8"),
        (2992, 743, "not", ""),
        (2992, 745, "iffalse", "488"),
        (2992, 854, "getproperty", "_-i16"),
        (2992, 904, "getproperty", "_-05s"),
        (2992, 1164, "callpropvoid", "_-CV, 1"),
        (2992, 1228, "callpropvoid", "_-CV, 1"),
        (2992, 1241, "getproperty", "_-l4A"),
        (2992, 1285, "getproperty", "_-g5E"),
        (2992, 1358, "getproperty", "_-i16"),
        (2992, 1408, "getproperty", "_-05s"),
        (2992, 1443, "callpropvoid", "_-CV, 1"),
        (2992, 1479, "getproperty", "_-T5L"),
        (2992, 1593, "getproperty", "_-73o"),
        (2992, 1619, "getproperty", "_-LX"),
        (2992, 1797, "callpropvoid", "_-51c, 2"),
        (2992, 1806, "initproperty", "_-T5L"),
        (2992, 1815, "initproperty", "_-WL"),
        (2992, 1823, "callproperty", "_-141, 0"),
        (2992, 1833, "getproperty", "_-n3h"),
        (2992, 1846, "initproperty", "_-w47"),
        (2768, 880, "initproperty", "_-i16"),
        (2768, 908, "initproperty", "_-73o"),
        (2768, 937, "initproperty", "_-05s"),
        (2768, 966, "initproperty", "_-LX"),
        (2768, 1086, "initproperty", "_-f6R"),
    ],
    "Entity.Dash #3132: ground only; side taps _-VE / _-V22 / _-r3L within 192 ms; windows 80 / 160 (_-532, _-3E, _-K1k); gate 7 / 15; turn locks; kinds _-L3a 1-7; writes": [
        (3132, 135, "callproperty", "_-y1U, 2"),
        (3132, 166, "callproperty", "_-w4c, 4"),
        (3132, 183, "getproperty", "_-96f"),
        (3132, 199, "callproperty", "_-141, 0"),
        (3132, 211, "callproperty", "_-r35, 0"),
        (3132, 223, "getproperty", "_-VE"),
        (3132, 234, "getproperty", "_-V22"),
        (3132, 244, "getproperty", "_-r3L"),
        (3132, 314, "getproperty", "_-t5z"),
        (3132, 366, "getproperty", "_-M3V"),
        (3132, 393, "pushuint", "160"),
        (3132, 399, "pushbyte", "80"),
        (3132, 408, "getproperty", "_-K1k"),
        (3132, 431, "getproperty", "_-532"),
        (3132, 449, "getproperty", "_-3E"),
        (3132, 466, "getproperty", "_-M3h"),
        (3132, 510, "pushuint", "192"),
        (3132, 651, "pushdouble", "7.0"),
        (3132, 657, "pushdouble", "15.0"),
        (3132, 760, "getproperty", "_-26T"),
        (3132, 764, "pushuint", "320"),
        (3132, 769, "pushuint", "320"),
        (3132, 799, "pushbyte", "96"),
        (3132, 842, "callproperty", "abs, 1"),
        (3132, 858, "pushbyte", "7"),
        (3132, 877, "pushbyte", "6"),
        (3132, 924, "pushbyte", "3"),
        (3132, 977, "pushbyte", "5"),
        (3132, 1009, "initproperty", "_-K1k"),
        (3132, 1017, "initproperty", "_-w47"),
        (3132, 1024, "pushbyte", "4"),
        (3132, 1042, "pushbyte", "2"),
        (3132, 1055, "pushbyte", "1"),
        (3132, 1067, "callpropvoid", "_-CV, 1"),
        (3132, 1077, "callpropvoid", "_-q2o, 1"),
        (3132, 1086, "initproperty", "_-v3x"),
        (3132, 1094, "initproperty", "_-P50"),
        (3132, 1102, "initproperty", "_-M3V"),
        (3132, 1111, "initproperty", "_-t5z"),
        (3132, 1118, "callpropvoid", "_-Q3q, 0"),
        (3132, 1127, "initproperty", "_-G6S"),
        (3132, 1142, "initproperty", "_-p3c"),
        (3132, 1433, "returnvalue", ""),
        (3132, 1435, "returnvalue", ""),
    ],
    "Gravity cancel: #6313 cancel flags 32 / 33 / 34 in _-H2b + 16 CancelStart .. 16 CancelLimit; #6334 _-rU air offset 3, 0 with the cancel flag; _-C5S / _-bC": [
        (6313, 2018, "callproperty", "_-E6P, 0"),
        (6313, 2054, "callproperty", "_-f2b, 0"),
        (6313, 2092, "getproperty", "_-H2b"),
        (6313, 2110, "callproperty", "_-26R, 1"),
        (6313, 2122, "setlocal", "34"),
        (6313, 2153, "setlocal", "38"),
        (6313, 2235, "getproperty", "_-O5C"),
        (6313, 2244, "setlocal", "39"),
        (6313, 2263, "getproperty", "_-M4L"),
        (6313, 2267, "pushbyte", "16"),
        (6313, 2276, "getproperty", "_-GX"),
        (6313, 2303, "greaterequals", ""),
        (6313, 2324, "lessequals", ""),
        (6313, 2332, "setlocal", "32"),
        (6313, 2342, "setlocal", "33"),
        (6313, 2918, "getlocal", "33"),
        (6313, 2920, "getlocal", "32"),
        (6313, 2922, "callproperty", "_-rU, 6"),
        (6334, 112, "callproperty", "_-wn, 0"),
        (6334, 128, "pushbyte", "3"),
        (6334, 141, "getlocal", "5"),
        (6334, 147, "pushbyte", "0"),
        (6334, 183, "callproperty", "_-y1U, 3"),
        (6334, 671, "callproperty", "_-C5S, 6"),
        (6334, 700, "callpropvoid", "_-bC, 2"),
        (6334, 718, "pushuint", "144"),
        (6334, 722, "initproperty", "_-B3V"),
        (6334, 799, "initproperty", "_-96f"),
        (2768, 447, "initproperty", "_-GX"),
        (2768, 477, "initproperty", "_-M4L"),
    ],
    "Entity._-bC cancel end: caps 60 x _-T5L / _-WL x AccelMult at 60, signed by _-O5C; _-T2R = 0; with gc _-a1h, _-y1F = _-Uy + Cooldown x 16, _-I2g |= 2 in the air": [
        (3041, 51, "getproperty", "_-T5L"),
        (3041, 56, "getproperty", "_-r4O"),
        (3041, 70, "getproperty", "_-WL"),
        (3041, 76, "getproperty", "_-k4q"),
        (3041, 91, "pushdouble", "60.0"),
        (3041, 130, "callproperty", "abs, 1"),
        (3041, 182, "negate", ""),
        (3041, 214, "callpropvoid", "_-N5C::_-E1t, 2"),
        (3041, 273, "callpropvoid", "_-N5C::_-E1t, 2"),
        (3041, 290, "initproperty", "_-T2R"),
        (3041, 298, "callpropvoid", "_-51c, 2"),
        (3041, 311, "initproperty", "_-a1h"),
        (3041, 324, "getproperty", "_-p2U"),
        (3041, 334, "initproperty", "_-y1F"),
        (3041, 389, "pushbyte", "2"),
        (3041, 393, "initproperty", "_-I2g"),
    ],
    "DodgeTypes.xml load: _-i32 iterates the children into _-I6L; DodgeID 0 dropped; _-Z4V[id]; StandardSpot -> _-Z6; _-w14 push": [
        (2767, 21, "initproperty", "_-w14"),
        (2767, 67, "callpropvoid", "_-I6L, 2"),
        (2768, 54, "callproperty", "get, 1"),
        (2768, 1451, "getproperty", "_-B3q"),
        (2768, 1462, "returnvoid", ""),
        (2768, 1526, "pushstring", "'StandardSpot'"),
        (2768, 1539, "initproperty", "_-Z6"),
        (2768, 1557, "setproperty", "[rt]"),
        (2768, 1570, "callpropvoid", "http://adobe.com/AS3/2006/builtin::push, 1"),
    ],
    "Dodge flags: E6P = _-y1o (_-w5G, true at commit @1080), u5E = _-l4c (_-E5I via _-51c); IsDodgeLocked #3075 tests, _-x2C >= 9": [
        (2941, 5, "getproperty", "_-y1o"),
        (2942, 5, "getproperty", "_-l4c"),
        (2899, 14, "initproperty", "_-y1o"),
        (2900, 14, "initproperty", "_-l4c"),
        (3027, 6, "callpropvoid", "_-E5I, 1"),
        (3027, 18, "initproperty", "_-53P"),
        (3027, 32, "initproperty", "_-a1h"),
        (3027, 46, "initproperty", "_-6K"),
        (3125, 1079, "pushtrue", ""),
        (3125, 1080, "callpropvoid", "_-w5G, 1"),
        (3125, 1961, "initproperty", "_-l4A"),
        (3075, 14, "callproperty", "IsMoveLocked, 1"),
        (3075, 30, "callproperty", "_-u5E, 0"),
        (3075, 54, "callproperty", "_-E6P, 0"),
        (3075, 72, "getproperty", "_-o3I"),
        (3075, 92, "getproperty", "_-r51"),
        (3075, 163, "callproperty", "_-12J, 4"),
        (3075, 178, "getproperty", "_-Xb"),
        (3075, 198, "callproperty", "_-C54, 1"),
        (3075, 213, "getproperty", "_-x2C"),
        (3075, 216, "pushbyte", "9"),
    ],
    "Entity._-C2E #3073: _-532 + _-84e (192) >= t, not against _-M3h, dir != 0, not Drop alone on the ground": [
        (3073, 6, "getproperty", "_-532"),
        (3073, 14, "getproperty", "_-84e"),
        (3073, 20, "lessthan", ""),
        (3073, 61, "getproperty", "_-M3h"),
        (3073, 82, "getproperty", "_-M3h"),
        (3073, 107, "getproperty", "_-96f"),
        (3073, 121, "pushbyte", "2"),
        (3173, 812, "initproperty", "_-84e"),
    ],
}}
