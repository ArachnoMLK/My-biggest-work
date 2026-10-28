### Relay — Claude Opus 5.5 (Claude Code, T3 worktree) — 2026-10-28 — patch 11.00

**Task:** integration groundwork: recover Q2 docs, fix the replay integration test, add
project context files. Draft only, not posted.

Pin: 11.00 / ABC SHA-256 `7d308423eaebcc82dfdda4ecc0e57d3abe78569534023aa7f9d776f626356db9`.

**Done:**
- [V] Brought the Codex Q2 docs ([tick-loop map](../docs/tick-loop-11.00.md), the
  [code-map](../docs/code-map-11.00.md) update, [Codex relay](2026-10-28-codex-q2.md)) from local
  commit `6d7c074` into this branch, without its `.gitignore` and `.sharelane/` changes.
- [V] Re-checked the key Q2 anchors in the pinned ABC (`abc-disasm --method 3336/3594/2990/3138/2984`):
  16 ms rounding, step count, `t += 16`, pass order, `_-vs + 450` gate, checkpoint anchor 5/300
  ticks, restart from `_-717`. All match the Codex relay. Added one clarification: table
  receivers are `_-h3U` properties (`_-3z`, `_-32h`, `_-s3D`); the cited methods are defined
  once each, on `_-E1V`, `_-26u`, `_-99` (`abc-disasm` header). [H] slot types not checked.
- [V] `test_some_replays_parse` failed on a local folder whose alphabetically last files are
  formats 257/258. The test now peeks the version (4 inflated bytes), parses up to 20
  supported-format files, skips with a message when there are none, and still fails when a
  supported file does not parse. 4 synthetic tests cover version peek, mixed and
  unsupported-only folders, and a broken supported file. No parser change; `PATCHES` unchanged.
- [V] Added [PROJECT.md](../PROJECT.md), [DECISIONS.md](../DECISIONS.md), [HANDOFF.md](../HANDOFF.md).

**Evidence:** `python -I tools/bht.py abc-validate` → 15,453 bodies, 0 errors, 0 bad branches.
`python -I -m unittest discover -s tests -v` → 12 tests OK, 0 skipped. Same suite with
`BRAWLHALLA_REPLAYS` pointing to synthetic folders: old formats only → `skipped 'no replay in
supported formats 261-271 …'`; one broken format-271 file → `EOFError`, test fails.

**Dead ends:** ShareLane MCP is not usable on this machine (missing `sharelane.mjs`), so no claim
was recorded there.

**Next:** open the Q2 PR the maintainer asked for, then trace `Entity._-x1M` #2977 /
`Entity._-eR` #3138 to the KO writer.

**Questions for humans:** approve publishing the Q2 docs and this relay (PR + relay post).
