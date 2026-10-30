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

from .air_move import LAVA, _back_off, air_move, gravity_applies, ground_reset, ground_walk
from .level_collision import Grid, compute_normals, static_lines
from . import items
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

def item_spawns(xml):
    """Centre of every `<ItemSpawn>` box and every `<ItemInitSpawn>` point of a LevelDesc."""
    out = []
    for tag, attrs in re.findall(r"<(ItemSpawn|ItemInitSpawn)\b([^>]*)/?>", xml):
        v = {k: float(n) for k, n in re.findall(r'\b(X|Y|W|H)="([^"]+)"', attrs)}
        if "X" in v and "Y" in v:
            out.append((v["X"] + v.get("W", 0.0) / 2, v["Y"] + v.get("H", 0.0) / 2))
    return out


def item_fall(grid, x, y, item, max_ticks=1000, stand_ticks=60):
    """An item at rest, not thrown (state 0), falls with `items.velocity`, `items.sweep` (mask hard | soft)
    and `items.after_sweep` (impact: bounce or stop) until it has stopped on a line, then rests `stand_ticks`
    more ticks. Returns a dict: contact tick, bounces, settle tick, error of the hit point on the line at
    the first contact, whether it stayed still, and whether it settled on a slope (where gravity keeps
    acting, so it never stops). A flat line whose normal y is not exactly -1 (Point.normalize rounding,
    e.g. width 1700) never lets the speed reach 0: the item micro-bounces, and `still` then tells whether it
    stays in place."""
    lu = vy = 0.0
    ground, state = None, 0
    out = {"contact": None, "bounces": 0, "settled": None, "err": None, "still": False, "slope": False}
    for tick in range(1, max_ticks + 1):
        lu, vy, mv = items.velocity(lu, vy, 0.0, 0.0, ground, item, thrown=False, o2o=False)
        x, y, ground, _ = items.sweep(grid, 0, x, y, mv, 3, item["S2O"])
        if ground is not None and out["contact"] is None:
            out["contact"] = tick
            b = items._back_off(ground, mv)
            out["err"] = 0.0 if ground.sx == ground.ex else (y + b[1]) - line_y(ground, x + b[0])
        lu, vy, state, kind = items.after_sweep(lu, vy, ground, item, state)
        out["bounces"] += kind == "bounce"
        if ground is not None and lu == 0 and vy == 0:
            out["settled"] = tick
            break
    else:
        out["slope"] = ground is not None and ground.sy != ground.ey
        if ground is None:
            return out
    y0, still = y, True
    for _ in range(stand_ticks):
        lu, vy, mv = items.velocity(lu, vy, 0.0, 0.0, ground, item, thrown=False, o2o=False)
        x, y, g2, _ = items.sweep(grid, 0, x, y, mv, 3, item["S2O"])
        ground = g2 if g2 is not None else ground
        lu, vy, state, _ = items.after_sweep(lu, vy, ground, item, state)
        still = still and abs(y - y0) <= 1e-6
    out["still"] = still
    return out


def run_items(level_xmls, item, max_ticks=1000):
    """Aggregate counts of `item_fall` over the static lines of many maps."""
    c = {"spawn_points": 0, "contact": 0, "on_line_1e-6": 0, "settled": 0, "still_60": 0, "bounces_max": 0,
         "not_settled_on_slope": 0, "not_settled_still_60": 0, "no_contact": 0, "no_contact_dynamic_map": 0, "settle_ticks_max": 0}
    for xml in level_xmls:
        grid = map_grid(xml)
        for x, y in item_spawns(xml):
            c["spawn_points"] += 1
            r = item_fall(grid, x, y, item, max_ticks)
            if r["contact"] is None:
                c["no_contact"] += 1
                c["no_contact_dynamic_map"] += bool(DYNAMIC.search(xml))
                continue
            c["contact"] += 1
            c["on_line_1e-6"] += abs(r["err"]) <= 1e-6
            c["bounces_max"] = max(c["bounces_max"], r["bounces"])
            if r["settled"] is None:
                c["not_settled_on_slope"] += r["slope"]
                c["not_settled_still_60"] += r["still"]
                continue
            c["settled"] += 1
            c["settle_ticks_max"] = max(c["settle_ticks_max"], r["settled"])
            c["still_60"] += r["still"]
    return c


def walk(grid, r, x_step, ticks=60, team=0):
    """After the contact `r`, `ticks` steps with a constant x step (a fighter walking at `_-v1D` = x_step /
    0.384): step-start landing, ground walk (`ground_walk`), gravity only off the ground, then the free move
    with the left-over x and the ground push. Returns (outcome, gap): outcome is "walked" (ground kept every
    tick), "wall" (a wall stopped it) or "left" (it lost the ground); gap is the largest change of the
    height above the ground line while on a flat line."""
    x, y, ground, p5s = r.x, r.y, r.ground, 0.0
    gap0, gap, wall = None, 0.0, False
    for _ in range(ticks):
        p5s, _ = ground_reset(ground, False, 0, False, p5s)
        w = ground_walk(grid, team, x, y, ground, x_step, 3)
        x, y, ground = w.x, w.y, w.ground
        wall = wall or w.stop_x
        if gravity_applies(False, ground, 0, 0, False, GRAVITY) and p5s < FALL_CAP:
            p5s += GRAVITY * STEP
        m = air_move(grid, team, x, y, w.left, p5s, ground is not None)
        x, y, ground = m.x, m.y, m.ground
        if ground is None:
            return "left", gap
        if ground.sy == ground.ey:
            g = y - ground.sy
            gap0 = g if gap0 is None else gap0
            gap = max(gap, abs(g - gap0))
    return ("wall" if wall else "walked"), gap


def run_walk(level_xmls, x_step=6.0, max_ticks=1000):
    """Aggregate counts of `walk` both ways from every respawn point that lands on a fixed, non-lava line."""
    c = {"walks": 0, "walked": 0, "wall": 0, "left": 0, "height_kept_1e-6": 0}
    for xml in level_xmls:
        grid = map_grid(xml)
        for x, y in respawns(xml):
            ticks, r = fall(grid, x, y, max_ticks)
            if r is None or r.ground.type & LAVA:
                continue
            for step in (x_step, -x_step):
                c["walks"] += 1
                outcome, gap = walk(grid, r, step)
                c[outcome] += 1
                c["height_kept_1e-6"] += gap <= 1e-6
    return c
