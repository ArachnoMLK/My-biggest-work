"""Respawn point lists of a level on patch 11.00: what `_-X6R._-x22` #6790 hands to `_-K5c` (respawn_index).

See docs/hit-detection-11.00.md §10. [V] unless marked [H]. A `<Respawn>` is read by `_-139._-L1q` #5288 into a
`_-R19` point (base `_-w3Y`: x `_-W2D`, y `_-U1v`, platform `_-Tt`) at (X + dx, Y + dy), dx / dy being the
parent's offset [H: the moving platform's position], with `Initial` and `ExpandedInit` true only when the
attribute is "TRUE" in any case. `_-a2j._-y1c` #5230 then pushes it to:
- `_-X6Q`: every point;
- `_-o5y`: points without ExpandedInit;
- `_-d2Y`: points with Initial.
A point inside a moving platform also sets `_-V5D` (`_-V4F` #5233); then the lists depend on time (`_-n1u`),
which is not transcribed here. `_-W1y` #5209 sorts the three lists with `_-J5b` #5210 once per tick.
"""
import functools
import re

from .movement import ABC_1100


def _flag(attrs, name):
    m = re.search(r'\b' + name + r'="([^"]*)"', attrs)
    return m is not None and m.group(1).upper() == "TRUE"


def parse_respawns(xml, dx=0.0, dy=0.0):
    """`<Respawn>` points of a LevelDesc in file order: dicts with x, y, initial, expanded, platform (None)."""
    out = []
    for attrs in re.findall(r"<Respawn\b([^>]*)/?>", xml):
        x = float(re.search(r'\bX="([^"]+)"', attrs).group(1)) + dx
        y = float(re.search(r'\bY="([^"]+)"', attrs).group(1)) + dy
        out.append({"x": x, "y": y, "initial": _flag(attrs, "Initial"), "expanded": _flag(attrs, "ExpandedInit"),
                    "platform": None})
    return out


def compare(a, b):
    """`_-J5b`: x, then y, then static points before platform points, then the platform id `_-94r`."""
    d = a["x"] - b["x"]
    if d != 0:
        return -1 if d < 0 else 1
    d = a["y"] - b["y"]
    if d != 0:
        return -1 if d < 0 else 1
    pa, pb = a["platform"] is None, b["platform"] is None
    if pa != pb:
        return -1 if pa else 1
    if pa or a["platform"] == b["platform"]:
        return 0
    return -1 if a["platform"] < b["platform"] else 1


def lists(points):
    """(`_-X6Q`, `_-o5y`, `_-d2Y`) after `_-y1c` and the sort of `_-W1y`. [H] AS3 `Array.sort` is not stable:
    points with equal keys may come out in another order."""
    key = functools.cmp_to_key(compare)
    all_points = sorted(points, key=key)
    return (all_points, [p for p in all_points if not p["expanded"]], [p for p in all_points if p["initial"]])


def candidates(points, n_alive, spawned, f3o=False):
    """`_-x22(t, n_alive, flags)` without moving respawns (`_-V5D` false). `n_alive` is local 5 of `_-K5c`:
    fighters without the `_-e3e` bit `Entity._-o2q` and not in state 7 / 8. `spawned` is flag 1 (`_-44x`).

    The Initial list when spawned and it has at least n_alive points, else the normal list; and when spawned
    without `_-F3O` and that list is shorter than n_alive, every point."""
    all_points, normal, initial = lists(points)
    out = initial if spawned and len(initial) >= n_alive else normal
    if spawned and not f3o and len(out) < n_alive:
        out = all_points
    return out


