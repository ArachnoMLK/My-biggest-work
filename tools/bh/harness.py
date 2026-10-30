"""First per-tick harness on patch 11.00: one fighter, inputs left / right / jump, on a static map.

Plan step 4 (notes/2026-10-30-replay-sim-plan.md). It chains the transcribed pieces in the byte order of
`Entity._-8i` #2984 (entity-step-11.00.md §2):

1. the input consumer (before `_-8i`): a fresh jump press calls `Entity.Jump(t)` (jump.py: squat or, in
   the dash window, the jump at once);
2. `_-8i`: step-start landing (`ground_reset`), friction then acceleration on `_-v1D` (horizontal.py,
   @519-2659), the squat release (@2674, `_-A2X` -> `Jump(t, false, true)`), the x impulse fold and clamp
   (@2790-3053), the ground walk (@3114-4213), the y impulse fold and clamp (@4217-4483), gravity
   (@5097-5353), the free move (@6620-), `_-r51` saved and cleared (@8869-8886), the response to the stop
   line (air_move.respond: ceiling, slope, wall contact and slide, @8890-12834), the stop line dropped
   from `_-96f` when its normal does not point up or it is steep (@13029-13127), `_-wn()` = airborne
   (@13169), the landing delay of a pending jump (@13427-13510), the ring-out
   test (@14270-14370: `_-c5C(x, y, _-5q(), !_-wn() || _-r51 != 0)`, a non-zero mask stored in `_-a3D`;
   ko.py, bounds from level_bounds.py), then `_-84` = `_-A4A` = 0 (@14563-14599).

The dodge (`dodge` for `Entity.Dodge` before `_-8i`, `dodge_tick` for `_-t1A` @2659; friction and gravity off
while dodging) runs when `dodge_rows` are given. Every piece is [V] in its own module; the glue is [H]: no
power, no hitstun, no bounce, no dash, no chase dodge, the `_-532` jump lock and the air-jump count are not updated by any transcribed
writer yet, the friction is applied on every tick, and a KO only records the mask (the KO commit and the
respawn of ko-11.00.md §5 / spawn_bot.py are not chained yet). Nothing here has been compared with the running game.

`match_start` chains the start of a plain 1v1 replay (match_start.py, spawn_bot.py): the step at 272 ms
(`_-n4k` = 16), the fighters in `_-5r` order (increasing entity id), R at that tick, the start placement
(`one_v_one`), then `Drone.place` with the replay's `_-w35` (1024) and the drone phases until the fighter is
let go (state 0, `_-P5S` = the drop speed). Its glue is [H]: the drone's first tick runs in the match-start
step only through `_-k5H` (now [V], spawn_bot.py), the `_-vs` gate holds, no game-mode test, no `_-S3h`, and the
fighters are independent.
"""
from dataclasses import dataclass, field

from .air_move import WallState, air_move, gravity_applies, ground_reset, ground_walk, respond, steep, wall_contact
from .dodge import (attack_air_offset, c2e, cancel_flags, clears_velocity, cooldown_ms, dodge_over, exit_velocity, facing, flags_51c, formula_mult,
                    gates, is_dodge_locked, k64, landed_cooldown, moves, neutral_push, pick, push, side_latch, speed_x,
                    speed_y, standard_flag, timers)
from .hitdetect import (area_center, capsules_touch, frame_window, hit_capsule, hurtbox_capsule, row_values,
                        target_method)
from .knockback import final_magnitude, hit_damage, hitstun_ms, knockback_decay, knockback_force
from .horizontal import (acceleration, apply_acceleration, apply_friction, friction_value, max_speed,
                         reversal_factor)
from .input_buffer import attack_slot, buffered_presses, state_at
from .power_data import power_steps
from .power_pick import power_name, redirect
from .power_timeline import Timeline, tick_index
from .ko import ko_mask
from .respawn_points import candidates
from .jump import (air_jump, dash_window, ground_jump, ground_tail, squat_due, squat_gate, squat_on_landing,
                   squat_start, wall_jump)
from .entity_states import respawn_index
from .match_start import STEP_MS, fighter_order, match_start_step, one_v_one, r_at_match_start, step_times, time_base
from .smoke import FALL_CAP, GRAVITY, STEP, TICK_MS
from .spawn_bot import IDLE, REPLAY_W35, SPAWNED_AT_MATCH_START, SPAWNED_IN_PLAY, Drone, scoring_rules, timing_flags
from .step import clamp, fold_impulse, speed_cap

