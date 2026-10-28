# Contributing

Everyone is welcome: humans and AI agents, beginners and reverse engineers. The rules are the
same for all. They are written in full in [AGENTS.md §2](AGENTS.md#2-non-negotiable-rules); in short:

1. **No game content in the repository**: no game files, decrypted data, extracted bytecode,
   decompiled code or replay files. Only our code, identifiers, hashes, derived constants and
   conclusions.
2. **Label claims** [V] verified (with the command that shows it) or [H] hypothesis.
3. **Pin the patch** and the ABC hash when you cite code; obfuscated names change every patch.
4. **Reproducible commands** for every result.
5. **Files on disk only**: no memory reading, injection or hooking of the running game, no
   online services, no cheat code.

## Ways to help

- Take a task from the work queue (AGENTS.md §4) and announce it in the relay thread.
- Reproduce someone else's [V] claim on your machine and reply `+[V] reproduced`.
- Improve the tools (`tools/bh/`, stdlib Python only, with a test in `tests/`).
- Update `ledger/game-files.csv`: set `status` (`unread` → `read` → `documented`), `owner` and
  `notes` for files you studied. `bht.py inventory` keeps these columns when it refreshes hashes.
- Comment and question: [Discussions](../../discussions) are open to everyone.

## Pull requests

- One topic per PR; say which task (Q-number) it serves.
- Run `python -I -m unittest discover -s tests` before pushing.
- Write in English (code, comments, docs) so that every contributor can follow.
