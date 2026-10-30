"""Hit detection on patch 11.00: which entities a power's hit area touches on one frame.

See docs/hit-detection-11.00.md. Chain: `_-l4X._-R63` #46 (power update) -> `_-l4X._-L5r` #65 (hit area of
one frame, per TargetMethod) -> `_-h3U._-R6C` #3538 -> `_-h3U._-G2C` #3539 (loop over entities) ->
`Entity._-N2t` #3142 (hurtbox, `_-x3p._-bg` #4777) -> `_-n36._-h2Z` #1271 -> `_-Q3r` capsule geometry
(#6295-#6299). The candidates end in `_-l4X._-U6i`, which `_-F5N._-T5A` #1731 copies to `_-F5N._-U5S`.

The functions transcribe the arithmetic in bytecode order (AS3 Numbers are IEEE doubles, like Python
floats). Field names are the obfuscated ones; column names come from the power and hurtbox parsers.
Anchors are (method id, offset, opname, operand text as printed by `abc-disasm`). Static evidence only.
"""
from . import air_move, entity_states, level_collision, platforms, power_data, power_timeline, raycast, spawn_bot, anim_frames, items, horizontal, jump
from .movement import ABC_1100, check, listing

# PowerType.static._-A3R #6483 @8709-9845: TargetMethod string -> `_-g4i`. A leading "SmashRelease" sets
# `_-w46` and is stripped; "SmashRelease" alone gives 1. Unknown or missing values keep the default 0.
TARGET_METHOD = {
    "SmashRelease": 1, "PBAoE": 1, "PBAoEHB": 1, "Grab": 1,
    "Ranged": 2, "GrabHit": 2, "GrabRelease": 2, "GroundCheckGrabHit": 2,
    "Path": 3,
    "Self": 4,
    "RangedAoE": 5, "RangedGrab": 5, "PathExplosion": 5,
    "GroundPound": 6, "GroundPoundHB": 6, "GroundCheck": 6,
    "GroundPoundRecover": 7,
    "Smash": 8, "SmashGrab": 8,
    "MeteorGrab": 9, "MeteorPound": 9,
    "MeteorPoundRelease": 10,
    "ThrownItem": 11,
    "Nobody": 12, "Taunt": 12, "TauntRelease": 12, "TeamTaunt": 12, "TeamTauntRelease": 12,
    "AssistTaunt": 12, "AssistTauntRelease": 12, "UITauntOverride": 12,
    "Collider": 13,
    "Stance": 14,
}
SMASH_RELEASE = "SmashRelease"

# `_-l4X._-L5r` #65 @283: lookupswitch on `_-g4i` (cases 0..14, default = clear)
CLEAR, HELD_OBJECT, AREA_AT_POINT, SELF, AREA_AT_POINT_OFFSET, AREA_AT_OWNER, COLLIDER = (
    "clear", "held object", "area at point", "self", "area at point + offset", "area at owner + offset",
    "collider")
QUERY_KIND = {0: CLEAR, 1: AREA_AT_OWNER, 2: HELD_OBJECT, 3: AREA_AT_POINT, 4: SELF, 5: AREA_AT_POINT_OFFSET,
              6: AREA_AT_OWNER, 7: CLEAR, 8: AREA_AT_OWNER, 9: AREA_AT_OWNER, 10: AREA_AT_OWNER,
              11: HELD_OBJECT, 12: CLEAR, 13: COLLIDER, 14: AREA_AT_OWNER}


def target_method(text):
    """(`_-g4i`, `_-w46`) for a TargetMethod cell (#6483 @8719-9841). Flags other than `_-w46` are not modelled."""
    w46 = False
    if text.startswith(SMASH_RELEASE):
        w46 = True
        text = text[len(SMASH_RELEASE):]
        if text == "":
            return 1, True
    return TARGET_METHOD.get(text, 0), w46


def query_kind(g4i):
    """What `_-L5r` does for a `_-g4i` value (default branch: clear the list)."""
    return QUERY_KIND.get(g4i, CLEAR)


