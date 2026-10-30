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
| `hit-detection-verify` | 714 | 0 |
| `prng-order-verify` | 87 | 0 |
| `step-verify` | 159 | 0 |
| `ko-verify` | 290 | 0 |
| `input-buffer-verify` | 341 | 0 |
| `knockback-verify` | 253 | 0 |

`prng-verify`: OK. `python -I -m unittest discover -s tests`: 235 tests pass.

## First smoke test: one fighter falls onto a map (`smoke-fall`, [`tools/bh/smoke.py`](../tools/bh/smoke.py))

One fighter starts at rest on a respawn point and receives no input. Each tick:
1. gravity `_-P5S += 3.75 × 0.384` while below the fall cap 70 (movement-11.00.md);
2. the free move against the map (`air_move.py`, PR #30), against the LevelDesc's static lines, normals
   and candidate grid (`level_collision.py`), through the map ray cast (`raycast.py`).

At the first ground contact, the test checks that the feet plus the 1.01 back-off (`_back_off`) lie on the
line that stopped the fall. It then runs 60 more ticks with no input. At each step start, the landing
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
| Ground kept for the 60 standing ticks | — | 955 of 965 (the 10 others are on moving platforms: carrying the fighter along is not modelled) |
| Exactly still (within 1e-6) on fixed ground | — | 794 of 812: **all 794 flat cases**; the 18 that move are the 18 slopes (sliding is not in this harness, largest drift 24.4) |

Of the 30 points without contact: 5 get one with another platform phase (t0 between 0 and 60 s), and 25,
on 4 maps, have no line below them at t = 0.

So the gravity, sweep, grid and ray cast pieces fit together, and the fall stops on the map geometry.
[H] This only shows that the transcribed pieces agree with the map files. It does not show that they match
the running game. Next: the slope slide and the platform carry while standing, then the KO oracle of #27.
