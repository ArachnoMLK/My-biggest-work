"""Slot -> power on patch 11.00: `_-F5N._-42t(t, slot, gc)` #1726, called by `_-F5N._-C5S` #1700 @40-55.

See docs/hit-detection-11.00.md §10.3. `_-C5S(t, slot, a3, a4, a5, a6)` passes gc = a3 and a6; `_-i4Z._-rU`
gives a3 = local 32 and a6 = local 33 of the input buffer #6313 (dodge.cancel_flags), so gc is the gravity
cancel. The weapon is the held item's ItemType (`_-O2R._-93n`, unarmed `ItemType._-m4V`), swapped for
`ItemType._-iJ` when it has `_-K1V`. Slots 13-20 read a per-fighter emote table and are not transcribed.
[V] unless marked [H].
"""
from .movement import ABC_1100

NEUTRAL_SIG, SIDE_SIG, DOWN_SIG = 11, 7, 8   # @494 / @681 / @790
ZOMBIE_FALLBACK = 8                          # @638: in ZOMBIE mode a missing neutral signature takes slot 8
EMOTE_SLOTS = range(13, 21)                  # @167-182
MOMENTUM_SPEED = 60.0                        # @1302: MomentumVersion needs |vx| >= 60 toward the facing


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


ANCHORS = {ABC_1100: {
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
    ],
}}
