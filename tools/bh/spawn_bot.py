"""Respawn drone on patch 11.00: how a fighter goes from state 3 back to 0 (`SpawnBot`, `_-X6R`).

See docs/hit-detection-11.00.md, section 10. Static evidence only; every rule below is [V] unless marked [H].

Path [V call edges]: `_-X6R.Respawn(t, f, eliminated=false)` #6784 -> `_-U6W(t, f, eliminated)` #6787
(state 7 through `Entity._-Y6o` only when `eliminated`; otherwise 2 / 9 -> 3, and 3 again at the end unless
the state is 8) -> `_-K5c(t, f)` #6778 (point choice) -> `f._-k5S._-P3o(t, point)` #11873. The drone
(`SpawnBot`, the fighter's `_-k5S`; its fighter is `_-767`) then runs one phase per tick through `_-i1H`
#11858, a lookupswitch on its phase `_-T1X`:
  0 idle (`_-q15`), 1 come down (`_-82`), 2 carry the fighter to the point (`_-31s`), 3 drop (`_-m1O`), 4 `_-Ck`.
`_-Y6i(p)` #11859 sets the phase and clears the phase start `_-A6k` (and the drone's own targets).
While the phase is 2, `_-i1H` moves the fighter onto the drone after the phase handler (`_-x1M(_-J2c, _-b3h)`).

In a replay [V]: replay start `_-h3U._-T12` #3624 sets `_-w35` = 1024 (@116-123); `_-01I` #3336 turns it into
2048 only once the target time passes `_-331._-G5C` + 2500 (@4315-4370, the end of the replay [H]). Neither has
a bit of INSTANT_MASK, so the drone flies in from the camera edge, unless `DevSettings.IsStandaloneClient()`
#2563: dev flag 3 set and dev flag 27 clear. [H] The shipped client has dev flag 3 clear.

`_-44x` at the match start [V; H: the `_-vs` gate of the normal update holds]: tick phase 5 of `_-01I` #3336
calls `Entity._-k5H(t)` on every entity of `_-5r` (@2725-2759), and `_-k5H` #2991 sets `_-44x` = true in
state 2 (lookupswitch @89 -> @194-199) and in state 9 (@1665-1670). A player waits in state 2 from replay start,
so `_-44x` is set when the match start (phase 4 of the 272 ms step) calls `_-P3o`. `_-X6R._-J1Y` does not
matter here: it is set only by the BRAWLBALL and TAG rules (`_-C20._-S4o` from `_-f40`, `_-od._-b6O`; built
in `_-99._-76j`), a snapshot read `_-B5T`, and `_-X6R._-sW`, which nothing references. The same `_-k5H` ticks
the drone first (`_-k5S._-i1H(t)`, @45-66), so its first tick is in phase 5 of the match-start step.

`_-44x` after the match start [V; H: `_-99._-h2k` is a round reset that a plain stock game does not reach]: in
states 0 and 5 (lookupswitch -> @240) `_-k5H` clears `_-44x` whenever `_-P4K` is false (@495-511); states 3 / 4
(-> @207) set `_-P4K` false. `_-P4K` is set true only by `Entity._-s2U` #3038 (which also sets `_-44x`), called
only from `_-99._-h2k` #7148 @399, and by the BRAWLBALL / TAG / `_-y3M` rules. So on the first in-play tick
`_-44x` is cleared, and a respawn after a KO takes the not-spawned path: `_-P3o` leaves the fighter where it
is, the durations use flags 0 (4700 ms by default), and the drop gives state 5 and `_-P5S` = 70 outside team
types 1 / 2.

Eliminated (`Entity._-19` #3016, the third argument of `Respawn` in the KO commit): false with the `_-e3e`
bit `_-B6B`; true in state 7; true when the lives `_-V` are 0 and `_-d3Y._-81d` > 0 (@0-81); the cases after
@82 (`_-s3D._-F3O`) are not read.
"""
from .movement import ABC_1100
from .platforms import ease

