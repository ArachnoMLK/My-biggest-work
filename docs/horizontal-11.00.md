# Horizontal movement (Q4/Q5, patch 11.00) — first part

Pin: patch 11.00, abc `7d308423eaebcc82dfdda4ecc0e57d3abe78569534023aa7f9d776f626356db9`.
Everything below is in the movement method **`Entity._-8i` #2984** (`abc-disasm --method 2984`), the same
method as the vertical chain (`docs/movement-11.00.md`). Stat names: `docs/stats-11.00.md`.

`_-wn()` is true in the air [H: it selects every `Air*` stat]; `_-v1D` is the horizontal velocity, read
and written through the numeric store (`_-N5C::_-U13` / `_-E1t`); `_-z2k._-Vj = 0.384` is the per-tick
scale (Q4).

## Maximum run speed (@519–615) [V]

```
ground  = RunSpeed    * _-Kc._-04K   (* 1.16 when _-w47 is set)
air     = AirRunSpeed * _-Kc._-u5j
max     = air if _-wn() else ground
```
[H] `_-Kc._-04K`, `_-Kc._-u5j` are per-fighter modifiers (1 normally).

## Friction (@838–1340) [V]

Choice of the friction value `F` (last match wins):
1. `AirFriction` in the air, `Friction` on the ground (@838–869);
2. within **640 ms** after `_-26T` (`_-26T + 640 >= now`; `_-26T` is also the dash timer of
   `Entity.Jump`, Q4): `3.534` in the air, `5.655` on the ground (@802–903) — the `Speed6` values;
3. weapon/power overrides from `_-Kc._-o3I`: `4.013` (@938–960), or `5.655` / `Friction` (@966–1036);
4. `_-5q()`: `4.0` (@1038–1055);
5. otherwise, when `_-H6t()` is true (@1059), by the flags `_-R5q._-66U` and the velocity sign: `9.0` (`vx >= 0` with bit 4 and not bit 8, @1065–1146;
   or `vx <= 0` with bit 8 and not bit 4, @1150–1231), else `3.25` (@1235). [H] meaning of `_-H6t` and of
   the two bits (a directional surface such as a slope or conveyor).

Application, once per tick (@1240–1340):
```
s   = +1 if vx > 0 else -1
v   = s * vx - F * 0.384
vx  = max(v, 0) * s
```
**Friction is a linear deceleration of `F × 0.384` per tick**, clamped at zero, not a multiplicative factor.

## Acceleration (@1928–2052) [V]

```
accel = AirAcceleration * _-Kc._-R4I  if _-wn()  else  Acceleration * _-Kc._-E16
accel *= 1.25 and max *= 1.25         when the mode hook _-N1k._-s3D._-H1g._-m47._-43P(now, this) is true
```

## Applying the acceleration (@2066–2659) [V]

Reached when the move condition holds: local 4 = `not IsMoveLocked(now) and _-81n() and not _-Kc._-J4Z`
(@471–517) [H: `_-81n()` = a horizontal input is held]. `left = Entity._-141()` #2935, which tests one bit
of the packed field `_-i3X`, the bit index being stored in bits 24–28 of the same field
(`i3X & (1 << ((i3X >>> 24) & 31)) != 0`) [H: the facing direction, updated from the input elsewhere].

```
accel *= _-Kc._-o3I._-x1E(now)                         when a power/weapon modifier is active (@2070–2109)
if left != (vx < 0) and vx != 0:                       # pushing against the current motion
    if not _-5q() and _-wn() and not (_-M3V and _-v3x > _-I5A) and not weapon._-ud:
        accel *= max(1 - |vx| / 50, 0)                 # in the air: no reversal above |vx| = 50 (@2329–2396)
if left:
    if vx > -max: vx -= accel * 0.384;  vx = max(vx, -max)     (@2412–2527)
else:
    if vx <  max: vx += accel * 0.384;  vx = min(vx,  max)     (@2535–2648)
_-t1A(now, max)                                        (@2652)
```

So one tick of horizontal motion is: **friction first** (linear, clamped at 0), **then acceleration toward
the held direction, clamped at the max speed** (only when already below it: a fighter faster than `max`,
e.g. after a hit, is not slowed down by the clamp, only by friction).

## Next

- Find where the facing bit of `_-i3X` and `_-81n()` are set from MoveLeft / MoveRight.
- Order of friction / acceleration / gravity / position update inside #2984, and the knockback decay
  (`docs/powers-11.00.md`).