DEFAULT_STATS = {"RunSpeed": 9.0, "AirRunSpeed": 7.0, "Friction": 2.5, "AirFriction": 1.2,
                 "Acceleration": 3.0, "AirAcceleration": 2.0}   # synthetic defaults; real ones from stats.py
AIR_JUMPS = 2       # [H] `_-56T()`: not read yet
MOVE_LEFT, MOVE_RIGHT, JUMP = 4, 8, 16   # replay.INPUT_BITS: bit i = 1 << i
FALL_CAP_DROP = 85.0                      # movement-11.00.md: `Entity._-8i` @5127-5170 with the Drop bit
DODGE_DASH, DIR_MASK = 256, 15            # the dodge key; Dodge's dir = keys & 15 (#6313 @2427)
LIGHT, HEAVY = 128, 64                    # LightAttack, HeavyAttack (input-buffer-11.00.md)


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
    wn: bool = True           # `_-wn()`: airborne after the previous move
    g1t: bool = False         # `_-G1T`
    y1l: int = 0              # `_-y1L`
    dodge: dict = None        # the DodgeTypes row of the last dodge (`_-Q42`)
    h2b: int = 0              # `_-H2b`, dodge start
    uy: int = 0               # `_-Uy`
    c1d: int = 0              # `_-C1d`
    y1f: int = 0              # `_-y1F`
    o5c: int = 0              # `_-O5C`, dodge dir
    w14: int = 0              # `_-14W`
    e6p: bool = False         # `_-E6P()`: dodging
    u5e: bool = False         # `_-u5E()`: dodge cooldown running
    a1h: bool = False         # `_-a1h`
    t5l: float = 1.0          # `_-T5L`
    wl: float = 1.0           # `_-WL`
    l4a: bool = False         # `_-l4A`
    g5e: bool = False         # `_-g5E`
    facing_left: bool = False  # `_-n3h`
    i46: int = 0              # `_-46I`, last hit (no hits here)
    e3: int = 0               # `_-3E`
    f6r: int = 0              # `_-f6R`, end of PostDodge
    t322: int = 0             # `_-322`, last landing (`_-8i` @13446)
    moves: dict = None        # {"hero": hero_powers row, "weapon": item_slots row, "powers": power_rows}
    power: dict = None        # the running power: {"name", "steps": power_steps, "tl": Timeline}
    w22: float = 0.0          # `_-W22`, damage taken
    j1m: float = 0.0          # `_-J1m`, x overshoot of the impulse fold
    d4x: float = 0.0          # `_-d4x`, y overshoot
    stun_until: int = 0       # end of the hitstun (`_-5q()` until then) [H]
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


def dodge(f, t, dir, rows):
    """`Entity.Dodge(t, dir)` (dodge.py) on the harness fighter: `gates`, `pick`, then the commit writes. Returns
    the DodgeName or None. [H] glue: no power, no move lock, no area / `_-C54` lock, `_-x2C` = 0, no chase dodge
    (`_-26R` false), no dash (`Dash` false: a refused ground side dodge does nothing), `_-VE` = 0, `_-M3h` false,
    the power multipliers `_-Kc._-u5j` / `_-04K` = 1, Set "Default", the `_-6K` counter not kept."""
    airborne = f.ground is None
    c = c2e(t, dir, f.lock_start, False, not airborne)

    def locked(flag):
        return is_dodge_locked(False, f.u5e, flag, f.e6p, False, f.r51, False, f.xb, False, 0)

    g = gates(t, dir, c, f.i46, airborne, locked(False), locked(c), f.h2b, f.w14, f.y1f, False, f.o5c, False,
              False, not airborne, 0, f.lock_start, f.facing_left, None)
    if g is None:
        return None
    d = g["dir"]
    row = pick(rows, d, airborne, g["is_fast"])
    if row is None:
        return None
    if g["w14"] is not None:
        f.w14 = g["w14"]
    if g["clear_vx"]:
        f.v1d = 0.0
    f.e6p, f.dodge, f.h2b, f.o5c, f.l4a = True, row, t, d, False
    f.facing_left = facing(d, f.facing_left)
    run, air_run = f.stats["RunSpeed"], f.stats["AirRunSpeed"]
    k = k64(standard_flag(t, airborne, f.i5a, f.air_used), airborne, air_run, 1.0, run, 1.0)
    f.t5l = speed_x(formula_mult(row.get("SpeedXFormula"), f.v1d, k, d), row.get("SpeedXMult", 1.0),
                    row.get("SpeedXMaxMult", 0.0), d, f.v1d, air_run)
    f.wl = speed_y(formula_mult(row.get("SpeedYFormula"), f.v1d, k, d), row.get("SpeedYMult", 1.0),
                   row.get("SpeedYMaxMult", 0.0), d, f.p5s)
    if row.get("IsFast") and row.get("SpeedXMult", 0.0) != 0:
        f.v1d = neutral_push(k, d)
    z4s = cooldown_ms(row.get("Cooldown", 0), row.get("CooldownGround", 0), airborne or f.r51 != 0)
    tm = timers(t, row.get("Duration", 0), row.get("Recover", 0), row.get("IsFast"), z4s, g["chain_end"])
    f.uy, f.c1d, f.y1f = tm["_-Uy"], tm["_-C1d"], tm["_-y1F"]
    if clears_velocity(d, airborne):
        f.v1d = f.p5s = 0.0
    return row.get("DodgeName")


