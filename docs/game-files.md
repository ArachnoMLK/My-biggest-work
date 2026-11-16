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

## Ledger roles (Q8)

Every row of `ledger/game-files.csv` now carries a `role:` tag in `notes` (rule-based on folder, name
and kind; `status` stays `unread` until someone studies the file):

| Role | Files | What it is | Needed to re-simulate? |
|---|---|---|---|
| `sim-code` | 1 | `BrawlhallaAir.swf`: the main ABC (simulation, replay reader) | yes |
| `sim-data` | 88 | the 4 `.swz` archives (levels, powers, stats…) and the `.anm` animation timelines | yes |
| `render` | 6,309 | `Gfx_*.swf`, `bones/`, `sprites/`, `mapArt/` | only to draw the result |
| `audio` | 348 | `SFX_*.swf`, sound banks, `.wem` | no |
| `ui` | 981 | `UI_*.swf`, `images/`, `languages/`, fonts, icons | no |
| `runtime` | 54 | launcher, Steam DLLs, AIR packaging (`META-INF/`) | no (never run or modified) |

So the simulator itself depends on **89 files** out of 7,781. Next for Q8: set `status: read` and a short
note for each `sim-data` file once its sections are described (start with the `.anm` format, issue #13).
