# Hit detection — patch 11.00

Which entities a power's hit area touches on one frame. This closes the gap left open in
[knockback-11.00.md](knockback-11.00.md) (PR #29): how the candidate list `_-F5N._-U5S` of
`_-F5N._-T5A` is filled.

Code: [`tools/bh/hitdetect.py`](../tools/bh/hitdetect.py). Check: `python -I tools/bht.py hit-detection-verify`
(380 anchors on ABC, ray cast included `7d308423…`, exit 1 on a mismatch, 2 on another ABC). Tests: `tests/test_hitdetect.py`.
**[V]** = read in the bytecode and pinned by an anchor; **[H]** = interpretation.

## 0. Chain

```text
_-l4X._-R63 #46            power update, once per tick
  for frame in the window _-51i(t) .. + _-R2x(t)      (§1)
    _-l4X._-L5r #65        hit area of that frame, by TargetMethod      (§2)
      _-h3U._-R6C #3538 -> _-h3U._-G2C #3539         every entity, team mask, capsule test   (§3)
        Entity._-N2t #3142 -> _-x3p._-bg #4777       target hurtbox capsule  (§4)
        _-n36._-h2Z #1271 -> _-Q3r._-h2Z #6298       capsule against capsule  (§5)
    -> list _-l4X._-U6i
    _-F5N._-T5A #1731 (17 arguments; arg 7 = that list)
      _-F5N._-U5S = copy of arg 7, arg 7 cleared                            [V]
      for each candidate: direction _-JQ, damage and knockback (knockback-11.00.md)
```

## 1. Frames scanned per update

`_-R63` @2053–2107 loops from `_-V6B._-51i(_-X2G)` for `_-V6B._-R2x(_-X2G)` frames. `_-X2G` is the power's
time [H]. `PowerType._-51i(t)` is `_-q24[t] & 0xFFFF`, and `_-R2x(t)` is `_-q24[t] >>> 16`. With no `_-q24`
table, the result is `t` and 1 [V]. So one update can test several frame indices of the power's lists.
`frame_window` models this.

At each index, `_-L5r` is called when one of these holds [V]:
- the frame is inside `_-B5B` frames of the start;
- `_-I4F` is set;
- the TargetMethod is 2.

The call is `_-L5r(power, _-X2G, index, owner x, owner y, list)`. The owner position is read from the
fighter store `_-Z2G` with the keys `_-M43` and `_-E3d` [V].

### 1.1 Which step fires on which tick ([`tools/bh/power_timeline.py`](../tools/bh/power_timeline.py))

The power is a list of **steps**, one per CastTime entry (`_-a2`, in ticks). `_-l4X._-R63` #46 runs once
per tick. Each call [V]:

1. **Tick number.** It computes `round((t − t mod 16) / 16)`. On the first update (`_-k4b == 0`) it runs
   the start set-up `_-f14`: start tick, then `_-82O = start + CastTime[0]` (entity-step-11.00.md).
2. **Gate.** A step fires only when it is not already running (`_-d38`) and the tick has reached `_-82O`.
   It then sets `_-d38`, and the step's hit detection runs over its frame window (§1).
3. **Advance.** If there is a next step (and, when `_-t3b` is set, the step is below `_-Q1n`), then
   `_-X2G += 1`, `_-82O += max(CastTime[_-X2G], 1)` and `_-d38` is cleared. Otherwise the power stays on its
   last step.
4. **Cancels.** A cancel path (`_-m2j`, gated by MinCancelTime `_-i2o`) can end the power instead. It is
   not modelled.

So **each step fires once**, on the tick it starts. A 0-tick step still takes 1 tick. `_-X2G` is the step
index, which indexes BaseDamage, `_-q24`, CenterOffset and AoERadius [V].

## 2. Hit area of one frame (`_-L5r` #65)

The power's per-frame lists are read at the frame index [V]:

| Column | Field | Use |
|---|---|---|
| CenterOffsetX | `_-T5q` | x offset, negated when the owner faces left (`_-L0`) |
| CenterOffsetY | `_-j4n` | y offset |
| AoERadiusX | `_-a4C` | half width of the area |
| AoERadiusY | `_-W2S` | half height of the area |

The team mask is `_-z2k._-I33` when `_-D6M < 0`, otherwise `_-z2k._-p3C | _-z2k._-V3W`. It becomes 0 when
CanDamageEveryone (`_-g14`) is set [V]. [H]: `p3C` = enemies, `I33` = allies, `V3W` = an extra filter flag.

The point is `_-H2U` when set, otherwise the owner position. Then a `lookupswitch` on `_-g4i` (TargetMethod)
decides what to do [V]:

| `_-g4i` | TargetMethod strings (parser #6483 @8709–9845) | Query |
|---|---|---|
| 0 | (missing) | list cleared |
| 1 | SmashRelease, PBAoE, PBAoEHB, Grab | area at owner + offset |
| 2 | Ranged, GrabHit, GrabRelease, GroundCheckGrabHit | list = [`_-x4I`] (held object) |
| 3 | Path | area at the point, no offset |
| 4 | Self | list = [owner] |
| 5 | RangedAoE, RangedGrab, PathExplosion | area at point + offset |
| 6 | GroundPound, GroundPoundHB, GroundCheck | area at owner + offset |
| 7 | GroundPoundRecover | list cleared |
| 8 | Smash, SmashGrab | area at owner + offset |
| 9 | MeteorGrab, MeteorPound | area at owner + offset |
| 10 | MeteorPoundRelease | area at owner + offset |
| 11 | ThrownItem | list = [`_-x4I`] |
| 12 | Nobody, Taunt, TauntRelease, TeamTaunt(Release), AssistTaunt(Release), UITauntOverride | list cleared |
| 13 | Collider | area at point + offset[index] − offset[current], only when index ≠ current frame |
| 14 | Stance | area at owner + offset |

A leading `SmashRelease` sets `_-w46` and is stripped before matching. On its own it gives 1 [V].

The other flags these strings set (`_-ZR`, `_-K2s`, `_-u3H`, `_-H8`, `_-o5W`, `_-I4F`, …) are not modelled.

Local data check (aggregate counts only, no values published): every TargetMethod cell of the 3,768 powers
maps to a known value:

| Query | Powers |
|---|---|
| area at owner + offset | 1,971 |
| list cleared | 904 |
| area at point + offset | 452 |
| held object | 279 |
| area at the point | 107 |
| Collider | 34 |
| Self | 21 |

So the attack hit area is the **AoE capsule of the power data**, not the animation's hitboxes [V for the
code path; H that no other path adds candidates for these powers].

## 3. Entity loop (`_-h3U._-G2C` #3539)

The loop goes over every entity of `_-5r`.

**Team filter.** The candidate counts as an opponent when [V]:
- there is no owner;
- or its team `_-25G` differs from the owner's;
- or it is another entity of the same team and `_-d3Y._-Z2Y & 2` is set (@218–262). [H]: friendly fire.

The owner itself never counts as an opponent. The mask bits then decide [V]:
- `p3C` keeps opponents;
- `I33` keeps non-opponents;
- no bit set keeps everyone.

Then one of the following must hold for the entity:
- `_-94F`: `_-55E`;
- `_-34m`: `_-E2I`;
- otherwise: `_-AP(owner, false, V3W)`.

It must also pass a `_-s3D._-H1g._-sZ._-r1o` exclusion [V; meaning H].

**Hit area capsule.** `_-Q3r._-KX(2·rx, 2·ry)` turns the area into a capsule. Then
`Entity._-N2t(cx + p.x, cy + ry + p.y, q.x, q.y, r)` is called. With §5 this gives a capsule centred on
(cx, cy) that fills the 2rx × 2ry box [V].

## 4. Hurtbox of the target (`_-x3p._-bg` #4777)

**Which hurtbox type** (`Entity._-p3N` #3100) [V]:
1. the active power's own hurtbox, `_-24N`. It is set at the power start from column **Hurtbox**
   (`_-c5b`) by name.
2. otherwise, when the fighter touches a wall (`_-r51`, see entity-step-11.00.md), `<Weapon>WallCling`,
   or `UnarmedWallCling`.
3. otherwise `DEFAULT`. Soccer, Volley Battle and Horde use `SoccerBall`, `VolleyBall` and `Horde` for
   some entities.

**Which row.** The animation frame is `_-o3I._-c2l` of the active power, or 0. The row is
`_-P6e[frame] − 1`, where `_-P6e` maps a frame to a row number (1-based) built from the **Frames** column
(1-based Flash frames, "a" or "a-b") [V].

The entry is read through `convert_u`. So a frame with no entry (a hole), a frame past the end, or an
entry of 0 falls back to the `DEFAULT` type [V]. With no Frames list, the row is 0.

**Row lists.** Width `_-Q4m`, Height `_-X5S`, OffsetX `_-C1u` and OffsetY `_-01R` are comma lists. A list
shorter than the row count repeats its first entry [V].

**Capsule.** `x = ex + p.x + OffsetX` (OffsetX negated when facing left) and `y = ey + p.y + OffsetY`, with
`(p, q, r) = KX(Width, Height)`. Unlike the hit area, there is no `+ h/2`. So the hurtbox spans
`[ey + OffsetY − Height, ey + OffsetY]` vertically [V]. The parser's "extends below ground" warning tests
`OffsetY + Height / 2 > 80`, which reads OffsetY as a centre. Only the warning uses that reading; the
collision code does not [V].

Local data check (aggregate):

| | |
|---|---|
| Powers with a Hurtbox name | 2,485 |
| … that resolve to a hurtbox type | 2,482 |
| Hurtbox types | 916 |
| … with no Frames list | 20 |
| … with holes before their first frame (DEFAULT there) | 370 |
| Parse errors | 0 |

## 5. Capsule geometry (`_-Q3r`, #6295–#6299)

**Box to capsule.** `KX(w, h)` [V]:
- `w < h`: r = w/2, p = (0, −r), q = (0, w − h);
- otherwise: r = h/2, p = (−w/2 + r, −h/2), q = (w − h, 0).

**Touch test.** Two capsules (start, segment, radius) touch when [V]:
- their segments cross (`_-R5v`: the usual ua / ub test in [0, 1], computed as `(1/d) · …`, with
  d == 0 counting as no cross);
- or the squared segment distance (`_-rR`, the smallest of the four endpoint-to-segment distances from
  `_-w5n`) is ≤ (ra + rb)².

The Python keeps the bytecode's order of operations.

## 6. Re-hit rule (`_-T5A` #1731, `_-R63` #46, `_-v57`)

Each power keeps a hit record `_-G6N`, a `_-v57` with entity ids `_-x3r` and times `_-E5Y` [V]:
- `Set(id, t, overwrite)` appends a new id, and replaces the time of a known id only when `overwrite`;
- `_-168(id)` returns the stored time, or 0.

**Skip.** Before a candidate is processed, `_-T5A` skips it when its id (`_-03K()`) is in the record and
either [V]:
- MinTimeBetweenHits (`_-ue`) is 0: one hit per target per cast;
- or `last + _-ue > now` (argument 2): the target can be hit again `_-ue` after the last hit.

The test is @321–413 for Entity targets and @652–744 for the others.

**Accept.** Accepted targets are pushed back into the list (argument 7), which `_-T5A` cleared at the
start. Its return value counts them; grabs (`_-K2s`) on some targets are written straight into the record
instead [V].

**Record.** After the pass, `_-R63` @2433–2547 stores every target left in the list with
`Set(id, now, true)`, when all of these hold [V]:
- the count is not 0;
- IsMultihit (`_-s5N`) is false, or `_-ue != 0`;
- `_-l4X._-T49()` is true.

`_-T49` is true when:
- `_-538` or `_-w4x` is non-zero;
- or else the BaseDamage list `_-L69` has a non-zero entry at `_-X2G`;
- or else `_-X2G` is past the end of `_-L69` and `_-D6M != 0`.

With no list it is false [V]. Since `_-T49` indexes BaseDamage with `_-X2G`, `_-X2G` is a step index of
the power, not a time [H]. The unit of `now` (argument 2 of `_-R63`) is open [H: ms].

So a non-multihit power with no MinTimeBetweenHits hits each target at most once per cast. A multihit power
without `_-ue` records nothing here, and hits again on every frame where its area touches.

## 7. Line of sight (`_-T5A` @1115–2710)

A target inside the area is still skipped when map geometry blocks it. The source S is argument 5 of
`_-T5A`, or argument 6 for Collider. The target centre T is `_-W3o`. Each ray goes through
`_-N1k._-b1x._-X2e`, the map ray cast, which is not transcribed here. Its mask is `_-z2k._-M4J` when
`_-l4X._-A3S` is set, otherwise 0. The tries run in this order, each one only while the target is still
blocked [V]:

1. **S → T.** Flags (1|2, 1|2|8). The target is blocked when all of these hold:
   - the power does not skip the test (`_-x28`);
   - the ray hits something;
   - the hit's `type` is not 2.

   The parser sets `_-x28` for TargetMethod 2, 3 and 11 (Ranged, Path, ThrownItem), and later overrides it
   for some powers by name.
2. **Detour through (Sx, Sy ± 100).** The sign follows `Ty − Sy`. Both legs use flags (1, 8). This try is
   skipped for CannotAttackAroundCorners (`_-y2`).
3. **Detour through (Sx ± 100, Sy).** Same condition as step 2.
4. **Rays to the hurtbox edges.** Straight rays to `(Tx, Ty − q.y/2)`, `(Tx, Ty + q.y/2)`,
   `(Tx − q.x/2, Ty)` and `(Tx + q.x/2, Ty)`, where q is the target hurtbox segment vector (`_-w2s`, `_-S2O`).

**Result.** A blocked Entity target is skipped, except in Volleyball when `_-s3D._-H1g._-06A._-Z3E(_-11)`
holds. A blocked non-Entity target is always skipped. Then `Entity._-AP(owner, _-f3B)` must hold;
otherwise `_-W1G(power, target, true)` runs and the target is skipped [V].

`line_of_sight_blocked` takes the ray cast as a callback. `map_ray(lines, team, item_ignore)` builds that
callback over map lines with the ray cast of §7.1.

### 7.1 The map ray cast (`_-CX._-X2e` #1581, [`tools/bh/raycast.py`](../tools/bh/raycast.py))

Line flags and the candidate order (grid cells of 100, then dynamic lines) are in
collision-11.00.md (PR #20). `ray_cast` takes the candidates already in that order.

**Arguments as `_-T5A` uses them.**

| Parameter | Value |
|---|---|
| 1 (owner) | the attacker's team `_-25G`, compared with the line owner `_-r1H` |
| 9 (mask) | 1 \| 2 on the first ray (hard and soft lines), 1 on the others (hard only) |
| 10 (options) | 1 \| 2 \| 8 on the first ray, 8 on the others |
| 12 (excluded) | item-ignore (32) when `_-A3S` is set |

The options [V]:
- 1: soft lines block from both sides;
- 2: skip lines that have an owner;
- 8: two-sided;
- 4: drops some results at the end.

**Per candidate.** In order, a line is skipped when [V]:
- it fails the mask;
- it is disabled;
- it belongs to the owner;
- it has an excluded flag;
- option 2 is set and the line has an owner;
- it is the ignored line;
- the hard-then-soft floor exception applies.

With none of the options 8, 4 and 1, a line with a normal is passed through when the motion goes the way
its normal points (it is left through its back). A soft line is skipped from its negative side (`_-PK`)
when the mask includes soft and option 1 is clear.

**Side and hit.** `_-PK` #1017 computes the unit normal `(−dy, dx) · (−1/|d|)` and the side
`(p − s) · n`. `_-R5v` then tests the line against the ray, which is shortened to each hit point. So the
result is the nearest line, and on equal distances the later candidate wins.

So the first straight ray of the line of sight sees soft platforms from both sides. A soft line of type
exactly 2 does not block, because only `type != 2` counts. Bouncy soft (66) and soft pressure plates (258)
do block [V; the effect in game is H]. The detour and edge rays only see hard lines.

### 7.2 Map lines and the candidate grid ([`tools/bh/level_collision.py`](../tools/bh/level_collision.py))

**One collision element.** `_-139._-J1j` #5295 turns one element into lines [V]:
- `X` / `Y` set both ends. Otherwise `X1` and `X2` (`Y1` and `Y2`) are used only when both exist; a
  missing pair stays 0.
- The ends are swapped so that start.x ≤ end.x.
- The element name gives the type flags (table of PR #20). `Flag` goes to `_-Z2Y` through `_-R15._-c1N`.
  `Team` becomes the line owner `_-r1H`, which the ray cast compares with the attacker's team.
- With `AnchorX` and `AnchorY`, `_-l49._-d1H` #1594 builds a quadratic curve. It has n straight lines,
  n = round(Manhattan size / 125) clamped to 4..10, each oriented left to right, with no normal.
- Otherwise there is one `_-R15(start, end, type, flag, team)`. It gets a normal only when `NormalX` or
  `NormalY` is present (the missing one is 0), normalised by `_-q3q`. `_-q3q` also sets `_-S1A` when
  `ny < 0` and `|nx / ny| ≥ 5/3`.

**The grid.** Static lines go into a grid of 100-unit cells (`_-43i` → `_-CX._-u2z` #1585). Each line is
appended to the bucket of every cell its segment crosses, in the cell order of `_-A6B._-t2D` #1028:
- the segment is made shallow, oriented left to right, and mirrored when it goes down;
- it is walked column by column, at most one step up per column.

The bucket key is `_-a2E` #1587: `((⌊x+0.01⌋·0.01 + 16000) << 16) | (⌊y+0.01⌋·0.01 + 16000)`.

Lines inside `DynamicCollision` and `MovingPlatform` blocks go to the dynamic list instead (`_-Z2B`).
`_-936` #1582 gathers the candidates of a ray: the buckets of the cells the ray crosses, then every
dynamic line. There is no de-duplication and no sort [V]. `map_ray` accepts a `Grid` and gathers the
candidates per ray the same way.

**Default normals.** Most lines have no normal in the file. When the level is set up (`_-139._-c6s` →
`_-a2j._-u8(W, H)` #5222), every line still without one gets one, static lines first, then dynamic ones.
W × H is the box around every line (`_-43i` bounds, started at ±MAX_VALUE in `_-y39`) [V]:
- a trigger line gets (0, 0);
- otherwise the start is n = (|Δy|, |Δx|);
- a soft line points up (y negated; x negated when its end is higher than its start);
- a hard line casts one ray from its midpoint, snapped to `v + 5 − v mod 10`: to the right (W + 10) when it
  is vertical, down (H + 10) otherwise. The ray is two-sided and sees hard lines only, ignores the line
  itself, and counts every line it crosses. The parity of that count flips the normal so that it points
  out of the solid (vertical: odd → x negated; otherwise, by the slope, y or x negated);
- the normal is then normalised (`_-q3q`).

`compute_normals` transcribes it. Local check: on the 122 maps, the flat hard lines without a normal get
296 "up" (tops of blocks) and 271 "down" (undersides), with 0 errors.

Local check (aggregate): the 122 LevelDescs parse with no error. They give 1,747 static lines, 61 of
them with a normal. That file order is the game's insertion order is [H].

### 7.3 Moving platforms and dynamic lines ([`tools/bh/platforms.py`](../tools/bh/platforms.py))

**Key frames.** `_-139._-Jb` #5298 walks the `Animation` of a `MovingPlatform` [V]:
- each `KeyFrame` becomes `_-A2j(x, y, frame, rotation, centre, cx, cy, easeIn, easeOut, power, respawnOff)`
  (#6029). Missing attributes take the Animation's values; the default EasePower is 2. The frame is
  `FrameNum` (default 0) plus the Phase start.
- a `Phase` walks its children with its `StartFrame`. When its first key frame starts later than the Phase
  and differs from the previous key frame, a hold of the previous one at the Phase start is inserted
  (`_-yo`).

**One point per frame.** `_-Y61` #5299 builds one point per frame [V]:
- frames are numbered from 1;
- key frame i runs until the next key frame's frame; the last one wraps to the first, until
  NumFrames + 1 (NumFrames defaults to the LevelDesc's, else 0);
- progress is linear `(f − f0)/(f1 − f0)`, or eased by `_-A6B._-D2g` #1131 (EaseIn, EaseOut, both = in-out,
  power 2 quadratic, otherwise power p);
- with a centre, the platform follows an arc between axis-aligned angles (0, π/2, π, 3π/2, 2π). The radii
  are `|x0 − x1|` and `|y0 − y1|`. It uses `_-K6l` / `_-b4l`: cos / sin of the angle reduced to [0, 2π),
  each rounded to 1/1000;
- each point is rounded to 1/100, then the platform X / Y offset is added [H: X / Y of the MovingPlatform
  element, passed as the sprite position].

**Time → position.** `_-V39` #6016 gives the frame
`StartFrame + ((t − n4k)·0.05 mod (1000·n/60·SlowMult)) / period · n`. SlowMult defaults to the LevelDesc's,
else 1. `_-I4v` #6018 blends point k and point k + 1, modulo n [V].

**Lines.**
- `DynamicCollision` children get the block's X / Y added at parse time (`_-J1j` arguments 2–3).
- `_-D19` #6027 stores each line's offset from the platform's first point.
- Each update, `_-Y3I` #6014 keeps the old start in `_-X1H` / `_-q1k` (the `_-X1H` of the ray-cast floor
  exception), then puts the line at offset + position. It is called from `_-p4E._-d4u` for every platform
  [V].
- A block whose PlatID has no animated platform does not move. That the link is by PlatID is [H].

Local check (aggregate): all 122 LevelDescs give 173 platforms and 0 errors. One file lacks a space between
two attributes, which the game's reader accepts; the parser accepts it too.

## 8. Thrown items and projectiles (`_-p5k`)

Thrown weapons and projectiles are `_-p5k` objects (148 instance traits), not powers. Each update,
`_-p5k._-h20` #15239 runs these steps [V]:

1. **Early exits.** It returns early in states `_-5T` 5 and 7, and when the item type `_-93n` has none of
   `_-o3Y`, `_-64N`, `_-n2m`.
2. **Broad query.** `_-R6C` around the item, with half sizes **1050 × 1050** (@492, @623). The mask is
   `_-34m`, or `_-p3C | _-34m`, depending on a timing flag (@419–571).
3. **Fine test.** For each candidate other than the item itself, the item capsule is tested against
   the candidate (`candidate._-N2t`). The capsule starts at (x + `_-86n`.x, y + `_-86n`.y), with segment
   `_-CB` and radius `_-SW`. While the item is held as a power (`_-gT`), the holder's hurtbox is used
   instead.
4. **Swept test.** When the fine test misses, a swept capsule from the previous position (`_-X2D`,
   `_-14l` − h/2) to the current one is tried, with radius min(w, h)/2 of the item type (@1234–1282). A
   fast item cannot pass through a target between two ticks.
5. **Per-target gates.** Gates per target run on the bit `1 << _-03K()` of `_-Io` / `_-x5G`. They
   involve:
   - catch windows `_-O13 + 400`;
   - 32 or 64 ms depending on whether the item moves mostly along x (`_-Lu`) or y (`_-33c`);
   - `_-K3V`, `_-J5Z`, `_-66f`, `_-I1E`.

   These are read but **not transcribed** [V shape; meanings H].
6. **Hit.** The last target that passes is handed to `_-Q3h(t, holder, target)` (@1792). That calls
   `_-R58` (#15230 @242), which spawns a power of the thrower with `_-F5N._-q5` (#15209 @1829). `_-q5`
   builds a new `_-l4X` with **`_-x4I = the hit target`** and `_-A3S = true`, adds it to `_-pX` and runs
   `_-R63` once (#1702).

So for TargetMethod 2 / 11 (Ranged, ThrownItem), §2's "list = [`_-x4I`]" means the power hits exactly the
target the item touched. `_-A3S` makes the line of sight ignore item-ignore lines (§7.1).

## 9. Where this runs in a tick

The order of one 16 ms tick is in tick-loop-11.00.md (scheduler `_-h3U._-01I` #3336). The pieces of this
document sit in it as follows [V]:

| Step in #3336 | What runs | This document |
|---|---|---|
| 3 (@2654) | `_-22K._-d4u(t)`, only while `_-vs == 0`: every moving platform `_-Y3I`, so its lines move | §7.3 |
| 5 (@2751) | every `Entity._-k5H(t)`: inputs, state, movement, map collision | — |
| 6 (@2802) | every `Entity._-10(t)` → `_-Kc._-n2B` (#2990 @98 / @124) → `_-F5N._-h1T` (#1688 @43) → `_-l4X._-R63` (#1742 @227): hit areas, line of sight, re-hit rule; `_-T5A` → `Entity.OnHit` **queues** a hit record in `_-26u._-T4G` (#3042 @179–184) | §1–§7 |
| 7a (@2824) | `_-3z._-s4H(t)`: every item `_-p5k._-h20` | §8 |
| 7b (@2836) | `_-32h._-d3s(t)`: the queue `_-T4G` is read (#1665 @2024) and each hit goes to `_-26u._-76s` (damage, knockback) | knockback-11.00.md |

Consequences:
- **Hits are applied after every entity has attacked.** Hits are only queued in step 6 and applied in
  step 7b, so two fighters can hit each other in the same tick [V].
- **Hit tests see the positions after movement.** Movement runs in step 5, hit tests in step 6, and both
  run in `_-5r` order [V]. The platforms have already moved in step 3.
- **Mud splash.** `Entity._-8i` #2984 also calls `Entity.OnHit` directly in step 5 (@6522–6597). The
  power is `PowerType._-h1r`, which `PowerType.static._-B6` #6482 sets to the power named `MudSplash`
  (@3116–3126). It fires once while `_-k2j == 0`, which then holds the time. The attacker is `_-W6D` (the last
  attacker, when 1–15) or the fighter itself. Its X velocity is scaled by `_-I1f._-X4E` just before [V].
  [H] The trigger is contact with mud (`MudCollision`); the gate before @5961 is not read.

## 10. Still open

- Platform rotation (`_-o2k` is computed but not applied to lines here), when `_-p4E._-d4u` runs inside a tick,
  and curves inside a DynamicCollision block (offset of the anchor) [H].
- The other guards at the top of `_-T5A` (`_-i4o` HoldHitEnts with `Entity._-b2C`, `_-u3H` against
  Uninterruptable `_-C5G`, `_-hQ` / `_-72e`). The order of the list follows `_-5r` [H].
- `_-B5B`, the meaning of `_-q24`, and the exact gate on `_-L5r` per frame (§1); the cancel path of §1.1.
- The other filters of §3 (`_-55E`, `_-E2I`, `_-AP`, `_-r1o`).
- Items: the per-target gates of §8 step 5, the item's own motion and map collision (`_-p5k._-8i` uses
  `_-X2e`), and the other spawners `_-F5N._-33h` (15 callers) and `_-p5k._-u1I`.
- Nothing has been checked against a running game. The next step towards the KO oracle
  (oracle-ko.md) is one scripted exchange: a hit, its knockback, then a ring-out.
