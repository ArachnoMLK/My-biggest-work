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