def area_center(g4i, owner_x, owner_y, frame, offset_x, offset_y, facing_left, point=None,
                current_frame=None):
    """Centre of the hit area for one frame index, or None when no area query is made (#65 @105-782).

    offset_x / offset_y are the power's CenterOffsetX / CenterOffsetY lists (`_-T5q`, `_-j4n`), indexed by
    `frame`; x is negated when `_-L0` (facing_left) is set. `point` is `_-H2U` (None -> the owner position).
    For Collider (13), `current_frame` is `_-V6B._-51i(time)`; the area is made only when it differs from
    `frame`, shifted back by the offset of `current_frame`.
    """
    kind = query_kind(g4i)
    ox = -offset_x[frame] if facing_left else offset_x[frame]
    oy = offset_y[frame]
    px, py = (owner_x, owner_y) if point is None else point
    if kind == AREA_AT_OWNER:
        return owner_x + ox, owner_y + oy
    if kind == AREA_AT_POINT:
        return px, py
    if kind == AREA_AT_POINT_OFFSET:
        return px + ox, py + oy
    if kind == COLLIDER:
        if current_frame == frame:
            return None
        cx = -offset_x[current_frame] if facing_left else offset_x[current_frame]
        return px + ox - cx, py + oy - offset_y[current_frame]
    return None


def frame_window(q24, time):
    """(first frame index, count) that `_-R63` scans for one update: `_-51i(t)`, `_-R2x(t)` (#6478, #6477).

    `q24` is the power's packed per-time table (low 16 bits = first index, high 16 bits = count); None means
    one frame at index `time`.
    """
    if q24 is None:
        return time, 1
    v = q24[time]
    return v & 0xFFFF, (v & 0xFFFF0000) >> 16


def capsule_of_box(w, h):
    """`_-Q3r._-KX(w, h, p, q)` #6299: a w x h box turned into a capsule. Returns (p, q, r): offset of the
    segment start from the anchor, segment vector, radius (min(w, h) / 2). Placed at an anchor, the capsule
    spans x in [-w/2, w/2] and y in [-h, 0]; hit_capsule adds h/2 to centre it, hurtbox_capsule does not.
    """
    if w < h:
        r = w * 0.5
        return (0, -r), (0, -h + w), r
    r = h * 0.5
    return (-(w * 0.5) + r, -(h * 0.5)), (w - h, 0), r


def hit_capsule(cx, cy, rx, ry):
    """Hit area capsule of `_-G2C` #3539 @401-495: box 2rx x 2ry centred on (cx, cy).

    Returns (x, y, dx, dy, r) = segment start, segment vector, radius.
    """
    (px, py), (qx, qy), r = capsule_of_box(rx + rx, ry + ry)
    return cx + px, cy + ry + py, qx, qy, r


def hurtbox_capsule(ex, ey, width, height, offset_x, offset_y, facing_left):
    """Hurtbox capsule of `_-x3p._-bg` #4777 @137-325 for one hurtbox row.

    x = ex + p.x + OffsetX (negated when facing left), y = ey + p.y + OffsetY: the box spans
    [ey + OffsetY - Height, ey + OffsetY] (no + h/2 term, unlike the hit area).
    """
    (px, py), (qx, qy), r = capsule_of_box(width, height)
    off = -offset_x if facing_left else offset_x
    return ex + px + off, ey + py + offset_y, qx, qy, r


def segments_cross(x1, y1, x2, y2, x3, y3, x4, y4):
    """`_-Q3r._-R5v` #6297: True when segments 1-2 and 3-4 intersect (parallel -> False)."""
    d = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
    if d == 0:
        return False
    inv = 1.0 / d
    ua = inv * ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3))
    ub = inv * ((x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3))
    return ua >= 0.0 and ua <= 1.0 and ub >= 0.0 and ub <= 1.0


def point_segment_dist2(sx, sy, dx, dy, px, py):
    """`_-Q3r._-w5n` #6295: squared distance from (px, py) to the segment (sx, sy) + t (dx, dy)."""
    dot = dx * (px - sx) + dy * (py - sy)
    if dot < 0:
        cx, cy = sx, sy
    else:
        len2 = dx * dx + dy * dy
        if len2 == 0:
            cx, cy = sx, sy
        elif dot > len2:
            cx, cy = sx + dx, sy + dy
        else:
            t = dot / len2
            cx, cy = sx + dx * t, sy + dy * t
    ex, ey = px - cx, py - cy
    return ex * ex + ey * ey


