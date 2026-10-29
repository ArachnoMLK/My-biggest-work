# Order of operations in one movement step — patch 11.00

Pin: **patch 11.00 / ABC SHA-256
`7d308423eaebcc82dfdda4ecc0e57d3abe78569534023aa7f9d776f626356db9`**. Method ids, obfuscated names
and offsets ("@N", as printed by `abc-disasm`) apply only to this ABC.

`Entity._-8i(t)` #2984 is the movement step of a fighter, run in tick phase 5 (tick-loop-11.00.md).
This page gives the **byte order and data flow** of its velocity and position updates. It is static
evidence: `_-8i` has many state branches and which of them runs on a given tick is not modelled; nothing
was executed. Velocities live in the fighter store `_-Z2G` (movement-11.00.md) under the handles
`_-v1D` (x velocity), `_-P5S` (y velocity), `_-84` (x impulse), `_-A4A` (y impulse), `_-11W` / `_-75K`
(x / y position).

## Reproduce

```text
python -I tools/bht.py step-verify                    # 151 anchors, 9 slot types
python -I tools/bht.py movement-verify                # gravity, jump impulses (movement-11.00.md)
python -I tools/bht.py abc-disasm --method 2984       # Entity._-8i
```

`tools/bh/step.py` holds the pins and `fold_impulse`, a transcription of the impulse fold;
`tests/test_step.py` checks it.

## 1. The two velocity pairs are velocity + one-tick impulse

This answers the open question "two vertical slots" of movement-11.00.md: **`_-A4A` is not a second
velocity. It is a one-tick impulse.** [V]
- `Entity.Jump` subtracts 57 / 170 from it (movement-11.00.md).
- `_-8i` folds it into `_-P5S` (step 4 below).
- `_-8i` resets it to 0 at the end of every step (@14583–14599).

`_-84` is the horizontal counterpart: it is folded into `_-v1D` (step 2) and reset to 0 @14563–14579.

The fold is the same on both axes [V]:

```text
if impulse != 0:
    s = impulse + velocity
    if s * s > Entity._-y4Q (= 62500.0 = 250^2, set in _-y2E.init #15351 @30022):
        overshoot = s           (x: Entity._-J1m, y: Entity._-d4x; Number)
        velocity = 250.0 if overshoot > 0 else -250.0
    else:
        velocity = s
```

[H] The overshoot fields keep how much the cap removed; `_-p1Y` (the KO reset) zeroes them.

## 2. Order in `_-8i` (byte order)

