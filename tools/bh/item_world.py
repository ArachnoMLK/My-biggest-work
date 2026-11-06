"""Items in the harness (integration glue): spawns, falls and weapon pick-ups during a replay.

The pieces are [V] in their own modules: `item_spawns.ItemManager` (`_-E1V`, generator I), the item motion of
items.py (`_-p5k._-8i`: velocity, map sweep, impact), the pick-up chain (entity_states.PICK_UP: ThrowItem 512 ->
`_-F5N._-LY` -> `_-N5R` 150 x 150 query -> `_-u30` -> `_-s1u`) and the weapon crate of `_-F5N._-u30` #1709
(@429-512, [V]): a WeaponCrate item (`_-E2E`) gives `mBaseWeapon1` when the fighter's counter `_-56C` is even,
else `mBaseWeapon2`, and `_-56C` += 1. `_-56C` starts at R % 2 (`_-F5N.<init>`, match_start.r_at_match_start).

The glue is [H]: the settings -> rates mapping skips `_-L5u`; I is seeded like R (`seed_from_header`, both come
from `_-h3U._-669`); the `_-56C` draws are taken in replay entity order; the item choice is pickup.choose
(`_-N5R`) with a2 true, the fighter point = the harness (x, y) and the item centre = its (x, y); a press while armed throws the
weapon away (no thrown item is simulated); a KO loses the weapon (the respawned fighter starts unarmed); held
weapons count for the weapon lane; `_-a3s()` is false for every item; items move in phase 4 after the spawns.
"""
import csv
import io

from . import items, pickup
from .item_spawns import ItemManager, parse_level_spawns
from .prng import Well512, seed_from_header

UNARMED = "Unarmed"


def item_types(csv_text):
    """itemTypes.csv -> {ItemName: items.item_type row + id (ItemID), name, E2E (WeaponCrate), F4E (TestFeature),
    B24 (RemoveDuringSuddenDeath)}."""
    rows = list(csv.reader(io.StringIO(csv_text)))
    head = rows[1]
    out = {}
    for r in rows[2:]:
        cells = dict(zip(head, r))
        name = cells.get("ItemName")
        if not name:
            continue
        it = items.item_type(cells)
        flag = lambda c: (cells.get(c) or "").strip().lower() == "true"
        it.update(id=int(cells.get("ItemID") or 0), name=name, E2E=flag("WeaponCrate"), F4E=flag("TestFeature"),
                  B24=flag("RemoveDuringSuddenDeath"), r5R=flag("Spawnable"),
                  p5R=flag("DisablePickup") or name == "ThrowBow", w2s=float(cells.get("Width") or 0))
        out[name] = it
    return out


class World:
    def __init__(self, seed, settings, rates, rule_sets, types, level_xml, grid, players=2, r56c=()):
        by_id = {r["f41"]: r for r in rates.values()}
        self.rule = rule_sets.get(settings.get("item_spawn_ruleset_id"))
        on = settings.get("variation") != 3                  # `_-I3W._-52d` [H: `_-L5u` not checked]
        wr = by_id.get(settings.get("weapon_spawn_rate_id")) if on else None
        gr = by_id.get(settings.get("gadget_spawn_rate_id")) if on else None
        rule = self.rule or {"weapons": [], "gadgets": [], "init_63N": False}
        weapons = [types[n] for n in rule["weapons"] if n in types]
        gadgets = [types[n] for n in rule["gadgets"] if n in types]
        self.mgr = ItemManager(Well512(seed_from_header(seed)), parse_level_spawns(level_xml), players)
        self.mgr.seed_lanes(self.rule, wr, gr, weapons, gadgets, settings.get("flags", 0),
                            settings.get("custom_gadget_selection", 0))
        self.grid = grid
        self.types = types
        self.live = []                                       # {"type", "x", "y", "lu", "vy", "ground", "state"}
        self.c56 = list(r56c)
        self.spawned = self.picked = 0

    def tick(self, t, n4k, held):
        """Phase 4: the two lanes (`held` = ItemTypes held by the fighters), then each live item moves."""
        w = sum(1 for h in held if h and h.get("G3X")) + sum(1 for i in self.live if i["type"].get("G3X"))
        g = sum(1 for h in held if h and not h.get("G3X")) + sum(1 for i in self.live if not i["type"].get("G3X"))
        self.mgr.tick(t, n4k, w, g, [i["type"]["id"] for i in self.live])
        for s in self.mgr.spawned:
            self.live.append({"type": s["type"], "x": s["x"], "y": s["y"], "lu": 0.0, "vy": 0.0, "ground": None,
                              "state": 0})
            self.spawned += 1
        self.mgr.spawned = []
        for i in self.live:
            it = i["type"]
            i["lu"], i["vy"], mv = items.velocity(i["lu"], i["vy"], 0.0, 0.0, i["ground"], it, thrown=False, o2o=False)
            i["x"], i["y"], ground, _ = items.sweep(self.grid, 0, i["x"], i["y"], mv, 3, it["S2O"])
            if ground is None and i.get("rest"):            # smoke.item_fall: a resting item keeps its line
                ground = i["ground"]
            i["lu"], i["vy"], i["state"], _ = items.after_sweep(i["lu"], i["vy"], ground, it, i["state"])
            i["ground"] = ground
            i["rest"] = ground is not None and i["lu"] == 0 and i["vy"] == 0

    def pick_up(self, t, me, x, y, hero):
        """`_-N5R` (pickup.choose, a2 true: no QuickAttack [H]) over the live items; the chosen one leaves the map."""
        best = pickup.choose(self.live, t, me, x, y, hero or {})
        if best is None:
            return None
        self.live.remove(best)
        self.picked += 1
        return best["type"]

    def crate_weapon(self, k, hero):
        """`_-u30` @440-512: the base weapon a crate gives fighter k (`_-56C` parity), and `_-56C` += 1."""
        c = self.c56[k] if k < len(self.c56) else 0
        if k < len(self.c56):
            self.c56[k] = c + 1
        return hero.get("mBaseWeapon1") if c % 2 == 0 else hero.get("mBaseWeapon2")
