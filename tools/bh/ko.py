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
