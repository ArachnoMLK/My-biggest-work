"""Power step timeline on patch 11.00: which step of an active power fires on which tick.

See docs/hit-detection-11.00.md, section 1. Transcribes the step gate and the step advance of
`_-l4X._-R63` #46. A power runs through the entries of CastTime (`_-a2`, durations in ticks). Each entry is
one step: on the tick its start is reached, the step fires once (hit detection over that step's frame window,
`frame_window`) and the next step is scheduled. The start set-up (`_-f14`: `_-k4b`, first `_-82O`) is in
entity-step-11.00.md (PR #26). Static evidence only.
"""
import math

from .movement import ABC_1100, check, listing

TICK_MS = 16


def tick_index(t):
    """#46 @183-204: round((t - t % 16) / 16), the tick number of a time in ms."""
    q = (t - t % TICK_MS) / TICK_MS
    return int(q // 1 + (1 if q % 1 >= 0.5 else 0))


def step_cap(charged, held, i6c, n_steps, minimum):
    """`_-Q1n` from the power constructor `_-l4X.<init>` #39 @592-750, or None when the power is not charged.

    For a charged power (`_-t3b`): ceil((held / `_-I6c`, or 0 when `_-I6c` is 0) * len(CastTime)), at least
    `_-L2X` (`minimum`). `held` is constructor argument 5 (`_-a6i`) [H: the charge time].
    """
    if not charged or n_steps is None:
        return None
    frac = held / i6c if i6c != 0 else 0
    cap = math.ceil(frac * n_steps)
    if cap < minimum:
        cap = minimum
    return cap


def momentum(v1d, facing_left):
    """`_-qm` at power creation (#39 @753-880): |x speed| / 60 when moving the way the fighter faces, else 0;
    at most 1."""
    q = abs(v1d) if (v1d < 0) == facing_left else 0
    q = q / 60.0
    return 1 if q > 1 else q


# `_-l4X._-O5N(t, step, hits, deals_damage)` #56, the end reason read by `_-R63` @4061-4083 [V]:
#   5  the power is not a ground pound / meteor (TargetMethod 6 / 9): nothing to end here
#   1  EndOnHit (`_-a3G`) and at least one hit this step (only reached for TargetMethod 6 / 9)
#   2  landed: the owner's ground line `_-96f` (or the `_-N20` look-ahead line) is a walkable line
#   4  the owner's ground line is vertical (a wall)
#   0  keep going
# `_-R63` @4258-4339 ends the power (`_-m2j`) when the reason is neither 0 nor 5 and MinCancelTime `_-i2o` is 0
# or already elapsed (ticks since start >= `_-i2o`).
END_REASONS = {5: "not a ground pound or meteor", 1: "end on hit", 2: "landed", 4: "against a wall", 0: "continue"}


def ends_now(reason, elapsed_ticks, min_cancel_time):
    """`_-R63` @4268-4330: whether the power ends on this step."""
    if reason in (0, 5):
        return False
    return min_cancel_time == 0 or elapsed_ticks >= min_cancel_time


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
    "_-l4X.<init>: _-Q1n = ceil(a6i / I6c * len(a2)) for charged (_-t3b) powers, at least _-L2X; _-qm = |v1D| / 60 (<= 1)": [
        (39, 601, "getproperty", "_-t3b"),
        (39, 666, "getproperty", "_-I6c"),
        (39, 669, "divide", ""),
        (39, 707, "callproperty", "ceil, 1"),
        (39, 712, "initproperty", "_-Q1n"),
        (39, 729, "getproperty", "_-L2X"),
        (39, 853, "pushdouble", "60.0"),
        (39, 880, "initproperty", "_-qm"),
    ],
    "_-O5N end reason (5 / 1 / 2 / 4 / 0) and the end gate in _-R63 (not 0 or 5, MinCancelTime _-i2o)": [
        (56, 37, "pushbyte", "6"),
        (56, 58, "pushbyte", "9"),
        (56, 68, "pushbyte", "5"),
        (56, 81, "getproperty", "_-a3G"),
        (56, 99, "pushbyte", "1"),
        (56, 211, "getproperty", "_-96f"),
        (56, 318, "callproperty", "_-N20, 2"),
        (56, 551, "pushbyte", "4"),
        (56, 559, "pushbyte", "2"),
        (56, 596, "pushbyte", "0"),
        (46, 4076, "callproperty", "_-O5N, 4"),
        (46, 4270, "pushbyte", "5"),
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
