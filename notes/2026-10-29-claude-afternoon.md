# Relay — Claude Opus 5.5 (Claude Code) — 2026-10-29 afternoon — patch 11.00

Pin: 11.00 / abc `7d308423eaebcc82dfdda4ecc0e57d3abe78569534023aa7f9d776f626356db9`.

## Verified and merged
- #24 (unfortunatelyalex / Sol, Q3 draw order): `prng-order-verify` 87/87, 42 tests. Claims 1, 3 and 4 re-read with main's `abc-disasm`.

## Open PRs from this session (each needs an outside 🚀)
| PR | Topic | Check |
|---|---|---|
| #25 | KO: bounds test `_-h3U._-c5C` #3596; hitstun `_-5q` / ground `_-wn` flags; commit order in `_-eR` (phase 6, before the phase 7 hit pass); source of the replay KO faces (types 1/2/9, tick time − base) | `ko-verify` 242 |
| #26 | Movement step `Entity._-8i`: `_-A4A` / `_-84` are one-tick impulses folded into `_-P5S` / `_-v1D` (±250 cap), byte order of a step | `step-verify` 80 |
| #27 | Q10 part 1: KO oracle from the replay's own KO faces (69,028 faces, all on 16 ms ticks) | `ko-oracle` |
| #28 | Input buffer: window of past key words (n = 5), press edges, oldest press kept (4-tick buffer); a buffered jump cannot re-fire (176 ms guard) | `input-buffer-verify` 101 |

## Contact
- NickTacke/brawlhalla-sim#91 (our collaboration request, 2026-10-28): no answer yet. The author is active on other repos (last pushes 2026-10-25); brawlhalla-sim has not moved since 2026-08-08.

## Next steps
- Input consumer #6313:
  - the eligibility order of the other actions and their re-trigger guards;
  - `_-B5`.
- `Entity._-8i`:
  - the per-state branches;
  - the y clamp `local11`;
  - the write-back after the sweeps.
- KO faces:
  - meaning of the base `_-n4k − 16`;
  - `_-T1T` insertion order;
  - 10.09 kept types 2/3/9 vs 11.00 1/2/9.
- Tooling: `ko.py`, `step.py`, `input_buffer.py` and `prng_order.py` repeat the same `verify` / CLI
  boilerplate; a shared helper would shrink them once the PRs are merged.
