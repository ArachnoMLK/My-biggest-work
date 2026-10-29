"""KO (ring-out) bounds test of patch 11.00, as a pure function plus pinned bytecode evidence.

See docs/ko-11.00.md. `ko_mask` mirrors `_-h3U._-c5C` #3596 instruction by instruction; `verify` checks
that the pinned ABC still has the shape the function was read from. Static evidence only: nothing
here runs the game or the bytecode.

Anchors are (method id, offset, opname, operand text as printed by `abc-disasm`), checked with
movement.check / movement.listing. Branch operands are relative, as `listing` prints them.
"""
from .movement import ABC_1100, check, listing
from .prng_order import slot_type

TOP, BOTTOM, LEFT, RIGHT = 1, 2, 4, 8   # bits of the mask returned by #3596
SOFT_MARGIN = 200.0                     # pushdouble 200.0 in #3596 (@132, @156, @175)


def ko_mask(x, y, cam, kill, exact, top_allowed):
    """Mask of the kill lines crossed by (x, y), as `_-h3U._-c5C(x, y, exact, top_allowed)` returns it.

    cam: (left, top, right, bottom) of the map's CameraBounds rectangle (flash Rectangle getters).
    kill: dict with LeftKill, RightKill, TopKill, BottomKill (uint) and HardLeftKill, HardRightKill,
    SoftTopKill (Boolean) of the LevelType. `exact` is the caller's `_-5q()` (in hitstun),
    `top_allowed` its `!_-wn() || _-r51 != 0` (`!_-wn()` = touching a collision line); see docs/ko-11.00.md.
    Comparisons are strict, as `ifnlt` / `ifngt` branch on their negation.
    """
    left, top, right, bottom = cam
    if (exact or top_allowed) and y < top - kill["TopKill"]:
        return TOP                                   # @34-69: early return, other lines not tested
    lo = left - kill["LeftKill"]
    hi = kill["RightKill"] + right
    if not exact:
        if kill["SoftTopKill"] and y < top - kill["TopKill"] - SOFT_MARGIN:
            return TOP                               # @108-143
        if not kill["HardLeftKill"]:
            lo -= SOFT_MARGIN
        if not kill["HardRightKill"]:
            hi += SOFT_MARGIN
    mask = 0
    if x < lo:
        mask |= LEFT
    elif x > hi:                                     # @208: only tested when x >= lo
        mask |= RIGHT
    if y > kill["BottomKill"] + bottom:
        mask |= BOTTOM
    return mask


# group -> anchors. Group names are the claims of docs/ko-11.00.md they support.
REPLAY_BITS = 1024 | 2048 | 8192                # replay / spectate playback (code-map-11.00.md)
NO_BASE_BITS = 2 | 4 | 0x400000 | REPLAY_BITS | 262144 | 524288


def ko_time_base(w35, ce, e4h, n4k):
    """Time base the replay writer `_-S45._-04F` #6711 @54-398 subtracts from KO face times.

    0 when `_-w35` has a bit of NO_BASE_BITS, or 32768 (or 32 with 32768 in the saved `_-ce`), or when
    `_-e4h == 2` and `_-w35` has 16 (or 32 with 16 in `_-ce`); otherwise `_-n4k - 16`.
    """
    if w35 & NO_BASE_BITS:
        return 0
    if w35 & 32768 or (w35 & 32 and ce & 32768):
        return 0
    if e4h == 2 and (w35 & 16 or (w35 & 32 and ce & 16)):
        return 0
    return (n4k - 16) % (1 << 32)


