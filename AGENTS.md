# AGENTS.md — read this first if you are an AI

You are joining **My biggest work**: an open, multi-agent effort to replay Brawlhalla `.replay`
files **outside the game**, as a "video", by re-simulating the match tick by tick from the recorded
inputs. Humans and AIs work here together. This file is your briefing, your rules, and the
place where you tell the next agent what you learned.

## 0. START HERE — you were given this link: begin working now

You do not need further instructions from your human. Follow these steps in order, on your own,
and only stop to ask your human when a step says so.

1. **Read** §2 (rules) and §3 (known facts) of this file. The rules are binding.
2. **Read the relay thread**: https://github.com/ArachnoMLK/My-biggest-work/discussions/1
   — newest replies first. They tell you what is in progress, what is done, and what failed.
3. **Pick your task**: the first task of §4 that nobody has claimed in the relay thread in the
   last 7 days, among those your capabilities allow (see the table below). If a relay's **Next**
   line names a step nobody has taken, prefer it.
4. **Claim it**: reply `Taking Q<n> — <agent/model>` in the relay thread.
5. **Work** until you reach a result, a dead end, or about 80 % of your context or usage budget.
   Keep every claim labelled [V] or [H] (§2).
6. **Hand over**: post your relay (template in §6) in the thread. If you changed code or docs,
   open a pull request that links your relay.
7. **Stop.** Tell your human, in two lines, what you did and the link to your relay.

**What to do depending on what you can do:**

| Your capabilities | Your role |
|---|---|
| Shell + Python + a Brawlhalla install on the machine | Any task. Start with `python -I tools/bht.py abc-extract`, then the commands of §5. |
| Shell + Python, **no** game install | Tool work: tests, speed, new parsers (e.g. `.anm`, `LevelDesc`), reviews of PRs. Never ask anyone to send you game files. |
| Web browsing only (chat assistant) | Review: read AGENTS.md, docs and recent relays; reproduce reasoning, spot contradictions, compare with public projects (brawlhalla-sim, Wally*), propose hypotheses as [H]. |
| Cannot post on GitHub | Write your claim and your relay as text and ask your human to paste them in the relay thread (or to add them to `notes/` in a PR). This is the one step where you ask your human. |

**Ask your human only for:** permission to run a downloaded executable, access you do not have
(posting, an install), or a decision that changes the rules of §2. Everything else, decide yourself
and write down why in your relay.

**Prompt for humans** — paste this to your AI to enrol it:

> Join the open research project https://github.com/ArachnoMLK/My-biggest-work. Read its
> AGENTS.md and follow section 0 "START HERE" on your own until you have posted your relay.
> Report back to me with what you did and the link to your relay.

## 1. The goal, precisely

A `.replay` file contains **inputs only** (per player: timestamp + 14-bit key state), plus
match settings, players, results and KO times. It does **not** contain positions, damage or
animation states. The in-game replay player re-runs the match in the real engine.

So the deliverable is, in this order:

1. **Map**: every game file, what it is, which part of the replay pipeline uses it (`ledger/`).
2. **Read**: the replay reader and the simulation loop inside the game code (AVM2 bytecode).
3. **Reproduce**: a deterministic simulator that reaches *tick-level state equivalence* with the
   game for a given patch (positions, velocities, states, damage, KOs, final result).
4. **Render**: draw the simulated state with the real maps and animations.

Success test: for every replay of a corpus, the simulator's KO list and final scores equal the
ones stored in the replay. Anything less is "provisional".

## 2. Non-negotiable rules

1. **Never commit game content.** No `.swf`, `.swz`, `.anm`, `.bnk`, images, decrypted XML/CSV,
   extracted `.abc`, decompiled AS3, or `.replay` files (they contain player names). Everything
   derived from the user's install stays in `work/` (git-ignored). You may commit: our own code,
   file names, sizes, hashes, method ids, constants *you derived*, short quotes needed to identify
   a structure, and your conclusions.
2. **Label every claim**: **[V]** verified (say how: command, method id, file) or **[H]**
   hypothesis. Never present [H] as [V]. Unknown stays unknown.
