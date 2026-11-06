"""KO oracle (Q10, part 1): the replay's own KO faces as ground truth for a simulator.

See docs/oracle-ko.md. A KO face is (victim entity, time) written by `_-S45._-04F` #6711 for KO events
of type 1, 2 or 9, at the tick time of the phase 6 commit minus a mode-dependent base (ko-11.00.md, §6).
This module only reads parsed replays (tools/bh/replay.py); it never touches the game.
"""
TICK_MS = 16


def ko_ticks(rep):
    """[(tick, victim)] of a parsed replay, oldest first. tick = time // 16.

    Raises ValueError if a time is not a multiple of 16, which would break the tick reading.
    """
    out = []
    for victim, ms in rep.get("kos") or []:
        if ms % TICK_MS:
            raise ValueError(f"KO time {ms} ms is not a multiple of {TICK_MS}")
        out.append((ms // TICK_MS, victim))
    return sorted(out)


def compare(predicted, recorded):
    """Differences between a simulator's [(tick, victim)] and the replay's, as text lines (empty = match).

    Both lists are compared as sorted multisets; a victim KO'd at the wrong tick shows as one missing and
    one unexpected entry.
    """
    want, got = sorted(recorded), sorted(predicted)
    bad = []
    i = j = 0
    while i < len(want) or j < len(got):
        if j == len(got) or (i < len(want) and want[i] < got[j]):
            bad.append(f"missing    tick {want[i][0]} victim {want[i][1]}")
            i += 1
        elif i == len(want) or got[j] < want[i]:
            bad.append(f"unexpected tick {got[j][0]} victim {got[j][1]}")
            j += 1
        else:
            i += 1
            j += 1
    return bad
