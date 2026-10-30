# Plan: first two-sided replay check (one self-KO, patch 11.00)

Written 30 Oct 2026 night, after roadmap steps 1–5. Goal: replay the inputs of one simple local replay with
the merged pieces of `integration-11.00` (draft PR #31), and compare the KO tick of one victim with its
recorded KO face (`oracle.ko_ticks`, PR #27). The checks done so far (`smoke-fall`, `ko-gap-check`) are
one-sided; this one can fail.

## Pick the replay (aggregate search, nothing published)

- Patch 11.00 (`version` 271), 1v1, a scoring type with the default drone durations (STOCK = 2).
- A victim whose **first** KO is a self-KO: no hit received before it. The KO list has (victim, ms) only.
  [H] The KO event type (1 opponent / 2 self / 9 team) lives in the face writer `_-S45._-04F` #6711
  (ko-11.00.md §6). Check whether `replay.parse` keeps it; if not, pick a victim whose opponent pressed
  no attack input before that KO (`input_buffer.state_at`).
- The simpler the better: a map without moving platforms, the victim walking or jumping off a ledge.

## Pieces already transcribed (module → what it gives)

| Need | Module (PR) | Entry points |
|---|---|---|
| Match start, first drone | `entity_states` (#30), `spawn_bot` (#30) | `MATCH_START_MS`, `respawn_index`, `Drone.place` / `tick`, `scoring_rules`, `respawn_ms` |
| Respawn after a KO | `spawn_bot` (#30) | same; KO commit → `Respawn` in the same tick |
| Gravity, fall cap | movement-11.00.md (#16 / #26), `smoke.fall` (#31) | 3.75 × 0.384 while `_-P5S` < 70 (85 with Drop) |
| Step order | entity-step-11.00.md (#26), `step` | `fold_impulse`, `speed_cap`, `clamp` |
| Ground walk, free move, landing | `air_move` (#30) | `ground_walk`, `air_move`, `respond`, `ground_reset`, `gravity_applies` |
| Map | `level_collision`, `platforms`, `raycast` (#30) | `static_lines`, `compute_normals`, `Grid`, `parse_platforms`, `carry` |
| Inputs | `replay` (#14), `input_buffer` (#28), `commands` (#16) | `parse` → `inputs`, `state_at`, `buffered_presses`, bit names |
| KO test | `ko` (#25) | `ko_mask(x, y, cam, kill, exact, top_allowed)`, commit order (ko-11.00.md §5) |
| KO oracle | `oracle` (#27) | `ko_ticks`, `compare` |
| Legend stats | `stats` (#17) | `fighter_stats(levels, stat_types)` (RunSpeed, Friction, …) |

## Pieces missing (in this order)

1. ~~Horizontal movement as code~~ — done: `tools/bh/horizontal.py` in #30 (max speed, friction choice and
   application, acceleration and its clamp; 47 anchors). Still open: where `_-141()` (facing) and `_-81n()`
   (a horizontal input held) are set from MoveLeft / MoveRight.
2. ~~Jump~~ — done in #30 (`tools/bh/jump.py`): the squat (`_-Xb` = 1 / 2 / 3, release at `_-I5A` + 32 through
   `_-A2X`, +64 ms on landing, 192 ms lock), ground / dash (57 × (0.86 | 1), 170), wall (53 × k, ± 48) and air jumps
   (57 / 65 × k). Left for the harness: feeding the press of bit 16 (#28) into `Jump(t)`.
3. ~~KO bounds data~~ — done in #31 (`tools/bh/level_bounds.py`: CameraBounds + LevelType kills; 989 of 995
   respawn points inside, 160 of 166 falls into the void end in a bottom KO). Open [H]: one map has 6 respawn
   points outside its static kill box.
4. **The harness.** One tick = platforms (`_-d4u`, carry) → per fighter: inputs (`_-1L`) → state
   dispatch (`_-k5H`: drone phases while state 3 / 4, movement in 0 / 5) → KO test. Start at t = 0 with
   the match start at 256 ms.
   Under way on `integration-11.00`: `tools/bh/harness.py` (one fighter, left / right / jump, wall contact and
   wall jumps, ring-out test; no replay inputs, real stats, drone / respawn, KO commit or powers yet).
5. **Compare.** The predicted KO tick of the victim against the face; aggregate over a few replays.

## Open points that may show up

- The slow creep on gentle hard slopes [H] (integration-11.00.md).
- Floors whose normal is −0.9999999999999999 (items micro-bounce) [H].
- The drone timing uses the flags `_-nN`; the first trip runs with flag 1 (`_-44x`) clear [H].
