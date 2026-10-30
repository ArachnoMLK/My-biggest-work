# Data registry (patch 11.00)

Pin: patch 11.00, abc `7d308423eaebcc82dfdda4ecc0e57d3abe78569534023aa7f9d776f626356db9`.

**[V]** `_-i2H.static._-U4F` #857 registers every data table of the `.swz` archives with its parser:
`_-F1m._-M46(name, parser)` for XML tables (one call per element) and `_-F1m._-13I(name, parser)` for CSV
tables (one call per row). 91 entries. Check: `abc-disasm --method 857`.

`LevelDesc` goes to `_-139.static._-PI` #5311, which stores each `LevelDesc` element by its `LevelName`
attribute in `_-139._-f3s` (a `StringMap`): this is the lookup the level selection uses (Q6).

"Simulation" marks the tables a re-simulator needs [H] (levels, powers, hurtboxes, stats, stances,
legends, items, scoring and game modes, spawns, animations and bones, costumes and weapon skins that may
change powers); the others are UI, store, progression and audio.

| Data | Parser | Kind | Simulation |
|---|---|---|---|
| `DefaultLegends` | `_-tE._-i32` | XML |  |
| `DodgeTypes` | `_-h3i._-i32` | XML | yes |
| `EmitterGroupTypes` | `_-W4p._-i32` | XML |  |
| `EmitterTypes` | `_-M41._-i32` | XML |  |
| `SoundVolumes` | `_-W4P._-i32` | XML |  |
| `ControllerTypes` | `_-J34._-i32` | XML |  |
| `ControllerMappingTypes` | `_-q3v._-i32` | XML |  |
| `StatTypes` | `_-C5c._-i32` | XML | yes |
| `HelpfulhintsTypes` | `_-M5z._-i32` | XML |  |
| `MusicTypes` | `MusicType._-i32` | XML |  |
| `TooltipTypes` | `_-221._-i32` | XML |  |
| `HurtboxTypes` | `_-x3p._-B6` | CSV | yes |
| `HotkeyTypes` | `HotkeyType._-i32` | XML |  |
| `VoiceOverTypes` | `_-Q3t._-i32` | XML |  |
| `AnimTypes` | `_-o5r._-i32` | XML | yes |
| `LevelDesc` | `_-139._-PI` | XML | yes |
| `ColorExceptionTypes` | `_-im._-B6` | CSV |  |
| `ClientThemeTypes` | `_-N1S._-i32` | XML |  |
| `TileTypes` | `_-f6S._-i32` | XML |  |
| `BoneTypes` | `_-T5Y._-i32` | XML | yes |
| `TournamentEventTypes` | `_-Y21._-i32` | XML |  |
| `StringTable` | `_-S5t._-K1L` | CSV |  |
| `LanguageTypes` | `_-S5t._-i32` | XML |  |
| `FontTypes` | `_-S5t._-x2B` | XML |  |
| `PowerSwapTypes` | `_-W3L._-i32` | XML | yes |
| `EndMatchVoicelineTypes` | `_-R2D._-B6` | CSV |  |
| `LessonCategoryTypes` | `_-R12._-i32` | XML |  |
| `HelpScreenTypes` | `_-P1B._-i32` | XML |  |
| `LessonTypes` | `_-S3O._-i32` | XML |  |
| `DefaultSoundBanks` | `_-m51._-933` | CSV |  |
| `DevOnlyDefaultSoundBanks` | `_-m51._-933` | CSV |  |
| `UITypes` | `_-b1G._-i32` | XML |  |
| `CutsceneType` | `CutsceneType._-14a` | XML |  |
| `BulletWaveTypes` | `_-O2L._-B6` | CSV |  |
| `StaticEventTypes` | `_-63l._-i32` | XML |  |
| `AvatarTypes` | `_-t3X._-B6` | CSV |  |
| `BattlePassRewardTypes` | `_-S2a._-S2N` | XML |  |
| `BattlePassTypes` | `_-A4g._-i32` | XML |  |
| `ChallengeTypes` | `_-S26._-i32` | XML |  |
| `ChanceBoxTypes` | `_-u48._-i32` | XML |  |
| `ChatChannelTypes` | `_-t3I._-i32` | XML |  |
| `ColorSchemeTypes` | `_-31J._-i32` | XML |  |
| `CostumeTypes` | `CostumeType._-B6` | CSV | yes |
| `CustomGameTypes` | `_-V4B._-i32` | XML | yes |
| `EntitlementTypes` | `EntitlementType._-i32` | XML |  |
| `GameModeTypes` | `_-A6._-i32` | XML | yes |
| `GuildMissionTypes` | `_-33b._-f2T` | XML |  |
| `GeoTypes` | `_-HH._-i32` | XML |  |
| `HeroTypes` | `HeroType._-i32` | XML | yes |
| `ItemSpawnRateTypes` | `_-T4A._-i32` | XML | yes |
| `ItemSpawnRuleSetTypes` | `_-w2j._-i32` | XML | yes |
| `ItemTypes` | `ItemType._-B6` | CSV | yes |
| `LevelSetTypes` | `_-91U._-i32` | XML | yes |
| `LevelTypes` | `LevelType._-i32` | XML | yes |
| `AchievementTypes` | `_-Y5u._-a1P` | XML |  |
| `MissionEventTypes` | `_-gz._-i32` | XML |  |
| `MissionTypes` | `_-Y5u._-X3V` | XML |  |
| `PastBattlePassRewardTypes` | `_-S2a._-n14` | XML |  |
| `PlayerThemeTypes` | `_-P2E._-i32` | XML |  |
| `PodiumTypes` | `_-f5U._-i32` | XML |  |
| `PowerTypes` | `PowerType._-B6` | CSV | yes |
| `QuestTypes` | `_-Y5u._-V4b` | XML |  |
| `RegionTypes` | `_-iz._-i32` | XML |  |
| `RuneTypes` | `_-a5R._-i32` | XML | yes |
| `ScoringTypes` | `ScoringType._-i32` | XML | yes |
| `SeasonBorderTypes` | `_-j1E._-i32` | XML |  |
| `SkirmishTypes` | `_-x2E._-i32` | XML |  |
| `SkirmishRewardTypes` | `_-H23._-i32` | XML |  |
| `SkirmishFactionTypes` | `_-I2w._-i32` | XML |  |
| `SpawnBotTypes` | `_-Q3W._-i32` | XML | yes |
| `SplashArtTypes` | `_-e6._-i32` | XML |  |
| `SteamPurchaseTypes` | `_-T8._-i32` | XML |  |
| `PromoTypes` | `StoreType._-52j` | CSV |  |
| `StoreTypes` | `StoreType._-44L` | CSV |  |
| `StoreEventTypes` | `StoreEventType._-i32` | XML |  |
| `TauntTypes` | `_-K3l._-i32` | XML |  |
| `TrailEffectTypes` | `_-13V._-i32` | XML |  |
| `TutorialTypes` | `_-J6J._-B6` | CSV |  |
| `WeaponSkinTypes` | `_-63m._-B6` | CSV | yes |
| `TimedEventTypes` | `_-e5w._-i32` | XML |  |
| `TimedPromotionTypes` | `_-73s._-i32` | XML |  |
| `MonikerTypes` | `_-11H._-B6` | CSV |  |
| `EmojiTypes` | `_-R4q._-B6` | CSV |  |
| `SpriteSourceTypes` | `_-A17._-B6` | CSV |  |
| `SpriteData` | `_-95S._-Z4g` | CSV |  |
| `CompanionTypes` | `CompanionType._-i32` | XML | yes |
| `GuildTagTypes` | `_-L4Q._-i32` | XML |  |
| `GuildTagCategoryTypes` | `_-z1j._-i32` | XML |  |
| `manualBoneSpriteData` | `_-95S._-Z4g` | CSV |  |
| `manualSpriteData` | `_-R5g._-Z4g` | CSV |  |
| `BoneSources` | `_-t2e._-i32` | XML |  |
