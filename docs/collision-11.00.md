# Level collision types (Q6, patch 11.00) — first part: flags

Pin: patch 11.00, abc `7d308423eaebcc82dfdda4ecc0e57d3abe78569534023aa7f9d776f626356db9`.
Check: `python -I tools/bht.py collision-verify` (58 pinned instructions, `tools/bh/collision.py`).

## Result

**[V]** The collision flags and the composition of every `LevelDesc` collision element are the same as
brawlhalla-sim found on 10.09.

- `_-y2E.init` #15351 (@13527–13627) sets the `_-z2k` statics: sticky `_-h5W = 8`, then `8 << 1 … 8 << 7`:
  no-slide `_-x1z = 16`, item-ignore `_-M4J = 32`, bounce `_-B6P = 64`, game-mode `_-J6w = 128`,
  pressure-plate `_-S1b = 256`, lava `_-s2O = 512`, `_-76n = 1024` (ice on 10.09, no consumer there).
- `_-i2H.static._-T5E` #858 registers each XML element name with a debug colour (uint) and its flags:
  base hard `1`, soft `2`, trigger `4`, OR the statics above.

| Element | Value | Flags |
|---|---|---|
| `HardCollision` | 1 | hard |
| `SoftCollision` | 2 | soft |
| `TriggerCollision` | 4 | trigger |
| `StickyCollision` | 9 | hard, sticky |
| `NoSlideCollision` | 17 | hard, no-slide |
| `ItemIgnoreCollision` | 49 | hard, no-slide, item-ignore |
| `BouncyHardCollision` | 65 | hard, bounce |
| `BouncySoftCollision` | 66 | soft, bounce |
| `BouncyNoSlideCollision` | 81 | hard, no-slide, bounce |
| `GameModeHardCollision` | 129 | hard, game-mode |
| `PressurePlateCollision` | 257 | hard, pressure-plate |
| `SoftPressurePlateCollision` | 258 | soft, pressure-plate |
| `LavaCollision` | 657 | hard, no-slide, game-mode, lava |
| `MudCollision` | 128 | game-mode only (no hard bit) |

## Next (from docs/prior-art-brawlhalla-sim.md)

Re-prove on 11.00: level selection (`LevelType` → `LevelDesc` in `Dynamic.swz`), the collision query
(10.09 `_-91W._-K2O` #1390, raster cell `100`, candidates in stored order then dynamic lines, later
equal-distance hit wins) and moving platforms (`1000·(N/60)·SlowMult`, `floor(frame + 1e-7)`).