def segment_dist2(ax, ay, adx, ady, bx, by, bdx, bdy):
    """`_-Q3r._-rR` #6296: smallest of the four endpoint-to-segment squared distances."""
    d1 = point_segment_dist2(ax, ay, adx, ady, bx, by)
    d2 = point_segment_dist2(bx, by, bdx, bdy, ax, ay)
    d3 = point_segment_dist2(ax, ay, adx, ady, bx + bdx, by + bdy)
    d4 = point_segment_dist2(bx, by, bdx, bdy, ax + adx, ay + ady)
    if d1 < d2:
        d2 = d1
    if d3 < d4:
        d4 = d3
    if d2 < d4:
        d4 = d2
    return d4


def capsules_touch(a, b):
    """`_-Q3r._-h2Z` #6298 for capsules (x, y, dx, dy, r): crossing segments, or distance <= ra + rb."""
    ax, ay, adx, ady, ar = a
    bx, by, bdx, bdy, br = b
    if segments_cross(ax, ay, ax + adx, ay + ady, bx, by, bx + bdx, by + bdy):
        return True
    rr = ar + br
    return segment_dist2(ax, ay, adx, ady, bx, by, bdx, bdy) <= rr * rr


def hurtbox_frames(frames):
    """`_-P6e` of a hurtbox type from its Frames list (#4780 @649-943), as a list indexed by frame.

    Each entry "a" or "a-b" is 1-based (Flash frames): it covers indices a - 1 (0 stays 0, with a warning)
    up to a (exclusive) or b. The value is the entry's row number (1-based); later entries overwrite
    earlier ones. Indices never written are holes (None here, `undefined` in the game).
    """
    out = []
    for row, item in enumerate(frames, start=1):
        parts = item.split("-")
        start = int(parts[0])
        start = start - 1 if start != 0 else 0
        end = start + 1
        if len(parts) > 1:
            end = int(parts[1])
        for i in range(start, end):
            while len(out) <= i:
                out.append(None)
            out[i] = row
    return out


def hurtbox_row(p6e, frame):
    """Row of the hurtbox lists used by `_-x3p._-bg` (#4777 @17-135) for animation frame `frame` (`_-c2l`).

    No Frames list (`_-P6e` null): row 0. Frame past the end of `_-P6e`, or entry 0: None, meaning the
    DEFAULT hurtbox type is used instead. Else `_-P6e[frame] - 1`. The entry is read through `convert_u`
    (@64), so a hole (undefined) counts as 0 and also gives the DEFAULT hurtbox.
    """
    if p6e is None:
        return 0
    if frame >= len(p6e) or not p6e[frame]:
        return None
    return p6e[frame] - 1


def row_values(values, row):
    """List entry `row`, or entry 0 when the list is shorter (#4780 @1250-1397)."""
    return values[row] if row < len(values) else values[0]


class HitRecord:
    """`_-v57` (#93-#103): ids `_-x3r` and times `_-E5Y` of the entities a power already hit."""

    def __init__(self):
        self.ids, self.times = [], []

    def set(self, ent_id, time, overwrite):
        """`Set` #95: append a new id; for a known id, replace the time only when `overwrite`."""
        if ent_id in self.ids:
            if overwrite:
                self.times[self.ids.index(ent_id)] = time
        else:
            self.ids.append(ent_id)
            self.times.append(time)

    def last(self, ent_id):
        """`_-168` #101: time stored for an id, 0 when absent."""
        for i, e in enumerate(self.ids):
            if e == ent_id:
                return self.times[i]
        return 0


def rehit_blocked(record, ent_id, min_time_between_hits, now):
    """`_-T5A` #1731 @321-413 (Entity) and @652-744 (other targets): skip a target the power already hit,
    unless MinTimeBetweenHits (`_-ue`) is non-zero and `last + _-ue > now` is false. No record: not blocked.
    """
    if record is None or ent_id not in record.ids:
        return False
    if min_time_between_hits == 0:
        return True
    return record.last(ent_id) + min_time_between_hits > now


def deals_damage(p538, w4x, base_damage, index, d6m):
    """`_-l4X._-T49` #83: whether this power step can record hits. True when `_-538` or `_-w4x` is non-zero;
    else, with a BaseDamage list (`_-L69`), its entry at `index` (`_-X2G`) is non-zero, or past its end
    `_-D6M != 0`; with no list, False.
    """
    if p538 != 0 or w4x != 0:
        return True
    if base_damage is None:
        return False
    if index < len(base_damage):
        return base_damage[index] != 0
    return d6m != 0


