"""Pinned bytecode anchors for the input command table (input bit names, see docs/input-commands-11.00.md).

Same format and checker as movement.py: (method id, offset, opname, operand text as printed by `abc-disasm`),
valid only for the ABC whose SHA-256 is the key of ANCHORS.
"""
from .movement import ABC_1100, check, listing  # noqa: F401  (re-exported for bht.py)

ANCHORS = {ABC_1100: [
    # _-y2E.init: IntMap hotkey -> input bit value, stored in Commands._-F6a
    (15351, 23502, "pushbyte", "4"), (15351, 23505, "pushbyte", "1"),      # JumpAimUp -> 1 (Up)
    (15351, 23517, "pushbyte", "5"), (15351, 23520, "pushbyte", "2"),      # Drop -> 2
    (15351, 23532, "pushbyte", "1"), (15351, 23535, "pushbyte", "4"),      # MoveLeft -> 4
    (15351, 23547, "pushbyte", "2"), (15351, 23550, "pushbyte", "8"),      # MoveRight -> 8
    (15351, 23562, "pushbyte", "6"), (15351, 23565, "pushint", "128"),     # QuickAttack -> 128
    (15351, 23577, "pushbyte", "9"), (15351, 23580, "pushbyte", "64"),     # HeavyAttack -> 64
    (15351, 23592, "pushbyte", "7"), (15351, 23595, "pushint", "256"),     # DodgeDash -> 256
    (15351, 23638, "pushbyte", "3"), (15351, 23641, "pushbyte", "16"),     # Jump -> 16
    (15351, 23653, "pushbyte", "8"), (15351, 23656, "pushint", "512"),     # ThrowItem -> 512
    (15351, 23669, "pushbyte", "29"), (15351, 23672, "pushbyte", "32"),    # AimUp -> 32
    (15351, 23909, "initproperty", "_-F6a"),
    # _-y2E.init: hotkey ids and their label keys, two parallel vectors (same index)
    (15351, 64372, "pushbyte", "1"), (15351, 64375, "pushbyte", "2"), (15351, 64378, "pushbyte", "4"),
    (15351, 64381, "pushbyte", "29"), (15351, 64384, "pushbyte", "3"),
    (15351, 64454, "pushstring", "'Command_Name_MoveLeft'"),
    (15351, 64457, "pushstring", "'Command_Name_MoveRight'"),
    (15351, 64461, "pushstring", "'Command_Name_JumpAimUp'"),
    (15351, 64465, "pushstring", "'Command_Name_AimUp'"),
    (15351, 64468, "pushstring", "'Command_Name_Jump'"),
]}
