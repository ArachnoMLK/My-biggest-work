# Vertical movement — patch 11.00 (Q4: port of the 10.09 evidence)

Pin: **patch 11.00 / abc `7d308423eaebcc82dfdda4ecc0e57d3abe78569534023aa7f9d776f626356db9`**.
Method ids and member names are only valid for this ABC. "@N" = instruction offset printed by
`abc-disasm`.

**Check it in one command** (after `python -I tools/bht.py abc-extract`):

```
python -I tools/bht.py movement-verify
```

It compares 31 pinned instructions (`tools/bh/movement.py`) with your ABC and exits 0 if all match,
1 on a mismatch, 2 if your ABC is another patch. Expected output on 11.00:

```
ABC 7d308423...  anchors 31  ok 31  mismatches 0
  grounded jump 57   x 0.384 = 21.888 per tick
  dash jump 170      x 0.384 = 65.28 per tick
  gravity 3.75       x 0.384 = 1.44 per tick
```

## Result: the 10.09 values of brawlhalla-sim hold on 11.00

| Value (brawlhalla-sim, 10.09) | 11.00 evidence | Status |
|---|---|---|
| Per-tick scale **0.384** | `script61.<init>` #1227 @256–259: `_-z2k._-Vj = 0.384`; @248–250 the same class holds `_-z2k._-x5b = 16` (tick length in ms). `_-z2k` is a global config class (also 60000, 1380000, 6000…). | [V] |
| Gravity field **3.75** | `Entity.<init>` #2887 @133–135: `_-84Q = 3.75` (instance field). Also a static copy `Entity._-22n = 3.75` in `script157.<init>` #3173 @1469, with no reader (`abc-find _-22n --member` → 1 method). | [V] |
| Gravity step **1.44** per tick | `Entity._-8i` #2984 @5277–5353: if `store[_-P5S] < cap` then `store[_-P5S] += _-84Q * _-z2k._-Vj` (= 3.75 × 0.384 = 1.44 in binary64). | [V] |
| Fall thresholds **70 / 85** | `Entity._-8i` #2984 @5127–5170: `cap = 85` if `_-61h()` or (Drop bit `2` held @5097 and not `IsMoveLocked`), else `70`; compared @5294. | [V] structure, [H] meaning of `_-61h` (fast-fall state?) |
| Jump bit **16** | `_-i4Z._-51o` #6313 @1220–1238: first record in the window with `keys & 16` sets a time; @3427–3445 `owner.Jump(t)` (`_-I3I` = owning Entity). | [V] |
| Grounded impulse **−57** | `Entity.Jump` #3052 @643–649: `impulse = 57.0 * k`, `k = 0.86` if arg 2 else `1.0` (@574–590); @1013–1048: `store[_-A4A] = store[_-A4A] − impulse`. Same branch sets `store[_-P5S] = 0` first (@977–991). | [V] |
| Dash-jump impulse **−170** | `Entity.Jump` #3052 @698–702: `impulse = 170.0` (no `k`) when the dash predicate (local 5) holds; emits `'dash.Jump'` @873; horizontal store slot `_-v1D` clamped to ±66 @716–786. | [V] |
| Dash predicate `_-ZQ + 160 > t && (_-32b != null ‖ _-U5H == 1)` | #3052 @76–127: `_-26T + 160 > t && (_-96f != null ‖ _-Xb == 1)` — identical structure, renamed members. | [V] |
| Telemetry branch near 170 | #3052 @673–695: `if (_-i2H._-A1S) _-K53._-r2W++` — counter only, does not gate the impulse (same as their `_-E3p` note). | [V] |
| Values are plain `Number`s behind `uint` handles in a fighter store | `_-Z2G` is an `_-N5C` store; reads `_-N5C::_-U13(handle)`, writes `_-N5C::_-E1t(handle, value)`; handles `_-A4A`, `_-P5S`, `_-v1D`, `_-11W`, `_-75K` are Entity members. | [V] calls, [H] storage layout not re-read |

The literals are **inlined** in `Entity.Jump` (`pushdouble 57.0`, `170.0`), while `script157.<init>`
also defines unused-looking static copies: `Entity._-E6v = 57`, `_-LG = 57`, `_-P6I = 65`,
`_-14z = 170`, `_-R1b = 70`, `_-l4y = 85`, `_-22n = 3.75`, `_-861 = 48`. [V] values (`abc-disasm
--method 3173`); [H] that they are Haxe `inline` constants whose readers were inlined away.

## New on 11.00 (not in the 10.09 table)

- [V] **Multiplier 0.86**: `Entity.Jump(t, a, b)` scales the grounded impulse by 0.86 when its second
  argument is true (@574–590). Callers: `_-i4Z._-51o` calls `Jump(t)` (defaults), `Entity._-A2X`
  #3131 @63–70 calls `Jump(t, false, true)`. [H] meaning of the argument.
- [V] A third branch of `Entity.Jump` (@2065–2146) uses `57 * k`, or `65 * k` when argument 2 is true,
  with the same `store[_-A4A] −= impulse` pattern; a fourth uses `Entity._-S4O * k` and a constant 48
  (@1615–1676). [H] these are air/wall jumps — not traced.
- [V] `_-8i` @1494–1574: a separate test `_-231 && _-5q() && (store[_-P5S] > 3.75 || store[_-A4A] > 0)`
  sets local 9. [H] "is falling / past apex".

## Open questions (not claimed)

- [H] **Two vertical slots.** The jump subtracts from `_-A4A` but gravity accumulates into `_-P5S`,
  and the jump resets `_-P5S` to 0. brawlhalla-sim calls the pair "vertical velocity"; on 11.00 it
  looks like *impulse velocity* (`_-A4A`) plus *gravity velocity* (`_-P5S`), summed somewhere into the
  y position. Where the two are combined and multiplied by 0.384 is not traced yet.
  **Update:** `_-A4A` is a one-tick impulse folded into `_-P5S` and reset to 0 at the end of every
  `_-8i` step; the y displacement is `_-P5S × 0.384`. See [entity-step-11.00.md](entity-step-11.00.md) (`step-verify`).
- [V] `_-z2k._-Vj` (0.384) is also the time step of the **animation player** `_-w2._-b2k` #11717
  (called from `Entity._-10` #2990 @1415–1432 with `0.384`, `1.1 × 0.384` or `0.384 × 1.23`
  depending on state). 0.384 = 16 ms × 24 frames/s, so it is "animation frames per tick". [H] the
  physics uses the same value as a per-tick velocity factor, not a separate constant.
- [V] **PRNG consumer for Q3**: `_-w2._-b2k` #11717 @215–261 multiplies its time step by
  `1 + (_-A6B._-PW._-f4c() / 4294967295 − 0.5) × 0.2` when `_-M6X._-s4M` is set (±10 % animation
  speed jitter, drawn from a WELL512 `Random`). [H] whether `_-A6B._-PW` is one of the two
  replay-seeded streams and whether `_-s4M` is ever set in a match.
- Horizontal movement, friction, dodge, wall jump, and the meaning of every `_-N5C` handle: Q5.
