"""Input buffer of patch 11.00: how `_-i4Z._-51o` #6313 turns the input timeline into buffered presses.

See docs/input-buffer-11.00.md. `state_at` and `buffered_presses` transcribe #6323 and #6313 @294-1278;
the pins check that the bytecode still has that shape. Static evidence only; nothing is executed.
Anchors are (method id, offset, opname, operand text as printed by `abc-disasm`); branch operands are
relative.
"""
import bisect

from .movement import ABC_1100, check, listing

TICK_MS = 16
DEFAULT_WINDOW = 5                    # pushbyte 5 @64; 9 or 11 in some states, see the doc
ACTIONS = {                           # tested in this order inside the loop @1066-1270
    "LightAttack": 128,
    "HeavyAttack": 64,
    "Taunt": 1024 | 2048 | 4096 | 8192,   # Commands._-z5Y
    "DodgeDash": 256,
    "Jump": 16,
    "PickUpThrow": 512,
}


def state_at(records, t, default=0):
    """Key word at time t: the keys of the last (time, keys) record with time <= t (#6323)."""
    i = bisect.bisect_right([r[0] for r in records], t)
    return records[i - 1][1] if i else default


def buffered_presses(records, t, n=DEFAULT_WINDOW, skip_current=False):
    """{action: press time} buffered at tick time t, or None before the first n ticks (#6313 @294-305).

    The window holds the key words at t, t-16, ..., t-16(n-1). A press is a bit that is set at tick i
    and clear at tick i+1 (the one before it); for each action the oldest press in ticks n-2 .. 0 is
    kept. With `skip_current` (`_-h2w`), tick 0 (= t) is not scanned.
    """
    if t < n * TICK_MS:
        return None
    window = [state_at(records, t - i * TICK_MS) for i in range(n)]
    out = {}
    for i in range(n - 2, 0 if skip_current else -1, -1):
        edge = (window[i] ^ window[i + 1]) & window[i]
        for name, mask in ACTIONS.items():
            if name not in out and edge & mask:
                out[name] = t - i * TICK_MS
    return out


JUMP_LOCK_MS = 192        # Entity._-z3C: no jump at the first site until t > _-532 + 192
CHAIN_MIN_MS = 300        # _-I35: no chain until the current move has run more than 300 ms
DODGE_REARM_MS = 480      # _-g3B + 480 > t sets the third Dodge argument (local 31)
# Slot names from _-F5N._-42t #1726: 7 / 8 / 11 are the side / down / neutral signatures, 9 / 10 the
# air heavies (recovery, ground pound) [H for 9 / 10], 1-6 the light attacks; 13-20 taunt / emote slots.
SLOT_NAMES = {1: "NLight", 2: "SLight", 3: "DLight", 4: "NAir", 5: "SAir", 6: "DAir",
              7: "SideSig", 8: "DownSig", 9: "Recovery", 10: "GroundPound", 11: "NeutralSig"}
# _-i4Z._-y2r: move slot for (kind offset + air offset + direction class); script347.<init> @150-191
ATTACK_SLOTS = (3, 1, 2, 6, 4, 5, 8, 11, 7, 10, 9, 9)
HEAVY_OFFSET = 6          # pushbyte 6 in the heavy block (@3097); the light block passes 0
AIR_OFFSET = 3            # _-rU @128 when airborne (_-wn) or with the jump flag


def attack_slot(keys, heavy=False, air=False):
    """Move slot `_-rU` #6334 starts for a light / heavy press with key word `keys`.

    Direction class: 0 when Drop (2) is held, else 1 (neutral) when bit 32 is set, else 2 (side)
    when MoveLeft / MoveRight (4 / 8) is held, else 1. The forced direction `_-O5C` and the
    ground-snap `_-y1U` cases are not modelled.
    """
    d = keys & 15
    if d & 2:
        cls = 0
    elif keys & 32:
        cls = 1
    elif d & 12:
        cls = 2
    else:
        cls = 1
    return ATTACK_SLOTS[cls + (HEAVY_OFFSET if heavy else 0) + (AIR_OFFSET if air else 0)]


