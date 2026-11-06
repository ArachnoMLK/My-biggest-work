# Integration branch for patch 11.00 (`integration-11.00`)

This branch merges the open PRs #16–#30 on top of `main`, so that one harness can import every module. It is
not meant to be merged as is: each PR is still reviewed on its own. When a PR changes, rebuild the branch.

## How it was built

`main`, then in this order: #16 `input-bit-names`, #17 `q5-legend-stats`, #18 `q8-ledger-roles`,
#19 `anm-format`, #20 `q6-collision-flags`, #21 `q9-settings-flags`, #22 `q7-power-parser`,
#23 `q4-horizontal`, #25 `q-ko-bounds`, #26 `q4-step-order`, #27 `q10-ko-oracle`, #28 `q-input-buffer`,
#29 `q11-knockback`, #30 `q12-hit-detection`.

Every conflict was additive: each PR registers its own command in `tools/bht.py` and, for some, its own
test in `tests/test_tools.py`. Both sides were kept. One trap: `cmd_step_verify`, `cmd_ko_verify`,
`cmd_input_buffer_verify` and `cmd_knockback_verify` have identical lines except the module name, so the
line merge kept a single body. Each one was taken back from its own branch. Every other function of
`tools/bht.py` is identical to its version in one of the branches.

## Checks on this branch (ABC `7d308423…`)

| Command | Anchors | Mismatches |
|---|---|---|
| `movement-verify` | 31 | 0 |
| `commands-verify` | 31 | 0 |
| `stats-verify` | 29 | 0 |
| `collision-verify` | 89 | 0 |
| `hit-detection-verify` | 1920 | 0 |
| `prng-order-verify` | 87 | 0 |
| `step-verify` | 159 | 0 |
| `ko-verify` | 290 | 0 |
| `input-buffer-verify` | 341 | 0 |
| `knockback-verify` | 253 | 0 |

`prng-verify`: OK. `python -I -m unittest discover -s tests`: 388 tests pass.

## First smoke test: one fighter falls onto a map (`smoke-fall`, [`tools/bh/smoke.py`](../tools/bh/smoke.py))

