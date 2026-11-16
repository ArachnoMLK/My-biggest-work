"""Animation frame table of a power on patch 11.00: `_-l4X._-54L` #86 builds `_-cA`, ticks since cast -> frame.

See docs/hit-detection-11.00.md, section 1.3. `_-54L` runs once, from the start set-up `_-f14` #59. Each update,
`_-o4b` #45 reads `_-cA[tick - _-k4b]` and, when it is > 0, stores it in `_-c2l`, the animation frame that
selects the target's hurtbox row (section 4). `_-cA` is a sparse Array: a tick only has an entry where the
integer frame changes, so `_-c2l` holds its value between entries. Static evidence only; [V] unless marked [H].

Inputs come from the power's PowerType (`_-V6B`), its CastAnim descriptor (`_-94J`) and the fighter's `.anm`
animation (`_-y1v`, PR #19):
- key frames `_-942` (`PowerType._-g1x` #6462, read by `_-y2b` #6470 / `_-P5A` #6471), from the CastTime
  markers "D@F", "D:R@F" and "D:R@F-G" (`PowerType.static._-A3R` #6483 @11337-11696);
- CastTime `_-a2`, its total `_-wj`, RecoverTime `_-Sp`, FixedRecoverTime `_-f5c`, the power's RecoverMod
  `_-01d` and its gate `_-s5C`;
- CastAnim "FLAGS:Name": the flag "L" (`_-6b`) makes the cast part loop between the animation's `_-T6` and
  `_-W1n` (the 2nd and 3rd header u32 of the .anm animation; PR #19 names them loop_start / recovery_start [H],
  this use shows the 3rd is where the loop wraps).
"""
import math

from .movement import ABC_1100

FRAMES_PER_TICK = 0.384     # `_-z2k._-Vj` (script61.<init> #1227): 24 frames per second over a 16 ms tick
KEY_FLAG = 0xF0000000       # "-G" end key: `_-P5A` adds 0.99, so the frame holds to its end
SNAP = 1e-05                # a frame within 1e-5 below an integer is snapped up to it


def key_entry(step, frame, end=False):
    """`PowerType._-g1x` #6462: one `_-942` entry, or None when step < 0 or frame <= 0 (the entry is skipped)."""
    if step is None or frame is None or step < 0 or frame <= 0:
        return None
    e = (frame << 16 | step) & 0xFFFFFFFF
    return e | KEY_FLAG if end else e


def key_step(entry):
    """`PowerType._-y2b` #6470."""
    return entry & 0xFFFF


def key_frame(entry):
    """`PowerType._-P5A` #6471: bits 16-27, plus 0.99 for an end key."""
    f = float((entry & 0x0FFF0000) >> 16)
    return f + 0.99 if entry & KEY_FLAG else f


def cast_keys(cell, parse_int):
    """`_-942` from a CastTime cell, in parse order (#6483 @11337-11696). `parse_int` is power_data.parse_int.

    For an entry whose first step has index s (the length of `_-a2` before it is pushed):
    "D@F" -> (s, F); "D:R@F" -> (s, F); "D:R@F-G" -> (s, F) then (s + R, G, end key).
    """
    from .power_data import cast_steps
    a2, entries = cast_steps(cell)
    out = []
    for raw, (s, _) in zip(cell.split(",") if cell else ["0"], entries):
        parts = raw.split(":")
        found = []
        if len(parts) > 1:
            at = parts[1].split("@")
            r = parse_int(at[0])
            if len(at) > 1:
                fg = at[1].split("-")
                found.append(key_entry(s, parse_int(fg[0])))
                if len(fg) > 1:
                    found.append(key_entry((r or 0) + s, parse_int(fg[1]), True))
        else:
            at = parts[0].split("@")
            if len(at) > 1:
                found.append(key_entry(s, parse_int(at[1])))
        out.extend(e for e in found if e is not None)
    return out


