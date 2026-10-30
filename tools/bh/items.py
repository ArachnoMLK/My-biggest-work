"""Motion of thrown items on patch 11.00: the velocity part of `_-p5k._-8i` #15192 (up to the move vector).

See docs/hit-detection-11.00.md, section 8.1. Arithmetic in bytecode order; [V] unless marked [H]. Not here:
the ground walk loop along a line (@1268-1732, the same shape as the fighter's), the path behaviours
(`PathType`, @1901-4344) and the map sweeps after the move vector (@4700-). Static evidence only.
"""
import math

from .air_move import steep
from .movement import ABC_1100
from .raycast import ray_cast

STEP = 0.384            # `_-z2k._-Vj`
DEFAULT_CAP = 350.0     # `_-93n._-Z5d` when 0; `ItemType.<init>` sets 0 and no parser column writes it
GROUND_PUSH = 1.01      # `_-p5k._-x3M` (script822.<init> #15249): the move gets 2 x this on a ground line
SMALL = 1.02            # `_-p5k._-u4H` = `Entity._-u4H` (_-y2E.init #15351 @80326-80338)
ITEM_IGNORE = 32        # `_-z2k._-M4J`: lines that items pass through
SOFT_THROW_MS = 64      # @818-834: soft lines are ignored this long after a throw from a soft platform

# `ItemType.static._-z2u` #4974 column -> field; defaults from `ItemType.<init>` #4963
ITEM_COLUMNS = {"Friction": "T2P", "AirFriction": "h5M", "Gravity": "84Q", "ThrownGravity": "OY",
                "PathLength": "G6o", "PathType": "z4P", "ForceNoHitstop": "T30", "OnlyStunnedTrigger": "N59",
                "AllowRepeatedCollision": "A4s", "Height": "S2O", "ForceNoGeometryCollision": "p2W",
                "Elasticity": "7c", "StickToWalls": "o1G", "AlwaysArmed": "XJ", "ConditionalStickToWalls": "o1l"}
ITEM_DEFAULTS = {"T2P": 2.5, "h5M": 0.15, "84Q": 3.75, "OY": 3.75, "G6o": 0, "z4P": 0, "T30": False,
                 "N59": False, "A4s": False, "S2O": 0, "p2W": False, "7c": 0.6, "o1G": False, "XJ": False,
                 "o1l": 0}
STICK_FLAGS = {"STRICT_ANGLE": 1, "FLOORS_ONLY": 2}           # ConditionalStickToWalls, split on "|"
REST_SPEED2 = 2500      # `_-p5k._-Y3M` (script822.<init> #15249): a thrown item at or below this speed^2 rests
STOP_SPEED = 5          # `_-u1I` @1366: on a flat floor, slower impacts stop instead of bouncing
STRICT_COS = -0.7237379   # `_-u1I` @1187: STRICT_ANGLE sticks when cos(velocity, normal) is below this
BOUNCY = 64             # `_-z2k._-B6P`
BOOMERANG_REARM_MS = 500    # `_-p5k._-K3V` (script822.<init> #15249)
THROW_GUARD_MS = 400        # `_-h20` @866-880
PATH_TYPES = {"BoomerangHoming": 1, "Linear": 2, "Rocket": 3, "RocketHoming": 4, "Crawl": 5}   # else 0


def sweep_mask(thrower_ground_soft, state, thrown_at, t, path_type, bg, thrown_gravity, force_no_hitstop):
    """@733-970: hard | soft (3), or hard only (1) when one of:
    - the thrower stands on a soft line, the item is in state `_-5T` 1 and t <= `_-O13` + 64;
    - PathType 1 (BoomerangHoming) while `_-BG` is set;
    - state 1, ThrownGravity 0 and `_-T30` (ForceNoHitstop column) set."""
    a = thrower_ground_soft and state == 1 and thrown_at + SOFT_THROW_MS >= t
    b = path_type == 1 and bg
    c = state == 1 and thrown_gravity == 0 and force_no_hitstop
    return 1 if a or b or c else 3


