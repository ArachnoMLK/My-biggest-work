"""Replay setup for the harness on patch 11.00 (plan step 4): map, KO bounds, legend stats and the match start
of a plain 1v1 replay, read from the local swz dump at run time (nothing from the game is stored).

Pieces [V] in their own modules: stats.py (the replay's stance -> fields), level_bounds.py (CameraBounds,
LevelType kills), respawn_points.py, smoke.map_grid, and harness.match_start (match_start.py, spawn_bot.py).
Once the drone lets go, the fighter moves in the same `Entity._-k5H` call (the drone ticks first, @45-66, then
the state dispatch), so its first harness tick is the let-go step.

The glue is [H]: the HeroType is found by HeroID; the fighter uses its first hero; the drone's camera
rectangle `_-I1f._-8I` is the CameraBounds at the match start; only the static lines (no moving platforms);
the fighters do not interact (no hits, no grabs); the harness reads only the Speed family fields; the lives
come from the settings' `starting_lives`.
"""
import os
import re
import xml.etree.ElementTree as ET

from . import dodge, harness, power_pick, stats
from .level_bounds import camera_bounds, level_kills
from .respawn_points import parse_respawns
from .smoke import map_grid

UNARMED = "Unarmed"        # `ItemType._-m4V` (ItemType._-R2Z #4965 @313-330); fighters start unarmed [H]
HARNESS_STATS = ("RunSpeed", "AirRunSpeed", "Friction", "AirFriction", "Acceleration", "AirAcceleration",
                 "ImpulseMult", "HPOffset", "ImpulseNegation", "Recovery")


def _read(path):
    with open(path, "rb") as f:
        raw = f.read()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252")


def hero_names(herotypes_xml):
    """{HeroID: HeroName} from HeroTypes.xml (the HeroName attribute, as RuneTypes.xml names the legends)."""
    out = {}
    for name, body in re.findall(r'<HeroType HeroName="([^"]+)"[^>]*>(.*?)</HeroType>', herotypes_xml, re.S):
        m = re.search(r"<HeroID>(\d+)</HeroID>", body)
        if m:
            out[int(m.group(1))] = name
    return out


def level_name(level_types_xml, level_id):
    """LevelName of the LevelType whose LevelID is `level_id`, or None."""
    for t in ET.fromstring(level_types_xml):
        if (t.findtext("LevelID") or "").strip() == str(level_id):
            return t.get("LevelName") or t.findtext("LevelName")
    return None


def harness_stats(entity, names, stances, stat_types):
    """The harness's stat dict for the entity's first hero and stance, or None when the stance is unknown."""
    h = entity["heroes"][0]
    levels = stances.get((names.get(h["hero_id"]), h["stance"]))
    if levels is None:
        return None
    full = stats.fighter_stats(levels, stat_types)
    return {k: full[k] for k in HARNESS_STATS if k in full}


def default_hurtbox(path):
    """The DEFAULT row of hurtboxTypes.csv as {"Width", "Height", "OffsetX", "OffsetY": int lists}, or None.
    [H] the harness uses it for every frame (the animation-dependent rows need the .anm frames)."""
    if not os.path.exists(path):
        return None
    import csv
    import io
    rows = list(csv.reader(io.StringIO(_read(path))))
    head = rows[1]
    for r in rows[2:]:
        cells = dict(zip(head, r))
        if cells.get("HurtboxName") == "DEFAULT":
            return {k: [int(float(x)) for x in (cells.get(k) or "0").split(",")]
                    for k in ("Width", "Height", "OffsetX", "OffsetY")}
    return None


class Swz:
    """The XML files the setup needs, from a swz-dump folder."""

    def __init__(self, root):
        self.root = root
        game = os.path.join(root, "Game.swz")
        self.names = hero_names(_read(os.path.join(game, "HeroTypes.xml")))
        self.stances = stats.parse_stances(_read(os.path.join(game, "RuneTypes.xml")))
        self.stat_types = stats.parse_stat_types(_read(os.path.join(game, "StatTypes.xml")))
        path = os.path.join(game, "DodgeTypes.xml")
        self.dodge_rows = dodge.parse_types(_read(path))[0] if os.path.exists(path) else None
        self.heroes = power_pick.hero_powers(_read(os.path.join(game, "HeroTypes.xml")))
        path = os.path.join(game, "itemTypes.csv")
        self.items = power_pick.item_slots(_read(path)) if os.path.exists(path) else {}
        self.hurtbox = default_hurtbox(os.path.join(game, "hurtboxTypes.csv"))
        path = os.path.join(game, "powerTypes.csv")
        self.powers = power_pick.power_rows(_read(path)) if os.path.exists(path) else {}
        self.scoring = {}
        for t in ET.fromstring(_read(os.path.join(game, "ScoringTypes.xml"))):
            cells = {c.tag: (c.text or "") for c in t}
            if cells.get("ScoringID"):
                self.scoring[int(cells["ScoringID"])] = cells
        self.level_types = _read(os.path.join(root, "Init.swz", "LevelTypes.xml"))
        self.kills = level_kills(self.level_types)

    def level(self, level_id):
        """(name, LevelDesc text) or (name, None) when the file is missing."""
        name = level_name(self.level_types, level_id)
        path = os.path.join(self.root, "Dynamic.swz", f"LevelDesc_{name}.xml")
        return name, (_read(path) if name and os.path.exists(path) else None)


def setup(rep, swz):
    """Everything `run` needs for one parsed replay, or raises ValueError with a reason."""
    if len(rep["entities"]) != 2:
        raise ValueError("not 1v1")
    name, desc = swz.level(rep["level_id"])
    if desc is None:
        raise ValueError("no LevelDesc")
    cam = camera_bounds(desc)
    if cam is None or name not in swz.kills:
        raise ValueError("no bounds")
    fighter_stats = {}
    for e in rep["entities"]:
        st = harness_stats(e, swz.names, swz.stances, swz.stat_types)
        if st is None:
            raise ValueError("unknown stance")
        fighter_stats[e["id"]] = st
    return {"grid": map_grid(desc), "points": parse_respawns(desc), "cam": cam, "kill": swz.kills[name],
            "drone_camera": (cam[0], cam[1], cam[2] - cam[0]), "stats": fighter_stats,
            "cells": swz.scoring.get(rep["settings"]["scoring_type_id"], {}),
            "moves": {e["id"]: {"hero": swz.heroes.get(e["heroes"][0]["hero_id"]), "weapon": swz.items.get(UNARMED),
                          "powers": swz.powers}
                      for e in rep["entities"] if swz.heroes.get(e["heroes"][0]["hero_id"]) and swz.items.get(UNARMED)}}


def run(rep, swz, ticks=6000):
    """Both fighters in lockstep (`harness.play`) with their own inputs: {entity id: {"kos", "let_go"}} (times
    in ms). Lives from the settings' `starting_lives` [H: `_-V` and `_-d3Y._-81d` are not traced to them]."""
    s = setup(rep, swz)
    lives = rep["settings"].get("starting_lives", 0)
    return harness.play(rep["entities"], rep["random_seed"], s["points"], s["drone_camera"], s["grid"],
                        (s["cam"], s["kill"]), s["stats"], rep["inputs"], s["cells"], lives=lives,
                        lives_mode=lives > 0, ticks=ticks, dodge_rows=swz.dodge_rows, moves_by_id=s["moves"],
                        hurtbox=swz.hurtbox)