def frame_table(start_frame, current_frame, keep_anim, keys, a2, wj, recover_time, recover_mod, recover_gate,
                fixed_recover, end_ticks, loop=None):
    """`_-l4X._-54L` #86 -> {tick since cast: frame} (the sparse `_-cA`).

    start_frame   `_-D6j` (0 = not set yet)          current_frame  `_-c2l` when `_-54L` runs
    keep_anim     `_-V6B._-W28` or no CastAnim name   keys           `_-942` entries, or None
    a2 / wj       CastTime and its total             recover_*      `_-Sp`, `_-01d`, `_-s5C`
    fixed_recover `_-f5c`                            end_ticks      `_-E5S - _-k4b` (PR #26)
    loop          (`_-T6`, `_-W1n`) when CastAnim has the "L" flag and the animation is found, else None
    """
    first = 0                                   # local1: first CastTime step of the next key
    if start_frame == 0:                        # @102-151
        start_frame = current_frame + FRAMES_PER_TICK + 1 if keep_anim else 1.0
    prev_key = start_frame                      # local3
    last_tick = 0                               # local14
    loop_start, loop_end = loop if loop else (0, 0)
    table = {0: math.floor(start_frame - 1)}    # @220-256
    frame = math.nan                            # local7
    if keys is not None:                        # @386-1156
        n = len(keys)
        for i in range(n):
            step, key = key_step(keys[i]), key_frame(keys[i])
            ticks = 0                           # local22
            fractional = key != math.floor(key)
            k = first
            while k < step + 1:                 # ticks of the CastTime steps up to the key's step
                if k >= len(a2):                # past the cast: the recovery
                    rec = math.floor(recover_time * recover_mod) if recover_gate else int(recover_time)
                    ticks += rec + fixed_recover
                    break
                d = a2[k] or 0          # a null parseInt pushed into the Vector.<uint> reads 0
                ticks += 1 if d <= 1 and (step != 0 or i != 0) else d
                k += 1
            if step == 0 and i == 0 and keep_anim:
                ticks += 1
            if step == 0 and i == 0 and ticks == 0 and key != 0:
                table[0] = key - 1
            prev = prev_key - 1                 # local6
            rate = (key - prev_key) / ticks if ticks != 0 else 1.0   # local8
            tick = last_tick                    # local9
            stop = tick + ticks                 # local10
            if not keep_anim or i != 0:
                tick += 1
            if i == 0 and keep_anim and stop != 0:
                stop -= 1
            while tick <= stop:                 # @978-1088
                frame = prev + rate
                if math.ceil(frame) - frame < SNAP:
                    frame = float(math.ceil(frame))
                if math.floor(frame) != math.floor(prev):
                    table[tick] = math.floor(frame)
                prev = frame
                tick += 1
            last_tick = tick - 1
            if fractional and i + 1 == n:
                table[stop] = frame
            first = step + 1
            prev_key = key
    else:                                       # @1160-1176
        tick = last_tick
        if not keep_anim:
            tick += 1
    rate = FRAMES_PER_TICK                      # @1178-1430: after the last key, 24 frames per second
    prev = prev_key - 1
    recover_from = wj + fixed_recover
    while tick < end_ticks:
        if recover_gate and recover_time != 0 and tick > recover_from:
            rate = FRAMES_PER_TICK / recover_mod
        frame = prev + rate
        if loop_end != 0 and frame > loop_end and tick <= wj:
            frame = float(loop_start)
        if math.floor(frame) != math.floor(prev):
            table[tick] = math.floor(frame)
        prev = frame
        tick += 1
    return table


def frame_at(table, ticks_since_cast, held):
    """`_-l4X._-o4b` #45 @123-171: the new `_-c2l` (the `held` value unless the entry exists and is > 0)."""
    v = table.get(ticks_since_cast)
    return v if v is not None and v > 0 else held


