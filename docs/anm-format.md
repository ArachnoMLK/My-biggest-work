# `.anm` animation format (patch 11.00)

Implementation: [`tools/bh/anm.py`](../tools/bh/anm.py); command `python -I tools/bht.py anm-info`.
Pin: patch 11.00, abc `7d308423eaebcc82dfdda4ecc0e57d3abe78569534023aa7f9d776f626356db9`.

**[V] Corpus check:** all 105 `anims/*.anm` of the install parse with no error and no trailing byte:
6,994 animations, 231,759 frames, 6,387,192 bones; every animation's frame block is consumed exactly, and
the declared size of every file equals its decompressed size (`anm-info`).

## Layout (all little-endian)

| Level | Content | Game method |
|---|---|---|
| file | `u32` decompressed size, then a zlib stream | — |
| payload | while `bool`: `utf` key, set | `_-B65.static._-46O` #169 (sets `Endian.LITTLE_ENDIAN`) |
| set | `utf`, `utf`, `u32` count, count × animation | `_-U4H.static._-y1m` #120 |
| animation | `utf` name, 6 × `u32`, `u32` n, n × `u32` data, `u32` frames_bytes, frames | `_-y1v.static._-B5I` #147 |
| frame | `i16` id, point?, point?, `i16` bone count, bones | `_-84Y.static._-RE` #125 |
| point | `bool` present, then `f64` x, `f64` y | `_-84Y.static._-72b` #127 |
| bone slot | `bool` reuse: copy bone *i* of the previous frame, then `bool` keep, else `i8` frame; otherwise a full bone | #125 |
| full bone | `i16` id, `bool` opaque, matrix, translation, frame, alpha | `_-q55.static._-kd` #694 |

`utf` = `u16` length + UTF-8 bytes (AS3 `readUTF`).

**Full bone, delta-coded against the previous bone of the same frame** (#694):
- matrix: `bool` copy → previous bone's `(a, b, c, d)`; else `bool` special → (`bool` identity → `(1, 0, 0, 1)`,
  else *symmetric*: `f32 a, f32 b`, then `c = b`, `d = −a`); else `f32 a, b, c, d`.
- translation: `bool` copy → previous bone's `(x, y)`; else `f32 x, f32 y`.
- frame: `bool` → `i8`, else 1.
- alpha: 1 when opaque, else `u8 / 255`.
- `id` indexes the bone-name table `_-T5Y._-HX`.

Frames are decoded lazily by the game (`_-y1v._-j5e` #141 jumps to the stored position); a frame that
reuses bones needs the previous frame, so decode in order.

## Animation header

The six `u32` go to `_-y1v.<init>` #138 in this order: [V] the first is the **frame count** (`_-012`, the
size of the frame vector) and the sixth is the base frame used with `gotoAndStop` (`_-r3Y`). [H] The
names `loop_start, recovery_start, free_start, preview_frame` for the four in between follow community
tools; check them against their uses before relying on them (Q7). The `u32` list (`_-X1I`) is not decoded
yet.
