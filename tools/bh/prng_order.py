"""Pinned static evidence for the draw order of the replay-seeded match generators (Q3).

See docs/prng-order-11.00.md. This checks bytecode *shape* only: receivers, call order, guards, sole
referencing methods and slot types of the ABC whose SHA-256 is the key of each table. It does not run
the game or the bytecode and is not an oracle: passing means the documented static paths still exist.

Anchors are (method id, offset, opname, operand text as printed by `abc-disasm`), checked with
movement.check / movement.listing.
"""
from . import abc as abcmod
from .movement import ABC_1100, check, listing

# group -> anchors. Group names are the claims of docs/prng-order-11.00.md they support.
ANCHORS = {ABC_1100: {
    "replay start sets mode 1024, then seeds R and I": [
        (3624, 119, "pushint", "1024"),
        (3624, 123, "initproperty", "_-w35"),
        (3624, 259, "callpropvoid", "_-Y3u, 2"),
    ],
    "lesson start sets mode 0x1000000, seeds with no seed, then sets _-3I": [
        (3630, 53, "callpropvoid", "_-Y3u, 1"),
        (3630, 136, "pushint", "16777216"),
        (3630, 140, "initproperty", "_-w35"),
        (3630, 152, "callpropvoid", "_-N13, 1"),
        (5142, 68, "initproperty", "_-3I"),
    ],
    "_-z1C._-O4q: needs _-3I and mode bit 0x1000000 (or bit 32 with saved _-ce bit)": [
        (5131, 5, "getproperty", "_-3I"),
        (5131, 12, "ifne", "2"),
        (5131, 16, "pushfalse", ""),
        (5131, 17, "returnvalue", ""),
        (5131, 29, "pushint", "16777216"),
        (5131, 36, "getproperty", "_-w35"),
        (5131, 40, "bitand", ""),
        (5131, 46, "iffalse", "38"),
        (5131, 54, "pushbyte", "32"),
        (5131, 57, "bitand", ""),
        (5131, 62, "iffalse", "16"),
        (5131, 67, "getproperty", "_-ce"),
        (5131, 72, "bitand", ""),
        (5131, 77, "returnvalue", ""),
        (5131, 82, "pushfalse", ""),
        (5131, 83, "returnvalue", ""),
        (5131, 88, "pushtrue", ""),
        (5131, 89, "returnvalue", ""),
    ],
    "other mode writers seen on replay paths keep both bits clear": [
        (3336, 4367, "pushint", "2048"),
        (3336, 4370, "initproperty", "_-w35"),
        (3626, 33, "initproperty", "_-ce"),
        (3626, 105, "pushint", "1024"),
        (3626, 127, "pushint", "2048"),
        (3626, 134, "pushbyte", "32"),
        (3626, 137, "initproperty", "_-w35"),
    ],
    "tick phases: rules 3, items 4, lesson-or-rules 9": [
        (3336, 2606, "callproperty", "_-O4q, 0"),
        (3336, 2612, "iffalse", "13"),
        (3336, 2624, "callpropvoid", "_-u1O, 1"),
        (3336, 2695, "callpropvoid", "_-O3d, 2"),
        (3336, 2973, "callproperty", "_-O4q, 0"),
        (3336, 2978, "iffalse", "19"),
        (3336, 2992, "callpropvoid", "_-44D, 1"),
        (3336, 3009, "callproperty", "_-m4d, 1"),
    ],
    "lesson tick: MessageTrigger.Tick draws R": [
        (5129, 12, "getproperty", "_-vs"),
        (5129, 87, "coerce", "MessageTrigger"),
        (5129, 92, "callpropvoid", "Tick, 1"),
        (5809, 710, "getproperty", "_-s3D"),
        (5809, 713, "getproperty", "_-22"),
        (5809, 716, "coerce", "Random"),
        (5809, 731, "callproperty", "_-f4c, 0"),
    ],
    "items phase 4: _-O3d refreshes _-Y1h then _-5J from I": [
        (4879, 51, "callpropvoid", "_-96d, 1"),
        (4879, 58, "callpropvoid", "_-u43, 1"),
        (4876, 562, "callpropvoid", "_-e3K, 4"),
        (4876, 566, "findproperty", "_-Y1h"),
        (4876, 572, "getproperty", "_-22"),
        (4876, 575, "callproperty", "_-f4c, 0"),
        (4876, 580, "initproperty", "_-Y1h"),
        (4880, 560, "callpropvoid", "_-e3K, 4"),
        (4880, 570, "getproperty", "_-22"),
        (4880, 573, "callproperty", "_-f4c, 0"),
        (4880, 578, "initproperty", "_-5J"),
        (4908, 9, "callpropvoid", "_-24O, 1"),
        (4908, 27, "initproperty", "_-Y1h"),
        (4908, 44, "initproperty", "_-5J"),
    ],
    "frame: replay modes run _-M4q only; _-M4q runs _-01I then the screen stack": [
        (3337, 1552, "pushint", "1024"),
        (3337, 1576, "callpropvoid", "_-M4q, 0"),
        (3337, 1648, "pushint", "1024"),
        (3337, 1683, "callproperty", "_-M4q, 0"),
        (3335, 1815, "callproperty", "_-01I, 0"),
        (3335, 2556, "callpropvoid", "_-w10, 0"),
        (9548, 24, "getproperty", "_-Bn"),
        (9548, 38, "callpropvoid", "_-D6k, 0"),
        (4331, 303, "callpropvoid", "OnTickScreen, 0"),
    ],
    "ScreenScoreboard tick: _-9D._-Y15 once, at screen tick _-xI == 2": [
        (10946, 264, "getproperty", "_-xI"),
        (10946, 267, "pushbyte", "2"),
        (10946, 271, "iffalse", "72"),
        (10946, 293, "getproperty", "_-r5y"),
        (10946, 334, "callpropvoid", "_-Y15, 0"),
        (10962, 222, "initproperty", "_-xI"),
    ],
    "_-9D._-Y15 draws R once or twice for the victory taunt": [
        (13733, 38, "getproperty", "_-C25"),
        (13733, 50, "returnvoid", ""),
        (13733, 427, "getproperty", "_-s3D"),
        (13733, 430, "getproperty", "_-22"),
        (13733, 433, "callproperty", "_-f4c, 0"),
        (13733, 645, "getproperty", "_-s3D"),
        (13733, 648, "getproperty", "_-22"),
        (13733, 651, "callproperty", "_-f4c, 0"),
        (13733, 683, "pushstring", "'TauntWin'"),
        (13733, 697, "pushstring", "'TauntSlowClap'"),
    ],
}}