IDLE, COME_DOWN, CARRY, DROP, PHASE_4 = 0, 1, 2, 3, 4

# `_-X6R._-nN(t, f)` #6791: the timing flags passed to the duration getters.
F_SPAWNED = 1      # `f._-44x`
F_MODE = 2         # `_-H1g._-06A._-Z3E(f._-11)` (a game-mode test on the fighter) [H: meaning]
F_TIMED = 4        # `_-H1g._-S3h` exists and its `_-w1s` >= t

INSTANT_MASK = 32768 | 16   # `_-N1k._-w35` bits that skip the drone outside a standalone client
REPLAY_W35 = 1024           # `_-w35` from replay start `_-T12`
SPAWNED_AT_MATCH_START = True   # `_-44x`, from `_-k5H` in state 2 on the steps before
SPAWNED_IN_PLAY = False         # `_-44x` once in state 0 / 5 (`_-P4K` false), so after a KO
REPLAY_END_W35 = 2048       # `_-w35` after the replay's end (`_-331._-G5C` + 2500)
DROP_SPEED = 30.0           # `_-P5S` (vertical speed, see movement.py) when the drone lets go
DROP_SPEED_FAST = 70.0      # in the other team-type case, with `_-F5c` set
SPAWNBOT_S1I = 1000         # `SpawnBot._-s1I`, set in script641.<init> #11876
DEFAULT_DROP_MS = 700       # the drop duration that scales the drop animation (700 / duration)


def timing_flags(spawned, mode_test, timed_until, t):
    """`_-X6R._-nN` #6791. `timed_until` is `_-S3h._-w1s`, or None when there is no `_-S3h`."""
    f = F_SPAWNED if spawned else 0
    if mode_test:
        f |= F_MODE
    if timed_until is not None and timed_until >= t:
        f |= F_TIMED
    return f


def _long_case(flags, mask, rules):
    """Shared test of `_-H6B` / `_-L26`: the match-start case, else the fighter flags against `_-K2V`."""
    if rules.get("timed_until") is not None and flags & F_TIMED \
            and rules["timed_until"] == rules["n4k"] + 6000:
        return True
    return bool(flags & mask) and not rules["K2V"]


def come_down_ms(flags, rules):
    """`_-X6R._-H6B` #6793: duration of phase 1. `rules` holds the scoring-type fields and match flags."""
    if rules["F3O"]:
        return SPAWNBOT_S1I          # static `SpawnBot._-s1I`
    if _long_case(flags, F_SPAWNED, rules):
        return 2000
    if rules["Ac"] and not flags & F_MODE:
        return 1500
    return rules["o2N"]


def carry_ms(flags, rules):
    """`_-X6R._-L26` #6792: duration of phase 2."""
    if rules["F3O"]:
        return 2000
    if _long_case(flags, F_SPAWNED | F_TIMED, rules):
        return 3000
    if rules["Ac"] and not flags & F_MODE:
        return 2500
    return rules["j57"]


def drop_ms(flags, rules):
    """`_-X6R._-d3X` #6794: duration of phase 3."""
    if rules["Ac"] and not flags & F_MODE:
        return DEFAULT_DROP_MS
    return rules["C18"]


# `ScoringType.static._-6P` #7475 column -> field, and the `ScoringType.<init>` #7470 defaults. `_-K2V` and
# `_-Ac` are Boolean slots that `<init>` leaves at false.
SCORING_COLUMNS = {"FetchDuration": "o2N", "RespawnDuration": "j57", "DropDuration": "C18",
                   "RespawnTimesForRounds": "K2V", "RespawnTimesOnlyForSpecialEntities": "Ac"}
SCORING_DEFAULTS = {"o2N": 1500, "j57": 2500, "C18": 700, "K2V": False, "Ac": False}