def dodge_tick(f, t, a, held):
    """`Entity._-t1A(t, a)` (dodge.py), run by `_-8i` @2659 with a = the step's max speed: the landed cooldown, the
    cooldown end, then while dodging the push of each tick or, at the timer end, the exit speed."""
    row = f.dodge
    if row is None:
        return
    airborne = f.ground is None
    f.y1f = landed_cooldown(f.y1f, airborne, f.r51, False, f.a1h, row.get("DodgeID", 0), t, f.i46,
                            row.get("CooldownLanded", 0), f.uy, f.c1d)
    if dodge_over(t, f.u5e, f.h2b, f.y1f, f.e3)[0]:
        f.h2b = 0
        f.u5e, f.a1h, _ = flags_51c(False, True, f.a1h, 0)
    if not f.e6p:
        return
    mv = moves(row.get("kind", 0), row.get("where", 0))
    if f.h2b + f.uy + f.c1d <= t:
        f.e6p = False                                           # `_-w5G(false)`
        if f.r51 == 0:                                          # @458-550: `_-f6R` = t + PostDodge x 16
            f.f6r = t + row.get("PostDodge", 0) * 16
        if not f.u5e:
            f.v1d, f.p5s, cv = exit_velocity(f.v1d, f.p5s, a, mv, held, f.l4a, f.g5e, f.t5l, row.get("ExitX", 1.0),
                                             row.get("ExitBackX", 1.0), row.get("ExitY", 1.0),
                                             row.get("ExitBackY", 1.0))
            if cv is not None:
                f.facing_left = cv
            f.u5e, f.a1h, _ = flags_51c(True, False, f.a1h, 0)
            f.t5l = f.wl = 1.0
    elif t >= f.h2b:
        p = push(t, f.h2b, 0, mv, f.t5l, f.wl, row.get("AccelXMult", 1.0), row.get("AccelYMult", 1.0),
                 row.get("AccelXFormula"), row.get("AccelYFormula"), f.uy, f.c1d, f.o5c)
        if p is not None:
            f.v1d = f.p5s = 0.0
            f.h84, f.a4a = p
        f.l4a, f.g5e = side_latch(f.l4a, f.g5e, held)


def attack(f, t, keys, heavy):
    """The move slot a fresh light / heavy press asks for (`_-i4Z._-rU` #6334): `dodge.cancel_flags` (in the
    cancel window of a dodge, local 33) then `dodge.attack_air_offset` (0 under the cancel: the gravity cancel)
    and `input_buffer.attack_slot`. Returns (slot, gravity cancel). [H] glue: no move runs (no `_-I35` chain),
    `_-f2b()` false, no jump flag, `_-y1U` false; the power itself is not started yet (plan step b2-b5)."""
    row = f.dodge if f.e6p else None
    gc = False
    if row is not None:
        press = t
        _, gc, _ = cancel_flags(t, True, False, 0 if heavy else press, press if heavy else 0, 0, 0, 0, f.h2b, False,
                                False, f.o5c, row.get("CancelStart", 0), row.get("CancelLimit", 0))
    off, _ = attack_air_offset(f.ground is None, False, gc, False)
    return attack_slot(keys, heavy, off != 0), gc


