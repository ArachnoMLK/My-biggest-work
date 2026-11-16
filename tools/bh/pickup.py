"""Which item a pick-up press takes on patch 11.00: `_-F5N._-LY` #1701 -> `_-F5N._-N5R` #1733.

Static reading of the bytecode (abc 7d308423...). [V] unless marked [H]; anchors in ANCHORS.

`_-LY(t, a2)`: no owner -> false; with a2, `_-I2Q` = t when `_-I2Q` + 240 < t; `IsMoveLocked(t)` or a running power
`_-o3I` -> false; then `_-N5R(t, a2, a2 && _-I2Q + 240 > t)`. [H] a2 is "no QuickAttack press" (entity_states.py).

`_-N5R(t, a2, a3)`:
1. candidates: `_-E1V._-91X(t, owner, x, y, 150, 150, 2, out)` with the fighter point (`_-Z2G._-M43`, `_-E3d`):
   the live items `_-O1L` whose box (centre `_-p5a()` / `_-d5F()` = `_-S1I` / `_-f66`, half sizes ItemType Width
   `_-w2s` / 2 and Height `_-S2O` / 2, + 100 each in item state 3) overlaps [x - 150, x + 150] x [y - 150, y + 150]
   (#4914 @40-358), not taken (`_-Jl`), and with mask bit 2 `_-86Q(t)` true (#15243: states 0, 1, 2, 4 unless
   `_-72T` and `_-f4i` without AlwaysArmed, or taken; then not DisablePickup `_-p5R`; state 3: a WeaponCrate,
   or `_-b37` + `_-E4u` <= t; states 5-9 never). No candidate -> null.
2. without a2: is an opponent near? `_-G2C` over a 150 x 150 box ahead of the fighter: offset 150 x w with
   w = 0.4, + 0.7 with `_-81n()`, else + 0.6 with input bit 2; negated when `_-141()` (#1733 @234-507).
3. each candidate gets a priority (#1733 @560-1020), skipped when: claimed by another fighter (`_-x5F._-b4Y` not 0
   and not this one); the game-mode test `_-25z` refuses; state 3 and not `_-u4s(item)`; state 1 (thrown) and a3;
   a Weapon (`_-G3X`) that is not Spawnable (`_-r5R`) and is neither of the legend's base weapons; the owner bit
   of `_-M5k` is set; dropped by this fighter (`_-r5B`) less than 64 ms ago (`_-O13`). Priority: state 1 -> 2,
   state 3 -> 4, a weapon claimed by this fighter -> 5, else ItemType `_-G35` (#4974 @3610-3790: name containing
   Brawlball 1, WaterBomb 3, BouncyBomb 7, CTFFlagRed / Blue 1, OddBall 1, WeaponCrate 6, others 8). Priority >= 6
   is skipped when an opponent is near (step 2).
4. the lowest priority wins; on equal priority the smaller squared distance `Entity._-u` #3126
   ((x - item x)^2 + (y - item y)^2), the first one on equal distance.
"""
from .movement import ABC_1100

QUERY_HALF = 150.0
STATE3_PAD = 100.0
DROP_GUARD_MS = 64
REGRAB_MS = 240


def type_priority(it):
    """`ItemType._-G35` as `ItemType.static._-z2u` #4974 @3610-3790 sets it."""
    name = it.get("name") or ""
    if "Brawlball" in name:
        return 1
    if name == "WaterBomb":
        return 3
    if name == "BouncyBomb":
        return 7
    if name in ("CTFFlagRed", "CTFFlagBlue", "OddBall"):
        return 1
    if it.get("E2E"):
        return 6
    return 8


def pickable(item, t):
    """`_-p5k._-86Q` #15243. item: {"state", "type", "taken", "x72T", "f4i", "b37"}; `_-E4u` as "e4u"."""
    it = item.get("type")
    if it is None:
        return False
    s = item.get("state", 0)
    if s in (0, 1, 2, 4):
        if (item.get("x72T") and item.get("f4i") and not it.get("XJ")) or item.get("taken"):
            return False
        return not it.get("p5R")
    if s == 3:
        return True if it.get("E2E") else item.get("b37", 0) + item.get("e4u", 0) <= t
    return False


def in_box(item, x, y):
    """`_-91X` @40-358 with half sizes 150 / 150: the item box overlaps the query box (edges included)."""
    it = item["type"]
    pad = STATE3_PAD if item.get("state") == 3 else 0.0
    hw = it.get("w2s", 0.0) * 0.5 + pad
    hh = it.get("S2O", 0.0) * 0.5 + pad
    return (not item["x"] - hw > x + QUERY_HALF and not item["x"] + hw < x - QUERY_HALF
            and not item["y"] + hh < y - QUERY_HALF and not item["y"] - hh > y + QUERY_HALF)


def candidates(items, t, x, y):
    """`_-91X(t, owner, x, y, 150, 150, 2, out)` in `_-O1L` order."""
    return [i for i in items if in_box(i, x, y) and not i.get("taken") and pickable(i, t)]


