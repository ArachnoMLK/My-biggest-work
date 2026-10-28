### Relay — GPT-6.1 Sol lead / Claude Opus 5.5 implementation — 2026-10-28 — patch 11.00

**Task:** Q3 plus recovery of existing Q2 documents and test/context groundwork.
Claim: https://github.com/ArachnoMLK/My-biggest-work/discussions/1#discussioncomment-19247299
Pin: 11.00 / ABC SHA-256 `7d308423eaebcc82dfdda4ecc0e57d3abe78569534023aa7f9d776f626356db9`.

**Done:**
- [V] Two Claude Opus 5.5 tasks implemented Q3 and context/test repair in separate T3 worktrees;
  Sol reviewed and combined them on local `integration/replay-foundations-2026-10-28`.
- [V] Both replay-seeded paths reach WELL512 `Random` (#1011 `_-24O`, #1013 `_-f4c`):
  #3348 seeds rules directly; ItemManager #4908 seeds, then consumes two draws. Original port,
  range/shuffle helpers and a bytecode verifier are in [Q3 evidence](../docs/prng-11.00.md).
- [V] Existing [Q2 scheduler notes](../docs/tick-loop-11.00.md) recovered from `6d7c074` and checked;
  they were not recreated. Broken replay-test sampling now selects supported formats explicitly
  and still rejects broken supported data. PROJECT, DECISIONS and HANDOFF persist session context.
- [V] Lead regression checks found/fixed noninteger snapshot state acceptance and a verifier that
  could skip missing helpers. Combined suite: 29 tests pass, zero skipped.
- [H] Receiver classifier totals are provisional; no exhaustive PRNG inventory or complete runtime
  consumer ordering is claimed. No simulator/runtime-equivalence result.

**Evidence:** command-scoped `BRAWLHALLA_DIR`, then `python -I tools/bht.py abc-extract`,
`python -I -W error::ResourceWarning -m unittest discover -s tests -v`,
`python -I tools/bht.py prng-verify --draws 1000` (6 seeds × 1,000 draws plus helpers),
`python -I tools/bht.py abc-validate` (15,453 bodies, zero errors/bad branches), `git diff --check`.

**Dead ends:** ShareLane is unavailable (configured executable missing). Original dirty main
was preserved; no pull, reset or stash. No push/PR was performed under this session's authorization.
The verifier uses modeled AVM2 semantics, not a running-game oracle; full corpus was not run.

**Next:** map Q3 rules/items draws into Q2 tick order, especially `_-9D._-Y15` and
`MessageTrigger.Tick` during replay playback. Ring-out/score order and Q2 publication remain pending.

**Questions for humans:** publication requires explicit authorization; local work is reviewable
on the integration branch. No game content, extracted bytecode or replays were committed.

**Publication follow-up:** the user subsequently authorized publication. [PR #14](https://github.com/ArachnoMLK/My-biggest-work/pull/14)
publishes this integration from `unfortunatelyalex/My-biggest-work`; no merge was performed.
