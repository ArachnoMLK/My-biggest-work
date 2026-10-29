# Match PRNG draw order — patch 11.00 (Q3, static)

Pin: **patch 11.00 / ABC SHA-256
`7d308423eaebcc82dfdda4ecc0e57d3abe78569534023aa7f9d776f626356db9`**. Method ids, obfuscated names
and offsets ("@N", as printed by `abc-disasm`) apply only to this ABC.

This page places the draws of the two replay-seeded generators of [prng-11.00.md](prng-11.00.md)
(**R** = rules `_-h3U._-s3D._-22`, **I** = items `_-h3U._-3z._-22`) on the tick phases of
[tick-loop-11.00.md](tick-loop-11.00.md). It is **static bytecode evidence**: call sites, guards and
the order of instructions. It is not a dynamic draw schedule; neither game nor bytecode was executed
for these ordering claims, and there is no
runtime oracle. A "[V]" below means "the bytecode has this shape", checked by the command given.

## Reproduce

From the repository root, with the pinned patch installed (`BRAWLHALLA_DIR` set):

```text
python -I tools/bht.py abc-extract                 # sha256 must be the pin above
python -I tools/bht.py prng-order-verify           # 87 anchors, 10 reference sets, 9 slot types
python -I tools/bht.py abc-disasm --method 3336    # scheduler: phases 3, 4, 9
python -I tools/bht.py abc-disasm --method 5131    # _-z1C._-O4q, the lesson gate
python -I tools/bht.py abc-disasm --method 5129    # _-z1C._-44D -> MessageTrigger.Tick
python -I tools/bht.py abc-disasm --method 5809    # MessageTrigger.Tick, R draw @731
python -I tools/bht.py abc-disasm --method 3624    # replay start _-T12: _-w35 = 1024
python -I tools/bht.py abc-disasm --method 3630    # lesson start _-m3D: _-w35 = 0x1000000
python -I tools/bht.py abc-disasm --method 3626    # _-f3N: 1024 -> 2048, saves _-ce
python -I tools/bht.py abc-disasm --method 3337    # frame dispatch on _-w35
python -I tools/bht.py abc-disasm --method 3335    # _-M4q: _-01I then the screen stack
python -I tools/bht.py abc-disasm --method 9548    # _-4p._-w10: OnTickScreen of every screen
python -I tools/bht.py abc-disasm --method 10946   # ScreenScoreboard.OnTickScreen -> _-Y15
python -I tools/bht.py abc-disasm --method 13733   # _-9D._-Y15, R draws @433 and @651
python -I tools/bht.py abc-disasm --method 4879    # _-E1V._-O3d -> _-96d, _-u43
python -I tools/bht.py abc-find _-Y15 --member     # 1 method (#10946); same for _-44D, _-O3d, _-N13
python -I tools/bht.py abc-find "[ScreenScoreboard.hx] ScoringType "   # -> a _-y4L method
python -I tools/bht.py abc-find "[LessonManager] AddMarker() Unhandled marker type: "  # -> a _-z1C method
```

`prng-order-verify` exits 0 when every pinned anchor, sole-reference set and slot type holds, 1 on any
mismatch or missing method, 2 for an ABC that is not pinned. Its groups are the headings of §2–§5.

## 1. Result