# member name -> every method that references it (any multiname op). A new reference fails the check.
REFERENCES = {ABC_1100: {
    "_-44D": {3336},          # lesson tick: only the scheduler
    "_-O3d": {3336},          # item tick: only the scheduler
    "_-u1O": {3336},
    "_-m4d": {3336},
    "_-N13": {3630},          # lesson setter of _-3I: only lesson start
    "_-m3D": {9748},          # lesson start: only _-l1U._-e26
    "_-96d": {4879},
    "_-u43": {4879},
    "_-Y15": {10946},         # victory taunt: only ScreenScoreboard.OnTickScreen
    "MessageTrigger": {5123, 5129, 5134, 5154, 5820},
}}

# (class, slot, declared type): the receivers named in #3336 / #5809 / #13733.
SLOTS = {ABC_1100: [
    ("_-h3U", "_-O4t", "_-z1C"),
    ("_-h3U", "_-s3D", "_-99"),
    ("_-h3U", "_-3z", "_-E1V"),
    ("_-h3U", "_-w35", "uint"),
    ("_-z1C", "_-3I", "_-S3O"),
    ("_-z1C", "_-c35", "Vector.<MessageTrigger>"),
    ("_-99", "_-22", "Random"),
    ("_-E1V", "_-22", "Random"),
    ("_-y4L", "_-r5y", "Vector.<_-9D>"),
]}


def referencing(abc, names):
    """{name: set of method ids referencing it}, one pass over every body (same rule as abc.callers_of)."""
    targets = {}
    for i, mn in enumerate(abc.multinames):
        if mn and mn[0] != 0x1D and mn[2] and abc.strings[mn[2]] in names:
            targets[i] = abc.strings[mn[2]]
    hits = {n: set() for n in names}
    for body in abc.bodies:
        try:
            ins = abcmod.decode(body["code"])
        except ValueError as exc:
            raise ValueError(f"cannot scan references in method #{body['method']}: {exc}") from exc
        for _, op, args in ins:
            if op in abcmod.MULTINAME_OPS and args and args[0] in targets:
                hits[targets[args[0]]].add(body["method"])
    return hits


def slot_type(abc, cls, slot):
    """Declared type of an instance slot, full name; None if the class or slot is missing."""
    for ci in range(len(abc.instances)):
        if abc.class_name(ci).split("::")[-1] == cls:
            for t in abc.instances[ci]["traits"]:
                if abc.mn_name(t["name"]) == slot and "type" in t:
                    return abc.mn_name(t["type"], full=True)
    return None


def verify(abc, sha):
    """Problems as text lines (empty = every pinned anchor holds). None if the ABC is not pinned."""
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
    want = REFERENCES[sha]
    got = referencing(abc, set(want))
    for name in sorted(want):
        if got[name] != want[name]:
            bad.append(f"references of {name}: want {sorted(want[name])}, found {sorted(got[name])}")
    for cls, slot, typ in SLOTS[sha]:
        found = slot_type(abc, cls, slot)
        if found != typ:
            bad.append(f"slot {cls}.{slot}: want {typ}, found {found}")
    return bad


def counts(sha):
    """(anchors, references, slots) pinned for an ABC."""
    return (sum(len(a) for a in ANCHORS[sha].values()), len(REFERENCES[sha]), len(SLOTS[sha]))
