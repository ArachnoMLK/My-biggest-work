# My biggest work

**Goal: watch Brawlhalla `.replay` files outside the game, like the in-game replay player, by
re-simulating the match from the recorded inputs.**

A `.replay` only stores what each player pressed and when (one record per key change, on a
16 ms tick). The game rebuilds everything else (positions, attacks, damage) by running its own
engine again. Nobody has reproduced that engine publicly yet. This project tries, in the open,
with as many humans and AIs as want to help.

> Unofficial fan research project. Not affiliated with or endorsed by Blue Mammoth Games or
> Ubisoft. No game file is distributed here: you need your own installation. See [LEGAL.md](LEGAL.md).

## Where we are

- ✅ Tools to read every layer: `.swz` data archives (key found automatically), the game's
  bytecode (all 15,453 methods of patch 11.00 decode), any `.swf`, and `.replay` files
  (formats 261–271, 9,653 real replays parsed with zero errors).
- ✅ Facts checked so far: 16 ms simulation tick, seeded PRNG in the replay header, entry points
  of the replay reader in the code. Full list in [AGENTS.md §3](AGENTS.md#3-what-is-already-known-patch-1100-october-2026).
- ⏳ Next: map the replay reader and the tick loop, then movement, collisions, attacks.
- ❌ No simulator yet. No video yet.

## Join

- **AIs**: start with [AGENTS.md](AGENTS.md). It has the rules, the work queue and the relay
  protocol.
- **Humans**: read [CONTRIBUTING.md](CONTRIBUTING.md), then pick a task in the work queue or ask in
  [Discussions](../../discussions). Comments, questions and corrections are welcome from anyone.

## Quick start

Requires Python 3.10+ (standard library only) and a Brawlhalla installation.

```bash
git clone https://github.com/ArachnoMLK/My-biggest-work.git
cd My-biggest-work
python -I tools/bht.py abc-extract        # code of your installed patch -> work/abc/
python -I tools/bht.py swz-key            # prints the data key of your patch
python -I tools/bht.py swz-dump --key <K> # game data -> work/swz/
python -I tools/bht.py replay "<path to a .replay>"
python -I -m unittest discover -s tests
```

Everything extracted goes to `work/`, which git ignores. Never commit it.

## Layout

| Path | Content |
|---|---|
| `AGENTS.md` | Briefing for AI agents: rules, known facts, work queue, relay protocol |
| `tools/bht.py`, `tools/bh/` | The toolkit (swz, swf, abc, replay) |
| `tests/` | Self-tests (game-dependent tests are skipped without an install) |
| `docs/` | Feasibility study, file formats, game file roles |
| `ledger/game-files.csv` | Every file of the install (name, size, hash, kind) with its research status |
| `notes/` | Fallback relay notes when Discussions cannot be used |

## Credits

Built on public work by the Brawlhalla research community: allhailcheese and moffel1020
(BrawlhallaReplayLibrary, bhswz-rs, WallyAnmRenderer, WallyMapEditor), itselectroz
(brawlhalla-replay-reader), NickTacke (brawlhalla-sim). See `docs/feasibility.md` for links.

License: [MIT](LICENSE) for the code of this repository.
