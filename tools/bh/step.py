"""Pinned static evidence of the order of operations inside one movement step, Entity._-8i #2984 (11.00).

See docs/entity-step-11.00.md. Byte order and data flow only: which branch runs on a given tick is not
modelled, and nothing is executed. Anchors are (method id, offset, opname, operand text as printed by
`abc-disasm`), checked with movement.check / movement.listing; branch operands are relative.
"""
from .movement import ABC_1100, check, listing
from .prng_order import slot_type

IMPULSE_CAP = 250.0      # sqrt(Entity._-y4Q = 62500.0), _-y2E.init #15351 @30022
SOFT_DROP_DECAY = 0.8    # Entity._-7c initial value, Entity.<init> #2887 @124


def fold_impulse(velocity, impulse):
    """Velocity after folding a one-tick impulse (#2984 @2800-2965 for x, @4217-4395 for y).

    Returns (new velocity, overshoot or None). A zero impulse leaves the velocity unchanged.
    """
    if impulse == 0:
        return velocity, None
    s = impulse + velocity
    if s * s > IMPULSE_CAP * IMPULSE_CAP:
        return (IMPULSE_CAP if s > 0 else -IMPULSE_CAP), s
    return s, None


SPEED_CAP = 1000.0          # local 11 of #2984 @2745
SPEED_CAP_POWER = 3000.0    # @2737, when _-Kc._-c5l (set by _-F5N._-u1N while a power runs)
SLOW_FLAG = 524288          # Entity._-4Z (script157.<init> #3173 @1231): cap / 3 when _-e3e has it


def speed_cap(power_active=False, flags=0):
    """local 11 of #2984 @2723-2781: the bound for both velocity clamps (x @2969-3053, y @4399-4483)."""
    cap = SPEED_CAP_POWER if power_active else SPEED_CAP
    if flags & SLOW_FLAG:
        cap = cap / 3
    return cap


def clamp(velocity, cap):
    """`v > cap -> cap`, else `v < -cap -> -cap` (ifngt / ifnlt, so NaN passes unchanged)."""
    if velocity > cap:
        return cap
    if velocity < -cap:
        return -cap
    return velocity


