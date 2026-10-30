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
| `hit-detection-verify` | 699 | 0 |
| `prng-order-verify` | 87 | 0 |
| `step-verify` | 159 | 0 |
| `ko-verify` | 290 | 0 |
| `input-buffer-verify` | 341 | 0 |
| `knockback-verify` | 253 | 0 |

`prng-verify`: OK. `python -I -m unittest discover -s tests`: 231 tests pass.

## First smoke test: one fighter falls onto a map (`smoke-fall`, [`tools/bh/smoke.py`](../tools/bh/smoke.py))

One fighter starts at rest on a respawn point and receives no input. Each tick:
1. gravity `_-P5S += 3.75 × 0.384` while below the fall cap 70 (movement-11.00.md);
2. the free move against the map (`air_move.py`, PR #30), against the LevelDesc's static lines, normals
   and candidate grid (`level_collision.py`), through the map ray cast (`raycast.py`).

Landing itself (@8869- of `Entity._-8i`) is not transcribed yet. So the test stops at the first ground
contact. It checks that the feet plus the 1.01 back-off (`_back_off`) lie on the line that stopped the fall.

Local result (aggregate counts only, no names or coordinates):

| | Count |
|---|---|
| LevelDescs | 122 |
| Respawn points | 995 |
| Ground contact | 829 (811 on flat lines, 18 on slopes, 0 on walls) |
| Contact point on the line within 1e-6 | **829 of 829** (largest error 1.8e-15) |
| No contact within 1000 ticks | 166, all on the 21 maps with moving platforms or dynamic lines, which this test leaves out |
| Longest fall | 116 ticks |

So the gravity, sweep, grid and ray cast pieces fit together, and the fall stops on the map geometry.
[H] This only shows that the transcribed pieces agree with the map files. It does not show that they match
the running game. Next: the dynamic lines of moving platforms (`platforms.py`) in the same harness, then
landing (@8869-), then the KO oracle of #27.
