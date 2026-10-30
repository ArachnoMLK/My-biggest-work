"""bht: Brawlhalla research toolkit (stdlib only, Python 3.10+).

Run `python -I tools/bht.py <command> --help`. Every output goes to ./work (git-ignored):
never commit game files, decrypted data, decompiled code or replays.
"""
import argparse
import csv
import glob
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bh import abc as abcmod  # noqa: E402
from bh import anm as anmmod, collision as collisionmod, commands as commandsmod, hitdetect as hitdetectmod, input_buffer as inputbufmod, ko as komod  # noqa: E402
from bh import movement as movementmod  # noqa: E402
from bh import oracle as oraclemod  # noqa: E402
from bh import knockback as knockbackmod  # noqa: E402
from bh import powertypes as powertypesmod  # noqa: E402
from bh import prng as prngmod  # noqa: E402
from bh import prng_order as prngordermod  # noqa: E402
from bh import render as rendermod  # noqa: E402
from bh import smoke as smokemod  # noqa: E402
from bh import ko_gaps as kogapsmod  # noqa: E402
from bh import level_bounds as levelboundsmod  # noqa: E402
from bh import step as stepmod  # noqa: E402
from bh import replay as replaymod  # noqa: E402
from bh import stats as statsmod  # noqa: E402
from bh import swf as swfmod  # noqa: E402
from bh import swz as swzmod  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(ROOT, "work")
DEFAULT_GAME = os.environ.get("BRAWLHALLA_DIR", r"C:\Program Files (x86)\Steam\steamapps\common\Brawlhalla")
DEFAULT_REPLAYS = os.environ.get("BRAWLHALLA_REPLAYS", os.path.join(os.path.expanduser("~"), "BrawlhallaReplays"))
ARCHIVES = ["Engine.swz", "Init.swz", "Game.swz", "Dynamic.swz"]


def out_path(*parts):
    p = os.path.join(WORK, *parts)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


def save_json(obj, *parts):
    p = out_path(*parts)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False, default=str)
    return p


def kind_of(rel):
    name = os.path.basename(rel)
    ext = os.path.splitext(name)[1].lower()
    for prefix, kind in (("Gfx_", "gfx-swf"), ("SFX_", "sfx-swf"), ("UI_", "ui-swf"), ("Bones_", "bones-swf"),
                         ("Animation_", "anm"), ("Splashart", "ui-swf")):
        if name.startswith(prefix):
            return kind
    if name == "BrawlhallaAir.swf":
        return "main-code"
    return {".swz": "swz-archive", ".anm": "anm", ".bnk": "audio-bank", ".swf": "swf", ".png": "image",
            ".jpg": "image", ".bin": "lang", ".xml": "xml", ".dll": "native", ".exe": "native",
            ".ane": "native-extension"}.get(ext, ext.lstrip(".") or "other")


