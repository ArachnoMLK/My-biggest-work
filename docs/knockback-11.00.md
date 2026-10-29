# Damage and knockback force (patch 11.00)

Pin: **patch 11.00 / ABC SHA-256 `7d308423…6db9`**. Method ids ("#N") and offsets ("@N", as printed by
`abc-disasm`) apply only to this ABC. Field names are the obfuscated ones; what they mean is [H] unless
a row says otherwise.

How a hit turns into damage and a knockback magnitude. The hit pass (tick phase 7, tick-loop-11.00.md)
reaches `_-26u._-76s` #1675, which computes the damage, the force, calls `_-26u._-u1x` #1674 for the
magnitude, builds the knockback point and hands it to `_-26u._-91G` #1677 (input-buffer-11.00.md §7:
the point goes into the one-tick impulses `_-84` / `_-A4A`).

## Reproduce

```
python -I tools/bht.py knockback-verify                 # 138 anchors
python -I tools/bht.py abc-disasm --method 1674         # _-26u._-u1x, the magnitude
python -I tools/bht.py abc-disasm --method 1675         # _-26u._-76s, damage and force
python -I tools/bht.py abc-disasm --method 1679         # script92.<init>, the _-M3e table
```

`tools/bh/knockback.py` transcribes the arithmetic as `stat_multiplier`, `hit_damage`, `charged_scale`
and `knockback_force`; `tests/test_knockback.py` pins their behaviour.

## 1. Damage (`local 28` of #1675)

