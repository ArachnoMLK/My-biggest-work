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
| `hit-detection-verify` | 1103 | 0 |
| `prng-order-verify` | 87 | 0 |
| `step-verify` | 159 | 0 |
| `ko-verify` | 290 | 0 |
| `input-buffer-verify` | 341 | 0 |
| `knockback-verify` | 253 | 0 |

`prng-verify`: OK. `python -I -m unittest discover -s tests`: 286 tests pass.

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

## First check against real replays: KO gaps (`ko-gap-check`, [`tools/bh/ko_gaps.py`](../tools/bh/ko_gaps.py))

The KO commit calls `Respawn` in the same tick, and the drone then comes down, carries and drops the fighter
(spawn_bot.py, PR #30). So two KO faces of the same victim (oracle.py, PR #27) are at least `respawn_ms`
apart. That time comes from the durations of the replay's scoring type (ScoringTypes.xml, by `ScoringID`).
With the defaults and a spawned fighter, it is 2000 + 3000 + 700 = 5700 ms.

Local result (756 patch 11.00 replays, aggregate only):

| | |
|---|---|
| Scoring types with at least one gap | 4 |
| Gaps between two KOs of the same victim | 3,241 |
| Gaps shorter than the predicted drone time | **0** |
| Smallest margin | 172 ms |
| Replays with a first KO | 688 |
| First KOs before match start (256 ms) + the first drone trip (4700 ms by default) | **0** (smallest margin 3,268 ms, a loose bound) |

This is a one-sided check. The replays allow the transcribed drone time, but they do not show it is exact:
the margin also contains the time needed to be knocked out again. It is the first comparison of a
transcribed piece with the replays' own records.

