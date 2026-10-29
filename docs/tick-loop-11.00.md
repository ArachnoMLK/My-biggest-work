# Tick loop — patch 11.00 (Q2)

Pin: **patch 11.00 / ABC SHA-256
`7d308423eaebcc82dfdda4ecc0e57d3abe78569534023aa7f9d776f626356db9`**.
Method ids and obfuscated names below apply only to this ABC. Offsets are bytecode offsets
printed by `abc-disasm`, not line numbers. This is a static call-order map, not a working
simulator or a runtime equivalence result.

[V] `_-h3U._-01I` (#3336) is the fixed-step simulation scheduler: it rounds the selected
time bounds down to multiples of 16 ms, calculates a step count, advances its tick time by
16, and calls the entity input/state update inside that loop. Evidence: #3336 offsets
417–493, 1838–1922, 2751, 4073–4077; the input chain is described in
[the replay-reader map](code-map-11.00.md#c-handing-inputs-to-fighters-every-16-ms).

## Reproduce

Run from the repository root with an installation of the pinned patch:

```text
python -I tools/bht.py abc-extract
python -I tools/bht.py abc-validate
python -I tools/bht.py abc-find _-01I --member
python -I tools/bht.py abc-disasm --method 3310
python -I tools/bht.py abc-disasm --method 3336
python -I tools/bht.py abc-disasm --method 3594
python -I tools/bht.py abc-disasm --method 2991
python -I tools/bht.py abc-disasm --method 2990
python -I tools/bht.py abc-disasm --method 2988
```

For a table row or other method cited below, use
`python -I tools/bht.py abc-disasm --method N`; `abc-refs --method N` gives a shorter member
summary. Check `work/abc/summary.json` against the full hash above before comparing offsets.
Keep all extracted bytes and listings under ignored `work/`.

## Clock and number of steps

| Evidence | Conclusion |
|---|---|
| `_-h3U._-L5y` #3310 @42–50, 211–294 | [V] Reads `flash.utils.getTimer()` and adjusts an intermediate clock `_-946` using 16 ms increments and clamps against the sampled time. The simulation time is not simply the raw wall clock. |
| #3310 @295–321 | [V] Saves `_-p2O = _-v4J` and `_-73m = _-94N` before updating the clocks. These are the previous bounds selected by #3336. |
| #3310 @325–384 | [V] Computes a delta from the intermediate clock, `_-i31`, and `_-v4J`; conditionally adds it to `_-94N` when `_-Y3n` is true. Other branches adjust it further. |
| #3310 @430–464, 528–1202 | [V] Mode bits `2048\|8192` can hold `_-94N` at `_-73m`. Replay-mode handling also sets a seek target, applies speed factors, or decreases the target and calls `_-k3g` (#3594). A decreasing replay clock requests restoration rather than a negative simulation timestep. |
| `_-h3U._-c4W` #3337 @529–532, 1680–1683 | [V] Calls the clock producer and, in the branch including mode `1024`, the update wrapper `_-M4q` (#3335). #3335 @1812–1815 calls `_-01I`; it is the only method referencing that member (`abc-find _-01I --member`). |
| #3336 @120–416, 417–493 | [V] Its mode predicate (local 2) selects target/start fields `_-94N`/`_-73m`, or `_-v4J`/`_-p2O`. Both selected values are rounded down by subtracting their remainder modulo 16. Replay mode `_-w35 = 1024` takes the first pair. |
| #3336 @1838–1896 | [V] With the selected target **T** and start **S**, the number of steps is `floor(max(T - S, 0) / 16)`. Local 17 starts at **S**. |
| #3336 @1908–1922, 4073–4077 | [V] Each iteration first adds 16 to local 17 (the tick time), publishes it to `_-e5T._-C4v`, then runs the tick body. Thus it processes **S + 16, S + 32, …, T** when T ≥ S. |

[V] Local/controller input sampling is outside that inner loop: #3336 @599–705 queries
eligible entities, optionally runs bot `_-m3N`, and calls
`_-i4Z._-a2I` (#6317) with the selected target plus `_-dQ`. Replay timeline consumption is
inside each entity's tick via #2991 → #2986 → #6313. These are separate operations; see
`abc-disasm --method 3336` and the Q1 input-buffer map.

## Calls within one tick

[V] The following rows give execution order inside #3336, including its gates. The entity
loops traverse `_-h3U._-5r` in increasing index order, with a count captured at the start
of the scheduler invocation (#3336 @107–119). Every entity completes a pass before the
next pass starts; the scheduler does not run the whole table separately for each entity.

[V] Receivers in the table are written as they appear in #3336 (`findproperty` names such as
`_-3z`, `_-32h`, `_-s3D`). The cited method ids belong to the classes that define those
names, each defined exactly once in this ABC: `_-s4H` #4881 and `_-O3d` #4879 are on
`_-E1V`, `_-d3s` #1665 on `_-26u`, `_-u1O` #7128 and `_-m4d` #7130 on `_-99`
(`abc-disasm --method N` header line). [V] Q3's follow-up checked the declared slot types:
`_-3z : _-E1V` and `_-s3D : _-99` (`prng-order-verify`, [evidence](prng-order-11.00.md)).
[H] The property `_-32h` holds the `_-26u` instance; that slot type remains unchecked here.

| Order / offsets in #3336 | Receiver and method | What is established |
|---|---|---|
| 1 / 1926–1957 | `_-h3U._-Y6a(t)`; `_-4p._-42O._-d6v()` | [V] Conditional pre-step calls when `_-n4k == 0`; their full roles remain unknown. |
| 2 / 2179–2556 | `_-H5G._-X6n/_-Q3x`; `_-3z._-u3q`; each entity's `_-W1L._-X6n/_-Q3x` | [V] Conditional checkpoint lookup/construction before simulation. Predicate includes `t / 16 % 5 == 1`; on restoration it excludes the first iteration. Replay bits `1024\|2048\|8192` preserve existing entries. |
| gate / 2560–2594 | `_-vs == 0` or `t < _-vs + 450` | [V] The following normal-update block runs only while this predicate holds. At equality it is skipped; beyond the threshold a different position-refresh loop runs (@3916–4069). |
| 3 / 2598–2654 | `_-s3D._-u1O(t)` #7128; `_-22K._-d4u(t)` | [V] The first is skipped if `_-O4t._-O4q()` is true; the second runs only when `_-vs == 0`. |
| 4 / 2658–2708 | `_-w1r._-A4l(t)`; `_-h3U._-54K()` #3592; `_-3z._-O3d(t, i == local6)` #4879; `_-W1R._-b3x(t)` | [V] Global preparation precedes all entity passes. #3592 clears a dictionary; the subsystem meanings are not all established. |
| 5 / 2725–2759 | every `Entity._-k5H(t)` #2991 | [V] Input decoding, entity state dispatch, and movement helpers occur in this pass; details below. |
| 6 / 2776–2810 | every `Entity._-10(t)` #2990 | [V] A separate entity pass, including `_-Kc._-n2B`, position publication and `_-eR`. See the limits below before assigning KO semantics. |
| 7 / 2814–2836 | `_-3z._-s4H(t)` #4881; `_-32h._-d3s(t)` #1665 | [V] The first iterates `_-p5k` objects and conditionally calls `_-h20`. The second calls `_-26u._-76s` #1675 with 21 arguments (@2269 in #1665). [H] These include item and queued combat processing; exact hit ordering needs Q7. |
| 8 / 2854–2888 | every `Entity._-J2g(t)` #2988 | [V] Calls `Companion._-4v(t)` #1835 if a companion exists, then `GameStats._-L5I(t)` #3922. |
| 9 / 2892–3294 | conditional `_-74F`; `_-O4t._-44D` or `_-s3D._-m4d` #7130 | [V] The boolean result of the latter can set `_-vs = t` and trigger entity `_-Hx` and replay-writer `_-Ek` calls. #7130 itself updates hazards, level sounds and other level objects, then returns `_-e5L(t)`. [H] This is the match-completion boundary; its scoring predicate is not yet mapped. |
| 10 / 3299–3912 | `_-Q6o._-A5k(t)`, `_-b1h._-o3T(_-v4J)`, conditional reconciliation/display calls | [V] These follow the entity and global passes. They include a separate `_-45v` entity loop and optional `Tick` call. Their complete simulation/render split remains unknown. |

### Inside the first entity pass

| Method / offsets | Conclusion |
|---|---|
| `Entity._-k5H` #2991 @45–75 | [V] Optionally updates `SpawnBot`, then calls `Entity._-1L(t)` #2986. |
| #2986 @21–34 | [V] If `_-R5q` exists, calls its `_-51o(t)` #6313 before the remaining input/state handling. |
| #2991 @79–89 | [V] Dispatches on `_-65w` after the input handler. No names are assigned here to its numeric states. |
| #2991 @495–727 | [V] In one state branch, when `_-P4K` is false, calls `_-Kc._-25(t)` (`_-F5N`, #1687), then selects `Entity._-8i(t)` #2984 or alternative entity behavior according to entity flags. |
| #2984 @3207–3290, with `_-CX._-X2e` #1581 | [V] Calls `_-b1x._-X2e` with coordinates, points and ten arguments; it returns an `_-R15`. [H] This is a level collision query. Q6 must establish line filtering and response rules. |
| #2984 @6522–6597 | [V] Contains a conditional direct `Entity.OnHit` call with 17 arguments. Therefore a single late global pass cannot account for every hit-related call. The condition's gameplay meaning remains unknown. |

## Checkpoints and rollback

[V] `_-h3U._-k3g` (#3594) schedules restoration. It returns early if `_-n4k == 0` or the
requested time rounds to tick zero (@30–74). Otherwise, when the requested tick is no
later than the previous tick (or its second argument forces the path), it calculates an
anchor from **requested tick − 1**, rounded down to a multiple of a checkpoint interval
(@110–231). That interval is normally **5 ticks**; a conditional non-replay path uses
**300 ticks** (@126–186). Under additional guards it stores the anchor time in `_-717`,
adjusts early-start boundaries, and sets `_-Kt = true` (@233–434). This method does not
itself call the entity updates.

[V] When `_-Kt` is set, #3336 @1184–1688 looks up the global snapshot at `_-717 + 16`,
calls `_-X51._-L3P` when present, and restores associated entity
snapshots, input-buffer cursors and trail effects. It then replaces start S with `_-717`
(@1814–1821), so the ordinary forward loop runs again from the restored interval. The
pre-step checkpoint timestamp is one tick later than the stored anchor.

[V] `_-h3U._-02X` (#3595) also writes `_-717` and `_-Kt`, in a path using a 10-tick
comparison and a five-tick anchor (@80–180). The rollback flag alone therefore does not
identify which kind of correction requested it.

[H] `_-X51` and `_-B3C` are global/entity simulation snapshots. Construction, lookup,
restoration calls and the subsequent re-simulation are verified above; completeness of
their captured state and deterministic equivalence have not been tested.

## Limits and next step

- [V] `Entity._-10` #2990 calls `Entity._-x1M` #2977 @548 and `Entity._-eR` #3138 @566
  before the global #1665 pass. #2977 tests rectangle edges; #3138 can call `Respawn`
  @1147. [H] These are promising boundary/KO paths. The exact ring-out test and its
  relationship to score updates remain unverified; do not label the second pass simply
  "KO after all hits".
- [V] Checkpoint restoration, controller sampling, post-match gates, and calls after the
  inner loop are present. This map does not establish that every call inside the loop
  affects simulation, or that everything outside it is presentation.
- [H] A future simulator should preserve these pass boundaries and entity vector order
  until commutativity has been proved. Reordering to a generic input → physics → hits →
  KO pipeline could change behavior.
- **Next:** trace `Entity._-x1M` #2977 and `Entity._-eR` #3138 into their boundary and
  score consumers, then locate the replay KO writer. That will establish where ring-outs
  are committed relative to #1665. Q3 can proceed independently from the seed map.
