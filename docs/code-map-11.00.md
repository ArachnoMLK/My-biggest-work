# Code map — patch 11.00 (Q1: the replay reader)

Pin: **patch 11.00 / abc `7d308423eaebcc82dfdda4ecc0e57d3abe78569534023aa7f9d776f626356db9`**
(`work/abc/summary.json`). All names below are obfuscated and change with each patch; method ids
are only valid for this ABC.

Commands used (from the repository root, after `python -I tools/bht.py abc-extract`):

```
python -I tools/bht.py abc-disasm --method N        # full listing
python -I tools/bht.py abc-disasm --class NAME      # every method of a class
python -I tools/bht.py abc-refs --method N          # members/constants a method touches (new)
python -I tools/bht.py abc-find NAME --member       # every method that references NAME
```

"Offset" below means the instruction offset printed by `abc-disasm`.

## Pipeline in one picture

```
file bytes ──_-Y26._-B1a──> zlib uncompress + XOR (_-S45._-031)        (#12856, #6715)
           ──new _-Lg(bytes)──> MSB-first bit reader                    (#610…#631)
           ──_-h3U._-C21(name, reader)──> new _-24q; _-24q._-b2L(name, reader, headerOnly)   (#3388, #6699)
           ──_-h3U._-T12(replay, seed)──> level + seed (_-Y3u), one Entity per player,
                 each recorded input → new _-k3h(t, keys) → Entity._-R5q (an _-i4Z) via _-c41   (#3624)
each simulation step: _-h3U._-01I ──t += 16──> Entity._-k5H(t) → Entity._-1L(t)
                 → _-i4Z._-51o(t) → _-i4Z._-7z(t − 16·i) = key state at time t   (#3336, #2991, #2986, #6313, #6323)
```

## (a) Reading the file and each object type