ANCHORS = {ABC_1100: {
    "_-139._-L1q: <Respawn> -> _-R19(X + dx, Y + dy), Initial / ExpandedInit = attribute.toUpperCase() == 'TRUE'; _-V4F with a platform, else _-y1c": [
        (5288, 9, "pushstring", "'X'"),
        (5288, 26, "add", ""),
        (5288, 32, "pushstring", "'Y'"),
        (5288, 52, "constructprop", "_-R19, 2"),
        (5288, 74, "pushstring", "'Initial'"),
        (5288, 110, "pushstring", "'TRUE'"),
        (5288, 131, "pushstring", "'ExpandedInit'"),
        (5288, 167, "pushstring", "'TRUE'"),
        (5288, 208, "callpropvoid", "_-V4F, 5"),
        (5288, 232, "callpropvoid", "_-y1c, 3"),
    ],
    "_-w3Y.<init>: x _-W2D = arg 1, y _-U1v = arg 2": [
        (233, 49, "initproperty", "_-W2D"),
        (233, 57, "initproperty", "_-U1v"),
    ],
    "_-a2j._-y1c: push to _-X6Q; to _-o5y unless ExpandedInit; to _-d2Y when Initial. _-V4F sets _-V5D": [
        (5230, 6, "getproperty", "_-X6Q"),
        (5230, 11, "callpropvoid", "http://adobe.com/AS3/2006/builtin::push, 1"),
        (5230, 16, "getlocal_3", ""),
        (5230, 26, "getproperty", "_-o5y"),
        (5230, 36, "getlocal_2", ""),
        (5230, 45, "getproperty", "_-d2Y"),
        (5233, 10, "callpropvoid", "_-y1c, 3"),
        (5233, 29, "initproperty", "_-V5D"),
    ],
    "_-a2j._-W1y sorts _-o5y, _-d2Y, _-X6Q with _-J5b; _-J5b: x, y, static first, platform _-94r": [
        (5209, 103, "getproperty", "_-o5y"),
        (5209, 111, "getproperty", "_-J5b"),
        (5209, 119, "callpropvoid", "http://adobe.com/AS3/2006/builtin::sort, 1"),
        (5209, 127, "getproperty", "_-d2Y"),
        (5209, 151, "getproperty", "_-X6Q"),
        (5210, 1, "getproperty", "_-W2D"),
        (5210, 8, "subtract", ""),
        (5210, 22, "getproperty", "_-U1v"),
        (5210, 45, "getproperty", "_-Tt"),
        (5210, 78, "pushbyte", "-1"),
        (5210, 85, "pushbyte", "1"),
        (5210, 107, "getproperty", "_-94r"),
    ],
    "_-X6R._-x22: _-d2Y when flag 1 and len >= n, else _-o5y; _-X6Q when flag 1, not _-F3O and too short (or _-V5D and _-d2Y short); _-V5D -> _-n1u": [
        (6790, 24, "getproperty", "_-d2Y"),
        (6790, 37, "pushbyte", "1"),
        (6790, 40, "bitand", ""),
        (6790, 59, "greaterequals", ""),
        (6790, 77, "getproperty", "_-o5y"),
        (6790, 105, "getproperty", "_-F3O"),
        (6790, 125, "lessthan", ""),
        (6790, 134, "getproperty", "_-V5D"),
        (6790, 156, "getproperty", "_-X6Q"),
        (6790, 183, "callproperty", "_-Y5H, 2"),
        (6790, 200, "callproperty", "_-n1u, 2"),
        (6790, 233, "getproperty", "_-o5y"),
    ],
    "_-X6R._-K5c: a mode point _-H1g._-sZ._-N3 first; n = fighters without _-o2q, not in state 7 / 8; _-x22(t, n, _-nN); empty -> _-I1f._-N4x()": [
        (6778, 50, "getproperty", "_-sZ"),
        (6778, 56, "callproperty", "_-N3, 2"),
        (6778, 107, "callproperty", "_-e35, 0"),
        (6778, 158, "getproperty", "_-o2q"),
        (6778, 176, "pushbyte", "7"),
        (6778, 191, "pushbyte", "8"),
        (6778, 232, "callproperty", "_-nN, 2"),
        (6778, 237, "callproperty", "_-x22, 3"),
        (6778, 302, "callproperty", "_-N4x, 0"),
    ],
}}
