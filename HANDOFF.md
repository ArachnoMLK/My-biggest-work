# HANDOFF — 2026-10-29

Sol lead review of Claude Opus 5.5 implementation (`effort: ultrathink`, fast mode off).
Overview: [PROJECT.md](PROJECT.md). Rules: [AGENTS.md](AGENTS.md). Decisions: [DECISIONS.md](DECISIONS.md).

## Repository and continuity

- [V] PR #14 (Q2 map, Q3 WELL512 reference and test repair) and #15 (Q4 movement) are merged.
  Fetched upstream `main` is `6834ad5`; open PRs #16–#23 cover inputs, stats, ledger, animations,
  collisions, flags, attacks and horizontal motion. They were inspected for scope, not accepted
  as verified or reimplemented. See [night relay](notes/2026-10-29-claude-night.md).
- [V] Current work: branch `t3/prng-order-verification`, T3 worktree
  `C:/Users/alex/.t3/worktrees/My-biggest-work/t3-ede82da9`, based on `6834ad5`.
  Claude implementation commit `556d036` is followed by Sol's review fixes and context update.
  [Claim](https://github.com/ArachnoMLK/My-biggest-work/discussions/1#discussioncomment-19260768).
  [Posted session relay](https://github.com/ArachnoMLK/My-biggest-work/discussions/1#discussioncomment-19261019).
- [V] Original dirty `main` at `06d1f3b` was not pulled, reset, stashed or edited by this session.
  Existing task worktrees `t3-24571f32` and `t3-b64061c8` were preserved. Use the new worktree for
  the new command; root checkout still lacks the merged tooling.
- [V] ShareLane tools are unavailable and the executable configured in `.mcp.json` is missing.
  No ShareLane claim, onboarding completion or context update was fabricated. T3 supplied the
  isolated worktree. Restore ShareLane before relying on its placeholder context chunks.

## Reviewed result — Q3 static ordering

Pin: **11.00 / ABC SHA-256
`7d308423eaebcc82dfdda4ecc0e57d3abe78569534023aa7f9d776f626356db9`**.
Evidence and boundaries: [prng-order-11.00.md](docs/prng-order-11.00.md).

- [V] Scheduler `_-h3U._-01I` #3336 orders the identified entry points as rules phase 3
  `_-u1O` @2624, items phase 4 `_-O3d` @2695, then phase 9 lesson `_-44D` @2992 or rules
  `_-m4d` @3009. Receiver slot types now confirm the rules and items owners previously [H] in Q2.
- [V] `_-z1C._-O4q` #5131 is false for modes 1024/2048. The identified lesson-only path reaches
  `MessageTrigger.Tick` #5809 (rules draw @731); replay start #3624 sets 1024 before seeding.
  This proves the guard, not that every playback mode transition preserves it (L1).
- [V] The identified scoreboard taunt path `_-9D._-Y15` #13733 is called by
  `ScreenScoreboard.OnTickScreen` #10946. Frame wrapper #3335 calls the tick batch @1815,
  then screen updates @2556. On this path its direct draws fall between tick batches.
  Whether it can precede later gameplay-relevant rules draws is unknown (L2).
- [V] Phase 4 visits the two item refresh helpers in order; their cached fields `_-Y1h`/`_-5J`
  are refreshed after `_-e3K` calls. [H] these represent two item spawn lanes; their meaning is open.
- [V] Added `prng-order-verify`, reusing `movement.check/listing`: 87 instruction anchors,
  10 name-based reference sets, 9 slot types. Wrong patch exits 2; mismatches fail.
  Sol fixed an unclosed CLI file and a reference scan that skipped undecodable methods,
  added explicit guard branches and a regression test, and narrowed unsupported prose.

## Validation

Local install: `F:/SteamLibrary/steamapps/common/Brawlhalla` (host setting, not a portable default).
All extracted data and review listings stay under ignored `work/`.

```powershell
$env:BRAWLHALLA_DIR='F:/SteamLibrary/steamapps/common/Brawlhalla'
python -I tools/bht.py abc-extract
python -I -W error::ResourceWarning -m unittest discover -s tests -v
python -I -W error::ResourceWarning tools/bht.py prng-order-verify
python -I tools/bht.py prng-verify --draws 1000
python -I tools/bht.py movement-verify
python -I tools/bht.py abc-validate
git diff --check
```

- [V] Lead rerun after review fixes: **42 tests pass, zero skipped**; new CLI has no resource warning.
- [V] New verifier: **87 anchors, 10 reference sets, 9 slot types, zero mismatches**.
- [V] Existing PRNG verifier: **6 seeds × 1,000 draws plus helpers pass**; movement **31/31**;
  ABC **15,453 bodies decoded, zero errors, zero bad branches**. Diff whitespace check passes.
- [V] Replay integration test samples 20 supported local files. Full local corpus was not run.

## Open boundaries and next step

No simulator, positions, video, complete random draw schedule or running-game equivalence yet.
The verifier checks static bytecode evidence; reference sets do not resolve dynamic dispatch.
Other game-mode writers, scoreboard activation during playback, global-generator effects,
rollback snapshot byte order and runtime arithmetic remain unresolved.

**Next:** trace rules entries `_-99._-u1O` #7128 and `_-99._-m4d` #7130 to their draw sites (L3),
then scoreboard `_-y4L` screen-stack pushes (L2). Audit remaining `_-w35` writers before asserting
unconditional lesson exclusion (L1). Q2 KO/score-writer ordering and Q10's oracle remain open.

[Session relay and reproduction commands](notes/2026-10-29-claude-prng-order.md).
[PR #24](https://github.com/ArachnoMLK/My-biggest-work/pull/24) publishes this work through the existing
fork under the user's PR authorization. It awaits upstream review; no merge or release was performed.
