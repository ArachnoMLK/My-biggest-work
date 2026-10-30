"""KO-gap check on patch 11.00: no fighter can be knocked out again before the respawn drone has dropped it.

The KO commit `Entity._-eR` calls `Respawn` in the same tick, and the drone then runs its three phases
(spawn_bot.py, PR #30). So between two KO faces of the same victim (oracle.py, PR #27) there are at least
`respawn_ms` milliseconds, with the durations of the replay's scoring type (ScoringTypes.xml, by
`ScoringID` = settings `scoring_type_id`). One-sided: a pass shows the replays allow the transcribed drone
time, not that it is exact. It also checks the first KO of each replay against the match start (256 ms) plus
the first drone trip with the fighters not yet spawned (1500 + 2500 + 700 ms by default) [H: that the first
trip runs with flag 1 clear]. Aggregate counts only.
"""
import collections
import xml.etree.ElementTree as ET

from . import oracle
from .match_start import STEP_MS, match_start_step
from .spawn_bot import F_SPAWNED, SPAWNED_AT_MATCH_START, SPAWNED_IN_PLAY, respawn_ms, scoring_rules


def scoring_cells(xml_text):
    """{ScoringID: {column: text}} from ScoringTypes.xml."""
    out = {}
    for t in ET.fromstring(xml_text):
        cells = {c.tag: (c.text or "") for c in t}
        if cells.get("ScoringID"):
            out[int(cells["ScoringID"])] = cells
    return out


def victim_gaps(rep):
    """Milliseconds between consecutive KO faces of each victim."""
    by = collections.defaultdict(list)
    for tick, victim in oracle.ko_ticks(rep):
        by[victim].append(tick)
    gaps = []
    for ticks in by.values():
        ticks.sort()
        gaps += [oracle.TICK_MS * (b - a) for a, b in zip(ticks, ticks[1:])]
    return gaps


def check(replays, cells, flags=F_SPAWNED if SPAWNED_IN_PLAY else 0):
    """Aggregate over parsed 11.00 replays: gaps, violations (gap < predicted drone time), smallest margin."""
    c = {"replays": 0, "scoring_types": 0, "gaps": 0, "below_floor": 0, "smallest_margin_ms": None,
         "first_kos": 0, "first_ko_below_floor": 0, "first_ko_smallest_margin_ms": None,
         "unknown_scoring_type": 0, "non_tick_ko": 0}
    seen = set()
    for rep in replays:
        c["replays"] += 1
        sid = rep["settings"]["scoring_type_id"]
        if sid not in cells:
            c["unknown_scoring_type"] += 1
            continue
        rules = scoring_rules(cells[sid])
        floor = respawn_ms(flags, rules)
        try:
            gaps = victim_gaps(rep)
            kos = oracle.ko_ticks(rep)
        except ValueError:
            c["non_tick_ko"] += 1
            continue
        if kos:                         # match start (272 ms: _-n4k = 16) + the first drone trip, `_-44x` set
            first_floor = match_start_step(STEP_MS) + respawn_ms(F_SPAWNED if SPAWNED_AT_MATCH_START else 0, rules)
            first = oracle.TICK_MS * kos[0][0]
            c["first_kos"] += 1
            c["first_ko_below_floor"] += first < first_floor
            m = first - first_floor
            c["first_ko_smallest_margin_ms"] = m if c["first_ko_smallest_margin_ms"] is None else min(
                c["first_ko_smallest_margin_ms"], m)
        if gaps:
            seen.add(sid)
        for g in gaps:
            c["gaps"] += 1
            c["below_floor"] += g < floor
            m = g - floor
            c["smallest_margin_ms"] = m if c["smallest_margin_ms"] is None else min(c["smallest_margin_ms"], m)
    c["scoring_types"] = len(seen)
    return c
