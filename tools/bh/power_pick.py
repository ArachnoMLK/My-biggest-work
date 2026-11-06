"""Slot -> power on patch 11.00: `_-F5N._-42t(t, slot, gc)` #1726, called by `_-F5N._-C5S` #1700 @40-55.

See docs/hit-detection-11.00.md §10.3. `_-C5S(t, slot, a3, a4, a5, a6)` passes gc = a3 and a6; `_-i4Z._-rU`
gives a3 = local 32 and a6 = local 33 of the input buffer #6313 (dodge.cancel_flags), so gc is the gravity
cancel. The weapon is the held item's ItemType (`_-O2R._-93n`, unarmed `ItemType._-m4V`), swapped for
`ItemType._-iJ` when it has `_-K1V`. Slots 13-20 read a per-fighter emote table and are not transcribed.
[V] unless marked [H].
"""
import csv
import io
import xml.etree.ElementTree as ET

from .movement import ABC_1100

NEUTRAL_SIG, SIDE_SIG, DOWN_SIG = 11, 7, 8   # @494 / @681 / @790
ZOMBIE_FALLBACK = 8                          # @638: in ZOMBIE mode a missing neutral signature takes slot 8
EMOTE_SLOTS = range(13, 21)                  # @167-182
MOMENTUM_SPEED = 60.0                        # @1302: MomentumVersion needs |vx| >= 60 toward the facing


SLOT_COUNT = 21                              # ItemType.<init> #4963 @370: `_-Z6M` = new Vector.<String>(21, fixed)
ITEM_SLOT_COLUMNS = {"PowerType_Combo1": 1, "PowerType_Forward": 2, "PowerType_Down": 3, "PowerType_Aerial": 4,
                     "PowerType_Aerial_Forward": 5, "PowerType_Aerial_Down": 6, "PowerType_Smash_Forward": 7,
                     "PowerType_Smash_Down": 8, "PowerType_Smash_Aerial_Up": 9, "PowerType_Smash_Aerial_Down": 10,
                     "PowerType_Smash_Neutral": 11}  # ItemType._-z2u #4974 @2331-2736
HERO_COLUMNS = ("BaseWeapon1", "BaseWeapon2", "SpecialPower1", "SpecialPower2", "SpecialPower1_Forward",
                "SpecialPower2_Forward", "SpecialPower1_Down", "SpecialPower2_Down")


def item_slots(csv_text):
    """itemTypes.csv (row 0 the table name, row 1 the header) -> {ItemName: {"id": ItemName, "slots": `_-Z6M`}}.
    `_-E49` is the ItemType's first constructor argument (#4963 @384), the name; empty cells stay None."""
    rows = list(csv.reader(io.StringIO(csv_text)))
    head = rows[1]
    out = {}
    for r in rows[2:]:
        cells = dict(zip(head, r))
        name = cells.get("ItemName")
        if not name:
            continue
        slots = [None] * SLOT_COUNT
        for col, i in ITEM_SLOT_COLUMNS.items():
            slots[i] = cells.get(col) or None
        out[name] = {"id": name, "slots": slots}
    return out


def power_rows(csv_text):
    """powerTypes.csv (row 0 the table name, row 1 the header) -> {PowerName: row of strings}, the map `_-kl` that
    `PowerType._-p4G(name)` #6493 reads (a haxe StringMap, `getReserved` for reserved keys). Empty cells are
    dropped so `redirect` sees a missing version as absent. [H] the key is PowerName (the `_-kl` writer is not
    read)."""
    rows = list(csv.reader(io.StringIO(csv_text)))
    head = rows[1]
    out = {}
    for r in rows[2:]:
        cells = {k: v for k, v in zip(head, r) if v != ""}
        if cells.get("PowerName"):
            out[cells["PowerName"]] = cells
    return out


def hero_powers(herotypes_xml):
    """HeroTypes.xml -> {HeroID: {"mBaseWeapon1": ..., "mSpecialPower1_Forward": ...}} for `power_name`.
    [H] the HeroType parser is not read: the columns are taken to fill the fields of the same name with "m"."""
    out = {}
    for h in ET.fromstring(herotypes_xml):
        hid = h.findtext("HeroID")
        if not hid:
            continue
        out[int(hid)] = {"m" + c: (h.findtext(c) or None) for c in HERO_COLUMNS}
    return out


