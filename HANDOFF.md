# HANDOFF — 2026-10-28

State at the end of the Claude Opus 5.5 context/integration session. Overwrite this file at each
handover; history lives in the relay thread and `notes/`.

## Repository state

| Item | State |
|---|---|
| This branch | `t3/24571f32` (T3 worktree), fast-forwarded to `origin/main` `3e10517` (README image, `render-summary`) plus one local commit. Not pushed. |
| Local root checkout (`main`) | At `06d1f3b`, 1 behind `origin/main`, so it lacks `render-summary` until synced. Dirty: modified `.gitignore`, `AGENTS.md`; untracked `.claude/`, `.mcp.json`, `.sharelane/`, `CLAUDE.md`. Left untouched. |
| ShareLane | Unavailable: `.mcp.json` points to a missing `sharelane.mjs`. No claims or locks were recorded through it; file scope was kept by agreement instead. |

## Verified in this session ([V], patch 11.00, ABC `7d308423…6db9`, `BRAWLHALLA_DIR` set per command)

- `abc-extract` reproduces the pinned SHA-256; `abc-validate`: 15,453 bodies, 0 errors, 0 bad branches.
- Q2 anchors re-checked with `abc-disasm`: #3336 @417–493 (mod-16 rounding), @1838–1896
  (`floor(max(T−S,0)/16)`), @1908–1922 (`t += 16`), @4073–4077 (loop test), @2560–2594
  (`_-vs + 450` gate), @2725–2888 (passes `_-k5H` → `_-10` → `_-s4H`/`_-d3s` → `_-J2g`),
  @1814–1821 (start := `_-717`); #3594 @126–231 (5 or 300-tick anchor); #2990 @548/@566;
  #3138 @1147 `Respawn`; #2984 @6597 `OnHit`/17. No contradiction found. Only clarification
  added: table receivers are `_-h3U` property names, method ids belong to `_-E1V`, `_-26u`, `_-99`.
- Local replay folder: 9,079 files, formats 248–271; 2,373 are in the supported 261–271 range.
  (Not the owner's 9,653-file corpus of AGENTS.md §3.)
- `python -I -m unittest discover -s tests -v`: 12 tests, OK, 0 skipped (also with
  `-W error::ResourceWarning`). Replay test parsed 20 format-271 files.

## Known failures and limits

- Fixed: `test_some_replays_parse` failed on local format-257 replays (`assertIn(version, PATCHES)`).
  The test now samples supported formats only; old formats are still not supported (D7, D8).
- The parser accepts some pre-261 replays without error; whether its output is right for them is unknown.
- `bht.py corpus` was not run on the local folder in this session.

## Pending

- **Q2 publication:** the Codex Q2 docs (from local ShareLane commit `6d7c074`, without its
  `.gitignore`/`.sharelane` changes) are in this branch. The maintainer asked for a PR
  ([reply](https://github.com/ArachnoMLK/My-biggest-work/discussions/1#discussioncomment-19245150));
  no PR was opened in this session because remote changes were not authorized.
- **Q3 (parallel):** another Claude worker on `t3/implement-replay-prng-q3` owns
  `tools/bh/prng.py`, `tools/bht.py`, `tests/test_prng.py`, `docs/prng-11.00.md`,
  `notes/2026-10-28-claude-q3.md`. No file overlap with this branch.
- README progress row for Q2 still says "in progress"; update it with the Q2 PR.

## Next steps

1. Owner/lead: review this branch, open the Q2 PR linking the Codex relay, and post
   [notes/2026-10-28-claude-context.md](notes/2026-10-28-claude-context.md) to the relay thread.
2. Q2 follow-up: trace `Entity._-x1M` #2977 and `Entity._-eR` #3138 to their boundary/score
   consumers and find the replay KO writer, to fix ring-out order relative to `_-26u._-d3s` #1665.
3. Merge Q3 when its worker reports; then the seed path from #3348 can be cross-checked.
