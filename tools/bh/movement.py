"""Pinned bytecode anchors for the vertical movement chain (Q4).

Each anchor is (method id, offset, opname, operand text as printed by `abc-disasm`). They only hold for
the ABC whose SHA-256 is the key of ANCHORS: other patches renumber methods and rename members.
See docs/movement-11.00.md for what each anchor means.
"""
from . import abc as abcmod

ABC_1100 = "7d308423eaebcc82dfdda4ecc0e57d3abe78569534023aa7f9d776f626356db9"

ANCHORS = {ABC_1100: [
    # script61.<init>: global config class _-z2k (tick length and per-tick scale)
    (1227, 248, "pushbyte", "16"),
    (1227, 250, "initproperty", "_-x5b"),
    (1227, 256, "pushdouble", "0.384"),
    (1227, 259, "initproperty", "_-Vj"),
    # Entity.<init>: gravity field
    (2887, 133, "pushdouble", "3.75"),
    (2887, 135, "initproperty", "_-84Q"),
    # _-i4Z._-51o: jump bit 16 of the input timeline -> owner.Jump(t)
    (6313, 1222, "pushbyte", "16"),
    (6313, 3445, "callpropvoid", "Jump, 1"),
    # Entity.Jump: dash window, multiplier, grounded and dash impulses, vy -= impulse
    (3052, 80, "getproperty", "_-26T"),
    (3052, 84, "pushuint", "160"),
    (3052, 579, "pushdouble", "0.86"),
    (3052, 586, "pushdouble", "1.0"),
    (3052, 643, "pushdouble", "57.0"),
    (3052, 647, "multiply", ""),
    (3052, 698, "pushdouble", "170.0"),
    (3052, 873, "pushstring", "'dash.Jump'"),
    (3052, 986, "getproperty", "_-P5S"),
    (3052, 989, "pushbyte", "0"),
    (3052, 1020, "getproperty", "_-A4A"),
    (3052, 1029, "getlocal", "8"),
    (3052, 1031, "subtract", ""),
    (3052, 1048, "callpropvoid", "_-N5C::_-E1t, 2"),
    # Entity._-8i: fall cap 70 / 85 (85 when Drop bit 2 is held), then _-P5S += gravity * 0.384
    (2984, 5097, "pushbyte", "2"),
    (2984, 5127, "pushdouble", "70.0"),
    (2984, 5132, "pushdouble", "85.0"),
    (2984, 5294, "getlocal", "23"),
    (2984, 5340, "getproperty", "_-84Q"),
    (2984, 5346, "getproperty", "_-Vj"),
    (2984, 5350, "multiply", ""),
    (2984, 5351, "add", ""),
    (2984, 5353, "callpropvoid", "_-N5C::_-E1t, 2"),
]}


def listing(abc, method_id):
    """{offset: (opname, operand text)} for one method, same text as `abc-disasm` (branches excluded)."""
    bi = abc.body_of.get(method_id)
    if bi is None:
        return {}
    return {off: (name, abcmod.operand_text(abc, name, args)) for off, name, args in abcmod.decode(abc.bodies[bi]["code"])}


def check(anchors, lister):
    """Return the anchors that do not match, as (anchor, found) pairs. `lister(method_id)` -> listing dict."""
    cache, bad = {}, []
    for anchor in anchors:
        m, off, op, text = anchor
        if m not in cache:
            cache[m] = lister(m)
        found = cache[m].get(off)
        if found != (op, text):
            bad.append((anchor, found))
    return bad
