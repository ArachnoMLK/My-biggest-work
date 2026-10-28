# PROJECT — short overview

Replay Brawlhalla `.replay` files outside the game by re-simulating the match from the recorded
inputs. Rules, task queue and relay protocol: [AGENTS.md](AGENTS.md). Decisions:
[DECISIONS.md](DECISIONS.md). Current state of work: [HANDOFF.md](HANDOFF.md).

## Pipeline we are building

1. **Map** game files and their role ([ledger/game-files.csv](ledger/game-files.csv), [docs/game-files.md](docs/game-files.md)).
2. **Read** the replay reader and the simulation loop in the game bytecode
   ([docs/code-map-11.00.md](docs/code-map-11.00.md), [docs/tick-loop-11.00.md](docs/tick-loop-11.00.md)).
3. **Reproduce** a deterministic simulator with tick-level equivalence (not started).
4. **Render** the simulated state with real maps and animations (not started).

## Architecture

| Path | Role |
|---|---|
| `tools/bht.py` | Single CLI; every result in the docs is reproduced by one of its subcommands. |
| `tools/bh/swf.py`, `abc.py` | SWF container and AVM2 (ABC) parser, disassembler, constant/member search. |
| `tools/bh/swz.py` | `.swz` decryption (key found among the ABC `uint` constants). |
| `tools/bh/replay.py` | `.replay` reader, formats 261–271 (10.02–11.00), keeps every input record. |
| `tools/bh/prng.py` | WELL512 reference, range/shuffle helpers and bytecode verifier (`prng`, `prng-verify`); [Q3 evidence](docs/prng-11.00.md). |
| `tools/bh/render.py` | `render-summary`: SVG of map geometry and key presses for one replay (no positions). |
| `tests/test_tools.py` | Pure tests always run; game- and replay-dependent tests skip without a local install. |
| `docs/`, `notes/` | Findings pinned to a patch and ABC hash; relay drafts. |
| `work/` (git-ignored) | Everything extracted from the local install. Never committed. |

Python 3.10+, standard library only.

## Current capabilities (patch 11.00)

- Extract and fully decode the main ABC (15,453 bodies, 0 errors, 0 bad branches).
- Find the `.swz` key and dump game data to `work/swz/`.
- Parse supported replays: header, settings, players, full input timelines, KO times, results.
- Static maps of the replay reader (Q1) and the 16 ms fixed-step scheduler and pass order (Q2).
- [V] Q3's identified replay seed paths reach two WELL512 instances; the reference port matches
  the emulated pinned bytecode. Runtime equivalence and full consumer order remain unverified.
- Draw one replay's stage geometry and input timeline (`render-summary`, on `origin/main` since `3e10517`).

**Not available yet:** no simulator, no player positions, no video. Every replay picture so far
shows inputs and static geometry only.
