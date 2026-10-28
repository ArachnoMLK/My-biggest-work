"""AVM2 ABC (ActionScript Byte Code) parser and disassembler, stdlib only.

Reference: "ActionScript Virtual Machine 2 Overview" (Adobe, 2007). The game code is Haxe compiled
to AS3, then obfuscated: most class and member names look like `_-y2E` and change every patch,
so tools here work on structure (constants, call graph, method ids) rather than names.
"""
import struct

# ---------------------------------------------------------------- opcodes
# operand kinds: u = u30, s = s24 branch offset, b = signed byte, B = unsigned byte, L = lookupswitch
OPS = {
    0x01: ("bkpt", ""), 0x02: ("nop", ""), 0x03: ("throw", ""), 0x04: ("getsuper", "u"),
    0x05: ("setsuper", "u"), 0x06: ("dxns", "u"), 0x07: ("dxnslate", ""), 0x08: ("kill", "u"),
    0x09: ("label", ""), 0x0C: ("ifnlt", "s"), 0x0D: ("ifnle", "s"), 0x0E: ("ifngt", "s"),
    0x0F: ("ifnge", "s"), 0x10: ("jump", "s"), 0x11: ("iftrue", "s"), 0x12: ("iffalse", "s"),
    0x13: ("ifeq", "s"), 0x14: ("ifne", "s"), 0x15: ("iflt", "s"), 0x16: ("ifle", "s"),
    0x17: ("ifgt", "s"), 0x18: ("ifge", "s"), 0x19: ("ifstricteq", "s"), 0x1A: ("ifstrictne", "s"),
    0x1B: ("lookupswitch", "L"), 0x1C: ("pushwith", ""), 0x1D: ("popscope", ""),
    0x1E: ("nextname", ""), 0x1F: ("hasnext", ""), 0x20: ("pushnull", ""),
    0x21: ("pushundefined", ""), 0x23: ("nextvalue", ""), 0x24: ("pushbyte", "b"),
    0x25: ("pushshort", "u"), 0x26: ("pushtrue", ""), 0x27: ("pushfalse", ""),
    0x28: ("pushnan", ""), 0x29: ("pop", ""), 0x2A: ("dup", ""), 0x2B: ("swap", ""),
    0x2C: ("pushstring", "u"), 0x2D: ("pushint", "u"), 0x2E: ("pushuint", "u"),
    0x2F: ("pushdouble", "u"), 0x30: ("pushscope", ""), 0x31: ("pushnamespace", "u"),
    0x32: ("hasnext2", "uu"), 0x35: ("li8", ""), 0x36: ("li16", ""), 0x37: ("li32", ""),
    0x38: ("lf32", ""), 0x39: ("lf64", ""), 0x3A: ("si8", ""), 0x3B: ("si16", ""),
    0x3C: ("si32", ""), 0x3D: ("sf32", ""), 0x3E: ("sf64", ""), 0x40: ("newfunction", "u"),
    0x41: ("call", "u"), 0x42: ("construct", "u"), 0x43: ("callmethod", "uu"),
    0x44: ("callstatic", "uu"), 0x45: ("callsuper", "uu"), 0x46: ("callproperty", "uu"),
    0x47: ("returnvoid", ""), 0x48: ("returnvalue", ""), 0x49: ("constructsuper", "u"),
    0x4A: ("constructprop", "uu"), 0x4C: ("callproplex", "uu"), 0x4E: ("callsupervoid", "uu"),
    0x4F: ("callpropvoid", "uu"), 0x50: ("sxi1", ""), 0x51: ("sxi8", ""), 0x52: ("sxi16", ""),
    0x53: ("applytype", "u"), 0x55: ("newobject", "u"), 0x56: ("newarray", "u"),
    0x57: ("newactivation", ""), 0x58: ("newclass", "u"), 0x59: ("getdescendants", "u"),
    0x5A: ("newcatch", "u"), 0x5D: ("findpropstrict", "u"), 0x5E: ("findproperty", "u"),
    0x5F: ("finddef", "u"), 0x60: ("getlex", "u"), 0x61: ("setproperty", "u"),
    0x62: ("getlocal", "u"), 0x63: ("setlocal", "u"), 0x64: ("getglobalscope", ""),
    0x65: ("getscopeobject", "B"), 0x66: ("getproperty", "u"), 0x67: ("getouterscope", "u"),
    0x68: ("initproperty", "u"), 0x6A: ("deleteproperty", "u"), 0x6C: ("getslot", "u"),
    0x6D: ("setslot", "u"), 0x6E: ("getglobalslot", "u"), 0x6F: ("setglobalslot", "u"),
    0x70: ("convert_s", ""), 0x71: ("esc_xelem", ""), 0x72: ("esc_xattr", ""),
    0x73: ("convert_i", ""), 0x74: ("convert_u", ""), 0x75: ("convert_d", ""),
    0x76: ("convert_b", ""), 0x77: ("convert_o", ""), 0x78: ("checkfilter", ""),
    0x80: ("coerce", "u"), 0x81: ("coerce_b", ""), 0x82: ("coerce_a", ""), 0x83: ("coerce_i", ""),
    0x84: ("coerce_d", ""), 0x85: ("coerce_s", ""), 0x86: ("astype", "u"), 0x87: ("astypelate", ""),
    0x88: ("coerce_u", ""), 0x89: ("coerce_o", ""), 0x90: ("negate", ""), 0x91: ("increment", ""),
    0x92: ("inclocal", "u"), 0x93: ("decrement", ""), 0x94: ("declocal", "u"), 0x95: ("typeof", ""),
    0x96: ("not", ""), 0x97: ("bitnot", ""), 0xA0: ("add", ""), 0xA1: ("subtract", ""),
    0xA2: ("multiply", ""), 0xA3: ("divide", ""), 0xA4: ("modulo", ""), 0xA5: ("lshift", ""),
    0xA6: ("rshift", ""), 0xA7: ("urshift", ""), 0xA8: ("bitand", ""), 0xA9: ("bitor", ""),
    0xAA: ("bitxor", ""), 0xAB: ("equals", ""), 0xAC: ("strictequals", ""), 0xAD: ("lessthan", ""),
    0xAE: ("lessequals", ""), 0xAF: ("greaterthan", ""), 0xB0: ("greaterequals", ""),
    0xB1: ("instanceof", ""), 0xB2: ("istype", "u"), 0xB3: ("istypelate", ""), 0xB4: ("in", ""),
    0xC0: ("increment_i", ""), 0xC1: ("decrement_i", ""), 0xC2: ("inclocal_i", "u"),
    0xC3: ("declocal_i", "u"), 0xC4: ("negate_i", ""), 0xC5: ("add_i", ""),
    0xC6: ("subtract_i", ""), 0xC7: ("multiply_i", ""), 0xD0: ("getlocal_0", ""),
    0xD1: ("getlocal_1", ""), 0xD2: ("getlocal_2", ""), 0xD3: ("getlocal_3", ""),
    0xD4: ("setlocal_0", ""), 0xD5: ("setlocal_1", ""), 0xD6: ("setlocal_2", ""),
    0xD7: ("setlocal_3", ""), 0xEF: ("debug", "BuBu"), 0xF0: ("debugline", "u"),
    0xF1: ("debugfile", "u"), 0xF2: ("bkptline", "u"), 0xF3: ("timestamp", ""),
}
# opcodes whose first u30 operand is a multiname index
MULTINAME_OPS = {
    "getsuper", "setsuper", "callsuper", "callproperty", "constructprop", "callproplex",
    "callsupervoid", "callpropvoid", "getdescendants", "findpropstrict", "findproperty",
    "finddef", "getlex", "setproperty", "getproperty", "initproperty", "deleteproperty",
    "coerce", "astype", "istype", "newcatch",
}


