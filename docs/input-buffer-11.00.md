# Input buffer — patch 11.00

Pin: **patch 11.00 / ABC SHA-256
`7d308423eaebcc82dfdda4ecc0e57d3abe78569534023aa7f9d776f626356db9`**. Method ids, obfuscated names
and offsets ("@N", as printed by `abc-disasm`) apply only to this ABC.

How the input consumer `_-i4Z._-51o(t)` #6313 reads the replay's input timeline: which key words it
sees, and when a key counts as **pressed**. This is static evidence (`input-buffer-verify`); the
eligibility rules that decide which buffered press fires are only started here.

## Reproduce

```text
python -I tools/bht.py input-buffer-verify            # 291 anchors
python -I tools/bht.py abc-disasm --method 6313       # _-i4Z._-51o, the consumer
python -I tools/bht.py abc-disasm --method 6323       # _-i4Z._-7z, key word at a time
```

`tools/bh/input_buffer.py` transcribes the two pieces as `state_at` and `buffered_presses`;
`tests/test_input_buffer.py` pins their behaviour.

## 1. Key word at a time: `_-7z(t)` #6323

On the playback path (mode bits 1024 / 2048 / 8192, or the lesson case; see prng-order-11.00.md), the
fighter's records `_-j1R` are `(time _-J6B, keys _-c3T)`. `_-7z(t)` returns the keys of the **last record
with time ≤ t**, moving a cursor `_-e3n` forward or backward. Before the first record it returns the keys
of a default record `_-X5q`. [V] So the replay's input list is a step function, as the format suggests
(a record at every change).

## 2. The window

