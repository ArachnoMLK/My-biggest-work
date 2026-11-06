"""Horizontal movement of a fighter on patch 11.00: max speed, friction, acceleration (`Entity._-8i` #2984).

See docs/horizontal-11.00.md (PR #23), which first read these parts, and docs/hit-detection-11.00.md §7.4.
Arithmetic in bytecode order; [V] unless marked [H]. `_-v1D` is the horizontal speed; one tick applies the
friction first (linear, clamped at 0), then the acceleration toward the held direction, clamped at the max
speed only when the fighter was below it. Static evidence only.
"""
from .movement import ABC_1100

STEP = 0.384                  # `_-z2k._-Vj`
DASH_WINDOW_MS = 640          # @828: `_-26T` + 640 >= t
DASH_FRICTION_AIR = 3.534     # @889
DASH_FRICTION_GROUND = 5.655  # @899, @1019
POWER_FRICTION = 4.013        # @956
HITSTUN_FRICTION = 4.0        # @1050
SURFACE_FRICTION_ALONG = 9.0  # @1141, @1226
SURFACE_FRICTION = 3.25       # @1235
W47_BOOST = 1.16              # @547
MODE_BOOST = 1.25             # @2038, @2047
AIR_REVERSAL_SPEED = 50.0     # @2346


def max_speed(run_speed, air_run_speed, airborne, k04k=1.0, ku5j=1.0, w47=False):
    """@519-615: RunSpeed x `_-Kc._-04K` (x 1.16 with `_-w47`) on the ground, AirRunSpeed x `_-Kc._-u5j` in
    the air (`_-wn()`)."""
    ground = run_speed * k04k * W47_BOOST if w47 else run_speed * k04k
    air = air_run_speed * ku5j
    return air if airborne else ground


def friction_value(t, airborne, friction, air_friction, dash_timer=0, power=None, hitstun=False,
                   surface=None, vx=0.0):
    """@802-1236: the friction F (the last rule that applies wins).

    `dash_timer` is `_-26T`; `power` is None or a dict with `7E` (`_-o3I._-7E`) and `y25`
    (`_-o3I._-V6B._-y25`); `surface` is None or the bits `_-R5q._-66U` when `local8` holds [H: `_-H6t()`].
    """
    dash = dash_timer != 0 and dash_timer + DASH_WINDOW_MS >= t
    f = air_friction if airborne else friction
    if dash:
        f = DASH_FRICTION_AIR if airborne else DASH_FRICTION_GROUND
    if power is not None:
        if not airborne and power.get("7E"):
            f = POWER_FRICTION
        elif power.get("y25"):
            f = DASH_FRICTION_GROUND if dash else friction
    if hitstun:
        return HITSTUN_FRICTION
    if surface is not None:
        if vx >= 0 and surface & 4 and not surface & 8:
            return SURFACE_FRICTION_ALONG
        if vx <= 0 and surface & 8 and not surface & 4:
            return SURFACE_FRICTION_ALONG
        return SURFACE_FRICTION
    return f


def apply_friction(vx, f):
    """@1240-1340: |vx| loses F x 0.384, clamped at 0 (the sign is kept)."""
    s = 1.0 if vx > 0 else -1.0
    v = s * vx - f * STEP
    if v < 0:
        v = 0
    return v * s


def acceleration(airborne, accel, air_accel, ke16=1.0, kr4i=1.0, mode_boost=False, vmax=0.0):
    """@1928-2052: (accel, max): Acceleration x `_-Kc._-E16` on the ground, AirAcceleration x `_-Kc._-R4I` in
    the air; both x 1.25 when the mode hook `_-m47._-43P(t, this)` is true."""
    a = air_accel * kr4i if airborne else accel * ke16
    if mode_boost:
        a, vmax = a * MODE_BOOST, vmax * MODE_BOOST
    return a, vmax


def reversal_factor(vx):
    """@2329-2396: the air acceleration against the current motion is scaled by max(1 - |vx| / 50, 0)."""
    r = vx / AIR_REVERSAL_SPEED
    if r < 0:
        r = r * -1
    f = 1.0 - r
    if f < 0.0:
        f = 0.0
    return f


