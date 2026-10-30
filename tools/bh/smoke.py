"""First end-to-end smoke test on patch 11.00: one fighter, no input, falls from a respawn point onto the map.

It chains pieces from several PRs: the gravity step (movement-11.00.md, `_-P5S += 3.75 x 0.384` below the fall
cap 70), the free move against the map (air_move.py, PR #30), the LevelDesc lines, normals and grid
(level_collision.py) and the ray cast (raycast.py). The fighter starts at rest; the step order is the one of
entity-step-11.00.md (gravity, then the sweeps). Landing itself (@8869-) is not transcribed yet, so the test
stops at the first ground contact and checks the feet against the line: the feet plus the 1.01 back-off must
be on the line. Static evidence only; nothing here has been compared with the running game.
"""
import re

from .air_move import _back_off, air_move
from .level_collision import Grid, compute_normals, static_lines

GRAVITY = 3.75        # `Entity._-84Q` (Entity.<init> #2887 @133)
STEP = 0.384          # `_-z2k._-Vj`
FALL_CAP = 70.0       # `Entity._-8i` fall cap without the Drop bit (movement-11.00.md)
DYNAMIC = re.compile(r"<(DynamicCollision|MovingPlatform)\b")   # lines this static test leaves out


def respawns(xml):
    """(x, y) of every `<Respawn>` of a LevelDesc, in file order."""
    out = []
    for attrs in re.findall(r"<Respawn\b([^>]*)/?>", xml):
        x = re.search(r'\bX="([^"]+)"', attrs)
        y = re.search(r'\bY="([^"]+)"', attrs)
        if x and y:
            out.append((float(x.group(1)), float(y.group(1))))
    return out


def map_grid(xml):
    """Static lines with their normals, in a candidate grid (dynamic lines left out)."""
    lines = static_lines(xml)
    compute_normals(lines)
    return Grid(lines)


def line_y(line, x):
    """Height of a non-vertical line at x."""
    return line.sy + (line.ey - line.sy) * (x - line.sx) / (line.ex - line.sx)


def fall(grid, x, y, max_ticks=1000, team=0):
    """Ticks of gravity + free move from rest. Returns (ticks, MoveResult of the contact) or (max_ticks, None)."""
    p5s = 0.0
    for tick in range(1, max_ticks + 1):
        if p5s < FALL_CAP:
            p5s += GRAVITY * STEP
        r = air_move(grid, team, x, y, 0.0, p5s, False)
        x, y = r.x, r.y
        if r.ground is not None:
            return tick, r
    return max_ticks, None


def check_landing(r):
    """(kind, error): kind is "flat" / "slope" / "wall"; error = how far the hit point (feet + back-off) is
    from the line, in y. The back-off is `_back_off` of air_move.py: along the move, or along -normal for a
    tiny move against a hard line."""
    g = r.ground
    if g.sx == g.ex:
        return "wall", 0.0
    b = _back_off(g, r.move)
    hx, hy = r.x + b[0], r.y + b[1]
    kind = "flat" if g.sy == g.ey else "slope"
    return kind, hy - line_y(g, hx)


def run(level_xmls, max_ticks=1000):
    """Aggregate counts over many maps (no coordinates, no names)."""
    c = {"maps": 0, "respawns": 0, "contact": 0, "flat": 0, "slope": 0, "wall": 0, "no_contact": 0,
         "no_contact_dynamic_map": 0,
         "within_1e-6": 0, "max_abs_error": 0.0, "max_ticks": 0}
    for xml in level_xmls:
        c["maps"] += 1
        grid = map_grid(xml)
        for x, y in respawns(xml):
            c["respawns"] += 1
            ticks, r = fall(grid, x, y, max_ticks)
            if r is None:
                c["no_contact"] += 1
                c["no_contact_dynamic_map"] += bool(DYNAMIC.search(xml))
                continue
            c["contact"] += 1
            c["max_ticks"] = max(c["max_ticks"], ticks)
            kind, err = check_landing(r)
            c[kind] += 1
            c["max_abs_error"] = max(c["max_abs_error"], abs(err))
            if abs(err) <= 1e-6:
                c["within_1e-6"] += 1
    return c
