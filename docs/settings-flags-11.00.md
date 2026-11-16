# Replay `settings.flags` and object 7 (Q9, patch 11.00) — first part

Pin: patch 11.00, abc `7d308423eaebcc82dfdda4ecc0e57d3abe78569534023aa7f9d776f626356db9`.

## Where the flags go

**[V]** `_-I3W._-b2L` #3876 reads the 15 settings words of replay object 4 into class `_-I3W` (the match
settings; it also has `mDuration`). Word 0, `flags`, goes to **`_-I3W._-Z2Y`**; word 5 is turned into the
`ScoringType` (`ScoringType._-M2W[word5]` → `_-11X`).

Careful: the obfuscated name `_-Z2Y` is **reused by other classes** (Entity, Companion…), so a plain
`abc-find --member _-Z2Y` mixes unrelated fields (146 methods). Only the accessors of `_-I3W` are certain:

| Accessor | Test | Notes |
|---|---|---|
| `_-I3W._-Z5E` #3869 | `flags & 1 != 0` | |
| `_-I3W._-O3P` #3867 | `flags & 1 != 0` and scoring type `_-n3u` | |
| `_-I3W._-L37` #3874 | if not `flags & 1`: `ForceUniqueColors()`; `CREWBATTLE` special case | callers handle colour schemes (`NO_COLOR_SCHEME`) |
| `_-I3W._-P5b` #3895 | scoring type is `TIMED` and `flags & 8 == 0` | callers count hits between different `_-25G` (team id) |
| `_-I3W._-x2U` #3914 | `flags & 8 != 0` | |
| `_-I3W._-K1q` #3913 | `flags & 16 == 0` | |
| `_-I3W._-Wr` #3868 | `flags & 64 != 0` | |

## Corpus

**[V]** 9,683 local replays (aggregate counts only):

| Bit (value) | Replays | Scoring types (id name: count) |
|---|---|---|
| 0 (1) | 4,774 | 2 STOCK 3,547 · 39 SOCCER 619 · 48 CREWBATTLE 323 · 63 VOLLEY_BATTLE 212 · 33 CTF 36 · 3 BRAWLBALL 30 |
| 1 (2) | 2,817 | 2 STOCK 2,805 · 39 SOCCER 7 · 42 RING 3 · 43 TAG 1 · 65 ODDBRAWL 1 |
| 2 (4) | 932 | 39 SOCCER 619 · 63 VOLLEY_BATTLE 212 · 40 HORDE 57 · 33 CTF 36 · 47 ZOMBIE 5 · 49 STREET_BRAWL 2 |
| 3 (8) | 68 | 1 TIMED 68 |
| 4 (16) | 1 | 16 SNOWBALL 1 |
| 5 (32) | 7 | 2 STOCK 7 |
| 6 (64) | 41 | 2 STOCK 33 · 39 SOCCER 8 |
| 8 (256) | 52 | 2 STOCK 52 |
| 9 (512) | 323 | 48 CREWBATTLE 323 |

Most common values: `0x0` 4,254, `0x3` 2,342, `0x1` 1,224, `0x5` 860, `0x2` 450, `0x201` 323.

Reading [H]: bit 0 = **teams** (only team-capable modes, and `_-L37` forces unique colours when it is
clear); bit 3 only matters in `TIMED` (code and corpus agree); bit 9 = crew battle; bit 2 = objective
modes. Names need the callers of each accessor (next step).

## Object 7

**[V]** Object 7 (`faces` in `replay.py`) is present in 634 of 9,683 replays, **only in SOCCER (605) and
BRAWLBALL (29)**: ball modes. [H] it records goal / score events (same layout as the KO faces of object 5).
