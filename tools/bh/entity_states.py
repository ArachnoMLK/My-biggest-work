"""Fighter state dispatch on patch 11.00: `Entity._-k5H` #2991 switches on `_-65w` every tick (step 5).

See docs/hit-detection-11.00.md, section 10. Each state's handler is [V]; the state names are [H], inferred
from the methods that set each value (`abc-find --member _-65w`). Static evidence only.
"""
import math

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
    7: ("eliminated", "once 1500 ms have passed since `_-164` (or `_-s3D._-zv() <= 1`), the bit `Entity._-e3c` is "
                    "added to `_-e3e`; `_-k5S` reset, `_-81Z`, `_-2c`, power update, `_-f5u = 0`, `_-P4K = false`; "
                    "the state itself is left by other code", "`Entity._-Y6o`, `_-I4N`, `_-y3M`, ..."),
    8: ("eliminated (variant)", "as 7, timed from `_-lV` instead of `_-164`", "`Entity._-S1D`"),
    9: ("respawning", "`_-44x` set, the bit `Entity._-e3c` cleared from `_-e3e`, `_-W1R.Respawn(t, this)`, "
                      "`_-q4u._-b3v(t, 7)`", "`Entity._-220`"),
}
UNHANDLED = (1,)   # the switch sends 1 (and anything above 9) to the "Unaccounted-for entity state" message


# How an input starts a power [V shape]: the input consumer `_-i4Z._-rU` / `_-I35` (PR #28) calls
# `_-F5N._-C5S` (attack slot -> power through `_-42t`; slot 9 has extra checks), `_-A3Q` or `_-V5I` (throw the
# held item: `_-3z._-q1S` spawns it at the feet). They end in `_-F5N._-J5R`, which returns unless `_-O5u` allows
# it (not while the running power has `_-82f`; `_-H1V` may swap the power for the weapon through `_-M1g` /
# `_-E2S` / `_-w3H`), ends the running power (`_-VY`) and sets `_-o3I = new _-l4X(...)`.
# State transitions found so far [V call edges]: a KO commit sets 3 (`Entity._-eR`, ko-11.00.md, PR #25);
# the respawn reset `_-X6R._-U6W` (#6787, which also resets the damage `_-W22`) calls `Entity._-Y6o` (#3122),
# which sets 7 (eliminated: `_-s3m._-a1k` #3948 @225-241 exports 'Eliminated' = (`_-65w` == 7)); `_-X6R.Respawn` (#6784) calls `Entity._-hq` (#2996), which sets 0; `_-d2C._-85Y`
# calls `Entity._-220` (#3000), which sets 9. State 7 is final for the match; a normal respawn places the fighter through `_-k5S._-P3o` (SpawnBot._-P3o sets 0).
# Match start, `_-X6R._-b3x` #6777 (tick step 4, `_-W1R._-b3x(t)`): on the first tick with t >= `_-n4k` + 256 ms
# (flag `_-C3h`), eligible fighters get state 3 and are passed to `Respawn` (eliminated = false: -> `_-U6W` -> 3 -> drone, spawn_bot.py), and the replay
# generator R (`_-s3D._-22`) is drawn twice: `_-G5X[i] = R._-f4c() % n` for i = 0, 1, with n = the number of
# `_-I1f._-o5y` entries, or 37 when there are none (@904-1002). These two draws are not in prng-order-11.00.md.
MATCH_START_MS = 256
MATCH_START_R_DRAWS = 2



def respawn_index(counters, team, n_points, team_mode):
    """`_-X6R._-K5c` #6778 @315-499: index of the respawn point for a fighter, advancing the counters.

    `counters` is `_-G5X` (two entries, seeded by the two match-start draws). In team mode (`_-O3P()`), teams
    1 and 2 use counters 0 and 1 and the first / second half of the point list; otherwise counter 0 and the
    whole list. Returns the index into the candidate list (from `_-x22`), mutating `counters`.
    """
    c = (team - 1) if team_mode and team <= 2 else 0
    counters[c] += 1
    k = counters[c]
    if team_mode:
        return k % (n_points >> 1) + (0 if c == 0 else math.ceil(n_points / 2))
    return k % n_points


TRANSITIONS = {(None, 3): "Entity._-eR (KO commit)", (None, 7): "_-X6R._-U6W(eliminated) -> Entity._-Y6o", (3, 4): "SpawnBot._-m1O (drop starts)",
               (4, 0): "SpawnBot._-m1O (let go)", (4, 5): "SpawnBot._-m1O (let go, other case)", (3, 0): "SpawnBot._-P3o (instant)",
               (None, 0): "_-X6R.Respawn -> Entity._-hq", (None, 9): "_-d2C._-85Y -> Entity._-220"}

