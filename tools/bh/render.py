"""Static SVG summary of a replay: the real map geometry and a per-player action timeline.

Everything drawn is read from the replay and the game data: no simulation, no position is guessed.
Player names are never drawn (privacy): players are shown as "P1", "P2"... with their legend.
"""
import re
from html import escape

# Input bit groups shown on the timeline (bit numbers from replay.INPUT_BITS)
ACTIONS = [
    ("Move", (2, 3), "#7aa2f7"),
    ("Jump", (4,), "#9ece6a"),
    ("Light", (7,), "#e0af68"),
    ("Heavy", (6,), "#f7768e"),
    ("Dodge", (8,), "#bb9af7"),
    ("Throw", (9,), "#7dcfff"),
]
BG, PANEL, GRID, TEXT, MUTED, KO = "#0f1117", "#171a23", "#2a2f3d", "#e6e6e6", "#8b93a7", "#ff5c5c"


def _num(attrs, key):
    m = re.search(rf'\b{key}="(-?[\d.]+)"', attrs)
    return float(m.group(1)) if m else None


def parse_level(xml):
    """Top-level geometry of a LevelDesc: camera bounds, collision segments, respawns, item spawns."""
    level = {"camera": None, "lines": [], "respawns": [], "items": []}
    m = re.search(r"<CameraBounds([^>]*)>", xml)
    if m:
        a = m.group(1)
        level["camera"] = (_num(a, "X"), _num(a, "Y"), _num(a, "W"), _num(a, "H"))
    for tag, a in re.findall(r"<(\w*Collision)\b([^>]*)/?>", xml):
        x1, x2 = _num(a, "X1"), _num(a, "X2")
        y1, y2 = _num(a, "Y1"), _num(a, "Y2")
        x, y = _num(a, "X"), _num(a, "Y")
        if x is not None:
            x1 = x2 = x
        if y is not None:
            y1 = y2 = y
        if None not in (x1, x2, y1, y2):
            level["lines"].append((tag, x1, y1, x2, y2))
    for a in re.findall(r"<Respawn\b([^>]*)/?>", xml):
        level["respawns"].append((_num(a, "X"), _num(a, "Y")))
    for a in re.findall(r"<ItemSpawn\b([^>]*)/?>", xml):
        level["items"].append((_num(a, "X"), _num(a, "Y"), _num(a, "W"), _num(a, "H")))
    return level


def presses(records, bits):
    """Timestamps (ms) where any of `bits` goes from released to pressed."""
    out, prev = [], 0
    mask = sum(1 << b for b in bits)
    for ts, flags in records:
        cur = flags & mask
        if cur & ~prev:
            out.append(ts)
        prev = cur
    return out