def velocity(lu, vy, impulse_x, impulse_y, ground, item, thrown, o2o, bg=False, cap=DEFAULT_CAP):
    """One tick of `_-p5k._-8i` @972-1260 and @1740-1820, @4348-4583.

    lu / vy are `_-Lu` / `_-33c`; impulse_x / impulse_y are `_-B66` / `_-46m`; `ground` is `_-96f` (a line
    with `.normal`, or None); `item` holds the ItemType fields (ITEM_DEFAULTS keys); `thrown` is
    `_-r5B != 0`; `o2o` is `_-o2O`. Returns (lu, vy, move) where move = `_-U5T`. With `bg` the path behaviour
    replaces the gravity (not transcribed) and move uses vy as left by the clamp.
    """
    friction = item["T2P"] if ground is not None else item["h5M"]
    sign = 1.0 if lu > 0 else -1.0                   # @1013-1037
    mag = sign * lu - friction * STEP
    if mag < 0:
        mag = 0
    lu = mag * sign
    lu += impulse_x                                  # @1126-1202: impulse, then the cap
    if lu > cap:
        lu = cap
    elif lu < -cap:
        lu = -cap
    x_step = lu * STEP
    vy += impulse_y                                  # @1740-1816
    if vy > cap:
        vy = cap
    elif vy < -cap:
        vy = -cap
    if not bg:                                       # @4348-4497: gravity unless at rest on a flat line
        resting = lu == 0 and vy == 0 and ground is not None and ground.normal[1] == -1
        if not resting:
            g = item["OY"] if thrown and not o2o else item["84Q"]
            vy += g * STEP
    my = vy * STEP + (GROUND_PUSH * 2 if ground is not None else 0.0)   # @4501-4583
    return lu, vy, (x_step, my)


def target_gate(c, item, t, thrown_at, lu, vy, io, x5g):
    """`_-p5k._-h20` #15239 @651-1744 for one candidate: (hit, new `_-x5G`).

    `c` describes the candidate: `bit` (1 << `_-03K()`), `entity` (a fighter), `hitstun` (`_-5q()`),
    `overlap` (the capsule or swept test, §8 steps 3-4), `catch` (`_-J5Z(t, false, true)` [H: a catch
    check]) with `catch_dir` (`_-66f(_-Lu, _-33c)`), `u4b` (`_-u4B`), and the thrower facts `thrower_stunned_by`
    (the thrower is in hitstun, its `_-W6D` is this candidate and that power is not a ThrownItem) and `i1e`
    (`_-I1E(candidate)`). `io` is `_-Io` (targets already hit, -1 = all), `x5g` is `_-x5G` (targets in
    contact). The last candidate that returns hit=True is the one handed to `_-Q3h` (§8 step 6).
    """
    bit = c["bit"]
    if c["entity"] and item["N59"] and not c["hitstun"]:            # OnlyStunnedTrigger, @712-742
        return False, x5g
    if io & bit and (not item["A4s"] or io == -1):                   # already hit, @771-841
        return False, x5g
    if c["entity"] and t < thrown_at + THROW_GUARD_MS:               # @845-997
        if c.get("thrower_stunned_by") or c.get("i1e"):
            return False, x5g
    if not c["overlap"]:                                             # @1297-1320: contact lost
        return False, x5g & ~bit
    if c["entity"] and c.get("catch"):                               # @1324-1409
        return False, (x5g & ~bit) if c.get("catch_dir") else (x5g | bit)
    grace = 64 if abs(vy) > abs(lu) else 32                          # @1413-1569
    if c["entity"] and not c["hitstun"] and t - thrown_at < grace:
        return False, x5g | bit
    if c["entity"] and item["z4P"] == 1 and t - max(c.get("u4b", 0), thrown_at) >= BOOMERANG_REARM_MS:
        x5g &= ~bit                                                  # @1573-1677: a boomerang re-arms
    if x5g & bit and not (c.get("f4i") and c.get("explode_power")):  # @1680-1735: still in contact
        return False, x5g
    return True, x5g


def _length(v):
    return math.sqrt(v[0] * v[0] + v[1] * v[1])


def _back_off(line, mv):
    """@5135-5418 / @6033-6290: along -normal for a hard line and a tiny move (|x|, |y| <= 1.02), else along
    the move; length `_-x3M` = 1.01."""
    tiny = line.type & 1 and -SMALL <= mv[0] <= SMALL and -SMALL <= mv[1] <= SMALL
    v = (-line.normal[0], -line.normal[1]) if tiny else mv
    n = _length(v)
    return (0.0, 0.0) if n == 0 else (v[0] * GROUND_PUSH / n, v[1] * GROUND_PUSH / n)


