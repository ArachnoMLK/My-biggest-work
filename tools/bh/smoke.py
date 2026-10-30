"""First end-to-end smoke test on patch 11.00: one fighter, no input, falls from a respawn point onto the map.

It chains pieces from several PRs: the gravity step (movement-11.00.md, `_-P5S += 3.75 x 0.384` below the fall
cap 70), the free move against the map (air_move.py, PR #30), the LevelDesc lines, normals and grid
(level_collision.py) and the ray cast (raycast.py). The fighter starts at rest; the step order is the one of
entity-step-11.00.md (gravity, then the sweeps). At the first ground contact it checks the feet
against the line (the feet plus the 1.01 back-off must be on the line), then runs 60 more ticks standing:
the step-start landing (`_-P5S` = 0) and no gravity on a ground line (air_move.py `ground_reset`,
`gravity_applies`). Static evidence only; nothing here has been compared with the running game.
"""
import re

from .air_move import LAVA, _back_off, air_move, gravity_applies, ground_reset
from .level_collision import Grid, compute_normals, static_lines
from .platforms import bind, carry, carry_offset, dynamic_lines, move, parse_platforms

GRAVITY = 3.75        # `Entity._-84Q` (Entity.<init> #2887 @133)
STEP = 0.384          # `_-z2k._-Vj`
FALL_CAP = 70.0       # `Entity._-8i` fall cap without the Drop bit (movement-11.00.md)
TICK_MS = 16
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


def map_grid(xml, with_platforms=False):
    """Static lines with their normals in a candidate grid. With `with_platforms`, the DynamicCollision lines
    are added as the grid's dynamic list (`_-82D`, tested on every query) and the result is (grid, movers):
    each mover is (Platform, its lines bound to the platform's first point), moved before the fighter each
    tick (section 9 of hit-detection-11.00.md: platforms move first)."""
    lines = static_lines(xml)
    if not with_platforms:
        compute_normals(lines)
        return Grid(lines)
    dyn = dynamic_lines(xml)
    every = [ln for group in dyn.values() for ln in group]
    compute_normals(lines, every)
    movers = []
    for plat in parse_platforms(xml):
        group = dyn.get(plat.plat_id)
        if group:
            bind(group, plat.points[0])
            movers.append((plat, group))
    return Grid(lines, every), movers


def line_y(line, x):
    """Height of a non-vertical line at x."""
    return line.sy + (line.ey - line.sy) * (x - line.sx) / (line.ex - line.sx)


def fall(grid, x, y, max_ticks=1000, team=0, movers=(), t0=0):
    """Ticks of gravity + free move from rest. Returns (ticks, MoveResult of the contact) or (max_ticks, None).

    `movers` (from `map_grid(..., True)`) are placed at their position for t = t0 + 16 x tick before the
    fighter moves. [H] t0 = 0 with the match start at 0: the phase of the platforms at a real respawn
    depends on the match clock, which this test does not model."""
    p5s = 0.0
    for tick in range(1, max_ticks + 1):
        for plat, lines in movers:
            move(lines, plat.at(t0 + TICK_MS * tick))
        if p5s < FALL_CAP:
            p5s += GRAVITY * STEP
        r = air_move(grid, team, x, y, 0.0, p5s, False)
        x, y = r.x, r.y
        if r.ground is not None:
            return tick, r
    return max_ticks, None


def stand(grid, r, start_tick, ticks=60, team=0, movers=(), t0=0):
    """After the contact `r`, more ticks with no input: the step start lands on `_-96f` (`ground_reset`:
    `_-P5S` = 0), gravity is skipped while a ground line is set (`gravity_applies`), and the move is the 2.02
    ground push. Before that, the fighter is carried by its ground line when it moved (platforms.py `carry`).
    Returns (ticks with a ground line, largest |y - contact y|, largest change of the height above the
    ground line)."""
    x, y0, ground, p5s = r.x, r.y, r.ground, 0.0
    y, kept, drift, rel, off = y0, 0, 0.0, None, 0.0
    for tick in range(start_tick + 1, start_tick + ticks + 1):
        for plat, lines in movers:
            move(lines, plat.at(t0 + TICK_MS * tick))
        if movers:                          # `_-d4u`: carried by the ground line kept in `_-u3j`
            x, y = carry(lambda cx, cy, dx, dy: grid.candidates(cx, cy, cx + dx, cy + dy), team, x, y,
                         carry_offset([ground]), ground)
        p5s, on_ground = ground_reset(ground, False, 0, False, p5s)
        if gravity_applies(False, ground, 0, t0 + TICK_MS * tick, False, GRAVITY) and p5s < FALL_CAP:
            p5s += GRAVITY * STEP
        m = air_move(grid, team, x, y, 0.0, p5s, ground is not None)
        x, y, ground = m.x, m.y, m.ground
        kept += ground is not None
        drift = max(drift, abs(y - y0))
        if ground is not None and ground.sx != ground.ex:
            gap = y - line_y(ground, x)
            rel = gap if rel is None else rel
            off = max(off, abs(gap - rel))
    return kept, drift, off


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


def run(level_xmls, max_ticks=1000, with_platforms=False):
    """Aggregate counts over many maps (no coordinates, no names)."""
    c = {"maps": 0, "respawns": 0, "contact": 0, "flat": 0, "slope": 0, "wall": 0, "no_contact": 0,
         "no_contact_dynamic_map": 0,
         "within_1e-6": 0, "max_abs_error": 0.0, "max_ticks": 0,
         "lava_hit": 0, "stand_60_on_ground": 0, "stand_static_flat": 0, "stand_static_flat_still": 0,
         "stand_static_slope": 0, "stand_static_slope_still": 0, "stand_moving": 0, "stand_moving_same_height": 0}
    for xml in level_xmls:
        c["maps"] += 1
        for x, y in respawns(xml):
            c["respawns"] += 1
            if with_platforms:              # fresh lines per fall: the movers keep their last position
                grid, movers = map_grid(xml, True)
            else:
                grid, movers = map_grid(xml), ()
            ticks, r = fall(grid, x, y, max_ticks, movers=movers)
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
            if r.ground.type & LAVA:        # `_-ao`: the line's power hits the fighter (lava_contact)
                c["lava_hit"] += 1
                continue
            on_static = r.ground not in grid.dynamic
            kept, drift, off = stand(grid, r, ticks, movers=movers)
            c["stand_60_on_ground"] += kept == 60
            if not on_static:
                c["stand_moving"] += 1
                c["stand_moving_same_height"] += off <= 1e-6
            if on_static:
                c[f"stand_static_{kind}"] += 1
                c[f"stand_static_{kind}_still"] += drift <= 1e-6
    return c
