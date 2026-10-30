"""First per-tick harness on patch 11.00: one fighter, inputs left / right / jump, on a static map.

Plan step 4 (notes/2026-10-30-replay-sim-plan.md). It chains the transcribed pieces in the byte order of
`Entity._-8i` #2984 (entity-step-11.00.md §2):

1. the input consumer (before `_-8i`): a fresh jump press calls `Entity.Jump(t)` (jump.py: squat or, in
   the dash window, the jump at once);
2. `_-8i`: step-start landing (`ground_reset`), friction then acceleration on `_-v1D` (horizontal.py,
   @519-2659), the squat release (@2674, `_-A2X` -> `Jump(t, false, true)`), the x impulse fold and clamp
   (@2790-3053), the ground walk (@3114-4213), the y impulse fold and clamp (@4217-4483), gravity
   (@5097-5353), the free move (@6620-), the landing delay of a pending jump (@13427-13510), the ring-out
   test (@14270-14370: `_-c5C(x, y, _-5q(), !_-wn() || _-r51 != 0)`, a non-zero mask stored in `_-a3D`;
   ko.py, bounds from level_bounds.py), then `_-84` = `_-A4A` = 0 (@14563-14599).

Every piece is [V] in its own module; the glue is [H]: no power, no hitstun, no wall contact (`_-r51` stays
0 unless set by the caller), the `_-532` jump lock and the air-jump count are not updated by any transcribed
writer yet, the friction is applied on every tick, and a KO only records the mask (the KO commit and the
respawn of ko-11.00.md §5 / spawn_bot.py are not chained yet). Nothing here has been compared with the running game.
"""
from dataclasses import dataclass, field

from .air_move import air_move, gravity_applies, ground_reset, ground_walk
from .horizontal import (acceleration, apply_acceleration, apply_friction, friction_value, max_speed,
                         reversal_factor)
from .ko import ko_mask
from .jump import (air_jump, dash_window, ground_jump, ground_tail, squat_due, squat_gate, squat_on_landing,
                   squat_start, wall_jump)
from .smoke import FALL_CAP, GRAVITY, STEP, TICK_MS
from .step import clamp, fold_impulse, speed_cap

DEFAULT_STATS = {"RunSpeed": 9.0, "AirRunSpeed": 7.0, "Friction": 2.5, "AirFriction": 1.2,
                 "Acceleration": 3.0, "AirAcceleration": 2.0}   # synthetic defaults; real ones from stats.py
AIR_JUMPS = 2       # [H] `_-56T()`: not read yet


@dataclass
class Fighter:
    x: float
    y: float
    v1d: float = 0.0          # `_-v1D`
    p5s: float = 0.0          # `_-P5S`
    h84: float = 0.0          # `_-84`, horizontal one-tick impulse
    a4a: float = 0.0          # `_-A4A`, vertical one-tick impulse
    ground: object = None     # `_-96f`
    r51: int = 0              # `_-r51`
    xb: int = 0               # `_-Xb`, pending jump kind
    i5a: int = 0              # `_-I5A`
    dash_timer: int = 0       # `_-26T`
    lock_start: int = 0       # `_-532`
    air_used: int = 0         # `_-P5Y()`
    air_allowed: int = AIR_JUMPS
    a3d: int = 0              # `Entity._-a3D`, the last non-zero ring-out mask
    stats: dict = field(default_factory=lambda: dict(DEFAULT_STATS))
    events: list = field(default_factory=list)


def _vmax(f):
    return max_speed(f.stats["RunSpeed"], f.stats["AirRunSpeed"], f.ground is None)


