"""Brawlhalla .swz archives: decryption and key search.

Format (from bhswz-rs, allhailcheese, MIT; re-implemented here, stdlib only):
  header : u32 BE key checksum, u32 BE seed
  PRNG   : WELL512 seeded with (key ^ seed)
  entries: u32 compressed size ^ rng, u32 decompressed size ^ rng, u32 checksum,
           then `compressed size` bytes, XORed byte by byte, then zlib.
"""
import os
import re
import struct
import zlib

M32 = 0xFFFFFFFF


class SwzRandom:
    """WELL512 generator, as used by the game for .swz files."""

    def __init__(self, seed):
        state = [seed & M32]
        for i in range(1, 16):
            prev = state[-1]
            state.append((((prev ^ (prev >> 30)) * 0x6C078965) + i) & M32)
        self.state = state
        self.index = 0

    def next(self):
        st, i = self.state, self.index
        self.index = n = (i + 15) % 16
        a1 = st[i]
        b1 = st[(i + 13) % 16]
        c = (a1 ^ (a1 << 16) ^ b1 ^ (b1 << 15)) & M32
        b2 = st[(i + 9) % 16]
        b3 = (b2 ^ (b2 >> 11)) & M32
        a2 = (b3 ^ c) & M32
        d = (a2 ^ ((a2 << 5) & 0xDA442D24)) & M32
        a3 = st[n]
        result = (a3 ^ (a3 << 2) ^ (b3 << 28) ^ c ^ (c << 18) ^ d) & M32
        st[i] = a2
        st[n] = result
        return result


def _rotr(v, r):
    return ((v >> r) | (v << (32 - r))) & M32


def check_key(data, key):
    """Return the PRNG positioned after the header if `key` opens `data`, else None."""
    checksum, seed = struct.unpack(">II", data[:8])
    rng = SwzRandom(key ^ seed)
    calc = 0x2DF4A1CD
    for _ in range(key % 31 + 5):
        calc ^= rng.next()
    return rng if calc == checksum else None


def iter_entries(data, key, verify=True):
    """Yield the decompressed bytes of each file stored in a .swz archive."""
    rng = check_key(data, key)
    if rng is None:
        raise ValueError("wrong .swz key")
    p = 8
    while p < len(data):
        csize = struct.unpack(">I", data[p:p + 4])[0] ^ rng.next()
        dsize = struct.unpack(">I", data[p + 4:p + 8])[0] ^ rng.next()
        checksum = struct.unpack(">I", data[p + 8:p + 12])[0]
        p += 12
        buf = bytearray(data[p:p + csize])
        p += csize
        calc = rng.next()
        for i in range(len(buf)):
            buf[i] ^= (rng.next() >> (i % 16)) & 0xFF
            if verify:
                calc = _rotr(calc, i % 7 + 1) ^ buf[i]
        if verify and calc != checksum:
            raise ValueError("entry checksum mismatch")
        out = zlib.decompress(bytes(buf))
        if len(out) != dsize:
            raise ValueError("decompressed size mismatch")
        yield out


def entry_name(content):
    """Name of an entry, the way the game identifies it: XML root tag (+ LevelName) or first CSV line."""
    head = content[:400]
    if head.lstrip()[:1] == b"<":
        tag = re.search(rb"<(\w+)", head).group(1).decode()
        level = re.search(rb'LevelName="([^"]+)"', head) if tag == "LevelDesc" else None
        name = f"{tag}_{level.group(1).decode()}" if level else tag
        ext = ".xml"
    else:
        name = head.split(b"\n", 1)[0].strip().decode("latin-1")
        ext = ".csv"
    return re.sub(r"[^\w.-]", "_", name) + ext


def dump(path, key, out_dir):
    """Decrypt one archive into out_dir. Returns the list of written file names."""
    data = open(path, "rb").read()
    os.makedirs(out_dir, exist_ok=True)
    names = []
    for content in iter_entries(data, key):
        name = entry_name(content)
        while name in names:
            name = "_" + name
        with open(os.path.join(out_dir, name), "wb") as f:
            f.write(content)
        names.append(name)
    return names


def find_key(data, candidates=(), patch_suffix=None):
    """Find the key of one archive.

    1. try `candidates` (e.g. every uint of the game's ABC constant pool: the key is pushed as a
       uint literal before ANE_RawData.Init);
    2. else brute-force keys ending with `patch_suffix` (e.g. 1100 for patch 11.00).
    """
    for k in candidates:
        if check_key(data, k):
            return k
    if patch_suffix is not None:
        mult = 10 ** len(str(patch_suffix))
        for prefix in range(0, (M32 // mult) + 1):
            k = prefix * mult + patch_suffix
            if k > M32:
                break
            if check_key(data, k):
                return k
    return None
