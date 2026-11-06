"""powerTypes cells -> per-step lists on patch 11.00, as `PowerType.static._-A3R` #6483 builds them.

See docs/hit-detection-11.00.md, section 1.2. CastTime is a small language: comma-separated entries
"D", "D@F" or "D:R[@F[-G]]". D is the step duration in ticks, and R adds R extra steps of 0 ticks. Related
columns (BaseDamage, AoERadius, CenterOffset, impulses, ...) give one cell per CastTime entry (or one cell for
all). `PowerType.static._-42F` #6484 expands each cell over the entry's steps: a plain value, "tN" (total N split
evenly), "a|b|c" (alternating), "a~b~c" (linear ranges), or "a&b" (simultaneous hitboxes, which also builds the
frame windows `_-q24`, `_-v5o` #6463). Static evidence only; the values are read from the game files at run time
and are never stored here.
"""
import math
import re

from .movement import ABC_1100, check, listing
from .power_timeline import momentum  # noqa: F401  (`_-qm`, #39; used with fire_x)

_NUM = re.compile(r"\s*[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?")
_INT = re.compile(r"\s*[-+]?\d+")


def parse_float(s):
    """Haxe Std.parseFloat on Flash (= AS3 parseFloat): the leading number, NaN if none."""
    m = _NUM.match(s)
    return float(m.group(0)) if m else math.nan


def parse_int(s):
    """Haxe Std.parseInt: the leading integer (hex "0x.." too), None if none."""
    t = s.strip()
    if re.match(r"[-+]?0[xX][0-9a-fA-F]+", t):
        return int(t, 16)
    m = _INT.match(s)
    return int(m.group(0)) if m else None


def to_int(v):
    """Pushing a Number into a Vector.<int> (ToInt32): truncation; NaN and infinities become 0."""
    if v is None or math.isnan(v) or math.isinf(v):
        return 0
    return int(v)


def cast_steps(cell):
    """CastTime cell -> (durations `_-a2`, entries [(first step, step count)]) (#6483 @10948-11946).

    Empty -> ["0"]. "D:R..." -> D then R steps of 0 ticks; "@F" / "-G" only feed `_-g1x` (not modelled here).
    """
    entries_raw = cell.split(",") if cell else ["0"]
    a2, entries = [], []
    for raw in entries_raw:
        parts = raw.split(":")
        d = parse_int(parts[0])
        r = 0
        if len(parts) > 1:
            r = parse_int(parts[1].split("@")[0])
        else:
            at = parts[0].split("@")
            if len(at) > 1:
                d = parse_int(at[0])
        count = 1 + math.ceil(r / 1)
        entries.append((len(a2), count))
        a2.append(d)
        a2.extend([0] * (count - 1))
    return a2, entries


def expand(cell_list, cast_index, count, as_int=True):
    """`_-42F` #6484 for one CastTime entry: (values for its `count` steps, total, simultaneous groups or None).

    `cell_list` is the column split on ","; one cell applies to every entry. The total is what `_-42F`
    returns (used for `_-D6M` = sum over BaseDamage). Simultaneous ("&") cells return the k values once and
    groups = k (each of the entry's steps then tests the k hitboxes).
    """
    conv = to_int if as_int else (lambda v: v)
    if not cell_list or cell_list == [""]:
        return [0] * count, 0, None
    n = len(cell_list)
    if n > 1 and n <= cast_index:
        return [0] * count, 0, None
    s = cell_list[cast_index] if n > 1 else cell_list[0]
    if "@" in s or ":" in s:
        return [0] * count, 0, None
    if "&" in s:
        if as_int:
            vals = [parse_int(v) or 0 for v in s.split("&")]
        else:
            vals = [parse_float(v) for v in s.split("&")]
        return vals, 0, len(vals)
    if "t" in s:
        total = parse_float(s[1:len(s)])
        per = total / count
        return [conv(per)] * count, total, None
    if "|" in s:
        parts = s.split("|")
        out, total = [], 0
        for i in range(count):
            v = parse_float(parts[i % len(parts)])
            out.append(conv(v))
            total += v
        return out, total, None
    if "~" in s:
        parts = s.split("~")
        if count == 1:
            v = parse_float(parts[0])
            return [conv(v)], v, None
        k = len(parts) - 1
        span = (count - 1) / k
        out, total = [], 0
        for i in range(count):
            sec = int(i / count * k)
            lo, hi = int(sec * span), int((sec + 1) * span)
            a, b = parse_float(parts[sec]), parse_float(parts[sec + 1])
            v = (i - lo) * ((b - a) / (hi - lo)) + a
            out.append(conv(v))
            total += v
        return out, total, None
    v = parse_float(s)
    return [conv(v)] * count, count * v, None


