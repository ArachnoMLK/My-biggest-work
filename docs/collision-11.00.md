# Level collision (Q6, patch 11.00) — flags and query candidates

Pin: patch 11.00, abc `7d308423eaebcc82dfdda4ecc0e57d3abe78569534023aa7f9d776f626356db9`.
Check: `python -I tools/bht.py collision-verify` (68 pinned instructions, `tools/bh/collision.py`).

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

## Collision query: candidate order

**[V]** The query is **`_-CX._-X2e` #1581**: 13 parameters `(int, Number, Number, Point, Point, _-R15,
Point, Point, uint, uint, int, uint, Vector.<_-R15>)`, returns a collision line `_-R15`, called from 38
methods (`abc-find --member _-X2e`), as the 13-argument form on 10.09.

It gathers candidates with **`_-CX._-936` #1582** (returns their count):
1. raster traversal `_-A6B._-t2D(x0, y0, x1, y1, cellsX, cellsY, 100)` (@66): **cell size 100**;
2. for each cell, key `_-CX._-a2E(cx, cy)` (@131), bucket `_-S4a.h[key]`, and **every member appended
   in stored order**;
3. **then every dynamic line** `_-82D` appended in stored order (@251–303).

No sort anywhere in #1582, as on 10.09. The segment test is `_-A6B._-PK` #1017 (7 Numbers + Point →
Number) at @850, and `_-Q3r._-R5v` #6297 (8 Numbers + Point → Boolean) at @956.

## Next (from docs/prior-art-brawlhalla-sim.md)

Re-prove on 11.00: level selection (`LevelType` → `LevelDesc` in `Dynamic.swz`), the acceptance rule in
#1581 (10.09: query end shortened to each accepted hit, later equal-distance hit wins, one hard-before-soft
exception) and moving platforms (`1000·(N/60)·SlowMult`, `floor(frame + 1e-7)`).