ANCHORS = {ABC_1100: {
    "constants: _-7c = 0.8 (Entity.<init>), Entity._-y4Q = 62500 = 250^2": [
        (2887, 124, "pushdouble", "0.8"),
        (2887, 127, "initproperty", "_-7c"),
        (15351, 30022, "pushdouble", "62500.0"),
        (15351, 30026, "initproperty", "_-y4Q"),
    ],
    "1. soft-line drop: on a line with type & 2, _-96f = null and the impulse _-A4A *= _-7c": [
        (2984, 1815, "getproperty", "type"),
        (2984, 1819, "pushbyte", "2"),
        (2984, 1822, "bitand", ""),
        (2984, 1840, "initproperty", "_-96f"),
        (2984, 1894, "getproperty", "_-7c"),
        (2984, 1897, "multiply", ""),
        (2984, 1914, "callpropvoid", "_-N5C::_-E1t, 2"),
    ],
    "2. horizontal impulse fold: v1D = v1D + _-84, or +/-250 (overshoot kept in _-J1m) when the square exceeds _-y4Q": [
        (2984, 2820, "getproperty", "_-84"),
        (2984, 2847, "getproperty", "_-84"),
        (2984, 2865, "getproperty", "_-v1D"),
        (2984, 2873, "add", ""),
        (2984, 2887, "getproperty", "_-y4Q"),
        (2984, 2891, "ifngt", "56"),
        (2984, 2901, "initproperty", "_-J1m"),
        (2984, 2931, "pushdouble", "250.0"),
        (2984, 2939, "pushdouble", "-250.0"),
        (2984, 2943, "callpropvoid", "_-N5C::_-E1t, 2"),
        (2984, 2965, "callpropvoid", "_-N5C::_-E1t, 2"),
    ],
    "3. horizontal step: local12 = v1D * 0.384, then on a ground line a walk loop along _-96f until local12 == 0": [
        (2984, 3092, "findproperty", "_-v1D"),
        (2984, 3106, "getproperty", "_-Vj"),
        (2984, 3110, "multiply", ""),
        (2984, 3112, "setlocal", "12"),
        (2984, 3117, "getproperty", "_-96f"),
        (2984, 3125, "ifeq", "1088"),
        (2984, 3138, "getproperty", "_-N3a"),
        (2984, 3203, "callpropvoid", "normalize, 1"),
        (2984, 3290, "callproperty", "_-X2e, 10"),
        (2984, 3333, "getproperty", "x"),
        (2984, 3354, "callpropvoid", "_-N5C::_-E1t, 2"),
        (2984, 3387, "getproperty", "y"),
        (2984, 3408, "callpropvoid", "_-N5C::_-E1t, 2"),
        (2984, 3426, "getlocal", "12"),
        (2984, 3448, "setlocal", "12"),
        (2984, 3466, "initproperty", "_-96f"),
        (2984, 4197, "pushtrue", ""),
        (2984, 4202, "ifgt", "7"),
        (2984, 4211, "lessthan", ""),
        (2984, 4213, "iftrue", "-1084"),
    ],
    "4. vertical impulse fold: P5S = P5S + _-A4A, or +/-250 (overshoot in _-d4x), then P5S clamped to +/-local11": [
        (2984, 4228, "getproperty", "_-A4A"),
        (2984, 4239, "ifgt", "24"),
        (2984, 4254, "getproperty", "_-A4A"),
        (2984, 4265, "lessthan", ""),
        (2984, 4281, "getproperty", "_-A4A"),
        (2984, 4299, "getproperty", "_-P5S"),
        (2984, 4307, "add", ""),
        (2984, 4321, "getproperty", "_-y4Q"),
        (2984, 4325, "ifngt", "52"),
        (2984, 4334, "initproperty", "_-d4x"),
        (2984, 4361, "pushdouble", "250.0"),
        (2984, 4369, "pushdouble", "-250.0"),
        (2984, 4373, "callpropvoid", "_-N5C::_-E1t, 2"),
        (2984, 4395, "callpropvoid", "_-N5C::_-E1t, 2"),
        (2984, 4416, "getlocal", "11"),
        (2984, 4418, "ifngt", "22"),
        (2984, 4436, "callpropvoid", "_-N5C::_-E1t, 2"),
        (2984, 4463, "negate", ""),
        (2984, 4464, "ifnlt", "19"),
        (2984, 4483, "callpropvoid", "_-N5C::_-E1t, 2"),
    ],
    "5. free move: displacement (local12, P5S * 0.384), +2.02 on y when a ground line is set, swept with _-X2e": [
        (2984, 6628, "getlocal", "12"),
        (2984, 6630, "initproperty", "x"),
        (2984, 6643, "getproperty", "_-P5S"),
        (2984, 6667, "getproperty", "_-Vj"),
        (2984, 6671, "multiply", ""),
        (2984, 6672, "initproperty", "y"),
        (2984, 6676, "findproperty", "_-96f"),
        (2984, 6704, "pushdouble", "2.02"),
        (2984, 6707, "add", ""),
        (2984, 6896, "callproperty", "_-X2e, 10"),
    ],
    "6. end of step: the impulse slots _-84 and _-A4A are reset to 0": [
        (2984, 14563, "findproperty", "_-Z2G"),
        (2984, 14573, "getproperty", "_-84"),
        (2984, 14577, "pushdouble", "0.0"),
        (2984, 14579, "callpropvoid", "_-N5C::_-E1t, 2"),
        (2984, 14593, "getproperty", "_-A4A"),
        (2984, 14597, "pushdouble", "0.0"),
        (2984, 14599, "callpropvoid", "_-N5C::_-E1t, 2"),
        (2984, 14603, "returnvoid", ""),
    ],
    "speed cap: local 11 = _-Kc._-c5l ? 3000 : 1000, / 3 when _-e3e & Entity._-4Z; one write on every path": [
        (2984, 2729, "getproperty", "_-c5l"),
        (2984, 2737, "pushdouble", "3000.0"),
        (2984, 2745, "pushdouble", "1000.0"),
        (2984, 2750, "setlocal", "11"),
        (2984, 2762, "getproperty", "_-4Z"),
        (2984, 2777, "pushbyte", "3"),
        (2984, 2779, "divide", ""),
        (2984, 2781, "setlocal", "11"),
        (3173, 1231, "pushint", "524288"),
        (3173, 1233, "initproperty", "_-4Z"),
    ],
    "both clamps use local 11: x after the x fold, y after the y fold": [
        (2984, 2986, "getlocal", "11"),
        (2984, 3006, "callpropvoid", "_-N5C::_-E1t, 2"),
        (2984, 3050, "getlocal", "11"),
        (2984, 3052, "negate", ""),
        (2984, 4416, "getlocal", "11"),
        (2984, 4436, "callpropvoid", "_-N5C::_-E1t, 2"),
        (2984, 4480, "getlocal", "11"),
        (2984, 4482, "negate", ""),
    ],
    "_-c5l: false on entry of _-F5N._-u1N, true only when _-o3I is set and _-o3I._-82f": [
        (1745, 66, "pushfalse", ""),
        (1745, 67, "initproperty", "_-c5l"),
        (1745, 125, "getproperty", "_-82f"),
        (1745, 135, "returnvoid", ""),
        (1745, 301, "pushtrue", ""),
        (1745, 302, "initproperty", "_-c5l"),
    ],
    "wall contact _-r51: saved to local 27 and cleared each step; 1 / 2 by the side of a vertical line": [
        (2984, 8873, "getproperty", "_-r51"),
        (2984, 8878, "setlocal", "27"),
        (2984, 8884, "pushbyte", "0"),
        (2984, 8886, "initproperty", "_-r51"),
        (2984, 11365, "getproperty", "startX"),
        (2984, 11370, "getproperty", "_-f1i"),
        (2984, 11373, "equals", ""),
        (2984, 11383, "getproperty", "_-S1A"),
        (2984, 11400, "pushdouble", "1.01"),
        (2984, 11493, "callproperty", "_-t46, 0"),
        (2984, 11517, "getlocal", "27"),
        (2984, 11547, "getproperty", "startX"),
        (2984, 11559, "getproperty", "_-11W"),
        (2984, 11571, "pushbyte", "1"),
        (2984, 11578, "pushbyte", "2"),
        (2984, 11581, "initproperty", "_-r51"),
        (2984, 11586, "getlocal", "27"),
        (2984, 11605, "getproperty", "_-P5S"),
        (2984, 11613, "pushbyte", "0"),
        (2984, 11635, "callpropvoid", "_-N5C::_-E1t, 2"),
        (3034, 285, "pushbyte", "0"),
        (3034, 287, "initproperty", "_-r51"),
    ],
    "power fire _-l4X._-O1K: CastImpulseX / Y (_-C6Z / _-8S) set v1D (sign by _-L0) / P5S unless 2147483647": [
        (91, 381, "iffalse", "1260"),
        (91, 393, "getproperty", "_-C6Z"),
        (91, 396, "pushint", "2147483647"),
        (91, 430, "getproperty", "_-L0"),
        (91, 446, "getproperty", "_-C6Z"),
        (91, 449, "negate_i", ""),
        (91, 467, "callpropvoid", "_-N5C::_-E1t, 2"),
        (91, 1095, "getproperty", "_-8S"),
        (91, 1098, "pushint", "2147483647"),
        (91, 1125, "getproperty", "_-P5S"),
        (91, 1136, "getproperty", "_-8S"),
        (91, 1140, "callpropvoid", "_-N5C::_-E1t, 2"),
        (59, 51, "getproperty", "_-k4b"),
        (59, 58, "iffalse", "1511"),
        (59, 68, "pushbyte", "16"),
        (59, 70, "modulo", ""),
        (59, 173, "initproperty", "_-k4b"),
        (59, 197, "getproperty", "_-a2"),
        (59, 210, "initproperty", "_-82O"),
        (59, 222, "getproperty", "_-Sp"),
        (59, 276, "getproperty", "_-f5c"),
        (59, 289, "initproperty", "_-E5S"),
        (59, 609, "callpropvoid", "_-O1K, 1"),
        (6483, 11090, "getlocal", "6"),
        (6483, 11503, "getproperty", "_-a2"),
        (39, 283, "pushbyte", "1"),
        (39, 306, "pushint", "512"),
        (39, 310, "pushbyte", "64"),
        (39, 328, "getproperty", "_-Y4G"),
        (39, 340, "getproperty", "_-NT"),
        (39, 357, "getproperty", "_-G6R"),
        (39, 376, "getproperty", "_-yD"),
        (39, 379, "initproperty", "_-01d"),
    ],
}}

SLOTS = {ABC_1100: [
    ("Entity", "_-Z2G", "_-N5C"),
    ("Entity", "_-v1D", "uint"),
    ("Entity", "_-P5S", "uint"),
    ("Entity", "_-A4A", "uint"),
    ("Entity", "_-84", "uint"),
    ("Entity", "_-7c", "Number"),
    ("Entity", "_-J1m", "Number"),
    ("Entity", "_-d4x", "Number"),
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