class Reader:
    def __init__(self, data, pos=0):
        self.d = data
        self.p = pos

    def u8(self):
        v = self.d[self.p]
        self.p += 1
        return v

    def u16(self):
        v = struct.unpack_from("<H", self.d, self.p)[0]
        self.p += 2
        return v

    def s24(self):
        b = self.d[self.p:self.p + 3]
        self.p += 3
        v = b[0] | (b[1] << 8) | (b[2] << 16)
        return v - (1 << 24) if v & 0x800000 else v

    def u30(self):
        result = shift = 0
        for _ in range(5):
            b = self.d[self.p]
            self.p += 1
            result |= (b & 0x7F) << shift
            if not b & 0x80:
                break
            shift += 7
        return result & 0xFFFFFFFF

    def s32(self):
        v = self.u30()
        return v - (1 << 32) if v & 0x80000000 else v

    def d64(self):
        v = struct.unpack_from("<d", self.d, self.p)[0]
        self.p += 8
        return v

    def bytes(self, n):
        v = self.d[self.p:self.p + n]
        self.p += n
        return v


# ---------------------------------------------------------------- file structure
class Abc:
    def __init__(self, data):
        r = Reader(data)
        self.minor, self.major = r.u16(), r.u16()
        self.ints = [0] + [r.s32() for _ in range(max(r.u30() - 1, 0))]
        self.uints = [0] + [r.u30() for _ in range(max(r.u30() - 1, 0))]
        self.doubles = [float("nan")] + [r.d64() for _ in range(max(r.u30() - 1, 0))]
        self.strings = [None]
        for _ in range(max(r.u30() - 1, 0)):
            self.strings.append(r.bytes(r.u30()).decode("utf-8", "replace"))
        self.namespaces = [(0, 0)] + [(r.u8(), r.u30()) for _ in range(max(r.u30() - 1, 0))]
        self.ns_sets = [[]]
        for _ in range(max(r.u30() - 1, 0)):
            self.ns_sets.append([r.u30() for _ in range(r.u30())])
        self.multinames = [None]
        for _ in range(max(r.u30() - 1, 0)):
            self.multinames.append(self._multiname(r))
        self.methods = [self._method(r) for _ in range(r.u30())]
        self.metadata = []
        for _ in range(r.u30()):
            name = r.u30()
            n = r.u30()
            items = [r.u30() for _ in range(2 * n)]
            self.metadata.append((name, items))
        class_count = r.u30()
        self.instances = [self._instance(r) for _ in range(class_count)]
        self.classes = [{"cinit": r.u30(), "traits": self._traits(r)} for _ in range(class_count)]
        self.scripts = [{"init": r.u30(), "traits": self._traits(r)} for _ in range(r.u30())]
        self.bodies = [self._body(r) for _ in range(r.u30())]
        self.body_of = {b["method"]: i for i, b in enumerate(self.bodies)}

    @staticmethod
    def _multiname(r):
        kind = r.u8()
        if kind in (0x07, 0x0D):
            return (kind, r.u30(), r.u30())  # ns, name
        if kind in (0x0F, 0x10):
            return (kind, 0, r.u30())
        if kind in (0x11, 0x12):
            return (kind, 0, 0)
        if kind in (0x09, 0x0E):
            name = r.u30()
            return (kind, r.u30(), name)  # ns_set, name
        if kind in (0x1B, 0x1C):
            return (kind, r.u30(), 0)
        if kind == 0x1D:
            name = r.u30()
            return (kind, name, [r.u30() for _ in range(r.u30())])
        raise ValueError(f"unknown multiname kind {kind:#x}")

    @staticmethod
    def _method(r):
        pc = r.u30()
        m = {"ret": r.u30(), "params": [r.u30() for _ in range(pc)], "name": r.u30(), "flags": r.u8()}
        if m["flags"] & 0x08:
            m["optional"] = [(r.u30(), r.u8()) for _ in range(r.u30())]
        if m["flags"] & 0x80:
            m["param_names"] = [r.u30() for _ in range(pc)]
        return m

    def _instance(self, r):
        inst = {"name": r.u30(), "super": r.u30(), "flags": r.u8()}
        if inst["flags"] & 0x08:
            inst["protected_ns"] = r.u30()
        inst["interfaces"] = [r.u30() for _ in range(r.u30())]
        inst["iinit"] = r.u30()
        inst["traits"] = self._traits(r)
        return inst

    @staticmethod
    def _traits(r):
        out = []
        for _ in range(r.u30()):
            t = {"name": r.u30()}
            kind = r.u8()
            t["kind"], attr = kind & 0x0F, kind >> 4
            if t["kind"] in (0, 6):  # slot / const
                t["slot"], t["type"], t["vindex"] = r.u30(), r.u30(), r.u30()
                if t["vindex"]:
                    t["vkind"] = r.u8()
            elif t["kind"] in (1, 2, 3):  # method / getter / setter
                t["disp"], t["method"] = r.u30(), r.u30()
            elif t["kind"] == 4:
                t["slot"], t["class"] = r.u30(), r.u30()
            elif t["kind"] == 5:
                t["slot"], t["method"] = r.u30(), r.u30()
            else:
                raise ValueError(f"unknown trait kind {t['kind']}")
            if attr & 0x04:
                t["metadata"] = [r.u30() for _ in range(r.u30())]
            out.append(t)
        return out

    def _body(self, r):
        b = {"method": r.u30(), "max_stack": r.u30(), "locals": r.u30(),
             "init_scope": r.u30(), "max_scope": r.u30()}
        b["code"] = r.bytes(r.u30())
        b["exceptions"] = [tuple(r.u30() for _ in range(5)) for _ in range(r.u30())]
        b["traits"] = self._traits(r)
        return b

    # ------------------------------------------------------------ names
    def ns_name(self, i):
        kind, name = self.namespaces[i]
        return self.strings[name] or ""

    def mn_name(self, i, full=False):
        if not i or i >= len(self.multinames):
            return "*"
        kind, a, name = self.multinames[i]
        if kind == 0x1D:
            return f"{self.mn_name(a)}.<{','.join(self.mn_name(x) for x in name)}>"
        n = self.strings[name] if name else "[rt]"
        if full and kind in (0x07, 0x0D) and self.ns_name(a):
            return f"{self.ns_name(a)}::{n}"
        return n

    def class_name(self, ci):
        return self.mn_name(self.instances[ci]["name"], full=True)

    def method_owner(self):
        """Map method id -> 'Class.member' (instance, static, init) for readable listings."""
        owner = {}
        for ci, inst in enumerate(self.instances):
            cname = self.class_name(ci)
            owner[inst["iinit"]] = f"{cname}.<init>"
            owner[self.classes[ci]["cinit"]] = f"{cname}.<cinit>"
            for t in inst["traits"]:
                if "method" in t and t["kind"] in (1, 2, 3):
                    owner[t["method"]] = f"{cname}.{self.mn_name(t['name'])}"
            for t in self.classes[ci]["traits"]:
                if "method" in t and t["kind"] in (1, 2, 3):
                    owner[t["method"]] = f"{cname}.static.{self.mn_name(t['name'])}"
        for si, s in enumerate(self.scripts):
            owner.setdefault(s["init"], f"script{si}.<init>")
            for t in s["traits"]:
                if t["kind"] in (1, 2, 3, 5) and "method" in t:
                    owner.setdefault(t["method"], f"script{si}.{self.mn_name(t['name'])}")
        return owner