def power_name(slot, hero, weapon, zombie=False):
    """The power name `_-42t` @473-892 picks before the PowerType lookup.

    hero: the HeroType fields `mBaseWeapon1` / `2`, `mSpecialPower1` / `2` and their `_Forward` / `_Down`
    variants; weapon: {"id": `_-E49`, "slots": `_-Z6M`}. Slot 11: the special power of the base weapon that
    matches (1 before 2); unarmed (`ItemType._-m4V`) it is `PowerType._-r7._-r1e`, not resolved here (None); in ZOMBIE mode a missing name takes slot 8 of the weapon. Other slots: `_-Z6M[slot]`,
    then slot 7 / 8 take the `_Forward` / `_Down` special of the matching base weapon when it is set.
    Returns None for the emote slots (not transcribed)."""
    if slot in EMOTE_SLOTS:
        return None
    slots = weapon.get("slots", [])
    wid = weapon.get("id")
    if slot == NEUTRAL_SIG:
        name = None
        if wid == hero.get("mBaseWeapon1"):
            name = hero.get("mSpecialPower1")
        elif wid == hero.get("mBaseWeapon2"):
            name = hero.get("mSpecialPower2")
        if zombie and name is None:
            name = slots[ZOMBIE_FALLBACK] if len(slots) > ZOMBIE_FALLBACK else None
        return name
    name = slots[slot] if 0 <= slot < len(slots) else None
    for sig, suffix in ((SIDE_SIG, "_Forward"), (DOWN_SIG, "_Down")):
        if slot != sig:
            continue
        if wid == hero.get("mBaseWeapon1") and hero.get("mSpecialPower1" + suffix) is not None:
            name = hero["mSpecialPower1" + suffix]
        elif wid == hero.get("mBaseWeapon2") and hero.get("mSpecialPower2" + suffix) is not None:
            name = hero["mSpecialPower2" + suffix]
    return name


def redirect(power, lookup, test_set=False, exhausted=False, gc=False, b3a=0, vx=0.0, facing_left=False):
    """`_-42t` @894-1331: from `PowerType._-p4G(name)` to the power actually used. With the team flag 64, the
    `name + "_TESTFEATURE"` power wins when it exists; then in order: `_-UT` (exhausted [H]) and an
    ExhaustedVersion (`_-M1g`); gc and a GCVersion (`_-E2S`); `_-b3A` > 1 and an OriginOverrideIfInMode
    (`_-w3H`); a MomentumVersion (`_-j5c`) when |vx| >= 60 with vx toward the facing (vx < 0 facing left).
    `power` is a dict of those columns plus "PowerName"; lookup(name) is `_-p4G` (None when unknown)."""
    if power is None:
        return None
    if test_set:
        alt = lookup(power["PowerName"] + "_TESTFEATURE")
        if alt is not None:
            power = alt
    for on, col in ((exhausted, "ExhaustedVersion"), (gc, "GCVersion"), (b3a > 1, "OriginOverrideIfInMode")):
        if power is not None and on and power.get(col):
            power = lookup(power[col])
    if power is not None and power.get("MomentumVersion"):
        speed = abs(vx) if (vx < 0) == facing_left else 0.0
        if speed >= MOMENTUM_SPEED:
            power = lookup(power["MomentumVersion"])
    return power


# --- per-power cooldowns: `_-F5N._-BC` #1747 (armed at a power's end), `_-S4J` #1748 (two slots), `_-O5u` #1744 ---
SIG_FLAGS = 512 | 64        # `PowerType._-I45` bits of a legend signature (`PowerType._-z24` #6491 @147-168)
SIG_LOCK_MS = 160           # #1747 @172-180: `_-y3G` = t + 160 after a signature


def _int_cell(row, col, default=0):
    v = (row or {}).get(col)
    if v in (None, ""):
        return default
    try:
        return int(float(v))
    except ValueError:
        return default


def origin_row(row, rows):
    """`PowerType._-N` (`_-H1V()` #6469) as `PowerType._-W6P` #6495 sets it: the OriginPower row (`_-c5M`), or the
    row itself without one, with 'VARIABLE' (then `_-a37`; `_-F5N._-H1V` #1723 picks `_-66R[_-e28]` [H: not
    modelled]) or with an unknown name."""
    name = (row or {}).get("OriginPower") or ""
    if not name or name == "VARIABLE":
        return row
    return rows.get(name) or row