# ---------------------------------------------------------------- commands
def cmd_inventory(a):
    """Hash and classify every file of the install; write work/inventory.json and the ledger CSV."""
    rows, t0 = [], time.time()
    ledger = os.path.join(ROOT, "ledger", "game-files.csv")
    old = {}
    if os.path.exists(ledger):
        with open(ledger, encoding="utf-8") as f:
            old = {r["path"]: r for r in csv.DictReader(f)}
    for dirpath, dirs, files in os.walk(a.game):
        if dirpath == a.game and "Adobe AIR" in dirs:
            dirs.remove("Adobe AIR")  # the bundled AIR runtime, not game content
        for fn in sorted(files):
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, a.game).replace("\\", "/")
            h = hashlib.sha256()
            with open(full, "rb") as f:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    h.update(chunk)
            prev = old.get(rel, {})
            rows.append({"path": rel, "size": os.path.getsize(full), "sha256": h.hexdigest(), "kind": kind_of(rel),
                         "status": prev.get("status", "unread"), "owner": prev.get("owner", ""),
                         "notes": prev.get("notes", "")})
    rows.sort(key=lambda r: (r["kind"], r["path"]))
    with open(ledger, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    kinds = Counter(r["kind"] for r in rows)
    sizes = Counter()
    for r in rows:
        sizes[r["kind"]] += r["size"]
    save_json({"game": a.game, "files": len(rows), "by_kind": {k: [kinds[k], sizes[k]] for k in kinds}}, "inventory.json")
    print(f"{len(rows)} files in {time.time() - t0:.0f}s -> ledger/game-files.csv")
    for k, n in kinds.most_common():
        print(f"  {k:<18} {n:5d} files {sizes[k] / 1e6:9.1f} MB")


def load_main_abc(game):
    swf = swfmod.Swf(open(os.path.join(game, "BrawlhallaAir.swf"), "rb").read())
    blocks = swf.abc_blocks()
    name, data = max(blocks, key=lambda b: len(b[1]))
    return swf, data


def cmd_abc_extract(a):
    """Extract the biggest DoABC block of BrawlhallaAir.swf to work/abc/main.abc and summarize it."""
    swf, data = load_main_abc(a.game)
    p = out_path("abc", "main.abc")
    open(p, "wb").write(data)
    abc = abcmod.Abc(data)
    obf = sum(1 for s in abc.strings[1:] if s and re.fullmatch(r"_-[A-Za-z0-9]{2,4}", s))
    hx = sorted({m.group(1) for s in abc.strings[1:] if s for m in re.finditer(r"\[(\w+)\.hx\]", s)})
    summary = {"sha256": hashlib.sha256(data).hexdigest(), "abc_version": f"{abc.major}.{abc.minor}",
               "swf_tags": swf.tag_counts(), "abc_blocks": [(n, len(d)) for n, d in swf.abc_blocks()],
               "ints": len(abc.ints), "uints": len(abc.uints), "doubles": len(abc.doubles),
               "strings": len(abc.strings), "multinames": len(abc.multinames), "methods": len(abc.methods),
               "classes": len(abc.instances), "scripts": len(abc.scripts), "bodies": len(abc.bodies),
               "obfuscated_strings": obf, "haxe_sources": hx}
    save_json(summary, "abc", "summary.json")
    print(json.dumps({k: v for k, v in summary.items() if k != "haxe_sources"}, indent=1))
    print(f"-> {p}")


def open_abc(a):
    p = a.abc or os.path.join(WORK, "abc", "main.abc")
    if not os.path.exists(p):
        sys.exit("run `abc-extract` first (or pass --abc)")
    return abcmod.Abc(open(p, "rb").read())


def cmd_abc_validate(a):
    """Decode every method body and check branch targets (sanity check of the disassembler)."""
    rep = abcmod.validate(open_abc(a))
    print(f"bodies {rep['bodies']}  decoded {rep['decoded']}  errors {len(rep['errors'])}  bad branches {rep['bad_branches']}")
    for m, e in rep["errors"][:20]:
        print(f"  method {m}: {e}")


def cmd_abc_classes(a):
    """List classes (name, super, member counts) to work/abc/classes.json."""
    abc = open_abc(a)
    out = []
    for ci, inst in enumerate(abc.instances):
        out.append({"id": ci, "name": abc.class_name(ci), "super": abc.mn_name(inst["super"], full=True),
                    "iinit": inst["iinit"], "cinit": abc.classes[ci]["cinit"],
                    "instance_traits": [abc.mn_name(t["name"]) for t in inst["traits"]],
                    "static_traits": [abc.mn_name(t["name"]) for t in abc.classes[ci]["traits"]]})
    p = save_json(out, "abc", "classes.json")
    named = [c for c in out if not c["name"].split("::")[-1].startswith("_-")]
    print(f"{len(out)} classes ({len(named)} with readable names) -> {p}")
    if a.grep:
        for c in out:
            if re.search(a.grep, c["name"] + " " + " ".join(c["instance_traits"] + c["static_traits"])):
                print(f"  #{c['id']:5d} {c['name']}  extends {c['super']}  ({len(c['instance_traits'])}+{len(c['static_traits'])} traits)")


def cmd_abc_disasm(a):
    """Disassemble one method (--method N) or every method of a class (--class ID or name)."""
    abc = open_abc(a)
    owner = abc.method_owner()
    ids = []
    if a.method is not None:
        ids = [a.method]
    if a.cls is not None:
        ci = int(a.cls) if a.cls.isdigit() else next(i for i in range(len(abc.instances)) if abc.class_name(i).endswith(a.cls))
        inst = abc.instances[ci]
        ids = [abc.classes[ci]["cinit"], inst["iinit"]] + [t["method"] for t in inst["traits"] + abc.classes[ci]["traits"] if "method" in t]
    for m in ids:
        print(f"method #{m}  {owner.get(m, '?')}")
        print(abcmod.disassemble(abc, m))
        print()


def cmd_abc_refs(a):
    """Summarize what one method touches: members read/written/called/constructed and constants pushed."""
    abc = open_abc(a)
    refs = abcmod.member_refs(abc, a.method)
    print(f"method #{a.method}  {abc.method_owner().get(a.method, '?')}")
    for title, table in (("members", refs["members"]), ("constants", refs["constants"])):
        print(f"{title}:")
        for (op, value), n in sorted(table.items(), key=lambda kv: (kv[0][0], kv[0][1])):
            print(f"  {n:3d}  {op:<16} {value}")


def _parse_value(v):
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    try:
        return float(v)
    except ValueError:
        return v


def cmd_abc_find(a):
    """Find methods that push a constant (number or string), or that reference a member name."""
    abc = open_abc(a)
    owner = abc.method_owner()
    hits = abcmod.callers_of(abc, a.value) if a.member else abcmod.find_constant_uses(abc, _parse_value(a.value))
    for m in hits:
        print(f"  method #{m:6d}  {owner.get(m, '?')}")
    print(f"{len(hits)} methods")


def cmd_abc_strings(a):
    """Search the constant pool strings with a regex."""
    abc = open_abc(a)
    rx = re.compile(a.pattern, re.I)
    for i, s in enumerate(abc.strings):
        if s and rx.search(s):
            print(f"  #{i:6d} {s[:200]!r}")


def _verify_anchors(a, table):
    """Check pinned bytecode anchors; exit 1 on mismatch, 2 on unknown ABC. Returns normally when all match."""
    p = a.abc or os.path.join(WORK, "abc", "main.abc")
    if not os.path.exists(p):
        sys.exit("run `abc-extract` first (or pass --abc)")
    data = open(p, "rb").read()
    sha = hashlib.sha256(data).hexdigest()
    anchors = table.get(sha)
    if anchors is None:
        print(f"no anchors for ABC {sha[:8]}... (known: {', '.join(k[:8] for k in table)})")
        sys.exit(2)
    abc = abcmod.Abc(data)
    owner = abc.method_owner()
    bad = movementmod.check(anchors, lambda m: movementmod.listing(abc, m))
    for (m, off, op, text), found in bad:
        print(f"  MISMATCH #{m} {owner.get(m, '?')} @{off}: want {op} {text}, found {found}")
    print(f"ABC {sha[:8]}...  anchors {len(anchors)}  ok {len(anchors) - len(bad)}  mismatches {len(bad)}")
    if bad:
        sys.exit(1)


def cmd_movement_verify(a):
    """Check the pinned bytecode anchors of the jump/gravity chain (Q4)."""
    _verify_anchors(a, movementmod.ANCHORS)
    scale = 0.384
    for label, v in (("grounded jump 57", 57.0), ("dash jump 170", 170.0), ("gravity 3.75", 3.75)):
        print(f"  {label:<18} x {scale} = {v * scale!r} per tick")


def cmd_commands_verify(a):
    """Check the pinned anchors of the input command table (names of input bits 1 and 32)."""
    _verify_anchors(a, commandsmod.ANCHORS)


def cmd_stats_verify(a):
    """Check the pinned anchors of the stance -> StatType chain (Q5)."""
    _verify_anchors(a, statsmod.ANCHORS)


def cmd_legend_stats(a):
    """Print the effective fighter stats of one legend and stance from the local swz dump (Q5)."""
    base = os.path.join(a.swz or os.path.join(WORK, "swz"), "Game.swz")
    stat_types = statsmod.parse_stat_types(rendermod.read_text(os.path.join(base, "StatTypes.xml")))
    stances = statsmod.parse_stances(rendermod.read_text(os.path.join(base, "RuneTypes.xml")))
    if a.hero is None:
        print(" ".join(sorted({h for h, _ in stances})))
        return
    levels = stances.get((a.hero, a.stance))
    if levels is None:
        sys.exit(f"no stance {a.stance} for {a.hero!r} (run without --hero for the list)")
    print(f"{a.hero} stance {a.stance}: " + ", ".join(f"{k} {v}" for k, v in levels.items()))
    for field, value in statsmod.fighter_stats(levels, stat_types).items():
        print(f"  {field:<16} {value!r}")


def cmd_anm_info(a):
    """Summarize .anm files (sets, animations, frames, bones); with --anim, print one animation's header."""
    files = [a.file] if a.file else sorted(glob.glob(os.path.join(a.game, "anims", "*.anm")))
    total = Counter()
    for path in files:
        sets = anmmod.parse(open(path, "rb").read())
        anims = [an for s in sets.values() for an in s["animations"]]
        frames = sum(len(an["frames"]) for an in anims)
        total.update(files=1, anims=len(anims), frames=frames, bones=sum(len(f["bones"]) for an in anims for f in an["frames"]))
        if a.file or a.verbose:
            print(f"{os.path.basename(path)}: {len(sets)} sets, {len(anims)} animations, {frames} frames")
        for an in anims:
            if a.anim and an["name"] == a.anim:
                print("  " + ", ".join(f"{k} {an[k]}" for k in ["name"] + anmmod.ANIM_FIELDS) + f", data {an['data']}")
    print(" ".join(f"{k} {v}" for k, v in total.items()))


def cmd_collision_verify(a):
    """Check the pinned anchors of the level collision flags (Q6) and print the type compositions."""
    _verify_anchors(a, collisionmod.ANCHORS)
    for name, value in collisionmod.TYPES.items():
        bits = [f for f, b in collisionmod.FLAGS.items() if value & b]
        print(f"  {name:<27} {value:4d}  {' | '.join(bits)}")


def cmd_hit_detection_verify(a):
    """Check the pinned shape of hit detection (hit area, hurtbox, capsule test); exit 1 on mismatch, 2 on unknown ABC."""
    p = a.abc or os.path.join(WORK, "abc", "main.abc")
    if not os.path.exists(p):
        sys.exit("run `abc-extract` first (or pass --abc)")
    with open(p, "rb") as f:
        data = f.read()
    sha = hashlib.sha256(data).hexdigest()
    if sha not in hitdetectmod.ANCHORS:
        print(f"no hit detection anchors for ABC {sha[:8]}... (known: {', '.join(k[:8] for k in hitdetectmod.ANCHORS)})")
        sys.exit(2)
    bad = hitdetectmod.verify(abcmod.Abc(data), sha)
    for line in bad:
        print(f"  MISMATCH {line}")
    print(f"ABC {sha[:8]}...  anchors {hitdetectmod.count(sha)}  mismatches {len(bad)}")
    if bad:
        sys.exit(1)
    for group in hitdetectmod.ANCHORS[sha]:
        print(f"  ok  {group}")
    print("static bytecode evidence only: no execution, no runtime oracle (docs/hit-detection-11.00.md)")


def cmd_prng_order_verify(a):
    """Check the pinned static evidence of PRNG draw order (Q3); exit 1 on mismatch, 2 on unknown ABC."""
    p = a.abc or os.path.join(WORK, "abc", "main.abc")
    if not os.path.exists(p):
        sys.exit("run `abc-extract` first (or pass --abc)")
    with open(p, "rb") as f:
        data = f.read()
    sha = hashlib.sha256(data).hexdigest()
    if sha not in prngordermod.ANCHORS:
        print(f"no draw-order anchors for ABC {sha[:8]}... (known: {', '.join(k[:8] for k in prngordermod.ANCHORS)})")
        sys.exit(2)
    bad = prngordermod.verify(abcmod.Abc(data), sha)
    for line in bad:
        print(f"  MISMATCH {line}")
    anchors, refs, slots = prngordermod.counts(sha)
    print(f"ABC {sha[:8]}...  anchors {anchors}  reference sets {refs}  slot types {slots}  mismatches {len(bad)}")
    if bad:
        sys.exit(1)
    for group in prngordermod.ANCHORS[sha]:
        print(f"  ok  {group}")
    print("static bytecode evidence only: no execution, no runtime oracle (docs/prng-order-11.00.md)")


def cmd_step_verify(a):
    """Check the pinned order of operations of Entity._-8i; exit 1 on mismatch, 2 on unknown ABC."""
    p = a.abc or os.path.join(WORK, "abc", "main.abc")
    if not os.path.exists(p):
        sys.exit("run `abc-extract` first (or pass --abc)")
    with open(p, "rb") as f:
        data = f.read()
    sha = hashlib.sha256(data).hexdigest()
    if sha not in stepmod.ANCHORS:
        print(f"no step anchors for ABC {sha[:8]}... (known: {', '.join(k[:8] for k in stepmod.ANCHORS)})")
        sys.exit(2)
    bad = stepmod.verify(abcmod.Abc(data), sha)
    for line in bad:
        print(f"  MISMATCH {line}")
    anchors, slots = stepmod.counts(sha)
    print(f"ABC {sha[:8]}...  anchors {anchors}  slot types {slots}  mismatches {len(bad)}")
    if bad:
        sys.exit(1)
    for group in stepmod.ANCHORS[sha]:
        print(f"  ok  {group}")
    print("static bytecode evidence only: no execution, no runtime oracle (docs/entity-step-11.00.md)")


def cmd_ko_verify(a):
    """Check the pinned static evidence of the KO bounds test; exit 1 on mismatch, 2 on unknown ABC."""
    p = a.abc or os.path.join(WORK, "abc", "main.abc")
    if not os.path.exists(p):
        sys.exit("run `abc-extract` first (or pass --abc)")
    with open(p, "rb") as f:
        data = f.read()
    sha = hashlib.sha256(data).hexdigest()
    if sha not in komod.ANCHORS:
        print(f"no KO anchors for ABC {sha[:8]}... (known: {', '.join(k[:8] for k in komod.ANCHORS)})")
        sys.exit(2)
    bad = komod.verify(abcmod.Abc(data), sha)
    for line in bad:
        print(f"  MISMATCH {line}")
    anchors, slots = komod.counts(sha)
    print(f"ABC {sha[:8]}...  anchors {anchors}  slot types {slots}  mismatches {len(bad)}")
    if bad:
        sys.exit(1)
    for group in komod.ANCHORS[sha]:
        print(f"  ok  {group}")
    print("static bytecode evidence only: no execution, no runtime oracle (docs/ko-11.00.md)")


def cmd_input_buffer_verify(a):
    """Check the pinned shape of the input buffer (#6313, #6323); exit 1 on mismatch, 2 on unknown ABC."""
    p = a.abc or os.path.join(WORK, "abc", "main.abc")
    if not os.path.exists(p):
        sys.exit("run `abc-extract` first (or pass --abc)")
    with open(p, "rb") as f:
        data = f.read()
    sha = hashlib.sha256(data).hexdigest()
    if sha not in inputbufmod.ANCHORS:
        print(f"no input-buffer anchors for ABC {sha[:8]}... (known: {', '.join(k[:8] for k in inputbufmod.ANCHORS)})")
        sys.exit(2)
    bad = inputbufmod.verify(abcmod.Abc(data), sha)
    for line in bad:
        print(f"  MISMATCH {line}")
    print(f"ABC {sha[:8]}...  anchors {inputbufmod.count(sha)}  mismatches {len(bad)}")
    if bad:
        sys.exit(1)
    for group in inputbufmod.ANCHORS[sha]:
        print(f"  ok  {group}")
    print("static bytecode evidence only: no execution, no runtime oracle (docs/input-buffer-11.00.md)")


def cmd_knockback_verify(a):
    """Check the pinned shape of the damage / knockback formula (#1674, #1675); exit 1 on mismatch, 2 on unknown ABC."""
    p = a.abc or os.path.join(WORK, "abc", "main.abc")
    if not os.path.exists(p):
        sys.exit("run `abc-extract` first (or pass --abc)")
    with open(p, "rb") as f:
        data = f.read()
    sha = hashlib.sha256(data).hexdigest()
    if sha not in knockbackmod.ANCHORS:
        print(f"no knockback anchors for ABC {sha[:8]}... (known: {', '.join(k[:8] for k in knockbackmod.ANCHORS)})")
        sys.exit(2)
    bad = knockbackmod.verify(abcmod.Abc(data), sha)
    for line in bad:
        print(f"  MISMATCH {line}")
    print(f"ABC {sha[:8]}...  anchors {knockbackmod.count(sha)}  mismatches {len(bad)}")
    if bad:
        sys.exit(1)
    for group in knockbackmod.ANCHORS[sha]:
        print(f"  ok  {group}")
    print("static bytecode evidence only: no execution, no runtime oracle (docs/knockback-11.00.md)")


def cmd_ko_gap_check(a):
    """No KO of the same victim before the respawn drone has dropped it (oracle + spawn bot); aggregate only."""
    base = os.path.join(a.swz or os.path.join(WORK, "swz"), "Game.swz", "ScoringTypes.xml")
    if not os.path.exists(base):
        sys.exit("no ScoringTypes.xml; run swz-dump first (or pass --swz)")
    cells = kogapsmod.scoring_cells(rendermod.read_text(base))
    reps = []
    for p in glob.glob(os.path.join(a.dir, "*.replay")):
        try:
            with open(p, "rb") as f:
                rep = replaymod.parse(f.read())
        except Exception:
            continue
        if rep.get("version") == 271:
            reps.append(rep)
    for k, v in kogapsmod.check(reps, cells).items():
        print(f"  {k:<22} {v}")
    print("one-sided check from the replays' own KO faces; nothing is published (tools/bh/ko_gaps.py)")


def cmd_smoke_fall(a):
    """One fighter, no input, falls from every respawn point of the local LevelDescs (aggregate counts only)."""
    import glob
    folder = os.path.join(a.swz or os.path.join(WORK, "swz"), "Dynamic.swz")
    files = sorted(glob.glob(os.path.join(folder, "LevelDesc_*.xml")))
    if not files:
        sys.exit("no LevelDesc files; run swz-dump first (or pass --swz)")
    xmls = [rendermod.read_text(f) for f in files]
    counts = smokemod.run(xmls, with_platforms=not a.static_only)
    for k, v in counts.items():
        print(f"  {k:<24} {v}")
    print("walking both ways at x step 6 after landing (static lines):")
    for k, v in smokemod.run_walk(xmls).items():
        print(f"  {k:<24} {v}")
    print("items (default ItemType, static lines):")
    for k, v in smokemod.run_items(xmls, smokemod.items.ITEM_DEFAULTS).items():
        print(f"  {k:<24} {v}")
    lt = os.path.join(a.swz or os.path.join(WORK, "swz"), "Init.swz", "LevelTypes.xml")
    if os.path.exists(lt):
        names = [os.path.basename(f)[len("LevelDesc_"):-len(".xml")] for f in files]
        print("KO bounds (CameraBounds + LevelType kill values), falls into the void:")
        for k, v in levelboundsmod.run(list(zip(names, xmls)), levelboundsmod.level_kills(rendermod.read_text(lt))).items():
            print(f"  {k:<24} {v}")
    print("item thrown from every landing, 6 directions x (no charge, 2.5 s) (static lines):")
    for k, v in smokemod.run_throws(xmls, smokemod.items.ITEM_DEFAULTS).items():
        print(f"  {k:<24} {v}")
    print("item pushed both ways (_-Lu = 10) after it stopped (static lines):")
    for k, v in smokemod.run_item_slide(xmls, smokemod.items.ITEM_DEFAULTS).items():
        print(f"  {k:<24} {v}")
    print("static bytecode evidence only: not compared with the running game (tools/bh/smoke.py)")
    if counts["contact"] != counts["within_1e-6"]:
        sys.exit(1)


def cmd_power_columns(a):
    """Print the powerTypes column -> PowerType field map rebuilt from the ABC (#6483); no game data is read."""
    p = a.abc or os.path.join(WORK, "abc", "main.abc")
    if not os.path.exists(p):
        sys.exit("run `abc-extract` first (or pass --abc)")
    with open(p, "rb") as f:
        data = f.read()
    sha = hashlib.sha256(data).hexdigest()
    if sha != movementmod.ABC_1100:
        print(f"the parser id #{powertypesmod.PARSER} is pinned to patch 11.00 (ABC {movementmod.ABC_1100[:8]}...)")
        sys.exit(2)
    cmap = powertypesmod.column_map(abcmod.Abc(data))
    if a.markdown:
        print("| Column | Fields |")
        print("|---|---|")
        for col in sorted(cmap):
            print(f"| {col} | {', '.join('`' + x + '`' for x in cmap[col]) or '—'} |")
    else:
        for col in sorted(cmap):
            print(f"{col:28} {' '.join(cmap[col]) or '-'}")
    print(f"{len(cmap)} columns", file=sys.stderr)


def cmd_swz_key(a):
    """Find the .swz key: try every uint of the main ABC, else brute-force keys ending with --suffix."""
    data = open(os.path.join(a.game, "Init.swz"), "rb").read()
    _, abc_data = load_main_abc(a.game)
    abc = abcmod.Abc(abc_data)
    key = swzmod.find_key(data, candidates=abc.uints[1:], patch_suffix=a.suffix)
    print(key if key is not None else "not found")


def cmd_swz_dump(a):
    """Decrypt Engine/Init/Game/Dynamic.swz to work/swz/<archive>/."""
    for name in ARCHIVES:
        names = swzmod.dump(os.path.join(a.game, name), a.key, os.path.join(WORK, "swz", name))
        print(f"{name}: {len(names)} files")


def cmd_swf_info(a):
    """Tag counts, DoABC blocks and exported symbols of any .swf."""
    swf = swfmod.Swf(open(a.file, "rb").read())
    print(f"{swf.compression} v{swf.version} {swf.frame_count} frames @ {swf.frame_rate} fps")
    print("tags:", swf.tag_counts())
    print("abc:", [(n, len(d)) for n, d in swf.abc_blocks()])
    syms = swf.symbols()
    print(f"{len(syms)} symbols")
    for cid, name in syms[: a.limit]:
        print(f"  {cid:5d} {name}")


def _bounded_int(lo, hi):
    def parse(text):
        try:
            v = int(text, 0)
        except ValueError:
            raise argparse.ArgumentTypeError(f"not an integer: {text!r}") from None
        if not lo <= v <= hi:
            raise argparse.ArgumentTypeError(f"{v} is outside [{lo}, {hi}]")
        return v
    return parse


def cmd_prng(a):
    """Print the match PRNG stream (WELL512 `Random`, see docs/prng-11.00.md) for a replay seed."""
    seed = prngmod.seed_from_header(a.seed)
    rng = prngmod.Well512(seed)
    for _ in range(a.skip):
        rng.next_u32()
    if a.state:
        index, words = rng.getstate()
        print(json.dumps({"seed": seed, "after_draws": a.skip, "index": index, "state": list(words)}))
        return
    rows = []
    for k in range(a.skip, a.skip + a.count):
        u = rng.next_u32()
        rows.append({"draw": k, "u32": u, "unit": u / 4294967295.0})
    if a.json:
        print(json.dumps({"seed": seed, "draws": rows}))
        return
    print(f"seed {seed} (0x{seed:08x})")
    for r in rows:
        print(f"  {r['draw']:7d}  {r['u32']:10d}  0x{r['u32']:08x}  {r['unit']:.17g}")


def cmd_prng_verify(a):
    """Check tools/bh/prng.py against the bytecode of class `Random` and its helpers (emulated)."""
    abc = open_abc(a)
    found = prngmod.locate(abc)
    print("Random class #{}  seed #{}  next #{}  uniform #{}  range_u32 #{}  range_i32 #{}  shuffle #{}".format(
        found["class"], *(found.get(k, "?") for k in ("seed", "next", "uniform", "range_u32", "range_i32", "shuffle"))))
    bad = prngmod.verify(abc, a.seeds, a.draws)
    for line in bad[:20]:
        print("  MISMATCH", line)
    print(f"{len(a.seeds)} seeds x {a.draws} draws + helpers: {'OK' if not bad else f'{len(bad)} mismatches'}")
    if bad:
        sys.exit(1)


def cmd_replay(a):
    """Print one replay: header, settings, players, results, KOs and the first inputs."""
    rep = replaymod.parse(open(a.file, "rb").read())
    inputs = rep.pop("inputs")
    if a.json:
        rep["inputs"] = inputs
        print(json.dumps(rep, indent=1, ensure_ascii=False, default=str))
        return
    print(json.dumps({k: v for k, v in rep.items() if k not in ("entities",)}, ensure_ascii=False, default=str))
    for e in rep["entities"]:
        print(f"  ent {e['id']} team {e['team']} bot={e['bot']} heroes={[h['hero_id'] for h in e['heroes']]} stance={e['heroes'][0]['stance']}")
    for who, lst in inputs.items():
        print(f"  inputs ent {who}: {len(lst)} records, last at {lst[-1][0] if lst else 0} ms")
        for ts, fl in lst[: a.limit]:
            print(f"    {ts:7d} ms  {fl:014b}  {replaymod.describe_flags(fl)}")


def cmd_ko_oracle(a):
    """Print the KO ticks of one replay (Q10 oracle, part 1); with --dir, aggregate counts only."""
    if a.dir:
        files = glob.glob(os.path.join(a.dir, "*.replay"))
        n = kos = bad = err = 0
        for p in files:
            try:
                with open(p, "rb") as f:
                    rep = replaymod.parse(f.read())
            except Exception:
                err += 1
                continue
            n += 1
            try:
                kos += len(oraclemod.ko_ticks(rep))
            except ValueError:
                bad += 1
        print(f"replays {n}  parse errors {err}  KO faces {kos}  replays with a non-tick KO time {bad}")
        return
    if not a.file:
        sys.exit("pass a replay file, or --dir")
    with open(a.file, "rb") as f:
        rep = replaymod.parse(f.read())
    for tick, victim in oraclemod.ko_ticks(rep):
        print(f"  tick {tick:6d}  ({tick * oraclemod.TICK_MS:7d} ms)  victim {victim}")


def cmd_render_summary(a):
    """Draw a replay as SVG: real map geometry + per-player input timeline + KOs (needs work/swz)."""
    rep = replaymod.parse(open(a.file, "rb").read())
    levels = rendermod.read_text(os.path.join(WORK, "swz", "Init.swz", "LevelTypes.xml"))
    name = None
    for lname, body in re.findall(r'<LevelType LevelName="([^"]+)"[^>]*>(.*?)</LevelType>', levels, re.S):
        if re.search(rf"<LevelID>{rep['level_id']}</LevelID>", body):
            name = lname
    desc = os.path.join(WORK, "swz", "Dynamic.swz", f"LevelDesc_{name}.xml")
    if not name or not os.path.exists(desc):
        sys.exit(f"no LevelDesc for level id {rep['level_id']} ({name}); run swz-dump first")
    level = rendermod.parse_level(rendermod.read_text(desc))
    legends = rendermod.legend_names(rendermod.read_text(os.path.join(WORK, "swz", "Game.swz", "HeroTypes.xml")))
    svg = rendermod.render(rep, level, name, legends)
    out = a.out or out_path("render", os.path.splitext(os.path.basename(a.file))[0] + ".svg")
    open(out, "w", encoding="utf-8").write(svg)
    print(f"{name}: {len(level['lines'])} collision lines, {len(level['respawns'])} respawns -> {out}")


def cmd_corpus(a):
    """Parse every replay of a folder and correlate it with the game data (work/swz must exist)."""
    levels, heroes = {}, {}
    lt = os.path.join(WORK, "swz", "Init.swz", "LevelTypes.xml")  # named after the root tag by swz-dump
    ht = os.path.join(WORK, "swz", "Game.swz", "HeroTypes.xml")
    if os.path.exists(lt):
        txt = open(lt, encoding="utf-8").read()
        for name, body in re.findall(r'<LevelType LevelName="([^"]+)"[^>]*>(.*?)</LevelType>', txt, re.S):
            m = re.search(r"<LevelID>(\d+)</LevelID>", body)
            if m:
                levels[int(m.group(1))] = name
    if os.path.exists(ht):
        txt = open(ht, encoding="utf-8").read()
        for name, body in re.findall(r'<HeroType HeroName="([^"]+)"[^>]*>(.*?)</HeroType>', txt, re.S):
            m = re.search(r"<HeroID>(\d+)</HeroID>", body)
            if m:
                heroes[int(m.group(1))] = name
    files = sorted(f for f in os.listdir(a.dir) if f.endswith(".replay"))[: a.limit or None]
    stats = {k: Counter() for k in ("version", "level", "hero", "playlist", "players", "objects", "error", "game_speed", "flags")}
    input_records = 0
    gaps = Counter()
    off16 = Counter()
    t0 = time.time()
    for i, fn in enumerate(files):
        try:
            rep = replaymod.parse(open(os.path.join(a.dir, fn), "rb").read())
        except Exception as e:  # noqa: BLE001 - corpus stats must survive bad files
            stats["error"][type(e).__name__ + ": " + str(e)[:60]] += 1
            continue
        stats["version"][rep["version"]] += 1
        stats["level"][levels.get(rep.get("level_id"), rep.get("level_id"))] += 1
        stats["playlist"][rep.get("playlist") or "(none)"] += 1
        stats["players"][len(rep["entities"])] += 1
        stats["objects"]["-".join(map(str, rep["objects"]))] += 1
        stats["game_speed"][rep["settings"]["game_speed"]] += 1
        stats["flags"][hex(rep["settings"]["flags"])] += 1
        for e in rep["entities"]:
            for h in e["heroes"]:
                stats["hero"][heroes.get(h["hero_id"], h["hero_id"])] += 1
        for lst in rep["inputs"].values():
            input_records += len(lst)
            for (t1, _), (t2, _) in zip(lst, lst[1:]):
                gaps[t2 - t1 if t2 - t1 <= 100 else ">100"] += 1
            for ts, _ in lst:
                off16[ts % 16] += 1
        if (i + 1) % 500 == 0:
            print(f"  {i + 1}/{len(files)} ({time.time() - t0:.0f}s)")
    # timestamps: are they all on the 16 ms simulation tick?
    result = {"files": len(files), "input_records": input_records,
              "input_gap_ms_histogram": {str(k): v for k, v in gaps.most_common()},
              "input_timestamp_mod_16ms": dict(off16.most_common()),
              **{k: dict(v.most_common()) for k, v in stats.items()}}
    p = save_json(result, "corpus.json")
    print(f"{len(files)} replays, {input_records} input records, errors {sum(stats['error'].values())} -> {p}")
    print("versions:", dict(sorted(stats["version"].items())))
    print("input timestamp mod 16 ms:", result["input_timestamp_mod_16ms"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add(name, fn, *args):
        p = sub.add_parser(name, help=fn.__doc__)
        p.set_defaults(fn=fn)
        for spec in args:
            p.add_argument(*spec[0], **spec[1])
        return p

    game = (["--game"], {"default": DEFAULT_GAME, "help": "Brawlhalla install folder (env BRAWLHALLA_DIR)"})
    abc = (["--abc"], {"help": "ABC file (default work/abc/main.abc)"})
    add("inventory", cmd_inventory, game)
    add("abc-extract", cmd_abc_extract, game)
    add("abc-validate", cmd_abc_validate, abc)
    add("abc-classes", cmd_abc_classes, abc, (["--grep"], {"help": "regex on class and member names"}))
    add("abc-disasm", cmd_abc_disasm, abc, (["--method"], {"type": int}), (["--class"], {"dest": "cls"}))
    add("abc-find", cmd_abc_find, abc, (["value"], {}), (["--member"], {"action": "store_true", "help": "value is a member name"}))
    add("abc-refs", cmd_abc_refs, abc, (["--method"], {"type": int, "required": True}))
    add("abc-strings", cmd_abc_strings, abc, (["pattern"], {}))
    add("movement-verify", cmd_movement_verify, abc)
    add("commands-verify", cmd_commands_verify, abc)
    add("stats-verify", cmd_stats_verify, abc)
    add("legend-stats", cmd_legend_stats, (["--hero"], {"help": "HeroName as in RuneTypes.xml"}),
        (["--stance"], {"type": int, "default": 0}), (["--swz"], {"help": "swz-dump folder (default work/swz)"}))
    add("anm-info", cmd_anm_info, game, (["--file"], {}), (["--anim"], {"help": "animation name to print"}),
        (["--verbose"], {"action": "store_true"}))
    add("collision-verify", cmd_collision_verify, abc)
    add("hit-detection-verify", cmd_hit_detection_verify, abc)
    add("swz-key", cmd_swz_key, game, (["--suffix"], {"type": int, "help": "brute-force fallback, e.g. 1100 for patch 11.00"}))
    add("swz-dump", cmd_swz_dump, game, (["--key"], {"type": int, "required": True}))
    add("swf-info", cmd_swf_info, (["file"], {}), (["--limit"], {"type": int, "default": 30}))
    seed = _bounded_int(-(1 << 31), (1 << 32) - 1)
    add("prng", cmd_prng, (["seed"], {"type": seed, "help": "replay random_seed, signed i32 or uint32 (0x.. ok)"}),
        (["--count"], {"type": _bounded_int(1, 100000), "default": 8}),
        (["--skip"], {"type": _bounded_int(0, 10_000_000), "default": 0, "help": "draws to discard first"}),
        (["--state"], {"action": "store_true", "help": "print (index, 16 words) after --skip draws"}),
        (["--json"], {"action": "store_true"}))
    seeds = (["--seeds"], {"type": lambda t: [_bounded_int(0, (1 << 32) - 1)(x) for x in t.split(",")],
                           "default": [0, 1, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, 123456789]})
    add("prng-verify", cmd_prng_verify, abc, seeds, (["--draws"], {"type": _bounded_int(1, 100000), "default": 256}))
    add("prng-order-verify", cmd_prng_order_verify, abc)
    add("step-verify", cmd_step_verify, abc)
    add("ko-verify", cmd_ko_verify, abc)
    add("ko-oracle", cmd_ko_oracle, (["file"], {"nargs": "?"}), (["--dir"], {"help": "replay folder: aggregate counts only"}))
    add("input-buffer-verify", cmd_input_buffer_verify, abc)
    add("knockback-verify", cmd_knockback_verify, abc)
    add("ko-gap-check", cmd_ko_gap_check, (["--dir"], {"required": True, "help": "folder of .replay files"}),
        (["--swz"], {"help": "swz-dump folder (default work/swz)"}))
    add("smoke-fall", cmd_smoke_fall, (["--swz"], {"help": "swz-dump folder (default work/swz)"}),
        (["--static-only"], {"action": "store_true", "help": "leave the moving platforms' lines out"}))
    add("power-columns", cmd_power_columns, abc, (["--markdown"], {"action": "store_true"}))
    add("replay", cmd_replay, (["file"], {}), (["--limit"], {"type": int, "default": 20}), (["--json"], {"action": "store_true"}))
    add("render-summary", cmd_render_summary, (["file"], {}), (["--out"], {"help": "SVG path (default work/render/)"}))
    add("corpus", cmd_corpus, (["--dir"], {"default": DEFAULT_REPLAYS, "help": "replay folder (env BRAWLHALLA_REPLAYS)"}),
        (["--limit"], {"type": int, "default": 0}))
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
