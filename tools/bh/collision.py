"""Collision type flags of level geometry (Q6), patch 11.00. See docs/collision-11.00.md.

FLAGS and TYPES are derived constants (not game content): the bit of each flag and the composition of each
XML collision element, as built by `_-y2E.init` #15351 and `_-i2H.static._-T5E` #858.
"""
from .movement import ABC_1100, check, listing  # noqa: F401  (re-exported for bht.py)

FLAGS = {"hard": 1, "soft": 2, "trigger": 4, "sticky": 8, "no_slide": 16, "item_ignore": 32, "bounce": 64,
         "game_mode": 128, "pressure_plate": 256, "lava": 512, "unused_1024": 1024}
TYPES = {"HardCollision": 1, "SoftCollision": 2, "TriggerCollision": 4, "StickyCollision": 9,
         "NoSlideCollision": 17, "ItemIgnoreCollision": 49, "BouncyHardCollision": 65, "BouncySoftCollision": 66,
         "GameModeHardCollision": 129, "PressurePlateCollision": 257, "SoftPressurePlateCollision": 258,
         "BouncyNoSlideCollision": 81, "LavaCollision": 657, "MudCollision": 128}

ANCHORS = {ABC_1100: [
    # _-CX._-X2e #1581 (13-parameter query) gathers candidates with _-CX._-936 #1582:
    # raster cells of 100, every bucket member in stored order, then every dynamic line _-82D
    (1581, 110, "callproperty", "_-936, 5"), (1581, 850, "callproperty", "_-PK, 7"),
    (1581, 956, "callproperty", "_-R5v, 9"),
    # filters: type & mask, owner, excluded mask; hard-before-soft floor exception (@296-480)
    (1581, 172, "bitand", ""), (1581, 236, "bitand", ""), (1581, 346, "pushbyte", "-1"), (1581, 361, "pushbyte", "1"),
    (1581, 381, "pushbyte", "2"), (1581, 435, "getproperty", "startY"), (1581, 440, "getproperty", "startY"),
    # accepted hit without a collection vector: the query end becomes the hit point (later equal hit wins)
    (1581, 972, "setlocal", "18"), (1581, 1061, "setlocal", "19"), (1581, 1075, "setlocal", "20"),
    (1581, 1099, "callproperty", "http://adobe.com/AS3/2006/builtin::indexOf, 1"),
    (1582, 64, "pushbyte", "100"), (1582, 66, "callproperty", "_-t2D, 7"), (1582, 131, "callproperty", "_-a2E, 2"),
    (1582, 143, "getproperty", "_-S4a"), (1582, 254, "getproperty", "_-82D"), (1582, 286, "getproperty", "_-82D"),
    (1582, 313, "returnvalue", ""),
    # _-i2H.static._-T5E: XML collision name -> base flag | statics
    (858, 7, 'pushbyte', '2'),
    (858, 10, 'pushstring', "'SoftCollision'"),
    (858, 24, 'pushbyte', '1'),
    (858, 27, 'pushstring', "'HardCollision'"),
    (858, 41, 'pushbyte', '4'),
    (858, 44, 'pushstring', "'TriggerCollision'"),
    (858, 58, 'pushbyte', '1'),
    (858, 64, 'getproperty', '_-h5W'),
    (858, 68, 'pushstring', "'StickyCollision'"),
    (858, 82, 'pushbyte', '1'),
    (858, 88, 'getproperty', '_-x1z'),
    (858, 92, 'pushstring', "'NoSlideCollision'"),
    (858, 106, 'pushbyte', '1'),
    (858, 112, 'getproperty', '_-M4J'),
    (858, 119, 'getproperty', '_-x1z'),
    (858, 123, 'pushstring', "'ItemIgnoreCollision'"),
    (858, 138, 'pushbyte', '1'),
    (858, 144, 'getproperty', '_-B6P'),
    (858, 149, 'pushstring', "'BouncyHardCollision'"),
    (858, 162, 'pushbyte', '2'),
    (858, 168, 'getproperty', '_-B6P'),
    (858, 173, 'pushstring', "'BouncySoftCollision'"),
    (858, 186, 'pushbyte', '1'),
    (858, 192, 'getproperty', '_-J6w'),
    (858, 197, 'pushstring', "'GameModeHardCollision'"),
    (858, 212, 'pushbyte', '1'),
    (858, 218, 'getproperty', '_-S1b'),
    (858, 223, 'pushstring', "'PressurePlateCollision'"),
    (858, 237, 'pushbyte', '2'),
    (858, 243, 'getproperty', '_-S1b'),
    (858, 248, 'pushstring', "'SoftPressurePlateCollision'"),
    (858, 261, 'pushbyte', '1'),
    (858, 267, 'getproperty', '_-x1z'),
    (858, 274, 'getproperty', '_-B6P'),
    (858, 279, 'pushstring', "'BouncyNoSlideCollision'"),
    (858, 294, 'pushbyte', '1'),
    (858, 300, 'getproperty', '_-s2O'),
    (858, 307, 'getproperty', '_-J6w'),
    (858, 315, 'getproperty', '_-x1z'),
    (858, 319, 'pushstring', "'LavaCollision'"),
    (858, 337, 'getproperty', '_-J6w'),
    (858, 341, 'pushstring', "'MudCollision'"),
    # _-y2E.init: _-z2k statics, sticky = 8 then 8 << 1 .. 8 << 7
    (15351, 13530, "pushbyte", "8"), (15351, 13533, "initproperty", "_-h5W"),
    (15351, 13542, "pushbyte", "1"), (15351, 13546, "initproperty", "_-x1z"),
    (15351, 13555, "pushbyte", "2"), (15351, 13559, "initproperty", "_-M4J"),
    (15351, 13568, "pushbyte", "3"), (15351, 13572, "initproperty", "_-B6P"),
    (15351, 13582, "pushbyte", "4"), (15351, 13586, "initproperty", "_-J6w"),
    (15351, 13596, "pushbyte", "5"), (15351, 13600, "initproperty", "_-S1b"),
    (15351, 13610, "pushbyte", "6"), (15351, 13614, "initproperty", "_-s2O"),
    (15351, 13623, "pushbyte", "7"), (15351, 13627, "initproperty", "_-76n"),
]}