3. **Pin the patch.** Game code is obfuscated (`_-y2E`, `_-V4R`…) and names change every patch.
   Always cite: patch, ABC SHA-256, method id, and the obfuscated name. Example:
   `11.00 / abc 7d308423… / method #3388 _-h3U._-C21`.
4. **Reproducible or it did not happen.** Give the exact `bht.py` command (or script in `tools/`)
   that shows your result on any machine with the game installed.
5. **No cheats, no live process access.** We read files on disk. We never inject into, hook or
   read the memory of the running game, never touch online services, never bypass anti-cheat.
   Do not use code from "trainer / ESP / hitbox hack" repositories.
6. **Do not run downloaded executables** unless the human owner approves it in the thread.
   Our tools are Python stdlib only on purpose.

## 3. What is already known (patch 11.00, October 2026)

| Fact | Status |
|---|---|
| Main code: `BrawlhallaAir.swf` → DoABC block of 4,029,515 bytes, SHA-256 `7d308423eaebcc82dfdda4ecc0e57d3abe78569534023aa7f9d776f626356db9` | [V] `bht.py abc-extract` |
| 854 classes, 15,510 methods, 15,453 bodies; **all bodies decode, 0 bad branch targets** with our disassembler | [V] `bht.py abc-validate` |
| ~25,600 obfuscated identifiers; only 95 classes keep a readable name; source language is Haxe (54 `*.hx` names in error strings) | [V] |
| Replay player lives in the same code: strings `REPLAY_MODE_REWIND_*`, `FASTFORWARD_*`, `SLOWMO_*`; netcode is rollback (`Rollback`, `RollbackFromInput`, `PostRollback`) | [V] strings |
| The replay player re-simulates with snapshots (rollback machinery) | [H] strong |
| `"Error in reading replay"` is pushed by methods #3388 `_-h3U._-C21`, #8732 (script init), #12889 `_-Y26._-I5w`, #12895 `_-Y26._-u52` → entry points to the replay reader | [V] `bht.py abc-find "Error in reading replay"` |
| `.swz` key 11.00 = `154281100`; it is a `uint` constant of the main ABC, so `bht.py swz-key` finds it instantly for any patch | [V] |
| Game data (`work/swz/`): `LevelDesc` per map (collisions, spawns, camera), `LevelTypes` (328 ids, kill zones), `powerTypes` (attacks, ~180 columns), `hurtboxTypes`, `HeroTypes` (only 4 stats), `DodgeTypes`, `itemTypes`, `GameModeTypes` | [V] |
| Movement constants (run speed, gravity, friction, jump impulses) are **not** in the data files: they are in code | [V] for HeroTypes, [H] for "all in code" |
| Replay corpus of the owner: 9,653 files, formats 261–271 (patches 10.02–11.00), 0 parse errors, 42.6 M input records | [V] `bht.py corpus` |
| **Every input timestamp is a multiple of 16 ms** (42,636,188 / 42,636,188) → one simulation tick = 16 ms | [V] |
| Replay header has a 32-bit `random_seed` → the simulation uses a seeded PRNG | [V] field exists, [H] usage |
| Object 6 (results) can appear several times (up to 11 in the corpus); "once per round" is the likely reason | [V] count, [H] reason |
| In score modes, object 5 (knockout faces) is empty and object 7 holds one event per point | [V] on one file, [H] in general |
| Patch 10.09 (not 11.00): grounded jump impulse −57, gravity 3.75, velocity scale 0.384 — from NickTacke/brawlhalla-sim | [V] by them, unverified on 11.00 |

Full background: [`docs/feasibility.md`](docs/feasibility.md). File formats: [`docs/replay-format.md`](docs/replay-format.md), [`docs/game-files.md`](docs/game-files.md).

## 4. Work queue (pick one, say so in the relay thread)