ANCHORS = {ABC_1100: {
    "_-54L: _-D6j start (keep anim: _-c2l + _-Vj + 1, else 1); _-cA[0] = floor(_-D6j - 1); loop from _-y1v _-T6 / _-W1n under _-6b": [
        (86, 75, "getproperty", "_-W28"),
        (86, 89, "getproperty", "_-HT"),
        (86, 128, "getproperty", "_-c2l"),
        (86, 134, "getproperty", "_-Vj"),
        (86, 225, "initproperty", "_-cA"),
        (86, 251, "callproperty", "floor, 1"),
        (86, 289, "getproperty", "_-6b"),
        (86, 331, "callproperty", "_-Y3, 1"),
        (86, 358, "getproperty", "_-T6"),
        (86, 366, "getproperty", "_-W1n"),
    ],
    "_-54L key loop: ticks over _-a2 up to the key step (<= 1 counts 1), recovery _-Sp (x _-01d under _-s5C) + _-f5c": [
        (86, 394, "getproperty", "_-942"),
        (86, 414, "getproperty", "_-a2"),
        (86, 475, "callproperty", "_-y2b, 1"),
        (86, 494, "callproperty", "_-P5A, 1"),
        (86, 574, "getproperty", "_-s5C"),
        (86, 593, "getproperty", "_-Sp"),
        (86, 600, "getproperty", "_-01d"),
        (86, 641, "getproperty", "_-f5c"),
        (86, 665, "lessequals", ""),
    ],
    "_-54L ramp: linear frames from key to key, snap 1e-05, entries where floor changes; end key keeps the fraction": [
        (86, 823, "setproperty", "[rt]"),
        (86, 851, "divide", ""),
        (86, 885, "divide", ""),
        (86, 994, "callproperty", "ceil, 1"),
        (86, 1002, "pushdouble", "1e-05"),
        (86, 1068, "setproperty", "[rt]"),
        (86, 1132, "setproperty", "[rt]"),
    ],
    "_-54L tail: _-Vj per tick up to _-E5S - _-k4b; / _-01d after _-wj + _-f5c; loop back to _-T6 past _-W1n while <= _-wj": [
        (86, 1181, "getproperty", "_-Vj"),
        (86, 1203, "getproperty", "_-wj"),
        (86, 1290, "divide", ""),
        (86, 1320, "greaterthan", ""),
        (86, 1340, "lessequals", ""),
        (86, 1396, "setproperty", "[rt]"),
        (86, 1416, "getproperty", "_-E5S"),
        (86, 1423, "getproperty", "_-k4b"),
    ],
    "_-g1x / _-y2b / _-P5A: entry = frame << 16 | step, end key | 0xF0000000 -> frame + 0.99": [
        (6462, 54, "pushbyte", "16"),
        (6462, 71, "pushuint", "4026531840"),
        (6470, 20, "pushuint", "65535"),
        (6471, 20, "pushuint", "268369920"),
        (6471, 67, "pushdouble", "0.99"),
    ],
    "CastTime markers: D:R@F-G -> _-g1x(s, F), _-g1x(s + R, G, true); D@F -> _-g1x(s, F)": [
        (6483, 11418, "pushstring", "'@'"),
        (6483, 11483, "pushstring", "'-'"),
        (6483, 11533, "callpropvoid", "_-g1x, 2"),
        (6483, 11589, "callpropvoid", "_-g1x, 3"),
        (6483, 11696, "callpropvoid", "_-g1x, 2"),
    ],
    "CastAnim 'FLAGS:Name': L -> _-6b; name -> _-HT; _-Vj = 0.384; _-54L from _-f14; _-o4b reads _-cA into _-c2l": [
        (6483, 1815, "pushstring", "'CastAnim'"),
        (6483, 1882, "pushstring", "'L'"),
        (6483, 1898, "initproperty", "_-6b"),
        (6483, 1985, "initproperty", "_-HT"),
        (1227, 256, "pushdouble", "0.384"),
        (1227, 259, "initproperty", "_-Vj"),
        (59, 599, "callpropvoid", "_-54L, 0"),
        (45, 152, "ifngt", "18"),
        (45, 171, "initproperty", "_-c2l"),
    ],
}}
