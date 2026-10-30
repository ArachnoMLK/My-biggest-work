# End-to-end roadmap: what one simulated tick needs (patch 11.00)

Status on 2026-10-29, evening. Goal: replay a `.replay` file's inputs through a Python re-implementation and
reproduce every KO tick of the KO oracle (PR #27). Every row below is static evidence from the pinned ABC
(`7d308423…`). Nothing has been run against the game. A row is "transcribed" when a function reproduces the
bytecode arithmetic and a `*-verify` command pins it.

## One tick, in the game's order (`_-h3U._-01I` #3336, tick-loop-11.00.md)

| Step | What happens | Transcribed in | Status |
|---|---|---|---|
| 3 | Moving platforms and their lines (`_-22K._-d4u`) | #30 `platforms.py` | done (rotation on lines open) |
| 5 | Inputs: replay timeline → keys, buffer, press edges | #28 `input_buffer.py`, #16 bit names | done |
| 5 | Fighter state dispatch (`_-65w`), power choice (slot → power) | #30 `entity_states.py` (dispatch map), #28 (slots) | dispatch, power start, match start, respawn points, respawn drone 3 → 4 → 0 / 5 (`spawn_bot.py`) mapped |
| 5 | Movement: impulses, friction, gravity, ground walk | #4 / #23 / #26 `step.py` | done (shape) |
| 5 | Free move against the map: sweeps, back-off, response (ceiling, slope, walls, bounce) | #30 `air_move.py` | done (`_-wn()`, `_-t46()` and other flags passed in) |
| 5 | Map: LevelDesc lines, curves, default normals, grid, ray cast | #20 (flags), #30 `level_collision.py`, `raycast.py` | done |
| 6 | Power timeline: CastTime steps, one hit test per step start | #30 `power_timeline.py`, `power_data.py` | done (end reasons `_-O5N`, step cap `_-Q1n`) |
| 6 | Hit areas (AoE capsules per TargetMethod), team mask, line of sight, re-hit rule | #30 `hitdetect.py` | done |
| 6 | Target hurtbox: hurtbox type by power, **row by animation frame `_-c2l`** | #30 (rows), — | **frame table `_-cA` missing** (needs `.anm` frame counts, see #19) |
| 7a | Thrown items and projectiles | #30 (`_-p5k._-h20` geometry) | item motion and catch gates missing |
| 7b | Queued hits → damage, knockback, DI, hitstun, flight | #29 `knockback.py`, #22 | done |
| — | KO bounds, commit order, respawn | #25 `ko.py` | done |
| — | PRNG and its draw order | #24 (merged) | done |
| — | Legend stats | #17 `stats.py` | done |

## Missing pieces, by priority

1. **Fighter state transitions.** Done (#30): the dispatch on `_-65w`, the power start chain, match start
   (state 3, then `Respawn` with `eliminated` = false, two R draws), the respawn point rotation, state 7 =
   "Eliminated", and the respawn drone `SpawnBot` (`spawn_bot.py`): instant 0 in some modes, otherwise come
   down / carry / drop phases, state 4 while held, then 0 (or 5). Left as data: the scoring-type durations.
2. **Animation frame table `_-cA`.** Done (#30, `anim_frames.py`, doc §1.3): `_-l4X._-54L` from the CastTime
   key frames (`D@F`, `D:R@F-G`), the recovery ticks and 0.384 frames per tick, with the CastAnim "L" loop
   between the `.anm` animation's `_-T6` / `_-W1n` (header u32 2 and 3, PR #19). Left: check on real data
   that the table's frame − 1 matches the 1-based rows of `_-P6e`.
3. **Flags passed in today**: decoded (#30). `_-wn()` is "airborne after the previous move", `_-5q()` "in
   hitstun" [H], `_-e36()` "on lava"; `_-t46()` / `_-81n()` come from the power and the input handler. A
   simulator keeps them as plain booleans (the camouflage draws from the global generator, not the replay
   one).
4. **Items.** Mostly done (#30, `items.py`): thrown item speeds and mask, ItemType columns, the per-target
   gates (`_-Io` / `_-x5G`, catch, grace, boomerang). Since then also done: the item ground walk, map sweeps,
   landing / impact / bounce, path behaviours (all five), special impacts, the throw and its spawn point, and
   the secondary powers of `_-33h`.
5. **An integration branch.** Done: `integration-11.00` (draft PR #31, do not merge) merges #16–#30;
   11 verify commands at 0 mismatches, 231 tests. First smoke test `smoke-fall`: one fighter falls from every
   respawn point of the 122 local maps; 829 of 829 ground contacts end on the line within 1e-6; the 166 falls
   without contact are all on maps with moving platforms (dynamic lines left out). With the moving platforms'
   lines: 965 of 965 contacts on the line; then 60 standing ticks (step-start landing `_-P5S` = 0, no gravity on
   a ground line, both in #30): all 794 flat fixed-ground cases stay still. Then lava as hits and the platform
   carry (#30): 954 of 954 keep the ground, 146 of 146 keep their height on moving lines; the 14 gentle hard
   slopes creep [H]. Next: the KO oracle of #27.

## Rules that stay in force

- Never modify the game folder; read-only.
- Publish only inside this repository; no game values, replays or player names in the repository or
  on Discord (column names and aggregate counts only).
- Label claims [V] / [H]; code, comments and docs in English.
