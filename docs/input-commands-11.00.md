# Input command table (patch 11.00) — names of the 14 input bits

Pin: patch 11.00, abc `7d308423eaebcc82dfdda4ecc0e57d3abe78569534023aa7f9d776f626356db9`.
Check: `python -I tools/bht.py commands-verify` (31 pinned instructions, `tools/bh/commands.py`).

## Result

**[V]** The game's own command table settles the names of values 1 and 32 of the replay input field:
**value 1 = Up** (command `JumpAimUp`, the default "up" key) and **value 32 = Aim Up** (the dedicated
`AimUp` command). This agrees with brawlhalla-sim on 10.09 (#19, #40) and corrects the names we took
from BrawlhallaReplayLibrary (`AimUp` for 1, `PrioritiseNeutralOverSide` for 32).
`tools/bh/replay.py` `INPUT_BITS` now uses `Up` and `AimUp`.

## Evidence

`_-y2E.init` #15351 builds, in this order:

1. A `haxe.ds.IntMap` **hotkey id → input value**, stored in `Commands._-F6a` (initproperty @23909).
   `abc-disasm --method 15351`, offsets 23497–23905:

| Hotkey id | Value | Bit | Command (from step 2) |
|---|---|---|---|
| 4 | 1 | 0 | `JumpAimUp` → **Up** |
| 5 | 2 | 1 | `Drop` |
| 1 | 4 | 2 | `MoveLeft` |
| 2 | 8 | 3 | `MoveRight` |
| 3 | 16 | 4 | `Jump` |
| 29 | 32 | 5 | `AimUp` → **Aim Up** |
| 9 | 64 | 6 | `HeavyAttack` |
| 6 | 128 | 7 | `QuickAttack` (light) |
| 7 | 256 | 8 | `DodgeDash` |
| 8 | 512 | 9 | `ThrowItem` |
| 13, 14, 15, 16, 51, 52, 53, 54 | 1024, 1024\|2048, 2048, 2048\|4096, 4096, 4096\|8192, 8192, 1024\|8192 | 10–13 | `Taunt1` … `Taunt8` |

   Other entries map hotkeys outside the replay field (23 → 32768, 10 → 65536, 11 → 32768, 36–39 and 30 →
   2^17…2^21): menu and UI commands, never seen in the 14-bit replay field.

2. Two parallel vectors (same index): hotkey ids `1, 2, 4, 29, 3, 5, 6, 9, 8, 7, 13, 14, 15, 16, 51, 52,
   53, 54, 11, 10` (@64372–64431) and label keys `Command_Name_MoveLeft, _MoveRight, _JumpAimUp, _AimUp,
   _Jump, _Drop, _QuickAttack, _HeavyAttack, _ThrowItem, _DodgeDash, _Taunt1 … _Taunt8, _Pause,
   _ShowNames` (@64454–64517). [H] small: pairing by index is read from the layout (both vectors are
   built side by side and have 20 entries); it gives a consistent table for every bit above.

The display label `'Aim Up'` is pushed only by `_-h3U._-h1H` #3573 (`abc-find "Aim Up"`).

## Corpus check

**[V]** On the 9,683 local replays (formats 261–271, 42,796,282 input records, 0 parse errors), counting
records by bits 1 and 32:

| Bits set | Records |
|---|---|
| 1 and 32 | 6,117,797 |
| 1 only | 373,665 |
| 32 only | 13,597 (in 1,034 files) |

So the two values are **separate commands**, usually pressed together (the default up key sets both), but
each one also appears alone: 32 alone is the dedicated Aim Up binding. This fits Up / Aim Up and does not
fit a "prioritise neutral over side" option flag, which would not toggle tick by tick with movement.
Script: count `flags & 1` and `flags & 32` over `replay.parse(...)["inputs"]` (aggregate only; no replay
or per-player data is published).

## Taunts

The four taunt bits are directions, and the 8 taunt commands are the 4 directions plus the 4 diagonals
(two bits at once). Our names `TauntUp, TauntRight, TauntDown, TauntLeft` for bits 10–13 are kept [H]:
the table proves the encoding, not which bit is which direction.

## Consumer of the replay input (first pass)

**[V]** `_-i4Z._-51o` #6313 is the method that turns the per-tick input word into fighter actions (it calls
`Entity.Jump` for bit 16, see `docs/movement-11.00.md`, and `Dodge` for bit 256). It is the 11.00
counterpart of the ordered eligibility state machine brawlhalla-sim describes on 10.09 (#40, method #6125
`_-Tx._-B1i`), which was "not located on 11.00 yet".

First-pass list of the masks it tests (offset, mask, first calls after the test) — **[H]**, the edge/held
logic and the order of eligibility still have to be read:

| Offset | Mask | Bit | Calls that follow |
|---|---|---|---|
| @850 | 8 | MoveRight | `_-r35()`, `_-Sz(…, 2)` |
| @890 | 4 | MoveLeft | `_-Sz(…, 2)` |
| @1078 | 128 | LightAttack | |
| @1114 | 64 | HeavyAttack | |
| @1185, @1300–1701 | 256 | DodgeDash | `_-365(…, 4)`; `Dodge(…, 3)` @2427 |
| @1222 | 16 | Jump | `Jump(t)` @3445 |
| @1253, @3173 | 512 | PickUpThrow | `_-b1I(…, 4)` |
| @3491, @3532 | 4, 8 | MoveLeft, MoveRight | `_-01L()`, `_-B3G()` |
| @3575, @3975 | 2 | Drop | `_-Y1K(…, 4)` |
| @3896 | 64 | HeavyAttack | `_-e3f()`, `_-q5E()`, `_-D67(…)` |
| @510, @635, @2427, @2825, @3030 | 15 | Up \| Drop \| Left \| Right (any direction) | `IsMoveLocked`, `Dodge`, `_-I35`, `_-rU` |

This scan (a mask pushed right before `bitand`) finds no test of bit 32 (Aim Up) or of the taunt bits in
#6313; they may be tested in another form or elsewhere (attack direction selection on 10.09: #6146).
