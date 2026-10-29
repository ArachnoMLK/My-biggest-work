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
python -I tools/bht.py knockback-verify                 # 65 anchors
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
| `magnitude = _-u1x(power, attacker, victim, fixed + variable, damage)` | @1176–1198 | [V] |

`power._-C7[i]` is read into local 36 (@951–1033: scaled by `1 + 0.5 × held / _-I6c` when `_-T4t`,
capped by an argument when `_-Q1u`); it is not an input of `_-u1x` [V]; its role is not traced here.

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

## Limits

- The power fields (`_-W1a`, `_-w4x`, `_-538`, `_-C7`…) come from the game's power data, which this
  repository does not publish; a simulator reads them from the user's own install.
- How the magnitude becomes the knockback point (angle, direction, the `normalize` @1644) is not traced.
- Which arguments the hit pass passes as p10 / p11 / held is not traced.
