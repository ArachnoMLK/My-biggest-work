"""Power step timeline on patch 11.00: which step of an active power fires on which tick.

See docs/hit-detection-11.00.md, section 1. Transcribes the step gate and the step advance of
`_-l4X._-R63` #46. A power runs through the entries of CastTime (`_-a2`, durations in ticks). Each entry is
one step: on the tick its start is reached, the step fires once (hit detection over that step's frame window,
`frame_window`) and the next step is scheduled. The start set-up (`_-f14`: `_-k4b`, first `_-82O`) is in
entity-step-11.00.md (PR #26). Static evidence only.
"""
from .movement import ABC_1100, check, listing

TICK_MS = 16


def tick_index(t):
    """#46 @183-204: round((t - t % 16) / 16), the tick number of a time in ms."""
    q = (t - t % TICK_MS) / TICK_MS
    return int(q // 1 + (1 if q % 1 >= 0.5 else 0))


class Timeline:
    """Step state of one power: `_-X2G` (step), `_-82O` (tick of the next step), `_-d38` (step running).

    `start_tick` is `_-k4b`; the first `_-82O` is start_tick + CastTime[0] (PR #26, `_-f14`).
    `last_step` / `cap` model the guard of @4514-4570: advance while step < len(CastTime) - 1 and, when
    `cap` (`_-t3b` set) is not None, step < cap (`_-Q1n`) [meanings H].
    """

    def __init__(self, cast_times, start_tick, cap=None):
        self.cast = list(cast_times)
        self.start = start_tick
        self.step = 0
        self.next_tick = start_tick + self.cast[0]
        self.running = False
        self.cap = cap
        self.done = False

    def update(self, tick):
        """One `_-R63` call at `tick`: the step index that fires now, or None.

        Gate @1594-1625: fires when not running (`_-d38` false) and tick >= `_-82O`; `_-d38` is set (@1708).
        Advance @4514-4654: if there is a next step, `_-X2G += 1`, `_-82O += max(CastTime[step], 1)` and
        `_-d38` is cleared; otherwise the power stays on its last step (`done`). Cancels (`_-m2j` @4339 under
        MinCancelTime `_-i2o`) are not modelled here.
        """
        if self.running or tick < self.next_tick:
            return None
        self.running = True
        fired = self.step
        i = self.step
        if i < len(self.cast) - 1 and (self.cap is None or i < self.cap):
            self.step += 1
            d = self.cast[self.step]
            self.next_tick += d if d >= 1 else 1
            self.running = False
        else:
            self.done = True
        return fired


def schedule(cast_times, start_tick, ticks):
    """[(tick, step)] for the ticks start_tick .. start_tick + ticks - 1 (one update per tick)."""
    tl = Timeline(cast_times, start_tick)
    out = []
    for k in range(start_tick, start_tick + ticks):
        s = tl.update(k)
        if s is not None:
            out.append((k, s))
    return out


ANCHORS = {ABC_1100: {
    "_-R63 step timeline: tick = round((t - t % 16) / 16); fire when !_-d38 and tick >= _-82O; then _-X2G += 1, _-82O += max(CastTime[_-X2G], 1)": [
        (46, 189, "pushbyte", "16"),
        (46, 191, "modulo", ""),
        (46, 197, "callproperty", "round, 1"),
        (46, 224, "callpropvoid", "_-f14, 1"),
        (46, 1603, "greaterequals", ""),
        (46, 1708, "initproperty", "_-d38"),
        (46, 4302, "getproperty", "_-i2o"),
        (46, 4339, "callpropvoid", "_-m2j, 1"),
        (46, 4524, "getproperty", "_-a2"),
        (46, 4550, "getproperty", "_-t3b"),
        (46, 4564, "getproperty", "_-Q1n"),
        (46, 4595, "increment", ""),
        (46, 4600, "initproperty", "_-X2G"),
        (46, 4629, "lessthan", ""),
        (46, 4645, "initproperty", "_-82O"),
        (46, 4654, "initproperty", "_-d38"),
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