def choose(items, t, me, x, y, hero, a2=True, a3=False, opponent_near=False):
    """`_-N5R`: the item to take, or None. me = this fighter's id; hero = {mBaseWeapon1, mBaseWeapon2}."""
    best, best_p, best_d = None, 0, 0.0
    for i in candidates(items, t, x, y):
        it = i["type"]
        claim = i.get("claimed_by", 0)
        if claim != 0 and claim != me:
            continue
        s = i.get("state", 0)
        if s == 1 and a3:
            continue
        if it.get("G3X") and not it.get("r5R") and it.get("name") not in (hero.get("mBaseWeapon1"),
                                                                           hero.get("mBaseWeapon2")):
            continue
        if i.get("m5k", 0) & (1 << me):
            continue
        if i.get("dropped_by") == me and t - i.get("dropped_at", 0) < DROP_GUARD_MS:
            continue
        if s == 1:
            p = 2
        elif s == 3:
            p = 4
        elif claim == me and it.get("G3X"):
            p = 5
        else:
            p = type_priority(it)
        if p >= 6 and opponent_near and not a2:
            continue
        d = (x - i["x"]) ** 2 + (y - i["y"]) ** 2
        if best is None or p < best_p:
            best, best_p, best_d = i, p, d
        elif p == best_p and d < best_d:
            best, best_d = i, d
    return best


ANCHORS = {ABC_1100: {
    "Pick-up _-LY: 240 ms _-I2Q, IsMoveLocked, running power, _-N5R(t, a2, a2 && _-I2Q + 240 > t)": [
        (1701, 41, "pushuint", "240"),
        (1701, 57, "initproperty", "_-I2Q"),
        (1701, 67, "callproperty", "IsMoveLocked, 1"),
        (1701, 83, "getproperty", "_-o3I"),
        (1701, 110, "pushuint", "240"),
        (1701, 118, "callproperty", "_-N5R, 3"),
    ],
    "Pick-up _-91X: item box (Width / Height halves, + 100 in state 3) overlaps x +- 150, y +- 150; _-Jl; mask 2 -> _-86Q": [
        (4914, 43, "subtract", ""),
        (4914, 195, "getproperty", "_-w2s"),
        (4914, 198, "pushdouble", "0.5"),
        (4914, 202, "pushbyte", "100"),
        (4914, 243, "getproperty", "_-S2O"),
        (4914, 275, "callproperty", "_-p5a, 0"),
        (4914, 318, "callproperty", "_-d5F, 0"),
        (4914, 361, "getproperty", "_-Jl"),
        (4914, 445, "callproperty", "_-86Q, 1"),
    ],
    "Pick-up _-86Q: states 0-2 / 4 (not _-72T with _-f4i unless AlwaysArmed, not taken, not DisablePickup), state 3 crate or _-b37 + _-E4u": [
        (15243, 29, "lookupswitch", "32, 32, 32, 112, 32, 174, 174, 174, 174, 174"),
        (15243, 95, "getproperty", "_-XJ"),
        (15243, 126, "getproperty", "_-p5R"),
        (15243, 164, "getproperty", "_-E2E"),
        (15243, 185, "getproperty", "_-E4u"),
    ],
    "Pick-up _-N5R: 150 x 150 query, opponent check ahead (0.4, + 0.7 / + 0.6, negated), skips, priorities 2 / 4 / 5 / _-G35, lowest then nearest": [
        (1733, 186, "pushuint", "150"),
        (1733, 201, "callpropvoid", "_-91X, 8"),
        (1733, 329, "pushdouble", "0.4"),
        (1733, 352, "pushdouble", "0.7"),
        (1733, 392, "pushdouble", "0.6"),
        (1733, 418, "negate", ""),
        (1733, 485, "callpropvoid", "_-G2C, 8"),
        (1733, 632, "getproperty", "_-b4Y"),
        (1733, 696, "callproperty", "_-25z, 3"),
        (1733, 793, "getproperty", "_-r5R"),
        (1733, 812, "getproperty", "mBaseWeapon1"),
        (1733, 828, "getproperty", "mBaseWeapon2"),
        (1733, 845, "getproperty", "_-M5k"),
        (1733, 904, "getproperty", "_-O13"),
        (1733, 910, "pushbyte", "64"),
        (1733, 936, "pushbyte", "2"),
        (1733, 952, "pushbyte", "4"),
        (1733, 1002, "pushbyte", "5"),
        (1733, 1014, "getproperty", "_-G35"),
        (1733, 1023, "pushbyte", "6"),
        (1733, 1087, "callproperty", "_-u, 1"),
        (1733, 1130, "ifnlt", "13"),
    ],
    "Pick-up Entity._-u: squared distance from the fighter point to the item centre": [
        (3126, 3, "callproperty", "_-p5a, 0"),
        (3126, 32, "callproperty", "_-d5F, 0"),
        (3126, 62, "multiply", ""),
        (3126, 66, "add", ""),
    ],
    "Pick-up ItemType._-G35: Brawlball 1, WaterBomb 3, BouncyBomb 7, CTF flags 1, OddBall 1, WeaponCrate 6, else 8; DisablePickup / ThrowBow -> _-p5R; Width -> _-w2s": [
        (4974, 3616, "pushstring", "'Brawlball'"),
        (4974, 3633, "pushbyte", "1"),
        (4974, 3658, "pushbyte", "3"),
        (4974, 3684, "pushbyte", "7"),
        (4974, 3766, "getproperty", "_-E2E"),
        (4974, 3775, "pushbyte", "6"),
        (4974, 3787, "pushbyte", "8"),
        (4974, 768, "pushstring", "'DisablePickup'"),
        (4974, 785, "initproperty", "_-p5R"),
        (4974, 3963, "pushstring", "'ThrowBow'"),
        (4974, 3396, "pushstring", "'Width'"),
        (4974, 3413, "initproperty", "_-w2s"),
        (4974, 99, "pushstring", "'Spawnable'"),
        (4974, 107, "constructprop", "ItemType, 2"),
    ],
}}