def records_after_pass(hits, is_multihit, min_time_between_hits, damage_step):
    """`_-R63` #46 @2433-2547: after `_-T5A` returned `hits` > 0, every target left in the list is stored in
    the power's record `_-G6N` at the current time (overwrite) when (not IsMultihit `_-s5N` or
    MinTimeBetweenHits != 0) and deals_damage.
    """
    return hits != 0 and (not is_multihit or min_time_between_hits != 0) and damage_step


def skips_line_of_sight(g4i):
    """`_-x28` (#6483 @13278-13321): True for TargetMethod 2, 3, 11 (Ranged, Path, ThrownItem). The parser
    later overrides it for some powers by name (not modelled)."""
    return g4i in (2, 3, 11)


ITEM_QUERY_RADIUS = 1050.0   # `_-p5k._-h20` #15239 @492: half size of the broad area query around an item


def item_capsule(x, y, offset, segment, radius):
    """Capsule of a thrown item or projectile `_-p5k` (`_-p5k._-N2t` #15240 and #15239 @1148-1216):
    start (x + `_-86n`.x, y + `_-86n`.y), segment `_-CB`, radius `_-SW`; (x, y) = (`_-p3V()`, `_-Sb()`)."""
    return x + offset[0], y + offset[1], segment[0], segment[1], radius


def item_swept_capsule(prev_x, prev_y, x, y, item_w, item_h):
    """Fallback test of #15239 @1234-1282 when the item capsule misses: a capsule from the previous position
    (`_-X2D`, `_-14l` - h/2) to the current one (`_-p3V()`, `_-Sb()`), radius min(w, h) / 2, with
    (w, h) = the item type's (`_-93n._-w2s`, `_-S2O`) (@360-417). Catches fast items passing through."""
    half_h = item_h * 0.5
    r = item_w * 0.5 if item_w < item_h else half_h
    return prev_x, prev_y - half_h, x - prev_x, y - prev_y, r


def item_query_mask(l5):
    """Team mask of the item query (#15239 @540-571): `_-34m` alone when the local flag (@419-490) holds,
    else `_-p3C | _-34m`. [H] `_-34m` selects the `_-E2I` check in `_-G2C`."""
    return ("_-34m",) if l5 else ("_-p3C", "_-34m")


def map_ray(lines, team, item_ignore=False):
    """The `ray` callback of line_of_sight_blocked over map lines (a list in candidate order, or a
    level_collision.Grid whose candidates are gathered per ray as `_-936` does), as `_-T5A` calls `_-CX._-X2e`: owner =
    the attacker's team `_-25G`, mask = flags_a, options = flags_b, excluded = `_-z2k._-M4J` (item-ignore, 32)
    when `_-l4X._-A3S` is set, else 0 (#1731 @1115-1270)."""
    excluded = 32 if item_ignore else 0

    def ray(x, y, dx, dy, flags_a, flags_b):
        cands = lines.candidates(x, y, x + dx, y + dy) if hasattr(lines, "candidates") else lines
        hit = raycast.ray_cast(cands, team, x, y, dx, dy, flags_a, flags_b, excluded)
        return None if hit is None else hit.line
    return ray


def line_of_sight_blocked(sx, sy, tx, ty, q_x, q_y, ray, skip=False, around_corners=True):
    """`_-T5A` #1731 @1115-2710: whether map geometry blocks the hit from source (sx, sy) to the target centre.

    `ray(x, y, dx, dy, flags_a, flags_b)` stands for `_-N1k._-b1x._-X2e` (map ray cast, not transcribed);
    it returns None when clear, else an object with `.type`. `q_x`, `q_y` are the target hurtbox segment
    vector (`_-a1E._-w2s`, `_-S2O`). Order of tries, each only while still blocked:
    1. S -> T with flags (1|2, 1|2|8); blocked when not `skip` (`_-x28`), the ray hits and the hit's type != 2;
    2. (not for CannotAttackAroundCorners `_-y2`, i.e. around_corners False) detour through (sx, sy +- 100) (sign of ty - sy), both legs with flags (1, 8);
    3. (same condition) detour through (sx +- 100, sy) (sign of tx - sx);
    4. straight rays to (tx, ty - q_y/2), (tx, ty + q_y/2), (tx - q_x/2, ty), (tx + q_x/2, ty).
    """
    r = ray(sx, sy, tx - sx, ty - sy, 1 | 2, 1 | 2 | 8)
    blocked = (not skip) and r is not None and r.type != 2

    def two_legs(vx, vy):
        if ray(sx, sy, vx - sx, vy - sy, 1, 8) is not None:
            return True
        return ray(vx, vy, tx - vx, ty - vy, 1, 8) is not None

    if blocked and around_corners:
        blocked = two_legs(sx, sy + (100 if ty > sy else -100))
        if blocked:
            blocked = two_legs(sx + (100 if tx > sx else -100), sy)
    hw, hh = q_x * 0.5, q_y * 0.5
    for px, py in ((tx, ty - hh), (tx, ty + hh), (tx - hw, ty), (tx + hw, ty)):
        if not blocked:
            break
        blocked = ray(sx, sy, px - sx, py - sy, 1, 8) is not None
    return blocked