| Class.method | id | Role | Status |
|---|---|---|---|
| `_-Y26._-I5w` | 12889 | Replay browser screen: opens the selected file (`FileStream.readBytes`), decodes it, builds `_-Lg`, calls `_-N1k._-C21(name, reader)`. Shows "Error in reading replay" on exception. | [V] `abc-disasm --method 12889` |
| `_-Y26._-u52` | 12895 | Same path for an asynchronously loaded file (`Event.COMPLETE`, `.data`). | [V] `abc-disasm --method 12895` |
| `_-Y26._-B1a` | 12856 | Decoder. If the file name contains `[sdr]` it returns untouched; otherwise `ByteArray.uncompress()` then `_-S45._-031(bytes)`. | [V] `abc-disasm --method 12856` |
| `_-S45.static._-031` | 6715 | XOR of the byte array with the static table `_-S45._-Ja` (indexed `i mod length`). Same order as `tools/bh/replay.py` (zlib, then XOR). | [V] for "loop over bytes with `_-Ja`" (`abc-refs --method 6715`), [H] for "it is the 64-byte KEY of replay.py" (table values not compared) |
| `_-Lg` (class 31) | 610–631 | Bit-stream reader *and* writer over a `ByteArray` (`_-L5F`); `_-gg` = read bit position, `_-Q4N` = write bit position. MSB-first. No decompression or XOR inside. | [V] `abc-disasm --class 31` |
| `_-Lg._-C4y(n)` | 628 | Read n bits as uint (= `BitReader.bits`). | [V] |
| `_-Lg._-a16()` | 623 | Read 32 bits, signed int (`readInt`). | [V] |
| `_-Lg._-X3I()` | 622 | Read 16 bits, signed short. | [V] |
| `_-Lg._-l4W()` | 621 | Read string: 16-bit length + UTF-8 bytes. | [V] |
| `_-Lg._-F6d()` | 624 | Read float32 (unused by the replay reader). | [V] |
| `_-Lg._-b5p(n, v)`, `_-I1l`, `_-w4F` | 619, 614, 612 | Write n bits / int / string (replay *writer* side). | [V] |
| `_-h3U._-C21(name, reader)` | 3388 | Creates `_-24q`, calls `_-b2L`. On success: `_-w1r._-qz()`, `_-d3Y._-82w(replay._-d3Y)` ([H] apply the replay settings), `_-T12(replay, replay._-669)` (start playback with the seed). On failure: "Replays from previous versions are incompatible" if `_-n4v`, else "Error in reading replay". | [V] `abc-disasm --method 3388` |
| `_-24q` (class 373) | 6696–6703 | The replay object (all parsed data). | [V] |
| `_-24q._-b2L(name, reader, headerOnly)` | 6699 | **The replay parser.** Reads `u32` version into `_-Dy`, compares with `_-z2k._-n1F` (current build); mismatch → `_-n4v = true`, returns false. Then loops while `bytesAvailable > 0`: 4-bit type, `lookupswitch` (offset 310). The third argument skips storing inputs (header-only scan). Sets `_-Y2j` = valid. | [V] `abc-disasm --method 6699` |
| type 1 — Inputs | 6699 @374–648 | While bit = 1: 5-bit entity, `i32` count, then count × (`i32` time ms, bit, 14-bit keys if bit else 0). Times → `_-t2P[entity]`, keys → `_-344[entity]` (both `IntMap<Vector.<uint>>`); keeps the max time in a local. | [V] |
| type 2 — End | 6699 @652 | Stops the loop. | [V] |
| type 3 — Header | 6699 @660–762 | `_-669` = random_seed (`i32`), `_-f4z` = playlist id, `_-BB` = playlist name (only if id ≠ 0), `_-B4E` = online bit. | [V] layout; field meanings from `docs/replay-format.md` |
| type 4 — GameData | 6699 @766–1412 | `_-d3Y._-b2L(reader)` (settings parse their own 15 values), `i32` level id → `_-T6w = LevelType._-s5b[id]`, `i16` hero count (> 5 → invalid). Then entities while bit = 1, each an `_-v2T`: id → `_-hw` (ordered list) and keys of `_-j1p` (data), second `i32` → `_-R4a[id]`, name → `_-F2S[id]`, six `i32` fields, 8 `i32` in `_-i10`, two `i16`, nested `_-n3q._-b2L`, `i16`, two `i32`, then `hero_count` × `_-C5l` heroes (`HeroType` id via `_-R4b`, costume id checked against `CostumeType._-23Z`, 2 more `i32`), bit → id also pushed to `_-044` (likely bots), `_-L1j = _-t4b._-Og(reader)`. Ends with `i32` checksum. `_-O19` = entity count. | [V] layout, [H] meaning of `_-044` |
| checksum | 6699 @1817–1907, `_-S45.static._-S4h` 6716 | If not header-only: valid only if the checksum equals `_-S45._-S4h(_-j1p, level._-L2H, hero_count)`. | [V] call; formula in `replay.py` not re-derived here |
| type 5 — KO faces | 6699 @1552–1780 | While bit = 1: 5-bit entity, `i32` time. Entities → `_-a4V`, times → `_-m12`, inserted **sorted by time** with `_-A6B._-p3g` (insert-at). | [V] |
| type 6 — Results | 6699 @1416–1548 | `_-G5C` = length (`i32`), scores while bit = 1 (5-bit entity → `i16`) in `_-F39`, `_-m3w` = `i32`. A later type 6 overwrites the previous one. | [V] |
| type 7 | 6699 @1552–1780 | Same code as type 5, other lists: entities → `_-84R`, times → `_-f37`. | [V] |
| type 0 | 6699 @342 | `_-G5C` = max input time, `_-m3w` = 1, stop (treated as a truncated replay that is still playable). | [V] code, [H] intent |
| type 8 / other | 6699 @1784 | Stop, invalid. | [V] |
| `_-24q._-V4r` | 6702 | Resets every list/map of the replay object. | [V] `abc-refs --method 6702` |
| `_-24q._-73z(id)` | 6700 | `_-044.indexOf(id) >= 0`. | [V] |
| `_-24q._-C1g` | 6701 | Builds a display string ("A - B", "Unknown") from `_-F2S` and `_-F39` (scores). | [V] constants, [H] use |
| `_-S45._-X4` | 6710 | **Replay writer of type 1**: walks every entity's `_-R5q._-j1R` and writes `_-b5p(5, entity)`, `_-I1l(time)`, flag bit, `_-b5p(14, keys)`. Mirror image of the reader. | [V] `abc-refs --method 6710` (constants 5, 14, 1) |

## (b) The per-entity input timeline