def jump(f, t, left, right, third_arg=False):
    """`Entity.Jump(t, false, third_arg)` without a power. Returns the branch taken."""
    dash = dash_window(t, f.dash_timer, f.ground, f.xb)
    if squat_gate(t, False, third_arg, None, f.lock_start, dash, 0):
        f.xb, f.i5a = squat_start(t, f.ground, f.r51)
        return "squat"
    f.i5a = t                                                   # @540: `_-I5A` = t on the jump path
    side = left or right
    r = ground_jump(t, f.dash_timer, f.ground, f.xb, f.a4a)
    if r is not None:
        f.a4a, f.p5s, f.ground, _ = r
        if side:
            f.v1d, f.h84 = ground_tail(left, False, f.v1d, f.h84, _vmax(f))
        return "ground"
    r = wall_jump(f.r51, f.xb, f.a4a, f.h84, left, side)
    if r is not None:
        f.a4a, f.p5s, f.v1d, f.h84, f.ground, _ = r
        return "wall"
    r = air_jump(f.air_used, f.air_allowed, f.a4a, f.v1d, left, side, _vmax(f))
    if r is not None:
        f.a4a, f.p5s, f.v1d, f.air_used = r
        return "air"
    f.i5a = 0                                                   # @2449: no air jump left
    return None


def tick(f, t, grid, left=False, right=False, jump_press=False, team=0, bounds=None):
    """One 16 ms tick at time t. `bounds` is (camera rectangle, kill dict) for the ring-out test, or None.
    Returns the list of events of this tick."""
    events = []
    if jump_press:
        events.append(("press", jump(f, t, left, right)))
    f.p5s, _ = ground_reset(f.ground, False, 0, False, f.p5s)
    airborne = f.ground is None
    vmax = _vmax(f)
    fr = friction_value(t, airborne, f.stats["Friction"], f.stats["AirFriction"], f.dash_timer, vx=f.v1d)
    f.v1d = apply_friction(f.v1d, fr)
    if left != right:
        a, vm = acceleration(airborne, f.stats["Acceleration"], f.stats["AirAcceleration"], vmax=vmax)
        if airborne and (f.v1d > 0) == left and f.v1d != 0:
            a *= reversal_factor(f.v1d)
        f.v1d = apply_acceleration(f.v1d, left, a, vm)
    if squat_due(t, f.xb, f.i5a):                               # `_-A2X`
        f.p5s, f.i5a = 0.0, 0
        events.append(("release", jump(f, t, left, right, third_arg=True)))
        f.xb = 0
    cap = speed_cap()
    f.v1d, _ = fold_impulse(f.v1d, f.h84)
    f.v1d = clamp(f.v1d, cap)
    x_step = f.v1d * STEP
    was_airborne = f.ground is None
    if f.ground is not None:
        w = ground_walk(grid, team, f.x, f.y, f.ground, x_step, 3)
        f.x, f.y, f.ground, x_step = w.x, w.y, w.ground, w.left
        if w.stop_x:
            f.v1d = 0.0
    f.p5s, _ = fold_impulse(f.p5s, f.a4a)
    f.p5s = clamp(f.p5s, cap)
    if gravity_applies(False, f.ground, 0, t, False, GRAVITY) and f.p5s < FALL_CAP:
        f.p5s += GRAVITY * STEP
    m = air_move(grid, team, f.x, f.y, x_step, f.p5s, f.ground is not None)
    f.x, f.y, f.ground = m.x, m.y, m.ground
    landed = was_airborne and f.ground is not None
    if landed:
        f.i5a = squat_on_landing(f.xb, f.i5a, True)
        f.air_used = 0                                          # [H] where `_-k1j(0)` runs is not read
        events.append(("land", f.y))
    if bounds is not None:
        mask = ko_mask(f.x, f.y, bounds[0], bounds[1], False, f.ground is not None or f.r51 != 0)
        if mask:
            f.a3d = mask
            events.append(("ko", mask))
    f.h84 = f.a4a = 0.0
    f.events.extend((t, e) for e in events)
    return events


def run(f, grid, inputs, ticks, t0=0, team=0, bounds=None, stop_on_ko=False):
    """`inputs(tick)` -> (left, right, jump_press). Returns the list of (t, x, y, airborne)."""
    out = []
    for i in range(1, ticks + 1):
        t = t0 + TICK_MS * i
        left, right, press = inputs(i)
        ev = tick(f, t, grid, left, right, press, team, bounds)
        out.append((t, f.x, f.y, f.ground is None))
        if stop_on_ko and any(e[0] == "ko" for e in ev):
            break
    return out