ANCHORS = {ABC_1100: {
    "LevelType._-a5F parses the kill lines into uint/Boolean fields": [
        (5275, 528, "pushstring", "'LeftKill'"),
        (5275, 548, "initproperty", "_-D3M"),
        (5275, 558, "pushstring", "'RightKill'"),
        (5275, 578, "initproperty", "_-a4Q"),
        (5275, 588, "pushstring", "'TopKill'"),
        (5275, 608, "initproperty", "_-Y2N"),
        (5275, 618, "pushstring", "'BottomKill'"),
        (5275, 638, "initproperty", "_-zh"),
        (5275, 1281, "pushstring", "'HardLeftKill'"),
        (5275, 1301, "initproperty", "_-l4N"),
        (5275, 1310, "pushstring", "'HardRightKill'"),
        (5275, 1330, "initproperty", "_-23z"),
        (5275, 1437, "pushstring", "'SoftTopKill'"),
        (5275, 1457, "initproperty", "_-M58"),
    ],
    "the level loader stores CameraBounds in _-I1f._-8I": [
        (5293, 1470, "pushstring", "'CameraBounds'"),
        (5293, 1484, "getproperty", "_-I1f"),
        (5293, 1502, "initproperty", "_-8I"),
    ],
    "_-h3U._-c5C: top line first (exact or top_allowed), then widened sides, then bottom": [
        (3596, 6, "getproperty", "_-I1f"),
        (3596, 10, "getproperty", "_-8I"),
        (3596, 26, "getproperty", "_-IX"),
        (3596, 36, "iftrue", "4"),
        (3596, 44, "iffalse", "22"),
        (3596, 51, "getproperty", "top"),
        (3596, 57, "getproperty", "_-Y2N"),
        (3596, 61, "subtract", ""),
        (3596, 62, "ifnlt", "4"),
        (3596, 69, "returnvalue", ""),
        (3596, 72, "getproperty", "left"),
        (3596, 78, "getproperty", "_-D3M"),
        (3596, 82, "subtract", ""),
        (3596, 88, "getproperty", "_-a4Q"),
        (3596, 94, "getproperty", "right"),
        (3596, 97, "add", ""),
        (3596, 104, "iffalse", "75"),
        (3596, 110, "getproperty", "_-M58"),
        (3596, 114, "iffalse", "26"),
        (3596, 121, "getproperty", "top"),
        (3596, 127, "getproperty", "_-Y2N"),
        (3596, 131, "subtract", ""),
        (3596, 132, "pushdouble", "200.0"),
        (3596, 136, "ifnlt", "4"),
        (3596, 143, "returnvalue", ""),
        (3596, 146, "getproperty", "_-l4N"),
        (3596, 156, "pushdouble", "200.0"),
        (3596, 159, "subtract", ""),
        (3596, 165, "getproperty", "_-23z"),
        (3596, 175, "pushdouble", "200.0"),
        (3596, 178, "add", ""),
        (3596, 191, "ifnlt", "13"),
        (3596, 197, "pushbyte", "4"),
        (3596, 211, "ifngt", "9"),
        (3596, 217, "pushbyte", "8"),
        (3596, 227, "getproperty", "_-zh"),
        (3596, 233, "getproperty", "bottom"),
        (3596, 237, "add", ""),
        (3596, 239, "ifngt", "9"),
        (3596, 245, "pushbyte", "2"),
        (3596, 254, "returnvalue", ""),
    ],
    "phase 5, Entity._-8i: mask = c5C(x, y, _-5q(), !_-wn() || _-r51 != 0), stored in _-a3D if non-zero": [
        (2984, 14276, "findproperty", "_-Z2G"),
        (2984, 14285, "getproperty", "_-11W"),
        (2984, 14288, "callproperty", "_-N5C::_-U13, 1"),
        (2984, 14302, "getproperty", "_-75K"),
        (2984, 14305, "callproperty", "_-N5C::_-U13, 1"),
        (2984, 14313, "callproperty", "_-5q, 0"),
        (2984, 14322, "callproperty", "_-wn, 0"),
        (2984, 14337, "getproperty", "_-r51"),
        (2984, 14346, "callproperty", "_-c5C, 4"),
        (2984, 14361, "iffalse", "8"),
        (2984, 14370, "initproperty", "_-a3D"),
        (2984, 14383, "getproperty", "_-51y"),
        (2984, 14479, "callproperty", "_-R4C, 6"),
        (2984, 14513, "pushbyte", "32"),
        (2984, 14517, "initproperty", "_-a3D"),
    ],
    "phase 6, Entity._-10 -> _-eR consumes _-a3D": [
        (3336, 2751, "callpropvoid", "_-k5H, 1"),
        (3336, 2802, "callpropvoid", "_-10, 1"),
        (2990, 548, "callpropvoid", "_-x1M, 3"),
        (2990, 566, "callpropvoid", "_-eR, 1"),
        (3138, 30, "getproperty", "_-a3D"),
        (3138, 36, "iffalse", "9"),
        (3138, 47, "not", ""),
        (3138, 49, "iffalse", "1"),
        (3138, 53, "returnvoid", ""),
        (3138, 60, "getproperty", "_-vs"),
        (3138, 68, "iffalse", "1"),
        (3138, 72, "returnvoid", ""),
        (3138, 76, "getproperty", "_-83l"),
        (3138, 79, "iffalse", "9"),
        (3138, 88, "initproperty", "_-a3D"),
        (3138, 91, "returnvoid", ""),
        (3138, 355, "getproperty", "_-a3D"),
        (3138, 364, "callproperty", "_-5q, 0"),
        (3138, 369, "iffalse", "9"),
        (3138, 375, "pushbyte", "16"),
        (3138, 378, "bitor", ""),
        (3138, 395, "initproperty", "_-65w"),
        (3138, 404, "getproperty", "_-w35"),
        (3138, 414, "pushint", "4194304"),
        (3138, 472, "callpropvoid", "_-84v, 4"),
    ],
    "exact = _-5q(): hitstun flag, set by the hit with (t, stun) and cleared after t > start + stun at speed <= 50": [
        (2931, 5, "getproperty", "_-H5X"),
        (2931, 10, "urshift", ""),
        (2931, 14, "bitand", ""),
        (2931, 28, "bitand", ""),
        (2889, 9, "callproperty", "_-W2b, 1"),
        (2889, 14, "initproperty", "_-H5X"),
        (1675, 198, "getproperty", "_-7Z"),
        (1675, 203, "multiply_i", ""),
        (1675, 229, "callpropvoid", "_-L3f, 7"),
        (1675, 1816, "getproperty", "_-7Z"),
        (1675, 1822, "multiply_i", ""),
        (1675, 1824, "setlocal", "41"),
        (1675, 2541, "getlocal", "41"),
        (1675, 2565, "callpropvoid", "_-L3f, 7"),
        (1670, 73, "pushtrue", ""),
        (1670, 74, "callpropvoid", "_-q2W, 1"),
        (1670, 81, "initproperty", "_-u4B"),
        (1670, 86, "getlocal_3", ""),
        (1670, 88, "initproperty", "_-v3y"),
        (2984, 214, "getproperty", "_-v1D"),
        (2984, 234, "callproperty", "_-N5C::_-U13, 1"),
        (2984, 249, "getproperty", "_-P5S"),
        (2984, 269, "callproperty", "_-N5C::_-U13, 1"),
        (2984, 275, "add", ""),
        (2984, 285, "callpropvoid", "_-Re, 2"),
        (2981, 34, "callproperty", "_-5q, 0"),
        (2981, 73, "getproperty", "_-u4B"),
        (2981, 81, "getproperty", "_-v3y"),
        (2981, 85, "add_i", ""),
        (2981, 88, "lessthan", ""),
        (2981, 100, "getproperty", "_-Nj"),
        (2981, 103, "lessequals", ""),
        (2981, 113, "pushfalse", ""),
        (2981, 114, "callpropvoid", "_-q2W, 1"),
        (15351, 30077, "pushdouble", "2500.0"),
        (15351, 30081, "initproperty", "_-Nj"),
        (3034, 221, "callpropvoid", "_-q2W, 1"),
    ],
    "_-wn() = (_-96f == null), _-96f = the line returned by the collision query": [
        (2949, 5, "getproperty", "_-j5M"),
        (2907, 9, "callproperty", "_-W2b, 1"),
        (2907, 14, "initproperty", "_-j5M"),
        (2984, 3290, "callproperty", "_-X2e, 10"),
        (2984, 3302, "setlocal", "17"),
        (2984, 3464, "getlocal", "17"),
        (2984, 3466, "initproperty", "_-96f"),
        (2984, 13127, "initproperty", "_-96f"),
        (2984, 13160, "getproperty", "_-96f"),
        (2984, 13168, "equals", ""),
        (2984, 13169, "callpropvoid", "_-v2J, 1"),
        (3034, 193, "callpropvoid", "_-v2J, 1"),
    ],
    "phase 6, Entity._-eR commit order: veto, attribution, reset, scoring, lives, respawn": [
        (3138, 109, "callproperty", "_-K19, 2"),
        (3138, 118, "returnvoid", ""),
        (3138, 167, "getproperty", "_-W6D"),
        (3138, 185, "getproperty", "_-V6R"),
        (3138, 198, "callproperty", "haxe:IMap::get, 1"),
        (3138, 253, "callpropvoid", "_-D2a, 3"),
        (3138, 273, "callpropvoid", "_-916, 2"),
        (3138, 281, "getproperty", "_-U1F"),
        (3138, 287, "iffalse", "61"),
        (3138, 347, "callpropvoid", "_-x1M, 2"),
        (3138, 385, "callpropvoid", "_-p1Y, 0"),
        (3138, 553, "callpropvoid", "_-jI, 3"),
        (3138, 565, "getproperty", "_-V"),
        (3138, 569, "decrement_i", ""),
        (3138, 570, "initproperty", "_-V"),
        (3138, 592, "getproperty", "_-K4x"),
        (3138, 706, "callpropvoid", "_-f6Q, 1"),
        (3138, 771, "callpropvoid", "_-U5x, 2"),
        (3138, 984, "callproperty", "_-x1R, 2"),
        (3138, 1085, "callproperty", "_-K19, 1"),
        (3138, 1113, "callproperty", "_-r3D, 1"),
        (3138, 1124, "iffalse", "24"),
        (3138, 1134, "getproperty", "_-W1R"),
        (3138, 1147, "callpropvoid", "Respawn, 3"),
        (3034, 11, "getproperty", "_-v1D"),
        (3034, 16, "callpropvoid", "_-N5C::_-E1t, 2"),
        (3034, 29, "getproperty", "_-P5S"),
        (3034, 34, "callpropvoid", "_-N5C::_-E1t, 2"),
        (3034, 68, "getproperty", "_-A4A"),
        (3034, 74, "callpropvoid", "_-N5C::_-E1t, 2"),
        (3034, 110, "initproperty", "_-a3D"),
        (3034, 287, "initproperty", "_-r51"),
        (3034, 444, "initproperty", "_-96f"),
        (3034, 451, "initproperty", "_-U1F"),
        (2990, 557, "callpropvoid", "_-82z, 1"),
    ],
    "replay KO faces: _-jI -> _-24k._-IH adds (type 1/2/9, t, victim); _-S45._-04F writes them": [
        (3047, 277, "getproperty", "_-2d"),
        (3047, 285, "callproperty", "_-IH, 3"),
        (5941, 38, "getproperty", "_-L4e"),
        (5941, 72, "getproperty", "_-L4e"),
        (5941, 121, "equals", ""),
        (5941, 127, "pushbyte", "2"),
        (5941, 139, "getproperty", "_-25G"),
        (5941, 142, "equals", ""),
        (5941, 147, "pushbyte", "9"),
        (5941, 154, "pushbyte", "1"),
        (5941, 171, "getproperty", "_-11"),
        (5941, 196, "getproperty", "_-l2t"),
        (5941, 266, "pushint", "1024"),
        (5941, 270, "pushint", "2048"),
        (5941, 274, "pushint", "8192"),
        (5941, 291, "getproperty", "_-X21"),
        (5941, 295, "greaterequals", ""),
        (5941, 372, "getproperty", "mTimeStamp"),
        (5941, 377, "equals", ""),
        (5941, 396, "getproperty", "mType"),
        (5941, 452, "getproperty", "_-I4o"),
        (5941, 486, "returnvalue", ""),
        (5941, 497, "pushnull", ""),
        (5941, 513, "getproperty", "_-N2o"),
        (5941, 516, "increment", ""),
        (5941, 532, "getproperty", "_-11"),
        (5941, 543, "getproperty", "_-l2t"),
        (5941, 546, "constructprop", "_-64j, 9"),
        (5941, 563, "callpropvoid", "_-T1T, 1"),
        (5946, 14, "getproperty", "mTimeStamp"),
        (5946, 78, "getproperty", "mTimeStamp"),
        (5946, 83, "lessequals", ""),
        (5946, 101, "callpropvoid", "_-p3g, 3"),
        (5946, 133, "callpropvoid", "http://adobe.com/AS3/2006/builtin::push, 1"),
        (5929, 13, "initproperty", "mType"),
        (5929, 21, "initproperty", "mTimeStamp"),
        (5929, 39, "initproperty", "_-R4U"),
        (5929, 49, "initproperty", "_-I4o"),
        (5929, 58, "initproperty", "_-31D"),
        (5929, 66, "initproperty", "_-E2h"),
        (5929, 75, "initproperty", "_-eI"),
        (6711, 390, "getproperty", "_-n4k"),
        (6711, 393, "pushbyte", "16"),
        (6711, 395, "subtract_i", ""),
        (6711, 408, "pushbyte", "4"),
        (6711, 411, "pushbyte", "5"),
        (6711, 414, "callpropvoid", "_-b5p, 2"),
        (6711, 433, "getproperty", "_-d3I"),
        (6711, 436, "getproperty", "length"),
        (6711, 487, "getproperty", "mType"),
        (6711, 496, "lookupswitch", "35, 35, 43, 43, 35, 35, 35, 35, 35, 35, 43"),
        (6711, 547, "pushbyte", "1"),
        (6711, 549, "pushbyte", "1"),
        (6711, 551, "callpropvoid", "_-b5p, 2"),
        (6711, 563, "pushbyte", "5"),
        (6711, 568, "getproperty", "_-I4o"),
        (6711, 572, "callpropvoid", "_-b5p, 2"),
        (6711, 588, "getproperty", "mTimeStamp"),
        (6711, 592, "greaterequals", ""),
        (6711, 610, "getlocal", "5"),
        (6711, 612, "subtract_i", ""),
        (6711, 614, "callpropvoid", "_-I1l, 1"),
        (6711, 634, "pushbyte", "1"),
        (6711, 636, "pushbyte", "0"),
        (6711, 638, "callpropvoid", "_-b5p, 2"),
    ],
    "base condition: 0 under 2|4|0x400000, replay bits, 32768 (or 32 + _-ce), e4h == 2 with 16; else _-n4k - 16": [
        (6711, 63, "pushbyte", "4"),
        (6711, 66, "pushbyte", "2"),
        (6711, 70, "pushint", "4194304"),
        (6711, 99, "pushint", "1024"),
        (6711, 103, "pushint", "2048"),
        (6711, 107, "pushint", "8192"),
        (6711, 125, "pushint", "262144"),
        (6711, 128, "pushint", "524288"),
        (6711, 170, "pushint", "32768"),
        (6711, 198, "pushbyte", "32"),
        (6711, 212, "getproperty", "_-ce"),
        (6711, 231, "getproperty", "_-e4h"),
        (6711, 235, "pushbyte", "2"),
        (6711, 243, "pushbyte", "16"),
        (6711, 282, "getproperty", "_-ce"),
        (6711, 339, "pushint", "1024"),
        (6711, 377, "pushbyte", "0"),
        (6711, 390, "getproperty", "_-n4k"),
        (6711, 393, "pushbyte", "16"),
        (6711, 395, "subtract_i", ""),
        (6711, 398, "setlocal", "5"),
    ],
    "base: _-n4k is the match start (_-Px.StartTime), set to the clock of the first tick by #3336": [
        (10723, 8, "getproperty", "_-n4k"),
        (10723, 11, "returnvalue", ""),
        (3545, 153, "findproperty", "_-n4k"),
        (3545, 156, "getlocal_1", ""),
        (3545, 157, "initproperty", "_-n4k"),
        (3336, 1910, "pushbyte", "16"),
        (3336, 1912, "add_i", ""),
        (3336, 1929, "getproperty", "_-n4k"),
        (3336, 1932, "pushbyte", "0"),
        (3336, 1935, "iffalse", "22"),
        (3336, 1943, "getlocal", "17"),
        (3336, 1945, "callpropvoid", "_-Y6a, 1"),
    ],
}}