| # | Claim | Status |
|---|---|---|
| 1 | Within one scheduler tick (#3336), the identified R/I entry points run in this order: phase 3 `_-s3D._-u1O(t)` (R side, @2624, skipped when `_-O4t._-O4q()`), phase 4 `_-3z._-O3d(t, …)` (I, @2695), phase 9 **either** `_-O4t._-44D(t)` (lesson, @2992) **or** `_-s3D._-m4d(t)` (R side, @3009), chosen by `_-O4t._-O4q()` @2973. Each of `_-u1O`, `_-O3d`, `_-m4d`, `_-44D` is referenced only by #3336. | [V] `prng-order-verify` |
| 2 | `MessageTrigger.Tick` (#5809, R draw @731 to pick a random `;`-separated message) is called only from `_-z1C._-44D` @92, i.e. only in phase 9 when `_-O4q()` is true. | [V] (name-based, see limit L4) |
| 3 | `_-O4q()` is **false** whenever `_-w35` ∈ {1024, 2048}, and whenever `_-z1C._-3I` is null. Replay start sets `_-w35 = 1024`; the replay-side writers found keep 1024 or set 2048. Hence on that path the lesson branch, and with it every `MessageTrigger.Tick` draw, does not run. | [V] for the shapes; boundary in L1 |
| 4 | The identified call to `_-9D._-Y15` (#13733, victory-taunt pick, 0–2 direct R draws) is from `ScreenScoreboard.OnTickScreen` (#10946 @334), a **per-frame screen tick outside the 16 ms step**: `_-M4q` #3335 runs the tick batch `_-01I` @1815 and then the screen stack `_-4p._-w10` @2556. On this path the draws fall *between* frame batches. | [V] (name-based, see L4) |
| 5 | Whether the scoreboard screen is on the stack during replay playback, and if so before or after the last gameplay-relevant R-drawing tick, is **unknown**. The `_-vs + 450` update window in Q2 means that being after the match-result flag alone does not settle this. | unknown; [V] window in tick-loop-11.00.md |
| 6 | Item seeding draws `_-Y1h` (I draw 0) and `_-5J` (I draw 1) are two per-lane cached values; they are redrawn in phase 4 by `_-96d` then `_-u43` (both called only by `_-O3d`), each after an `_-e3K(…, 4 args)` call. | [V] shape; [H] meaning |

Net answer to the Q3 question: the lesson/trigger path cannot consume R during a replay as long as
`_-w35` keeps a replay value (claim 3); the scoreboard taunt path can consume R only outside the fixed
step and only while that screen is ticking (claim 4, boundary claim 5).

## 2. Lesson gate: `MessageTrigger.Tick`

| Method / offsets | What | Status |
|---|---|---|
| `_-h3U` slot types | `_-O4t : _-z1C`, `_-s3D : _-99`, `_-3z : _-E1V`, `_-w35 : uint` (trait types; resolves Q2's "[H] slot types not checked" for these three receivers) | [V] `prng-order-verify` (slot check) |
| `_-z1C` | LessonManager: its methods hold `[LessonManager] …` strings; slots `_-3I : _-S3O`, `_-c35 : Vector.<MessageTrigger>` | [V] `abc-find` on the string, slot check |
| `_-z1C._-O4q` #5131 | @2–17 returns false if `_-3I == null`; @29–46 returns true if `_-w35 & 0x1000000`; @50–77 else, if `_-w35 & 32`, returns `(_-ce & 0x1000000) != 0`; else false | [V] |
| `_-z1C._-44D` #5129 | @6–24 returns if `_-N1k._-vs != 0` (after match end); @43–99 loops `_-c35` in index order, each `MessageTrigger.Tick(t)` @92 | [V] |
| `MessageTrigger.Tick` #5809 | @704–731 `R = _-N1k._-s3D._-22` (coerce `Random`), `R._-f4c() % parts.length` selects a message passed to `_-4p._-v3Q._-aV` (UI) @752; conditional on a timer test @662–672 | [V] draw; [H] UI-only effect |
| `_-z1C._-N13` #5142 | only non-null store to `_-z1C._-3I` (@68 and its copy on `_-z2w` @88); its only referencing method is `_-h3U._-m3D` #3630. `_-z1C._-q2K` #5134 sets `_-3I = null`. (`_-a1N._-r1r` stores null into the unrelated slot `_-a1N._-3I`.) | [V] reference set |
| `_-h3U._-m3D` #3630 (lesson start) | @49–53 `_-Y3u(level)` with **one** argument → `seed == null` → seeded from the global generator (prng-11.00 §3, #3348 @46–79); @133–140 `_-w35 = 0x1000000`; @143–152 `_-O4t._-N13(lesson)` | [V] |
| `_-h3U._-T12` #3624 (replay start) | @116–123 `_-w35 = 1024`, then @259 `_-Y3u(level, seed)` with the replay seed | [V] |
| `_-h3U._-f3N` #3626 | if `_-w35 & (32\|2048) == 0`: `_-ce = _-w35` (@23–33), then `_-w35 = 2048` when no bit of `2\|4\|0x400000` and none of `1\|8\|8192` is set and one of `1024\|2048\|8192` is set, else `32` (@37–137). From 1024: `_-ce = 1024`, `_-w35 = 2048`. | [V] |
| `_-h3U._-01I` #3336 @4342–4370 | `_-w35 = 2048` under a time test (end of replay data, [H]) | [V] store |

The identified lesson-start path uses a seed from `Math.random()` via `_-PW`, rather than the replay
header, and sets bit `0x1000000`. Modes 1024/2048 keep `_-O4q()` false (also on a bit-32 path when
`_-ce` = 1024). This establishes the guard, not that all mode transitions during playback preserve it (L1).

## 3. Scoreboard taunt: `_-9D._-Y15`

| Method / offsets | What | Status |
|---|---|---|
| `_-y4L` | ScreenScoreboard (`[ScreenScoreboard.hx] ScoringType …` in `_-y4L._-J1z`), extends the screen base `_-E6N`; slot `_-r5y : Vector.<_-9D>` | [V] |
| `_-9D` | scoreboard character slot (extends `_-x1d`; strings `TauntWin`, `TauntSlowClap`, `UI_CharacterSlotScoreboard_*`) | [V] strings |
| `ScreenScoreboard.OnTickScreen` #10946 | @158–255 guard: `_-N1k._-P2u == null`, `_-71F != null`, and not `_-N1k._-YX._-I2T()`; @261–271 only when `_-xI == 2`; @275–343 for i in 0..7, if `_-r5y[i]` exists and `_-L3x`, calls `_-Y15()` @334; @347–357 `_-xI += 1`. `_-xI` is reset to 0 in `_-y4L._-r5q` #10962 @217–222. | [V] |
| `_-9D._-Y15` #13733 | @34–50 returns if `_-C25` (`PaperDoll`) is null (no draw); @186–462 if no preset taunt and the candidate list `_-t3S` is non-empty: **draw @433** (`R._-f4c() % length`); **draw @651** always after @50 (5th argument of `_-k5N._-QF`, whose String result, or `TauntWin`/`TauntSlowClap` when empty, goes to `_-C25._-Y4d` @719) | [V] |
| `_-h3U._-c4W` #3337 | frame dispatch on `_-w35`: `== 1024` → @1680–1683 `_-M4q()` only; `== 32` or `== 2048` with a bit of `1024\|2048\|8192` → @1573–1576 `_-M4q()` only. The direct `_-4p._-q26.OnTickScreen()` calls (@1521, @1613, @1748) are on the `16`, non-replay `32/2048` and `32768` branches. | [V] |
| `_-h3U._-M4q` #3335 | @1815 `_-01I()` (all 16 ms ticks due this frame), then @2556 `_-4p._-w10()`. Two other `_-w10` calls are on paths that return without `_-01I` (@481 → return @607, @1363 → return @1385). | [V] |
| `_-4p._-w10` #9548 → `_-E6N._-D6k` #4331 | ticks every screen of `_-4p._-Bn` from top to bottom; `_-D6k` calls `OnTickScreen` @303 (guarded) | [V] |

On this call path, at most 8 slots × 2 = 16 direct R draws per scoreboard showing, when `_-xI` reaches 2. They are
*between* tick batches; the number of ticks before them depends on frame timing, so if they ever
precede an R-drawing tick the stream position would not be a function of the replay alone. Whether
that can happen is limit L2.

## 4. Items: `_-Y1h` / `_-5J`

| Method / offsets | What | Status |
|---|---|---|
| `_-E1V._-13p` #4908 | @2–9 `I._-24O(seed)`; @13–27 `_-Y1h = I.next`; @30–44 `_-5J = I.next` | [V] (prng-11.00 §3) |
| `_-E1V._-b2A` #4874 | arg 3 selects lane A (`_-T6S`, `_-O5i`, `_-Y1h`, `_-K4U`) or lane B (`_-k5F`, `_-z4Q`, `_-5J`, `_-c44`) | [V]; [H] two spawn lanes |
| `_-E1V._-O3d` #4879 (phase 4) | @51 `_-96d(…)`, @58 `_-u43(…)` | [V] |
| `_-96d` #4876 / `_-u43` #4880 | conditionally: `_-e3K(…)` (@562 / @560), then `_-Y1h = I.next` (@566–580) / `_-5J = I.next` (@564–578) | [V] shape; branch conditions not traced |
| `_-Z3n` #4872, `_-B5T` #4900, `_-SH` #4899 | snapshot write / read of both values; reset to 0 | [V] |

`_-e3K` #4920 is the only method referencing `_-K5X` (an I draw site) and one of seven referencing
`_-p1K`; so phase 4 may draw I inside `_-e3K` *before* the lane refresh. [H] until `_-e3K` is traced.

## 4b. Match start: `_-X6R._-b3x` (added from hit-detection-11.00.md §10)

| Element | Evidence | Status |
|---|---|---|
| `_-X6R._-b3x` #6777 (tick phase 4, `_-W1R._-b3x(t)` in #3336 @2708) | @49–80: local 2 = `!_-C3h && t >= _-n4k + 256`; @140–149 sets `_-C3h`, so this happens on one tick only | [V] |
| | @904–1002, only when local 2: n = `_-N1k._-I1f._-o5y.length`, or 37 when 0 (@919–943); **two draws** `_-G5X[i] = R._-f4c() % n` for i = 0, 1 with `R = _-N1k._-s3D._-22` (@972–992) | [V] draws; [H] `_-G5X` meaning |
| | the same call gives the eligible fighters state 3 (@408–411) and passes them to `Respawn` (@879–886) | [V] |

So the replay generator R is drawn twice on the first tick with t ≥ `_-n4k` + 256 ms, in phase 4, before
the entity passes. Pinned by `hit-detection-verify` (group "Match start in _-X6R._-b3x").

## 5. Limits and unknowns (precise boundaries)

- **L1 — other `_-w35` writers.** `abc-find _-w35 --member` lists every method touching the name.
  Stores not shown above to be off the replay path include `_-h3U._-l3f` #3555 (`_-w35 = _-ce`),
  `_-Px.OnTickScreen` #10734 (`_-N1k._-w35 = _-P5F`), `LinkUpdater` #5389/#5413/#5415/#5417/#5426,
  `_-F3g._-n5P` #5245 and `_-h2u` #13236/#13243/#13245. (`_-y4L._-r5q` #10962 @225–229 writes the scoreboard's own
  `_-y4L._-w35` slot, not `_-h3U._-w35`.) Claim 3 needs either their unreachability during
  playback or that none of them can store a value with bit `0x1000000` (or 32 with `_-ce` bit
  `0x1000000`) while `_-3I` is non-null. Not done.
- **L2 — scoreboard timing.** Unknown which code pushes `_-y4L` onto `_-4p._-Bn` (candidates:
  `_-4p.static._-7G`, `_-E6e._-g5j`, `_-o4W._-O27`, `_-9D._-q4z` reference `_-y4L`) and whether that can
  happen during replay playback before the last tick that draws R.
- **L3 — rule entry points.** `_-99._-u1O` #7128 (phase 3) and `_-99._-m4d` #7130 (phase 9) are the
  rules entry points, but their call graphs to the R draw sites of prng-11.00 §3 (rule subclasses
  built by `_-76j`, `_-P4P` Horde alias, `_-X6R`, `MessageTrigger`…) were not traced. Draw counts per
  tick and the order between rule objects remain unknown.
- **L4 — name-based references.** Sole-reference checks match multiname *names*; calls through
  runtime multinames (`[rt]`) or untyped `*` receivers on another class with the same member name
  are not resolved. The `Tick` call sites of #3336 and #7130 were read and fetch other types
  (`_-V5u`, `_-23P`, `LevelSound`, `_-T5N`); the remaining `Tick`-referencing methods do not
  reference `MessageTrigger`.
- **L5 — global generator.** `_-A6B._-PW` draws inside the tick (prng-11.00 §4) are out of scope here.
- **Next step:** trace `_-99._-u1O` #7128 and `_-99._-m4d` #7130 to the R draw methods (L3), then the
  pushes of `_-y4L` (L2). Together with phase 4 (`_-e3K`), that gives a per-tick static draw list
  that an oracle (Q10) could then confirm.