# ---------------------------------------------------------------- code
def decode(code):
    """Decode a method body into a list of (offset, opname, operands). Raises on unknown opcode."""
    r = Reader(code)
    out = []
    while r.p < len(code):
        off = r.p
        op = r.u8()
        if op not in OPS:
            raise ValueError(f"unknown opcode {op:#04x} at {off}")
        name, kinds = OPS[op]
        args = []
        if kinds == "L":
            default = r.s24()
            count = r.u30()
            args = [default] + [r.s24() for _ in range(count + 1)]
        else:
            for k in kinds:
                if k == "u":
                    args.append(r.u30())
                elif k == "s":
                    args.append(r.s24())
                elif k == "b":
                    v = r.u8()
                    args.append(v - 256 if v > 127 else v)
                elif k == "B":
                    args.append(r.u8())
        out.append((off, name, args))
    return out


def branch_targets(ins, code_len):
    """Absolute branch targets; returns (targets, bad) where bad lists out-of-range ones."""
    targets, bad = [], []
    for i, (off, name, args) in enumerate(ins):
        if OPS_KIND.get(name) == "s":
            nxt = ins[i + 1][0] if i + 1 < len(ins) else code_len
            tgt = nxt + args[0]
            (targets if 0 <= tgt <= code_len else bad).append(tgt)
        elif name == "lookupswitch":
            for a in args:
                tgt = off + a
                (targets if 0 <= tgt <= code_len else bad).append(tgt)
    return targets, bad


