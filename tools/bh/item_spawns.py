"""Item spawns on patch 11.00: the ItemManager `_-E1V` and its generator I (`_-E1V._-22`).

Static reading of the bytecode (abc 7d308423...). [V] unless marked [H]; anchors in ANCHORS.

**Data.** `ItemSpawnRateTypes.xml` rows become `_-T4A` (`_-T4A.static._-W68` #4949): ExtraTimeBeforeMax `_-n1a`,
FixedTimeBetweenSpawns `_-T2X`, InitSpawnDelay `_-41r`, MaxItemCountFixed `_-93K`, MaxItemCountMultiplier `_-dD`,
RandomTimeBetweenSpawns `_-j5F`, RoundUpMaxItemMultiplier `_-rL`, SpawnAllZonesFirstDrop `_-M2s`,
SpawnAllZonesSimultaneously `_-k4w`, SpawnRateID `_-f41`, VariableTimeBetweenSpawns `_-E3k`; a row with
InheritSpawnRate copies its parent's values first (`_-T4A.<init>` #4944). The row named "Disabled" (id 0) is
`_-T4A._-02s` (#4948). `ItemSpawnRuleSetTypes.xml` rows become `_-w2j` (`_-w2j.static._-mD` #4958): WeaponList,
GadgetList (comma lists), RuleSetID, Use1v1AndTeamInitialWeaponSpawns `_-63N`.

**Match settings.** The settings reader `_-I3W._-G5` #3875 reads 15 u32 in this order: `_-Z2Y` (flags), `_-Q4J`,
`mDuration`, `_-r5t`, `_-81d`, (scoring type), `_-o3c`, `_-Z1I`, `_-04o`, `_-f3V`, `_-46U` (item spawn rule set id),
`_-O2B` (weapon spawn rate id), `_-O4I` (gadget spawn rate id), `_-i48` (custom gadget selection), `_-K4x`
(variation): the replay header's settings in replay.py order. `_-I3W._-F24` #3901 / `_-m2K` #3903 give the rate
by id, or Disabled when `_-52d()` is false (#3896: variation 3, or a scoring type with `_-L5u`).

**Seeding** (`_-E1V._-13p` #4908, from `_-h3U._-Y3u` with the replay seed, like R): I is seeded, draw 0 -> `_-Y1h`
(weapon lane), draw 1 -> `_-5J` (gadget lane), then `_-A1o` (#4907): rule set `_-r3G`, weapon rate `_-T6S` and
gadget rate `_-k5F` (None when Disabled), weapons `_-62P` = WeaponList without TestFeature types (unless flag
64), gadgets `_-Y6M` = GadgetList without the types whose index bit is set in `_-i48`; the four lane values reset
to 0. `_-SH` (#4899, from `<init>`) sets the spawn cursor `_-S3D` to 0xFFFFFFFF, so the first random spawn
shuffles the spawn list.

**Level lists** (`_-a2j._-q1q` #5231 from `_-139._-W5J` #5294): `ItemSpawn` -> `_-X69`, `ItemInitSpawn` -> `_-i4e`,
`TeamItemInitSpawn` -> `_-03f`, `ItemSet` -> `_-v3h`; rectangles X / Y / W / H (`_-139._-G2x` #5289) with
defaults H 10 (`_-k1`), 40 x 40 (`_-X3M`, ItemSet), 50 x 50 (`_-15j`, init spawns) (#15351).

**Each tick** (phase 4, `_-E1V._-O3d` #4879): `_-y4V` (spawn timers), `_-I4n` under flag 64, then the weapon lane
`_-96d` #4876, then the gadget lane `_-u43` #4880, then the item updates `_-418`. I is drawn only by `_-13p`,
`_-96d`, `_-u43`, `_-p1K`, `_-K5X` and the shuffle `_-e4H` (abc-reach from #4879, receiver `_-22`).
"""
import re
import xml.etree.ElementTree as ET

from .movement import ABC_1100
from .prng import js_mod, shuffle, to_u32

