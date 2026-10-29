"""Damage and knockback force of a hit on patch 11.00: `_-26u._-76s` #1675 and `_-26u._-u1x` #1674.

See docs/knockback-11.00.md. The functions transcribe the arithmetic in bytecode order (AS3 Numbers are
IEEE doubles, like Python floats); field names are the obfuscated ones, their meanings are [H].
Anchors are (method id, offset, opname, operand text as printed by `abc-disasm`); branch operands are
relative. Static evidence only; nothing is executed.
"""
from .movement import ABC_1100, check, listing

# _-26u._-M3e, script92.<init> #1679 @59-131: multiplier by stat difference, index 11 + a - b
STAT_TABLE = (0.8349, 0.8384, 0.8437, 0.851, 0.8604, 0.8719, 0.8857, 0.9022, 0.9215, 0.9439, 0.9699, 1,
              1.031, 1.0594, 1.0852, 1.1084, 1.129, 1.1469, 1.1623, 1.1751, 1.1853, 1.1928, 1.1978)
STAT_CENTER = 11


def stat_multiplier(attacker_p3i, victim_92e):
    """`_-26u._-M3e[11 + attacker._-P3I - victim._-92e]` (#1675 @592-640). Out of range raises.

    In AS3 an index outside the array reads `undefined`, which becomes NaN; no clamp is in the code.
    """
    i = STAT_CENTER + attacker_p3i - victim_92e
    if not 0 <= i < len(STAT_TABLE):
        raise IndexError(f"stat index {i} outside _-M3e")
    return STAT_TABLE[i]


def hit_damage(base, charge, p538, n_r, l_a, o3t, attacker_45j=None, stat=1.0, victim_w22=0):
    """Damage of a hit, `local 28` of #1675 @480-704, before the match setting of @1152-1174.

    base = the power's damage entry; extra = charge * `_-538`, and when non-zero extra - 50 * `_-538`,
    at least 1; then * weapon `_-nR` * victim `_-lA` / `_-o3t`; * attacker `_-45J` (when the attacker is
    an Entity); * `stat` (the `_-M3e` entry, see stat_multiplier; skipped when 0); a negative result is
    kept above -victim `_-W22` (truncated to int).
    """
    d = base
    e = charge * p538
    if e != 0:
        e = e - 50 * p538
        if e < 1.0:
            e = 1.0
    d = d + e
    d = d * (n_r * l_a / o3t)
    if attacker_45j is not None:
        d = d * attacker_45j
    if stat != 0:
        d = d * stat
    if d < 0:
        floor = int(-1 * victim_w22)
        if not floor < d:
            d = float(floor)
    return d


def charged_scale(held, i6c):
    """`1 + held / _-I6c * 0.25` (#1675 @1100-1116), applied to damage and to the fixed force."""
    return 1 + held / i6c * 0.25


def knockback_force(force, damage, victim_w22, victim_w3f, attacker_g4s, victim_13t, victim_p1r,
                    attacker_z4f=1.0, same_team=False, mode5=False):
    """`_-26u._-u1x(power, attacker, victim, force, damage)` #1674: the knockback magnitude.

    d = (victim `_-W22` + victim `_-w3F` + damage) / 100, or (50 + `_-w3F` + damage) / 100 when the
    scoring rule `_-U6g == 5`; force * 0.75 against a team mate; then
    max(force * (d + d * (d / 2)) * attacker `_-Kc._-G4s` * `_-z4f` / victim `_-Kc._-13t` - victim `_-P1r`, 0).
    `attacker_z4f` is used only when the attacker is an Entity and the power is not `_-Rc` / `_-d6x`.
    """
    if mode5:
        d = (50 + victim_w3f + damage) / 100
    else:
        d = (victim_w22 + victim_w3f + damage) / 100
    if same_team:
        force = force * 0.75
    f = force * (d + d * (d / 2)) * attacker_g4s * attacker_z4f / victim_13t
    return max(f - victim_p1r, 0)