UNSET = 2147483647        # an empty CastImpulse cell (`_-l4X._-O1K` #91 @396)


def cast_impulse(f, power):
    """`_-l4X._-O1K` #91 @385-471 / @1087-1144 (entity-step-11.00.md): CastImpulseX (`_-C6Z`) **sets** `_-v1D`,
    negated when `_-L0` (facing left), and CastImpulseY (`_-8S`) sets `_-P5S`, each unless unset. [H] glue: run at
    the power start (the first `_-f14` update), `_-L0` = the facing, the other branches of #91 (@475-1083,
    @1148-1491: `_-I2g & 2`, combo fields) are not read."""
    def num(k):
        v = power.get(k)
        try:
            v = int(float(v))
        except (TypeError, ValueError):
            return None
        return None if v == UNSET else v
    cx, cy = num("CastImpulseX"), num("CastImpulseY")
    if cx is not None:
        f.v1d = float(-cx if f.facing_left else cx)
    if cy is not None:
        f.p5s = float(cy)


def _int_list(cell):
    out = []
    for x in (cell or "").split(","):
        try:
            out.append(int(float(x)))
        except ValueError:
            out.append(UNSET)
    return out


def fire_impulse(f, power, step):
    """`_-l4X._-a5A` #47, run by `_-R63` when a step fires: FireImpulseX (`_-84C`)[step] (entry 0 past the end)
    **sets** `_-v1D`, negated when `_-L0`; FireImpulseY (`_-ol`)[step] sets `_-P5S`, unless that y is > 0 under
    `_-I2g & 2` within `_-t2b` ticks of the start; each unless unset. [H] glue: no charge factor (`_-V3`), the
    FireImpulseMaxX branch (@249-387) and the `_-I2g` gate not modelled, the cells read as plain int lists."""
    for col, attr in (("FireImpulseX", "v1d"), ("FireImpulseY", "p5s")):
        vals = _int_list(power.get(col))
        if not power.get(col):
            continue
        v = vals[step] if step < len(vals) else vals[0]
        if v == UNSET:
            continue
        if attr == "v1d" and f.facing_left:
            v = -v
        setattr(f, attr, float(v))


