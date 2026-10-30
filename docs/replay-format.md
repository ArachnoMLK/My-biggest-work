# `.replay` format (formats 261–271, patches 10.02 – 11.00)

Implementation: [`tools/bh/replay.py`](../tools/bh/replay.py). Field names follow
BrawlhallaReplayLibrary (allhailcheese, MIT). Corpus check: 9,653 replays, 0 errors **[V]**.

## Envelope

1. zlib-compressed.
2. XOR with a fixed 64-byte key (`KEY` in `replay.py`), byte `i` with `KEY[i % 64]`.
3. MSB-first bit stream: `u32 version`, then objects, each prefixed by a 4-bit type, until type 2.

Version → patch: 261 = 10.02 … 268 = 10.09 … 271 = 11.00 (`PATCHES`).

## Objects

| Type | Name | Content |
|---|---|---|
| 3 | Header | `u32 random_seed`, `u32 playlist_id`, `str playlist` (if id ≠ 0), `bit online` |
| 4 | GameData | 15 × `u32` settings, `u32 level_id`, `u16 hero_count`, entities (while bit = 1), `u32 checksum` |
| 6 | Results | `u32 length_ms`, scores (`5-bit entity`, `i16 score`), `u32 end_of_match_fanfare`. Can repeat (up to 11 times seen) |
| 1 | Inputs | per entity (while bit = 1): `5-bit entity`, `i32 count`, then `count` × (`i32 timestamp_ms`, `bit has_flags`, `14-bit flags`) |
| 5 | KnockoutFaces | (`5-bit entity`, `i32 timestamp_ms`) while bit = 1 |
| 7 | Faces (other) | same layout; only in SOCCER and BRAWLBALL replays **[V]** (634 / 9,683, see [`settings-flags-11.00.md`](settings-flags-11.00.md)), goal events **[H]** |
| 2 | End | — |

Order seen in the corpus: `3-4-6…6-1-5-[7]-2` **[V]**.

### Settings (15 × u32)

`flags, max_players, duration, round_duration, starting_lives, scoring_type_id, score_to_win,
game_speed, damage_multiplier, level_set_id, item_spawn_ruleset_id, weapon_spawn_rate_id,
gadget_spawn_rate_id, custom_gadget_selection, variation`.

### Entity

`i32 id`, `u32 player_id` (format ≥ 268), `str name`, 6 × `u32` (color scheme, spawn bot,
companion, emitter, trail, player theme), 8 × `u32` taunts, `u16` win taunt, `u16` lose taunt,
owned-taunt bit field (`u32` words while bit = 1), `u16 avatar`, `i32 team`, `i32 connection_time`,
then per hero: `u32 hero_id`, `u32 costume`, `u32 stance`, weapon skins (`bit, 15 bits, bit, 15 bits`),
then `bit bot`, `bit handicaps` (+ 3 × `u32`).

The GameData checksum is `(Σ entity checksums + level_id × 47) mod 173`; see `replay.py` for the
per-entity formula. A mismatch means the format changed.

### Inputs

- One record per **change** of the 14-bit key state, per entity.
- **All timestamps are multiples of 16 ms** (42,636,188 records) **[V]** → the simulation tick is 16 ms.
- Bits (low to high): `AimUp, Drop, MoveLeft, MoveRight, Jump, PrioritiseNeutralOverSide,
  HeavyAttack, LightAttack, DodgeDash, PickUpThrow, TauntUp, TauntRight, TauntDown, TauntLeft`.
- **Naming conflict** [H]: brawlhalla-sim proves on 10.09 that value 32 is *Aim Up* (paired with value 1 = Up), where
  BrawlhallaReplayLibrary names value 1 `AimUp` and value 32 `PrioritiseNeutralOverSide`. See
  [`prior-art-brawlhalla-sim.md`](prior-art-brawlhalla-sim.md#inputs--a-naming-conflict-to-resolve).
- The game consumes edges (pressed this tick and not the previous one): `(current XOR previous)
  AND current` on 10.09 per brawlhalla-sim **[V] by them**.

## Open questions

- How the game turns `random_seed` into its PRNG state (Q3).
- Meaning of `settings.flags` bits and of object 7 in every mode (Q9).
- Whether timestamps are relative to match start or to the countdown end.