| Claim | Where | Status |
|---|---|---|
| Window size `n` = **5** ticks by default (`owner` = `_-I3I`, the fighter) | @64 | [V] |
| `n = _-i3b(_-L3a)` when `owner._-P50 \|\| owner._-M3V` | @69–118 | [V]; [H] meaning |
| `n = 9` when `owner._-E6P()`, or `t ≤ _-322 + 64`, or `t ≤ _-I5A + 32`, or `t ≤ _-f6R` | @122–209 | [V]; [H] recent state changes widen the buffer |
| `n = 9` when `_-d3Y._-K4x == 3` and `_-Kc._-o3I` is set; `n = 11` when `_-Kc._-h2w`; `n = 9` when `_-Kc._-3N` (`_-Kc` = the owner's `_-F5N`) | @213–293 | [V]; [H] meaning |
| **No action at all while `t < 16 n`** (the method returns) | @294–305 | [V] |
| `_-O1I[i] = _-7z(t − 16 i)` for `i = 0 … n−1`; `_-66U = _-O1I[0]` is the current word | @306–388 | [V] |

## 3. Presses

| Claim | Where | Status |
|---|---|---|
| For `i = n−2` down to `0`: `press = (O1I[i] ^ O1I[i+1]) & O1I[i]`: bits set at tick i and clear on the tick before | @965–1278 | [V] |
| With `_-Kc._-h2w` the loop stops before `i = 0`: the current tick's presses are not seen | @978–999 | [V] |
| For each action the **oldest** press in the window is kept, as its time `t − 16 i` (locals 18, 20, 22, 23, 25, 26); for light attack, heavy attack and dodge, the key word of that tick is kept too | @1054–1270 | [V] |
| Actions tested, in order: LightAttack 128, HeavyAttack 64, Taunt `Commands._-z5Y` = 1024 \| 2048 \| 4096 \| 8192, DodgeDash 256, Jump 16, PickUpThrow 512 | @1076–1253; `_-y2E.init` #15351 @20872–20892 | [V] |

So with the default window, **a press is buffered for 4 ticks** (64 ms): it is seen on the tick of the
press and the three ticks after it. A key held down is not a new press.

## 4. Firing (started)

- [V] Jump: `owner.Jump(t)` @3445 runs when `local14` (an action already taken in this pass) is false and
  a jump press is buffered (`local25 ≠ 0`).
- [V] **A buffered jump cannot fire twice.**
  - `Entity.Jump(t, a, b)` #3052 returns at once when `!a && _-H5F(t, b)` (@36–59).
  - Otherwise it records `_-I5A = t` (@497–502, @540–545).
  - `Entity._-H5F` #3065 returns true while `t ≤ _-I5A + Entity._-Y35`, and `_-Y35 = 176` ms (11 ticks, `script157.<init>` #3173 @829). That is longer than the 4-tick buffer.
  - `_-H5F` also allows a jump only in states `_-65w` ∈ {0, 5} (`lookupswitch` @27), and blocks it when `IsMoveLocked(t)`, `_-u4F()`, `_-Xb ≠ 0`, `_-Kc._-cr ≠ 0` or `_-C54(t)` (unless its second argument is set), when `t < _-f6R`, and in the air (`_-wn()`) with `_-P5Y() ≥ _-56T()` and `_-r51 == 0` [H: no jump left].
- The guards of the dodge and the attacks, and `_-C51`, `_-z3C`: see §6.
- Not read yet [H]: the role of `_-B5 = t` (written after every action block).

## 5. Order of the action blocks

After the window, #6313 tries the actions in this byte order. Local 14 ("an action was taken") and
local 15 ("input handled") are set by most blocks and gate the later ones. [V] order and calls; the
meaning of the helpers is [H].

| # | Block | Trigger and guard (summary) | Call | Where |
|---|---|---|---|---|
| 1 | Mode hook | `_-s3D._-H1g._-m47._-365(t, id, keys, dodge-held time)`; if true: every flag set, `_-66U = 0` (input swallowed) | `_-365` | @1386–1488 |
| 2 | Any press | when `_-e3e & Entity._-m1t` and any press is buffered | `_-A5q(t)` | @1491–1532 |
| 3 | Dodge-related | (not read) | `_-U6t(…, 8 args)` | @1536–1916 |
| 4 | **Dodge** | dodge press newer than `_-C51` (or `_-C51 == 0`) | `Dodge(t, keys & 15, …)` | @2376–2504 |
| 5 | **Jump (first site)** | `!14`, jump press, and `local28 == 0 \|\| t > local28 + Entity._-z3C` | `Jump(t)` | @2507–2578 |
| 6 | `_-LY` ×2 | uses the light press | `_-LY(…, 2)` | @2590–2709 |
| 7 | **Light** | light press, `(!15 && !17) \|\| local32`; then `_-I35(t, dir, …, 2)` or `_-rU(…)` | `_-I35` / `_-rU` | @2709–2959 |
| 8 | **Heavy** | same shape with the heavy press; `_-I35(…, 3)` or `_-rU(…)` | `_-I35` / `_-rU` | @2996–3135 |
| 9 | **Pick-up** | pick-up press | `_-b1I(…, 4)` | @3154–3274 |
| 10 | Throw | pick-up press **newer than** the light press | `_-L6S(t, …)` | @3310–3414 |
| 11 | **Jump (second site)** | `!14` and a jump press | `Jump(t)` | @3418–3452 |
| 12 | Movement | left / right | `_-01L()`, `_-B3G()` | @3491–3594 |
| 13 | **Taunt** | taunt press | `_-Y1K(…, 4)` | @3626–3658 |
| 14 | Hand-off | light / heavy presses | `HandleInput(…, 4)` | @3680–3723 |

So a light or heavy press beats a pick-up only when the pick-up press is not newer. A jump press is
tried before the attacks (block 5) and again after them (block 11). The 2 / 3 / 4 codes passed to
`_-I35`, `_-LY`, `_-b1I` and `_-Y1K` look like action kinds [H].

## 6. Guards against re-triggering

`tools/bh/input_buffer.py` gives `first_jump_allowed`, `chain_allowed` and `attack_slot`; the anchor
groups from "jump lock" to "`_-y2r`" pin every row below.

| Claim | Where | Status |
|---|---|---|
| The first jump site needs `owner._-532 == 0` or `t > _-532 + Entity._-z3C`, with `_-z3C = 192` ms (12 ticks). The second jump site (block 11) has no such test | #6313 @2350–2556; `script157.<init>` #3173 @893 | [V] |
| `_-532 = t` is written by `Entity._-c1r` (called only from `_-F5N._-h1T` @853, right after `_-BC` starts a move) and by the pick-up `_-q2i._-b1I` @274 | #3025 @29, #1742, #3814 | [V]; [H] "time the last move / pick-up started" |
| Dodge fires only for a press newer than `_-C51` (or `_-C51 == 0`). When `Dodge` returns false while `owner._-P50` is set, `_-C51 = _-B5 = t` and the press counts as handled: the same buffered press is not tried on the next ticks | @2389–2504 | [V]; [H] meaning of `_-P50` |
| Late dodge: with no dodge press in the window, not move-locked, `t > 16 (n+7)` and `owner._-C2E(t, dir)`, the six ticks `t − 16(n+5) … t − 16n` are scanned for a dodge press | @1538–1734 | [V] |
| `_-C2E(t, dir)` is false once `t > _-532 + Entity._-84e` (`_-84e = 192`), when `dir` points against `_-M3h` (Left with `!_-M3h`, Right with `_-M3h`), when `dir == 0`, or when `dir == 2` on the ground (`_-96f ≠ null`) | #3073; #3173 @812 | [V] |
| Held dodge: with still no press, a dodge held since `_-D3F` (local 27) counts as a press when `owner._-01g ≠ 0`, `_-D3F > _-C51` and `_-D3F + 32 > owner._-01g`; the third `Dodge` argument (local 31) is then true. It is also true when a press exists and `_-g3B + 480 > t` (`_-g3B` = the previous `_-D3F`) | @1282–1384, @1742–1867, @2431 | [V]; [H] "dodge right after another dodge" |
| Cancel window: when the owner's current move record (`_-h3i._-Z4V[_-Q42]`) exists and `_-E6P()`, local 32 is set while `_-H2b + 16 _-M4L ≤ t ≤ _-H2b + 16 _-GX` (frames → ms); local 33 when the extra test local 39 holds. Light and heavy may fire with local 32 even after an action was taken | @2009–2342, @2763–2798 | [V]; [H] `_-H2b` = start of the current move |
| Light / heavy route: if a move runs (`_-Kc._-O2R ≠ null`) without `_-93n._-Z6M[1]` and `owner._-r51 == 0`, the press goes to `_-I35` (chain); otherwise to `_-rU` (new attack), but only when no move runs or the press is **newer than `_-Kc._-sM`**. `_-sM` is written with `_-O2R` in `_-F5N._-s1u`, so it is the start time of the current move | @2709–2959, @2996–3135; #1734 @182–189 | [V] |
| `_-I35(t, dir, a, b, kind)` returns false while `t − _-sM ≤ 300` (unsigned) or with no move; otherwise it calls `_-Kc._-V5I(t, dir)` if the move has `_-93n._-qo`, else `_-Kc._-A3Q(t, kind)` (kind 2 light, 3 heavy) | #6335 | [V]; [H] "string / chain the next part of the move" |
| `_-rU` picks the move slot `_-i4Z._-y2r[class + kind + air]`: class 0 when Drop (2) is held, else 1 when bit 32 is set, else 2 when MoveLeft / MoveRight is held, else 1; kind 0 light, 6 heavy; air +3 when `_-wn()` (in the air) or the jump flag is set. `_-y2r = [3, 1, 2, 6, 4, 5, 8, 11, 7, 10, 9, 9]`; then `_-Kc._-C5S(t, slot, …)` | #6334 @93–671; `script347.<init>` #6336 @150–191 | [V] |

What the slots are: `_-Kc._-C5S(t, slot, …)` #1700 gets the power from `_-F5N._-42t(t, slot, …)` #1726.

| Slot | Power name taken from | Status |
|---|---|---|
| 11 | the legend's `mSpecialPower1` / `mSpecialPower2` (by which of `mBaseWeapon1` / `2` is held) | [V] → neutral signature |
| 7 | `mSpecialPower1_Forward` / `mSpecialPower2_Forward`, else the weapon list | [V] → side signature |
| 8 | `mSpecialPower1_Down` / `mSpecialPower2_Down`, else the weapon list | [V] → down signature |
| other slots | the held weapon's list `ItemType._-Z6M[slot]` (unarmed: `ItemType._-m4V`) | [V] |
| 13–20 | a per-fighter table `_-b14[slot − 13]` (emote / taunt slots) | [V] shape |

So, by the `_-y2r` table: ground heavy down / neutral / side = signatures 8 / 11 / 7 [V]. Light
down / neutral / side = 3 / 1 / 2 and air light = 6 / 4 / 5 come from the weapon list [V slots; H
names]. Air heavy down = 10 and neutral = side = 9 [V]; slot 9 is refused when `_-UT` is set and the
fighter's `_-P5Y() ≥ _-56T()` (the jump-count test of `_-H5F`), so 9 reads as the recovery and 10 as
the ground pound [H]. `SLOT_NAMES` in the module uses these names.

On the input bit names (replay-format.md "naming conflict"): in `_-rU`, bit 1 is not read, and bit 32
turns a side attack into a neutral one. That is the behaviour the name `PrioritiseNeutralOverSide`
describes. [V] for this path; other readers of bit 32 are not checked here.

## 7. Jump and recovery counters

| Claim | Where | Status |
|---|---|---|
| `Entity._-P5Y()` = `_-3j ^ _-ef` (the counter is stored xor a key; `_-k1j(n)` writes it) and `_-56T()` always returns **2** | #2962, #2920, #3095 | [V] |
| `Jump` has three branches, tagged `'jump.Ground'`, `'jump.Wall'` and `'jump.Air'`. The ground branch calls `_-Kc._-C3x()`, which sets the counter to 0 (and `_-UT = false`); only the air branch adds 1; the wall branch leaves it | #3052 @968–1058, @2005, @2150–2176, @2414; #1712 @112–127 | [V] |
| So a fighter has a ground jump plus `_-56T() = 2` air jumps: `_-H5F` refuses an air jump when `_-P5Y() ≥ _-56T()` and `_-r51 == 0` | §4, #3065 | [V] |
| Each step of `_-8i`, when the fighter is on a line (`_-96f ≠ null`), not in hitstun (`!_-5q()`) and without the flag `Entity._-B6B`, `_-G1T = true` and `_-Kc._-C3x()` refreshes the counter, unless `_-r51 ≠ 0` and `_-x2C ≥ 9` | #2984 @290–467 | [V]; [H] landing refresh |
| The KO reset `_-p1Y` sets the counter to 0 | #3034 @197–202 | [V] |
| Each slot 9 power (recovery) without `_-UT` calls `_-31A`: `_-x2C += 1`; at `_-x2C == 9` the counter is set to 2 (no air jump left) and `_-UT = true`. `_-C5S` also tests `_-x2C ≥ 5` right after | #3082; #1700 @703–759 | [V]; [H] meaning of 5 and 9 |
| `IsDodgeLocked(t, a)` is true when `IsMoveLocked(t)`, `_-u5E()` (unless `a`), `_-E6P()`, a power runs (`_-Kc._-o3I ≠ null`), the fighter is on a wall (`_-r51 ≠ 0`), the zone test `_-I1f._-12J(1, …, _-25G)` holds, `_-Xb ≠ 0` or `_-C54(t)`; otherwise it is `_-x2C ≥ 9`. So a fighter whose `_-x2C` reached 9 can neither dodge nor air-jump until the refresh | #3075 | [V]; [H] "spent" state |
| With `_-UT` set, a slot 9 power is refused once `_-P5Y() ≥ 2`; when it starts (and its fifth argument is false) it also runs `Jump(t, true)` | #1700 @79–158, @399–423 | [V] |

## Limits

- Static only, and the playback path of `_-7z` only; the live path (@492 onwards) is not read.
- The meaning of the owner fields `_-P50`, `_-M3V`, `_-E6P`, `_-322`, `_-I5A`, `_-f6R` and of `_-Kc._-h2w`, `_-Kc._-3N` is open.
