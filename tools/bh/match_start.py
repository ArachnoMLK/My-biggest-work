"""Match start on patch 11.00: where `_-X6R._-b3x` #6777 puts the fighters, and its replay-generator draws.

Correction to hit-detection-11.00.md §10 and prng-order-11.00.md §4b: on the match-start tick (local 2: first
tick with t >= `_-n4k` + 256, flag `_-C3h`) the fighters are not all passed to `Respawn`. [V] unless marked [H]:

- The loop runs over `_-N1k._-5r` in order (@224-604). A fighter is skipped when its `_-e3e` has one of the
  bits `Entity._-c3E | _-46p | _-y5N | _-J5I` or it has no drone `_-k5S`; on the match-start tick, when its
  state is not 2 (not spawned yet); on the `_-F3O` tick (local 3), when its state is 7 or 8.
- With `_-J1Y` (local 4) it gets state 3 and `_-44x` = true (@400-417). Every kept fighter goes through
  `_-U6W(t, f)` (@594-600, state 3).
- It joins the **start list** (local 6) when it has no `Entity._-o2q` bit, the game-mode test
  `_-H1g._-06A._-Z3E(f._-11)` is false and the mode gives no point (`_-H1g._-sZ._-N3(f, t)` == null);
  otherwise the **respawn list** (local 7), whose fighters go to `Respawn(t, f)` (@838-891).
- The start list (@617-834): one fighter -> `_-X5t(t, list)`; more -> sorted by `_-34Y` when
  `_-d3Y._-a4w()`, else **shuffled with R** (`_-A6B._-eV(list, R)`: one R draw per fighter); then two fighters
  outside team mode (`_-O3P()`) -> `_-Q2Q(t, list)`; else `_-z16` when `_-d3Y._-Z2Y & 1`, else `_-U24`.
- `_-Q2Q` #6782: candidates = `_-x22(t, 2, 1)` (respawn_points.candidates with n = 2 and the spawned flag); the
  first fighter of the list gets the first candidate, the second the last one; with fewer than 2 candidates,
  `_-I1f._-N4x()`. Each gets `f._-k5S._-P3o(t, point)` (the drone, spawn_bot.Drone.place).
- Then (@904-1002) the two `_-G5X` draws (entity_states.py).

So in a plain 1v1 the match start draws R four times: two for the shuffle, then two for `_-G5X`. [H] `_-a4w()`
(sort instead of shuffle), `_-X5t`, `_-z16` and `_-U24` are not read.
"""
from .movement import ABC_1100
from .prng import js_mod, shuffle, to_u32
from .respawn_points import candidates

G5X_DEFAULT_N = 37


def one_v_one(rng, fighters, points, sort_mode=False):
    """Plain 1v1 start (two fighters in the start list, no team mode). `fighters` in `_-5r` order; `points`
    from respawn_points.parse_respawns. Returns ([(fighter, point)], g5x) and advances `rng` (four draws, or
    two with `sort_mode`, where the `_-34Y` order is not transcribed and the list order is kept)."""
    order = list(fighters)
    if not sort_mode:
        shuffle(rng, order)
    cands = candidates(points, 2, True)
    m = len(cands)
    placed = []
    for i, f in enumerate(order):
        point = None if m < 2 else (cands[0] if i == 0 else cands[m - 1])   # None: `_-N4x()`
        placed.append((f, point))
    n = sum(1 for p in points if not p["expanded"]) or G5X_DEFAULT_N
    g5x = [to_u32(js_mod(rng.next_u32(), n)) for _ in range(2)]
    return placed, g5x


ANCHORS = {ABC_1100: {
    "_-X6R._-b3x loop: skip bits / no _-k5S; match start: state != 2 skipped; _-F3O tick: 7 / 8 skipped; _-J1Y: state 3, _-44x": [
        (6777, 80, "setlocal_2", ""),
        (6777, 116, "setlocal", "4"),
        (6777, 230, "getproperty", "_-5r"),
        (6777, 274, "getproperty", "_-c3E"),
        (6777, 281, "getproperty", "_-46p"),
        (6777, 289, "getproperty", "_-y5N"),
        (6777, 297, "getproperty", "_-J5I"),
        (6777, 313, "getproperty", "_-k5S"),
        (6777, 342, "pushbyte", "2"),
        (6777, 369, "pushbyte", "7"),
        (6777, 384, "pushbyte", "8"),
        (6777, 400, "getlocal", "4"),
        (6777, 411, "initproperty", "_-65w"),
        (6777, 417, "initproperty", "_-44x"),
    ],
    "_-X6R._-b3x split: no _-o2q, not _-Z3E, no _-sZ._-N3 point -> start list (local 6), else respawn list (local 7); _-U6W for both": [
        (6777, 463, "callproperty", "_-Z3E, 1"),
        (6777, 485, "getproperty", "_-o2q"),
        (6777, 525, "callproperty", "_-N3, 2"),
        (6777, 547, "callpropvoid", "http://adobe.com/AS3/2006/builtin::push, 1"),
        (6777, 589, "callpropvoid", "http://adobe.com/AS3/2006/builtin::push, 1"),
        (6777, 600, "callpropvoid", "_-U6W, 2"),
    ],
    "_-X6R._-b3x start list: 1 -> _-X5t; else sort _-34Y (_-a4w) or shuffle _-A6B._-eV(list, R); 2 and not _-O3P -> _-Q2Q; _-Z2Y & 1 -> _-z16; else _-U24; respawn list -> Respawn": [
        (6777, 653, "callpropvoid", "_-X5t, 2"),
        (6777, 681, "callproperty", "_-a4w, 0"),
        (6777, 696, "getproperty", "_-34Y"),
        (6777, 727, "getproperty", "_-22"),
        (6777, 730, "callpropvoid", "_-eV, 2"),
        (6777, 737, "pushbyte", "2"),
        (6777, 761, "callproperty", "_-O3P, 0"),
        (6777, 779, "callpropvoid", "_-Q2Q, 2"),
        (6777, 797, "getproperty", "_-Z2Y"),
        (6777, 819, "callpropvoid", "_-z16, 2"),
        (6777, 834, "callpropvoid", "_-U24, 2"),
        (6777, 886, "callpropvoid", "Respawn, 2"),
    ],
    "_-A6B._-eV shuffle: for i < n: j = R._-f4c() % n; swap list[i], list[j]": [
        (1068, 55, "callproperty", "_-f4c, 0"),
        (1068, 62, "modulo", ""),
        (1068, 77, "setproperty", "[rt]"),
        (1068, 85, "setproperty", "[rt]"),
    ],
    "_-X6R._-Q2Q: _-x22(t, 2, 1); < 2 candidates -> _-N4x(); first fighter -> cands[0], others -> cands[m - 1]; _-k5S._-P3o": [
        (6782, 24, "pushbyte", "2"),
        (6782, 26, "pushbyte", "1"),
        (6782, 29, "callproperty", "_-x22, 3"),
        (6782, 115, "pushbyte", "2"),
        (6782, 132, "callproperty", "_-N4x, 0"),
        (6782, 153, "pushbyte", "0"),
        (6782, 169, "pushbyte", "1"),
        (6782, 171, "subtract_i", ""),
        (6782, 187, "getproperty", "_-k5S"),
        (6782, 193, "callpropvoid", "_-P3o, 2"),
    ],
}}
