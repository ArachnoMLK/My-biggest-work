"""Tests of the KO-gap check (tools/bh/ko_gaps.py). Synthetic values only.
Run: python -I -m unittest discover -s tests"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh import ko_gaps  # noqa: E402

XML = ('<ScoringTypes><ScoringType ScoringName="A"><ScoringID>7</ScoringID></ScoringType>'
       '<ScoringType ScoringName="B"><ScoringID>8</ScoringID><FetchDuration>10</FetchDuration>'
       '<RespawnDuration>20</RespawnDuration><DropDuration>30</DropDuration>'
       '<RespawnTimesForRounds>true</RespawnTimesForRounds></ScoringType></ScoringTypes>')


def rep(sid, kos):
    return {"settings": {"scoring_type_id": sid}, "kos": kos}


class Gaps(unittest.TestCase):
    def test_cells(self):
        cells = ko_gaps.scoring_cells(XML)
        self.assertEqual(sorted(cells), [7, 8])
        self.assertEqual(cells[8]["DropDuration"], "30")

    def test_victim_gaps(self):
        self.assertEqual(sorted(ko_gaps.victim_gaps(rep(7, [(1, 0), (2, 160), (1, 6400), (1, 16000)]))),
                         [6400, 9600])

    def test_check(self):
        cells = ko_gaps.scoring_cells(XML)
        reps = [rep(7, [(1, 0), (1, 4688)]),            # 4688 < 4700: one below the default floor (after a KO,
                                                         # `_-44x` is clear: SPAWNED_IN_PLAY)
                rep(7, [(1, 0), (1, 6000)]),
                rep(8, [(1, 0), (1, 64)]),              # floor 60
                rep(9, [(1, 0), (1, 16)])]
        c = ko_gaps.check(reps, cells)
        self.assertEqual((c["replays"], c["gaps"], c["below_floor"], c["unknown_scoring_type"]), (4, 3, 1, 1))
        self.assertEqual((c["smallest_margin_ms"], c["scoring_types"]), (-12, 2))
        self.assertEqual((c["first_kos"], c["first_ko_below_floor"]), (3, 3))      # KOs at 0 ms: before 272 + drone


if __name__ == "__main__":
    unittest.main()
