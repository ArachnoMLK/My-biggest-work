### Relay — Claude Opus 5.5 (Claude Code) — 2026-10-28 — patch 11.00

**Task:** bootstrap (tools, ledger, briefing).

**Done:**
- [V] Toolkit `tools/bht.py`: swz (decrypt + key search), swf (tags, DoABC, symbols), abc (parser,
  disassembler, constant/member search), replay (full parser with inputs), corpus stats, inventory.
- [V] All 15,453 method bodies of the 11.00 ABC decode, 0 bad branch targets (`abc-validate`).
- [V] The `.swz` key is a uint constant of the ABC: `swz-key` finds `154281100` in 0.4 s.
- [V] 9,653 replays (formats 261–271) parse with 0 errors; all 42,636,188 input timestamps are
  multiples of 16 ms (`corpus`).
- [V] `"Error in reading replay"` is pushed by methods #3388, #8732, #12889, #12895.
- [V] Ledger of 7,781 files (`ledger/game-files.csv`, Adobe AIR runtime excluded).

**Evidence:** commands above, ABC SHA-256 `7d308423…6db9`.

**Dead ends:** none yet. Note: the toolkit's first bit reader used one big Python int and was
quadratic; replaced by byte slicing (whole corpus in ~110 s).

**Next:** Q1 — start from `abc-disasm --method 12889` and `--method 12895` (class `_-Y26`), list
the members they touch, and find the class that stores per-entity input lists.

**Questions for humans:** see the owner's access list in the first discussion.
