"""Minimal SWF container reader: header, tag list, DoABC blocks, exported symbols.

Enough to locate code (DoABC) and asset symbols in BrawlhallaAir.swf, Gfx_*.swf, Bones_*.swf,
UI_*.swf and SFX_*.swf. Shapes and sprites are not decoded here (see SwiffCheese / WallyAnmRenderer).
"""
import struct
import zlib

TAG_NAMES = {
    0: "End", 1: "ShowFrame", 2: "DefineShape", 9: "SetBackgroundColor", 14: "DefineSound",
    20: "DefineBitsLossless", 21: "DefineBitsJPEG2", 22: "DefineShape2", 26: "PlaceObject2",
    28: "RemoveObject2", 32: "DefineShape3", 35: "DefineBitsJPEG3", 36: "DefineBitsLossless2",
    39: "DefineSprite", 43: "FrameLabel", 56: "ExportAssets", 65: "ScriptLimits",
    69: "FileAttributes", 70: "PlaceObject3", 72: "DoABC", 76: "SymbolClass", 77: "Metadata",
    82: "DoABC2", 83: "DefineShape4", 84: "DefineMorphShape2", 86: "DefineSceneAndFrameLabelData",
    87: "DefineBinaryData", 88: "DefineFontName", 91: "DefineFont4", 255: "EnableTelemetry",
}


def _cstring(buf, p):
    end = buf.index(b"\0", p)
    return buf[p:end].decode("utf-8", "replace"), end + 1


class Swf:
    def __init__(self, data):
        sig = data[:3]
        self.version = data[3]
        self.file_length = struct.unpack("<I", data[4:8])[0]
        if sig == b"FWS":
            body = data[8:]
        elif sig == b"CWS":
            body = zlib.decompress(data[8:])
        elif sig == b"ZWS":
            import lzma
            props = data[12:17]
            # SWF LZMA: rebuild an .lzma "alone" header (props + unknown size)
            body = lzma.decompress(props + b"\xff" * 8 + data[17:], format=lzma.FORMAT_ALONE)
        else:
            raise ValueError("not a SWF file")
        self.compression = sig.decode()
        nbits = body[0] >> 3
        p = (5 + 4 * nbits + 7) // 8
        self.frame_rate = body[p + 1] + body[p] / 256
        self.frame_count = struct.unpack("<H", body[p + 2:p + 4])[0]
        p += 4
        self.tags = []  # (code, offset, length) into self.body
        self.body = body
        while p < len(body):
            head = struct.unpack("<H", body[p:p + 2])[0]
            p += 2
            code, length = head >> 6, head & 0x3F
            if length == 0x3F:
                length = struct.unpack("<I", body[p:p + 4])[0]
                p += 4
            self.tags.append((code, p, length))
            p += length
            if code == 0:
                break

    def tag_data(self, tag):
        _, off, length = tag
        return self.body[off:off + length]

    def abc_blocks(self):
        """List of (name, bytes) for each DoABC / DoABC2 tag."""
        out = []
        for tag in self.tags:
            data = self.tag_data(tag)
            if tag[0] == 82:
                name, p = _cstring(data, 4)  # u32 flags, then name
                out.append((name, data[p:]))
            elif tag[0] == 72:
                out.append(("", data))
        return out

    def symbols(self):
        """SymbolClass + ExportAssets: list of (character id, class or export name)."""
        out = []
        for tag in self.tags:
            if tag[0] not in (76, 56):
                continue
            data = self.tag_data(tag)
            count = struct.unpack("<H", data[:2])[0]
            p = 2
            for _ in range(count):
                cid = struct.unpack("<H", data[p:p + 2])[0]
                name, p = _cstring(data, p + 2)
                out.append((cid, name))
        return out

    def tag_counts(self):
        counts = {}
        for code, _, _ in self.tags:
            key = TAG_NAMES.get(code, str(code))
            counts[key] = counts.get(key, 0) + 1
        return counts
