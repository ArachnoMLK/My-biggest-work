### Relay — Claude Opus 5.5 (Claude Code, scheduled run) — 2026-10-28 — patch 11.00

**Task:** Q1 (map the replay reader). Full table: [`docs/code-map-11.00.md`](../docs/code-map-11.00.md).
Pin: 11.00 / abc `7d308423…6db9`.

**Done:**
- [V] Load path: `_-Y26._-I5w` #12889 / `_-u52` #12895 → `_-Y26._-B1a` #12856 (skip if name has `[sdr]`, else `uncompress` then XOR `_-S45._-031` #6715) → bit reader `_-Lg` (class 31, #610–631, MSB-first reader+writer) → `_-h3U._-C21` #3388 → parser `_-24q._-b2L` #6699 (`abc-disasm --method 6699`).
- [V] `_-24q._-b2L` reads every object type with one `lookupswitch`: 1 inputs → `_-t2P`/`_-344` (per-entity time/keys vectors), 3 header (`_-669` = random_seed), 4 game data (`_-d3Y` settings, `_-T6w` LevelType, entities `_-v2T` in `_-j1p`, checksum via `_-S45._-S4h` #6716), 5 → `_-a4V`/`_-m12`, 6 → `_-G5C`/`_-F39`/`_-m3w`, 7 → `_-84R`/`_-f37`, 2 end, 0 = "stop, length = last input". Version mismatch → `_-n4v` → "Replays from previous versions are incompatible".
- [V] `_-S45._-X4` #6710 is the writer of type 1 (5-bit entity, i32 time, bit, 14-bit keys): same layout as our parser.
- [V] Playback start `_-h3U._-T12(replay, seed)` #3624: sets replay flag `_-w35 = 1024`, creates one Entity per player, pushes each input as `new _-k3h(time, keys)` (class 265) into `Entity._-R5q` (an `_-i4Z`, class 347) with `_-c41` (sorted insert).
- [V] Query: `_-i4Z._-7z(t)` #6323 = state of the last record with time ≤ t; in replay mode (flag 1024…) it walks a cursor `_-e3n` both ways (rewind-capable).
- [V] Per-tick chain: `_-h3U._-01I` #3336 (inner loop `t += 16`) → `Entity._-k5H` #2991 → `Entity._-1L` #2986 → `_-i4Z._-51o(t)` #6313 → `_-7z(t − 16·i)` for the last N ticks → Jump/Dodge/attack triggers. Each link has exactly one caller (`abc-find <name> --member`).
- [V] Seed: `_-h3U._-Y3u(level, seed)` #3348 stores `_-669 = seed` (random `mod 2147483647` if null) and seeds `_-3z._-13p(seed)` and `_-s3D._-22._-24O(seed)`; `_-24O` is also called by `Random.<init>` #1008.
- [V] New tool `bht.py abc-refs --method N` (members and constants a method touches) + test; 7 tests OK.
- [H] `_-h3U._-01I` is the fixed 16 ms simulation step; `_-h3U._-k3g(t)` = rollback to t; `_-I6Z.Tick` #14085 is the on-screen input display (gives a key-bit → button-index map).

**Evidence:** method ids above; `python -I tools/bht.py abc-disasm --method N`, `abc-refs --method N`, `abc-find NAME --member`.

**Dead ends:** `_-I6Z.Tick` looks like an input feeder (reads `_-R5q._-j1R` each tick) but it is a UI widget (super `_-x1d` with Show/Hide/SetPosition), not the simulation. `_-a1N._-Q5h` also reads `_-7z` but is a clip/recording feature.

**Next:** Q2 — read `_-h3U._-01I` #3336 (2,199 lines): where the step start time and count come from, and the update order around `Entity._-k5H` (offset 2751). In parallel Q3 can start from `Random.<init>` #1008 and `_-24O`.

**Questions for humans:** none.
