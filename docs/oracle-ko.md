# KO oracle — Q10, part 1

Q10 asks for ground truth that does not require touching the game process. Each replay already
carries a partial one: the **KO faces** (object 5). The meaning of these records is proven statically
in [ko-11.00.md](ko-11.00.md), §6 (PR #25):
- a face is written for every KO event of type 1 (by an opponent), 2 (self) or 9 (team);
- it holds the **victim** entity and the **tick time of the phase 6 commit** of that KO, minus a
  mode-dependent base. [V] static.

So a simulator that replays the inputs must reproduce, for every victim, the tick of each ring-out.
That checks positions only at the moments that matter most (leaving the blast zone). It is
coarse but real ground truth, and it is available for every replay of the corpus.

## Use

```text
python -I tools/bht.py ko-oracle FILE.replay                      # list (tick, victim) of one replay
python -I tools/bht.py ko-oracle --dir "%USERPROFILE%\BrawlhallaReplays"   # aggregate counts only
```

In code: `bh.oracle.ko_ticks(parsed_replay)` gives `[(tick, victim)]`, oldest first.
`bh.oracle.compare(predicted, recorded)` lists the differences, empty when they match.

## Corpus check (local, aggregate only)

| | |
|---|---|
| Replays parsed | 9,683 (0 errors) |
| KO faces | 69,028 |
| Replays with a KO time that is not a multiple of 16 ms | **0** |

## Limits

- **Base.** In some modes the writer subtracts `_-N1k._-n4k − 16` (ko-11.00.md §6). `_-n4k` is the match
  start time: the clock of the first tick (`_-Px.StartTime`, set by the scheduler on its first tick). So
  the recorded time is then 16 × (ticks since the first tick + 1), and otherwise the absolute tick time.
  A simulator that counts ticks from the first one should compare against both readings until the
  modes are told apart [H: which header fields select the base is open]. The exact bit condition is in
  ko-11.00.md §6 (`ko.ko_time_base`).
- **Corpus check of the origin.** On the 756 patch 11.00 replays of the local corpus (format 271), every
  input timeline starts at **0 ms**, and the last KO falls before the last input record in all but 2
  files (median 1 s before). So KO faces and input records share one origin. [V] corpus statistics; [H]
  that this origin is the first tick, which would make `_-n4k − 16 = 0` and the two readings equal.
- **Coverage.** Only KOs. Score modes keep list 5 empty and use object 7 instead (replay-format.md).
  Positions between KOs are not checked.
- **Off-by-one risk.** The time is the tick of the phase 6 commit, which follows the phase 5 detection
  of the same tick (ko-11.00.md §5). A simulator must commit KOs on the same phase.
- Nothing here is published: the command reads the user's own local replays and prints to the
  terminal.
