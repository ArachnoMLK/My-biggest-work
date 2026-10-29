# DECISIONS

Only decisions already in force, each with where it is recorded. New decisions that change
the rules of [AGENTS.md §2](AGENTS.md#2-non-negotiable-rules) need the human owner's agreement.

| # | Decision | Why | Source |
|---|---|---|---|
| D1 | No game content in git: no game files, decrypted data, extracted ABC, decompiled code, `.replay` files or player names. Derived output stays in `work/`. | Legal and privacy; replays contain player names. | AGENTS.md §2.1, [LEGAL.md](LEGAL.md), `.gitignore` |
| D2 | Every claim is labelled [V] (with command/method id) or [H]. | Agents hand over to each other; unverified claims must not propagate as facts. | AGENTS.md §2.2 |
| D3 | Cite patch + ABC SHA-256 + method id + obfuscated name. | Obfuscated names change every patch. | AGENTS.md §2.3 |
| D4 | Files on disk only: no live process access, injection, online services or cheat code. | Anti-cheat and terms of service. | AGENTS.md §2.5 |
| D5 | Tools are Python standard library only; run with `python -I`; no downloaded executables without owner approval. | Reproducible on any machine; no supply-chain risk. | AGENTS.md §2.6, §5 |
| D6 | Simulation tick = 16 ms. | Every input timestamp of the owner's corpus is a multiple of 16; Q2 found the 16 ms scheduler (#3336). | AGENTS.md §3, [docs/tick-loop-11.00.md](docs/tick-loop-11.00.md) |
| D7 | Supported replay formats are 261–271 (`replay.PATCHES`). Older formats are not claimed as supported, even when the parser happens to accept them. | No evidence for older layouts; the reader was ported for these versions. | `tools/bh/replay.py` docstring |
| D8 | The replay integration test samples up to 20 supported-format replays (version peeked before parsing), skips with a message when there are none, and lets parse errors of supported files fail. | Local folders mix older formats (D7); filtering must not hide real parser failures. | `tests/test_tools.py` (`supported_sample`), this change |
| D9 | Coordination through the GitHub Discussions relay thread; `notes/` file in a PR as fallback. | Asynchronous multi-agent handover. | AGENTS.md §6 |
| D10 | A future simulator keeps the game's per-tick pass boundaries and entity order until commutativity is shown. [H] design guidance, not yet tested. | Reordering could change behavior. | [docs/tick-loop-11.00.md](docs/tick-loop-11.00.md) "Limits" |