One fighter starts at rest on a respawn point and receives no input. Each tick:
1. gravity `_-P5S += 3.75 × 0.384` while below the fall cap 70 (movement-11.00.md);
2. the free move against the map (`air_move.py`, PR #30), against the LevelDesc's static lines, normals
   and candidate grid (`level_collision.py`), through the map ray cast (`raycast.py`).

At the first ground contact, the test checks that the feet plus the 1.01 back-off (`_back_off`) lie on the
line that stopped the fall. It then runs 60 more ticks with no input. Each tick, after the platforms move, the fighter is carried by
its ground line (`_-p4E._-d4u`, platforms.py `carry`). At each step start, the landing
(`ground_reset`, @290–408) sets `_-P5S` to 0. Gravity is skipped while a ground line is set
(`gravity_applies`, @5172–5273), so the move is only the 2.02 ground push (air_move.py, PR #30).

With `--static-only`, the moving platforms' lines are left out. By default they are included: the
DynamicCollision lines (normals computed with the static ones, `_-u8`) are the grid's dynamic list. Each tick,
before the fighter moves, each one is placed at its platform's position (`platforms.py`: `_-V39` time →
frame, `_-I4v` blend, `_-Y3I` move). [H] The platform clock starts at t = 0; at a real respawn it depends on
the match clock.

Local result (aggregate counts only, no names or coordinates):

| | Static only | With moving platforms |
|---|---|---|
| LevelDescs | 122 | 122 |
| Respawn points | 995 | 995 |
| Ground contact | 829 (811 flat, 18 slopes) | 965 (947 flat, 18 slopes) |
| Contact point on the line within 1e-6 | **829 of 829** | **965 of 965** (largest error 1.8e-15) |
| No contact within 1000 ticks | 166 | 30, all on maps with dynamic lines |
| Longest fall | 116 ticks | 144 ticks |
| Lava landings (the lava line's power hits the fighter, `lava_contact`) | — | 11 (not counted as standing) |
| Ground kept for the 60 standing ticks | — | **954 of 954** |
| Exactly still on fixed flat ground | — | **794 of 794** |
| Still on fixed hard slopes (11.3°) | — | 0 of 14: a slow creep of about 0.02 per tick in y, see [H] below |
| Same height above a moving line (carry `_-d4u`, platforms.py `carry`) | — | **146 of 146** |

Of the 30 points without contact: 5 get one with another platform phase (t0 between 0 and 60 s), and 25,
on 4 maps, have no line below them at t = 0.

So the gravity, sweep, grid and ray cast pieces fit together, and the fall stops on the map geometry.
[H] This only shows that the transcribed pieces agree with the map files. It does not show that they match
the running game. [H] On a gentle hard slope, the ground push stops after a tiny move, so the 1.01 back-off goes along −normal
and the fighter creeps. Either the game does the same, or a part not read yet compensates; a real game is
needed to tell. Next: the KO oracle of #27.

### Walking

After landing on a fixed, non-lava line, the fighter walks both ways at a constant x step of 6 (`_-v1D` =
15.6) for 60 ticks. Each tick runs the step-start landing, the ground walk (`air_move.ground_walk`, PR #30),
gravity only off the ground, then the free move with the left-over x and the 2.02 ground push.

| | |
|---|---|
| Walks | 1,650 (825 landings × 2 directions) |
| Ground kept for 60 ticks | 1,187 |
| Stopped by a wall (`_-v1D` = 0) | 35 |
| Left the ground | 428: 427 past the end of their line (a ledge), 1 inside its x range (a corner) |
| Height above a flat line kept within 1e-6 | **1,650 of 1,650** |

### Items

`smoke-fall` also drops an item of the default ItemType, at rest and not thrown, from the centre of every
`ItemSpawn` box and every `ItemInitSpawn` point. It runs `items.velocity`, `items.sweep` and
`items.after_sweep` (impact: bounce or stop; PR #30) on the static lines. Once the item has stopped, it
rests 60 more ticks.

| | |
|---|---|
| Item spawn points | 823 |
| Contact | 682, **all on the line within 1e-6** |
| Stopped (both speeds 0) | 623, after up to 349 ticks of bounces; all 623 stay still for 60 ticks |
| Never stopped | 59: they micro-bounce on flat floors whose normal y is −0.9999999999999999, not −1; 58 of them still stay in place |
| No contact | 141: 129 on maps with moving platforms (left out here), 12 with no line below them at all |

**Sliding.** Each item that stopped is then pushed both ways (`_-Lu` = ±10) and slides. Each tick runs the
item ground walk (`items.ground_walk`), whose full x step is used again by the free move, then the sweep and
the landing:

| | |
|---|---|
| Slides | 1,246 |
| Stopped | 1,244, within 6 ticks: under speed 5, the impact stops the item dead on a flat floor |
| Off a ledge | 2 |
| **Fell through a floor** | **0** |

While it moves, the free move has an x part, so the 1.01 back-off goes along the move. The height above the
floor is then not constant (about 0.05 instead of 1.01) [V].

**Throws.** From every respawn landing on a fixed, non-lava line, the fighter (at rest, facing right)
throws a default item in 6 directions (facing, up, down, left, right, up-left), uncharged and charged
2.5 s. The throw uses `items.throw_vector` / `throw_start` (PR #30), with the spawn 30 above the feet. Each
tick then runs the velocity (thrown gravity), item ground walk, sweep and landing:

| | |
|---|---|
| Throws | 9,900 |
| First contact on its line within 1e-6 | **6,910 of 6,910** |
| Stopped on a line | 3,738 (within 863 ticks) |
| Left the map (no line touched for 300 ticks) | 5,688: a 75- to 135-unit throw often leaves the stage |
| Still bouncing after 900 ticks | 474 |

**Rounding finding [V].** A flat line's normal is (0, w) scaled by `Point.normalize(1)`, i.e. times
1 / length. For some widths (e.g. 1700) this gives −0.9999999999999999 instead of −1. The impact test
`normal y != -1` (`_-u1I` @1359) then never lets the item stop, and the rest test of `items.velocity` never
holds. If the game computes the normal the same way, items on those floors bounce imperceptibly forever.
[H] That depends on the player's `Point.normalize` doing `x *= thickness / length`, which a real game
should confirm.

### KO bounds ([`tools/bh/level_bounds.py`](../tools/bh/level_bounds.py))

The data for `ko.ko_mask` (PR #25) comes from two places: the LevelDesc's CameraBounds (left, top,
right, bottom = x, y, x + w, y + h), and the kill values of the LevelType of the same name (LevelTypes.xml).
All 122 local LevelDescs have such a LevelType.

| | |
|---|---|
| Respawn points inside the kill box | 989 of 995. The 6 others are all on one map, outside on the left (4) or the top (2) [H: a map whose camera or bounds change during the match] |
| Falls with no line below (static lines) | 166 |
| … ending in a bottom KO | 160, within 189 ticks |
| … ending in another KO | 6: the 6 points above, KO'd at tick 1 |

## Per-tick harness, first version ([`tools/bh/harness.py`](../tools/bh/harness.py))

Plan step 4. One fighter, inputs left / right / jump, a static map. One tick at time t:

1. the input consumer: a fresh jump press calls `Jump(t)` (jump.py: the squat, or the jump at once in the
   dash window);
2. `_-8i` in byte order: step-start landing → friction, then acceleration toward the held side → squat
   release (`_-A2X` once t ≥ `_-I5A` + 32) → x impulse fold and clamp → ground walk → y impulse fold and
   clamp → gravity → free move → landing delay of a pending jump (+64 ms) → `_-84` = `_-A4A` = 0.

After the free move the tick follows `_-8i` @8869–13169: `_-r51` is saved and cleared, the stop line goes
through `respond` (ceiling, slope, or `wall_contact` + slide on a vertical line, which sets `_-r51` = 1 / 2),
and the stop line is dropped from `_-96f` when its normal does not point up or it is steep (@13029–13127,
`_-X3S.y` ≥ 0 or `_-S1A`), so a wall never stays the ground line and the jump there takes the wall branch.

Replay inputs: `harness.from_records(rep["inputs"][entity])` reads the key word at each tick time
(`input_buffer.state_at`); left / right are MoveLeft (4) / MoveRight (8), and a jump press is bit 16 set on the
tick and clear 16 ms before. [H] The 5-tick press buffer and the `_-532` lock of input-buffer-11.00.md (#28)
are not modelled yet.

Every piece is [V] in its own module; the glue is [H]. Not modelled yet: powers, hitstun, bounce, the `_-532` lock and the air-jump counter writers (the harness resets the count on landing [H]),
the facing flip of the wall jump, the KO commit and respawn after a ring-out, and real legend stats
(synthetic defaults; the caller can pass `stats.fighter_stats` values).

The ring-out test runs after the move, as `_-8i` @14270–14370 calls it: `ko_mask(x, y, cam, kill, _-5q(),
!_-wn() || _-r51 != 0)` with `_-5q()` false (no hitstun yet); a non-zero mask is kept in `a3d` (`_-a3D`).

On the synthetic flat map of `tests/test_harness.py`: the fighter lands at 500 − 1.01; a jump press leaves
the ground 32 ms later with a first rise of (57 − 1.44) × 0.384; two air jumps follow, a third press does
nothing; walking right reaches RunSpeed; walking off a narrow ledge ends in one ring-out below the
bottom kill line; a fighter jumping into a tall block clings (`_-r51` = 2) and its jump there is a wall jump,
pushed away and up. Static evidence only; not compared with the running game.

**Match start, chained** (`harness.match_start`). For a plain 1v1 replay: the match-start step at 272 ms
(`_-n4k` = 16), the fighters in `_-5r` order (increasing entity id), R at that tick (seed, one draw per
player), the start placement (`one_v_one`: shuffle, first / last Initial candidate), then `Drone.place` with
the replay's `_-w35` = 1024 (no instant bit) and the drone phases until it lets go. On the synthetic map of the
tests, with the default scoring durations:

| `_-44x` | Let go at | State | `_-P5S` |
|---|---|---|---|
| set (the replay case) | 6000 ms (272 + 5700, rounded up to the steps) | 0 | 30 |
| clear (not reached in a replay) | 4992 ms (272 + 4700, idem) | 5 | 70 |

`_-44x` is set [V]: tick phase 5 runs `Entity._-k5H` on every fighter, and it sets `_-44x` in state 2, where
players wait from replay start (spawn_bot.py `SPAWNED_AT_MATCH_START`; `_-J1Y` only comes from the BRAWLBALL /
TAG rules). `_-k5H` also ticks the drone first, so the drone's first tick is in the match-start step [V]. The
KO gap check now uses the 5700 ms first trip. [H] the `_-vs` gate of the normal update holds.

## Real replays through the harness (`replay-start-check`, [`tools/bh/replay_setup.py`](../tools/bh/replay_setup.py))

For each local 1v1 replay of patch 11.00: the map (static lines of the LevelDesc), the KO bounds (CameraBounds
and the LevelType kills), the legend stats of each fighter's first hero and stance (stats.py), the scoring
durations, then `harness.play`: both fighters in lockstep from the match-start step, each tick in `_-5r` order

- phase 5 (`Entity._-k5H`): the drone first, then, in states 0 / 5, the movement with the fighter's own inputs
  (which also clears `_-44x`, spawn_bot.py `SPAWNED_IN_PLAY`);
- phase 6 (`Entity._-eR`, ko-11.00.md §5): a ring-out mask is a KO at this tick; `_-p1Y` reset, state 3,
  lives − 1, then `Respawn`: state 7 when eliminated (`Entity._-19`), else the next point of the shared `_-G5X`
  counter (`respawn_index`, `candidates` with `_-44x` clear) and the drone, which leaves the fighter where it
  is, takes 4700 ms by default and lets go in state 5 with `_-P5S` = 70.

Glue [H]: the HeroType by HeroID, the first hero only, the drone's camera rectangle = CameraBounds, no moving
platforms, no hits or grabs between the fighters, only the Speed family fields used, the lives from the
settings' `starting_lives`, the state 5 → 0 timer not modelled (movement is the same in both).

Local run (aggregate only, 6000 ticks = 96 s from the match start):

| | |
|---|---|
| 1v1 replays run | 266 (490 others skipped: not 1v1) |
| Fighters let go | 532 (472 first let go at 6000 ms, the others under other scoring durations) |
| Predicted KOs | 1,389 |
| Respawns let go | 928 |

This only shows that the chain runs on real data. The predicted KOs are **not** compared with the replays'
KO faces yet: that is plan step 5.

## First check against real replays: KO gaps (`ko-gap-check`, [`tools/bh/ko_gaps.py`](../tools/bh/ko_gaps.py))

The KO commit calls `Respawn` in the same tick, and the drone then comes down, carries and drops the fighter
(spawn_bot.py, PR #30). So two KO faces of the same victim (oracle.py, PR #27) are at least `respawn_ms`
apart. That time comes from the durations of the replay's scoring type (ScoringTypes.xml, by `ScoringID`).
After a KO `_-44x` is clear (spawn_bot.py `SPAWNED_IN_PLAY`), so with the defaults it is 1500 + 2500 + 700 =
4700 ms (it was 5700 ms, the spawned case, before that was read).

Local result (756 patch 11.00 replays, aggregate only):

| | |
|---|---|
| Scoring types with at least one gap | 4 |
| Gaps between two KOs of the same victim | 3,241 |
| Gaps shorter than the predicted drone time | **0** |
| Smallest margin | 1,172 ms (172 ms against the 5700 ms floor used before) |
| Replays with a first KO | 688 |
| First KOs before match start (272 ms: `_-n4k` = 16, match_start.py) + the first drone trip (5700 ms by default: `_-44x` is set, spawn_bot.py) | **0** (smallest margin 2,252 ms, a loose bound) |

This is a one-sided check. The replays allow the transcribed drone time, but they do not show it is exact:
the margin also contains the time needed to be knocked out again. It is the first comparison of a
transcribed piece with the replays' own records.


## Plan step 5: first two-sided check (`ko-compare`, [`tools/bh/ko_compare.py`](../tools/bh/ko_compare.py))

The harness's first predicted KO of a victim is compared with the replay's own KO face (`oracle.ko_ticks`).
Face time and harness time share one clock: a replay has `_-w35` = 1024, a bit of `ko.NO_BASE_BITS`, so
`ko.ko_time_base` is 0 [V in ko.py / spawn_bot.py]. Only the match's **first** KO is used, and only when the
opponent pressed no LightAttack (128), HeavyAttack (64) or PickUpThrow (512) before it, so that no hit can
explain it [H: `replay.parse` does not keep the KO type, this input filter stands in for "self-KO"]. Cases
where the victim pressed a key the harness does not model (attacks, DodgeDash 256, taunts) are counted apart.

Local run (aggregate only, format 271): 68 replays without a KO, 454 not 1v1, **233 skipped because the
opponent attacked before the first KO**, and **1 candidate**, predicted early by more than a tick; its victim
used DodgeDash before the KO, which the harness does not move. 0 candidates with a victim that only walked
and jumped.

So the filter is too strict to test the movement alone: in a 1v1 almost every first KO follows an attack.
The check can only bite once the harness models what the players actually do before a KO. Two ways on,
in roadmap order: (a) DodgeDash movement in the harness (the one unmodelled key of the one candidate), then
(b) the hit detection of #30 wired into `harness.play`, so that the filter can be dropped. [H] until run.

**(a) wired** (`harness.dodge` / `harness.dodge_tick`, DodgeTypes.xml through `replay_setup.Swz`): a fresh
DodgeDash press runs `dodge.gates` → `pick` → the commit before `_-8i`, and `_-t1A` runs at @2659 (landed
cooldown, cooldown end, the push of each dodge tick, the exit speed); friction and gravity are off while
`_-E6P()`. Glue [H]: no power, no move lock, no dash (`Dash` false), no chase dodge (`_-26R` false), `_-VE` = 0,
`_-M3h` false, power multipliers 1, Set "Default". Rerun (aggregate only, format 271): 68 without a KO, 460 not
1v1, 236 skipped (opponent attacked first), and the **1 candidate is now predicted late** instead of early: the
dodge moves its victim, but the KO is not reproduced yet (its dash and chase dodge are still missing). Next:
(b), the hit detection in `harness.play` (plan in the evening note: b1 slot, b2 power name, b3 timeline and
frames, b4 capsules, b5 knockback and hitstun, b6 rerun).

**(b1)** `harness.attack`: a fresh LightAttack (128) / HeavyAttack (64) press records `("attack", slot, gravity
cancel)`: `dodge.cancel_flags` in a dodge, `dodge.attack_air_offset`, `input_buffer.attack_slot`. Nothing moves
yet: the power is not started (b2-b5). [H] glue: no running move, `_-f2b()` false, no jump flag, `_-y1U` false.

**(b2)** the event also names the power (`power_pick.power_name`): `replay_setup` loads HeroTypes.xml
(signatures) and itemTypes.csv (`_-Z6M`), and each fighter starts with the Unarmed item (`ItemType._-m4V`)
[H: no pick-up yet]. **(b3, start)** the name then goes through the powerTypes.csv lookup (`power_pick.power_rows`, `_-p4G`) and
`redirect` (GCVersion under the gravity cancel, MomentumVersion at \|vx\| >= 60 toward the facing; no test set,
not exhausted, `_-b3A` 0 [H]). Then the power starts when none runs: `power_data.power_steps` and a `power_timeline.Timeline` from the press
tick; each tick, before `_-8i` (`_-Kc._-25` in state 0), the step that fires is recorded ("step", name, step) and
the power is dropped once its last step fired [H: the end rules `ends_now`, chains and cancels are not chained].
**(b4, first cut)** `harness.step_hits`: when a power step fires, its frames (`hitdetect.frame_window(q24, step)`)
make hit areas (`area_center` with the TargetMethod `_-g4i` and CenterOffsetX / Y, `hit_capsule` with AoERadiusX
/ Y), tested with `capsules_touch` against the opponent's hurtbox capsule; `play` records (t, victim, power), one
hit per power and victim. Glue [H]: the DEFAULT row of hurtboxTypes.csv for every frame (no `.anm` frame yet),
no team mask, no line of sight, no item / point areas, fighters stay Unarmed, the hit changes nothing yet (b5).
Local run (aggregate only, first 60 s of 269 1v1 replays of format 271): **175 hits, in 114 replays**, far
fewer than in real games, as expected without weapons, animation hurtboxes and knockback.
**(b5, first cut)** `harness.apply_hit`: damage (`hit_damage`, BaseDamage), magnitude (`knockback_force` with
VariableImpulse and the victim's `_-W22` before the hit plus this damage, then + FixedImpulse via
`final_magnitude`), direction ImpulseOffsetX (mirrored by the attacker's facing) / ImpulseOffsetY, written into the
victim's `_-84` / `_-A4A` after clearing its velocity; hitstun `hitstun_ms(FixedStunTime)` turns the inputs off and
feeds the `_-5q()` argument of the ring-out test. Glue [H]: no charge / item part / DI / MinimumImpulse / damage
setting, `_-M3e` and the power-controller factors 1, the knockback decay `_-V12` not chained.

**(b6) first-KO check without the attack filter** (aggregate only, 1v1 format 271, first KO of the match): 233
predicted early, 4 late, median gap about 30 s, 2 within 1 s; the victim was hit in the harness in 60 of them. The
**same run without hits** gives 232 early, 5 late: the early KOs come from the movement, not the knockback. Leading
[H]: powers do not move their owner yet (recoveries, aerials, the power's own velocity writes), there are no
weapons, no ledge / platform behaviour beyond the static map, so the simulated fighters fall where the players
recover.

**Owner movement of a power**: `harness.cast_impulse` (`_-l4X._-O1K` #91 main branches: CastImpulseX / Y **set**
`_-v1D` / `_-P5S` at the power start) and `harness.fire_impulse` (`_-l4X._-a5A` #47, run when a step fires:
FireImpulseX / Y[step] set `_-v1D` (by the facing) / `_-P5S`). Glue [H]: no charge factor, no FireImpulseMaxX
branch, no `_-I2g` gate, cells read as plain int lists. Rerun (aggregate): the cast impulse alone changes nothing;
with the fire impulse **224 early, 13 late, 3 within 1 s**, and the harness victims live 13.8 s after the let-go
(median; 11.9 s before) against 44.2 s in the replays. Next: why the simulated fighters still fall (weapons and
pick-ups, recovery rules, platforms and ledges, `_-V12` knockback decay), then the `.anm` frames.

What the harness KOs look like (aggregate, all 269 1v1 replays, first 40 s): 874 KOs, **809 through the bottom
line**, 64 through a side; at the KO 702 fighters had used both air jumps, 531 were in the dodge cooldown, 170
were in a power, 88 had been hit. So the simulated fighters run out of air options and fall where the players
recover. Caveat on the method: a replay holds only the inputs, so the check is open loop. Once the simulated
position drifts from the real one, the replayed inputs no longer fit, and the drift grows. A KO can match only
when the movement is exact up to it, so this check measures exactness, not "closeness".

Two more [V] rules added after that: a hit with a knockback gives the victim one air jump back (#1677
@1171-1226), and the fall cap is 85 with Drop held (movement-11.00.md, @5097-5170). Neither moves the
aggregate (224 early, 13 late, harness life 13.8 s): the drift is broad, and the first-KO time is too coarse to
judge one piece at a time. A finer check needs a per-tick reference (positions), which a replay does not hold.

Then the knockback decay `_-V12` (in hitstun while v² >= 2500, instead of friction; fold overshoots kept in
`_-J1m` / `_-d4x`): no change. Then **the input buffer in `play`**: `input_buffer.buffered_presses` (window 5, a
press kept 4 ticks) feeds Jump, DodgeDash, LightAttack and HeavyAttack, and a press counts as handled once its
action ran (`_-C51` for the dodge; [H] for the others), so a refused press is retried on the next ticks. Rerun:
10 late, **1 off by one tick** (the first near-exact first KO), 4 within 1 s, harness life 14.0 s (median).
With the window widenings of #6313 §2 (9 ticks while dodging, within 32 ms of `_-I5A`, before `_-f6R`; the dodge
exit now writes `_-f6R` = t + PostDodge × 16 off a wall) and [H] the `_-322` / `_-P50` / `_-M3V` cases left out:
225 early, 11 late, 1 off by one tick, 5 within 1 s, harness life 13.2 s (median; p90 26.6 s).
Then `_-532` = t at each power start (`Entity._-c1r`, input-buffer-11.00.md §6), which feeds the jump lock and
`_-C2E`: 226 early, 11 late, 5 within 1 s (the near-exact case turns early), life 13.3 s; kept since the rule is [V].
Then the last widening, `_-322` = the landing time (`_-8i` @13446): window 9 for 64 ms after a landing; no change.
Then the power and hitstun friction rules of `friction_value` (KeepGroundFriction `_-y25`; [H] `_-o3I._-7E` false;
4.0 in hitstun below the decay speed): no change.

More diagnosis (aggregate, local): harness life is the same on maps with and without moving platforms (median
13.9 s over 60 victims vs 13.1 s over 177), so the left-out platforms are not the main gap. Of 879 harness KOs,
**118 never landed** after the let-go (a placement / drop question to check against the drone and the spawn
points), 525 landed 1-3 times, 236 four times or more.

**Move lock of a power** (`harness.move_locked`): a power with neither AllowMove nor AllowMoveForward makes its
owner move-locked (`_-l4X._-f14` #59 @682-725 → `Entity._-a6l(true)` → `_-23G` → `_-65i()` → `IsMoveLocked`
#3061), and `Entity._-1L` then takes no left / right; the lock also feeds `IsDodgeLocked`. [H] cleared when the
harness drops the power (AllowRecoverMove and `_-Kc._-H6I` not modelled). Rerun: **222 early, 15 late**, 4 within
1 s, 85 victims hit, harness life 14.2 s (median, was 13.3 s).
Then the power stays until its end tick `_-E5S` = `_-k4b` + FixedRecoverTime + RecoverTime (#59 @214-289) after
its last step, with the move lock cleared there under AllowRecoverMove (#46 @4677-4719): identical aggregate. [H]
`_-E5S` counts from the start, so it often falls before the last step; what else ends or extends a power is
not read.
Then CancelGravity (`_-q1G`, the `_-8i` gravity gate @5252) while a power runs: 220 early, 17 late, harness life
14.4 s (median).
Then the power's acceleration factor `_-l4X._-x1E(t)` #68 (AccelMult[step] while a step is pending, else
BackwardAccelMult against the facing; [H] the air-power and `_-H6I` rules left out), applied at `_-8i` @2070-2109:
220 early, 17 late, harness life **14.9 s** (median).
Then `_-Kc._-J4Z` = `_-759` (the last fired step set a FireImpulseX) and not `_-d38` (#1745 @231-266), which turns
the acceleration off (`_-8i` @2054-2066): identical aggregate.
Then the speed limits of `_-O1K` #91 @714-1083 at a power start without CastImpulseX (SpeedLimitBackward `_-M2J`
for a backward speed, else SpeedLimit `_-u1G` toward the facing): identical aggregate.
Then the power's gravity cancel as `_-o4b` #45 sets it (while the step is held: tick < start + AntigravTime, from
#59 @515-592; else CancelGravity): identical aggregate.

**Video oracle, 6 Nov (owner's Medal clip of the in-game replay player, local only).** [V by frame reading] The clip
runs about **0.45 s behind the replay clock** (replay time = clip time + 0.45): CLO's dash and dash jump (inputs at
6768 / 6816 ms) show at clip 6.33 / 6.36 s, the match timer flips at clip 6.55 / 7.55 s (start at replay 6.0 s),
and CLO's first KO shows at clip 40.8 s (replay 41.2 s). The earlier comparison that assumed clip = replay time was
off by that much. With the offset, the first real hit on replay 186 is MAM's unarmed side heavy
(`BaseSmashSideCombo`, 18 damage) at replay ~10.69 s, not a side light; no damage before.
Three rules found from that clip and wired (transcribed on #30 in `air_move.py`, 2259 anchors):
- **`_-u55` drop lock**: the drone drop (`SpawnBot._-m1O` #11857 @489 / @516) sets `_-u55` (= `_-44x` in state 0,
  true in state 5); `IsMoveLocked` #3061 tests it and `_-8i` @13288-13335 clears it on a ground line. The harness
  let MAM drift ~150 units right while falling at the match start; the clip shows a straight fall.
- **Apex gravity** `Entity._-71A` #3171 (3.25 − |vy| × 3.25 / 48 for |vy| ≤ 48, × 0.384, out of hitstun).
- **Fast fall** (`_-61h` / `_-rA`, `_-G1a` from `_-1L`): 48-80 ms after a Drop press in the air (P5S ≥ −38, no
  power), a rise is cut to 0 and 12 × 0.384 is added each falling tick; plus the 85 cap and the ease back to 70
  (− 6 × 0.384) of @5604-5853. CLO's dash-jump hop now lands at ~7.06 s (clip: ~7.04 s), it stayed in the air
  ~0.6 s longer before.
Aggregate (own script, first KO of the real victim, 254 1v1 11.00 replays): before 243 early / 5 early within
1 s / 2 late within 1 s / 4 none, harness life median 12.5 s; after 248 early / 2 early within 1 s / 2 late /
1 off by one tick / 1 none, **life 10.2 s** (real 44.3 s). The fall terms make jumps shorter, so fighters fall
sooner; the rules are bytecode-backed and match the clip, so the remaining gap is elsewhere (open [H]).
**Recovery times (6 Nov).** [V] `PowerType._-A3R` #6483 reads FixedRecoverTime / RecoverTime as `split('@')[0]`
through Std.parseInt (the part after '@' is an animation frame for `_-g1x`); the harness read the whole cell as a
float, so **707 cells written "N@F" gave no recovery at all** (`power_data.recover_times`, #30 at 2270 anchors).
The end tick also takes the fighter's recover factor: `_-E5S` = floor(`_-k4b` + FixedRecoverTime + RecoverTime ×
`_-01d`) under `_-s5C` = not (ComboOverrideIfHit and not EndOnHit), `_-01d` = AirRecoverMod for an IsAirPower,
else RecoverMod (#59 @214-289, #39 @265-379; SigRecoverMod only for legend signatures, flags 512|64 from
`PowerType._-z24` #6491). Aggregate: life 10.2 → **10.7 s** (246 early / 2 early within 1 s / 1 exact / 3 late /
1 late within 1 s / 1 none). On replay 186 MAM's missed side light now recovers until ~10.32 s instead of 10.13 s;
the clip still shows no second side light at ~10.34 s but the side heavy charge (open [H]: why the light press at
10.304 does not fire).
**Per-power cooldowns (6 Nov).** [V] `_-F5N._-h1T` #1742 calls `_-BC` #1747 when a power ends: the cooldown of
its origin (OriginPower `_-N`, #6495) is armed for OnHitCooldownTime after a hit, else CooldownTime (the origin's
when 0), × 16 ms, in one of two slots (`_-S4J` #1748); `_-O5u` #1744 refuses a power whose PowerID is on
cooldown (#30 `power_pick.Cooldowns`, 2301 anchors). On replay 186 this is what the clip shows: MAM's missed side
light ends in BaseSideMiss, whose end arms BaseSide's cooldown, so the light pressed at 10.304 s is refused and
the side heavy pressed at 10.336 s starts (charge visible at ~10.37 s). Aggregate unchanged (life 10.7 s).
Next gap seen: charged powers (heavies) have no release in the harness (the charge-up runs its full CastTime).
**Charged powers (6 Nov).** [V] 493 powers are charge-ups (TargetMethod Smash, `_-e4g`); the harness never released
them, so every heavy ran its whole charge (81 ticks for the unarmed side heavy) and never hit. #6313 @3821-3913
flags the release (`_-e3f` → `_-64U` → `_-43C`) once HeavyAttack (64; 64|512|128 for IsThrow) is not held;
`_-R63` @255-347 calls `_-G5P` #82 once FixedMinChargeTime (`_-l5m`) ticks have passed, which ends the charge
(`_-a6i` = charge ticks) and the ComboName release power starts (#30 `power_timeline.smash_release`, 2326 anchors).
Replay 186: MAM's side heavy is released at 10.528 s and its hit step fires at 10.640 s (clip: the 18-damage hit at
~10.69 s). Aggregate: life 10.6 s (248 early / 2 within 1 s / 1 exact / 1 late / 1 late within 1 s / 1 none).
Not modelled yet: the charge factor of the release (`_-a6i` / `_-I6c` on damage, impulse and `_-Q1n`).
**IsMoveLocked and the action pass (6 Nov).** [V] `move_locked(f, t)` now follows `Entity.IsMoveLocked` #3061:
the power lock, dodging (`_-E6P`), hitstun, `_-u55`, a pending dash (`_-P50`), then `_-q2B` #3084 (a kind 3 / 7
dash within 112 ms); [H] `_-cr`, `_-P4K`, `_-H6I` left out. #6313 computes local 15 (locked, `_-Xb`, `_-f6R`)
before the dodge; a Dodge that ran sets locals 14 / 15 (@2442-2455), so no jump (@2567 / @3445 need local 14
false) and no attack (@2763-2798 / @2968-3003 need local 15 false unless the gravity cancel, local 32) on the same
pass; a started attack sets local 15 (@2932). Also: a CastTime part without a number is 0 (#30). Aggregate:
life 10.6 → 10.2 s (248 early / 2 within 1 s / 4 late). On replay 186 MAM now dashes at 10.336 s instead of
starting the heavy (the clip shows the heavy: open, likely an earlier state difference).
**Order inside a fighter's step (6 Nov).** [V] `Entity._-k5H` #2991 calls `_-1L` (@75, which runs the input pass
`_-51o` first) before the power update `_-Kc._-25` (@522) and the physics `_-8i` (@585). The harness ran the power
update before the inputs; now inputs → power update → physics, so a press seen on the tick a power ends waits one
tick, and a power started by a press gets its first update on the same tick. Aggregate: life 10.0 s (247 early /
2 within 1 s / 4 late / 1 late within 1 s).
**Dodge during a power (6 Nov).** [V] `IsDodgeLocked` #3075 is true while a power runs (`_-Kc._-o3I`); the
harness passed false there, so a fighter could air-dodge in the middle of an attack (replay 186: MAM's up heavy
turned into a 0.3 s FastSide glide off the stage). Aggregate: life 9.9 s (247 early / 2 within 1 s / 5 late).
Seen next on replay 186 (clip vs harness, relative to the stage edge): from 7.5 to 8.5 s the harness MAM moves
~650 units right (air max speed with Right held after BaseAirSideMiss), the clip ~50-100; and it rises ~490
units, the clip ~330. Open.
**The jump guard `_-H5F` (6 Nov).** [V] `Entity.Jump` returns at once when `_-H5F(t, third)` #3065 holds (@36-59):
states other than 0 / 5; IsMoveLocked (or `_-u4F`, `_-Xb`, `_-cr`, `_-C54`) unless the third argument (the squat
release `_-A2X` passes it after `_-I5A` = 0); `_-f6R` > t; airborne with no air jump left and no wall; within 176 ms
(`_-Y35`) of `_-I5A`; within 256 ms (`_-R6Q`) of both `_-I5A` and `_-46I`. The harness had no guard, so a jump
pressed during an attack's recovery fired at once. Replay 186: MAM's jump press at 7.568 s (inside BaseSideMiss)
is now refused, the press at 7.712 s jumps, and MAM lands at 8.688 s — the clip shows the landing at ~8.67 s.
Aggregate: life 10.6 s (247 early / 1 within 1 s / 6 late). [H] `_-u4F`, `_-cr`, `_-C54` false.
