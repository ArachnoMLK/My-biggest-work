"""Fighter stats from the legend's stance (Q5), as the game builds them on patch 11.00.

Chain (docs/stats-11.00.md): RuneTypes.xml gives (Strength, Dexterity, Weight, Speed) levels per legend
and stance; each level picks one StatType of StatTypes.xml named family + level (`Speed0` .. `Speed11`);
each family sets only its own fields. Fields a StatType leaves out keep the constructor defaults of
`_-C5c.<init>` #11983 (the `Template` entry is skipped by the parser). Four fields are stored as 1 / value.
Reads the local `swz-dump` output; nothing from the game is stored in the repository.
"""
import re

from .movement import ABC_1100, check, listing  # noqa: F401  (re-exported for bht.py)

FAMILIES = ["Strength", "Dexterity", "Weight", "Speed"]  # _-C5c._-36d, index = first argument of _-q2w
MAX_LEVEL = 11
# Fields copied by Entity._-p1E #3049 from each family's StatType
FAMILY_FIELDS = {
    "Strength": ["ImpulseMult"],
    "Dexterity": ["RecoverMod", "AirRecoverMod", "SigRecoverMod", "MinChargeMod", "DurabilityMod"],
    "Weight": ["Recovery"],
    "Speed": ["AnimSpeed", "RunSpeed", "AirRunSpeed", "Acceleration", "AirAcceleration", "Friction",
              "AirFriction", "JumpXImpulse"],
}
# _-C5c.<init> #11983 (JumpXImpulse comes from a static field, not a literal: None here)
DEFAULTS = {"DurabilityMod": 1.0, "JumpXImpulse": None, "AirFriction": 1.2, "Friction": 2.5,
            "AirAcceleration": 5.16, "Acceleration": 4.7, "AirRunSpeed": 30.0, "RunSpeed": 30.0,
            "Recovery": 4.0, "AnimSpeed": 1.0, "ImpulseNegation": 0.0, "InterruptThreshold": 0.0,
            "HPOffset": 0.0, "MinChargeMod": 1.0, "SigRecoverMod": 1.0, "AirRecoverMod": 1.0,
            "RecoverMod": 1.0, "DamageFixed": 0.0, "ImpulseMult": 1.0}
RECIPROCAL = {"AirRecoverMod", "MinChargeMod", "RecoverMod", "SigRecoverMod"}  # 1.0 / value in #11987

ANCHORS = {ABC_1100: [
    (11990, 86, "pushstring", "'Strength'"), (11990, 90, "pushstring", "'Dexterity'"),
    (11990, 93, "pushstring", "'Weight'"), (11990, 97, "pushstring", "'Speed'"),
    (11990, 102, "initproperty", "_-36d"),
    (11986, 175, "pushbyte", "11"), (11986, 202, "add", ""), (11986, 302, "pushstring", "'Missing Core Stat: '"),
    (11988, 10, "pushbyte", "4"), (11988, 20, "pushbyte", "11"), (11988, 32, "getproperty", "_-cx"),
    (11987, 39, "pushstring", "'Template'"), (11987, 47, "returnvoid", ""),
    (11987, 242, "pushdouble", "1.0"), (11987, 256, "divide", ""), (11987, 257, "initproperty", "_-G6R"),
    (11983, 66, "pushdouble", "30.0"), (11983, 69, "initproperty", "_-z2v"),
    (3049, 383, "pushbyte", "0"), (3049, 404, "pushbyte", "1"), (3049, 425, "pushbyte", "2"),
    (3049, 446, "pushbyte", "3"), (3049, 451, "callproperty", "_-q2w, 2"),
    (3049, 535, "getproperty", "_-z4f"),
    # replay parser _-24q._-b2L #6699: per hero, costume then stance; Entity._-f6Q #3051 passes the stance on
    (6699, 1156, "initproperty", "_-617"), (6699, 1168, "initproperty", "_-b67"),
    (3051, 379, "getproperty", "_-b67"), (3051, 382, "callpropvoid", "_-p1E, 2"), (3049, 623, "getproperty", "_-z2p"),
]}


def _items(xml, tag):
    for m in re.finditer(rf"<{tag}\b([^>]*)>(.*?)</{tag}>", xml, re.S):
        yield m.group(1), dict(re.findall(r"<(\w+)>([^<]*)</\1>", m.group(2)))


def parse_stat_types(xml):
    """{StatName: {field: float}} with the fields each entry sets (Template skipped, reciprocals applied)."""
    out = {}
    for attrs, fields in _items(xml, "StatType"):
        name = re.search(r'StatName="([^"]*)"', attrs).group(1)
        if name == "Template":
            continue
        out[name] = {k: (1.0 / float(v) if k in RECIPROCAL else float(v)) for k, v in fields.items() if k in DEFAULTS}
    return out


def parse_stances(xml):
    """{(HeroName, RuneIndex): {family: level}}; HeroName carries over to following entries, as in #7304."""
    out, hero = {}, None
    for _, f in _items(xml, "RuneType"):
        hero = f.get("HeroName") or hero
        out[(hero, int(f.get("RuneIndex", 0)))] = {fam: int(f[fam]) for fam in FAMILIES if fam in f}
    return out


def fighter_stats(levels, stat_types):
    """Effective fields for one stance: each family's StatType fields, else the constructor default."""
    out = {}
    for fam in FAMILIES:
        level = levels.get(fam)
        st = stat_types.get(f"{fam}{level}", {}) if level is not None and 0 <= level <= MAX_LEVEL else {}
        for field in FAMILY_FIELDS[fam]:
            out[field] = st.get(field, DEFAULTS[field])
    return out
