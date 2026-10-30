"""Ground and dash jumps on patch 11.00: the grounded branch of `Entity.Jump` #3052.

See docs/movement-11.00.md (PR #16), which first read these values, and docs/hit-detection-11.00.md §7.4.
`_-i4Z._-51o` #6313 calls `owner.Jump(t)` on a fresh press of input bit 16 (input-buffer-11.00.md, PR #28,
for the 192 ms lock and the air-jump count). [V] unless marked [H]. The air jumps (@1545-) are not here.
"""
from .movement import ABC_1100

GROUND_IMPULSE = 57.0      # @643
GROUND_K = 0.86            # @579: when Jump's second argument is true (`Entity._-A2X` #3131)
DASH_IMPULSE = 170.0       # @698
DASH_WINDOW_MS = 160       # @84: `_-26T` + 160 > t


def dash_window(t, dash_timer, ground, xb):
    """@75-127 (local 5): `_-26T` + 160 > t and (a ground line `_-96f` or `_-Xb` == 1)."""
    return dash_timer + DASH_WINDOW_MS > t and (ground is not None or xb == 1)


def ground_jump(t, dash_timer, ground, xb, a4a, second_arg=False):
    """@574-1048: the grounded branch, taken when `_-96f` is set or `_-Xb` == 1. Returns (a4a, p5s, ground,
    dash) after the jump, or None when the branch is not taken (the air jumps of @1545-, not transcribed).

    The impulse is 57 x k (k = 0.86 with the second argument, else 1), or 170 in the dash window. `_-P5S` is
    set to 0, `_-96f` to null, and `_-A4A` -= impulse; `step.fold_impulse` (PR #26) then folds `_-A4A` into
    `_-P5S`. [H] The dash branch also clamps `_-v1D` (@704-) and fires 'dash.Jump'; not modelled here.
    """
    if ground is None and xb != 1:
        return None
    k = GROUND_K if second_arg else 1.0
    impulse = GROUND_IMPULSE * k
    dash = dash_window(t, dash_timer, ground, xb)
    if dash:
        impulse = DASH_IMPULSE
    return a4a - impulse, 0.0, None, dash


ANCHORS = {ABC_1100: {
    "Entity.Jump grounded branch: dash window _-26T + 160 > t and (_-96f or _-Xb == 1); 57 x (0.86 | 1) or 170; _-P5S = 0, _-96f = null, _-A4A -= impulse": [
        (3052, 80, "getproperty", "_-26T"),
        (3052, 84, "pushuint", "160"),
        (3052, 99, "getproperty", "_-96f"),
        (3052, 116, "getproperty", "_-Xb"),
        (3052, 579, "pushdouble", "0.86"),
        (3052, 586, "pushdouble", "1.0"),
        (3052, 596, "getproperty", "_-96f"),
        (3052, 622, "iffalse", "919"),
        (3052, 643, "pushdouble", "57.0"),
        (3052, 653, "iffalse", "228"),
        (3052, 698, "pushdouble", "170.0"),
        (3052, 989, "pushbyte", "0"),
        (3052, 991, "callpropvoid", "_-N5C::_-E1t, 2"),
        (3052, 1003, "initproperty", "_-96f"),
        (3052, 1020, "getproperty", "_-A4A"),
        (3052, 1031, "subtract", ""),
        (3052, 1048, "callpropvoid", "_-N5C::_-E1t, 2"),
    ],
}}
