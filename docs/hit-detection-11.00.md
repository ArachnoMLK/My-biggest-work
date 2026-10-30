# Hit detection — patch 11.00

Which entities a power's hit area touches on one frame. This closes the gap left open in
[knockback-11.00.md](knockback-11.00.md) (PR #29): how the candidate list `_-F5N._-U5S` of
`_-F5N._-T5A` is filled.

Code: [`tools/bh/hitdetect.py`](../tools/bh/hitdetect.py). Check: `python -I tools/bht.py hit-detection-verify`
(760 anchors on ABC, ray cast included `7d308423…`, exit 1 on a mismatch, 2 on another ABC). Tests: `tests/test_hitdetect.py`.
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
4. **End.** Each fired step asks `_-l4X._-O5N` #56 for an end reason (`ends_now`):

   | Code | Meaning |
   |---|---|
   | 5 | not a ground pound or meteor (TargetMethod 6 / 9): nothing to end |
   | 1 | EndOnHit (`_-a3G`) and at least one hit (only reached for TargetMethod 6 / 9, after the 5 test) |
   | 2 | landed on a walkable line (the owner's ground line `_-96f`, or the `_-N20` look-ahead line) |
   | 4 | the ground line is a wall |
   | 0 | continue |

   The power ends (`_-m2j`) on 1, 2 or 4, once MinCancelTime `_-i2o` is 0 or has elapsed [V].

The cap `_-Q1n` comes from the power constructor `_-l4X.<init>` #39 (`step_cap`) [V]. For a charged power
(`_-t3b`) it is `ceil(held / _-I6c × len(CastTime))`, at least `_-L2X`, where held is constructor argument
5, `_-a6i` [H: the charge time]. A longer charge therefore plays more steps. The constructor also sets
`_-qm` = |x speed| / 60, at most 1, when the fighter moves the way it faces (`momentum`).

So **each step fires once**, on the tick it starts. A 0-tick step still takes 1 tick. `_-X2G` is the step
index, which indexes BaseDamage, `_-q24`, CenterOffset and AoERadius [V].

### 1.2 Reading the power data ([`tools/bh/power_data.py`](../tools/bh/power_data.py))

`PowerType.static._-A3R` #6483 turns the powerTypes cells into the per-step lists used above [V]:

**CastTime.** Comma-separated entries:
- `D`, `D@F` or `D:R[@F[-G]]`, where D is a duration in ticks and R adds R extra steps of 0 ticks;
- F and G only feed `_-g1x`, which is not modelled;
- an empty cell counts as "0".

**Related columns** (VariableImpulse, FixedImpulse, AoERadiusX/Y, CenterOffsetX/Y, BaseDamage,
ImpulseOffsetX/Y, FixedStunTime, …) have one cell per CastTime entry, or one cell for all. When AoERadiusY
is empty it uses AoERadiusX. `_-42F` #6484 expands each cell over its entry's steps:

| Cell | Steps get |
|---|---|
| `v` | v on every step |
| `tN` | N / steps each |
| `a\|b` | alternating a, b, … |
| `a~b~c` | linear ranges between the points |
| `a&b` | k simultaneous values (k hitboxes) |

Most of these lists are `Vector.<int>`: values are truncated, and NaN becomes 0.

**Frame windows.** When any cell uses `&`, `_-q24[step] = (k << 16) | first` (`_-v5o` #6463). Every other
step gets a window of 1 at its place in the AoERadiusX list. This is the frame window of §1.

**`_-D6M`.** It is the sum of the BaseDamage expansions. Its sign picks the team mask of §2.

Local check (aggregate): all 3,768 powers parse with no error, and the lists of steps without `&` always
have the CastTime length:

| Powers | Count |
|---|---|
| use `&` | 1,141 |
| use ranges `~` | 258 |
| use totals `t` | 214 |
| use alternation `\|` | 1 |

### 1.3 Animation frame of a power (`_-l4X._-54L` #86, [`tools/bh/anim_frames.py`](../tools/bh/anim_frames.py))

The start set-up `_-f14` #59 calls `_-54L` once. It builds `_-cA`, a sparse table from ticks since cast to
an animation frame [V]. Each update, `_-o4b` #45 reads `_-cA[tick − _-k4b]`. When that entry exists and is
> 0, it becomes `_-c2l`, the frame that picks the target's hurtbox row (§4). Between entries, `_-c2l` keeps
its value [V].

**Inputs** [V]:
- **Key frames** `_-942`. Each entry is `frame << 16 | step` (`PowerType._-g1x` #6462). The step is read by
  `_-y2b` and the frame by `_-P5A` (bits 16–27). An end key also has `0xF0000000` set, and `_-P5A` then adds
  0.99. The keys come from CastTime markers (`_-A3R` @11337–11696). With s = index of the entry's first step:
  - "D@F" gives (s, F);
  - "D:R@F" gives (s, F);
  - "D:R@F-G" gives (s, F), then the end key (s + R, G).

  A key with step < 0 or frame <= 0 is skipped.
- **CastAnim** "FLAGS:Name". The name goes to `_-94J._-HT`, and the flags are letters: "L" sets `_-6b`,
  "R" `_-9v`, "F" `_-JL`. With "L", and when the fighter's animation of that name exists (`_-pr._-04T()._-Y3`),
  the cast part loops between the animation's `_-T6` and `_-W1n`. Those are the 2nd and 3rd header u32 of
  the `.anm` animation (`_-y1v.static._-B5I` #147 → `<init>` #138). PR #19 names the 3rd one
  "recovery_start" [H]. This use shows it is where the loop wraps.
- **"Keep the animation"** = `_-V6B._-W28` or no CastAnim name. The start frame `_-D6j`, when not set, is
  `_-c2l + 0.384 + 1` in that case, otherwise 1. `_-cA[0] = floor(_-D6j − 1)`.
- **Timing:** CastTime `_-a2` and its total `_-wj`. `_-wj` adds each entry's D (max 1 after the first entry)
  plus R. Also used: RecoverTime `_-Sp`, FixedRecoverTime `_-f5c`, the power's RecoverMod `_-01d` with its
  gate `_-s5C`, and the end `_-E5S − _-k4b` (PR #26). `_-z2k._-Vj` = **0.384** frames per tick, i.e.
  24 frames per second over a 16 ms tick (script61.<init> #1227).

**Algorithm** [V, bytecode order]:
1. For each key i (step k_i, frame F_i), count the ticks from the previous key's step + 1 to k_i:
   - a CastTime step of 0 or 1 counts 1, except step 0 of the first key;
   - a longer step counts its duration;
   - once past the end of CastTime, the recovery counts once: `floor(_-Sp × _-01d)` (under `_-s5C`) or
     `_-Sp`, plus `_-f5c`.

   With "keep the animation", the first key at step 0 counts one more tick.
2. The frame then moves linearly from the previous key frame − 1 to F_i − 1 over those ticks. A value within
   1e-5 below an integer is snapped up to it. An entry is written only where the integer part changes.
   Each range starts one tick after the previous one ends (the first one at tick 1), except that with
   "keep the animation" the first range starts at tick 0 and ends one tick earlier.
   For an end key (fractional frame) that is the last key, the fractional value itself is stored at the
   range end.
3. After the last key (or from tick 1 without keys, or tick 0 with "keep"), the frame advances by 0.384 per
   tick up to the end. After `_-wj + _-f5c` the rate becomes 0.384 / `_-01d`, under `_-s5C` and a non-zero
   `_-Sp`. With the "L" loop, a frame above `_-W1n` is put back to `_-T6` while the tick is <= `_-wj`.

[H] The table holds frame − 1 for key frames, and `_-P6e` (§4) maps a frame to a 1-based row. Whether the
two indexings agree needs a check on real data.

Local check (aggregate counts only): the tables of all 3,768 powers build with 0 errors; 1,997 have key
frames, 903 an end key, and 687 have the CastAnim "L" flag. A CastTime duration that `parseInt` cannot read
is null, and a null pushed into the `Vector.<uint>` reads 0 [V].

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

**Which row.** The animation frame is `_-o3I._-c2l` of the active power (§1.3), or 0. The row is
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

**Carry of the entities that touch a moving line** (`carry_offset`, `carry`; `_-p4E._-d4u` #7436 @1082–1961) [V].
In step 1 of the tick, once every platform has moved its lines, each entity is carried. Entities in state 3,
7 or 8 are skipped (lookupswitch @1042).
- **Which lines.** `_-u3j` lists the lines the entity touched during its last step. It is cleared at the
  step start (@3057–3082) and filled by the ground walk, the ceiling checks and the walls. At the step end,
  the ground line `_-96f` goes into `_-O6z` and, if not already there, into `_-u3j` (@12918–13024).
- **Offset `_-s2h`.** Only dynamic lines count (`_-O2N`). Each one adds its displacement since `_-Y3I`. In x
  that is `start + _-e2l − _-t5b − _-E2x`, which equals `start − _-X1H` because `_-E2x` = old start +
  `_-e2l` − `_-t5b`. The y part is added only for a line that is not vertical.
- **Lava push.** On a lava line whose power has a push (`_-p4E._-k4L` #7443: `_-is` / `_-96U` non-zero),
  the offset is set to that push instead.
- **Sweeps.** Two sweeps, from the feet and then from 120 above. Both ignore the entity's `_-96f`, use the
  hard | soft mask and options 4, and go along the offset. A hit line stops the carry 1.01 off it:
  - a vertical line on x, when its x is inside the swept range (`_-A6B._-f6f` #1059 = clamp);
  - a horizontal line on y (a soft one only from above);
  - a sloped line by adding 1.01 along its normal to the full offset.

  The entity is then placed at the result (@1933–1961).

### 7.4 Free move against the map ([`tools/bh/air_move.py`](../tools/bh/air_move.py))

The fighter's own movement uses the same ray cast. `Entity._-8i` #2984 @6620–8865 (step 6 of
entity-step-11.00.md, PR #26) moves the feet point (`_-11W`, `_-75K`) by U = (x step, `_-P5S` × 0.384),
plus 2.02 on y while a ground line `_-96f` is set [V]. Every sweep is a 10-argument `_-X2e(team, x, y, d,
out, null, null, null, mask, 0)`: one-sided lines count only when moved into, and soft lines only from
above.

1. **Feet sweep.** Mask hard | soft, or hard only when dropping through a soft platform (local 3 = 1,
   @1780–1791).
2. **Head sweep.** From 120 above the feet, hard lines only. When it stops sooner, it takes over. Its line
   becomes the stop line only if that line's normal points down or sideways (ny ≥ 0).
3. **Attack sweep.** During some attacks (`_-wn()` with the power's `_-V67 ≠ 0`), a sweep from
   120 + `_-V67` above, on no-slide lines (16), takes over when its line faces down and it stops sooner.
4. **Ceiling check.** At the provisional stop, backed off 1.01, a sweep of (0, −120) on hard lines looks for
   a ceiling. If one is found, it is kept in `_-u3j` and steps 1–2 are redone with the x part set to 0.
5. **Placement.** The feet move by the chosen vector. The stop line becomes `_-96f`. The fighter is backed
   off by 1.01: along −normal when the line is hard and the move was tiny (|x|, |y| ≤ `_-u4H` = 1.02),
   otherwise straight back along the move.

**After the stop** (@8869–12927, `respond`). When `_-96f` is set, the branches run in this order [V]:

| # | Condition | Effect | Transcribed |
|---|---|---|---|
| 1 | bounce state (`_-e3e & _-B6B`, or `_-5q() && !_-e36()`) | `_-048` bounce; impact effect when the speed changed by > 50 | yes (`bounce`) |
| 2 | head stop on a flat line, or on a down-facing no-slide line | **ceiling**: an upward `_-P5S` becomes 0; the power's `_-K3` is set when it has `_-4A` | yes |
| 3 | head stop on a non-vertical line, or a steep line (`_-S1A`: ny < 0 and \|nx/ny\| ≥ 5/3) | **slope**: the missing y (move.y − wanted.y) is replayed along the line, the x speed `_-v1D` is pushed to at least 15 in that direction, with a hard-line sweep and a 1.01 back-off | yes |
| 4 | game-mode line with `_-ao` | mode-specific | no |
| 5 | vertical line | wall cling, ledge assist (probe from 5 below the top, ±2.02 / 6), sticky-wall timers (`_-y1L`, 5000 ms), slide damping `_-84Q` × 0.85 × 0.384, `_-r51` (PR #26); then **the remaining y continues along the wall** (feet and head sweeps, ±1.01 back-off) | yes (`wall_contact` + slide), with the fighter state passed in (`WallState`) |
| 6 | anything else (floors) | pressure plates `_-U5a` | no |

At the end, `_-O6z` = `_-96f`.

**Entity flags used here.** Several of the fighter's booleans are camouflaged: `_-wn()`, `_-t46()`, `_-5q()`
and `_-81n()` each read bit `(v >>> 24) & 31` of an int field. `Entity._-W2b` #3002 picks that bit index
and the other bits with the global generator `_-A6B._-PW` (seeded from Math.random, not the replay
PRNG), so only the decoded value matters (`packed_flag`) [V]. What they hold:
- `_-wn()`: airborne after the previous move (`_-v2J(_-96f == null)`, #2984 @13169) [V];
- `_-5q()`: set when a hit is applied (`_-26u._-L3f`), cleared when `_-Nj` runs out (`_-Re`). [H] in hitstun;
- `_-t46()`: set and cleared by the running power (`_-l4X._-o4b` / `_-VY`) [H];
- `_-81n()`: `_-O5C ≠ 0` in the input handler `_-1L` [H];
- `_-e36()`: the ground line is lava (`type & 512`) [V].

Bounce details (`bounce`, `Entity._-048` #3151) [V]:
- **Elasticity e.** `_-7c` (0.8 for a fighter, set in `Entity.<init>`); 1.0 when `_-050()`; 0.9 on bouncy
  lines (64); 1.2 in the `_-m1t` state. Game-mode lines use `_-h40`.
- **Thresholds.** `_-OI` = `_-J4r` = 25, or 0.5 in the `_-m1t` state.
- **Real speed.** When a real flight speed is kept (`_-J1m` / `_-d4x`, above 250, PR #29), the velocity is
  first rescaled to its length.
- **Vertical line.** x speed × −e. A horizontal line does the same on y. Below the threshold, the speed is
  set to 0.
- **Slanted line.** The velocity is reflected on the normal: the tangential part loses 2.5 (not below 0),
  the normal part is scaled by e, and the result is kept only if it is at least 25.
- **Afterwards.** For an axis whose real speed was kept, a speed above 250 (`_-y4Q` = 62500 = 250²) is
  capped to ±250 again and the real one stored; otherwise it is cleared.
- **Skips.** `_-83l` stops the fighter. `_-m5a` skips down-facing no-slide lines.

Wall details (`wall_contact`) [V]:
- **Ledge assist.** It runs when `_-wn()` holds and the wall is not no-slide:
  1. a hard-line probe at head height reaches 2.02 past the wall;
  2. if it finds no vertical line there, the feet are within 60 (`_-w2p`) below the wall top, and `_-P5S` is
     above −35 (`_-w5U`), a second probe goes from 5 above the top, (±2.02, 6), toward the wall;
  3. if that probe lands on a walkable line (not vertical, not steep), the fighter is put on it with a
     1.01 back-off, and `_-P5S` becomes `_-84Q` × 0.384.
- **Contact.** It runs when `_-t46()` is false, the head is on a wall or the fighter was already on one, and
  the fighter did not climb onto the ledge:
  - `_-r51` = 1 (wall at or left of the feet) or 2;
  - on first contact, a falling `_-P5S` becomes 0, and `_-y1L` = t + 112 when below the wall's bottom;
  - on a sticky wall with `_-G1T` set, the hold lasts 5000 ms (`_-P5S` = 0), then `_-G1T` is cleared;
  - otherwise a fall faster than `_-84Q` × 0.85 × 0.384 is reduced by (`_-84Q` + this step's gravity) ×
    0.85 × 0.384.
- **After the contact.**
  - On a no-slide wall, `_-v1D` = 0.
  - Otherwise, with no power and not `_-M5t`, `_-v1D` = ±10 toward the wall.


**Landing and gravity on the ground** (`ground_reset`, `gravity_applies`) [V]:
- At the **start** of the next step (@290–408), the ground line `_-96f` left by the previous move counts as a
  landing. This holds only when `_-5q()` (hitstun [H]) is false and the `_-e3e` bit `_-B6B` is clear. `_-P5S`
  becomes 0, unless the power holds `_-564` and `_-P5S` <= 0 (a rise is kept). The flag `_-G1T` (on the
  ground) is set. Then the power's `_-C3x()` runs, unless `_-r51` is set and `_-x2C` >= 9 (@411–467).
- Gravity (@5172–5353) is added only when `_-E6P()` is false, **there is no ground line**, there is no
  `_-y1L` hold (`_-y1L` = 0 or <= t), the power has no CancelGravity (`_-q1G`) and `_-84Q` is non-zero. So a
  fighter standing on a line gets no gravity; its move is only the 2.02 ground push, which the sweep stops
  on the line again.

**Lava** (`lava_contact`, `Entity._-ao` #3116 @621–997) [V]: whenever the ground line has the game-mode bit
128 (`_-J6w`), `_-8i` calls `_-ao(t, flag)`. It does so during the ground walk (@3722), after the move (@9331,
@10747) and at @13080. For a lava line (type & 512, `_-s2O`):
- the power named by the line (`PowerType._-p4G(line._-S14)`) hits the fighter through `OnHit` (17
  arguments, the damage / knockback chain of #29);
- the hit is credited to `_-W6D` when 0 < `_-W6D` < 16 (the last attacker), else to the fighter's own `_-11`;
- the same power (`_-K1e` = its `_-H4O`) cannot hit again before `_-k2j` + 240 ms, unless it has `_-x1N`.

So a fighter that lands on lava is hit by it, rather than standing. The RING scoring type takes another
branch first (@73–620), which is not read here.

[H] **Gentle slopes.** With no input, the transcribed step gives a slow creep on a hard slope. The ground
push (0, 2.02) stops against the line after a tiny move (<= 1.02), so the 1.01 back-off goes along −normal
(@7544–7770). That is about 0.02 per tick in y on the 11.3° slopes of the local maps. Either the game creeps
the same way, or a part not read yet compensates. A real game is needed to tell.

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

## 10. Fighter states (`Entity._-k5H` #2991, [`tools/bh/entity_states.py`](../tools/bh/entity_states.py))

In step 5, each fighter first reads its inputs (`_-1L(t)`), then switches on `_-65w` [V]. The handlers are
[V]. The names are [H], from the methods that set each value.

| `_-65w` | Name [H] | Handler | Set by |
|---|---|---|---|
| 0 | in play | power update `_-Kc._-25`, then movement `_-8i` (§7.4), or `_-763` in the `_-m1t` state, or pinned to `_-aB` / `_-v1Z` in the `_-J5I` state | many |
| 2 | not spawned yet | `_-44x` only | `Entity.<init>` |
| 3 | knocked out / waiting | power update only | `Entity._-eR`, `_-X6R._-U6W` (respawn, PR #25) |
| 4 | held still | as 3 | `SpawnBot`, `_-y3M` |
| 5 | in play, timed | as 0; back to 0 after 2500 ms (`_-f5u`), on lava, or other conditions | `SpawnBot`, `_-W6p` |
| 6 | held by a power (grab) | power update; released when the holder's power ends (`mHeldByPower`) | `Entity._-j4e` |
| 7 / 8 | **eliminated** (`_-s3m._-a1k` #3948 exports `Eliminated = (_-65w == 7)`) [V] | once 1500 ms have passed since `_-164` (7) or `_-lV` (8), or when `_-s3D._-zv() <= 1`, the bit `Entity._-e3c` is added to `_-e3e`; power update. The state is left by other code | `Entity._-Y6o` / `_-S1D` |
| 9 | respawning | the bit `Entity._-e3c` is cleared from `_-e3e`, then `_-W1R.Respawn(t, this)` and `_-q4u._-b3v(t, 7)` | `Entity._-220` |

Value 1, and anything above 9, falls into the "Unaccounted-for entity state" message. So **movement and
map collision only run in states 0 and 5**.

**Transitions found so far** [V call edges]:
- a KO commit sets 3 (`Entity._-eR`, ko-11.00.md);
- the respawn reset `_-X6R._-U6W(t, f, eliminated)` #6787 (which also resets the damage `_-W22`) calls
  `Entity._-Y6o`, which sets 7 (eliminated), **only when `eliminated` is true**; otherwise it turns 2 / 9 into 3
  and, unless the state is 8, sets 3 again at the end (@464-494);
- `_-X6R.Respawn` #6784 calls `Entity._-hq`, which sets 0;
- `_-d2C._-85Y` calls `Entity._-220`, which sets 9.

- `Entity._-X1J` releases a grab (6 → 0).
- **Match start** (`_-X6R._-b3x` #6777, tick step 4). On the first tick with t ≥ `_-n4k` + 256 ms (flag
  `_-C3h`), the eligible fighters get state 3 and are passed to `_-X6R.Respawn(t, f)` #6784 with two
  arguments, so `eliminated` takes its declared default, false (method info optional value kind 0x0A).
  **Correction:** Respawn therefore runs `_-U6W` without `_-Y6o`; the fighter stays in state 3 and goes to
  the respawn drone through `_-K5c` (§10.1). A game-mode rule can instead call `_-hq`, which gives
  state 0 at once. In the same call, the replay generator R (`_-s3D._-22`) is **drawn twice**:
  `_-G5X[i] = R._-f4c() % n` for i = 0, 1, where n is the number of `_-I1f._-o5y` entries, or 37 when there
  are none (@904–1002) [V].
- **Respawn point** (`_-X6R._-K5c` #6778, `respawn_index`). `_-G5X` holds the respawn point counters, so
  the two draws above pick where the rotation starts [V]. Each respawn takes the candidate list from `_-x22`
  and adds 1 to a counter:
  - outside team mode, counter 0, and the index is the counter mod n;
  - in team mode (`_-O3P()`), team 1 uses counter 0 and the first half of the list (counter mod (n >> 1));
    team 2 uses counter 1 and the second half (the same plus ceil(n/2));
  - the fighter is then placed with `_-k5S._-P3o`.

### 10.1 Respawn drone: from state 3 back to 0 ([`tools/bh/spawn_bot.py`](../tools/bh/spawn_bot.py))

`Respawn(t, f, eliminated=false)` → `_-U6W` (state 3) → `_-K5c` (point choice, above) → `f._-k5S._-P3o(t, point)`.
`f._-k5S` is the fighter's `SpawnBot` (the drone; its fighter is `_-767`) [V].

- **Placement `SpawnBot._-P3o` #11873** [V]: returns on a null point; sets drone phase 1 (`_-Y6i(1)`) and the
  target (`_-36A`, `_-35U`) = the point. Only when the fighter is spawned (`_-44x`) and `_-s3D._-F3O` is false:
  - in a standalone client, or when `_-N1k._-w35 & (32768 | 16)` is non-zero: state **0 at once**, the fighter
    is put on the point, phase 0;
  - otherwise the fighter is put just off camera: x = right edge of `_-I1f._-8I` if the point is right of
    its centre, else the left edge; y = top − 200. The state stays 3.
- **Per tick `SpawnBot._-i1H` #11858**: a lookupswitch on the phase `_-T1X`: 0 `_-q15` (idle), 1 `_-82`, 2 `_-31s`,
  3 `_-m1O`, 4 `_-Ck`. While the phase is 2 the fighter is moved onto the drone afterwards (`_-x1M(_-J2c, _-b3h)`).
  `_-Y6i(p)` sets the phase and clears its start time `_-A6k` [V].
- **Phase 1 `_-82`** (come down, duration `_-X6R._-H6B`): on the first tick `_-A6k` = t and the drone's start
  position is kept; each tick the drone eases in (power 2, `_-D2g`, §7.3) toward the fighter. When
  t > `_-A6k` + duration: phase 2, state 3, and `_-31s` runs in the same tick [V].
- **Phase 2 `_-31s`** (carry, duration `_-L26`): the start is the fighter's position; the drone (and the
  fighter with it) eases out to the point, power 3, or 2 when the fighter is not spawned and `_-d3Y._-K4x` is
  neither 1 nor 2. When t > start + duration: both are put on the point, phase 3, and `_-m1O` runs [V].
- **Phase 3 `_-m1O`** (drop, duration `_-d3X`): on the first tick (the arrival tick) `_-A6k` = t and the
  fighter gets **state 4** (held still). Once `_-A6k` + duration <= t: phase 0, the fighter's vertical speed
  `_-P5S` is set to 30 (spawned, or `_-K4x` 1 / 2) or 70 with `_-F5c` set, then **state 0** when the `_-e3e`
  bit `_-M14` is clear and (bit `_-o24` is set, or the fighter is spawned and `_-F3O` is false); otherwise
  **state 5** (timed in play, back to 0 after 2500 ms, see the table), `_-u55` set and `_-U5l()` called [V].
  The drop animation speed is 700 / duration [V].
- **Durations** [V], from the flags `_-nN(t, f)` (1 = spawned, 2 = a game-mode test `_-06A._-Z3E(f._-11)`,
  4 = `_-S3h._-w1s` >= t) and the scoring type `_-d3Y._-11X`:

| Phase | `_-F3O` | long case | `_-Ac` and not flag 2 | otherwise |
|---|---|---|---|---|
| 1 `_-H6B` | `SpawnBot._-s1I` = 1000 (script641.<init>) | 2000 | 1500 | `_-o2N` |
| 2 `_-L26` | 2000 | 3000 | 2500 | `_-j57` |
| 3 `_-d3X` | — | — | 700 | `_-C18` |

  The long case is: `_-S3h` exists, flag 4 is set and `_-w1s` = `_-n4k` + 6000; or else flag 1 (phase 1) or
  flag 1 or 4 (phase 2) is set and `_-K2V` is false.
- [H] The scoring-type fields (`_-o2N`, `_-j57`, `_-C18`, `_-K2V`, `_-Ac`) come from game data and are not
  read here; with them, a normal respawn takes phase 1 + phase 2 + phase 3 ms before the fighter moves.

`Entity._-b6D` #3015 is true for 4000 ms after the elimination, from `_-164` in state 7 or `_-a2O` in state 8 (it first requires the `_-8` bit of `_-e3e`) [V]. [H] It drives the post-elimination display.

**How an input starts a power** [V shape]:
1. The input consumer `_-i4Z._-rU` / `_-I35` (input-buffer-11.00.md, PR #28) calls one of:
   - `_-F5N._-C5S`: attack slot → power through `_-42t`, with extra checks for slot 9;
   - `_-A3Q`;
   - `_-V5I`: throws the held item; `_-3z._-q1S` spawns it at the feet.
2. All three end in `_-F5N._-J5R`. It returns unless `_-O5u` allows the start. `_-O5u` refuses while the
   running power has `_-82f`. It may swap the power for the held weapon through `_-H1V` (`_-M1g` / `_-E2S` /
   `_-w3H` matched against `_-r1e`).
3. `_-J5R` then ends the running power (`_-VY`) and sets `_-o3I = new _-l4X(...)`.
4. From the next update, `_-R63` runs the new power (§1.1).

Chained powers start from `_-h1T` through the same `_-J5R`.

## 11. Still open

- Platform rotation (`_-o2k` is computed but not applied to lines here), when `_-p4E._-d4u` runs inside a tick,
  and curves inside a DynamicCollision block (offset of the anchor) [H].
- The other guards at the top of `_-T5A` (`_-i4o` HoldHitEnts with `Entity._-b2C`, `_-u3H` against
  Uninterruptable `_-C5G`, `_-hQ` / `_-72e`). The order of the list follows `_-5r` [H].
- `_-B5B`, the meaning of `_-q24`, and the exact gate on `_-L5r` per frame (§1); the cancel path of §1.1.
- The other filters of §3 (`_-55E`, `_-E2I`, `_-AP`, `_-r1o`).
- Items: the per-target gates of §8 step 5, the item's own motion and map collision (`_-p5k._-8i` uses
  `_-X2e`), and the other spawners `_-F5N._-33h` (15 callers) and `_-p5k._-u1I`.
- Respawn drone (§10.1): the idle and phase-4 handlers (`_-q15`, `_-Ck`), the
  scoring-type durations (`_-o2N`, `_-j57`, `_-C18`) and who calls `Respawn` after a KO [H].
- Nothing has been checked against a running game. The next step towards the KO oracle
  (oracle-ko.md) is one scripted exchange: a hit, its knockback, then a ring-out.