ANCHORS = {ABC_1100: {
    "_-u1x: z4f factor, d = (W22 + w3F + damage) / 100 (50 instead of W22 when _-U6g == 5)": [
        (1674, 85, "getproperty", "_-z4f"),
        (1674, 92, "pushdouble", "1.0"),
        (1674, 111, "getproperty", "_-U6g"),
        (1674, 114, "pushbyte", "5"),
        (1674, 123, "getproperty", "_-W22"),
        (1674, 127, "getproperty", "_-w3F"),
        (1674, 132, "getlocal", "5"),
        (1674, 136, "pushbyte", "100"),
        (1674, 138, "divide", ""),
        (1674, 146, "pushbyte", "50"),
        (1674, 158, "pushbyte", "100"),
    ],
    "_-u1x: team mate x 0.75, F = force * (d + d * (d / 2)) * G4s * z4f / 13t, max(F - P1r, 0)": [
        (1674, 179, "getproperty", "_-25G"),
        (1674, 201, "pushdouble", "0.75"),
        (1674, 210, "getlocal", "9"),
        (1674, 216, "pushbyte", "2"),
        (1674, 218, "divide", ""),
        (1674, 219, "multiply", ""),
        (1674, 220, "add", ""),
        (1674, 222, "multiply", ""),
        (1674, 227, "getproperty", "_-G4s"),
        (1674, 239, "getproperty", "_-13t"),
        (1674, 242, "divide", ""),
        (1674, 253, "getproperty", "_-P1r"),
        (1674, 260, "callproperty", "max, 2"),
        (1674, 265, "returnvalue", ""),
    ],
    "_-76s damage: base + charge extra, * nR * lA / o3t, * 45J, * _-M3e[11 + P3I - 92e], floor at -W22": [
        (1675, 488, "setlocal", "28"),
        (1675, 493, "getproperty", "_-538"),
        (1675, 510, "pushbyte", "50"),
        (1675, 523, "pushdouble", "1.0"),
        (1675, 549, "getproperty", "_-nR"),
        (1675, 554, "getproperty", "_-lA"),
        (1675, 560, "getproperty", "_-o3t"),
        (1675, 584, "getproperty", "_-45J"),
        (1675, 592, "pushbyte", "11"),
        (1675, 608, "getproperty", "_-P3I"),
        (1675, 622, "getproperty", "_-92e"),
        (1675, 634, "getproperty", "_-M3e"),
        (1675, 646, "setlocal", "31"),
        (1675, 660, "multiply", ""),
        (1675, 672, "pushbyte", "-1"),
        (1675, 676, "getproperty", "_-W22"),
    ],
    "_-76s force: W1a[i] (+ _-4r), variable part * w4x * 0.5, charge 1 + held / I6c * 0.25, damage * _-04o / 100, then _-u1x": [
        (1675, 921, "getproperty", "_-W1a"),
        (1675, 943, "getproperty", "_-4r"),
        (1675, 952, "getproperty", "_-C7"),
        (1675, 1038, "getproperty", "_-w4x"),
        (1675, 1046, "pushdouble", "0.5"),
        (1675, 1054, "getproperty", "_-h5f"),
        (1675, 1078, "getproperty", "_-w46"),
        (1675, 1105, "getproperty", "_-I6c"),
        (1675, 1109, "pushdouble", "0.25"),
        (1675, 1136, "pushdouble", "1.25"),
        (1675, 1164, "getproperty", "_-04o"),
        (1675, 1168, "pushdouble", "100.0"),
        (1675, 1188, "add", ""),
        (1675, 1192, "callproperty", "_-u1x, 5"),
    ],
    "_-26u._-M3e: 23 stat multipliers, 1 at index 11": [
        (1679, 63, "pushdouble", "0.8349"),
        (1679, 91, "pushdouble", "0.9699"),
        (1679, 94, "pushbyte", "1"),
        (1679, 96, "pushdouble", "1.031"),
        (1679, 126, "pushdouble", "1.1978"),
        (1679, 129, "newarray", "23"),
        (1679, 131, "initproperty", "_-M3e"),
    ],
    "the hit _-91G gets the knockback point; it is written into the one-tick impulses _-84 / _-A4A": [
        (1675, 2205, "callproperty", "_-91G, 11"),
        (1677, 932, "getproperty", "_-84"),
        (1677, 951, "getproperty", "_-A4A"),
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
