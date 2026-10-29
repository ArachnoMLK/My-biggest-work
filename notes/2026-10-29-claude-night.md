# Relay — Claude Opus 5.5 (Claude Code) — 2026-10-29 night run — patch 11.00

Pin: 11.00 / abc `7d308423eaebcc82dfdda4ecc0e57d3abe78569534023aa7f9d776f626356db9`.
Same content as the relays posted on discussion #1 (comments 19259828, 19259939, 19260089, 19260190, 19260231).

## Verified and merged
- #14 (Q2 evidence + Q3 WELL512 port, unfortunatelyalex / Sol): bytecode compared by hand, `prng-verify` OK, tests OK.
- #15 (Q4 vertical movement): 31/31 anchors re-checked with main's `abc-disasm`.
- Prior-art deep read of brawlhalla-sim (`docs/prior-art-brawlhalla-sim.md`).

## Open PRs (each needs an outside 🚀)
| PR | Topic | Check |
|---|---|---|
| #16 | Input bits: 1 = Up, 32 = Aim Up; input consumer #6313 (first pass) | `commands-verify` |
| #17 | Q5 stats: RuneTypes levels → StatTypes Family+level; stance from the replay | `stats-verify`, `legend-stats` |
| #18 | Q8 roles of 7,781 files (89 needed); data registry #857 | ledger counts |
| #19 | `.anm` format, 105/105 files | `anm-info` |
| #20 | Q6 collision flags, query #1581, candidate order, acceptance, moving platforms | `collision-verify` (89) |
| #21 | Q9 flags accessors and per-mode corpus use; object 7 only in ball modes | — |
| #22 | Q7 parser, clash arbitration, repeated hits, knockback formula #1674, stun | — |
| #23 | Horizontal movement: max speed, linear friction, acceleration | — |

## Next steps
- KO detection: `Entity._-763` #2994 compares x with `CameraBounds` (`_-N1k._-I1f._-8I`) ± 50; find the blast-zone test.
- Order inside `Entity._-8i` #2984: friction → acceleration → gravity → position; knockback decay.
- Input consumer #6313: edge/held logic and eligibility order (10.09 #40).
- Q3: draw order of the PRNG consumers. Q10: oracle.
