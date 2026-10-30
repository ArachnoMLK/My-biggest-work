"""KO bounds data for the harness on patch 11.00: CameraBounds of a LevelDesc and kill values of its LevelType.

`ko.ko_mask` (PR #25) takes the camera rectangle (left, top, right, bottom) and the LevelType's LeftKill,
RightKill, TopKill, BottomKill (uint) and HardLeftKill, HardRightKill, SoftTopKill (Boolean). Here they are read
from the local swz dump (Init.swz/LevelTypes.xml, by LevelName; Dynamic.swz/LevelDesc_<name>.xml). Values are
read at run time and never stored. [H] A missing uint reads 0 and a missing Boolean false (AS3 slot defaults).
"""
import re
import xml.etree.ElementTree as ET

from . import ko
from .smoke import fall, map_grid, respawns

KILL_UINTS = ("LeftKill", "RightKill", "TopKill", "BottomKill")
KILL_BOOLS = ("HardLeftKill", "HardRightKill", "SoftTopKill")


def level_kills(level_types_xml):
    """{LevelName: kill dict} from LevelTypes.xml."""
    out = {}
    for t in ET.fromstring(level_types_xml):
        name = t.get("LevelName") or t.findtext("LevelName")
        if not name:
            continue
        k = {f: int(t.findtext(f) or 0) for f in KILL_UINTS}
        k.update({f: (t.findtext(f) or "").strip().lower() == "true" for f in KILL_BOOLS})
        out[name] = k
    return out


def camera_bounds(desc_xml):
    """(left, top, right, bottom) of the LevelDesc's CameraBounds (flash Rectangle getters: x, y, x + w, y + h)."""
    m = re.search(r"<CameraBounds\b([^>]*)/?>", desc_xml)
    if not m:
        return None
    v = {k: float(n) for k, n in re.findall(r'\b(X|Y|W|H)="([^"]+)"', m.group(1))}
    return v["X"], v["Y"], v["X"] + v["W"], v["Y"] + v["H"]


def fall_to_ko(grid, x, y, cam, kill, max_ticks=2000):
    """A fighter at rest falls (smoke.fall, one tick at a time) until `ko_mask` reports a kill line, testing
    after each move with exact = False (not in hitstun) and top_allowed = False (in the air, no wall).
    Returns (tick, mask) or (None, 0) when it lands first or never crosses a line."""
    from .air_move import air_move
    from .smoke import FALL_CAP, GRAVITY, STEP
    p5s = 0.0
    for tick in range(1, max_ticks + 1):
        if p5s < FALL_CAP:
            p5s += GRAVITY * STEP
        r = air_move(grid, 0, x, y, 0.0, p5s, False)
        x, y = r.x, r.y
        if r.ground is not None:
            return None, 0
        mask = ko.ko_mask(x, y, cam, kill, False, False)
        if mask:
            return tick, mask
    return None, 0


def run(desc_xmls, kills):
    """Aggregate counts over many LevelDescs: respawn points inside the bounds, and the falls that end in a KO."""
    c = {"maps": 0, "maps_with_bounds": 0, "respawns": 0, "respawns_inside": 0, "falls_without_ground": 0,
         "falls_to_bottom_ko": 0, "falls_to_other_ko": 0, "ko_ticks_max": 0}
    for name, xml in desc_xmls:
        c["maps"] += 1
        cam, kill = camera_bounds(xml), kills.get(name)
        if cam is None or kill is None:
            continue
        c["maps_with_bounds"] += 1
        grid = map_grid(xml)
        for x, y in respawns(xml):
            c["respawns"] += 1
            c["respawns_inside"] += ko.ko_mask(x, y, cam, kill, False, False) == 0
            if fall(grid, x, y)[1] is not None:
                continue
            c["falls_without_ground"] += 1
            tick, mask = fall_to_ko(grid, x, y, cam, kill)
            if tick is None:
                continue
            c["falls_to_bottom_ko" if mask == ko.BOTTOM else "falls_to_other_ko"] += 1
            c["ko_ticks_max"] = max(c["ko_ticks_max"], tick)
    return c
