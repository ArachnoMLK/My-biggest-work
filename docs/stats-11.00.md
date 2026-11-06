# Fighter stats from the legend's stance (Q5, patch 11.00)

Pin: patch 11.00, abc `7d308423eaebcc82dfdda4ecc0e57d3abe78569534023aa7f9d776f626356db9`.
Checks: `python -I tools/bht.py stats-verify` (29 pinned instructions, `tools/bh/stats.py`), then
`python -I tools/bht.py legend-stats --hero <HeroName> --stance <n>` to print the result for one stance
from your local `swz-dump` (no game data is stored in the repository).

## Result

**[V]** Movement and recovery constants are **not computed by a formula**: they are **table lookups**.

1. `RuneTypes.xml` (Game.swz) has one `RuneType` per legend and stance (`RuneIndex`, the replay's
   `stance`), with four levels `Strength`, `Dexterity`, `Weight` (shown as Defense in game), `Speed`.
   `HeroName` is written once and carries over to the following entries (`_-a5R.static._-765` #7304).
2. `StatTypes.xml` (Game.swz) has 12 entries per family: `Strength0`…`Strength11`,
   `Dexterity0`…`11`, `Weight0`…`11`, `Speed0`…`11`, plus mode entries (`BrawlballStats`, `CTFBaseStats`,
   `HordeStats`, `ZombieStats1`…`9`, …).
3. `_-C5c.static._-i32` #11986 builds `_-C5c._-cx[family][level]` = the StatType named
   `FAMILY[family] + level` for level 0…11 (`11 + 1` loop bound @175, string `add` @202, error
   `'Missing Core Stat: '` @302), with `FAMILY = [Strength, Dexterity, Weight, Speed]` (`_-36d`, #11990).
   `_-C5c.static._-q2w(family, level)` #11988 returns it, or `null` if `family ≥ 4` or `level > 11`.
4. **[V] The stance is the replay's.** The replay parser `_-24q._-b2L` #6699 reads, per hero, `hero_id`
   (`_-TC`), `costume` (`_-617` @1156), `stance` (`_-b67` @1168), weapon skins (`_-T3n`), in the order of
   `docs/replay-format.md`; `Entity._-f6Q` #3051 calls `_-p1E(heroType, record._-b67)` (@372–382).
5. `Entity._-p1E` #3049 reads the stance's four levels, calls `_-q2w(0…3, level)` and copies **only each
   family's own fields** into the fighter. A mode override (`_-nt`, non-null) replaces all four lookups.

| Family | Fields copied into the fighter |
|---|---|
| Strength | `ImpulseMult` |
| Dexterity | `RecoverMod`, `AirRecoverMod`, `SigRecoverMod`, `MinChargeMod`, `DurabilityMod` |
| Weight | `Recovery` |
| Speed | `AnimSpeed`, `RunSpeed`, `AirRunSpeed`, `Acceleration`, `AirAcceleration`, `Friction`, `AirFriction`, `JumpXImpulse` |

These are exactly the fields each family sets in `StatTypes.xml`.

## Parsing details that matter for a faithful port

- **`Template` is skipped** (`_-72d` #11987 returns at @47 when `StatName == 'Template'`). Missing fields
  keep the **constructor defaults** of `_-C5c.<init>` #11983, not the `Template` values. They differ: for
  example the default `AirRunSpeed` is `30.0` in code (@66) while the `Template` entry says `0`.
- **Four fields are stored as reciprocals**: `AirRecoverMod`, `RecoverMod`, `SigRecoverMod`,
  `MinChargeMod` are stored as `1.0 / value` (e.g. `pushdouble 1.0 … divide` @242–256 for `AirRecoverMod`).
- Engine field names (11.00): `ImpulseMult _-z4f`, `RecoverMod _-yD`, `AirRecoverMod _-G6R`,
  `SigRecoverMod _-Y4G`, `MinChargeMod _-d3w`, `DurabilityMod _-q10`, `Recovery _-z2p`, `AnimSpeed _-I3r`,
  `RunSpeed _-M1U`, `AirRunSpeed _-z2v`, `Acceleration _-m3Q`, `AirAcceleration _-i3E`, `Friction _-T2P`,
  `AirFriction _-h5M`, `JumpXImpulse _-13G`; also parsed but not stance-driven: `DamageFixed _-n2x`,
  `HPOffset _-w3F`, `ImpulseNegation _-P1r`, `InterruptThreshold _-ro`.

## Open

- [H] The `JumpXImpulse` default comes from a static field (`_-32g`), not a literal.
- Not yet: how `RunSpeed`, `Acceleration`, `Friction` are used per tick (Q4 covers vertical motion only).