def tick(f, t, grid, left=False, right=False, jump_press=False, team=0, bounds=None, dodge_press=False, keys=0,
         dodge_rows=None, light_press=False, heavy_press=False):
    """One 16 ms tick at time t. `bounds` is (camera rectangle, kill dict) for the ring-out test, or None.
    `dodge_press` with `dodge_rows` (dodge.parse_types) tries `Entity.Dodge(t, keys & 15)` first (#6313 tries the
    dodge before the jump). Returns the list of events of this tick."""
    events = []
    if t < f.stun_until:                                        # `_-5q()`: no input acts in hitstun [H]
        left = right = jump_press = dodge_press = light_press = heavy_press = False
        keys = 0
    if f.power is not None:                                     # `_-Kc._-25` before `_-8i` (state 0)
        step = f.power["tl"].update(tick_index(t))
        if step is not None:
            events.append(("step", f.power["name"], step))
            f.power["fired"] = step
            fire_impulse(f, f.power.get("row", {}), step)
        if f.power["tl"].done:
            f.power = None                                      # [H] the end rules (`ends_now`) are not chained
    if dodge_press and dodge_rows:
        name = dodge(f, t, keys & DIR_MASK, dodge_rows)
        if name is not None:
            events.append(("dodge", name))
    if jump_press:
        events.append(("press", jump(f, t, left, right)))
    for press, heavy in ((light_press, False), (heavy_press, True)):
        if press:
            slot, gc = attack(f, t, keys, heavy)
            name = power_name(slot, f.moves["hero"], f.moves["weapon"]) if f.moves else None
            rows = (f.moves or {}).get("powers")
            if name is not None and rows:
                power = redirect(rows.get(name), rows.get, gc=gc, vx=f.v1d, facing_left=f.facing_left)
                name = power["PowerName"] if power else None
                if power is not None and f.power is None:       # [H] no chain / cancel into a running power
                    steps = power_steps(power)
                    if steps["CastTime"]:
                        f.power = {"name": name, "steps": steps, "tl": Timeline(steps["CastTime"], tick_index(t)),
                                   "g4i": target_method(power.get("TargetMethod", ""))[0], "hit": set(),
                                   "row": power}
                        cast_impulse(f, power)
                        f.lock_start = t                        # `_-532` = t: `Entity._-c1r` at the move start
            events.append(("attack", slot, gc, name))
    f.p5s, _ = ground_reset(f.ground, False, 0, False, f.p5s)
    airborne = f.ground is None
    vmax = _vmax(f)
    if t < f.stun_until and f.v1d * f.v1d + f.p5s * f.p5s >= 2500.0:   # @713-760: `_-V12` instead of friction
        f.v1d, f.p5s, f.j1m, f.d4x = knockback_decay(f.v1d, f.p5s, f.j1m, f.d4x, f.stats.get("Recovery", 4.0))
    elif not f.e6p:                                             # friction only when !`_-E6P()` [H: local 8]
        pw = None
        if f.power is not None:                                 # [H] `_-o3I._-7E` false
            keep = str(f.power.get("row", {}).get("KeepGroundFriction", "")).upper() == "TRUE"
            pw = {"7E": False, "y25": keep}
        fr = friction_value(t, airborne, f.stats["Friction"], f.stats["AirFriction"], f.dash_timer, power=pw,
                            hitstun=t < f.stun_until, vx=f.v1d)
        f.v1d = apply_friction(f.v1d, fr)
    if left != right:
        a, vm = acceleration(airborne, f.stats["Acceleration"], f.stats["AirAcceleration"], vmax=vmax)
        if airborne and (f.v1d > 0) == left and f.v1d != 0:
            a *= reversal_factor(f.v1d)
        f.v1d = apply_acceleration(f.v1d, left, a, vm)
    dodge_tick(f, t, vmax, keys & DIR_MASK)                     # `_-t1A` @2659
    if squat_due(t, f.xb, f.i5a):                               # `_-A2X`
        f.p5s, f.i5a = 0.0, 0
        events.append(("release", jump(f, t, left, right, third_arg=True)))
        f.xb = 0
    cap = speed_cap()
    f.v1d, over = fold_impulse(f.v1d, f.h84)
    if over is not None:
        f.j1m = over                                            # @2901 [H: the stored value is the full sum]
    f.v1d = clamp(f.v1d, cap)
    x_step = f.v1d * STEP
    was_airborne = f.ground is None
    if f.ground is not None:
        w = ground_walk(grid, team, f.x, f.y, f.ground, x_step, 3)
        f.x, f.y, f.ground, x_step = w.x, w.y, w.ground, w.left
        if w.stop_x:
            f.v1d = 0.0
    f.p5s, over = fold_impulse(f.p5s, f.a4a)
    if over is not None:
        f.d4x = over
    f.p5s = clamp(f.p5s, cap)
    g_term = 0.0
    fall_cap = FALL_CAP_DROP if keys & 2 else FALL_CAP           # @5097-5170: 85 with Drop held [H: `_-61h`, lock]
    if gravity_applies(f.e6p, f.ground, f.y1l, t, False, GRAVITY) and f.p5s < fall_cap:
        g_term = GRAVITY * STEP
        f.p5s += g_term
    m = air_move(grid, team, f.x, f.y, x_step, f.p5s, f.ground is not None)
    f.x, f.y, f.ground = m.x, m.y, m.ground
    r51_before, f.r51 = f.r51, 0                                # @8869-8886
    if m.ground is not None:
        ws = None
        if m.ground.sx == m.ground.ex:
            ws = WallState(t, f.wn, False, r51_before, f.g1t, f.y1l, f84q=GRAVITY, gravity=g_term)
            r51 = wall_contact(grid, team, m.x, m.y, m.ground, f.p5s, f.v1d, ws)[4]
            if r51 is not None:
                f.r51 = r51
                events.append(("wall", r51))
        r = respond(grid, team, m, f.p5s, f.v1d, wall_state=ws)
        f.x, f.y, f.p5s, f.v1d = r.x, r.y, r.p5s, r.v1d
        g = f.ground
        if g.normal is not None and (g.normal[1] >= 0 or steep(g)):   # @13029-13127
            f.ground = None
    f.wn = f.ground is None                                     # @13169
    landed = was_airborne and f.ground is not None
    if landed:
        f.t322 = t
        f.i5a = squat_on_landing(f.xb, f.i5a, True)
        f.air_used = 0                                          # [H] where `_-k1j(0)` runs is not read
        events.append(("land", f.y))
    if bounds is not None:
        mask = ko_mask(f.x, f.y, bounds[0], bounds[1], t < f.stun_until, f.ground is not None or f.r51 != 0)
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


