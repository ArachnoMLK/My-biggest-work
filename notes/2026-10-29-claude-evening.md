# Relay — Claude Opus 5.5 (Claude Code) — 2026-10-29 evening — patch 11.00

Pin: 11.00 / abc `7d308423eaebcc82dfdda4ecc0e57d3abe78569534023aa7f9d776f626356db9`.
All claims below are static bytecode readings ([V]) unless marked [H]; each is pinned by anchors in
the PR that carries it. Nothing was executed in the game, and no game value is stored.

## Open PRs (each needs an outside 🚀; the owner account cannot approve its own)
| PR | What was added this evening | Check |
|---|---|---|
| #25 | Exact condition for the KO-face time base (`ko.ko_time_base`); `_-T1T` keeps KO events newest first; respawn `_-U6W` resets the damage taken `_-W22` and the state | `ko-verify` 290 |
| #26 | Speed cap `local11` = 1000, 3000 while a power runs, ÷3 under `_-4Z`, on both clamps; wall contact `_-r51` (1 / 2 by side, stops the fall); cast impulse **sets** the velocity on the power's first update; power start set-up (start tick, CastTime `_-a2`, recover end with Sig / Air / RecoverMod) | `step-verify` 159 |
| #27 | Corpus: on 756 local 11.00 replays, inputs start at 0 ms and KO faces share their origin | `ko-oracle` |
| #28 | Re-trigger guards (jump lock 192 ms, dodge `_-C51`, late / held dodge, cancel window, chain after 300 ms); attack slot table `_-y2r` and slot names (signatures 7 / 8 / 11, recovery 9, ground pound 10); air jumps (max 2, refresh on ground); recovery count `_-x2C`; `IsDodgeLocked`, `IsMoveLocked`; hit effects on jumps; bit 32 behaves as `PrioritiseNeutralOverSide` in `_-rU` | `input-buffer-verify` 341 |
| **#29 (new)** | Damage, knockback and flight: BaseDamage pipeline with the Strength-vs-Weight table, knockback magnitude `_-u1x` (`d + d·(d/2)` scaling), FixedImpulse added outside, MinimumImpulse floor, directional influence (≤ 0.8 rad, netsafe trig rounded to 1/1000), base direction `_-JQ`, hitstun = 16 ms × FixedStunTime, reaction gates (Uninterruptable, InterruptThreshold), flight under the 250 cap with decay Recovery × 0.384 per tick; `power-columns` rebuilds the 171-column `powerTypes` map (names only) | `knockback-verify` 253 |

PRs #16–#23 from earlier sessions are still open and mergeable.

## Corrections made during the evening
- #29: the first labels of `_-W1a` / `_-C7` were swapped; the column parser shows `_-W1a` =
  VariableImpulse (scaled by damage) and `_-C7` = FixedImpulse (added outside). Fixed in the doc and
  the code names.

## Next steps
- `_-JQ`: the ImpulseToPoint branch; hit detection (how `_-F5N._-U5S` is filled).
- Power timeline: what `_-82O` (cast end) and `_-E5S` (end tick) gate after the first update.
- Meaning of the flags `_-B6B`, `_-a60`, `_-m1t`, `_-050()` / `_-86K`.
- A first end-to-end check: simulate one simple replay (one hit, one KO) with the transcribed pieces
  and compare with the KO oracle of #27.
- Tooling: the `*-verify` commands share the same boilerplate; a shared helper once the PRs merge.