| Class.method | id | Role | Status |
|---|---|---|---|
| `_-h3U._-T12(replay, seed)` | 3624 | Starts playback: mode string `'replay'`, `_-331 = replay`, `_-w35 = 1024` (**replay mode flag**), resets the timers (`_-94N`, `_-hU`, `_-rz`…), `_-Y3u(replay._-T6w, seed)`. For each id of `replay._-hw`: `Entity = this._-724(name, id, Entity._-X5p \| Entity._-8, data)`; then for every recorded (time, keys) pair `entity._-R5q._-c41(new _-k3h(time, keys))`. | [V] `abc-disasm --method 3624` |
| `_-k3h` (class 265) | 4862 | One input record: `_-J6B` = time ms, `_-c3T` = 14-bit key state, `_-Y1l` = wall clock `getTimer()` at send (local online player only; ping). | [V] ctor; [H] for `_-Y1l` meaning |
| `Entity._-R5q` : `_-i4Z` (class 347) | 6310–6335 | Input buffer of one entity. `_-j1R` = confirmed records sorted by time, element 0 is a sentinel `_-k3h(0,0)`; `_-t4x` = predicted (local, unconfirmed) records; `_-e3n` = read cursor (replay path); `_-66U` = current key state; `_-O1I` = key states of the last N ticks. | [V] subagent read of `abc-disasm --class _-i4Z`; spot-checked by me (`abc-find _-7z --member`, `pushint 1024` in #6323) |
| `_-i4Z._-c41(rec)` | 6321 | Sorted insert into `_-j1R`. | [V] |
| `_-i4Z._-7z(t)` | 6323 | **Key state at time t**: last record with time ≤ t. If `_-w35` has a replay/spectate bit (1024, 2048, 8192, 262144, 524288) it walks `_-j1R` from cursor `_-e3n` forward or backward (supports rewind); else it scans `_-j1R` and `_-t4x` backward and prefers the newer of confirmed/predicted. | [V] (offsets 62–699 of #6323) |
| `_-i4Z._-A3G(t, keys)` | 6316 | Network confirmation of an input: replaces the prediction, inserts into `_-j1R`, returns "changed". Calls `_-h3U._-k3g(t)`. | [V] code, [H] `_-k3g` = "roll back to t" |
| `_-i4Z._-a2I(t)` | 6317 | Samples the local controller each step; on change creates `_-k3h(t, keys)` (to `_-j1R` offline/replay, to `_-t4x` + network send online). Called from `_-h3U._-01I`. | [V] |

## (c) Handing inputs to fighters every 16 ms

| Class.method | id | Role | Status |
|---|---|---|---|
| `_-h3U._-01I` | 3336 | **Fixed-step scheduler (Q2).** Aligns target/start to 16 ms, computes `floor(max(target - start, 0) / 16)`, and advances tick time by 16 per iteration. Calls `Entity._-k5H(t)` for all entities, then a separate `Entity._-10(t)` pass, global processing, and `Entity._-J2g(t)`. Controller sampling remains outside the inner loop. See [tick-loop map](tick-loop-11.00.md) for gates, checkpoints and exact order. | [V] `abc-disasm --method 3336`, offsets 417–493, 1838–1922, 2725–2888, 4073–4077 |
| `Entity._-k5H(t)` | 2991 | Per-entity step; calls `Entity._-1L(t)`. Only caller: `_-h3U._-01I`. | [V] `abc-find _-k5H --member` |
| `Entity._-1L(t)` | 2986 | Calls `_-R5q._-51o(t)` (input decoding) before the rest of the entity update. Only caller: `_-k5H`. | [V] `abc-find _-1L --member` |
| `_-i4Z._-51o(t)` | 6313 | **Input → action decoder.** Fills `_-O1I[i] = _-7z(t − 16·i)` for the last N ticks (N = 5, or 9/10/11/13 depending on mode), sets `_-66U`, detects key edges and triggers `Entity.Jump`, `Entity.Dodge`, attacks/throws (helpers #6331–#6335). Only caller: `Entity._-1L`. | [V] caller; [V] subagent for the 16·i loop; [H] for the exact action list |
| `_-I6Z.Tick` | 14085 | *Not simulation*: on-screen input display (class extends UI widget `_-x1d`). It looks up the followed entity's last record ≤ current time and lights buttons. Useful as a **key-bit map**: bits `1\|32`→0, `2`→1, `4`→2, `8`→3, `16`→6, `64`→8, `128`→7, `256`→5, `512`→4 (button indices of the widget). | [V] mapping offsets 530–909; [H] button names |
| `_-a1N._-Q5h` | 1760 | Extracts a clip of inputs between two times using `_-7z(tick·16)` with a 60-tick lead-in (training/recording feature, not the replay player). | [V] code, [H] feature |

## (d) The header `random_seed`

| Class.method | id | Role | Status |
|---|---|---|---|
| `_-h3U._-C21` → `_-T12(replay, replay._-669)` | 3388, 3624 | The header seed is passed to playback start. | [V] |
| `_-h3U._-Y3u(level, seed)` | 3348 | Builds the level (`new _-a2j(level)` into `_-I1f`). If seed is null: `seed = _-A6B._-PW._-f4c() mod 2147483647`. Stores `_-h3U._-669 = seed`, then **seeds two generators**: `_-3z._-13p(seed)` and `_-s3D._-22._-24O(seed)`. | [V] `abc-disasm --method 3348` |
| `_-24O` | — | Also called by `Random.<init>` (#1008, readable class name), `_-h3U._-425`, `_-E1V._-13p`, `_-Mr.static._-n5z`: the PRNG seeding method. Starting point for Q3. | [V] `abc-find _-24O --member`; [H] that `_-s3D._-22` is a `Random` |

## Open points

- [V] Q2 confirmed `_-h3U._-01I` as the fixed 16 ms scheduler and mapped its clock bounds and pass order; see [tick-loop map](tick-loop-11.00.md). Full physics, hit and KO semantics remain open.
- [V] `_-h3U._-k3g` #3594 schedules restoration using a rounded checkpoint anchor and `_-Kt`; #3336 restores checkpoints before re-running forward ticks. [H] Snapshot state completeness and deterministic equivalence remain untested; see the tick-loop map for guards and offsets.
- [H] Meaning of type 7 lists (`_-84R`/`_-f37`) and of `_-044`.
- Not done: comparing `_-S45._-Ja` with the XOR key of `replay.py`, and `_-S45._-S4h` with the checksum formula (both cheap with a small script that reads the static initializer of `_-S45`).