COLUMNS = ("VariableImpulse", "FixedImpulse", "AoERadiusX", "AoERadiusY", "CenterOffsetX", "CenterOffsetY",
           "BaseDamage", "ImpulseOffsetX", "ImpulseOffsetY", "FixedStunTime")
# FireImpulseX -> `_-84C`, FireImpulseY -> `_-ol` (#6483 @5244-5344: split ',', then `_-a3P(cells, '!',
# '2147483647')`, i.e. "!" = unset), expanded per step by `_-42F` like the columns above (@12022-12068).
FIRE_COLUMNS = ("FireImpulseX", "FireImpulseY", "FireImpulseMaxX")   # FireImpulseMaxX -> `_-L3` (@5183-5234)
UNSET = 2147483647


def fire_x(base, max_v, l27, v2f, qm, charge=1.0):
    """`_-l4X._-a5A` #47 @204-392: the FireImpulseX of a step before the facing sign. With `_-l27` (a
    FireImpulseMaxX or ImpulseOffsetMaxX cell) and a FireImpulseMaxX list: without ImpulseMaxOnDCOnly (`_-V2F`)
    base + (max - base) x `_-qm`, with it max once `_-qm` >= 1; then x the charge factor (1 + 0.5 x `_-a6i` /
    `_-I6c` under `_-V3`, 1 otherwise). None (unset) stays None."""
    if base is None or base == UNSET:
        return None
    v = base
    if l27 and max_v is not None:
        if not v2f:
            v = (max_v - v) * qm + v
        elif qm >= 1:
            v = max_v
    return v * charge


def power_steps(row):
    """One powerTypes row (dict) -> {"CastTime": durations, column: per-step list, "q24": windows or None,
    "D6M": total BaseDamage}. AoERadiusY falls back to AoERadiusX's cells when empty (#6483 @10677-10708).
    Values go into int vectors (parseInt-style truncation of the expanded value) [V shape]."""
    a2, entries = cast_steps(row.get("CastTime", ""))
    cells = {c: (row.get(c) or "").split(",") if row.get(c) else [] for c in COLUMNS}
    for c in FIRE_COLUMNS:
        cells[c] = [s.replace("!", str(UNSET)) for s in row.get(c).split(",")] if row.get(c) else []
    if cells["AoERadiusX"] and not cells["AoERadiusY"]:
        cells["AoERadiusY"] = cells["AoERadiusX"]
    out = {"CastTime": a2, "q24": None, "D6M": 0}
    lists = {c: [] for c in COLUMNS + FIRE_COLUMNS}
    windows, defaults = {}, {}
    for idx, (first, count) in enumerate(entries):
        for c in COLUMNS + FIRE_COLUMNS:
            start = len(lists[c])
            vals, total, groups = expand(cells[c], idx, count)
            lists[c].extend(vals)
            if groups is not None and c not in FIRE_COLUMNS:
                for step in range(first, first + count):
                    windows.setdefault(step, (start, groups))
            if c == "BaseDamage":
                out["D6M"] += total
        # @12605-12709: other steps get a window of 1 at their place in the AoERadiusX list (`_-a4C`)
        end = len(lists["AoERadiusX"])
        for i in range(count):
            defaults[first + i] = (end - count + i, 1)
    out.update(lists)
    if windows:
        q24 = [0] * len(a2)
        for step in range(len(a2)):
            start, k = windows.get(step, defaults[step])
            q24[step] = (k << 16) | start
        out["q24"] = q24
    return out


def recover_times(row):
    """(FixedRecoverTime `_-f5c`, RecoverTime `_-Sp`) as `PowerType._-A3R` #6483 reads them (@5529-5635, @8327-8435):
    the cell is split on '@' and the first part goes through Std.parseInt (None -> 0 here [H: the null coerced to
    the int field]); the part after '@' is only an animation frame for `_-g1x` (@12723-12821), not a duration."""
    out = []
    for col in ("FixedRecoverTime", "RecoverTime"):
        cell = row.get(col) or ""
        v = parse_int(cell.split("@")[0]) if cell else None
        out.append(v or 0)
    return tuple(out)


