# Game files and their role (patch 11.00)

Per-file list with hashes and research status: [`ledger/game-files.csv`](../ledger/game-files.csv)
(regenerate with `bht.py inventory`; the `status`, `owner` and `notes` columns are kept).

| Kind | Files | Role for a replay player | Status |
|---|---|---|---|
| `BrawlhallaAir.swf` (main-code) | 1 | **All game logic**, including the replay reader, the replay player UI logic and the simulation. 12 DoABC blocks; the big one (4.0 MB) is the game. | [V] located; reading = Q1–Q7 |
| `*.swz` (Engine, Init, Game, Dynamic) | 4 | Encrypted game data. Init: `AnimTypes`, `BoneTypes`, `BoneSources`, `LevelTypes`. Game: `powerTypes`, `hurtboxTypes`, `HeroTypes`, `DodgeTypes`, `itemTypes`, `GameModeTypes`, `ScoringTypes`… Dynamic: one `LevelDesc` per map. | [V] decrypted with `swz-dump` |
| `anims/*.anm` | 105 | Bone animations (frames, bone transforms) per animation class; rendering, and probably attack timing. | [V] present; format read by WallyAnmSpinzor; not parsed here yet |
| `bones/Bones_*.swf` | 112 | Vector sprites of bones (body parts, weapons). Rendering only. | [H] |
| `Gfx_*.swf` | 372 | Skins and effects graphics. Rendering only. | [H] |
| `SFX_*.swf`, `audio/` | 96 + 225 banks | Sounds. Not needed. | [H] |
| `UI_*.swf` | 116 | Interface. `UI_Replays.swf` holds replay screen symbols (`a_ScreenReplayControls`, `a_ReplaySetting*`) and only 2.5 KB of code. | [V] `swf-info` |
| `mapArt/`, `images/` | 6,671 images | Map backgrounds, platforms, thumbnails. Rendering only. | [V] present |
| `languages/*.bin` | 13 | Text. Not needed (except to name things). | [H] |
| `META-INF/AIR/` | — | AIR app descriptor: native extensions `SteamAir`, `MultiKeyboard`, `RawData` (decrypts `.swz`), `DnaManager`, `EpicAir`, `WindowsExtensionWrapper`, `DesktopExtension`, `SoundEngineExtension`. | [V] |

## What a simulator needs, and where it is

| Need | Source |
|---|---|
| Inputs, seed, settings, players | `.replay` [V] |
| Map geometry, spawns, kill zones | `LevelDesc_*.xml` + `LevelTypes.xml` [V] |
| Attack definitions | `powerTypes.csv`, `PowerSwapTypes.csv` [V] |
| Hurtboxes | `hurtboxTypes.csv` [V] |
| Attack hitboxes and active frames | `.anm` + `powerTypes` [H] |
| Movement constants and formulas | **code only** (`BrawlhallaAir.swf`) [H] |
| Tick order, state machines, damage/knockback formulas, PRNG | **code only** [H] |