def scoring_rules(cells, f3o=False, timed_until=None, n4k=0):
    """`rules` for the duration getters from one ScoringType's cells ({column: text}); missing cells keep
    the defaults. Integers through `_-N2e._-vD`, booleans through `_-Qr` ("true" [H: the exact spelling
    rules of `_-Qr` are not read here])."""
    r = dict(SCORING_DEFAULTS)
    for col, field in SCORING_COLUMNS.items():
        v = cells.get(col)
        if v is None or v == "":
            continue
        r[field] = v.strip().lower() == "true" if field in ("K2V", "Ac") else int(v)
    r.update({"F3O": f3o, "timed_until": timed_until, "n4k": n4k})
    return r


def respawn_ms(flags, rules):
    """Phases 1 + 2 + 3 of the drone: the time from `Respawn` to the drop."""
    return come_down_ms(flags, rules) + carry_ms(flags, rules) + drop_ms(flags, rules)


def drop_anim_scale(duration):
    """`SpawnBot._-m1O` @55-106: the drop animation speed `_-H1j`."""
    return DEFAULT_DROP_MS / duration if duration != DEFAULT_DROP_MS else 1.0


class Drone:
    """The deterministic part of `SpawnBot`: phase, phase start and the eased positions.

    `fighter` is a dict with `x`, `y`, `state` (`_-65w`), `vy` (`_-P5S`), `spawned` (`_-44x`), and the
    `_-e3e` tests `held_bit` (`_-M14`), `free_bit` (`_-o24`). Rendering, sounds and display order are left out.
    """

    def __init__(self, fighter):
        self.fighter = fighter
        self.phase = IDLE
        self.start = 0          # `_-A6k`
        self.x = self.y = 0.0   # `_-J2c`, `_-b3h`
        self.from_x = self.from_y = 0.0   # `_-uj`, `_-P6P`
        self.to_x = self.to_y = 0.0       # `_-36A`, `_-35U`
        self.fast_drop = False  # `_-F5c` on the fighter

    def set_phase(self, p):
        """`_-Y6i`."""
        self.phase = p
        self.start = 0

    @staticmethod
    def standalone(dev_flags):
        """`DevSettings.IsStandaloneClient()` #2563 from the set of dev flags."""
        return 3 in dev_flags and 27 not in dev_flags

    @staticmethod
    def eliminated(lives, lives_mode, state=0, b6b=False):
        """`Entity._-19` #3016 @0-81 (`lives_mode` is `_-d3Y._-81d` > 0); the `_-F3O` cases are not read."""
        if b6b:
            return False
        if state == 7:
            return True
        return lives == 0 and lives_mode

    def place(self, t, point, standalone, w35, f3o, camera):
        """`SpawnBot._-P3o` #11873. `point` = (x, y); `camera` = (x, y, width) of `_-I1f._-8I`."""
        if point is None:
            return
        self.set_phase(COME_DOWN)
        self.to_x, self.to_y = point
        f = self.fighter
        if not (f["spawned"] and not f3o):
            return
        if standalone or w35 & INSTANT_MASK:
            f["state"] = 0
            f["x"], f["y"] = point
            self.set_phase(IDLE)
            return
        cx, cy, cw = camera
        f["x"] = cx + cw if self.to_x > cx + cw * 0.5 else cx   # `right` / `x` of the camera rectangle
        f["y"] = cy - 200

    def tick(self, t, flags, rules, team_type, f3o):
        """`SpawnBot._-i1H` #11858 for the phases that move the fighter (1-3)."""
        if self.phase == COME_DOWN:
            self._come_down(t, flags, rules, team_type, f3o)
        elif self.phase == CARRY:
            self._carry(t, flags, rules, team_type, f3o)
        elif self.phase == DROP:
            self._drop(t, flags, rules, team_type, f3o)
        if self.phase == CARRY:
            self.fighter["x"], self.fighter["y"] = self.x, self.y   # `_-x1M(_-J2c, _-b3h)`

    def _come_down(self, t, flags, rules, team_type, f3o):
        """`SpawnBot._-82` #11856: ease in (power 2) from the drone's position to the fighter's."""
        d = come_down_ms(flags, rules)
        if self.start != 0 and t > self.start + d:
            self.set_phase(CARRY)
            self.fighter["state"] = 3
            self._carry(t, flags, rules, team_type, f3o)
            return
        if self.start == 0:
            self.start = t
            self.from_x, self.from_y = self.x, self.y
        p = ease(True, False, 2, t - self.start, d)
        self.x = p * (self.fighter["x"] - self.from_x) + self.from_x
        self.y = p * (self.fighter["y"] - self.from_y) + self.from_y

    def _carry(self, t, flags, rules, team_type, f3o):
        """`SpawnBot._-31s` #11853: ease out to the respawn point, power 3, or 2 when `_plain_team_type` is false."""
        d = carry_ms(flags, rules)
        if self.start != 0 and t > self.start + d:
            self.x, self.y = self.to_x, self.to_y
            self.fighter["x"], self.fighter["y"] = self.x, self.y
            self.set_phase(DROP)
            self._drop(t, flags, rules, team_type, f3o)
            return
        if self.start == 0:
            self.from_x, self.from_y = self.fighter["x"], self.fighter["y"]
            self.start = t
        power = 3 if _plain_team_type(self.fighter, team_type) else 2
        p = ease(False, True, power, t - self.start, d)
        self.x = p * (self.to_x - self.from_x) + self.from_x
        self.y = p * (self.to_y - self.from_y) + self.from_y

    def _drop(self, t, flags, rules, team_type, f3o):
        """`SpawnBot._-m1O` #11857: hold the fighter (state 4), then let go after the drop duration."""
        d = drop_ms(flags, rules)
        f = self.fighter
        if self.start == 0:
            self.start = t
            f["state"] = 4
            return
        if self.start + d > t:
            return
        self.set_phase(IDLE)
        if _plain_team_type(f, team_type):
            f["vy"] = DROP_SPEED
        else:
            f["vy"] = DROP_SPEED_FAST
            self.fast_drop = True
        if not f.get("held_bit") and (f.get("free_bit") or (f["spawned"] and not f3o)):
            f["state"] = 0
        else:
            f["state"] = 5      # timed in-play state; `_-u55` set and `_-U5l()` called