MAX = 1.79769313486231e+308          # "no position": pick a random ItemSpawn
CURSOR_RESET = 0xFFFFFFFF            # `_-SH` @103-109
FLAG_PAIR_SPAWNS = 1                 # `_-Z2Y & 1` in `_-s3q`
FLAG_TEST = 64                       # `_-Z2Y & 64`
MAX_ITEMS_CAP = 100                  # `_-Z2q`
DEFAULT_RECTS = {"ItemSpawn": (MAX, MAX, MAX, 10), "ItemSet": (MAX, MAX, 40, 40),
                 "ItemInitSpawn": (MAX, MAX, 50, 50), "TeamItemInitSpawn": (MAX, MAX, 50, 50)}
LIST_OF_TAG = {"ItemSpawn": "X69", "ItemInitSpawn": "i4e", "TeamItemInitSpawn": "03f", "ItemSet": "v3h"}

RATE_COLUMNS = {"ExtraTimeBeforeMax": "n1a", "FixedTimeBetweenSpawns": "T2X", "InitSpawnDelay": "41r",
                "MaxItemCountFixed": "93K", "MaxItemCountMultiplier": "dD", "RandomTimeBetweenSpawns": "j5F",
                "RoundUpMaxItemMultiplier": "rL", "SpawnAllZonesFirstDrop": "M2s",
                "SpawnAllZonesSimultaneously": "k4w", "SpawnRateID": "f41", "VariableTimeBetweenSpawns": "E3k"}
RATE_DEFAULTS = {"n1a": 0, "T2X": 0, "41r": 0, "93K": 0, "dD": 0.0, "j5F": 0, "rL": False, "M2s": False,
                 "k4w": False, "f41": 0, "E3k": 0}


def _value(field, text):
    if field in ("rL", "M2s", "k4w"):
        return text.strip().lower() == "true"
    if field == "dD":
        return float(text)
    return int(text)


def parse_rates(xml_text):
    """ItemSpawnRateTypes.xml -> {name: rate dict}; InheritSpawnRate copies the parent first (#4944, [H] the
    parent must come earlier in the file)."""
    out = {}
    for row in ET.fromstring(xml_text):
        name = row.get("SpawnRateName")
        parent = row.get("InheritSpawnRate") or ""
        r = dict(out[parent]) if parent in out else dict(RATE_DEFAULTS)
        r["name"] = name
        for cell in row:
            f = RATE_COLUMNS.get(cell.tag)
            if f is not None and cell.text is not None:
                r[f] = _value(f, cell.text)
        out[name] = r
    return out


def parse_rule_sets(xml_text):
    """ItemSpawnRuleSetTypes.xml -> {RuleSetID: {name, weapons, gadgets, weapon_rates, gadget_rates, init_63N}}."""
    out = {}
    for row in ET.fromstring(xml_text):
        r = {"name": row.get("RuleSetName"), "weapons": [], "gadgets": [], "weapon_rates": [],
             "gadget_rates": [], "init_63N": False, "id": 0}
        for cell in row:
            t = cell.text or ""
            if cell.tag == "WeaponList":
                r["weapons"] = t.split(",")
            elif cell.tag == "GadgetList":
                r["gadgets"] = t.split(",")
            elif cell.tag == "WeaponSpawnRateTypes":
                r["weapon_rates"] = t.split(",")
            elif cell.tag == "GadgetSpawnRateTypes":
                r["gadget_rates"] = t.split(",")
            elif cell.tag == "RuleSetID":
                r["id"] = int(t)
            elif cell.tag == "Use1v1AndTeamInitialWeaponSpawns":
                r["init_63N"] = t.strip().lower() == "true"
        if r["name"] != "Template":
            out[r["id"]] = r
    return out


def parse_level_spawns(level_xml_text, off_x=0.0, off_y=0.0):
    """LevelDesc -> {"X69": [...], "i4e": [...], "03f": [...], "v3h": [...]} of rects {x, y, w, h} in file order.
    Regex reading like level_collision (some LevelDescs are not well-formed XML). [H] the tags inside a
    `DynamicItemSpawn` (spawns on a moving platform, `_-a2j._-u50`) are left out."""
    xml = re.sub(r"<DynamicItemSpawn\b.*?</DynamicItemSpawn>", "", level_xml_text, flags=re.S)
    lists = {k: [] for k in LIST_OF_TAG.values()}
    for tag, attrs in re.findall(r"<(ItemSpawn|ItemInitSpawn|TeamItemInitSpawn|ItemSet)\b([^>]*)>", xml):
        dx, dy, dw, dh = DEFAULT_RECTS[tag]

        def g(k, d):
            m = re.search(r'\b' + k + r'="([^"]*)"', attrs)
            return float(m.group(1)) if m else d
        lists[LIST_OF_TAG[tag]].append({"x": g("X", dx) + off_x, "y": g("Y", dy) + off_y,
                                        "w": g("W", dw), "h": g("H", dh), "j2X": 0})
    return lists