def sweep(lines, team, x, y, move, mask, height, no_geometry=False):
    """`_-p5k._-8i` @4683-6357: the map sweeps of an item. Returns (x, y, ground `_-96f`, head_stop).

    `no_geometry` is ForceNoGeometryCollision (`_-p2W`) in state 1: no sweep at all. Otherwise a feet cast
    along the move (mask, item-ignore lines excluded) and a top cast from `height` above (hard only); the
    top one wins when shorter and its line is not a flat floor (normal y != -1). The item moves by the
    shortened vector, its `_-96f` becomes the hit line, and it backs off 1.01 from it. The ceiling cast of
    @5474-5544 is a `callpropvoid` whose result is never stored (`local37` stays null), so items have no
    ceiling re-cast.
    """
    if hasattr(lines, "candidates"):
        def cands(cx, cy, d):
            return lines.candidates(cx, cy, cx + d[0], cy + d[1])
    else:
        def cands(cx, cy, d):
            return lines
    if no_geometry:
        return x + move[0], y + move[1], None, False
    hit = ray_cast(cands(x, y, move), team, x, y, move[0], move[1], mask, 0, ITEM_IGNORE)
    mv = move if hit is None else hit.remaining
    line = None if hit is None else hit.line
    top = ray_cast(cands(x, y - height, move), team, x, y - height, move[0], move[1], 1, 0, ITEM_IGNORE)
    head_stop = False
    if top is not None and _length(top.remaining) < _length(mv) and top.line.normal[1] != -1:
        mv, line, head_stop = top.remaining, top.line, True
    x, y = x + mv[0], y + mv[1]
    if line is not None:
        b = _back_off(line, mv)
        x, y = x - b[0], y - b[1]
    return x, y, line, head_stop


def bounce(line, lu, vy, elasticity, friction):
    """`_-p5k._-048` #15245 (the game-mode lines' `_-h40` override is left out): the speeds after a bounce.

    The elasticity is `_-7c` (the item's Elasticity), averaged with 1 on a bouncy line (64). A vertical line
    reverses `_-Lu`, a horizontal one `_-33c`, both times e. On a slope the normal part is reversed times e
    (1.05 on a steep line `_-S1A` while falling toward it), and the tangent part loses `Friction` when it is
    longer than 1.5 x Friction.
    """
    e = (1 + elasticity) * 0.5 if line.type & BOUNCY else elasticity
    if line.sx == line.ex:
        return lu * -e, vy
    if line.sy == line.ey:
        return lu, vy * -e
    nx, ny = line.normal
    if steep(line) and vy > 0 and (lu > 0) == (nx > 0):
        e = 1.05
    d = lu * nx + vy * ny
    ux, uy = d * nx, d * ny
    wx, wy = lu - ux, vy - uy
    wl = math.sqrt(wx * wx + wy * wy)
    if wl > friction * 1.5:
        k = (wl - friction) / wl
        wx, wy = wx * k, wy * k
    ux, uy = ux * e, uy * e
    return wx - ux, wy - uy


def impact(lu, vy, line, item, can_stick=False):
    """`_-p5k._-u1I` #15194 @712-1515, without the special cases before it (ExpireOnGeometryCollision powers,
    Teleport, lava with Weapon) and the path behaviours. Returns (lu, vy, kind): "stick", "bounce" or "stop".

    `can_stick` is StickToWalls with `_-72T` and (thrown or AlwaysArmed) [H: `_-72T`]. STRICT_ANGLE also
    sticks a head-on hit (cos < -0.7237379); FLOORS_ONLY cancels sticking when -|nx| < ny. A stuck item
    stops (`_-f4i`). Otherwise it bounces when the line is not a flat floor or the speed is >= 5, else stops.
    """
    speed = math.sqrt(lu * lu + vy * vy)
    stick = can_stick
    nx, ny = line.normal
    if item["o1l"] & 1:
        c = (lu * nx + vy * ny) / speed if speed != 0 else 0
        if c < STRICT_COS:
            stick = True
    if item["o1l"] & 2 and -abs(nx) < ny:
        stick = False
    if stick:
        return 0.0, 0.0, "stick"
    if ny != -1 or speed >= STOP_SPEED:
        lu, vy = bounce(line, lu, vy, item["7c"], item["T2P"])
        return lu, vy, "bounce"
    return 0.0, 0.0, "stop"