def from_records(records, t0=0):
    """Inputs of one entity of a replay (`replay.parse(...)["inputs"][entity]`, (time ms, key word) at every
    change) as `run` wants them: tick i reads the key word at t = t0 + 16 i (`input_buffer.state_at`).
    Left / right are MoveLeft / MoveRight; the jump press is bit 16 set at t and clear at t - 16.
    [H] The input buffer of #28 (a press kept up to 5 ticks, the 192 ms `_-532` lock) is not modelled: only
    the edge on the tick itself counts."""
    def inputs(i):
        t = t0 + TICK_MS * i
        keys = state_at(records, t)
        before = state_at(records, t - TICK_MS)
        return bool(keys & MOVE_LEFT), bool(keys & MOVE_RIGHT), bool(keys & JUMP and not before & JUMP)
    return inputs


def step_hits(f, step, victim, hurtbox):
    """The frame index of the first hit area of `f`'s power at `step` touching `victim`'s hurtbox, or None.

    The frames scanned are `hitdetect.frame_window(q24, step)`; each makes an area with `area_center` (the power's
    TargetMethod `_-g4i`, CenterOffsetX / Y), the capsule `hit_capsule(AoERadiusX, AoERadiusY)`, tested with
    `capsules_touch` against `hurtbox_capsule` of the victim's `hurtbox` row 0. [H] glue: the DEFAULT hurtbox
    (no animation frame), no team mask, no line of sight, no item or point areas."""
    st = f.power["steps"]
    first, count = frame_window(st["q24"], step)
    w = row_values(hurtbox["Width"], 0)
    h = row_values(hurtbox["Height"], 0)
    hb = hurtbox_capsule(victim.x, victim.y, w, h, row_values(hurtbox["OffsetX"], 0), row_values(hurtbox["OffsetY"], 0),
                         victim.facing_left)
    for i in range(first, first + count):
        if not all(i < len(st[c]) for c in ("CenterOffsetX", "CenterOffsetY", "AoERadiusX", "AoERadiusY")):
            continue
        c = area_center(f.power["g4i"], f.x, f.y, i, st["CenterOffsetX"], st["CenterOffsetY"], f.facing_left)
        if c is None:
            continue
        if capsules_touch(hit_capsule(c[0], c[1], st["AoERadiusX"][i], st["AoERadiusY"][i]), hb):
            return i
    return None


def _at(values, i, default=0):
    return values[i] if i < len(values) else (values[0] if values else default)


def apply_hit(f, v, i, t):
    """`_-26u._-76s` #1675 in short (knockback.py) for the hit of `f`'s power entry i on `v`: damage
    (BaseDamage; `hit_damage`), magnitude `knockback_force(VariableImpulse)` (then `_-W22` += damage) +
    FixedImpulse (`final_magnitude`), direction (ImpulseOffsetX mirrored by the attacker's facing, ImpulseOffsetY)
    scaled to it and written into the victim's `_-84` / `_-A4A`, one air jump back when all were used
    (`_-91G` #1677 @1171-1226), hitstun `hitstun_ms(FixedStunTime)`.
    Glue [H]: no charge, no item part, weapon / victim factors and `_-G4s` / `_-13t` = 1, the `_-M3e` Strength /
    Weight entry 1, no directional influence, no MinimumImpulse, no damage setting; the victim's velocity is
    cleared first. Returns (damage, magnitude)."""
    st = f.power["steps"]
    dmg = hit_damage(_at(st["BaseDamage"], i), 0, 0, 1.0, 1.0, 1.0, victim_w22=v.w22)
    vi = _at(st["VariableImpulse"], i)
    u = knockback_force(vi, dmg, v.w22, v.stats.get("HPOffset", 0.0), 1.0, 1.0, v.stats.get("ImpulseNegation", 0.0),
                        attacker_z4f=f.stats.get("ImpulseMult", 1.0))   # `_-W22` before this hit + its damage
    v.w22 += dmg                                                # [H] where `_-W22` is written is not chained
    m = final_magnitude(u, _at(st["FixedImpulse"], i), 0.0, vi)
    dx = _at(st["ImpulseOffsetX"], i)
    dy = _at(st["ImpulseOffsetY"], i)
    if f.facing_left:
        dx = -dx
    n = (dx * dx + dy * dy) ** 0.5
    v.v1d = v.p5s = 0.0
    if n > 0:
        v.h84, v.a4a = dx / n * m, dy / n * m
    if m > 0 and v.air_used == v.air_allowed:                   # #1677 @1171-1226: one air jump back
        v.air_used -= 1
    v.stun_until = t + int(hitstun_ms(_at(st["FixedStunTime"], i)))
    return dmg, m


