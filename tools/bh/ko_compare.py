"""Plan step 5: the first two-sided check. The harness's predicted first KO of a victim against the replay's
own KO face (`oracle.ko_ticks`), on local 1v1 replays of patch 11.00; aggregate counts only.

Only the match's first KO is used, and only when the opponent pressed no LightAttack, HeavyAttack or
PickUpThrow before it, so no hit can explain it ([H] a KO type 2 "self" is not kept by `replay.parse`; this
input filter stands in for it). Cases where the victim itself pressed an attack, a dodge or a throw are
counted apart: the harness only moves left / right / jump.

Time base: in a replay `_-w35` has 1024 (`spawn_bot.REPLAY_W35`), a bit of `ko.NO_BASE_BITS`, so
`ko.ko_time_base` is 0 and the face time is the absolute tick time of the phase 6 commit, the same clock as
`harness.play`'s KO times. [V] in their own modules; the pairing here is glue.
"""
from collections import Counter

from . import oracle, replay_setup
from .input_buffer import ACTIONS

TICK_MS = 16
HIT_KEYS = ACTIONS["LightAttack"] | ACTIONS["HeavyAttack"] | ACTIONS["PickUpThrow"]
UNMODELLED_KEYS = HIT_KEYS | ACTIONS["DodgeDash"] | ACTIONS["Taunt"]


def pressed_before(records, mask, ms):
    """True if any (time, keys) record with time < ms has a bit of mask."""
    return any(t < ms and keys & mask for t, keys in records)


def first_ko(rep):
    """(victim, ms) of the match's first recorded KO, or None."""
    kos = oracle.ko_ticks(rep)
    if not kos:
        return None
    tick, victim = kos[0]
    return victim, tick * TICK_MS


def classify(predicted, ms):
    """How the predicted KO times [ms] of the victim compare with the recorded first KO at ms."""
    if not predicted:
        return "none predicted"
    d = predicted[0] - ms
    if d == 0:
        return "exact"
    if abs(d) <= TICK_MS:
        return "off by one tick"
    return "early" if d < 0 else "late"


def compare_one(rep, swz, ticks):
    """(category, victim kept simple) for one parsed replay, or (reason, None) when it is not a candidate."""
    ko = first_ko(rep)
    if ko is None:
        return "no KO", None
    victim, ms = ko
    ids = [e["id"] for e in rep["entities"]]
    if len(ids) != 2 or victim not in ids:
        return "not 1v1", None
    other = ids[1 - ids.index(victim)]
    inputs = rep["inputs"]
    if pressed_before(inputs.get(other, []), HIT_KEYS, ms):
        return "opponent attacked first", None
    out = replay_setup.run(rep, swz, ticks=max(ticks, ms // TICK_MS + 64))
    simple = not pressed_before(inputs.get(victim, []), UNMODELLED_KEYS, ms)
    return classify(out[victim]["kos"], ms), simple


def check(reps, swz, ticks=6000):
    """Aggregate counts over parsed replays (format 271 only)."""
    c = Counter()
    for rep in reps:
        if rep.get("version") != 271:
            continue
        try:
            cat, simple = compare_one(rep, swz, ticks)
        except ValueError as e:
            c[f"skipped ({e})"] += 1
            continue
        if simple is None:
            c[f"skipped ({cat})"] += 1
            continue
        c[f"all candidates: {cat}"] += 1
        if simple:
            c[f"victim moved / jumped only: {cat}"] += 1
    return c