def after_sweep(lu, vy, ground, item, state, can_stick=False):
    """`_-p5k._-8i` @6891-7391 with a ground line: (lu, vy, state, impact kind or None).

    A moving item (`_-Lu` or `_-33c` != 0) in state 0 or 1, or AlwaysArmed, calls the impact; so does a
    lava line; otherwise a floor (normal y < 0) zeroes `_-33c`. Then, on a floor that is not steep, a thrown
    item (state 1) at or below speed^2 2500 rests (state 0), and state 2 rests once both speeds are 0.
    """
    kind = None
    if ground is None:
        return lu, vy, state, kind
    if (lu != 0 or vy != 0) and (state in (0, 1) or item["XJ"]):
        lu, vy, kind = impact(lu, vy, ground, item, can_stick)
    elif ground.type & 512:
        lu, vy, kind = impact(lu, vy, ground, item, can_stick)
    elif ground.normal[1] < 0:
        vy = 0.0
    if ground.normal[1] < 0 and not steep(ground):
        if state == 1 and lu * lu + vy * vy <= REST_SPEED2:
            state = 0
        elif state == 2 and lu == 0 and vy == 0:
            state = 0
    return lu, vy, state, kind


def expired(t, thrown_at, path_length):
    """@1832-1882: `_-5k()` (the item is removed) once t - `_-O13` > PathLength, when PathLength != 0."""
    return path_length != 0 and t - thrown_at > path_length


def item_type(cells):
    """ItemType fields from one row's cells ({column: text}); missing cells keep the defaults."""
    r = dict(ITEM_DEFAULTS)
    for col, field in ITEM_COLUMNS.items():
        v = cells.get(col)
        if v is None or v == "":
            continue
        if field == "z4P":
            r[field] = PATH_TYPES.get(v, 0)
        elif field == "o1l":
            r[field] = sum(STICK_FLAGS.get(p, 0) for p in set(v.split("|")))   # OR of distinct bits
        elif field in ("T30", "N59", "A4s", "p2W", "o1G", "XJ"):
            r[field] = v.strip().lower() == "true"
        elif field in ("G6o", "S2O"):            # uint slots
            r[field] = int(v)
        else:
            r[field] = float(v)
    return r


