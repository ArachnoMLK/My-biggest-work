# Level collision (Q6, patch 11.00) — flags and query candidates

Pin: patch 11.00, abc `7d308423eaebcc82dfdda4ecc0e57d3abe78569534023aa7f9d776f626356db9`.
Check: `python -I tools/bht.py collision-verify` (89 pinned instructions, `tools/bh/collision.py`).

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

## Collision query: filters and acceptance

**[V]** Per candidate, in order (#1581, loop @132–1123), a line is **skipped** when:
- `type & mask == 0` (mask = parameter 9) (@166–180);
- the line is disabled (`_-44f`) (@184–193);
- it has an owner (`_-r1H != 0`) equal to parameter 1 (@197–224);
- `type & excluded != 0` (parameter 12) (@228–245);
- option bit 2 is set and the line has an owner (@249–280);
- it is the line passed as parameter 6 (@284–292);
- **hard-before-soft floor exception** (@296–480): the previous accepted line is hard (`type & 1`) with
  normal `y == −1`, this one is soft (`type & 2`) with normal `y == −1`, same `startY`, no collection
  vector, and `_-X1H == startX` on this line (meaning of `_-X1H` [H]);
- with no option among `8 | 4 | 1` and a normal, one-sided tests by the sign of the motion against the
  normal (@484–805).

Then `_-A6B._-PK` (@850) gives a signed side value; the line is skipped when that value is negative,
the mask includes soft (`mask & 2`), the line is soft (`type & 2`) and option 1 is clear (@858–915): soft
lines only block from one side; `_-Q3r._-R5v` (@956) tests the segment against the line and writes the hit
point. On a hit: the line becomes the result (@972), the outputs are copied (@974–1036), and **with no
collection vector the query end is replaced by the hit point** (@1049–1089). So a later candidate hitting
at the same point (the test is inclusive) replaces it, and farther ones fail: **the later equal-distance hit
wins**. With a collection vector, every hit line is pushed once (`indexOf`, @1095–1114).

The offsets of the exception (296–480) are the same as brawlhalla-sim's on 10.09: the method is very
likely unchanged between the two patches.

## Moving platforms: time to position

**[V]** `MovingPlatform._-V39` #6016 `(t, n)` with `n` key frames, `start = _-N1k._-n4k`:
```
t'     = t - start if t >= start else t                 (subtract_i)
period = 1000 * (n / 60) * SlowMult                      (SlowMult = _-t4q)
m      = (t' * 0.05) % period
frame  = StartFrame + m / period * n                     (StartFrame = _-d5L)
```
`MovingPlatform._-I4v` #6018: `k = floor(frame + 1e-7)`, `p1 = points[(k + 1) % n]`, `p2 = points[k % n]`,
`frac = frame - k`, position `= p1 * frac + p2 * (1 - frac)` (same for the origin points). `#6017` is the
plain `floor(x + 1e-7)`. Same formula as brawlhalla-sim on 10.09 (#47).

## Next (from docs/prior-art-brawlhalla-sim.md)

Re-prove on 11.00: level selection (`LevelType` → `LevelDesc` in `Dynamic.swz`): the moving-platform manager order and line refresh (10.09 #7240, #5836).
