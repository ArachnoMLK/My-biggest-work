"""Brawlhalla .replay reader (formats 261-271, patches 10.02 to 11.00).

Ported from the WaveDash plugin `brawlhalla-replays` (itself based on BrawlhallaReplayLibrary,
allhailcheese, MIT, and brawlhalla-replay-reader, itselectroz, MIT).

Layout: zlib -> XOR with a 64-byte key -> MSB-first bit stream of typed objects (4-bit type).
Unlike the plugin, this reader keeps every input record: it is the raw material of a simulator.
"""
import zlib

KEY = bytes([107, 16, 222, 60, 68, 75, 209, 70, 160, 16, 82, 193, 178, 49, 211, 106, 251, 172, 17, 222, 6, 104,
             8, 120, 140, 213, 179, 249, 106, 64, 214, 19, 12, 174, 157, 197, 212, 107, 84, 114, 252, 87, 93, 26,
             6, 115, 194, 81, 75, 176, 201, 140, 120, 4, 17, 122, 239, 116, 62, 70, 57, 160, 199, 166])
PATCHES = {261: "10.02", 262: "10.03", 263: "10.04", 264: "10.05", 265: "10.06", 266: "10.07",
           267: "10.08", 268: "10.09", 269: "10.10", 270: "10.11", 271: "11.00"}
# Input bits, as named by BrawlhallaReplayLibrary (ReplayInputFlags). Bit 0 = lowest bit of the 14-bit field.
INPUT_BITS = ["AimUp", "Drop", "MoveLeft", "MoveRight", "Jump", "PrioritiseNeutralOverSide", "HeavyAttack",
              "LightAttack", "DodgeDash", "PickUpThrow", "TauntUp", "TauntRight", "TauntDown", "TauntLeft"]
# The 15 u32 of the game settings (ReplayGameSettings).
SETTINGS = ["flags", "max_players", "duration", "round_duration", "starting_lives", "scoring_type_id",
            "score_to_win", "game_speed", "damage_multiplier", "level_set_id", "item_spawn_ruleset_id",
            "weapon_spawn_rate_id", "gadget_spawn_rate_id", "custom_gadget_selection", "variation"]


class FormatError(Exception):
    pass


class BitReader:
    def __init__(self, data):
        self.b = data
        self.size = len(data) * 8
        self.p = 0

    def bits(self, k):
        if self.p + k > self.size:
            raise EOFError("end of replay data")
        first, last = self.p >> 3, (self.p + k + 7) >> 3
        chunk = int.from_bytes(self.b[first:last], "big")
        v = (chunk >> ((last << 3) - self.p - k)) & ((1 << k) - 1)
        self.p += k
        return v

    def bit(self):
        return self.bits(1)

    def u32(self):
        return self.bits(32)

    def i32(self):
        v = self.bits(32)
        return v - (1 << 32) if v & 0x80000000 else v

    def str(self):
        n = self.bits(16)
        return bytes(self.bits(8) for _ in range(n)).decode("utf-8", "replace")


def _round_even(x):
    return round(x)  # Python rounds half to even, like C# Math.Round


def _add(*values):
    s = 0
    for v in values:
        s = (s + v) % 4294967296
    return s


def decode_bytes(raw):
    data = bytearray(zlib.decompress(raw))
    for i in range(len(data)):
        data[i] ^= KEY[i & 63]
    return bytes(data)


