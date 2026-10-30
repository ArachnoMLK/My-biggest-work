"""Motion of thrown items on patch 11.00: the velocity part of `_-p5k._-8i` #15192 (up to the move vector).

See docs/hit-detection-11.00.md, section 8.1. Arithmetic in bytecode order; [V] unless marked [H]. Not here:
the ground walk loop along a line (@1268-1732, the same shape as the fighter's), the path behaviours
(`PathType`, @1901-4344) and the map sweeps after the move vector (@4700-). Static evidence only.
"""
from .movement import ABC_1100

STEP = 0.384            # `_-z2k._-Vj`
DEFAULT_CAP = 350.0     # `_-93n._-Z5d` when 0; `ItemType.<init>` sets 0 and no parser column writes it
GROUND_PUSH = 1.01      # `_-p5k._-x3M` (script822.<init> #15249): the move gets 2 x this on a ground line
SOFT_THROW_MS = 64      # @818-834: soft lines are ignored this long after a throw from a soft platform

# `ItemType.static._-z2u` #4974 column -> field; defaults from `ItemType.<init>` #4963
ITEM_COLUMNS = {"Friction": "T2P", "AirFriction": "h5M", "Gravity": "84Q", "ThrownGravity": "OY",
                "PathLength": "G6o", "PathType": "z4P", "ForceNoHitstop": "T30"}
ITEM_DEFAULTS = {"T2P": 2.5, "h5M": 0.15, "84Q": 3.75, "OY": 3.75, "G6o": 0, "z4P": 0, "T30": False}
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
        elif field == "T30":
            r[field] = v.strip().lower() == "true"
        elif field == "G6o":
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
}}
