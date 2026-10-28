# HANDOFF — 2026-10-28

Lead review and local integration of two Claude Opus 5.5 implementation tasks (T3,
`effort: ultrathink`). Project overview: [PROJECT.md](PROJECT.md); rules: [AGENTS.md](AGENTS.md);
decisions: [DECISIONS.md](DECISIONS.md).

## Repository and access

- [V] Integration branch: `integration/replay-foundations-2026-10-28`, in the existing T3
  worktree `C:/Users/alex/.t3/worktrees/My-biggest-work/t3-24571f32`. Based on fetched
  `origin/main` `3e10517`, context commit `105d402`, Q3 cherry-pick `ee165ba`, then lead review fixes.
  Published after explicit user authorization as [PR #14](https://github.com/ArachnoMLK/My-biggest-work/pull/14),
  from the same branch on `unfortunatelyalex/My-biggest-work` into upstream `main`. No merge or release.
- [V] Original `main` remains at `06d1f3b`, one commit behind fetched upstream, with its original
  local changes: `.gitignore`, `AGENTS.md`, `.claude/`, `.mcp.json`, `.sharelane/`, `CLAUDE.md`.
  It was not pulled, reset, stashed or modified. Use the integration worktree for the new commands.
- [V] ShareLane MCP is unavailable: its configured script belongs to the previous machine and
  is missing here. No ShareLane claims, context updates or onboarding completion were fabricated.
  Task scopes were separated in T3 worktrees. Restore ShareLane before relying on its context map.
- [V] GitHub discussions including replies, all ten open issues, PR history and local task branches
  were read. Q3 claim: [discussion comment](https://github.com/ArachnoMLK/My-biggest-work/discussions/1#discussioncomment-19247299).

## Implemented and independently reviewed

- [V] Recovered the Q2 [tick-loop map](docs/tick-loop-11.00.md), Q1 map update and
  [previous relay](notes/2026-10-28-codex-q2.md) from local commit `6d7c074`, without its
  `.gitignore` or ShareLane files. Key scheduler, pass-order and checkpoint anchors were
  checked against the pinned ABC. Q2 ring-out/score commit order is still open.
- [V] Repaired replay test sampling: inspect the version first, select at most 20 supported
  formats (261–271), explicitly skip if none exist, and preserve supported-file parse failures.
  Synthetic mixed/unsupported/broken samples cover the behavior. Parser support was not broadened.
- [V] Added Q3's [WELL512 reference and evidence](docs/prng-11.00.md), range/shuffle helpers,
  `prng` and `prng-verify` commands, and independent/golden tests. Both identified match seed
  paths reach `Random`: rules starts at draw 0; items consumes two draws in #4908 after seeding.
- [V] Lead review found and fixed two defects: snapshot restore now rejects noninteger index/words
  without changing existing state, and verification reports missing required methods rather than
  silently skipping helpers. Regression tests cover both.
- [V] Narrowed unsupported exhaustive PRNG claims; consumer totals from the uncommitted exploratory
  classifier are provisional [H]. Individual sites retain method ids for manual verification.

## Validation

Pin: **11.00 / ABC SHA-256
`7d308423eaebcc82dfdda4ecc0e57d3abe78569534023aa7f9d776f626356db9`**.
Local install is `F:/SteamLibrary/steamapps/common/Brawlhalla`; set `BRAWLHALLA_DIR` for commands
on this host only. All game-derived bytes/listings stay in ignored `work/`.

Run from the integration worktree:

```powershell
$env:BRAWLHALLA_DIR='F:/SteamLibrary/steamapps/common/Brawlhalla'
python -I tools/bht.py abc-extract --game $env:BRAWLHALLA_DIR
python -I -W error::ResourceWarning -m unittest discover -s tests -v
python -I tools/bht.py prng-verify --draws 1000
python -I tools/bht.py abc-validate
git diff --check
```

- [V] Full combined suite: **29 tests passed, zero skipped**, resource warnings treated as errors.
- [V] PRNG verifier: **6 seeds × 1,000 draws plus range/shuffle cases passed**.
- [V] ABC validation: **15,453 bodies decoded, zero errors, zero bad branch targets**.
- [V] Signed-seed/skip/JSON CLI smoke passed; original main's dirty file list remains unchanged.
- [V] Context worker counted 9,079 local replays (formats 248–271), including 2,373 supported files;
  this differs from the owner's documented corpus. The integration test parsed 20 format-271 files.
  Full local corpus validation was not run.

## Limits and next step

- No simulator, runtime equivalence or video. The bytecode interpreter models AVM2 semantics;
  a running-game oracle has not confirmed its arithmetic or output. Snapshot byte order is unknown.
- Consumer counts are provisional. Whether global-generator draws affect simulated state remains
  unknown; UI `_-9D._-Y15` and `MessageTrigger.Tick` draw from the rules stream and need tracing.
- **Next:** combine Q2's scheduler with Q3's rules/items consumers to establish draw order during
  replay playback, including those UI/trigger paths. Then continue Q2's #2977/#3138/KO-writer trace.
- The user explicitly authorized PR creation after local integration. [PR #14](https://github.com/ArachnoMLK/My-biggest-work/pull/14)
  now publishes the reviewed Q2/Q3 integration and links both relays. Upstream push access was
  unavailable, so publication uses a fork; original remotes and dirty main were preserved.
  Original task commits remain `105d402` and `5960f14` on their task branches. Review and merge are pending.