def apply_acceleration(vx, left, accel, vmax):
    """@2398-2648: toward the held side (`_-141()` = left), only while below the max, clamped at it."""
    if left:
        if vx > -vmax:
            vx = vx - accel * STEP
            if vx < -vmax:
                vx = -vmax
    elif vx < vmax:
        vx = vx + accel * STEP
        if vx > vmax:
            vx = vmax
    return vx


ANCHORS = {ABC_1100: {
    "_-8i max speed: RunSpeed _-M1U x _-04K (x 1.16 under _-w47), AirRunSpeed _-z2v x _-u5j in the air": [
        (2984, 523, "getproperty", "_-w47"),
        (2984, 534, "getproperty", "_-M1U"),
        (2984, 543, "getproperty", "_-04K"),
        (2984, 547, "pushdouble", "1.16"),
        (2984, 577, "getproperty", "_-z2v"),
        (2984, 586, "getproperty", "_-u5j"),
        (2984, 597, "callproperty", "_-wn, 0"),
    ],
    "_-8i friction: AirFriction / Friction, dash 640 ms 3.534 / 5.655, power 4.013 / y25, hitstun 4.0, surface 9.0 / 3.25": [
        (2984, 782, "callproperty", "_-E6P, 0"),
        (2984, 807, "getproperty", "_-26T"),
        (2984, 828, "pushuint", "640"),
        (2984, 854, "getproperty", "_-h5M"),
        (2984, 865, "getproperty", "_-T2P"),
        (2984, 889, "pushdouble", "3.534"),
        (2984, 899, "pushdouble", "5.655"),
        (2984, 948, "getproperty", "_-7E"),
        (2984, 956, "pushdouble", "4.013"),
        (2984, 1004, "getproperty", "_-y25"),
        (2984, 1019, "pushdouble", "5.655"),
        (2984, 1041, "callproperty", "_-5q, 0"),
        (2984, 1050, "pushdouble", "4.0"),
        (2984, 1099, "getproperty", "_-66U"),
        (2984, 1141, "pushdouble", "9.0"),
        (2984, 1226, "pushdouble", "9.0"),
        (2984, 1235, "pushdouble", "3.25"),
    ],
    "_-8i friction application: s = sign(vx), v = s vx - F x _-Vj, clamped at 0, vx = v s": [
        (2984, 1263, "pushdouble", "1.0"),
        (2984, 1270, "pushdouble", "-1.0"),
        (2984, 1301, "getproperty", "_-Vj"),
        (2984, 1314, "ifnlt", "5"),
        (2984, 1340, "callpropvoid", "_-N5C::_-E1t, 2"),
    ],
    "_-8i acceleration: AirAcceleration _-i3E x _-R4I / Acceleration _-m3Q x _-E16; x 1.25 under _-43P; air reversal max(1 - |vx| / 50, 0)": [
        (2984, 1943, "getproperty", "_-i3E"),
        (2984, 1952, "getproperty", "_-R4I"),
        (2984, 1964, "getproperty", "_-m3Q"),
        (2984, 1973, "getproperty", "_-E16"),
        (2984, 2026, "callproperty", "_-43P, 2"),
        (2984, 2038, "pushdouble", "1.25"),
        (2984, 2047, "pushdouble", "1.25"),
        (2984, 2318, "getproperty", "_-ud"),
        (2984, 2346, "pushdouble", "50.0"),
        (2984, 2379, "pushdouble", "0.0"),
    ],
    "_-8i acceleration application: _-141 left: vx -= a x _-Vj while > -max, clamp; else += while < max, clamp; _-t1A": [
        (2984, 2402, "callproperty", "_-141, 0"),
        (2984, 2432, "ifngt", "95"),
        (2984, 2478, "getproperty", "_-Vj"),
        (2984, 2527, "callpropvoid", "_-N5C::_-E1t, 2"),
        (2984, 2554, "ifnlt", "94"),
        (2984, 2600, "getproperty", "_-Vj"),
        (2984, 2648, "callpropvoid", "_-N5C::_-E1t, 2"),
        (2984, 2659, "callpropvoid", "_-t1A, 2"),
    ],
}}
