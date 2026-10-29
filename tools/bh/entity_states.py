"""Fighter state dispatch on patch 11.00: `Entity._-k5H` #2991 switches on `_-65w` every tick (step 5).

See docs/hit-detection-11.00.md, section 10. Each state's handler is [V]; the state names are [H], inferred
from the methods that set each value (`abc-find --member _-65w`). Static evidence only.
"""
from .movement import ABC_1100, check, listing

# value: (name [H], handler in #2991, setters)
STATES = {
    0: ("in play", "power update `_-Kc._-25(t)`, then movement `_-8i` (or `_-763` in the `_-m1t` state, or pinned "
                   "to `_-aB` / `_-v1Z` in the `_-J5I` state); replay recording afterwards", "many (`_-048`, `_-hq`, ...)"),
    2: ("not spawned yet", "`_-44x` set; nothing else", "`Entity.<init>`"),
    3: ("knocked out / waiting", "power update only, `_-f5u = 0`, `_-P4K` set", "`Entity._-eR`, `_-X6R._-U6W`, ..."),
    4: ("held still", "same as 3", "`SpawnBot._-m1O`, `_-y3M._-n3w`"),
    5: ("in play, timed", "as 0, after a 2500 ms timer `_-f5u` (or lava ground, or other conditions) returns to 0",
        "`SpawnBot._-m1O`, `_-W6p._-Y2v`"),
    6: ("held by a power (grab)", "power update; back to 0 and `mHeldByPower = null` when the holder's power "
                                 "ends, or through `_-j9` (Uninterruptable `_-C5G` checked)", "`Entity._-j4e`"),
    7: ("entering", "flags `_-e3e = _-e3c`, `_-k5S` reset, `_-81Z`, `_-2c`, power update, `_-f5u = 0`",
        "`Entity._-Y6o`, `_-I4N`, `_-y3M`, ..."),
    8: ("entering (variant)", "as 7, with `_-lV` instead of `_-164`", "`Entity._-S1D`"),
    9: ("respawning", "`_-44x` set, `_-e3e = _-e3c`, `_-W1R.Respawn(...)`, `_-q4u._-b3v(.., 7)`", "`Entity._-220`"),
}
UNHANDLED = (1,)   # the switch sends 1 (and anything above 9) to the "Unaccounted-for entity state" message


def handler(state):
    """(name, handler) of a `_-65w` value, or None for an unhandled one."""
    if state in STATES:
        return STATES[state][:2]
    return None


ANCHORS = {ABC_1100: {
    "_-k5H: _-1L(t) (inputs) then lookupswitch on _-65w; 0/5 -> movement, 3/4 -> _-25 only, 6 held, 7/8 enter, 9 respawn": [
        (2991, 75, "callpropvoid", "_-1L, 1"),
        (2991, 82, "getproperty", "_-65w"),
        (2991, 124, "pushstring", "'Unaccounted-for entity state '"),
        (2991, 214, "callpropvoid", "_-25, 1"),
        (2991, 246, "pushbyte", "5"),
        (2991, 274, "pushuint", "2500"),
        (2991, 522, "callpropvoid", "_-25, 1"),
        (2991, 585, "callpropvoid", "_-8i, 1"),
        (2991, 620, "callpropvoid", "_-763, 1"),
        (2991, 1300, "callpropvoid", "_-25, 1"),
        (2991, 1344, "initproperty", "mHeldByPower"),
        (2991, 1447, "pushbyte", "7"),
        (2991, 1707, "callpropvoid", "Respawn, 2"),
        (2991, 1741, "callpropvoid", "_-b3v, 2"),
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