| # | Step | Where | Status |
|---|---|---|---|
| — | Friction and acceleration on `_-v1D` | @1240–2470 | [V] see horizontal notes (PR #23) |
| 1 | On a ground line whose `type & 2` is set, the line is dropped (`_-96f = null`); then either `_-w3i = t` (when `_-G1a()`) or the y impulse decays: `_-A4A *= _-7c` (`_-7c = 0.8` in `Entity.<init>` @124–127, `Number`, also written by `_-048` and item code) | @1792–1928 | [V] shape; [H] "drop through a soft platform" |
| 2 | Horizontal impulse fold `_-v1D ← fold(_-v1D, _-84)`, then `_-v1D` clamped to ±`local11` (the speed cap, below) | @2790–3053 | [V] |
| 3 | Horizontal step `local12 = _-v1D × 0.384` (`_-z2k._-Vj`) | @3086–3112 | [V] |
| 3a | If a ground line `_-96f` is set: walk loop. Each pass points `Entity._-N3a` along the line, normalises it to `local12`, sweeps with `_-CX._-X2e` (@3290), adds `_-N3a` (as the sweep leaves it) to x and y (@3311–3408), takes the moved length off `local12` (@3426–3448) and switches `_-96f` to the line that was hit (@3466). It repeats while `local12 ≠ 0` (@4197–4213), and some branches leave the loop early (@4185, @4193). | @3114–4213 | [V] shape; [H] left-over `local12` then becomes air movement |
| 4 | Vertical impulse fold `_-P5S ← fold(_-P5S, _-A4A)`, then `_-P5S` clamped to ±`local11` | @4217–4483 | [V] |
| 5 | Gravity `_-P5S += 3.75 × 0.384` while below the fall cap 70 / 85 | @5097–5353 | [V] movement-11.00.md |
| 6 | Free move: `Entity._-U5T = (local12, _-P5S × 0.384)`, plus 2.02 on y when `_-96f` is set; copied to `_-611` / `_-N6L` and swept with `_-X2e` @6896 (more sweeps follow @6999–8209) | @6620–6896 | [V] shape |
| 7 | Ring-out test `_-c5C` and `_-a3D` (ko-11.00.md, PR #25) | @14270–14517 | [V] |
| 8 | `_-L3z(x, y)`, then `_-84 = 0`, `_-A4A = 0`, return | @14520–14603 | [V] |

So within one step the order is: friction/acceleration → x impulse → x step (ground walk) → y impulse
→ gravity → free move and collision sweeps → ring-out test → impulses cleared. [V] byte order; [H] that
a single tick follows this order on every branch.

The y displacement uses `_-P5S` only (@6640–6672): with the fold, a grounded jump (`P5S = 0`,
`A4A = −57`) gives `P5S = −57` before gravity in the same step [H: the same step runs the jump,
which happens in the input consumer before `_-8i`].

## Speed cap (`local11`)

`local11` is written once, @2723–2781, and no branch jumps over that write; both clamps read it.
`step.speed_cap` and `step.clamp` transcribe it. [V]

```
cap = 3000 if _-Kc._-c5l else 1000          # @2729-2750
if _-e3e & Entity._-4Z: cap = cap / 3        # _-4Z = 524288 (script157.<init> @1231)
v1D = clamp(v1D, cap)                        # @2969-3053, every tick, impulse or not
P5S = clamp(P5S, cap)                        # @4399-4483, every tick, impulse or not
```

- `_-Kc._-c5l` is cleared at the top of `_-F5N._-u1N` #1745 and set again only when the fighter's
  power `_-o3I` exists and `_-o3I._-82f` is true (@99–135, @297–302). [V]; [H] "an attack is
  running", so attacks can move a fighter up to 3000 units/s instead of 1000.
- The meaning of the `_-e3e` bit 524288 is open [H].
- The clamp tests are `ifngt` / `ifnlt`, so a NaN velocity passes unchanged.

## Wall contact (`_-r51`)

| Claim | Where | Status |
|---|---|---|
| Each step saves `_-r51` in local 27 and sets `_-r51 = 0` | @8869–8886 | [V] |
| After a sweep, when the line hit (local 40) is vertical (`startX == _-f1i`) and not `_-S1A`, the fighter is pushed out along the normal `Entity._-04L` scaled to 1.01 | @11349–11481 | [V]; [H] `_-f1i` = end x |
| Then, when `!_-t46()` and (local 38 or the saved `_-r51 ≠ 0`) and not local 37: `_-r51 = 1` if `_-96f.startX ≤ x`, else `2` | @11489–11581 | [V]; [H] 1 = wall on the left, 2 = wall on the right |
| On the first tick of contact (saved `_-r51 == 0`) with `_-P5S ≥ 0`, `_-P5S = 0`: a falling fighter stops on the wall; y is then bounded by the line's `startY` / `_-P2s` | @11586–11700 | [V] shape |
| The KO reset `_-p1Y` clears it | #3034 @281–287 | [V] |

So `_-r51 ≠ 0` reads as "on a wall" [H]. This fits its other readers: the KO test lets the top line
count when the fighter is on the ground or on a wall (ko-11.00.md), `_-H5F` allows an air jump with
`_-r51 ≠ 0` (a wall jump), and the input consumer does not chain an attack with `_-I35` while it is set
(input-buffer-11.00.md §6). The meaning of locals 37 / 38 and of `_-t46()` is open.

## Attack movement at power fire

`_-l4X._-O1K` #91 (a running power, `_-l4X`; called from `_-l4X._-f14` #59) moves its owner `_-pr`
when `_-SQ` is not set (@374–381). [V] shape:

| Step | Where | Status |
|---|---|---|
| If the power type's `_-C6Z` (column **CastImpulseX**, power-columns-11.00.md in PR #29) is not 2147483647 (unset), the owner's `_-v1D` is **set** to `_-C6Z`, negated when `_-L0` | @385–471 | [V]; [H] `_-L0` = facing left |
| If `_-8S` (**CastImpulseY**) is not 2147483647, `_-P5S` is **set** to `_-8S` | @1087–1144 | [V] |
| Otherwise other branches run (flags `_-I2g & 2`, combo fields) | @475–1083, @1148–1491 | not read |

So a power's cast impulse replaces the velocity (it is not one of the one-tick impulses `_-84` /
`_-A4A`), and the next step's friction, gravity and clamps apply to it. [V]

When it runs: `_-l4X._-f14(t)` #59 does its set-up only while `_-k4b == 0` (the first update of the
power, @47–58) [V]:

```
_-k4b = round((t - t % 16) / 16)                     # the start tick, @62-173
_-82O = _-k4b + power._-a2[0]                        # @177-210; _-a2 is built from the CastTime column
                                                     # (PowerType._-A3R #6483 @11082-12715)
r     = power._-Sp (RecoverTime), x _-01d when _-s5C # @214-252
_-E5S = floor(_-k4b + power._-f5c (FixedRecoverTime) + r)   # @253-289, the end tick
(+ a charge share when _-a6i and _-e5i, + _-J2L(_-Q1n) or _-wj, AntigravTime _-q12)  # @292-592
_-54L(); _-O1K(t)                                    # @595-609: the cast impulse, on that first update
```

So the cast impulse is applied on the power's first update, and the power's times are counted in
ticks from `_-k4b` [V]; what `_-82O` / `_-E5S` gate later is not read.

## Limits

- Static only, and per byte order: the state branches of `_-8i` (hitstun, dodge, wall, ledge…) are
  not enumerated.
- The sweep `_-X2e` and its response rules are in collision-11.00.md (PR #20); how the swept result
  is written back after @6896 is not traced here.