ANCHORS = {ABC_1100: {
    "_-R63: candidates _-l4X._-U6i filled by _-L5r(power, time, frame, x, y, list) then passed to _-T5A": [
        (46, 2112, "getlex", "_-l4X"),
        (46, 2115, "getproperty", "_-U6i"),
        (46, 2221, "getproperty", "_-Z2G"),
        (46, 2226, "getproperty", "_-M43"),
        (46, 2270, "getproperty", "_-E3d"),
        (46, 2281, "callpropvoid", "_-L5r, 6"),
        (46, 2422, "callproperty", "_-T5A, 17"),
        (46, 2067, "callproperty", "_-51i, 1"),
        (46, 2091, "callproperty", "_-R2x, 1"),
    ],
    "_-T5A: _-F5N._-U5S is a copy of argument 7 (the candidate list), which is then cleared": [
        (1731, 107, "getlex", "_-F5N"),
        (1731, 111, "getproperty", "_-U5S"),
        (1731, 117, "initproperty", "length"),
        (1731, 154, "getlocal", "7"),
        (1731, 165, "setproperty", "[rt]"),
        (1731, 181, "initproperty", "length"),
    ],
    "_-L5r: CenterOffsetX/Y _-T5q/_-j4n, AoERadiusX/Y _-a4C/_-W2S at the frame; x negated by _-L0": [
        (65, 31, "getproperty", "_-T5q"),
        (65, 51, "getproperty", "_-j4n"),
        (65, 72, "getproperty", "_-a4C"),
        (65, 92, "getproperty", "_-W2S"),
        (65, 119, "getproperty", "_-L0"),
        (65, 129, "negate_i", ""),
        (65, 274, "getproperty", "_-g4i"),
    ],
    "_-L5r: mask I33 when _-D6M < 0 else p3C | V3W, 0 when CanDamageEveryone _-g14; point _-H2U or (x, y)": [
        (65, 147, "getproperty", "_-D6M"),
        (65, 159, "getproperty", "_-I33"),
        (65, 170, "getproperty", "_-p3C"),
        (65, 176, "getproperty", "_-V3W"),
        (65, 180, "bitor", ""),
        (65, 188, "getproperty", "_-H2U"),
        (65, 253, "getproperty", "_-g14"),
    ],
    "_-L5r cases: held object _-x4I, area at point, self _-pr, point + offset, owner + offset, collider": [
        (65, 382, "getproperty", "_-x4I"),
        (65, 445, "callpropvoid", "_-R6C, 8"),
        (65, 496, "getproperty", "_-pr"),
        (65, 535, "add", ""),
        (65, 555, "callpropvoid", "_-R6C, 8"),
        (65, 582, "add", ""),
        (65, 598, "callpropvoid", "_-R6C, 8"),
        (65, 636, "callproperty", "_-51i, 1"),
        (65, 760, "subtract", ""),
        (65, 773, "subtract", ""),
        (65, 782, "callpropvoid", "_-R6C, 8"),
    ],
    "_-R6C -> _-G2C over every entity _-5r: team _-25G, capsule _-KX(2rx, 2ry), _-N2t(cx + p.x, cy + ry + p.y, q, r)": [
        (3538, 65, "callpropvoid", "_-G2C, 8"),
        (3539, 173, "getproperty", "_-5r"),
        (3539, 232, "getproperty", "_-25G"),
        (3539, 409, "add", ""),
        (3539, 415, "add", ""),
        (3539, 430, "callproperty", "_-KX, 4"),
        (3539, 456, "getlocal", "6"),
        (3539, 458, "add", ""),
        (3539, 495, "callproperty", "_-N2t, 5"),
        (3539, 508, "callpropvoid", "http://adobe.com/AS3/2006/builtin::push, 1"),
    ],
    "_-KX: capsule of a w x h box, r = min(w, h) / 2": [
        (6299, 10, "pushdouble", "0.5"),
        (6299, 42, "getlocal_2", ""),
        (6299, 43, "negate", ""),
        (6299, 56, "pushdouble", "0.5"),
        (6299, 65, "pushdouble", "0.5"),
        (6299, 80, "pushdouble", "0.5"),
        (6299, 93, "subtract", ""),
        (6299, 108, "returnvalue", ""),
    ],
    "Entity._-N2t / _-x3p._-bg: hurtbox row P6e[frame] - 1, Width _-Q4m, Height _-X5S, OffsetX _-C1u (mirrored), OffsetY _-01R": [
        (3142, 9, "getproperty", "_-T3L"),
        (3142, 32, "callproperty", "_-h2Z, 5"),
        (3099, 26, "getproperty", "_-o3I"),
        (3099, 48, "getproperty", "_-c2l"),
        (4777, 64, "convert_u", ""),
        (4777, 77, "getproperty", "_-y2F"),
        (4777, 123, "pushbyte", "1"),
        (4777, 144, "getproperty", "_-Q4m"),
        (4777, 158, "getproperty", "_-X5S"),
        (4777, 182, "callproperty", "_-KX, 4"),
        (4777, 200, "getproperty", "_-C1u"),
        (4777, 211, "negate", ""),
        (4777, 253, "initproperty", "_-J2c"),
        (4777, 277, "getproperty", "_-01R"),
        (4777, 290, "initproperty", "_-b3h"),
        (4777, 305, "initproperty", "_-w2s"),
        (4777, 319, "initproperty", "_-S2O"),
        (4777, 325, "initproperty", "_-y15"),
    ],
    "_-h2Z: segments cross (_-R5v) or segment distance^2 (_-rR) <= (ra + rb)^2": [
        (6298, 37, "callproperty", "_-R5v, 9"),
        (6298, 53, "add", ""),
        (6298, 75, "callproperty", "_-rR, 8"),
        (6298, 90, "multiply", ""),
        (6298, 91, "lessequals", ""),
        (6297, 33, "pushdouble", "1.0"),
        (6297, 98, "pushdouble", "0.0"),
        (6297, 107, "pushdouble", "1.0"),
        (6296, 13, "callproperty", "_-w5n, 6"),
        (6296, 96, "callproperty", "_-w5n, 6"),
        (6295, 29, "multiply", ""),
        (6295, 124, "divide", ""),
        (6295, 177, "returnvalue", ""),
    ],
    "Hurtbox pick (Entity._-p3N): power hurtbox _-24N, wall cling per weapon when _-r51, else DEFAULT": [
        (3100, 66, "getproperty", "_-24N"),
        (3100, 82, "getproperty", "_-r51"),
        (3100, 114, "pushstring", "'UnarmedWallCling'"),
        (3100, 591, "getproperty", "_-y2F"),
        (4779, 186, "pushstring", "'DEFAULT'"),
        (4779, 197, "initproperty", "_-y2F"),
        (59, 146, "getproperty", "_-c5b"),
        (59, 149, "callproperty", "_-i4h, 1"),
        (59, 164, "initproperty", "_-24N"),
    ],
    "Hurtbox parser #4780: Frames 1-based, OffsetX/OffsetY/Width/Height lists, shorter lists repeat [0]": [
        (4780, 340, "pushstring", "'Frames'"),
        (4780, 379, "pushstring", "'OffsetX'"),
        (4780, 412, "setlocal", "4"),
        (4780, 420, "pushstring", "'OffsetY'"),
        (4780, 453, "setlocal", "5"),
        (4780, 461, "pushstring", "'Width'"),
        (4780, 493, "setlocal", "6"),
        (4780, 501, "pushstring", "'Height'"),
        (4780, 534, "setlocal", "7"),
        (4780, 663, "initproperty", "_-P6e"),
        (4780, 803, "decrement", ""),
        (4780, 1401, "getproperty", "_-C1u"),
        (4780, 1415, "getproperty", "_-01R"),
        (4780, 1429, "getproperty", "_-Q4m"),
        (4780, 1442, "getproperty", "_-X5S"),
    ],
    "TargetMethod parser #6483: SmashRelease prefix sets _-w46; values of _-g4i": [
        (6483, 8711, "pushstring", "'TargetMethod'"),
        (6483, 8741, "pushstring", "'SmashRelease'"),
        (6483, 8758, "initproperty", "_-w46"),
        (6483, 8808, "pushstring", "'PBAoE'"),
        (6483, 9001, "pushstring", "'Smash'"),
        (6483, 9011, "pushbyte", "8"),
        (6483, 8851, "pushstring", "'Collider'"),
        (6483, 8860, "pushbyte", "13"),
        (6483, 9529, "pushbyte", "14"),
    ],
    "Re-hit: _-T5A skips ids already in the record _-G6N (_-v57._-x3r) unless _-ue != 0 and last + _-ue <= now": [
        (1731, 344, "getproperty", "_-x3r"),
        (1731, 349, "callproperty", "http://adobe.com/AS3/2006/builtin::indexOf, 1"),
        (1731, 377, "getproperty", "_-ue"),
        (1731, 398, "callproperty", "_-168, 1"),
        (1731, 405, "getproperty", "_-ue"),
        (1731, 408, "add_i", ""),
        (1731, 410, "getlocal_2", ""),
        (1731, 411, "greaterthan", ""),
        (1731, 675, "getproperty", "_-x3r"),
        (1731, 736, "getproperty", "_-ue"),
        (1731, 2861, "callpropvoid", "http://adobe.com/AS3/2006/builtin::push, 1"),
        (95, 32, "callpropvoid", "http://adobe.com/AS3/2006/builtin::push, 1"),
        (95, 71, "setproperty", "[rt]"),
        (101, 77, "returnvalue", ""),
    ],
    "_-R63 after _-T5A: hits != 0 and (not IsMultihit _-s5N or _-ue != 0) and _-T49 -> Set(id, now, true)": [
        (46, 2455, "getproperty", "_-s5N"),
        (46, 2473, "getproperty", "_-ue"),
        (46, 2487, "getlocal", "5"),
        (46, 2540, "callproperty", "_-5a::_-03K, 0"),
        (46, 2547, "callpropvoid", "Set, 3"),
        (83, 15, "getproperty", "_-538"),
        (83, 33, "getproperty", "_-w4x"),
        (83, 60, "getproperty", "_-L69"),
        (83, 122, "getproperty", "[rt]"),
        (83, 145, "getproperty", "_-D6M"),
    ],
    "Line of sight in _-T5A: ray S -> T (1|2, 1|2|8), +-100 detours (1, 8), hurtbox edges q/2; _-x28, _-y2": [
        (1731, 1117, "getproperty", "_-A3S"),
        (1731, 1128, "getproperty", "_-M4J"),
        (1731, 1270, "callproperty", "_-X2e, 12"),
        (1731, 1287, "getproperty", "_-x28"),
        (1731, 1314, "getproperty", "type"),
        (1731, 1318, "pushbyte", "2"),
        (1731, 1336, "getproperty", "_-y2"),
        (1731, 1363, "pushbyte", "100"),
        (1731, 1370, "pushbyte", "-100"),
        (1731, 1593, "callproperty", "_-X2e, 12"),
        (1731, 1742, "pushbyte", "100"),
        (1731, 2106, "getproperty", "_-w2s"),
        (1731, 2109, "pushdouble", "0.5"),
        (1731, 2124, "getproperty", "_-S2O"),
        (1731, 2260, "callproperty", "_-X2e, 12"),
        (1731, 2694, "callproperty", "_-X2e, 12"),
        (1731, 2749, "getproperty", "VOLLEYBALL"),
        (1731, 2834, "callpropvoid", "_-W1G, 3"),
        (6483, 13287, "pushbyte", "3"),
        (6483, 13301, "pushbyte", "11"),
        (6483, 13316, "pushbyte", "2"),
        (6483, 13321, "initproperty", "_-x28"),
    ],
    "Items / projectiles _-p5k._-h20: broad _-R6C 1050, item capsule _-86n/_-CB/_-SW, swept capsule, Q3h -> R58 -> q5 (x4I = target)": [
        (15239, 492, "pushdouble", "1050.0"),
        (15239, 549, "getproperty", "_-34m"),
        (15239, 560, "getproperty", "_-p3C"),
        (15239, 623, "callpropvoid", "_-R6C, 9"),
        (15239, 1135, "callproperty", "_-5a::_-N2t, 5"),
        (15239, 1153, "getproperty", "_-86n"),
        (15239, 1193, "getproperty", "_-CB"),
        (15239, 1213, "getproperty", "_-SW"),
        (15239, 1239, "getproperty", "_-X2D"),
        (15239, 1245, "getproperty", "_-14l"),
        (15239, 1248, "getlocal_3", ""),
        (15239, 1282, "callproperty", "_-5a::_-N2t, 5"),
        (15239, 369, "pushdouble", "0.5"),
        (15239, 1792, "callpropvoid", "_-Q3h, 3"),
        (15240, 79, "callproperty", "_-h2Z, 10"),
        (15230, 242, "callpropvoid", "_-R58, 4"),
        (15209, 1829, "callproperty", "_-q5, 12"),
        (1702, 27, "constructprop", "_-l4X, 7"),
        (1702, 40, "initproperty", "_-x4I"),
        (1702, 52, "initproperty", "_-A3S"),
        (1702, 170, "callpropvoid", "_-R63, 1"),
    ],
    "Place in the tick (#3336): platforms _-d4u, pass 5 _-k5H, pass 6 _-10 -> _-n2B -> _-h1T -> _-R63 (hits queued in _-26u._-T4G by OnHit), pass 7 items _-s4H then queue _-d3s": [
        (3336, 2654, "callpropvoid", "_-d4u, 1"),
        (3336, 2751, "callpropvoid", "_-k5H, 1"),
        (3336, 2802, "callpropvoid", "_-10, 1"),
        (3336, 2824, "callpropvoid", "_-s4H, 1"),
        (3336, 2836, "callpropvoid", "_-d3s, 1"),
        (2990, 98, "callpropvoid", "_-n2B, 1"),
        (2990, 124, "callpropvoid", "_-n2B, 1"),
        (1688, 43, "callpropvoid", "_-h1T, 3"),
        (1742, 227, "callproperty", "_-R63, 1"),
        (3042, 179, "getproperty", "_-T4G"),
        (3042, 184, "callpropvoid", "http://adobe.com/AS3/2006/builtin::push, 1"),
        (1665, 2024, "getproperty", "_-T4G"),
    ],
    "Mud splash: Entity._-8i calls OnHit directly with PowerType._-h1r (MudSplash) while _-k2j == 0": [
        (2984, 6425, "getproperty", "_-k2j"),
        (2984, 6440, "getproperty", "_-W6D"),
        (2984, 6548, "getproperty", "_-h1r"),
        (2984, 6597, "callpropvoid", "OnHit, 17"),
        (6482, 3116, "pushstring", "'MudSplash'"),
        (6482, 3126, "initproperty", "_-h1r"),
    ],
}}


ANCHORS[ABC_1100].update(raycast.ANCHORS[ABC_1100])
ANCHORS[ABC_1100].update(level_collision.ANCHORS[ABC_1100])
ANCHORS[ABC_1100].update(platforms.ANCHORS[ABC_1100])
ANCHORS[ABC_1100].update(power_timeline.ANCHORS[ABC_1100])
ANCHORS[ABC_1100].update(air_move.ANCHORS[ABC_1100])
ANCHORS[ABC_1100].update(power_data.ANCHORS[ABC_1100])
ANCHORS[ABC_1100].update(entity_states.ANCHORS[ABC_1100])
ANCHORS[ABC_1100].update(spawn_bot.ANCHORS[ABC_1100])
ANCHORS[ABC_1100].update(anim_frames.ANCHORS[ABC_1100])
ANCHORS[ABC_1100].update(items.ANCHORS[ABC_1100])
ANCHORS[ABC_1100].update(horizontal.ANCHORS[ABC_1100])
ANCHORS[ABC_1100].update(jump.ANCHORS[ABC_1100])


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


def count(sha):
    """Number of anchors pinned for an ABC."""
    return sum(len(a) for a in ANCHORS[sha].values())