OPS_KIND = {name: kinds for name, kinds in OPS.values()}


def operand_text(abc, name, args):
    if not args:
        return ""
    a = args[0]
    if name in MULTINAME_OPS:
        rest = f", {args[1]}" if len(args) > 1 else ""
        return f"{abc.mn_name(a, full=True)}{rest}"
    if name in ("pushstring", "dxns", "debugfile"):
        return repr(abc.strings[a])
    if name == "pushint":
        return str(abc.ints[a])
    if name == "pushuint":
        return str(abc.uints[a])
    if name == "pushdouble":
        return repr(abc.doubles[a])
    if name in ("newclass",):
        return abc.class_name(a)
    if name in ("newfunction", "callstatic"):
        return f"method#{a}"
    return ", ".join(str(x) for x in args)


def disassemble(abc, method_id):
    bi = abc.body_of.get(method_id)
    if bi is None:
        return "  (no body)"
    body = abc.bodies[bi]
    ins = decode(body["code"])
    lines = []
    for i, (off, name, args) in enumerate(ins):
        txt = operand_text(abc, name, args)
        if OPS_KIND.get(name) == "s":
            nxt = ins[i + 1][0] if i + 1 < len(ins) else len(body["code"])
            txt = f"-> {nxt + args[0]}"
        elif name == "lookupswitch":
            txt = "-> " + ", ".join(str(off + a) for a in args)
        lines.append(f"  {off:6d}  {name:<16} {txt}")
    return "\n".join(lines)