def cooldown_ms(row, origin, on_hit):
    """`_-F5N._-BC(t, power, on_hit, secondary)` #1747: the cooldown armed when a power ends, in ms. The power's
    OnHitCooldownTime (`_-eQ`) after a hit, else CooldownTime (`_-46C`); when that is 0, the origin's; x 16
    (@186-195). An empty OnHitCooldownTime is CooldownTime (`_-eQ` == -1 -> `_-46C`, #6483 @10924-10945)."""
    def cd(r):
        base = _int_cell(r, "CooldownTime")
        return _int_cell(r, "OnHitCooldownTime", base) if on_hit else base
    v = cd(row)
    if v == 0 and cd(origin) != 0:
        v = cd(origin)
    return v * 16


class Cooldowns:
    """The two cooldown slots of `_-F5N`: (`_-b24`, `_-S32`) and (`mPowerIdOnCooldown2`,
    `mCurrCooldownTimestamp2`). Ids are the origin's PowerID (`_-H4O`)."""

    def __init__(self):
        self.id1, self.until1 = None, 0
        self.id2, self.until2 = None, 0
        self.y3g = 0                                     # `_-y3G`: signature lock

    def arm(self, t, power_id, ms, sig=False, secondary=False):
        """`_-BC` tail and `_-S4J(t, origin, ms)` #1748: slot 1 when the id is already there or slot 1 has run
        out, else slot 2; a signature (flags 512|64) of a non-secondary power also sets `_-y3G` = t + 160."""
        if ms == 0:
            return
        if sig and not secondary:
            self.y3g = t + SIG_LOCK_MS
        if power_id == self.id1 or t >= self.until1:
            self.until1, self.id1 = t + ms, power_id
        else:
            self.until2, self.id2 = t + ms, power_id

    def allows(self, t, power_id, sig=False):
        """`_-O5u(power, t)` #1744 @197-320: false for a signature while t < `_-y3G`, or while the power's id is
        on cooldown in either slot. [H] the start of #1744 (a running power with `_-82f`, the origin swap by
        `_-M1g` / `_-E2S` / `_-w3H` names) is left to the caller."""
        if sig and t < self.y3g:
            return False
        if power_id == self.id1 and t < self.until1:
            return False
        if power_id == self.id2 and t < self.until2:
            return False
        return True