def match_start(entities, seed, points, camera, cells=None, team_type=0, spawned=SPAWNED_AT_MATCH_START,
                start_xy=(0.0, 0.0),
                standalone=False, max_ticks=1000):
    """Start of a plain 1v1 replay. `entities`: replay.parse "entities" (the two players); `points`:
    respawn_points.parse_respawns; `camera`: (x, y, width); `cells`: the replay's ScoringType cells; `spawned`:
    `_-44x` (set by `_-k5H` in state 2, spawn_bot.py); `start_xy`: the position before the drone when it is
    clear [H].
    Returns [(entity, Fighter or None, t let go, state)] in `_-5r` order (None: no point or never let go)."""
    n4k = time_base(step_times(0, STEP_MS))
    t0 = match_start_step(n4k)
    rng, _ = r_at_match_start(seed, len(entities))
    placed, _ = one_v_one(rng, fighter_order(entities), points)
    rules = scoring_rules(cells or {}, n4k=n4k)
    by_id = {}
    for e, point in placed:
        f = {"x": start_xy[0], "y": start_xy[1], "state": 3, "vy": 0.0, "spawned": bool(spawned)}
        d = Drone(f)
        d.place(t0, None if point is None else (point["x"], point["y"]), standalone, REPLAY_W35, False, camera)
        t, ready = t0, False
        while point is not None and d.phase != IDLE and t <= t0 + STEP_MS * max_ticks:
            d.tick(t, timing_flags(f["spawned"], False, None, t), rules, team_type, False)
            if d.phase == IDLE:
                ready = True
                break
            t += STEP_MS
        ready = ready or (point is not None and f["state"] == 0)
        by_id[id(e)] = (e, Fighter(f["x"], f["y"], p5s=f["vy"]) if ready else None, t if ready else None,
                        f["state"])
    return [by_id[id(e)] for e in fighter_order(entities)]


def ko_reset(f):
    """`Entity._-p1Y` #3034 on the harness fighter: velocities, impulses, ring-out mask, wall flag, ground."""
    f.v1d = f.p5s = f.h84 = f.a4a = 0.0
    f.a3d = f.r51 = 0
    f.ground = None


