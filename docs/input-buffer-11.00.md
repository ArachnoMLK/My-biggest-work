# Input buffer — patch 11.00

Pin: **patch 11.00 / ABC SHA-256
`7d308423eaebcc82dfdda4ecc0e57d3abe78569534023aa7f9d776f626356db9`**. Method ids, obfuscated names
and offsets ("@N", as printed by `abc-disasm`) apply only to this ABC.

How the input consumer `_-i4Z._-51o(t)` #6313 reads the replay's input timeline: which key words it
sees, and when a key counts as **pressed**. This is static evidence (`input-buffer-verify`); the
eligibility rules that decide which buffered press fires are only started here.

## Reproduce

```text
python -I tools/bht.py input-buffer-verify            # 85 anchors
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
- Not read yet [H]:
  - the eligibility order of the other actions;
  - how a press that fired is kept from firing again on the next ticks;
  - the role of `_-B5 = t` @3383.

## Limits

- Static only, and the playback path of `_-7z` only; the live path (@492 onwards) is not read.
- The meaning of the owner fields `_-P50`, `_-M3V`, `_-E6P`, `_-322`, `_-I5A`, `_-f6R` and of `_-Kc._-h2w`, `_-Kc._-3N` is open.