def _plain_team_type(fighter, team_type):
    """The test at `_-31s` @143-214 and `_-m1O` @195-269: true when the fighter is spawned (`_-44x`), else
    when `_-d3Y._-K4x` is 1 or 2. It picks the carry easing power (3 / 2) and the drop speed (30 / 70)."""
    if fighter["spawned"]:
        return True
    return team_type in (1, 2)


ANCHORS = {ABC_1100: {
    "Respawn(t, f, eliminated=false) -> _-U6W -> state 3 -> _-K5c -> f._-k5S._-P3o (SpawnBot)": [
        (6784, 255, "callpropvoid", "_-U6W, 3"),
        (6784, 286, "callpropvoid", "_-K5c, 2"),
        (6787, 34, "callpropvoid", "_-Y6o, 1"),
        (6787, 70, "pushbyte", "3"),
        (6787, 487, "pushbyte", "3"),
        (6778, 21, "getproperty", "_-k5S"),
        (6778, 24, "coerce", "SpawnBot"),
    ],
    "SpawnBot._-P3o: phase 1, target point; instant state 0 when standalone or _-w35 & 0x8010; else off camera": [
        (11873, 43, "callpropvoid", "_-Y6i, 1"),
        (11873, 176, "callproperty", "IsStandaloneClient, 0"),
        (11873, 195, "pushint", "32768"),
        (11873, 198, "pushbyte", "16"),
        (11873, 230, "initproperty", "_-65w"),
        (11873, 351, "callpropvoid", "_-Y6i, 1"),
        (11873, 391, "pushdouble", "0.5"),
        (11873, 490, "pushint", "200"),
    ],
    "SpawnBot._-i1H: lookupswitch on _-T1X (q15, _-82, _-31s, _-m1O, Ck); carried fighter _-x1M in phase 2": [
        (11858, 197, "lookupswitch", "20, 24, 38, 50, 64, 76"),
        (11858, 226, "callpropvoid", "_-q15, 1"),
        (11858, 239, "callpropvoid", "_-82, 1"),
        (11858, 252, "callpropvoid", "_-31s, 1"),
        (11858, 265, "callpropvoid", "_-m1O, 1"),
        (11858, 328, "pushbyte", "2"),
        (11858, 377, "callpropvoid", "_-x1M, 2"),
    ],
    "SpawnBot._-82: ease in power 2 over _-H6B; then phase 2, state 3, _-31s": [
        (11856, 48, "callproperty", "_-H6B, 1"),
        (11856, 91, "pushbyte", "2"),
        (11856, 152, "pushbyte", "3"),
        (11856, 163, "callpropvoid", "_-31s, 1"),
        (11856, 263, "pushbyte", "2"),
        (11856, 275, "callproperty", "_-D2g, 5"),
    ],
    "SpawnBot._-31s: ease out power 3 / 2 over _-L26; on arrival _-x1M, phase 3, _-m1O": [
        (11853, 69, "callproperty", "_-L26, 1"),
        (11853, 427, "callpropvoid", "_-x1M, 2"),
        (11853, 435, "pushbyte", "3"),
        (11853, 446, "callpropvoid", "_-m1O, 1"),
        (11853, 898, "pushbyte", "3"),
        (11853, 907, "pushbyte", "2"),
        (11853, 930, "callproperty", "_-D2g, 5"),
    ],
    "SpawnBot._-m1O: state 4 on entry; after _-d3X: _-P5S 30 / 70, then state 0 or 5": [
        (11857, 48, "callproperty", "_-d3X, 1"),
        (11857, 56, "pushuint", "700"),
        (11857, 135, "pushbyte", "4"),
        (11857, 171, "lessequals", ""),
        (11857, 297, "pushdouble", "30.0"),
        (11857, 329, "pushdouble", "70.0"),
        (11857, 467, "pushbyte", "0"),
        (11857, 503, "pushbyte", "5"),
    ],
    "_-X6R timing getters: _-nN flags 1/2/4; _-H6B 2000/1500/_-o2N; _-L26 2000/3000/2500/_-j57; _-d3X 700/_-C18": [
        (6791, 24, "getproperty", "_-44x"),
        (6791, 128, "getproperty", "_-w1s"),
        (6793, 23, "getproperty", "_-s1I"),
        (11876, 96, "pushuint", "1000"),
        (11876, 99, "initproperty", "_-s1I"),
        (6793, 112, "pushuint", "6000"),
        (6793, 164, "pushuint", "2000"),
        (6793, 191, "pushuint", "1500"),
        (6793, 196, "getproperty", "_-o2N"),
        (6792, 20, "pushuint", "2000"),
        (6792, 165, "pushuint", "3000"),
        (6792, 192, "pushuint", "2500"),
        (6792, 197, "getproperty", "_-j57"),
        (6794, 37, "pushuint", "700"),
        (6794, 53, "getproperty", "_-C18"),
    ],
    "ScoringType columns: FetchDuration _-o2N 1500, RespawnDuration _-j57 2500, DropDuration _-C18 700; K2V / Ac": [
        (7475, 290, "pushstring", "'DropDuration'"),
        (7475, 312, "initproperty", "_-C18"),
        (7475, 321, "pushstring", "'FetchDuration'"),
        (7475, 342, "initproperty", "_-o2N"),
        (7475, 352, "pushstring", "'RespawnDuration'"),
        (7475, 373, "initproperty", "_-j57"),
        (7475, 1106, "pushstring", "'RespawnTimesForRounds'"),
        (7475, 1126, "initproperty", "_-K2V"),
        (7475, 1136, "pushstring", "'RespawnTimesOnlyForSpecialEntities'"),
        (7475, 1156, "initproperty", "_-Ac"),
        (7470, 24, "pushuint", "700"),
        (7470, 32, "pushuint", "2500"),
        (7470, 42, "pushuint", "1500"),
    ],
    "KO commit Entity._-eR calls _-W1R.Respawn(t, this, _-19()) in the same tick": [
        (3138, 1134, "getproperty", "_-W1R"),
        (3138, 1142, "callproperty", "_-19, 0"),
        (3138, 1147, "callpropvoid", "Respawn, 3"),
    ],
    "Replay drone: _-T12 sets _-w35 = 1024; _-01I sets 2048 past _-331._-G5C + 2500; IsStandaloneClient = dev flag 3 and not 27": [
        (3624, 119, "pushint", "1024"),
        (3624, 123, "initproperty", "_-w35"),
        (3336, 4350, "getproperty", "_-G5C"),
        (3336, 4354, "pushuint", "2500"),
        (3336, 4367, "pushint", "2048"),
        (3336, 4370, "initproperty", "_-w35"),
        (2563, 3, "pushbyte", "3"),
        (2563, 6, "callproperty", "ContainsDevFlag, 1"),
        (2563, 18, "pushbyte", "27"),
        (2563, 26, "not", ""),
        (2563, 32, "pushfalse", ""),
    ],
    "_-44x at the match start: phase 5 _-k5H on every _-5r entity; _-k5H ticks the drone first; state 2 / 9 -> _-44x = true; _-J1Y writers only BRAWLBALL / TAG rules": [
        (3336, 2736, "getproperty", "_-5r"),
        (3336, 2751, "callpropvoid", "_-k5H, 1"),
        (2991, 48, "getproperty", "_-k5S"),
        (2991, 66, "callpropvoid", "_-i1H, 1"),
        (2991, 75, "callpropvoid", "_-1L, 1"),
        (2991, 89, "lookupswitch", "35, 151, 35, 105, 118, 118, 151, 1204, 1352, 1352, 1576"),
        (2991, 198, "pushtrue", ""),
        (2991, 199, "initproperty", "_-44x"),
        (2991, 1669, "pushtrue", ""),
        (2991, 1670, "initproperty", "_-44x"),
        (7133, 104, "getproperty", "BRAWLBALL"),
        (7133, 125, "constructprop", "_-C20, 1"),
        (7133, 583, "getproperty", "TAG"),
        (7133, 604, "constructprop", "_-od, 1"),
        (6991, 161, "callpropvoid", "_-S4o, 3"),
        (6993, 458, "initproperty", "_-J1Y"),
        (7219, 208, "initproperty", "_-J1Y"),
        (6783, 6, "initproperty", "_-J1Y"),
        (6786, 41, "initproperty", "_-J1Y"),
        (6777, 168, "initproperty", "_-J1Y"),
    ],
    "_-44x in play: states 0 / 5 clear it unless _-P4K (_-k5H @495-511); 3 / 4 clear _-P4K; _-s2U sets both, only from _-99._-h2k; _-19 eliminated": [
        (2991, 498, "getproperty", "_-P4K"),
        (2991, 510, "pushfalse", ""),
        (2991, 511, "initproperty", "_-44x"),
        (2991, 232, "pushfalse", ""),
        (2991, 233, "initproperty", "_-P4K"),
        (3038, 49, "pushtrue", ""),
        (3038, 50, "initproperty", "_-44x"),
        (7148, 399, "callpropvoid", "_-s2U, 1"),
        (3016, 12, "getproperty", "_-B6B"),
        (3016, 32, "pushbyte", "7"),
        (3016, 47, "getproperty", "_-V"),
        (3016, 68, "getproperty", "_-81d"),
        (3016, 74, "greaterthan", ""),
    ],
}}