POWER_START = ("_-i4Z._-rU / _-I35", "_-F5N._-C5S / _-A3Q / _-V5I", "_-F5N._-J5R", "_-O5u", "new _-l4X")


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
    "Power start: _-i4Z._-rU / _-I35 -> _-F5N._-C5S (slot -> _-42t) / _-A3Q / _-V5I (throw) -> _-J5R: _-O5u check, old power _-VY, new _-l4X": [
        (1700, 55, "callproperty", "_-42t, 3"),
        (1700, 81, "pushbyte", "9"),
        (1699, 7, "callproperty", "_-O5u, 2"),
        (1699, 43, "callpropvoid", "_-VY, 0"),
        (1699, 79, "constructprop", "_-l4X, 7"),
        (1699, 83, "initproperty", "_-o3I"),
        (1744, 39, "getproperty", "_-82f"),
        (1744, 54, "callproperty", "_-H1V, 1"),
        (1744, 87, "getproperty", "_-M1g"),
        (1744, 125, "getproperty", "_-E2S"),
        (1744, 165, "getproperty", "_-w3H"),
        (1750, 118, "callpropvoid", "_-q1S, 5"),
    ],
    "States 7/8: add the _-e3c bit after 1500 ms or zv() <= 1; state 9: clear it, Respawn": [
        (2991, 1489, "getproperty", "_-e3c"),
        (2991, 1512, "callproperty", "_-zv, 0"),
        (2991, 1529, "pushuint", "1500"),
        (2991, 1558, "bitor", ""),
        (2991, 1691, "bitnot", ""),
        (2991, 1692, "bitand", ""),
    ],
    "Transitions: _-U6W -> _-Y6o sets 7; Respawn -> _-hq sets 0": [
        (6787, 34, "callpropvoid", "_-Y6o, 1"),
        (3122, 5, "pushbyte", "7"),
        (3122, 8, "initproperty", "_-65w"),
        (6784, 180, "callpropvoid", "_-hq, 0"),
        (2996, 27, "initproperty", "_-65w"),
    ],
    "_-b6D: in state 7 (8) true until _-164 (_-a2O) + 4000 ms; _-X1J releases a grab (6 -> 0)": [
        (3015, 92, "getproperty", "_-164"),
        (3015, 96, "pushuint", "4000"),
        (3015, 117, "getproperty", "_-a2O"),
        (3036, 59, "pushbyte", "6"),
        (3036, 73, "initproperty", "_-65w"),
    ],
    "Match start in _-X6R._-b3x: once at t >= n4k + 256 (_-C3h): state 3 + Respawn, two R draws % len(_-o5y) (or 37)": [
        (6777, 63, "pushuint", "256"),
        (6777, 72, "getproperty", "_-n4k"),
        (6777, 149, "initproperty", "_-C3h"),
        (6777, 408, "pushbyte", "3"),
        (6777, 886, "callpropvoid", "Respawn, 2"),
        (6777, 919, "getproperty", "_-o5y"),
        (6777, 940, "pushbyte", "37"),
        (6777, 981, "getproperty", "_-22"),
        (6777, 984, "callproperty", "_-f4c, 0"),
        (6777, 991, "modulo", ""),
        (6777, 998, "pushbyte", "2"),
        (6784, 255, "callpropvoid", "_-U6W, 3"),
    ],
    "Respawn point choice _-K5c: counter _-G5X[team] += 1, index % n (team mode: % (n >> 1) + ceil(n / 2) for team 2)": [
        (6778, 237, "callproperty", "_-x22, 3"),
        (6778, 331, "callproperty", "_-O3P, 0"),
        (6778, 355, "getproperty", "_-25G"),
        (6778, 388, "getproperty", "_-G5X"),
        (6778, 411, "increment", ""),
        (6778, 435, "pushbyte", "1"),
        (6778, 437, "urshift", ""),
        (6778, 464, "callproperty", "ceil, 1"),
        (6778, 482, "modulo", ""),
        (6778, 499, "callpropvoid", "_-P3o, 2"),
    ],
    "State 7 is 'Eliminated' (_-s3m._-a1k); respawn placement _-k5S._-P3o -> SpawnBot._-P3o sets 0": [
        (3948, 227, "pushstring", "'Eliminated'"),
        (3948, 236, "pushbyte", "7"),
        (6778, 499, "callpropvoid", "_-P3o, 2"),
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
