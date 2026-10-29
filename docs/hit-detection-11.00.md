# Hit detection — patch 11.00

Which entities a power's hit area touches on one frame. This closes the gap left open in
[knockback-11.00.md](knockback-11.00.md) (PR #29): how the candidate list `_-F5N._-U5S` of
`_-F5N._-T5A` is filled.

Code: [`tools/bh/hitdetect.py`](../tools/bh/hitdetect.py). Check: `python -I tools/bht.py hit-detection-verify`
(146 anchors on ABC `7d308423…`, exit 1 on a mismatch, 2 on another ABC). Tests: `tests/test_hitdetect.py`.
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

## 7. Still open

- The rest of `_-T5A` (@756–3541): the other guards (`_-i4o` HoldHitEnts, `_-u3H` against Uninterruptable
  `_-C5G`, `_-Z3E`) and the order of the list (the order of `_-5r`, [H]).
- The meaning of `_-X2G`, `_-B5B`, `_-q24`, and the exact gate on `_-L5r` per frame (§1).
- The other filters of §3 (`_-55E`, `_-E2I`, `_-AP`, `_-r1o`).
- The Ranged / ThrownItem object `_-x4I` and the projectile path.
- Nothing has been checked against a running game. The next step towards the KO oracle
  (oracle-ko.md) is one scripted exchange: a hit, its knockback, then a ring-out.