def max_items(rate, players):
    """`_-T4A.static._-Z2q` #4952: None -> 0; fixed 0 and multiplier 0 -> 100; else
    min(100, ceil-or-floor(players x multiplier) + fixed). `players` = `_-s3D._-8W()` ([H] the player count)."""
    if rate is None:
        return 0
    if rate["93K"] == 0 and rate["dD"] == 0.0:
        return MAX_ITEMS_CAP
    v = players * rate["dD"]
    n = to_u32(int(-(-v // 1)) if rate["rL"] else int(v // 1))
    n = to_u32(n + rate["93K"])
    return n if n <= MAX_ITEMS_CAP else MAX_ITEMS_CAP


def lane_due(t, count, rate, base, rand, max_count):
    """`_-E1V._-b2A` #4874: is the next spawn of a lane due? count = items of the lane on the map / held.
    interval = Fixed (+ ExtraTimeBeforeMax when count + 1 == max) + floor((count + 1) x Variable / max)
    + (rand % (2 Random + 1)) - Random, all in uint arithmetic; due when base + interval < t."""
    fixed = rate["T2X"]
    if to_u32(count + 1) == max_count:
        fixed = to_u32(fixed + rate["n1a"])
    step = int((to_u32(count + 1) * (rate["E3k"] / max_count)) // 1)
    a = to_u32(fixed + step)
    j = rate["j5F"]
    m = js_mod(rand, to_u32(to_u32(j + j) + 1))
    interval = to_u32(to_u32(a + int(m)) - j)
    return to_u32(base + interval) < t


def gate(t, rate, rule_set_present, n4k, w35=0, ce=0, q2c=False):
    """`_-E1V._-n3V` #4921: may the lane spawn at t? Not without a rate or a rule set, not with `_-w35` bit
    0x1000000 (or bit 32 with `_-ce` bit 0x1000000), not with `_-Q2c`, not before the time base `_-n4k` is set,
    not before `_-n4k` + InitSpawnDelay."""
    if rate is None or not rule_set_present:
        return False
    if w35 & 0x1000000 or (w35 & 32 and ce & 0x1000000):
        return False
    if q2c or n4k == 0:
        return False
    return not to_u32(n4k + rate["41r"]) > t


def spawn_pos(spawn, r):
    """`_-p1K` #4888 @371-436: one I draw r places the item in the rect: y from the high 16 bits, x from the low."""
    y = spawn["y"] + (r >> 16) / 65535.0 * spawn["h"]
    x = spawn["x"] + (r & 65535) / 65535.0 * spawn["w"]
    return x, y


def shuffle_spawns(rng, spawns, sides):
    """`_-E1V._-e4H` #4892: shuffle `_-X69` with I (`_-A6B._-eV`), then with `sides` move the leftmost rect
    (smallest x, first on ties) to 0 and the rightmost (largest x + w, first on ties) to 1."""
    shuffle(rng, spawns)
    if not sides:
        return spawns
    lo = hi = 0
    for i in range(1, len(spawns)):
        if spawns[i]["x"] < spawns[lo]["x"]:
            lo = i
        if spawns[i]["x"] + spawns[i]["w"] > spawns[hi]["x"] + spawns[hi]["w"]:
            hi = i
    if lo != 0:
        spawns[0], spawns[lo] = spawns[lo], spawns[0]
        if hi == 0:
            hi = lo
    if hi != 1:
        spawns[1], spawns[hi] = spawns[hi], spawns[1]
    return spawns


class Counts:
    """`_-v57` used as a counter (`_-R2V`): ids `_-x3r`, values `_-E5Y`."""

    def __init__(self):
        self.ids, self.vals = [], []

    def get(self, k):                           # `_-168` #101
        return self.vals[self.ids.index(k)] if k in self.ids else 0

    def set(self, k, v, overwrite=True):        # `Set` #95
        if k in self.ids:
            if overwrite:
                self.vals[self.ids.index(k)] = v
        else:
            self.ids.append(k)
            self.vals.append(v)

    def bump(self, k):                          # `_-a4o` #100
        if k in self.ids:
            self.vals[self.ids.index(k)] += 1
        else:
            self.ids.append(k)
            self.vals.append(1)


def pick_type(rng, types, counts, live_ids, sudden_death=False):
    """`_-E1V._-K5X` #4911: weighted pick that favours the types picked least. `types` = [{"id", "B24"}...]
    (ItemID, RemoveDuringSuddenDeath), `live_ids` = ItemIDs of the live items not `_-a3s()`. One I draw when
    there are two types or more, none for one. Returns the type or None."""
    if not types:
        return None
    if len(types) == 1:
        it = types[0]
        counts.set(it["id"], 1, False)
    else:
        total = 0
        for it in types:
            c = counts.get(it["id"])
            if c == 0:
                c = 1
                counts.set(it["id"], c)
            total += c
        live = {}
        avg = to_u32(int(-(-total // len(types))))       # ceil(total / n)
        for k in live_ids:
            live[k] = to_u32(live.get(k, 0) + avg) if live.get(k, 0) else avg
            total += avg
        r = int(js_mod(rng.next_u32(), total * (len(types) - 1)))
        it = None
        for cand in types:
            it = cand
            r -= total - to_u32(counts.get(cand["id"]) + live.get(cand["id"], 0))
            if r < 0:
                break
    if sudden_death and it.get("B24"):
        return None
    counts.bump(it["id"])
    return it


class Lane:
    def __init__(self, weapons):
        self.weapons = weapons          # True: `_-96d` (T6S, O5i, Y1h, K4U); False: `_-u43` (k5F, z4Q, 5J, c44)
        self.rate = None
        self.types = None
        self.base = 0
        self.rand = 0
        self.max = 0


class ItemManager:
    """`_-E1V` as far as spawning goes. `spawn` callbacks receive (t, type, x, y)."""

    def __init__(self, rng, level, players):
        self.rng = rng
        self.level = level              # parse_level_spawns() lists
        self.players = players
        self.a, self.b = Lane(True), Lane(False)
        self.rule_set = None
        self.cursor = CURSOR_RESET      # `_-S3D`
        self.counts = Counts()          # `_-R2V`
        self.spawned = []

    def seed_lanes(self, rule_set, weapon_rate, gadget_rate, weapons, gadgets, flags=0, gadget_mask=0):
        """`_-13p` after the seeding: the two lane draws, then `_-A1o`."""
        self.a.rand = self.rng.next_u32()
        self.b.rand = self.rng.next_u32()
        self.rule_set = rule_set
        self.a.rate = None if weapon_rate is None or weapon_rate.get("f41") == 0 else weapon_rate
        self.b.rate = None if gadget_rate is None or gadget_rate.get("f41") == 0 else gadget_rate
        self.a.types = [w for w in weapons if not (w.get("F4E") and not flags & FLAG_TEST)] or None
        self.b.types = [g for i, g in enumerate(gadgets)
                        if not (g.get("F4E") and not flags & FLAG_TEST) and not gadget_mask & (1 << i)] or None
        for lane in (self.a, self.b):
            lane.base = lane.max = 0
        self.flags = flags

    def place(self, t, it, x=MAX, y=MAX):
        """`_-p1K` #4888: the next free rect of `_-X69` (shuffled when the cursor runs past the end), then one I
        draw for the position. [H] `_-T1v` is always true (static spawns; it tests only spawns on platforms)."""
        if x == MAX or y == MAX:
            spawns = self.level["X69"]
            n = len(spawns)
            if n == 0:
                return None
            tries = 0
            while True:
                if self.cursor >= n:
                    self.shuffle(False)
                sp = spawns[self.cursor]
                self.cursor += 1
                tries += 1
                blocked = bool(sp.get("j2X")) and bool(it.get("E2E")) if self.flags & FLAG_TEST else False
                if not blocked or tries >= n:
                    break
            if self.flags & FLAG_TEST and self.cursor >= n:
                return None
            x, y = spawn_pos(sp, self.rng.next_u32())
        item = {"t": t, "type": it, "x": x, "y": y}
        self.spawned.append(item)
        return item

    def shuffle(self, sides):
        self.cursor = 0
        shuffle_spawns(self.rng, self.level["X69"], sides)

    def spawn_random(self, t, types, x=MAX, y=MAX, live_ids=(), sudden_death=False):
        """`_-e3K` #4920: `_-K5X` then `_-p1K`."""
        it = pick_type(self.rng, types, self.counts, list(live_ids), sudden_death)
        return None if it is None else self.place(t, it, x, y)

    def spawn_all(self, t, spawns, weapons, live_ids=()):
        """`_-127` #4886: one `_-e3K` at the centre of each rect."""
        types = self.a.types if weapons else self.b.types
        for sp in spawns:
            self.spawn_random(t, types, sp["x"] + sp["w"] * 0.5, sp["y"] + sp["h"] * 0.5, live_ids)

    def first_spawn(self, t, live_ids=()):
        """`_-s3q` #4922 (weapon lane only)."""
        if not self.rule_set["init_63N"]:
            return False
        if self.players == 2 and self.level["i4e"]:
            self.spawn_all(t, self.level["i4e"], True, live_ids)
            return True
        if self.flags & FLAG_PAIR_SPAWNS:
            if len(self.level["03f"]) > 1:
                self.spawn_all(t, self.level["03f"], True, live_ids)
            else:
                self.shuffle(True)
                self.spawn_random(t, self.a.types, live_ids=live_ids)
                self.spawn_random(t, self.a.types, live_ids=live_ids)
            return True
        return False

    def lane_tick(self, lane, t, n4k, on_map, live_ids=(), **gate_kw):
        """`_-96d` / `_-u43`: `on_map` = held + live items of the lane (weapons: `_-93n._-G3X`; gadgets: not
        G3X and not `_-a3s()`)."""
        if lane.rate is None or not lane.types or not gate(t, lane.rate, self.rule_set is not None, n4k, **gate_kw):
            return
        if lane.base != 0:
            if lane.max == 0:
                lane.max = max_items(lane.rate, self.players)
            if on_map >= lane.max:
                lane.base = t
                return
            if not lane_due(t, on_map, lane.rate, lane.base, lane.rand, lane.max):
                return
        elif lane.weapons and self.first_spawn(t, live_ids):
            lane.base = t
            return
        if lane.rate["k4w"] or (lane.rate["M2s"] and lane.base == 0):
            self.spawn_all(t, self.level["X69"], lane.weapons, live_ids)
        else:
            self.spawn_random(t, lane.types, live_ids=live_ids)
        lane.rand = self.rng.next_u32()
        lane.base = t

    def tick(self, t, n4k, weapons_on_map, gadgets_on_map, live_ids=(), **gate_kw):
        """Phase 4 spawning part of `_-O3d`: weapon lane, then gadget lane."""
        self.lane_tick(self.a, t, n4k, weapons_on_map, live_ids, **gate_kw)
        self.lane_tick(self.b, t, n4k, gadgets_on_map, live_ids, **gate_kw)


ANCHORS = {ABC_1100: {
    "Item spawns: _-13p seeds I, lane draws _-Y1h then _-5J, then _-A1o": [
        (4908, 9, "callpropvoid", "_-24O, 1"),
        (4908, 22, "callproperty", "_-f4c, 0"),
        (4908, 27, "initproperty", "_-Y1h"),
        (4908, 39, "callproperty", "_-f4c, 0"),
        (4908, 44, "initproperty", "_-5J"),
        (4908, 103, "callpropvoid", "_-A1o, 4"),
    ],
    "Item spawns: _-O3d order _-y4V, _-I4n (flag 64), _-96d, _-u43, _-418": [
        (4879, 7, "callpropvoid", "_-y4V, 1"),
        (4879, 25, "pushbyte", "64"),
        (4879, 42, "callpropvoid", "_-I4n, 1"),
        (4879, 51, "callpropvoid", "_-96d, 1"),
        (4879, 58, "callpropvoid", "_-u43, 1"),
        (4879, 67, "callpropvoid", "_-418, 2"),
    ],
    "Item spawns: _-b2A due test (Fixed + Extra at max - 1, floor((n+1) Variable / max), rand % (2 Random + 1) - Random)": [
        (4874, 105, "getproperty", "_-E3k"),
        (4874, 113, "getproperty", "_-T2X"),
        (4874, 122, "getproperty", "_-j5F"),
        (4874, 145, "getproperty", "_-n1a"),
        (4874, 168, "divide", ""),
        (4874, 170, "callproperty", "floor, 1"),
        (4874, 189, "modulo", ""),
        (4874, 194, "subtract_i", ""),
        (4874, 206, "lessthan", ""),
    ],
    "Item spawns: _-96d weapon lane (max lazily, count >= max resets base, _-s3q first, all zones, _-e3K, redraw _-Y1h)": [
        (4876, 177, "callproperty", "_-Z2q, 2"),
        (4876, 282, "getproperty", "_-G3X"),
        (4876, 413, "greaterequals", ""),
        (4876, 433, "callproperty", "_-b2A, 3"),
        (4876, 453, "callproperty", "_-s3q, 1"),
        (4876, 484, "getproperty", "_-k4w"),
        (4876, 495, "getproperty", "_-M2s"),
        (4876, 537, "callpropvoid", "_-127, 3"),
        (4876, 562, "callpropvoid", "_-e3K, 4"),
        (4876, 575, "callproperty", "_-f4c, 0"),
        (4876, 580, "initproperty", "_-Y1h"),
        (4876, 587, "initproperty", "_-O5i"),
    ],
    "Item spawns: _-u43 gadget lane (no _-s3q; redraw _-5J)": [
        (4880, 573, "callproperty", "_-f4c, 0"),
    ],
    "Item spawns: _-n3V gate (bit 0x1000000, _-Q2c, _-n4k, InitSpawnDelay)": [
        (4921, 42, "pushint", "16777216"),
        (4921, 71, "pushbyte", "32"),
        (4921, 108, "getproperty", "_-Q2c"),
        (4921, 124, "getproperty", "_-n4k"),
        (4921, 146, "getproperty", "_-41r"),
        (4921, 153, "greaterthan", ""),
    ],
    "Item spawns: _-s3q first drop (_-63N, 2 players + _-i4e, flag 1 + _-03f, else e4H(true) + 2 x _-e3K)": [
        (4922, 8, "getproperty", "_-63N"),
        (4922, 34, "pushbyte", "2"),
        (4922, 52, "getproperty", "_-i4e"),
        (4922, 109, "pushbyte", "1"),
        (4922, 131, "getproperty", "_-03f"),
        (4922, 180, "callpropvoid", "_-e4H, 1"),
        (4922, 201, "callpropvoid", "_-e3K, 4"),
        (4922, 221, "callpropvoid", "_-e3K, 4"),
    ],
    "Item spawns: _-127 spawns at each rect centre (x + w / 2, y + h / 2)": [
        (4886, 66, "getproperty", "_-W2D"),
        (4886, 71, "getproperty", "_-w2s"),
        (4886, 74, "pushdouble", "0.5"),
        (4886, 82, "getproperty", "_-U1v"),
        (4886, 88, "getproperty", "_-S2O"),
        (4886, 97, "callpropvoid", "_-e3K, 4"),
    ],
    "Item spawns: _-K5X weighted pick (ceil average for live items, I % (total (n - 1)), sudden death)": [
        (4911, 230, "callproperty", "_-168, 1"),
        (4911, 305, "callproperty", "ceil, 1"),
        (4911, 356, "callproperty", "_-a3s, 0"),
        (4911, 479, "multiply_i", ""),
        (4911, 489, "callproperty", "_-f4c, 0"),
        (4911, 496, "modulo", ""),
        (4911, 583, "subtract_i", ""),
        (4911, 617, "getproperty", "_-F3O"),
        (4911, 626, "getproperty", "_-B24"),
        (4911, 651, "callpropvoid", "_-a4o, 1"),
    ],
    "Item spawns: _-p1K cursor _-S3D over _-X69, shuffle when past the end, one I draw for x (low 16) / y (high 16)": [
        (4888, 68, "getproperty", "_-X69"),
        (4888, 189, "callpropvoid", "_-e4H, 0"),
        (4888, 224, "initproperty", "_-S3D"),
        (4888, 246, "callproperty", "_-T1v, 2"),
        (4888, 377, "callproperty", "_-f4c, 0"),
        (4888, 393, "pushbyte", "16"),
        (4888, 395, "urshift", ""),
        (4888, 397, "pushdouble", "65535.0"),
        (4888, 419, "pushint", "65535"),
        (4888, 422, "bitand", ""),
        (4888, 461, "constructprop", "_-64Z, 4"),
        (4888, 488, "constructprop", "_-p5k, 6"),
    ],
    "Item spawns: _-e4H shuffle (_-A6B._-eV with I), leftmost to 0, rightmost to 1": [
        (4892, 69, "initproperty", "_-S3D"),
        (4892, 83, "callpropvoid", "_-eV, 2"),
        (4892, 152, "ifnlt", "4"),
        (4892, 214, "ifngt", "5"),
    ],
    "Item spawns: _-SH resets the cursor _-S3D to uint(-1)": [
        (4899, 106, "pushbyte", "-1"),
        (4899, 109, "initproperty", "_-S3D"),
    ],
    "Item spawns: _-A1o rates (Disabled -> null), TestFeature filter, gadget mask bits": [
        (4907, 105, "getproperty", "_-02s"),
        (4907, 384, "getproperty", "_-F4E"),
        (4907, 421, "lshift", ""),
    ],
    "Item spawns: _-Z2q max item count (100 default and cap)": [
        (4952, 14, "getproperty", "_-93K"),
        (4952, 37, "pushbyte", "100"),
        (4952, 63, "callproperty", "ceil, 1"),
        (4952, 78, "callproperty", "floor, 1"),
    ],
    "Item spawns: ItemSpawnRateType columns (_-W68)": [
        (4949, 189, "pushstring", "'ExtraTimeBeforeMax'"),
        (4949, 211, "initproperty", "_-n1a"),
        (4949, 220, "pushstring", "'FixedTimeBetweenSpawns'"),
        (4949, 242, "initproperty", "_-T2X"),
        (4949, 252, "pushstring", "'InitSpawnDelay'"),
        (4949, 274, "initproperty", "_-41r"),
        (4949, 345, "pushstring", "'RandomTimeBetweenSpawns'"),
        (4949, 365, "initproperty", "_-j5F"),
        (4949, 496, "pushstring", "'VariableTimeBetweenSpawns'"),
        (4949, 517, "initproperty", "_-E3k"),
    ],
    "Item spawns: settings order _-46U, _-O2B, _-O4I, _-i48 (_-I3W._-G5)": [
        (3875, 147, "initproperty", "_-46U"),
        (3875, 162, "initproperty", "_-O2B"),
        (3875, 177, "initproperty", "_-O4I"),
        (3875, 192, "initproperty", "_-i48"),
    ],
    "Item spawns: level lists (ItemSet _-v3h, ItemInitSpawn _-i4e, TeamItemInitSpawn _-03f, ItemSpawn _-X69)": [
        (5231, 35, "getproperty", "_-v3h"),
        (5231, 57, "getproperty", "_-i4e"),
        (5231, 81, "getproperty", "_-03f"),
        (5231, 98, "getproperty", "_-X69"),
    ],
    "Item spawns: default rects H 10, ItemSet 40 x 40, init spawns 50 x 50": [
        (15351, 43780, "pushbyte", "10"),
        (15351, 43786, "initproperty", "_-k1"),
        (15351, 43801, "pushbyte", "40"),
        (15351, 43809, "initproperty", "_-X3M"),
        (15351, 43824, "pushbyte", "50"),
        (15351, 43832, "initproperty", "_-15j"),
    ],
    "Item spawns: rule set Use1v1AndTeamInitialWeaponSpawns -> _-63N": [
        (4958, 263, "pushstring", "'Use1v1AndTeamInitialWeaponSpawns'"),
        (4958, 284, "initproperty", "_-63N"),
    ],
}}
