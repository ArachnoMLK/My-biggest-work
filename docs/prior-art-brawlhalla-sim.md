# Prior art: NickTacke/brawlhalla-sim (patch 10.09)

Deep read on 2026-10-29 of `main` at `1492832` (last commit 2026-08-04), all 91 issues with their 117
comments, and the reports on the 62 `research/*` and `task/*` branches (about 1.25 MB of text).
Nothing was installed, built or executed: this note comes from reading public text and code only.
Contact: [brawlhalla-sim#91](https://github.com/NickTacke/brawlhalla-sim/issues/91). License: MIT, so
cite the issue or commit when you reuse a result.

## Why it matters

[brawlhalla-sim](https://github.com/NickTacke/brawlhalla-sim) has the same goal as this project:
tick-exact re-simulation of replays. Its README undersells it. `main` holds only a provisional
TypeScript scaffold (`packages/core`, `packages/replay-format`) and one analyzer
(`tools/avm2-provenance/movement_provenance.ts`). The real work is in **closed issues and `research/*`
branches**: each links a report pinned to the 10.09 ABC (`9fe9c830…ba2d`, build `10.09.96325`, 3,934,088
bytes, 15,010 method bodies) and a fail-closed analyzer. Their evidence policy (proven / source-derived /
provisional / unknown, hash-pinned, adversarial review) is stricter than ours.

| | brawlhalla-sim | My biggest work |
|---|---|---|
| Patch | 10.09 only, no backward compatibility | 11.00 (current) |
| ABC | 3,934,088 bytes, 15,010 bodies | 4,029,515 bytes, 15,453 bodies |
| Method ids | 10.09 ids (e.g. tick loop #3217) | 11.00 ids (tick loop #3336) |
| Scope | stock (lives) matches only (decided in #1; special modes closed as out of scope) | not restricted yet |
| Replay corpus | 12 attested format-268 replays (online timed 4-player FFA, playlist 108) | 9,653 local replays, 790 of them format 268 |
| Runtime | simulator scaffold, mostly provisional | none yet |
| Oracle | plans a deterministic **patched Ruffle** AIR runtime (#5, #72, #89, #90), not built | none (Q10) |
| Tooling | TypeScript on Bun + `abc-disassembler` (npm) | Python stdlib only |

## How to read this note

- **[V 10.09]** = proven by them on 10.09, with their issue/report. **[H 11.00]** = what we expect on our
  ABC until somebody re-proves it with our tools. Nothing here is [V] for 11.00.
- Their method ids and obfuscated names (`_-V4R`, `_-Tx`…) are **not valid on 11.00**. What survives a
  patch: readable strings (Haxe/AS3 names that the obfuscator left alone), numeric constants, call
  structure, AVM2 opcode patterns, class shape (field and method counts), and the **order of
  operations** documented below.
- Re-proof commands are suggestions built from `tools/bht.py` (§5 of `AGENTS.md`); I did not run them
  (no game files in this session). Adjust the search term if the first hit list is empty.
- Each report lives on its branch: `https://github.com/NickTacke/brawlhalla-sim/blob/<branch>/artifacts/research/<name>/<name>.md`
  (the state-7 and wayfinder reports sit under `research/wayfinder/`). Branch name = report topic; the
  closing issue comment gives the exact commit.

### Anchors that should survive into 11.00 (search with these first)

| Kind | Anchors (10.09 evidence) | Use |
|---|---|---|
| Readable strings | `Inputs for entId` (replay diagnostic), `jump.Ground`, `jump.Wall`, `jump.Air`, `dash.Jump`, `RunSpeed`, `AirRunSpeed`, `JumpXImpulse` (hero stat parser), `SpawnImportantItem2`, `Think` (bot AI), `Random`, `ScoringType.*` (`BOMBSKETBALL BRAWLBALL COLORPLATFORMS CTF HORDE SOCCER VOLLEYBALL ZOMBIE RING STREET_BRAWL VOLLEY_BATTLE BUDDY`), `GadgetList`, `FaceVictory`, `Template`, `TargetMethod`, `SmashRelease`, `CanDamageEveryone`, `CanAssist`, `IsThrow`, `LoseInvulnTime`, `MinTimeBetweenHits`, `InheritAlreadyHit`, `IsMultihit`, `CastTime`, `AoERadiusX/Y`, `CenterOffsetX/Y`, `Hurtbox`, `MovingPlatform`, `DynamicCollision`, `SlowMult`, `StartFrame`, collision names (`HardCollision` … `LavaCollision`), `Command_Name_AimUp`, `JumpAimUp`, `Aim Up`, `REPLAY_MODE_*` | `abc-strings REGEX` then `abc-find STRING` for the referencing methods |
| Constants | tick `16`; grace `450` after the terminal tick; playback cutoff `2500`; `GameDuration = result − q3e − 6000`; dash-jump window `160`; velocity thresholds `70`, `85`; gravity `3.75`, velocity scale `0.384`, jump `-57`, dash jump `-170`; PRNG multiplier `1812433253`; seed reduction `% 2147483647`; checksum `% 173`; sticky `+5000`; ring `+560`; attribution expiry `T + 500`; raster cell `100`; moving-line changed test `0.1`; floor epsilon `1e-7`; collision flag powers of two `1…1024` | `abc-find VALUE` (numeric) |
| Shapes | hit queue `OnHit` appends and does nothing else; hit arbitration runs after all fighters' post-movement pass; replay loader builds one `(timestamp, mask)` snapshot per record | `abc-refs --method N` on candidates |

## Their results, by our task

### Q1 replay reader (done here) — cross-check and corrections to apply

Their format-268 work ([`replay-format-268/format-268-semantics.md`](https://github.com/NickTacke/brawlhalla-sim/blob/research/replay-format-268-semantics/artifacts/research/replay-format-268/format-268-semantics.md),
and the per-field tickets below) pairs reader #6510 `_-E4h._-N4v` with writers #6516–#6524. Our parser
`_-24q._-b2L` #6699 does the same job on 11.00.

| Their 10.09 result [V 10.09] | Our file / status | Action |
|---|---|---|
| Envelope: state-2 END, then repeating 64-byte XOR (#6526; key built in #14909), then AIR `ByteArray.compress()` (zlib, RFC 1950) | `docs/replay-format.md` zlib + XOR | consistent |
| Section states: 1 inputs (#6521), 2 END, 3 header (#6518), 4 settings/level/roster/checksum (#6519), 5 KO faces (#6522), 6 results (#6520), 7 victory faces (#6523), 8 = invalid marker, no writer. Authentic order: `format, 3, 4, 6×(1–3), 1, 5, 2` | our objects 1–8 | consistent |
| Header seed is `u32` (we read `i32`) | `tools/bh/replay.py` | trivial: print as unsigned |
| **Roster record: trail-effect ID is written before emitter-group ID** (#6519 PCs 339–343 then 344–348). Their older parser had them reversed | our `docs/replay-format.md` lists "companion, emitter, trail"; `replay.py` assigns `emitter` then `trail` | [H 11.00] we have the same order bug; check against `_-24q._-b2L` #6699 @766+ |
| Last roster word `_-o1O` = unsigned Unix connection time in seconds, roster order key (tie: entity ID) (#23) | `connection_time` | meaning added |
| Selected taunt slots: win first, lose second (#24); 8 equipped taunt IDs before them | `win_taunt`, `lose_taunt` | consistent |
| Generic bitset word list in the roster = **available-TauntID bitset**, LSB-first, word `n>>5`, bit `n&31` (#22). `_-C5F` is a generic bitset class; the same class backs `mFavoriteWeapons` | unnamed in our parser | rename candidate (taunt meaning only for this field) |
| Settings word 14 = `disabledGadgetsMask` over the rule set's ordered `GadgetList`, bit set = removed (#21) | `custom_gadget_selection` | rename |
| Packed weapon word: bits 0–14 skin 1, **bit 15 reserved/unused but preserved and checksummed**, 16–30 skin 2, bit 31 = weapon 2 first (#25) | `weapon_skins` | consistent; bit 15 meaning still unknown |
| Handicap block = presence bit, **word 1 overrides lives**, word 2 damage-dealt %, word 3 damage-taken %; 0 → ×1, else `p/100`; damage applies target-taken then attacker-dealt (#26, method 4019) | `handicap` | meaning added |
| Bot bit in the roster = composite "non-human entity" classification (`_-V4R._-56G` masked against five entity-type flags), not proven equal to `isBot` (#27 closed out of scope) | `bot` | keep as [H] |
| `gameDataChecksum` = weak weighted checksum of roster/loadout fields and `levelId`, uint32 arithmetic, `% 173`; static method #6527; binds **no** patch data or physics (#4, `patch-snapshot-closure`) | `replay.py` already verifies it | consistent |
| Settings words (15 × `u32`) in order: flags, max players, duration, round duration, starting lives, scoring type, score to win, game speed, damage ratio, level set, item-spawn rule set, weapon-spawn rate, word 14, variation (all labelled by method #3746 except word 14) | `docs/replay-format.md` | the `Flags` word (word 1) is **not decoded by them either** |
| Input records: every snapshot is serialized, **even if the mask equals the previous one** (network insert #6128 does not dedupe). "Only changes are stored" is false | — | do not assume deduplicated timelines |
| Replay loader #3507 `_-u16._-H4o` order: parse all → reset shell → init match + seed (#3229) → create entities → load input timelines → finalize | our `_-h3U._-T12` #3624 | [H 11.00] same order, confirm |
| Replay level word indexes `LevelType`; 162 LevelTypes, 120 loadable (#33, #46) | `level_id` | consistent |

**Re-prove on 11.00:** `python -I tools/bht.py abc-disasm --method 6699` and compare the entity-record read
order after the 8 taunt IDs; then `python -I tools/bht.py abc-find "Inputs for entId"` for the diagnostic method.

### Inputs — a naming conflict to resolve (feeds Q2, Q9)

[`input-bit-32`](https://github.com/NickTacke/brawlhalla-sim/blob/research/input-bit-32/artifacts/research/input-bit-32/input-bit-32.md)
(#19, #40) proves on 10.09 [V 10.09]:

- **Value 32 is `Aim Up`**: hotkey 29 → `Commands._-Q4s[29] = 32` → label `Aim Up` (method #14909
  PCs 18921–19372 and 63194–63294, label in #3456). Value `1` is `Up` (hotkey 4/3 `JumpAimUp`/`Jump`).
- Every reachable producer emits `1 | 32` together (controller #1960, keyboard #4900, raw-keyboard
  normalizer #6439). A standalone `32` is only possible through a user binding of command 32 (#1974/#1964),
  and the 12-replay cohort has none. The playback HUD tests the union `(1|32)` for its UP display.
- Method #6146 uses bit 32 alone for **attack-direction selection**, without testing bit 1.
- Masks: jump `0x0010`, heavy `0x0040`, light/quick-pickup `0x0080`, dodge/dash `0x0100`,
  throw/pickup `0x0200`, taunt group `0x3c00`. 13 of 14 bits named (bit 32 was the 14th).

Our `INPUT_BITS` (BrawlhallaReplayLibrary) names value 1 `AimUp` and value 32 `PrioritiseNeutralOverSide`;
the other masks agree. [H 11.00] brawlhalla-sim is right. To settle: find the 11.00 init method that
registers the command table (`abc-find Command_Name_AimUp`, `abc-strings "^Aim Up$"`), read which hotkey
maps to 32, then the producers with `abc-find 32`.

### Q2 tick loop (🔄 in progress here) — their order, method by method

[`tick-phase-semantics`](https://github.com/NickTacke/brawlhalla-sim/blob/research/tick-phase-semantics/artifacts/research/tick-phase-semantics/tick-phase-semantics.md)
(#7) [V 10.09, ABC-pinned, PCs are original byte offsets]:

| Fact | 10.09 anchor | Re-prove on 11.00 |
|---|---|---|
| ENTER_FRAME handler `Main._-52Z` #5527 → `_-u16._-U3n` #3215 → `_-A3f` #3218 → `_-t20` #3216 → **tick loop `_-u16._-z3z` #3217** (PC 1812–1816 in #3216) | one AIR frame runs 0, 1 or many ticks (**no 1:1 frame:tick**) | ours: #3336 `_-h3U._-01I`; check that the caller chain reaches it from the `ENTER_FRAME` handler |
| Catch-up arithmetic: `available = max(now − processed, 0)`, `tickCount = floor(available/16)`; per tick `processed += 16`, publish to the shared clock field (`_-X6r._-L67`), then run systems | PCs 1828–1916 | `abc-disasm --method 3336`: look for `floor`, `16`, then a `setproperty` of the clock |
| Tick begin hook = right after the clock publish (PC 1916); tick complete = just before the outer back-edge `iflt` (PC 4051) | two unique anchors | same two shapes in #3336 |
| #3273 `_-u16._-A4X` is **post-frame** (coordinate `writeDouble`/`readDouble` round trip + random draws), **not a tick**. The loop caches `_-Y1k.length` before iterating | — | do not treat the post-frame method as the tick coordinator |
| First tick calls #3428, which writes `_-q3e = T` (the "activation marker"); runs once when `_-q3e == 0` | PCs 1916–1940 | the first-step initialization in ours |
| Within a tick (partial order, three fighter loops all ascending array index, cached length): publish T → [first-step init] → pre-phases: mode #6933, **moving world #7240 (platform refresh + carry)**, #11414, items #4753, respawn/scoring manager #6583 → **fighter pass 1** #2894 per fighter (bot producer → action #2889 → input sampler #6125 → jump #2954; movement/collision monolith #2887; `OnHit` #2944 appends) → **fighter pass 2** #2893 (post-movement power, bounds, ordinary KO #3040) → item post-phase #4755 → **hit arbitration `_-Wv._-Z29` #1474** (accepted records via #1484 → force/stun #1486; clear queue) → fighter pass 3 #2891 → mode/item/trigger/hazard work → standard mode `_-a1B._-g2p` (terminal predicate, placement, sudden death) → if terminal: `_z1s = T`, finalize fighters, fanfare, result writer, network note | whole tick PCs 1916–4051 | compare with Codex's #3336 order (all `_-k5H`, all `_-10`, globals, all `_-J2g`); map each of our loops to pass 1/2/3 |
| Hits detected at tick T are applied in the global hit phase of T; their force is consumed by movement and bounds on **T+1**, so ordinary KO from a hit is handled on T+1 (an immediate-KO path in #1484 is not excluded) | — | key invariant for any simulator test |
| Hit queue: `OnHit` builds a `_-m2j` record and pushes to `_-g5u`; arbitration is nested forward over the snapshot length, then application, then `_g5u` is cleared and a second deferred-removal list is drained | #2944, #1474 | find the append-only method and the later arbitration |
| KO order in #3040/#2949: attribution → victim stats → timestamped event (same tick) → killer stats → mode scoring callback → lives decrement. Attribution expiry `T + 500` | #3040, #2949, #1486 | — |
| Respawn: manager #6583 before fighters; multiple eligible fighters are sorted by comparator when the rule asks, otherwise **PRNG-shuffled**, then spawned forward through #6590 | → Q3 | — |
| Terminal: standard-mode predicate true → `_z1s = T` (inclusive last tick); the loop keeps going until the clock reaches `_z1s + 450`. Sudden death entered through the same predicate (`STREET_BRAWL`, `VOLLEY_BATTLE`: extra equality condition; `BUDDY`: extra callback) | PCs 2986–3013, 5119–5154 | search `450` near the terminal flag |

**Input timeline** [V 10.09]: loader #3507 builds `_-O3Y(timestamp, mask)` (PCs 627–649) and inserts via
#6133, which keeps the array ascending (equal timestamps are **not** replaced: a new equal entry can land
before the existing run when the backward scan finds a smaller one; a value not greater than the first is
dropped). Sampler #6135 is a right-continuous step function, `sample(t) = newest snapshot with timestamp ≤ t`, exact match returns
immediately, before the first record returns the baseline. #6125 samples slots `inputTime − i·16` and uses
`edge = (current XOR prior) AND current`. Jump bit 16 reaches #2954 before the fighter's movement.
Recording (#6129 `_-Tx._-91w`) constructs a snapshot only when the mask changes; it ORs several controller
sources and masks with `~Commands._-736`. [H 11.00] our `_-i4Z._-7z` is the sampler.

**Command-selection state machine** ([`command-selection-priority`](https://github.com/NickTacke/brawlhalla-sim/blob/research/command-selection-priority/artifacts/research/command-selection-priority/command-selection-priority.md), #40,
method #6125 `_-Tx._-B1i`, 4,006 bytes of code) [V 10.09]: rising edges in one 16 ms interval go through
ordered eligibility gates, not a bit-priority list: dodge → first eligible jump → throw-button pickup →
light/quick-pickup → heavy → mode-specific throw → ordinary throw → fallback jump and held-state actions →
taunt-group action. Equal-time light suppresses **both** throws even if light is rejected (mode throw needs
`lightTime == 0`; ordinary throw needs `throwTime > lightTime`); a failed heavy can fall through to throw;
the mode throw also accepts a throw held from an earlier interval. Local `32` (a runtime context flag)
can reopen later paths. Collector PC ranges 1063–1270 give each command's timestamp/held-mask local.
Re-prove: the 11.00 counterpart is the 4,000-byte method that calls the jump application and contains the
`XOR`/`AND` edge pattern (`abc-find` on the jump class, `abc-refs --method` on candidates).

**Timestamp model** (`gameplay-transition-6016`, `special-mode-timestamps`, `replay-lifecycle-zero-origin`,
#30, #29, #59) [V 10.09, ordinary modes]:

- `serialized = max(0, source − origin)`, `origin = q3e − 16` (so `q3e` serializes to 16). Special modes
  can use `origin = 0` through one shared compiled guard (lifecycle mask bits 2, 4, 8192, 262144, 4194304;
  readable mode names unresolved).
- State-1 timestamp = effective input sample slot. State-6 result = first tick whose terminal predicate is
  true (inclusive). `GameDuration = result_tick − q3e − 6000`, so serialized result minus `GameDuration` is
  exactly **6016 ms**: that is a reporting epoch, not a gameplay transition (#30). Methods #3805, #3833.
- Input timelines are dumped **after** the fresh result snapshot; real tails extend 592–3,168 ms past the
  result and are never consumed. Playback cutoff = result + 2,500 ms (#10459 `EndTime`, clamp in #3191).
  END carries no timestamp.
- State 6 may occur 1–3 times (lifecycle call in #3217 PCs 1391–1400, finalizer #6524 calls it again);
  reader #6510 is last-write-wins for result time and fanfare, and replaces the placement map only if the
  later section has placements. All repeats in the cohort are bit-identical. Placements are finish
  places (1 = winner), **not scores**. [H 11.00] this probably explains our "up to 11 results" only in
  multi-round modes.

### Q3 randomness (partly verified here) — they published test vectors

[`format-268-header-seed`](https://github.com/NickTacke/brawlhalla-sim/blob/research/format-268-header-seed/artifacts/research/format-268-header-seed/format-268-header-seed.md)
(#20) [V 10.09]:

- Header `u32` word 1 is the **match random seed**: reader #6510 → `reader._-l4` → #3272 → loader #3507 →
  initializer **#3229 `_-u16._-T3Q`** (explicit seed; if omitted, `% 2147483647` of a global `Random`
  `_-f0._-01W`) → `match._-l4`. Live writers #3282, #3514, #5257 (`LinkUpdater`) serialize the effective
  seed. The seed is restored **before** rules, level, fighters and input timelines; this order is part of
  determinism.
- The initializer seeds **two independent `Random` objects**: item/weapon/gadget stream (class 253,
  `_-61q._-h2u` #4780, which immediately consumes outputs 1 and 2 into `_-V2e`, `_-06p`) and rules/mode
  stream (class 382 `_-a1B._-p38`, rules built by `_-a1B._-Ga` #6937). Both begin with the same seed;
  both are serialized for rollback (#4747/#4774, #6931/#6939).
- PRNG = class 96 `Random`: **#1797 seeds** (resets cursor; `state[0] = seed & 0xff`; expands a 16-word
  `uint` state with multiplier `1812433253`, shifts, XOR, `multiply_i`, `add_i`, `& 0xff`), **#1799 draws**
  (fixed indexed reads/shifts/XORs, cursor update, one `uint`). Only the **low 8 bits of the seed** matter
  to the stream (seed 256 = seed 0; `4294967295` = 255).
- **Known-answer vectors** from their controlled mirror of AVM2 uint semantics (first four `_-H2L()`
  outputs): seed 0 → `3664512821, 3578536085, 3671592843, 2940218815`; seed 1 → `541330531, 3767533875,
  2226135129, 3006268673`; seed 255 → `2607024047, 3190304111, 254552081, 3792179193`.
  **Re-prove**: run our WELL512 implementation (Codex, Q3) on seeds 0, 1, 255 and compare. This is the
  cheapest hard test we can get; a mismatch means our state expansion or draw differs (our note says
  "two draws"; they have four-draw vectors).
- Three **direct seed consumers** outside the PRNG states: combat power-variant selection (#1535 PCs
  249–455: fighter ID, tick-derived input, hero data, `seed >>> 16`, power index), companion/spawn-bot
  scheduling (#1692 PCs 387–431), ColorPlatforms selection (#6869 PCs 62–235: entity ID,
  `floor(time/16)`, `seed & 0xffff`).
- The restored trait `_-l4` has exactly 16 opcode references in the whole ABC (the closure is a model for
  our own `abc-refs`/`abc-find` sweeps).
- Draw order across all consumers: **open on their side** ([#6](https://github.com/NickTacke/brawlhalla-sim/issues/6)),
  also respawn shuffles and item-type choice read the rules stream.

Re-prove on 11.00: `abc-find 1812433253`, `abc-find 2147483647`, then compare with Codex's WELL512 findings;
look for the three direct consumers by `seed >>> 16` (`>>> 16` with a `uint` read of the match seed field).

### Q4 / Q5 movement and fighter stats

([`docs/provenance.md`](https://github.com/NickTacke/brawlhalla-sim/blob/main/docs/provenance.md),
`movement-numeric-storage` #41, `numeric-semantics` #8, `avm2-air-native-semantics` #37, `air-numeric-parse` #58) [V 10.09]:

- Replay record `_-E4h` #6509 → loader #3507 → snapshot `_-O3Y` → insert #6133 → sample #6135 → consumer
  #6125 → fighter `_-V4R` (class 147) → **jump application #2954 `_-61V`** → movement monolith **#2887
  `_-D38`** (about 7,000 bytes; impulse and velocity consumption, gravity write at PCs 5380–5391, motion-delta
  construction at PCs 6680–6733, stage collision interleaved).
- Values: grounded jump `-57` (motion-delta equivalent `-21.888` per tick), dash jump `-170` (`-65.28`),
  vertical velocity scale `0.384`, gravity field `3.75` (velocity change `1.44` per tick, motion delta
  `0.55296`), vertical-velocity thresholds `70` / `85`. Dash-jump predicate:
  `_-ZQ + 160 > inputTime && (_-32b != null || _-U5H == 1)`; the branch emits `dash.Jump` and skips
  `jump.Ground`. The branch near literal `170` gating a telemetry increment is **not** the impulse gate.
  `jump.Ground` takes an optional scale argument (default and alternate scale are two literals).
- Gravity and the time-scale are **literals assigned in the fighter constructor** (and a time-scale class
  field); `RunSpeed`, `AirRunSpeed`, `JumpXImpulse` are parsed by a "fighter stat parser" (a method that
  mentions all three strings) and applied by a `HeroType`-typed fighter method; the movement monolith reads
  `RunSpeed`/`AirRunSpeed` (a movement method over 1,000 instructions that references both fields).
  The stat names are **readable strings in the pinned ABC**. [H 11.00] our "movement constants are not in
  the data files" needs rechecking: `abc-strings "RunSpeed|AirRunSpeed|JumpXImpulse"` finds the parser; the
  source table that feeds it is the missing link (their report does not say which `.swz` section).
- **Storage**: pending impulse (`_-l16`) and vertical velocity (`_-30`) are `uint` **handles** into a
  numeric store `_-V1I` (interface `_-z5S`, read `_-k17(uint)→Number`, write `_-G1Q(uint,Number)`). Three
  implementations: direct (class 151 `_-N3P`), mapped (152 `_-X3G`, permutation vector), rotating (153
  `_-b27`, `(map[h] + offset) % 128` physical index). The **payload is a binary64 `Number`**: no scale, no
  rounding, no wrap; only handles and the physical index wrap. 1,450 reads in 259 methods and 323 writes in
  70 methods. Rollback history is infrastructure, not gameplay encoding. [H 11.00] same store shape;
  `abc-find` on the fighter field that is read through `callproperty` taking a `uint` and returning `Number`.
- **Numeric contract** (#8, #37): keep three coercion domains (`Number` = binary64, `int`, `uint`), coerce at
  every opcode/typed-slot/argument/return boundary, `_i` ops wrap mod 2³², `%` is truncating remainder with
  the sign of the dividend, preserve bytecode operation order, no reassociation, exact `floor` and `round`;
  JavaScript doubles equal AS3 `Number`. Profile `avm2-air-10.09-v1`, goldens required from AIR
  `33.1.1.633` (macOS x86_64) for target-variable behaviour.
- **Patch data parsing** (#35, #58, partly proven): numeric XML/CSV fields use **empty-only default then
  prefix parsers** (`parseFloat`, Haxe `Std.parseInt`), not strict `Number()`: empty Number text is `+0`
  (#6079); int/uint go through `Std.parseInt` (#6071, #6074, #6075) where `NaN` becomes `null`. Relevant to
  how we read `powerTypes`/`HeroTypes` (watch trailing garbage, whitespace, `1e3`).
- Not done by them: horizontal acceleration/friction, dodge, wall jump, stats→constants interpolation. The
  `MAX_FALL_SPEED_LADDER`, `97.2` jump and weight tables in their `packages/core` are **provisional and
  wrong-labelled by their own header** ("Provisional movement scaffold"); do not use them as evidence.

### Q6 level collision model

Reports: `level-collision-geometry` (#33), `level-instance-geometry` (#45), `legacy-level-selection` (#46),
`collision-query-flags` (#48), `collision-query-reachability` (#65), `collision-arbitration-order` (#66),
`collision-owner-responses` (#67), `moving-platform-semantics` (#47), `moving-platform-carry-states` (#62),
`dynamic-leveldesc-loader` (#55), task `collision-query-provenance` (#68) [V 10.09, "bounded static" unless noted].

- **Level selection**: replay level word → `LevelType._-k56` → `LevelName` → `_-h5c._-XY` → one
  `Dynamic.swz` `LevelDesc` root. 162 LevelTypes in `Init.swz`, 120 `LevelDesc` roots in `Dynamic.swz` (42
  LevelTypes with no root; filtered not aliased; `Random` is a pre-write sentinel resolved with the match
  PRNG; readers fail closed on legacy names). All 11 distinct levels of their cohort resolve uniquely.
- **The only reached collision source is explicit Dynamic XML**, parsed by #5137. Platform art is PNGs under
  `mapArt/` loaded by #5139 using `AssetDir`; `InstanceName` is a scoring-rule hook for `COLORPLATFORMS`
  only (method #5133, base no-op). The eight `Level_*.swf` files and display-tree line extraction
  (#1400→#1401→#1402, #5073) are **dormant**: no reachable caller found (bounded static, not absolute).
- Dynamic XML defects (parse with care): `Dynamic.swz.103.xml` lacks whitespace between two attributes
  (game-compatible fix recovers `ThreeShips`); a cutscene section (`.122.xml`) has an unescaped `&`.
- Inventory (120 roots): 1,792 `HardCollision`, 272 `Soft`, 235 `NoSlide`, 72 `BouncyHard`, 1 `BouncySoft`,
  2 `BouncyNoSlide`, 2 `GameModeHard`, 43 `Lava`, 167 `MovingPlatform` (+ `Animation` + `DynamicCollision`),
  28 `DynamicRespawn`, 28 `DynamicItemSpawn`, 1,394 `Platform` elements with `InstanceName`.
- **Collision flags** (initialized in #14909 PCs 12128–12228; names composed in #850 `_-n2S._-W3S`; XML
  vocabulary #5156): hard 1, soft 2, trigger 4, sticky 8, no-slide 16, item-ignore 32, bounce 64,
  game-mode/mud 128, pressure plate 256, lava 512, ice 1024 (no consumer). Compositions: Hard 1, Soft 2,
  Trigger 4, Sticky 9, NoSlide 17, ItemIgnore 49, BouncyHard 65, BouncySoft 66, BouncyNoSlide 81,
  GameModeHard 129, PressurePlate 257, SoftPressurePlate 258, Lava 657 (= 1|16|128|512), **Mud 128 (no
  hard bit)**. Re-prove: `abc-find 657`, `abc-find 129` in the static initializer.
- **Query** `_-91W._-K2O` #1390: 93 direct callsites in 38 methods; positive masks seen: `1`, `2`, `3`, no-slide
  `16`; options `0, 4, 8, 9, 11`; 13-argument form with an excluded-type mask (item-ignore `32` rejects when
  `segment.type & excluded != 0`).
- **Candidates** (#1391 `_-K4Z`): raster traversal #1814 `_-f0._-t5I` (cell size `100`, dominant-axis walk)
  → cells in output order via key #1396 `_-w5r` and vector `_-D3I` → every bucket member in stored order →
  **then all dynamic lines** `_-A2S` in stored order. **No distance/type/id sort.** Segment tests are inclusive
  at endpoints. After an accepted hit with no collection argument, the query end is shortened to the
  intersection, so a **later equal-distance hit overwrites** (outputs and return); farther ones fail. One
  exception skips a later candidate (PCs 296–480: hard-before-soft case). Static-vs-dynamic equality: the
  later (dynamic) candidate wins.
- **Moving platforms**: manager #7240 `_-04B._-W1I` runs **before** fighters; refresh #5836 translates
  associated lines by the interpolated displacement (not rotated), endpoints updated before the `0.1` changed
  test; time to frame `1000·(N/60)·SlowMult`, epsilon `floor(frame + 1e-7)`, `StartFrame`, wrap; query masks
  `1`, `3`, `3` with options `0, 4, 4`. Carry gates: fighter state (`_-N14`) values `0,1,2,4,5,6` admitted,
  `3,7,8` rejected; companion state (`_-m4f._-h48`) `2–9` admitted, `1` only if `CompanionType._-16A == 2`,
  `0,10` rejected. No separate crush damage: "crush" is a geometric correction; 182 branches in 12 stages,
  46 mutations. Toggle writers #5842/#5843 (the only writers of the query-visible disabled field) have **no
  reachable callsite** in the ABC.
- **Owner responses** (fragments only): sticky = `tick + 5000` timestamp gate (fighter, companion); bounce
  factor `0.9` in fighter #3053 `_-7G`; item-ignore `32` in 8 sites of #14750; lava `512` → `PowerType` lookup
  (#3018 `_-N4f(uint, Boolean, optional segment)`); pressure plate `256` → `_-s4y(tick, this)`; game-mode `128` →
  #3018; Ring mode #3605 `tick + 560`.
- Their open list: runtime toggle reachability, dynamic transition order, hard/soft/trigger response state
  machines for items, projectiles and bots, no differential trace.

Re-prove on 11.00: `abc-find 657`, `abc-find 0.9`, `abc-find 5000`; `abc-strings "SlowMult|StartFrame|MovingPlatform"`;
`abc-find 100` inside the raster method; locate the query as the method with 13 parameters and the
`segment.type & mask` test.

### Q7 power (attack) state machine and hit geometry

Reports: `offensive-hitbox-timing` (#34), `offensive-collision-transform` (#51), `offensive-admission-pipeline` (#70),
`offensive-target-modes` / `-policy` (#52, #69), `repeated-hit-lifecycle` (#71), `reachable-power-phases` (#50) [V 10.09, bounded].

- **Source of timing and geometry**: `powerTypes` (3,671 records, 182 columns, 6,329 serialized geometry
  slots) → parser **#6294 `PowerType._-L4o`** (`Template` row returns at PC 155; `TargetMethod` read at PC
  8694, prefix `SmashRelease` handled) → per-phase vectors `CastTime`, `AoERadiusX/Y`, `CenterOffsetX/Y` →
  active-power tick **#46 `_-M5v._-81I`** selects the phase → collision-region creation. `hurtboxTypes` (906
  records) is **defensive only** (frame-ranged rectangles by `HurtboxName`, `AnimClass`, `AnimName`,
  `Frames`; a power's `Hurtbox` column selects one) and never feeds the offensive creation call. SWF
  `CastGfx/FireGfx/HitGfx` and `ForcePowerFacing`'s `scaleX` are presentation only.
- **Not the gameplay primitive**: `_-b20` (factory #13561 `_-S4l`; reached via #10280, not #10239, because
  the exact static receiver type is constructed there) is an **axis-aligned screen/tooling rectangle**
  (center ± radius, full width = 2×radius, facing mirrors center X, three display-container scales, owner
  anchor via `globalToLocal(root.localToGlobal(p))`, inclusive point containment). The gameplay hit test runs
  **first** through #1540 `_-Y4C._-06D` → geometry #1537 `_-vk`; that primitive is **still unknown** (#77 open).
  Do not implement hits from `_b20`.
- **Arbitration**: pairwise by `Priority`, then `_-F5f`, then `_-V6R`, then loser marking; same-team bypass;
  gates `CanDamageEveryone` (`_-n59`), `CanAssist` (`_-L1z`), `IsThrow` (`_-O2D`), `LoseInvulnTime`
  (`_-R1Q`); target collection #65 over `TargetMethod` modes 0–14 (44 distinct names, 15-way switch; bounded
  origin setup #44 `_-M5v._-b5W`).
- **Repeated hits** (`_-M5v._-D3h`): absent target ≠ timestamp 0; interval 0 blocks a present target;
  positive interval blocks while `prior + interval > now` (equality admits); the hit writes `currentTime`
  **before** target `OnHit`; `IsMultihit`, `MinTimeBetweenHits`, `InheritAlreadyHit` (copy on combo
  transition); in a tick, repeat processing and combo lifecycle run **before** pairwise arbitration.
- **Reachability**: following power-to-power transitions closes 3,632 of 3,670 non-template records; 38
  records are unknown, not unreachable (72 calls to the central `PowerType` name lookup in 47 methods, some
  names built dynamically).
- Not done: final admitted target sets for the 14 modes, damage/force formula, stun, combo cancel rules,
  defensive hurtbox use, the gameplay intersection primitive (#77).

Re-prove: `abc-strings "CastTime|AoERadiusX|CenterOffsetX|TargetMethod|SmashRelease"` finds the 11.00
parser; `abc-refs --method <parser>` for its field map; look for a class with `Priority` comparison and loser
marking; `swz-dump` `powerTypes` and `hurtboxTypes` columns against the 182/10 column counts.

### Q8 ledger (file roles)

From their archive work [V 10.09]: **`Init.swz`** → `LevelTypes` (entry 8); **`Game.swz`** sections: `.10`
CustomGameTypes, `.11` Dodge, `.17` GameModeTypes, `.30` LevelSets, `.43` ScoringTypes (24 scoring families,
164 non-template mode presets, 4 custom-game profiles); **`Dynamic.swz`** → 186 sections, 120 `LevelDesc`
roots plus 65 `CutsceneType`; `HeroTypes`, `itemTypes`, `PowerSwapTypes`, `TauntTypes`, `powerTypes`,
`hurtboxTypes` feed power roots. `Engine.swz` has no offensive geometry edge. `BrawlhallaAir.swf` (1,730,834
bytes) holds the ABC. Dormant for gameplay: legacy `Level_*.swf`, display-tree graphics reader #1400–1402.
Platform PNGs (637 distinct, 1,416 references) are loaded for rendering only. `startup and visual asset
membership` (#38) and `patch closure minimality` (#39) are open. Their 261-entry extraction aggregate is
the closest thing to a ledger; our `ledger/game-files.csv` can reuse the roles above (section numbers will
shift on 11.00).

### Q9 object 5 / 6 / 7 and `settings.flags`

- State 5 (our object 5): KO/event faces; writer #6522 keeps only event types **2, 3, 9**; stored
  **newest-first** (insert before the first event with timestamp ≤ new); entity 5-bit, `u32` timestamp; type
  3 producer unknown [V 10.09].
- State 7 (our object 7): **FaceVictory timeline** `(entity, timestamp)`; the only producers are
  `BRAWLBALL`, `SOCCER`, `VOLLEYBALL` (soccer/volley can store entity 0); same-tick writes overwrite
  (timestamp-keyed `IntMap`); reader merges repeated sections sorted by timestamp. Writer #6523 emits the
  section when the output stream, rules object and map are non-null (empty map still writes it). Their ticket
  closed as **out of scope** (special mode) without an authentic fixture. [H 11.00] our "one event per point"
  is the same table.
- State 6: see Q2 timestamps. State 8 never written.
- `settings.flags` (word 1): **undecoded** by them; also bits of lifecycle mask 2/4/8192/262144/4194304
  are distinct (transfer-wait, post-link-update, reserved, post-startup spectate, reserved).

### Q10 ground truth — their oracle plan

[`interpreted-reference-oracle`](https://github.com/NickTacke/brawlhalla-sim/blob/research/interpreted-reference-oracle/artifacts/research/interpreted-reference-oracle/interpreted-reference-oracle.md)
(#5), `wayfinder-air-host-capabilities` (#88), `native-replay-writer`, `replay-save-reachability`,
`replay-setup-cleanup-traces`, `patch-loader-mutation-oracle` (#56), `legacy-level-graphics-reachability` (#63):

- Plan: a headless **Ruffle `core` embedder at commit `6e69eaf8…`**, loading the complete AIR application
  boundary, deterministic **deny-by-default** host services, authenticated instrumentation of an
  independently verified copy of the app at method + byte-PC hooks (tick begin PC 1916, tick end PC 4051 of
  #3217), canonical traces. Trust ladder T0 identified → T1 booted → T2 deterministic twice → T3
  reviewed-corpus reference (12 fixtures, x64 and arm64, optimizer on/off). **Nothing beyond T0 is reached**:
  no target AIR boot, no trace. Stock Ruffle is nondeterministic and has material AIR stubs.
- Excluded by policy: live-client capture, instrumenting/modifying the official app, heap snapshots. An
  authorized Adobe/HARMAN AIR runtime may run only tiny synthetic microtests to produce goldens.
- Compatible with our AGENTS.md rule 5 (files on disk only). Actually running the game code inside Ruffle is
  a build/run of third-party code, which our rule 6 forbids without the owner's approval, so any Q10 work
  needs a human decision first.
- Static-only pieces we can reuse without Ruffle: the hook anchors, the capability disposition table
  (`include / deterministic-stub / reject / unresolved`), the "authentic fixture" HITL contract (#74: private
  consented replays, aggregates only, never bytes).

## Cross-checks to run on our side (concrete, small, high value)

| # | Check | Their claim | Where |
|---|---|---|---|
| 1 | Seeds 0, 1, 255 → first four WELL512-like outputs | vectors above | Q3 |
| 2 | Trail vs emitter order in roster record | trail first | `replay.py`, `docs/replay-format.md` |
| 3 | Input bit 1 vs 32 names | 32 = Aim Up | `INPUT_BITS` |
| 4 | Seed unsigned | `u32` | parser |
| 5 | Is `RunSpeed`/`AirRunSpeed`/`JumpXImpulse` a readable string in 11.00? Which swz feeds it? | stat parser exists | Q5 |
| 6 | Does #3336 publish the clock before systems, and does the back-edge exist once? | begin/end anchors | Q2 |
| 7 | Hit queue is deferred; fighter pass order 1/2/3 | DAG above | Q2 |
| 8 | `Dynamic.swz` XML defects in our `swz-dump` output | section 103, cutscene `.122` | Q6 |
| 9 | Dodge window `160`, impulses `-57/-170`, `3.75`, `0.384`, thresholds `70/85` | table above | Q4 |
| 10 | Corpus statistics: how many replays have 1/2/3 state-6 sections (their cohort: 6/3/3 of 12); tail length over the result (592–3,168 ms) | numbers above | our corpus |

## Dead ends and corrections (so we do not repeat them)

- **Method 3273 as tick coordinator**: wrong. It is post-frame coordinate work. Do not hook callback entry/exit
  or the loop's return as tick boundaries; anchor on the clock publish and the back-edge.
- **Frame = tick**: wrong. Count frames and ticks separately.
- **`getTimer` as simulation time**: wrong; only the published `T` counts.
- **6,016 ms as a gameplay event**: wrong; it is the epoch difference between the serialized result and `GameDuration`.
- **`_b20` as the hit test**: wrong (screen/tooling projection). Also `#10239` vs `#10280` share the QName
  `_j5S`; QName-only reading picks the wrong target.
- **`Platform.InstanceName` → `Level_*.swf` binding in #5133**: disproved; the callback is a scoring hook.
- **"Only changed masks are serialized"** in replays: false.
- **Discarding the leading boolean/bit 15 of the weapon word** (`morphWeapon2` hypothesis): the bit is consumed or
  preserved and checksummed; meaning unknown.
- **Rendered names from old dumps**: older `disasm_*.txt` mislabel names because they omit the
  `strings[index − 1]` correction; their opcode structure is still fine. Check that our ABC name resolution
  uses the correct off-by-one (we parse constant pools ourselves; `abc-validate` passes, but name lookup
  deserves one sanity test against a known readable string).
- **Ordinary vs special origin**: one corpus cohort cannot show `origin = 0` modes; absence in a corpus is
  never proof of unreachability.
- **Zero-clamped timestamps are not invertible** (every source ≤ origin maps to 0).
- **Static reachability with dynamic dispatch**: 27 of 134 first-frontier call sites have several same-QName
  candidates; QName grouping needs receiver typing. This blocked their #32 executable-closure goal.
- **Their `packages/core` numbers** (`97.2`, fall-speed ladder, weight tables) are explicitly provisional.
- **Live capture / unauthorized AIR**: excluded by them as by us.

## Their open questions (do not assume answered)

Complete PRNG draw order (#6) and the rules-stream consumers; state inventory (#9); exact gameplay hit/hurt
primitive (#77); the 38 power records outside the transition graph; admitted target sets for the 14 target
modes (#69); damage/force/stun/knockback (their `physics/knockback.ts` is scaffold); fighter action-state
machine (locomotion, walls, dodge, cancel); respawn eligibility and invulnerability fields; sudden death and
round transitions beyond the timed-FFA cohort; weapon/gadget/projectile behaviour; collision toggle
reachability (#85, #86) and per-owner responses (#67); bit 15 of the weapon word and settings word 1 `Flags`;
state-5 type-3 event producer; lifecycle zero-origin reachability (#59); invalid replay and snapshot
failure semantics (#15); the Dynamic loader (#55, #80), patch-loader normalization (#35, #81), numeric parse
goldens (#79), full AIR host/native capability dispositions (#88), the oracle itself (#72, #89, #90).
Corpus gaps: no bots, teams, ties, sudden death, rounds, disconnects, forfeits, state 7.

## Suggested next steps here

1. **Q3**: run seeds 0/1/255 through our PRNG and compare with the vectors above; then look for the three
   direct seed consumers and the item-stream double draw in 11.00.
2. **Q2**: reconcile Codex's #3336 with the pass 1/2/3 DAG and the hit-after-KO invariant; look for the `450`
   grace and the `2500` cutoff constants as cheap confirmations.
3. **Inputs**: settle bit 1/32 naming via the command init method; fix `INPUT_BITS`, header-seed signedness and
   the roster trail/emitter order in `tools/bh/replay.py` and `docs/replay-format.md`.
4. **Q5**: find the `RunSpeed` stat parser on 11.00 and its source table; port the 10.09 jump chain (§Q4) with
   our ids, each item as its own [V].
5. **Q6/Q7**: port collision flags and candidate order, then the power parser column map; do not use `_b20`.
6. **Q9**: add 11.00 statistics from the 790 format-268 replays: state-6 repeat counts, input tails, event
   types in state 5 (aggregates only).
7. **Offer to them** (in #91, once we have 11.00 results): an 11.00 method table keyed by their anchors,
   aggregate statistics from our format-268 replays (never files), and our disassembler for cross-checks.
8. **Q10**: discuss the Ruffle oracle with them in #91 rather than starting a parallel one, and ask the
   owner before running any third-party runtime (AGENTS.md rule 6).