ANCHORS = {ABC_1100: {
    "_-A3R FixedRecoverTime / RecoverTime: split '@', _-F5E.parseInt(part 0) -> _-f5c / _-Sp; part 1 -> local 25 -> _-g1x frame": [
        (6483, 5529, "pushstring", "'FixedRecoverTime'"),
        (6483, 5547, "pushstring", "'@'"),
        (6483, 5580, "callproperty", "parseInt, 1"),
        (6483, 5586, "initproperty", "_-f5c"),
        (6483, 8327, "pushstring", "'RecoverTime'"),
        (6483, 8346, "pushstring", "'@'"),
        (6483, 8379, "callproperty", "parseInt, 1"),
        (6483, 8385, "initproperty", "_-Sp"),
        (6483, 8433, "setlocal", "25"),
        (6483, 12739, "pushstring", "'end'"),
        (6483, 12821, "callpropvoid", "_-g1x, 2"),
    ],
    "_-A3R CastTime: split ',', D:R@F-G or D@F, a2.push(D) + R extra 0 steps; empty -> '0'": [
        (6483, 2368, "pushstring", "','"),
        (6483, 10959, "pushstring", "'0'"),
        (6483, 11339, "pushstring", "':'"),
        (6483, 11418, "pushstring", "'@'"),
        (6483, 11483, "pushstring", "'-'"),
        (6483, 11384, "pushbyte", "1"),
        (6483, 11389, "pushfalse", ""),
        (6483, 11799, "callproperty", "ceil, 1"),
        (6483, 11816, "callpropvoid", "http://adobe.com/AS3/2006/builtin::push, 1"),
        (6483, 12119, "callpropvoid", "_-42F, 6"),
        (6483, 12381, "callproperty", "_-42F, 6"),
        (6483, 12388, "initproperty", "_-D6M"),
        (6483, 12686, "callpropvoid", "_-v5o, 4"),
    ],
    "FireImpulseMaxX: _-l27 + _-L3 (_-A3R); _-qm = min(|vx| / 60, 1) toward the facing (#39); _-a5A lerp by _-qm, or max under _-V2F when _-qm >= 1": [
        (6483, 5183, "pushstring", "'FireImpulseMaxX'"),
        (6483, 5193, "initproperty", "_-l27"),
        (6483, 6647, "pushstring", "'ImpulseMaxOnDCOnly'"),
        (6483, 6664, "initproperty", "_-V2F"),
        (6483, 6673, "pushstring", "'ImpulseOffsetMaxX'"),
        (6483, 10791, "initproperty", "_-L3"),
        (6483, 12086, "getproperty", "_-L3"),
        (6483, 12094, "callpropvoid", "_-42F, 6"),
        (39, 784, "lessthan", ""),
        (39, 830, "callproperty", "abs, 1"),
        (39, 853, "pushdouble", "60.0"),
        (39, 868, "pushbyte", "1"),
        (47, 74, "pushdouble", "0.5"),
        (47, 221, "getproperty", "_-l27"),
        (47, 237, "getproperty", "_-L3"),
        (47, 335, "getproperty", "_-V2F"),
        (47, 352, "getproperty", "_-qm"),
        (47, 376, "pushbyte", "1"),
        (47, 390, "multiply", ""),
    ],
    "_-A3R FireImpulseX / Y: split ',', '!' -> '2147483647' (_-a3P), then _-42F per step into _-84C / _-ol": [
        (6483, 5244, "pushstring", "'FireImpulseX'"),
        (6483, 5283, "pushstring", "'!'"),
        (6483, 5285, "pushstring", "'2147483647'"),
        (6483, 5289, "callpropvoid", "_-a3P, 3"),
        (6483, 5299, "pushstring", "'FireImpulseY'"),
        (6483, 5344, "callpropvoid", "_-a3P, 3"),
        (6483, 10735, "initproperty", "_-84C"),
        (6483, 10763, "initproperty", "_-ol"),
        (6483, 12036, "getproperty", "_-84C"),
        (6483, 12043, "callpropvoid", "_-42F, 6"),
        (6483, 12061, "getproperty", "_-ol"),
        (6483, 12068, "callpropvoid", "_-42F, 6"),
    ],
    "_-42F: '&' simultaneous (v5o), 't' total / n, '|' alternating, '~' ranges, plain value; _-965 fill; v5o packs (k << 16) | first": [
        (6484, 166, "callpropvoid", "_-965, 4"),
        (6484, 432, "pushstring", "'t'"),
        (6484, 444, "pushstring", "'|'"),
        (6484, 457, "pushstring", "'~'"),
        (6484, 470, "pushstring", "'&'"),
        (6484, 846, "callpropvoid", "_-v5o, 3"),
        (6484, 1185, "divide", ""),
        (6484, 1373, "modulo", ""),
        (6484, 1833, "divide", ""),
        (6484, 2079, "divide", ""),
        (6484, 2177, "multiply", ""),
        (6485, 47, "callpropvoid", "http://adobe.com/AS3/2006/builtin::push, 1"),
        (6463, 92, "pushbyte", "16"),
        (6463, 95, "lshift", ""),
        (6463, 98, "bitor", ""),
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