| ID | Task | Starting point |
|---|---|---|
| Q1 | ✅ **Done** (Claude, 2026-10-28): see [`docs/code-map-11.00.md`](docs/code-map-11.00.md). Map the replay reader: from method #3388 / #12889 to the class that holds the input timeline and to the code that feeds inputs to fighters. | `bht.py abc-disasm --method 12889`, `abc-find --member <name>` |
| Q2 | 🔄 **In progress** (Codex via @unfortunatelyalex, relay of 2026-10-28; PR pending). Find the main tick loop (16 ms) and the order of updates per tick (input → state machine → physics → collision → hits → KO). | search `16`, `0.016`, `60` constants, callers of the input consumer |
| Q3 | Identify the PRNG and where `random_seed` enters (item spawns, random legend/map). | header parser, `abc-find` on multiplications/xor constants |
| Q4 | Port the 10.09 movement evidence of brawlhalla-sim to 11.00 (same constants? same structure?). | their `docs/provenance.md` |
| Q5 | Movement constants as functions of the 4 stats (`Strength`, `Dexterity`, `Weight` = Defense in game, `Speed`). | `HeroTypes.xml`, getters around `Speed`/`Weight` |
| Q6 | Level collision model: how `HardCollision`, `SoftCollision`, `Bouncy*`, `NoSlide*` lines are tested each tick. | `LevelDesc_*.xml`, `CollisionObject.hx` strings |
| Q7 | Power (attack) state machine: how `powerTypes` columns drive cast, active frames, recover, combos, hitboxes. | `PowerType.hx` strings, `powerTypes.csv` |
| Q8 | Ledger: classify each file kind in `ledger/game-files.csv` by role in the replay pipeline (status `unread` → `read` → `documented`). | `bht.py inventory`, `swf-info` |
| Q9 | Meaning of replay object 7 and of the `settings.flags` bits. | `work/corpus.json`, the replay reader (Q1) |
| Q10 | A minimal **reference oracle**: any way to obtain ground-truth positions for a replay without touching the game process (e.g. frame capture of the in-game player by the human owner, then manual annotation). | discuss first |

## 5. Tools

```
python -I tools/bht.py --help
python -I tools/bht.py abc-extract           # main.abc + summary
python -I tools/bht.py abc-validate          # disassembler self-check
python -I tools/bht.py abc-classes --grep REGEX
python -I tools/bht.py abc-disasm --method N | --class ID
python -I tools/bht.py abc-find VALUE [--member]
python -I tools/bht.py abc-strings REGEX
python -I tools/bht.py abc-refs --method N  # members and constants one method touches
python -I tools/bht.py swz-key && python -I tools/bht.py swz-dump --key K
python -I tools/bht.py swf-info FILE.swf
python -I tools/bht.py replay FILE.replay [--json]
python -I tools/bht.py render-summary FILE.replay  # SVG: map geometry + input timeline + KOs
python -I tools/bht.py corpus [--dir FOLDER]
python -I tools/bht.py inventory             # rewrites ledger/game-files.csv, keeps status/notes
python -I -m unittest discover -s tests
```

Environment variables: `BRAWLHALLA_DIR` (install folder), `BRAWLHALLA_REPLAYS` (replay folder).
Add new tools to `tools/bh/` + a `bht.py` subcommand, stdlib only, with a test.

## 6. How agents talk to each other

**Primary: GitHub Discussions → thread "AI relay — read me first"** (category General, pinned).
At the end of every working session, post **one** reply with this template:

```
### Relay — <agent/model> — <date> — patch <x.yy>
**Task:** Q<n> (or new)
**Done:** what you established, each line [V] (+ command) or [H]
**Evidence:** method ids / files / commands
**Dead ends:** what you tried that did not work (so nobody repeats it)
**Next:** the single most useful next step
**Questions for humans:** (access, decisions)
```

Reply to other agents' relays when you confirm (`+[V] reproduced on <setup>`) or contradict them.
Disagreements are settled by a reproducible command, not by authority.

**Questions and proposals**: open a discussion in *Q&A* or *Ideas*. **Bugs in our tools**: issues.

**Fallback if you cannot use Discussions** (no API access, or GitHub unavailable): add a file
`notes/YYYY-MM-DD-<agent>.md` with the same template in a pull request. The human owner merges
notes and mirrors them to the relay thread.

## 7. Feedback on this file

This README for AIs is meant to evolve. If a rule slows you down, if something here is wrong or
missing, say it in the **"Feedback on AGENTS.md"** discussion, or open a PR that edits this file
with the reason in the description. Keep the rules of §2 unless the human owner agrees.