MAX_AIR_JUMPS = 2         # Entity._-56T() returns pushbyte 2


def first_jump_allowed(t, last_move_start):
    """First jump site of #6313 (@2529-2556): `_-532 == 0` or t > `_-532` + 192."""
    return last_move_start == 0 or t > last_move_start + JUMP_LOCK_MS


def chain_allowed(t, move_start):
    """`_-I35` #6335 @17-46 refuses while t - `_-sM` <= 300 (unsigned difference)."""
    return (t - move_start) % (1 << 32) > CHAIN_MIN_MS


ANCHORS = {ABC_1100: {
    "window size n: 5, or _-i3b(_-L3a), 9 or 11 by state; no action before n ticks": [
        (6313, 64, "pushbyte", "5"),
        (6313, 76, "getproperty", "_-P50"),
        (6313, 90, "getproperty", "_-M3V"),
        (6313, 108, "getproperty", "_-L3a"),
        (6313, 111, "callproperty", "_-i3b, 1"),
        (6313, 153, "pushbyte", "64"),
        (6313, 156, "add_i", ""),
        (6313, 176, "pushbyte", "32"),
        (6313, 179, "add_i", ""),
        (6313, 195, "getproperty", "_-f6R"),
        (6313, 198, "lessequals", ""),
        (6313, 204, "pushbyte", "9"),
        (6313, 228, "pushbyte", "3"),
        (6313, 238, "getproperty", "_-o3I"),
        (6313, 263, "getproperty", "_-h2w"),
        (6313, 271, "pushbyte", "11"),
        (6313, 281, "getproperty", "_-3N"),
        (6313, 289, "pushbyte", "9"),
        (6313, 296, "pushbyte", "16"),
        (6313, 298, "multiply_i", ""),
        (6313, 300, "lessthan", ""),
        (6313, 305, "returnvoid", ""),
    ],
    "window: _-O1I[i] = _-7z(t - 16 i) for i < n; _-66U = _-O1I[0]": [
        (6313, 331, "pushbyte", "16"),
        (6313, 333, "multiply_i", ""),
        (6313, 334, "subtract_i", ""),
        (6313, 342, "getproperty", "_-O1I"),
        (6313, 353, "callproperty", "_-7z, 1"),
        (6313, 359, "setproperty", "[rt]"),
        (6313, 367, "iflt", "-51"),
        (6313, 383, "getproperty", "[rt]"),
        (6313, 388, "initproperty", "_-66U"),
        (6313, 400, "getproperty", "[rt]"),
        (6313, 510, "pushbyte", "15"),
        (6313, 513, "bitand", ""),
    ],
    "presses: for i = n-2 down to 0 (1 with _-h2w), edge = (O1I[i] ^ O1I[i+1]) & O1I[i]; oldest edge per action kept": [
        (6313, 966, "pushbyte", "2"),
        (6313, 968, "subtract_i", ""),
        (6313, 971, "setlocal", "4"),
        (6313, 980, "getproperty", "_-h2w"),
        (6313, 991, "pushbyte", "0"),
        (6313, 1011, "getproperty", "[rt]"),
        (6313, 1032, "getproperty", "[rt]"),
        (6313, 1037, "bitxor", ""),
        (6313, 1040, "bitand", ""),
        (6313, 1042, "setlocal", "28"),
        (6313, 1057, "pushbyte", "16"),
        (6313, 1059, "multiply_i", ""),
        (6313, 1060, "subtract_i", ""),
        (6313, 1068, "pushbyte", "0"),
        (6313, 1078, "pushint", "128"),
        (6313, 1094, "setlocal", "18"),
        (6313, 1114, "pushbyte", "64"),
        (6313, 1130, "setlocal", "20"),
        (6313, 1154, "getproperty", "_-z5Y"),
        (6313, 1185, "pushint", "256"),
        (6313, 1202, "setlocal", "23"),
        (6313, 1222, "pushbyte", "16"),
        (6313, 1238, "setlocal", "25"),
        (6313, 1253, "pushint", "512"),
        (6313, 1270, "setlocal", "26"),
        (6313, 1272, "declocal_i", "4"),
        (6313, 1278, "ifge", "-305"),
    ],
    "jump fires on a buffered press when no other action was taken": [
        (6313, 3427, "getlocal", "25"),
        (6313, 3431, "equals", ""),
        (6313, 3445, "callpropvoid", "Jump, 1"),
    ],
    "_-7z(t): keys of the last input record with time <= t (cursor _-e3n)": [
        (6323, 68, "pushint", "1024"),
        (6323, 72, "pushint", "2048"),
        (6323, 76, "pushint", "8192"),
        (6323, 228, "findproperty", "_-e3n"),
        (6323, 250, "getproperty", "_-J6B"),
        (6323, 253, "getlocal_1", ""),
        (6323, 254, "equals", ""),
        (6323, 261, "getproperty", "_-c3T"),
        (6323, 264, "returnvalue", ""),
        (6323, 267, "getproperty", "_-J6B"),
        (6323, 271, "lessthan", ""),
        (6323, 340, "greaterthan", ""),
        (6323, 437, "getproperty", "_-J6B"),
        (6323, 441, "lessequals", ""),
        (6323, 458, "getproperty", "_-c3T"),
        (6323, 488, "getproperty", "_-c3T"),
    ],
    "Commands._-z5Y = 1024 | 2048 | 4096 | 8192 (the taunt bits)": [
        (15351, 20876, "pushint", "1024"),
        (15351, 20880, "pushint", "2048"),
        (15351, 20884, "pushint", "4096"),
        (15351, 20887, "pushint", "8192"),
        (15351, 20892, "initproperty", "_-z5Y"),
    ],
    "no re-trigger: Jump sets _-I5A = t and _-H5F blocks jumps while t <= _-I5A + _-Y35 (176)": [
        (3052, 37, "getlocal_2", ""),
        (3052, 38, "not", ""),
        (3052, 49, "callproperty", "_-H5F, 2"),
        (3052, 59, "returnvoid", ""),
        (3052, 502, "initproperty", "_-I5A"),
        (3052, 545, "initproperty", "_-I5A"),
        (3065, 20, "getproperty", "_-65w"),
        (3065, 27, "lookupswitch", "23, 29, 23, 23, 23, 23, 29"),
        (3065, 247, "getproperty", "_-I5A"),
        (3065, 255, "getproperty", "_-Y35"),
        (3065, 258, "add_i", ""),
        (3065, 261, "greaterequals", ""),
        (3065, 263, "setlocal", "7"),
        (3065, 271, "pushtrue", ""),
        (3173, 829, "pushuint", "176"),
        (3173, 831, "initproperty", "_-Y35"),
    ],
    "action blocks in byte order: mode hook, dodge, jump, _-LY, light, heavy, pick-up, throw, jump, move, taunt, HandleInput": [
        (6313, 1447, "callproperty", "_-365, 4"),
        (6313, 1453, "iffalse", "34"),
        (6313, 1479, "initproperty", "_-66U"),
        (6313, 1532, "callpropvoid", "_-A5q, 1"),
        (6313, 1916, "callpropvoid", "_-U6t, 8"),
        (6313, 2403, "getlocal", "23"),
        (6313, 2408, "getproperty", "_-C51"),
        (6313, 2411, "greaterthan", ""),
        (6313, 2433, "callproperty", "Dodge, 3"),
        (6313, 2517, "getlocal", "25"),
        (6313, 2547, "getproperty", "_-z3C"),
        (6313, 2551, "add_i", ""),
        (6313, 2553, "greaterthan", ""),
        (6313, 2567, "callpropvoid", "Jump, 1"),
        (6313, 2612, "getlocal", "18"),
        (6313, 2617, "callproperty", "_-LY, 2"),
        (6313, 2693, "getlocal", "18"),
        (6313, 2698, "callproperty", "_-LY, 2"),
        (6313, 2791, "getlocal", "18"),
        (6313, 2825, "pushbyte", "15"),
        (6313, 2833, "pushbyte", "2"),
        (6313, 2836, "callproperty", "_-I35, 5"),
        (6313, 2922, "callproperty", "_-rU, 6"),
        (6313, 2996, "getlocal", "20"),
        (6313, 3028, "getlocal", "21"),
        (6313, 3038, "pushbyte", "3"),
        (6313, 3041, "callproperty", "_-I35, 5"),
        (6313, 3104, "callproperty", "_-rU, 6"),
        (6313, 3245, "getlocal", "26"),
        (6313, 3249, "callproperty", "_-b1I, 4"),
        (6313, 3338, "getlocal", "26"),
        (6313, 3340, "getlocal", "18"),
        (6313, 3342, "greaterthan", ""),
        (6313, 3358, "callproperty", "_-L6S, 3"),
        (6313, 3427, "getlocal", "25"),
        (6313, 3445, "callpropvoid", "Jump, 1"),
        (6313, 3553, "callpropvoid", "_-01L, 0"),
        (6313, 3594, "callpropvoid", "_-B3G, 0"),
        (6313, 3626, "getlocal", "22"),
        (6313, 3647, "callproperty", "_-Y1K, 4"),
        (6313, 3723, "callpropvoid", "HandleInput, 4"),
        (6313, 4011, "returnvoid", ""),
    ],
    "jump lock: local 28 = owner._-532, set at move start (_-F5N._-h1T -> _-c1r) and by _-q2i._-b1I; _-z3C = 192": [
        (6313, 2350, "getproperty", "_-532"),
        (6313, 2355, "setlocal", "28"),
        (6313, 2541, "getlocal", "28"),
        (3025, 29, "initproperty", "_-532"),
        (1742, 853, "callpropvoid", "_-c1r, 5"),
        (3814, 274, "initproperty", "_-532"),
        (3173, 893, "pushuint", "192"),
        (3173, 895, "initproperty", "_-z3C"),
    ],
    "dodge: a refused dodge under _-P50 stamps _-C51 = t, so the same press is not tried again": [
        (6313, 2468, "getproperty", "_-P50"),
        (6313, 2480, "initproperty", "_-B5"),
        (6313, 2487, "getlocal_1", ""),
        (6313, 2488, "initproperty", "_-C51"),
    ],
    "late dodge: 6 ticks before the window when _-C2E; held dodge since _-D3F within 32 ms of _-01g; _-g3B + 480": [
        (6313, 1560, "pushbyte", "7"),
        (6313, 1585, "callproperty", "_-C2E, 2"),
        (6313, 1630, "pushbyte", "5"),
        (6313, 1684, "pushint", "256"),
        (6313, 1717, "setlocal", "23"),
        (6313, 1791, "pushbyte", "32"),
        (6313, 1802, "getproperty", "_-01g"),
        (6313, 1853, "pushuint", "480"),
        (6313, 1867, "setlocal", "31"),
        (6313, 2431, "getlocal", "31"),
        (3073, 6, "getproperty", "_-532"),
        (3073, 14, "getproperty", "_-84e"),
        (3173, 810, "pushuint", "192"),
        (3173, 812, "initproperty", "_-84e"),
    ],
    "cancel window: local 32 when _-H2b + 16 _-M4L <= t <= _-H2b + 16 _-GX of the current move record": [
        (6313, 2263, "getproperty", "_-M4L"),
        (6313, 2267, "pushbyte", "16"),
        (6313, 2276, "getproperty", "_-GX"),
        (6313, 2295, "getproperty", "_-H2b"),
        (6313, 2332, "setlocal", "32"),
        (6313, 2342, "setlocal", "33"),
    ],
    "light / heavy route: _-I35 (chain) when a move runs without _-Z6M[1], else _-rU when the press is newer than _-sM": [
        (6313, 2726, "getproperty", "_-r51"),
        (6313, 2836, "callproperty", "_-I35, 5"),
        (6313, 2881, "getproperty", "_-sM"),
        (6313, 2884, "getlocal", "18"),
        (6313, 2886, "lessthan", ""),
        (6313, 2916, "pushbyte", "0"),
        (6313, 2922, "callproperty", "_-rU, 6"),
        (6313, 3097, "pushbyte", "6"),
        (6313, 3104, "callproperty", "_-rU, 6"),
        (1734, 182, "initproperty", "_-O2R"),
        (1734, 189, "initproperty", "_-sM"),
    ],
    "_-I35: refuse while t - _-sM <= 300; then _-V5I (move has _-qo) or _-A3Q(t, kind)": [
        (6335, 21, "getproperty", "_-sM"),
        (6335, 24, "subtract_i", ""),
        (6335, 26, "pushuint", "300"),
        (6335, 29, "lessequals", ""),
        (6335, 64, "getproperty", "_-qo"),
        (6335, 76, "callproperty", "_-V5I, 2"),
        (6335, 98, "callproperty", "_-A3Q, 2"),
        (6335, 134, "callpropvoid", "_-bC, 2"),
    ],
    "_-rU: direction class (Drop 0, bit 32 neutral, side 2, else 1), air +3, slot _-y2r[...], _-Kc._-C5S": [
        (6334, 112, "callproperty", "_-wn, 0"),
        (6334, 128, "pushbyte", "3"),
        (6334, 413, "pushbyte", "2"),
        (6334, 494, "pushbyte", "32"),
        (6334, 515, "pushbyte", "1"),
        (6334, 527, "pushbyte", "4"),
        (6334, 530, "pushbyte", "8"),
        (6334, 590, "pushbyte", "2"),
        (6334, 600, "pushbyte", "1"),
        (6334, 628, "add_i", ""),
        (6334, 632, "add_i", ""),
        (6334, 640, "getproperty", "_-y2r"),
        (6334, 671, "callproperty", "_-C5S, 6"),
    ],
    "_-y2r = [3, 1, 2, 6, 4, 5, 8, 11, 7, 10, 9, 9]": [
        (6336, 153, "pushbyte", "3"),
        (6336, 156, "pushbyte", "1"),
        (6336, 159, "pushbyte", "2"),
        (6336, 162, "pushbyte", "6"),
        (6336, 165, "pushbyte", "4"),
        (6336, 168, "pushbyte", "5"),
        (6336, 171, "pushbyte", "8"),
        (6336, 174, "pushbyte", "11"),
        (6336, 177, "pushbyte", "7"),
        (6336, 180, "pushbyte", "10"),
        (6336, 183, "pushbyte", "9"),
        (6336, 186, "pushbyte", "9"),
        (6336, 189, "newarray", "12"),
        (6336, 191, "initproperty", "_-y2r"),
    ],
    "slot -> power: _-Kc._-C5S calls _-42t; slots 7 / 8 / 11 read the legend's side / down / neutral signature, others the weapon list _-Z6M[slot]": [
        (1700, 55, "callproperty", "_-42t, 3"),
        (1700, 81, "pushbyte", "9"),
        (1700, 93, "getproperty", "_-UT"),
        (1700, 134, "callproperty", "_-P5Y, 0"),
        (1700, 146, "callproperty", "_-56T, 0"),
        (1700, 151, "greaterequals", ""),
        (1700, 423, "callpropvoid", "Jump, 2"),
        (1726, 168, "pushbyte", "13"),
        (1726, 178, "pushbyte", "20"),
        (1726, 495, "pushbyte", "11"),
        (1726, 520, "getproperty", "mSpecialPower1"),
        (1726, 550, "getproperty", "mSpecialPower2"),
        (1726, 661, "getproperty", "_-Z6M"),
        (1726, 665, "getlocal_2", ""),
        (1726, 681, "pushbyte", "7"),
        (1726, 708, "getproperty", "mSpecialPower1_Forward"),
        (1726, 757, "getproperty", "mSpecialPower2_Forward"),
        (1726, 790, "pushbyte", "8"),
        (1726, 817, "getproperty", "mSpecialPower1_Down"),
        (1726, 868, "getproperty", "mSpecialPower2_Down"),
        (1726, 899, "callproperty", "_-p4G, 1"),
    ],
    "air jump counter: _-P5Y() = _-3j ^ _-ef, max _-56T() = 2; ground jump -> 0, air jump +1, wall jump unchanged": [
        (2962, 5, "getproperty", "_-3j"),
        (2962, 12, "getproperty", "_-ef"),
        (2962, 16, "bitxor", ""),
        (3095, 15, "pushbyte", "2"),
        (3095, 18, "returnvalue", ""),
        (2920, 14, "bitxor", ""),
        (2920, 15, "initproperty", "_-3j"),
        (3052, 968, "pushstring", "'jump.Ground'"),
        (3052, 1058, "callpropvoid", "_-C3x, 0"),
        (3052, 2005, "pushstring", "'jump.Wall'"),
        (3052, 2159, "callproperty", "_-P5Y, 0"),
        (3052, 2172, "pushbyte", "1"),
        (3052, 2174, "add_i", ""),
        (3052, 2176, "callpropvoid", "_-k1j, 1"),
        (3052, 2414, "pushstring", "'jump.Air'"),
        (1712, 116, "initproperty", "_-UT"),
        (1712, 125, "pushbyte", "0"),
        (1712, 127, "callpropvoid", "_-k1j, 1"),
        (3034, 200, "pushbyte", "0"),
        (3034, 202, "callpropvoid", "_-k1j, 1"),
    ],
    "refresh in _-8i: on a line, not in hitstun, no _-B6B -> _-G1T, then _-Kc._-C3x() unless _-r51 != 0 and _-x2C >= 9": [
        (2984, 295, "getproperty", "_-96f"),
        (2984, 311, "callproperty", "_-5q, 0"),
        (2984, 333, "getproperty", "_-B6B"),
        (2984, 408, "initproperty", "_-G1T"),
        (2984, 414, "getproperty", "_-x2C"),
        (2984, 428, "getproperty", "_-r51"),
        (2984, 442, "pushbyte", "9"),
        (2984, 467, "callpropvoid", "_-C3x, 0"),
    ],
    "recovery count: _-31A adds 1 to _-x2C; at 9 the air jumps are used up and _-UT is set": [
        (3082, 11, "increment", ""),
        (3082, 21, "pushbyte", "9"),
        (3082, 35, "callproperty", "_-56T, 0"),
        (3082, 40, "callpropvoid", "_-k1j, 1"),
        (3082, 51, "initproperty", "_-UT"),
        (1700, 728, "callpropvoid", "_-31A, 0"),
        (1700, 738, "getproperty", "_-x2C"),
        (1700, 741, "pushbyte", "5"),
    ],
    "IsDodgeLocked: move lock, _-u5E, _-E6P, a running power, a wall, a zone test, _-Xb, _-C54; else _-x2C >= 9": [
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
        (3075, 219, "greaterequals", ""),
        (3125, 156, "callproperty", "IsDodgeLocked, 1"),
        (3125, 416, "callproperty", "Dash, 2"),
    ],
    "_-01g: time of the first hit of a hitstun chain (set by _-L3f when 0), cleared by _-Re once !_-u5E() and t > _-46I + 32": [
        (1670, 81, "initproperty", "_-u4B"),
        (1670, 88, "initproperty", "_-v3y"),
        (1670, 225, "getproperty", "_-01g"),
        (1670, 237, "initproperty", "_-01g"),
        (2981, 453, "getproperty", "_-01g"),
        (2981, 469, "callproperty", "_-u5E, 0"),
        (2981, 485, "getproperty", "_-46I"),
        (2981, 488, "pushbyte", "32"),
        (2981, 494, "lessthan", ""),
        (2981, 505, "initproperty", "_-01g"),
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
