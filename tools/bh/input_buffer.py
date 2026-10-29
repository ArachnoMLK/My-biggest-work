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