ANCHORS = {ABC_1100: {
    "_-p5k._-8i friction: _-Lu toward 0 by (Friction on ground / AirFriction) x _-Vj, + _-B66, cap _-Z5d or 350": [
        (15192, 993, "getproperty", "_-T2P"),
        (15192, 1006, "getproperty", "_-h5M"),
        (15192, 1027, "pushdouble", "1.0"),
        (15192, 1034, "pushdouble", "-1.0"),
        (15192, 1056, "getproperty", "_-Vj"),
        (15192, 1097, "getproperty", "_-Z5d"),
        (15192, 1106, "pushdouble", "350.0"),
        (15192, 1142, "getproperty", "_-B66"),
        (15192, 1217, "getproperty", "_-Vj"),
    ],
    "_-p5k._-8i vertical: _-33c + _-46m capped; gravity ThrownGravity / Gravity unless at rest on a flat line": [
        (15192, 1756, "getproperty", "_-46m"),
        (15192, 1850, "getproperty", "_-G6o"),
        (15192, 1882, "callpropvoid", "_-5k, 0"),
        (15192, 1892, "getproperty", "_-z4P"),
        (15192, 4416, "pushbyte", "-1"),
        (15192, 4441, "getproperty", "_-r5B"),
        (15192, 4456, "getproperty", "_-o2O"),
        (15192, 4471, "getproperty", "_-OY"),
        (15192, 4484, "getproperty", "_-84Q"),
        (15192, 4575, "getproperty", "_-x3M"),
        (15192, 4578, "pushbyte", "2"),
    ],
    "_-p5k._-8i mask: soft dropped 64 ms after a throw from a soft line, BoomerangHoming under _-BG, T30": [
        (15192, 826, "pushbyte", "64"),
        (15192, 864, "pushbyte", "2"),
        (15192, 885, "getproperty", "_-z4P"),
        (15192, 935, "getproperty", "_-OY"),
        (15192, 953, "getproperty", "_-T30"),
        (15192, 967, "bitnot", ""),
    ],
    "ItemType columns: Friction 2.5, AirFriction 0.15, Gravity 3.75, ThrownGravity 3.75, PathLength, PathType 1-5; x3M 1.01": [
        (4974, 201, "pushstring", "'AirFriction'"),
        (4974, 223, "initproperty", "_-h5M"),
        (4974, 1312, "pushstring", "'Friction'"),
        (4974, 1332, "initproperty", "_-T2P"),
        (4974, 1341, "pushstring", "'Gravity'"),
        (4974, 1359, "initproperty", "_-84Q"),
        (4974, 3106, "pushstring", "'ThrownGravity'"),
        (4974, 3124, "initproperty", "_-OY"),
        (4963, 263, "pushdouble", "3.75"),
        (4963, 280, "pushdouble", "0.15"),
        (4963, 290, "pushdouble", "2.5"),
        (4974, 1286, "pushstring", "'ForceNoHitstop'"),
        (4974, 1303, "initproperty", "_-T30"),
        (4974, 2120, "pushstring", "'PathLength'"),
        (4974, 2137, "initproperty", "_-G6o"),
        (4974, 2182, "pushstring", "'BoomerangHoming'"),
        (4974, 2213, "pushbyte", "5"),
        (4974, 2235, "pushbyte", "2"),
        (4974, 2257, "pushbyte", "3"),
        (4974, 2279, "pushbyte", "4"),
        (15249, 339, "pushdouble", "1.01"),
        (15249, 342, "initproperty", "_-x3M"),
        (4963, 210, "initproperty", "_-Z5d"),
    ],
    "_-h20 target gates: OnlyStunnedTrigger, _-Io (AllowRepeatedCollision, -1), 400 ms thrower guard, _-I1E": [
        (15239, 526, "getproperty", "_-N59"),
        (15239, 761, "callproperty", "_-5a::_-03K, 0"),
        (15239, 766, "lshift", ""),
        (15239, 776, "getproperty", "_-Io"),
        (15239, 799, "getproperty", "_-A4s"),
        (15239, 816, "pushbyte", "-1"),
        (15239, 875, "pushuint", "400"),
        (15239, 909, "getproperty", "_-W6D"),
        (15239, 967, "pushbyte", "11"),
        (15239, 987, "callproperty", "_-I1E, 1"),
    ],
    "_-h20 contact mask _-x5G: lost -> clear; catch _-J5Z / _-66f; 32 / 64 ms grace; boomerang re-arm _-K3V 500": [
        (15239, 1317, "initproperty", "_-x5G"),
        (15239, 1337, "callproperty", "_-J5Z, 3"),
        (15239, 1365, "callproperty", "_-66f, 2"),
        (15239, 1497, "pushbyte", "64"),
        (15239, 1505, "pushbyte", "32"),
        (15239, 1590, "pushbyte", "1"),
        (15239, 1601, "getproperty", "_-u4B"),
        (15239, 1643, "getproperty", "_-K3V"),
        (15239, 1703, "getproperty", "_-f4i"),
        (15239, 1717, "getproperty", "_-W5n"),
        (15239, 1744, "setlocal", "7"),
        (15249, 533, "pushdouble", "500.0"),
        (4974, 2042, "pushstring", "'OnlyStunnedTrigger'"),
        (4974, 2058, "initproperty", "_-N59"),
        (4974, 233, "pushstring", "'AllowRepeatedCollision'"),
        (4974, 250, "initproperty", "_-A4s"),
    ],
    "_-p5k._-8i sweeps: none under ForceNoGeometryCollision; feet + top (Height) casts excluding item-ignore; ceiling result dropped": [
        (15192, 4705, "getproperty", "_-p2W"),
        (15192, 4813, "getlocal", "6"),
        (15192, 4822, "getproperty", "_-M4J"),
        (15192, 4830, "callproperty", "_-X2e, 13"),
        (15192, 4884, "getproperty", "_-S2O"),
        (15192, 4918, "pushbyte", "1"),
        (15192, 4936, "callproperty", "_-X2e, 13"),
        (15192, 5005, "pushbyte", "-1"),
        (15192, 5174, "getproperty", "_-u4H"),
        (15192, 5377, "getproperty", "_-x3M"),
        (15192, 5544, "callpropvoid", "_-X2e, 13"),
        (15192, 5555, "ifeq", "381"),
        (15192, 6015, "initproperty", "_-96f"),
        (15192, 6290, "callpropvoid", "normalize, 1"),
        (4974, 1261, "pushstring", "'ForceNoGeometryCollision'"),
        (4974, 1277, "initproperty", "_-p2W"),
        (4974, 1393, "pushstring", "'Height'"),
        (4974, 1411, "initproperty", "_-S2O"),
        (15351, 80334, "getproperty", "_-u4H"),
        (15351, 80338, "initproperty", "_-u4H"),
    ],
    "_-p5k._-8i after the sweeps: impact _-u1I when moving (state 0/1 or AlwaysArmed) or on lava, else floor vy = 0; rest at speed^2 <= _-Y3M": [
        (15192, 6912, "getproperty", "_-Lu"),
        (15192, 6964, "pushbyte", "1"),
        (15192, 6980, "getproperty", "_-XJ"),
        (15192, 7000, "callpropvoid", "_-u1I, 2"),
        (15192, 7072, "getproperty", "_-s2O"),
        (15192, 7130, "initproperty", "_-33c"),
        (15192, 7166, "initproperty", "_-B66"),
        (15192, 7176, "initproperty", "_-46m"),
        (15192, 7227, "getproperty", "_-S1A"),
        (15192, 7298, "getproperty", "_-Y3M"),
        (15192, 7314, "initproperty", "_-5T"),
        (15192, 7387, "pushbyte", "5"),
        (15249, 141, "pushint", "2500"),
        (15249, 144, "initproperty", "_-Y3M"),
    ],
    "_-p5k._-u1I impact: stick (StickToWalls, STRICT_ANGLE -0.7237379, FLOORS_ONLY), bounce unless a flat floor and speed < 5": [
        (15194, 720, "getproperty", "_-o1G"),
        (15194, 765, "getproperty", "_-XJ"),
        (15194, 813, "callproperty", "sqrt, 1"),
        (15194, 1106, "getproperty", "_-o1l"),
        (15194, 1187, "pushdouble", "-0.7237379"),
        (15194, 1208, "pushbyte", "2"),
        (15194, 1234, "callproperty", "abs, 1"),
        (15194, 1277, "initproperty", "_-f4i"),
        (15194, 1359, "pushbyte", "-1"),
        (15194, 1368, "pushbyte", "5"),
        (15194, 1415, "callpropvoid", "_-048, 1"),
        (15194, 1501, "initproperty", "_-33c"),
        (15194, 1511, "initproperty", "_-Lu"),
    ],
    "_-p5k._-048 bounce: _-7c (bouncy: (1 + e) / 2), vertical -> Lu, horizontal -> 33c, slope normal x e (1.05 steep) and tangent friction": [
        (15245, 23, "getproperty", "_-B6P"),
        (15245, 46, "pushdouble", "0.5"),
        (15245, 70, "getproperty", "_-J6w"),
        (15245, 157, "initproperty", "_-Lu"),
        (15245, 192, "initproperty", "_-33c"),
        (15245, 203, "getproperty", "_-S1A"),
        (15245, 258, "pushdouble", "1.05"),
        (15245, 433, "getproperty", "_-T2P"),
        (15245, 436, "pushdouble", "1.5"),
        (15245, 474, "callpropvoid", "normalize, 1"),
        (4974, 880, "pushstring", "'Elasticity'"),
        (4974, 897, "initproperty", "_-7c"),
        (4963, 298, "pushdouble", "0.6"),
        (4974, 618, "pushstring", "'STRICT_ANGLE'"),
        (4974, 645, "pushstring", "'FLOORS_ONLY'"),
        (4974, 259, "pushstring", "'AlwaysArmed'"),
        (4974, 276, "initproperty", "_-XJ"),
        (4974, 2997, "pushstring", "'StickToWalls'"),
        (4974, 3014, "initproperty", "_-o1G"),
    ],
}}
