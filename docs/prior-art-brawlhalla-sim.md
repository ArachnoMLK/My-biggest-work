# Prior art: NickTacke/brawlhalla-sim (patch 10.09)

Read on 2026-10-28 (repository `main` at `1492832`, 91 issues, 62 research/task branches). Nothing was
installed or executed: this note comes from reading the public code, issues and linked reports.
Contact: [brawlhalla-sim#91](https://github.com/NickTacke/brawlhalla-sim/issues/91). License: MIT, so
cite the issue or commit when you reuse a result.

## Why it matters

[brawlhalla-sim](https://github.com/NickTacke/brawlhalla-sim) has the same goal as this project:
tick-exact re-simulation of replays. Its README undersells it. The real work is in **closed issues and
`research/*` branches**: each closed issue links a report pinned to the 10.09 ABC
(`9fe9c830…ba2d`, build `10.09.96325`, 15,010 method bodies). Its evidence policy (proven /
source-derived / provisional / unknown, hash-pinned, adversarial review) is stricter than ours.

**Differences to keep in mind:**

| | brawlhalla-sim | My biggest work |
|---|---|---|
| Patch | 10.09 only, no backward compatibility | 11.00 (current) |
| Method ids | 10.09 ids (e.g. tick loop #3217) | 11.00 ids (tick loop #3336) |
| Scope | stock (lives) matches only | not restricted yet |
| Replay corpus | 12 attested format-268 replays (online timed 4-player FFA) | 9,653 local replays, 790 of them format 268 (10.09) |
| Runtime | simulator scaffold, mostly provisional | none yet |
| Oracle | plans a deterministic **patched Ruffle** AIR runtime (#5, #72, #89, #90), not built yet | none (Q10) |

Their method ids and obfuscated names are **not** valid on 11.00. Every result below is [V] for 10.09
by them and [H] for 11.00 until someone re-proves it on our ABC.

## Their results, by our task

### Q1 replay reader (done here) — cross-check

| Their 10.09 result | Our 11.00 result | Status |
|---|---|---|
| Replay reader method 6510 reads the level word, indexes `LevelType`, stores it (#33) | Parser `_-24q._-b2L` #6699, type 4 @766+ | consistent |
| Header word 1 = **match random seed**, restored before initialization; seeds **two independent `Random` objects** (item/weapon/gadget stream and rules/mode stream); the item stream consumes two outputs immediately; three direct consumers use other bits of the word (power variant, companion/spawn-bot scheduling, ColorPlatforms) (#20) | `_-h3U._-Y3u` #3348 seeds `_-3z._-13p` and `_-s3D._-22._-24O` | consistent (two streams) — the extra consumers are new for us |
| Settings word 14 = `disabledGadgetsMask` (#21) | `custom_gadget_selection` in our parser | rename candidate |
| Last roster word = unsigned Unix connection time in seconds, used as roster order key (#23) | `connection_time` | consistent, meaning added |
| Selected taunt slots: win first, lose second (#24) | `win_taunt`, `lose_taunt` | consistent |
| Packed weapon word: bits 0–14 skin 1, bit 15 reserved, bits 16–30 skin 2, bit 31 = weapon two first (#25) | `weapon_skins` tuple | meaning added |
| Handicap words 2 and 3 = damage dealt / taken percentages, 0 → 1, else /100; damage applies target taken then attacker dealt (#26) | `handicap` | meaning added |
| Bots: commands recorded in state 1; replay restores them with bot AI disabled (#28) | — | new |

### Inputs — a naming conflict to resolve

brawlhalla-sim (#19, #40) proves on 10.09: **input value 32 is Aim Up**, normally paired with value 1
(Up); attack selection tests 32 alone. Command masks: jump `0x0010`, heavy `0x0040`,
light `0x0080`, dodge/dash `0x0100`, throw/pickup `0x0200`, taunts `0x3c00`.

Our `INPUT_BITS` (from BrawlhallaReplayLibrary) names value 1 `AimUp` and value 32
`PrioritiseNeutralOverSide`. The masks for jump, heavy, light, dodge, throw and taunts agree; the
names of values 1 and 32 disagree. [H] brawlhalla-sim is right (it traced producers and consumers);
to settle on 11.00, find the producers of 1 and 32 in our ABC.

Simultaneous inputs in one 16 ms interval are resolved by an **ordered eligibility state machine**
(#40, method 6125 `_-Tx._-B1i` on 10.09; not located on 11.00 yet): dodge, first eligible
jump, throw-button pickup, light, heavy, mode throw, ordinary throw, fallback jump/held, taunts;
equal-time light suppresses the later throw even when it fails.

### Q2 tick loop — strong head start

From #7 and #47 (10.09):
- Method 3217 is the fixed 16 ms authoritative loop; it **publishes tick T before the systems** run;
  one AIR frame runs 0, 1 or several ticks; method 3273 is post-frame work, not a tick.
- Order inside a tick: mode pre-phase → moving-world update and carry (PC 2642) → item pre-phase →
  respawn/scoring pre-phase → fighter tick → fighter post-movement → item post-phase → **deferred
  hits** (`OnHit` appends records, applied later) → terminal phase.
- Replay input is an **inclusive hold-last** timeline (matches our `_-i4Z._-7z`).
- Timing: tick 1 = 16 ms; the "6,016 ms" seen in results is a reporting epoch
  (`result − (q3e − 16)` vs `GameDuration`), not a gameplay transition; the countdown gate is still
  open (#30).

Codex's 11.00 relay (`_-h3U._-01I` #3336: all `_-k5H`, then all `_-10`, then globals, then all
`_-J2g`) should be reconciled with this order.

### Q3 randomness

Two seeded streams and three direct seed consumers are proven (#20); the complete draw order is still
open on their side (#6). The PRNG algorithm itself is not described in what was read.

### Q4 / Q5 movement

- Proven chain replay → jump bit 16 → grounded impulse **−57**, dash jump **−170**, gravity **3.75**,
  vertical velocity scale **0.384**, thresholds 70 / 85 (`docs/provenance.md`).
- Movement values are **plain binary64 Numbers** behind `uint` handles into a fighter store (three
  storage variants, one rotating over 128 cells); no fixed-point encoding (#41).
- Numeric rules for a faithful port: keep AVM2 `Number`/`int`/`uint` coercion at every boundary, 32-bit
  wrap for `_i` ops (`Math.imul`), bytecode operation order, no reassociation, exact `floor`/`round`
  (#8). JavaScript doubles match AS3 `Number`.
- Horizontal movement, friction, dodge, wall jump: not done on their side either.

### Q6 level collision — partial

- Level resolution: 162 LevelTypes in `Init.swz`, 121 published at runtime (`Template` and 40
  `DevOnly` dropped), 120 with a `LevelDesc` root; `Random` is a sentinel replaced via the match PRNG
  (#33, #46).
- `LevelDesc` inventory (10.09): 1,792 hard, 272 soft, 235 no-slide, 72 bouncy-hard collisions, 43 lava,
  175 dynamic-collision containers, … (#33).
- Collision query: candidates from raster cells, then static buckets in stored order, then dynamic lines;
  no distance sort; finite segments accept endpoints inclusively; later equal-distance hits overwrite
  earlier ones except one hard/soft case (#66).
- Moving platforms: exact frame/time formula (`1000 * (N / 60) * SlowMult`, `0.05`, `floor(frame +
  1e-7)`), linear interpolation, collision translated not rotated (#47).
- Still open: runtime arbitration order, owner responses, toggles (#48, #65–#67, #85–#86).

### Q7 attacks — partial

- `powerTypes` drives offensive timing and geometry: `CastTime`, `AoERadiusX/Y`, `CenterOffsetX/Y` →
  parser → phase vectors; active-power tick creates the hit region (#34).
- `hurtboxTypes` is defensive geometry only; it never feeds the offensive call (#34).
- Target arbitration order: `Priority`, then two internal keys, then loser marking (#34).
- The screen-space rectangle class (`_b20` on 10.09) is a projection for tools, **not** the gameplay
  hit test; the real intersection primitive is still open (#51, #77).
- 10.09 inventories: 3,671 powers, 906 hurtbox records, 44 `TargetMethod` names.

### Q10 ground truth

Their plan (#5): a **hash-pinned AIR runtime built on Ruffle** (the open-source Flash/AS3 emulator),
with deny-by-default host services and authenticated instrumentation, to run the real game code
without a live client and record exact per-tick traces. Not built yet (#72, #89, #90). This is the
most credible oracle idea seen so far; worth discussing before we design our own.

## Suggested next steps here

1. Reconcile the Q2 relay with their tick order (above), method by method on 11.00.
2. Settle the input bit 1 / 32 naming on 11.00 and update `tools/bh/replay.py` and `docs/replay-format.md`.
3. Port their proven 10.09 facts one by one, each as a new [V] for 11.00 with our method ids
   ([issue #6](https://github.com/ArachnoMLK/My-biggest-work/issues/6) for movement).
4. Offer them what we have that they lack: an 11.00 code map, and aggregated statistics from 790
   format-268 replays (never the files themselves).
5. Discuss the Ruffle oracle (Q10) with them in #91 rather than starting a parallel one.