def validate(abc):
    """Decode every method body and check branch targets. Returns a report dict."""
    report = {"bodies": len(abc.bodies), "decoded": 0, "errors": [], "bad_branches": 0}
    for bi, body in enumerate(abc.bodies):
        try:
            ins = decode(body["code"])
        except ValueError as e:
            report["errors"].append((body["method"], str(e)))
            continue
        report["decoded"] += 1
        _, bad = branch_targets(ins, len(body["code"]))
        report["bad_branches"] += len(bad)
    return report


def find_constant_uses(abc, value):
    """Method ids whose code pushes `value` (int, uint, double or string)."""
    hits = []
    for body in abc.bodies:
        try:
            ins = decode(body["code"])
        except ValueError:
            continue
        for _, name, args in ins:
            v = None
            if name == "pushbyte" or name == "pushshort":
                v = args[0]
            elif name == "pushint":
                v = abc.ints[args[0]]
            elif name == "pushuint":
                v = abc.uints[args[0]]
            elif name == "pushdouble":
                v = abc.doubles[args[0]]
            elif name == "pushstring":
                v = abc.strings[args[0]]
            if v == value and (type(v) is type(value) or isinstance(value, (int, float)) and isinstance(v, (int, float))):
                hits.append(body["method"])
                break
    return hits


def callers_of(abc, member_name):
    """Method ids that reference a property/method name (call, get, set...)."""
    targets = {i for i, mn in enumerate(abc.multinames) if mn and mn[0] != 0x1D and mn[2] and abc.strings[mn[2]] == member_name}
    hits = []
    for body in abc.bodies:
        try:
            ins = decode(body["code"])
        except ValueError:
            continue
        if any(name in MULTINAME_OPS and args and args[0] in targets for _, name, args in ins):
            hits.append(body["method"])
    return hits


def member_refs(abc, method_id):
    """Summary of one method body: {"members": {(op, name): count}, "constants": {(op, value): count}}.

    Lets you see what a method reads, writes, calls and constructs without reading the whole listing.
    """
    bi = abc.body_of.get(method_id)
    members, constants = {}, {}
    if bi is None:
        return {"members": members, "constants": constants}
    for _, name, args in decode(abc.bodies[bi]["code"]):
        if name in MULTINAME_OPS and args:
            key = (name, abc.mn_name(args[0], full=True))
            members[key] = members.get(key, 0) + 1
        elif name in ("pushbyte", "pushshort", "pushint", "pushuint", "pushdouble", "pushstring"):
            key = (name, operand_text(abc, name, args) if name not in ("pushbyte", "pushshort") else str(args[0]))
            constants[key] = constants.get(key, 0) + 1
    return {"members": members, "constants": constants}