# (class, slot, declared type) of every field the KO path reads or writes.
SLOTS = {ABC_1100: [
    ("_-h3U", "_-I1f", "_-a2j"),
    ("_-a2j", "_-8I", "flash.geom::Rectangle"),
    ("_-a2j", "_-IX", "LevelType"),
    ("LevelType", "_-D3M", "uint"),
    ("LevelType", "_-a4Q", "uint"),
    ("LevelType", "_-Y2N", "uint"),
    ("LevelType", "_-zh", "uint"),
    ("LevelType", "_-l4N", "Boolean"),
    ("LevelType", "_-23z", "Boolean"),
    ("LevelType", "_-M58", "Boolean"),
    ("Entity", "_-a3D", "uint"),
    ("Entity", "_-r51", "uint"),
    ("Entity", "_-H5X", "uint"),
    ("Entity", "_-j5M", "uint"),
    ("Entity", "_-u4B", "uint"),
    ("Entity", "_-v3y", "uint"),
    ("Entity", "_-96f", "_-R15"),
    ("Entity", "_-V", "int"),
    ("Entity", "_-W6D", "uint"),
    ("Entity", "_-U1F", "Boolean"),
    ("_-h3U", "_-m17", "LinkUpdater"),
    ("_-h3U", "_-W1R", "_-X6R"),
]}


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
    for cls, slot, typ in SLOTS[sha]:
        found = slot_type(abc, cls, slot)
        if found != typ:
            bad.append(f"slot {cls}.{slot}: want {typ}, found {found}")
    return bad


def counts(sha):
    """(anchors, slots) pinned for an ABC."""
    return sum(len(a) for a in ANCHORS[sha].values()), len(SLOTS[sha])