def render(rep, level, level_name, legends, width=1200):
    pad, map_h, lane_h = 24, 380, 22
    players = [e for e in rep["entities"]]
    tl_top = pad * 2 + map_h + 30
    height = tl_top + len(players) * (len(ACTIONS) * lane_h + 46) + 40
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
         f'font-family="Segoe UI, Helvetica, Arial, sans-serif">',
         f'<rect width="100%" height="100%" rx="14" fill="{BG}"/>']
    title = f"{escape(level_name)} · patch {rep['patch']} · {rep['length_ms'] / 1000:.0f} s · " \
            f"{len(rep['kos'])} KOs · {sum(len(v) for v in rep['inputs'].values())} input records"
    s.append(f'<text x="{pad}" y="{pad + 14}" fill="{TEXT}" font-size="18" font-weight="600">{title}</text>')

    # ---- map panel
    mx, my, mw, mh = pad, pad + 30, width - 2 * pad, map_h - 30
    s.append(f'<rect x="{mx}" y="{my}" width="{mw}" height="{mh}" rx="10" fill="{PANEL}"/>')
    # frame the stage (collisions, respawns, item spawns) with a margin; camera bounds are much larger
    xs = [v for t in level["lines"] for v in (t[1], t[3])] + [x for x, _ in level["respawns"]]
    ys = [v for t in level["lines"] for v in (t[2], t[4])] + [y for _, y in level["respawns"]]
    bx, by = min(xs), min(ys)
    bw, bh = max(xs) - bx or 1, max(ys) - by or 1
    cx, cy, cw, ch = bx - bw * 0.3, by - bh * 0.25, bw * 1.6, bh * 1.5
    k = min((mw - 40) / cw, (mh - 50) / ch)
    ox = mx + (mw - cw * k) / 2 - cx * k
    oy = my + (mh - 30 - ch * k) / 2 - cy * k

    def P(x, y):
        return f"{ox + x * k:.1f}", f"{oy + y * k:.1f}"

    for x, y, w, h in level["items"]:
        a, b = P(x, y)
        s.append(f'<rect x="{a}" y="{b}" width="{w * k:.1f}" height="{max(h * k, 2):.1f}" fill="#e0af68" opacity="0.35"/>')
    for tag, x1, y1, x2, y2 in level["lines"]:
        a, b = P(x1, y1)
        c, d = P(x2, y2)
        soft = "Soft" in tag
        style = 'stroke="#9ece6a" stroke-width="2" stroke-dasharray="8 5"' if soft else f'stroke="{TEXT}" stroke-width="3"'
        s.append(f'<line x1="{a}" y1="{b}" x2="{c}" y2="{d}" {style} stroke-linecap="round"/>')
    for x, y in level["respawns"]:
        a, b = P(x, y)
        s.append(f'<circle cx="{a}" cy="{b}" r="4" fill="#7aa2f7"/>')
    ly = my + mh - 14
    s.append(f'<text x="{mx + 14}" y="{ly}" fill="{MUTED}" font-size="12">'
             f'<tspan fill="{TEXT}">━</tspan> hard collision  <tspan fill="#9ece6a">┅</tspan> soft platform  '
             f'<tspan fill="#7aa2f7">●</tspan> respawn  <tspan fill="#e0af68">▬</tspan> item spawn   '
             f'(level geometry from LevelDesc; no player position is shown: they need the simulator)</text>')

    # ---- timeline
    tx, tw = pad + 90, width - 2 * pad - 100
    length = max(rep["length_ms"], 1)
    s.append(f'<text x="{pad}" y="{tl_top - 8}" fill="{TEXT}" font-size="15" font-weight="600">'
             f'Inputs over time (one tick per key press, 16 ms resolution)</text>')
    y = tl_top
    for i, e in enumerate(players):
        hero = e["heroes"][0]["hero_id"]
        s.append(f'<text x="{pad}" y="{y + 18}" fill="{TEXT}" font-size="14" font-weight="600">'
                 f'P{i + 1} · {escape(legends.get(hero, "#" + str(hero)))}</text>')
        y += 28
        recs = rep["inputs"].get(e["id"], [])
        for name, bits, color in ACTIONS:
            s.append(f'<text x="{pad}" y="{y + 15}" fill="{MUTED}" font-size="12">{name}</text>')
            s.append(f'<rect x="{tx}" y="{y + 3}" width="{tw}" height="{lane_h - 6}" rx="3" fill="{PANEL}"/>')
            for t in presses(recs, bits):
                xx = tx + tw * min(t, length) / length
                s.append(f'<rect x="{xx:.1f}" y="{y + 4}" width="1.4" height="{lane_h - 8}" fill="{color}"/>')
            y += lane_h
        for ent, t in rep["kos"]:
            if ent == e["id"]:
                xx = tx + tw * min(t, length) / length
                top = y - len(ACTIONS) * lane_h
                s.append(f'<line x1="{xx:.1f}" y1="{top}" x2="{xx:.1f}" y2="{y}" stroke="{KO}" stroke-width="2"/>')
                s.append(f'<text x="{xx + 3:.1f}" y="{top - 3}" fill="{KO}" font-size="11" font-weight="600">KO</text>')
        y += 18
    for sec in range(0, int(length / 1000) + 1, 30):
        xx = tx + tw * sec * 1000 / length
        s.append(f'<text x="{xx:.1f}" y="{y + 4}" fill="{MUTED}" font-size="11" text-anchor="middle">'
                 f'{sec // 60}:{sec % 60:02d}</text>')
    s.append("</svg>")
    return "\n".join(s)


def legend_names(herotypes_xml):
    names = {}
    for body in re.findall(r"<HeroType HeroName=\"[^\"]+\"[^>]*>(.*?)</HeroType>", herotypes_xml, re.S):
        hid = re.search(r"<HeroID>(\d+)</HeroID>", body)
        disp = re.search(r"<HeroDisplayName>([^<]*)</HeroDisplayName>", body)
        if hid and disp:
            names[int(hid.group(1))] = disp.group(1).title()
    return names


def read_text(path):
    raw = open(path, "rb").read()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252")