| Step | Where | Status |
|---|---|---|
| `d = base` (an entry of the power's table, index local 8) | @480–488 | [V] |
| `e = charge × _-538`; when `e ≠ 0`: `e = e − 50 × _-538`, and `e = 1` when below 1; `d += e` | @490–543 | [V]; [H] charge bonus |
| `d = d × (weapon _-nR × victim _-lA / _-o3t)` | @545–567 | [V] |
| `d *= attacker._-45J` when the attacker is an Entity | @569–590 | [V] |
| `d *= _-26u._-M3e[11 + attacker._-P3I − victim._-92e]` (attacker term 0 when not an Entity), skipped when the entry is 0 | @592–662 | [V]; [H] strength vs defence |
| A negative `d` (a heal) is kept above `−victim._-W22` (the `int` of it) | @664–704 | [V]; [H] `_-W22` = damage taken |
| Later: `d *= _-N1k._-d3Y._-04o / 100` (a match setting in percent) | @1152–1174 | [V]; [H] damage setting |

`_-M3e` (script92.<init> #1679 @59–131) has 23 entries, increasing, with 1 at index 11:

```
0.8349 0.8384 0.8437 0.851  0.8604 0.8719 0.8857 0.9022 0.9215 0.9439 0.9699 1
1.031  1.0594 1.0852 1.1084 1.129  1.1469 1.1623 1.1751 1.1853 1.1928 1.1978
```

An index outside 0–22 reads `undefined` (NaN in AS3); the code does not clamp it. [V]

## 2. Force

| Step | Where | Status |
|---|---|---|
| `fixed = power._-W1a[i]` (+ `power._-4r` when local 13) | @920–949 | [V] |
| `variable = p10 × power._-w4x × p11 × 0.5`, or `power._-w4x × p11 × 0.5` when `power._-h5f` (p10, p11 = arguments of #1675) | @1035–1074 | [V]; [H] meaning of p10 / p11 |
| Charged power (`_-w46` and `_-I6c ≠ 0`): `k = 1 + held / _-I6c × 0.25`; damage and `fixed` are multiplied by `k`; flag `0x400000` when `k ≥ 1.25` | @1076–1150 | [V]; [H] held = charge time |
| `u = _-u1x(power, attacker, victim, fixed + variable, damage)` | @1176–1198 | [V] |
| `c7 = power._-C7[i]`, × `(1 + 0.5 × held / _-I6c)` when `_-T4t`, capped by an argument when `_-Q1u` | @951–1033 | [V] |

## 4. Knockback point

| Step | Where | Status |
|---|---|---|
| `m = u + (c7 + variable)`: so `c7` and the variable part are added **outside** `_-u1x` too | @1198–1211 | [V] |
| When `power._-A6P ≠ 0` and `fixed ≠ 0`, `m` is raised to at least `_-A6P`; a non-zero `m` clears the victim's `_-B2Q` | @1213–1274 | [V]; [H] minimum force |
| Directional influence: when the victim lacks the flag `Entity._-a60` and (`fixed ≤ 0`, or `_-x1F` is set and …), `_-N6u` runs; then, when (`!_-M6J` or the victim has `Entity._-m1t`) and `t − victim._-R5q._-c3J ≥ 32`, a held direction (`victim._-R5q._-66U & 15 ≠ 0`) calls `_-e4x(point, keys, power)` | @1278–1480 | [V] shape; [H] "DI" |
| `m *= 0.9` when the victim has `Entity._-B6B` and (`fixed == 0` or the DI case) | @1484–1532 | [V] |
| Power-specific factors for one named power | @1534–1638 | [V]; not modelled |
| `point.normalize(m)`: the direction `point` (argument 7 of #1675, after `_-e4x`) gets length `m`; this point is what `_-91G` writes into `_-84` / `_-A4A` | @1640–1644, @2170–2205 | [V] |

`final_magnitude` in the module transcribes the first, second and fourth rows.

## 3. Magnitude: `_-26u._-u1x(power, attacker, victim, force, damage)` #1674

```
z = attacker._-z4f   if attacker is an Entity and power and not power._-Rc and not power._-d6x
    1.0              otherwise                                              # @31-96
d = (victim._-W22 + victim._-w3F + damage) / 100                            # @98-142
d = (50 + victim._-w3F + damage) / 100     when _-N1k._-d3Y._-11X._-U6g == 5 # @146-162
force *= 0.75   when attacker != victim, same team (_-25G) and not power._-Rc # @164-206
F = force * (d + d * (d / 2)) * attacker._-Kc._-G4s * z / victim._-Kc._-13t   # @208-244
return max(F - victim._-P1r, 0)                                              # @246-265
```

[V] every line. So the magnitude grows as `d + d²/2` with the victim's damage after the hit (`_-W22`
plus this hit's damage), which matches the game's "more damage, more knockback" [H for `_-W22`]. The
order `d * (d / 2)` matters for exact doubles.

## 5. Directional influence: `_-26u._-e4x(point, keys, power)` #1664

`directional_influence` transcribes it; the angle helpers are the game's "netsafe" ones, which round
their inputs and results to 1/1000 [V] (the reason, cross-machine determinism, is [H]).

```
if point == (0, 0): return                                         # @3-29
c = (-1 if Left(4) else +1 if Right(8) else 0,
     -1 if Up(1) else +1 if Drop(2) else 0)      # _-26u._-Cg   @30-172
if c == (0, 0): return                                             # @176-214
a = atan2_netsafe(point.y, point.x)                                # #1098
b = _-75B(c.y, c.x)        # octant: 0, ±0.785, ±1.571, ±2.356, 3.142 (#1084)
diff = b - a, wrapped once into [-pi, pi]                          # @272-342
limit = 0.8, or power._-x1F when it is not Number.MAX_VALUE        # @344-367
if |diff| < limit: point = c            (not normalised here)      # @369-418
else: ang = a + limit if diff > 0 else a - limit
      point = (cos_netsafe(ang), sin_netsafe(ang))   # #1094, #1093 @422-479
```

| Helper | Body | Status |
|---|---|---|
| `atan2_netsafe(y, x)` #1098 | `r = sqrt(x² + y²)`; 0 if `r ≤ 0`; `atan2(R(y / r), R(x / r))` rounded, with `R(v) = Math.round(v × 1000) / 1000` | [V] |
| `_-K6l(a)` / `_-b4l(a)` #1094 / #1093 | `a − floor(a / PI2) × PI2`, rounded by `R`, then `cos` / `sin`, rounded by `R`; `PI2 = Math.PI × 2` (`_-y2E.init` @12002–12012) | [V] |
| `Math.round` | AS3 rounds halves up (`floor(v + 0.5)`), not to even | [V] language rule; `as3_round` |

So a held direction turns the knockback by at most 0.8 rad (about 46°), and replaces it outright when
the two are closer than that. Which key word is passed is in §4 (`_-R5q._-66U`, the victim's current
keys). [V]

## Limits

- The power fields (`_-W1a`, `_-w4x`, `_-538`, `_-C7`…) come from the game's power data, which this
  repository does not publish; a simulator reads them from the user's own install.
- The direction comes from the hit pass `_-26u._-d3s` #1665 @2038–2269: for each queued hit `_-P6X` of the list `_-T4G` whose `_-fP` is false, the shared point `_-26u._-ba` gets `(_-X5n, _-d4V)` and `_-76s` is called with it as argument 7 [V]. They are filled by `Entity.OnHit` #3042, which builds the `_-P6X` record and normalises the direction to length 1 (@2–65); the power hit routine `_-F5N._-T5A` #1731 gets that direction from `_-F5N._-JQ(…)` (11 arguments, @889–936) and passes it at @3443–3530 [V]. `_-JQ` (the angle from the power data and facing) is not read yet. A second writer, `_-P6X._-L3D` #1660, sets `(b.x − a.x, b.y − a.y − 0.25 |b.x − a.x|)` for a special conversion of the hit [V shape].
- `Math.atan2`, `cos`, `sin`, `sqrt` of the Flash runtime are assumed to match IEEE / libm closely enough that the 1/1000 rounding hides any difference [H]; values that land on a rounding edge could still differ.
- Which arguments the hit pass passes as p10 / p11 / held is not traced.
