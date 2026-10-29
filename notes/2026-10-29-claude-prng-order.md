### Relay — GPT-6.1 Sol lead / Claude Opus 5.5 implementation — 2026-10-29 — patch 11.00

**Task:** Q3 follow-up: static draw order of the replay-seeded rules/items PRNG relative to Q2's tick
phases; can the UI/trigger draws `_-9D._-Y15` and `MessageTrigger.Tick` consume the replay stream during
playback? Evidence: [`docs/prng-order-11.00.md`](../docs/prng-order-11.00.md). Pin: 11.00 / abc
`7d308423eaebcc82dfdda4ecc0e57d3abe78569534023aa7f9d776f626356db9`.
Static bytecode evidence only: no game execution or runtime oracle for ordering.

**Done:**
- [V] Per scheduler tick `_-h3U._-01I` #3336: phase 3 `_-s3D._-u1O` (@2624, rules) → phase 4
  `_-3z._-O3d` (@2695, items) → phase 9 **either** lesson `_-O4t._-44D` (@2992) **or** rules
  `_-s3D._-m4d` (@3009), chosen by `_-O4t._-O4q()` (@2973; the same gate skips phase 3). Each of these
  four members is referenced only by #3336. Slot types `_-O4t : _-z1C` (LessonManager),
  `_-s3D : _-99`, `_-3z : _-E1V` are now checked (they were [H] in Q2).
- [V] `MessageTrigger.Tick` #5809 (R draw @731, random lesson message to the UI) is called only from
  `_-z1C._-44D` #5129 @92 on the identified name-based call path (L4), i.e. on the lesson branch.
  `_-z1C._-O4q` #5131 is false when `_-3I` is
  null and when `_-w35` ∈ {1024, 2048}. Replay start `_-T12` #3624 stores `_-w35 = 1024` (@116–123)
  before seeding; `_-f3N` #3626 turns 1024 into 2048 (saving `_-ce = 1024`); #3336 @4370 stores 2048.
  Lesson start `_-m3D` #3630 is the only path that sets `_-3I` (via `_-N13` #5142); it stores
  `_-w35 = 0x1000000` and seeds with no seed (global `Math.random` generator). The identified lesson
  start does not use the replay header. On the replay path found, the lesson branch and its R draws
  do not run; other mode transitions remain open (L1).
- [V] `_-9D._-Y15` #13733 is the post-match victory-taunt pick (0–2 R draws per slot, @433 and @651) and
  is reached only from `ScreenScoreboard.OnTickScreen` (`_-y4L` #10946 @334) on the screen tick where
  `_-xI == 2`, for up to 8 slots. Screens are ticked per frame by `_-M4q` #3335 **after** the tick
  batch (`_-01I` @1815, then `_-4p._-w10` @2556 → `_-E6N._-D6k` → `OnTickScreen`). For `_-w35` 1024 and
  replay-bit 2048, the frame dispatcher #3337 calls only `_-M4q`. On this identified call path the
  direct draws fall between frame batches. Dynamic dispatch remains open (L4).
- [V] shape / [H] meaning: `_-Y1h`/`_-5J` (item draws 0 and 1 at seeding) are per-lane cached values
  read by `_-E1V._-b2A` #4874 and redrawn from I in phase 4 by `_-96d` #4876 then `_-u43` #4880 (only
  caller `_-O3d` #4879), each right after a call to `_-e3K` #4920 (which reaches the I draw sites
  `_-K5X`/`_-p1K`).
- [V] New `python -I tools/bht.py prng-order-verify` (`tools/bh/prng_order.py`): 87 pinned anchors
  (via `movement.check`/`listing`), 10 sole-reference sets, 9 slot types; exit 1 on mismatch or
  missing method, 2 on an unpinned ABC. Tests `tests/test_prng_order.py` (stubbed changed operand /
  opcode, missing method, new reference, changed slot type, unpinned hash; CLI wrong-patch exit 2;
  game-gated pins and one-pass references == `abc.callers_of`). Lead review added explicit guard
  branch anchors, rejected undecodable reference-scan bodies and closed the CLI's ABC file.

**Evidence ([V] lead rerun with `BRAWLHALLA_DIR` set, pinned extracted ABC):**
```
python -I tools/bht.py prng-order-verify     # anchors 87  reference sets 10  slot types 9  mismatches 0
python -I -W error::ResourceWarning -m unittest discover -s tests -v   # Ran 42 tests, OK, 0 skipped
python -I tools/bht.py prng-verify --draws 1000   # 6 seeds x 1000 draws + helpers: OK
python -I tools/bht.py movement-verify            # anchors 31  ok 31  mismatches 0
python -I tools/bht.py abc-validate               # bodies 15453 decoded 15453 errors 0 bad branches 0
# Repeat abc-disasm --method N for N = 3336, 5131, 5129, 5809, 3624, 3630, 3626,
# 3337, 3335, 10946, 13733, 4879. These numbers are separate commands, not shell pipes.
python -I tools/bht.py abc-disasm --method 5131
```

**Dead ends:** `abc-find _-Y15 --member` alone shows the caller but not *when* it runs; the frame
dispatcher #3337 has direct `OnTickScreen` calls that look relevant but are on non-replay branches —
the replay-relevant screen tick is the one inside `_-M4q` @2556.

**Limits / unknowns:** (L1) other `_-w35` writers (`_-l3f` #3555 `= _-ce`, `_-Px.OnTickScreen` #10734,
`LinkUpdater`, `_-F3g`, `_-h2u`) are not proven off the playback path; (L2) whether ScreenScoreboard is
on the screen stack during playback before the last R-drawing tick is unknown; (L3) the call graphs
from `_-99._-u1O` #7128 / `_-99._-m4d` #7130 to the rule R draw sites are not traced, so no per-tick draw
count; (L4) reference sets are name-based (`[rt]`/untyped dispatch not resolved); (L5) global-generator
draws inside ticks out of scope. No dynamic schedule and no runtime equivalence are claimed.

**Next:** trace `_-99._-u1O` #7128 and `_-99._-m4d` #7130 to the R draw methods, then who pushes
`_-y4L` onto `_-4p._-Bn` (candidates `_-4p.static._-7G`, `_-E6e._-g5j`, `_-o4W._-O27`, `_-9D._-q4z`).

**Questions for humans:** none.