def parse(raw):
    """Parse the bytes of a .replay file into a dict (inputs included)."""
    r = BitReader(decode_bytes(raw))
    rep = {"version": r.u32(), "objects": [], "entities": [], "inputs": {}, "kos": [], "faces": []}
    rep["patch"] = PATCHES.get(rep["version"])
    while True:
        t = r.bits(4)
        rep["objects"].append(t)
        if t == 3:  # header
            rep["random_seed"] = r.u32()
            rep["playlist_id"] = r.u32()
            rep["playlist"] = r.str() if rep["playlist_id"] else ""
            rep["online"] = bool(r.bit())
        elif t == 4:  # game data
            rep["settings"] = dict(zip(SETTINGS, (r.u32() for _ in range(15))))
            rep["level_id"] = r.u32()
            hero_count = r.bits(16)
            if not 1 <= hero_count <= 5:
                raise FormatError("invalid legend count")
            total = 0
            while r.bit():
                e = {"id": r.i32()}
                if rep["version"] >= 268:
                    e["player_id"] = r.u32()  # added in format 268 (patch 10.09); 0 for bots
                e["name"] = r.str()
                cos = [r.u32() for _ in range(6)]
                e["color"], e["spawnbot"], e["companion"], e["emitter"], e["trail"], e["theme"] = cos
                cs = _add(cos[0] * 5, cos[1] * 93, cos[3] * 97, cos[5] * 53)
                e["taunts"] = [r.u32() for _ in range(8)]
                for i, v in enumerate(e["taunts"]):
                    cs = _add(cs, v * (13 + i))
                e["win_taunt"], e["lose_taunt"] = r.bits(16), r.bits(16)
                cs = _add(cs, e["win_taunt"] * 37, e["lose_taunt"] * 41)
                i = 0
                while r.bit():
                    cs = _add(cs, bin(r.u32()).count("1") * (11 + i))
                    i += 1
                e["avatar"] = r.bits(16)
                e["team"] = r.i32()
                e["connection_time"] = r.i32()
                cs = _add(cs, (e["team"] % 4294967296) * 43)
                e["heroes"] = []
                for i in range(hero_count):
                    h = {"hero_id": r.u32(), "costume": r.u32(), "stance": r.u32()}
                    top, skin2, morph, skin1 = r.bit(), r.bits(15), r.bit(), r.bits(15)
                    h["weapon_skins"] = (top, skin2, morph, skin1)
                    packed = ((top * 32768 + skin2) * 65536 + skin1 + morph * 32768) % 4294967296
                    cs = _add(cs, h["hero_id"] * (17 + i), h["costume"] * (7 + i), h["stance"] * (3 + i), packed * (2 + i))
                    e["heroes"].append(h)
                e["bot"] = bool(r.bit())
                if r.bit():
                    hc = [r.u32(), r.u32(), r.u32()]
                    e["handicap"] = hc
                    cs = _add(cs, hc[0] * 31, _round_even(hc[1] / 10) * 3, _round_even(hc[2] / 10) * 23)
                else:
                    cs = _add(cs, 29)
                total = _add(total, cs)
                rep["entities"].append(e)
            if r.u32() != _add(total, rep["level_id"] * 47) % 173:
                raise FormatError(f"game data checksum mismatch (version {rep['version']})")
        elif t == 6:  # results; written once per round in some modes (up to 11 seen), the last one is final
            res = {"length_ms": r.u32()}
            scores = {}
            if r.bit():
                while r.bit():
                    eid, s = r.bits(5), r.bits(16)
                    scores[eid] = s - 65536 if s > 32767 else s
            res["scores"] = scores
            res["end_of_match_fanfare"] = r.u32()
            rep.setdefault("results", []).append(res)
            rep.update(res)
        elif t in (5, 7):  # KnockoutFaces (5) and other Faces (7): (entity, timestamp ms).
            # Seen: in score modes (e.g. scoring type 39) list 5 is empty and list 7 holds one event per point.
            events = []
            while r.bit():
                events.append((r.bits(5), r.i32()))
            rep["kos" if t == 5 else "faces"] = events
        elif t == 1:  # inputs: (timestamp ms, 14-bit key state) at every change, per entity
            while r.bit():
                who, count = r.bits(5), r.i32()
                if not 0 <= count <= 2_000_000:
                    raise FormatError("invalid input count")
                lst = rep["inputs"].setdefault(who, [])
                for _ in range(count):
                    ts = r.u32()
                    flags = r.bits(14) if r.bit() else 0
                    lst.append((ts, flags))
        elif t == 2:  # end
            break
        else:
            raise FormatError(f"unknown object type {t}")
    return rep


def describe_flags(flags):
    return "+".join(n for i, n in enumerate(INPUT_BITS) if flags >> i & 1) or "-"