def play(entities, seed, points, camera, grid, bounds, stats_by_id, inputs_by_id, cells=None, lives=3,
         lives_mode=True, team_type=0, standalone=False, ticks=6000, dodge_rows=None, moves_by_id=None,
         hurtbox=None):
    """Both fighters of a plain 1v1 replay in lockstep from the match-start step. Per tick, in `_-5r` order:
    phase 5 (`_-k5H`: the drone first, then movement in states 0 / 5, which clears `_-44x`), then phase 6
    (`_-eR`: a ring-out mask -> KO commit at t, lives - 1, then `Respawn`: state 7 when eliminated, else the
    next point of the shared `_-G5X` counter and the drone). Returns {entity id: {"kos": [t], "let_go": [t]}}.
    [H] the glue of `match_start` and replay_setup.py; no hits; inputs only feed the movement."""
    n4k = time_base(step_times(0, STEP_MS))
    t0 = match_start_step(n4k)
    rng, _ = r_at_match_start(seed, len(entities))
    placed, g5x = one_v_one(rng, fighter_order(entities), points)
    counters = list(g5x)
    rules = scoring_rules(cells or {}, n4k=n4k)
    players = []
    for e, point in placed:
        body = {"x": 0.0, "y": 0.0, "state": 3, "vy": 0.0, "spawned": SPAWNED_AT_MATCH_START}
        d = Drone(body)
        d.place(t0, None if point is None else (point["x"], point["y"]), standalone, REPLAY_W35, False, camera)
        players.append({"e": e, "body": body, "drone": d, "f": None, "lives": lives, "kos": [], "let_go": []})
    by_order = {id(e): i for i, e in enumerate(fighter_order(entities))}
    players.sort(key=lambda p: by_order[id(p["e"])])
    for k in range(ticks):
        t = t0 + STEP_MS * k
        for p in players:                                   # phase 5
            body, d = p["body"], p["drone"]
            if d.phase != IDLE:
                d.tick(t, timing_flags(body["spawned"], False, None, t), rules, team_type, False)
                if d.phase == IDLE and body["state"] in (0, 5):
                    st = stats_by_id.get(p["e"]["id"])
                    p["f"] = Fighter(body["x"], body["y"], p5s=body["vy"], stats=dict(st) if st else dict(DEFAULT_STATS),
                                     moves=(moves_by_id or {}).get(p["e"]["id"]))
                    p["let_go"].append(t)
            if body["state"] in (0, 5) and p["f"] is not None:
                body["spawned"] = SPAWNED_IN_PLAY
                records = inputs_by_id.get(p["e"]["id"], [])
                keys = state_at(records, t)
                f = p["f"]                                      # #6313 @122-209: window 9 while dodging,
                wide = (f.e6p or t <= f.t322 + 64 or t <= f.i5a + 32   # 64 ms after landing, in a squat,
                        or t <= f.f6r)                          # before `_-f6R`; else 5
                bp = buffered_presses(records, t, 9 if wide else 5) or {}   # [H] the `_-P50` / `_-M3V` cases
                done = p.setdefault("handled", {})
                fresh = {a: bp[a] for a in ("Jump", "DodgeDash", "LightAttack", "HeavyAttack")
                         if a in bp and bp[a] > done.get(a, -1)}
                ev = tick(p["f"], t, grid, bool(keys & MOVE_LEFT), bool(keys & MOVE_RIGHT), "Jump" in fresh, 0,
                          bounds, "DodgeDash" in fresh, keys, dodge_rows, "LightAttack" in fresh,
                          "HeavyAttack" in fresh)
                attacks = [a for a in ("LightAttack", "HeavyAttack") if a in fresh]   # tick's order
                for e in ev:                                    # a press is handled once its action ran [H]
                    if e[0] == "press" and e[1] is not None:
                        done["Jump"] = fresh["Jump"]
                    elif e[0] == "dodge":
                        done["DodgeDash"] = fresh["DodgeDash"]  # `_-C51` = t (#6313 @2389-2504)
                    elif e[0] == "attack" and attacks:
                        a = attacks.pop(0)
                        done[a] = fresh[a]
        if hurtbox is not None:                             # b4: queued hits of the fired steps [H]
            for p in players:
                f = p["f"]
                if f is None or f.power is None or f.power.get("fired") is None:
                    continue
                step, f.power["fired"] = f.power["fired"], None
                for q in players:
                    v = q["f"]
                    if q is p or v is None or q["e"]["id"] in f.power["hit"]:
                        continue
                    i = step_hits(f, step, v, hurtbox)
                    if i is not None:
                        f.power["hit"].add(q["e"]["id"])
                        apply_hit(f, v, i, t)
                        p.setdefault("hits", []).append((t, q["e"]["id"], f.power["name"]))
        for p in players:                                   # phase 6
            f, body = p["f"], p["body"]
            if f is None or body["state"] not in (0, 5) or not f.a3d:
                continue
            p["kos"].append(t)
            ko_reset(f)
            body.update(x=f.x, y=f.y, vy=0.0, state=3)
            p["lives"] -= 1
            if Drone.eliminated(p["lives"], lives_mode, body["state"]):
                body["state"] = 7
                continue
            alive = sum(1 for q in players if q["body"]["state"] not in (7, 8))
            cands = candidates(points, alive, body["spawned"])
            point = cands[respawn_index(counters, 0, len(cands), False)] if cands else None
            p["drone"].place(t, None if point is None else (point["x"], point["y"]), standalone, REPLAY_W35, False,
                             camera)
        if all(p["body"]["state"] == 7 for p in players):
            break
    return {p["e"]["id"]: {"kos": p["kos"], "let_go": p["let_go"], "hits": p.get("hits", [])} for p in players}
