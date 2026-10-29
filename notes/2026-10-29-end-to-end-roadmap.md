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
| 5 | Fighter state dispatch (`_-65w`), power choice (slot → power) | #30 `entity_states.py` (dispatch map), #28 (slots) | dispatch, power start, match start, respawn points mapped; respawn 3 → 0 to confirm |
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

1. **Fighter state transitions.** Mostly done (#30): the dispatch on `_-65w`, the power start chain, match
   start (state 3 then Respawn, two R draws), the respawn point rotation, and state 7 = "Eliminated" (no
   7 → 0 in a normal match). Left: confirm that a normal respawn goes 3 → 0 through `_-k5S._-P3o`
   (SpawnBot `_-P3o` / `_-m1O`).
2. **Animation frame table `_-cA`** (`_-l4X._-54L` #86). It maps ticks since cast to animation frames, from
   CastAnim (`_-HT` / `_-6b`) and the animation's frame data (`_-y1v`: `_-T6`, `_-W1n`, `_-012`). It
   selects the target's hurtbox row (§4 of hit-detection-11.00.md). Needs the `.anm` parser of PR #19.
3. **Flags passed in today**: decoded (#30). `_-wn()` is "airborne after the previous move", `_-5q()` "in
   hitstun" [H], `_-e36()` "on lava"; `_-t46()` / `_-81n()` come from the power and the input handler. A
   simulator keeps them as plain booleans (the camouflage draws from the global generator, not the replay
   one).
4. **Items**: motion of `_-p5k`, pick-up and catch gates (`_-Io` / `_-x5G`), other spawners (`_-33h`).
5. **An integration branch** that merges #16–#30 so that one harness can import every module, then a
   first smoke test: one fighter, no attacks, falling onto a map's spawn platform. Check the landing
   height against the map geometry. That checks the movement + map chain before any KO oracle comparison.

## Rules that stay in force

- Never modify the game folder; read-only.
- Publish only inside this repository; no game values, replays or player names in the repository or
  on Discord (column names and aggregate counts only).
- Label claims [V] / [H]; code, comments and docs in English.
