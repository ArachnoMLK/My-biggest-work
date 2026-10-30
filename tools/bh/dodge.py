"""The commit part of `Entity.Dodge` #3125 on patch 11.00: what a dodge writes on the fighter the tick it starts.

See docs/hit-detection-11.00.md §10.2. `_-i4Z._-51o` #6313 @2418-2433 calls `owner.Dodge(t, keys & 15, held)`
on a buffered DodgeDash (256) press (input-buffer-11.00.md, PR #28). This module transcribes the writes made
once Dodge has decided to dodge (@1024-2288). The gates before it (@0-1022: `IsDodgeLocked`, the chained
dodge `_-26R`, `Dash`, the ground `_-96f`) are only pinned, not transcribed. The motion during the dodge is
in the dodge state of `Entity._-8i` and is not transcribed yet.

Names: `dir` is Dodge's second argument (`keys & 15`: Up 1, Drop 2, Left 4, Right 8). `_-wn()` is called
`grounded` here [H: the name; it gates the ground cases of Jump too]. The DodgeType is
`_-h3i._-26O(dir, grounded, local 8, team flag 64, local 10)`, a row of DodgeTypes.xml (`_-h3i._-i32`).
[V] unless marked [H].
"""
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


def clears_velocity(dir, grounded):
    """@1876-1937: with a direction or on the ground, `_-P5S` and `_-v1D` are set to 0. A neutral air dodge
    keeps them (after the `_-v1D` = ±`_-K64` write of @1290-1446 when the type has `_-t3v` and `_-a5a`)."""
    return dir != 0 or grounded


def neutral_push(k64, dir):
    """@1407-1446: the value written to `_-v1D` when the type has `_-t3v` and `_-a5a` != 0: `_-K64(...)`, negated
    when `_-O5C` (= dir) has Left. [H] It survives only when `clears_velocity` is false, so with dir == 0."""
    return -k64 if dir & LEFT else k64


def counter(k6, chained, has_dir_bits, grounded, f2b, e6p=False):
    """`_-6K` after the dodge (@499-520, @1708-1873). The count is `_-6K` >>> 16.

    @499: without `_-E6P()` and not chained (local 7), the count is cleared first. Then the low half is
    reset: when `_-f2b()`, a chained dodge with a direction (local 15) sets it to 2 on the ground, else 1; a
    fresh air dodge with a direction sets it to 1. If the low half is then non-zero or the dodge is chained,
    the count is the old count + 1; otherwise `_-6K` stays 0 (count lost). [H] `_-f2b`, `_-E6P` meanings.
    """
    if not e6p and not chained:
        k6 &= LOW_MASK
    count = k6 >> COUNT_SHIFT
    k6 = 0
    if f2b:
        if chained:
            if has_dir_bits:
                k6 = 2 if grounded else 1
        elif not grounded and has_dir_bits:
            k6 = 1
    if k6 != 0 or chained:
        k6 = ((count + 1) << COUNT_SHIFT) | (k6 & LOW_MASK)
    return k6


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
}}
