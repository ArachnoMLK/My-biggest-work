"""Parser for `.anm` animation files (patch 11.00). Stdlib only.

Layout read from the game code (abc 7d308423..., see docs/anm-format.md):
  file      u32 (LE) then zlib; the payload is little-endian (`_-B65._-46O` #169 sets LITTLE_ENDIAN)
  payload   while bool: utf key, set                                   (#169)
  set       utf, utf, u32 count, count x animation                     (`_-U4H._-y1m` #120)
  animation utf name, 6 x u32, u32 n, n x u32, u32 frames_bytes, frames (`_-y1v._-B5I` #147)
  frame     i16 id, point?, point?, i16 bones, bones                   (`_-84Y._-RE` #125)
  point     bool present, then f64 x, f64 y                            (`_-84Y._-72b` #127)
  bone      bool reuse previous frame's bone (then bool keep frame, else i8 frame), else full bone
  full bone i16 id, bool opaque, matrix, translation, frame, alpha     (`_-q55._-kd` #694)
Bones are delta-coded against the previous bone of the same frame (matrix and translation "copy").
"""
import struct
import zlib

# Field order of the six u32 of an animation, as passed to `_-y1v.<init>` #138 (names are [H])
ANIM_FIELDS = ["frame_count", "loop_start", "recovery_start", "free_start", "preview_frame", "base_start"]


class Reader:
    def __init__(self, data):
        self.d, self.p = data, 0

    def take(self, n):
        if self.p + n > len(self.d):
            raise EOFError("truncated .anm")
        b = self.d[self.p:self.p + n]
        self.p += n
        return b

    def unpack(self, fmt):
        return struct.unpack("<" + fmt, self.take(struct.calcsize("<" + fmt)))

    def bool(self):
        return self.take(1)[0] != 0

    def u32(self):
        return self.unpack("I")[0]

    def i16(self):
        return self.unpack("h")[0]

    def utf(self):
        return self.take(self.unpack("H")[0]).decode("utf-8")


def decompress(raw):
    """(declared size, payload): a little-endian u32 then a zlib stream."""
    size = struct.unpack_from("<I", raw)[0]
    return size, zlib.decompress(raw[4:])


def read_bone(r, prev):
    bone_id, opaque = r.i16(), r.bool()
    if r.bool():  # matrix copied from the previous bone
        a, b, c, d = prev["matrix"]
    else:
        identity = symmetric = False
        if r.bool():
            if r.bool():
                identity = True
            else:
                symmetric = True
        if identity:
            a, b, c, d = 1.0, 0.0, 0.0, 1.0
        else:
            a, b = r.unpack("ff")
            c, d = (b, -a) if symmetric else r.unpack("ff")
    x, y = prev["xy"] if r.bool() else r.unpack("ff")
    frame = r.unpack("b")[0] if r.bool() else 1
    alpha = 1.0 if opaque else r.take(1)[0] / 255.0
    return {"id": bone_id, "matrix": (a, b, c, d), "xy": (x, y), "frame": frame, "alpha": alpha}


def read_point(r):
    return r.unpack("dd") if r.bool() else None


def read_frame(r, prev_frame):
    frame = {"id": r.i16(), "point_a": read_point(r), "point_b": read_point(r), "bones": []}
    bones = frame["bones"]
    for i in range(r.i16()):
        if r.bool():
            bone = dict(prev_frame["bones"][i])
            if not r.bool():
                bone["frame"] = r.unpack("b")[0]
        else:
            bone = read_bone(r, bones[i - 1] if i > 0 else None)
        bones.append(bone)
    return frame


def read_animation(r, frames=True):
    anim = {"name": r.utf()}
    anim.update(zip(ANIM_FIELDS, (r.u32() for _ in ANIM_FIELDS)))
    anim["data"] = [r.u32() for _ in range(r.u32())]
    size = r.u32()
    start = r.p
    if frames:
        fr = Reader(r.take(size))
        anim["frames"] = []
        for _ in range(anim["frame_count"]):
            anim["frames"].append(read_frame(fr, anim["frames"][-1] if anim["frames"] else None))
        anim["frames_unread"] = len(fr.d) - fr.p
    else:
        r.take(size)
    anim["frames_bytes"] = r.p - start
    return anim


def parse(raw, frames=True):
    """{key: {"names": (utf, utf), "animations": [...]}} from the bytes of an .anm file."""
    _, data = decompress(raw)
    r, out = Reader(data), {}
    while r.bool():
        key = r.utf()
        names = (r.utf(), r.utf())
        out[key] = {"names": names, "animations": [read_animation(r, frames) for _ in range(r.u32())]}
    if r.p != len(r.d):
        raise ValueError(f"{len(r.d) - r.p} trailing bytes")
    return out