ANCHORS = {ABC_1100: {
    "cooldowns: _-h1T arms _-BC at a power's end; _-BC on-hit _-eQ else _-46C, origin's when 0, x 16, _-y3G = t + 160 for sigs; _-S4J two slots; _-O5u refuses": [
        (1742, 227, "callproperty", "_-R63, 1"),
        (1742, 482, "getproperty", "_-OD"),
        (1742, 741, "callpropvoid", "_-BC, 4"),
        (1747, 25, "callproperty", "_-H1V, 1"),
        (1747, 43, "getproperty", "_-eQ"),
        (1747, 51, "getproperty", "_-46C"),
        (1747, 176, "pushuint", "160"),
        (1747, 180, "initproperty", "_-y3G"),
        (1747, 191, "pushbyte", "16"),
        (1747, 195, "callpropvoid", "_-S4J, 3"),
        (1748, 11, "getproperty", "_-b24"),
        (1748, 41, "initproperty", "_-S32"),
        (1748, 67, "initproperty", "mCurrCooldownTimestamp2"),
        (1748, 77, "initproperty", "mPowerIdOnCooldown2"),
        (1744, 251, "getproperty", "_-H4O"),
        (1744, 278, "getproperty", "_-S32"),
        (1744, 308, "getproperty", "mCurrCooldownTimestamp2"),
        (1744, 239, "getproperty", "_-y3G"),
        (6469, 6, "getproperty", "_-N"),
        (6495, 25, "pushstring", "'VARIABLE'"),
        (6495, 62, "initproperty", "_-N"),
        (6483, 4177, "pushstring", "'CooldownTime'"),
        (6483, 4194, "initproperty", "_-46C"),
        (6483, 7781, "pushstring", "'OnHitCooldownTime'"),
        (6483, 7799, "initproperty", "_-eQ"),
        (6483, 7955, "pushstring", "'OriginPower'"),
        (6483, 7976, "initproperty", "_-c5M"),
        (6483, 8244, "pushstring", "'PowerID'"),
        (6483, 8262, "initproperty", "_-H4O"),
        (6483, 10929, "pushbyte", "-1"),
        (6483, 10945, "initproperty", "_-eQ"),
    ],
    "_-F5N._-42t slot -> power: emote slots 13-20; slot 11 mSpecialPower1 / 2 by mBaseWeapon; ZOMBIE slot 8; _-Z6M[slot]; 7 / 8 _Forward / _Down": [
        (1700, 46, "getlocal_3", ""),
        (1700, 52, "getlocal", "6"),
        (1700, 55, "callproperty", "_-42t, 3"),
        (1726, 103, "getproperty", "_-93n"),
        (1726, 114, "getproperty", "_-m4V"),
        (1726, 145, "getproperty", "_-K1V"),
        (1726, 156, "getproperty", "_-iJ"),
        (1726, 168, "pushbyte", "13"),
        (1726, 178, "pushbyte", "20"),
        (1726, 495, "pushbyte", "11"),
        (1726, 511, "getproperty", "mBaseWeapon1"),
        (1726, 520, "getproperty", "mSpecialPower1"),
        (1726, 541, "getproperty", "mBaseWeapon2"),
        (1726, 550, "getproperty", "mSpecialPower2"),
        (1726, 584, "getproperty", "_-r1e"),
        (1726, 611, "getproperty", "ZOMBIE"),
        (1726, 638, "pushbyte", "8"),
        (1726, 661, "getproperty", "_-Z6M"),
        (1726, 681, "pushbyte", "7"),
        (1726, 708, "getproperty", "mSpecialPower1_Forward"),
        (1726, 757, "getproperty", "mSpecialPower2_Forward"),
        (1726, 790, "pushbyte", "8"),
        (1726, 817, "getproperty", "mSpecialPower1_Down"),
        (1726, 868, "getproperty", "mSpecialPower2_Down"),
        (4963, 370, "pushbyte", "21"),
        (4963, 376, "initproperty", "_-Z6M"),
        (4963, 385, "initproperty", "_-E49"),
        (4974, 2333, "pushstring", "'PowerType_Aerial'"),
        (4974, 2346, "pushbyte", "4"),
        (4974, 2444, "pushstring", "'PowerType_Combo1'"),
        (4974, 2458, "pushbyte", "1"),
        (4974, 2519, "pushstring", "'PowerType_Forward'"),
        (4974, 2532, "pushbyte", "2"),
        (4974, 2705, "pushstring", "'PowerType_Smash_Neutral'"),
        (4974, 2718, "pushbyte", "11"),
    ],
    "_-F5N._-42t redirects: _TESTFEATURE (flag 64); ExhaustedVersion under _-UT; GCVersion under gc; OriginOverrideIfInMode under _-b3A > 1; MomentumVersion at |vx| >= 60": [
        (1726, 899, "callproperty", "_-p4G, 1"),
        (1726, 925, "pushbyte", "64"),
        (1726, 942, "pushstring", "'_TESTFEATURE'"),
        (1726, 997, "getproperty", "_-UT"),
        (1726, 1008, "getproperty", "_-M1g"),
        (1726, 1057, "getlocal_3", ""),
        (1726, 1066, "getproperty", "_-E2S"),
        (1726, 1121, "getproperty", "_-b3A"),
        (1726, 1125, "pushbyte", "1"),
        (1726, 1136, "getproperty", "_-w3H"),
        (1726, 1186, "getproperty", "_-j5c"),
        (1726, 1232, "lessthan", ""),
        (1726, 1241, "callproperty", "_-r35, 0"),
        (1726, 1302, "pushdouble", "60.0"),
        (6493, 3, "getproperty", "_-kl"),
        (6493, 27, "callproperty", "getReserved, 1"),
        (6493, 41, "getproperty", "h"),
    ],
    "Exhausted _-UT: ExhaustedVersion -> _-M1g + _-8u (_-A3R); _-h1T sets _-UT for a _-8u power unless _-P5D; _-C3x (ground refresh) clears it": [
        (6483, 4519, "pushstring", "'ExhaustedVersion'"),
        (6483, 4540, "initproperty", "_-M1g"),
        (6483, 4546, "initproperty", "_-8u"),
        (1742, 505, "getproperty", "_-P5D"),
        (1742, 560, "getproperty", "_-8u"),
        (1742, 581, "initproperty", "_-UT"),
        (1712, 116, "initproperty", "_-UT"),
        (1712, 127, "callpropvoid", "_-k1j, 1"),
        (2984, 414, "getproperty", "_-x2C"),
    ],
}}
