"""Match PRNG of the game (patch 11.00): class `Random`, a WELL512 generator. Stdlib only.

Evidence and method ids: docs/prng-11.00.md. Summary (patch 11.00, abc 7d308423...):
  seed  `Random._-24O(uint)` #1011: index = 0, s[0] = seed, s[i] = 1812433253 * (s[i-1] ^ s[i-1] >>> 30) + i
  next  `Random._-f4c()`     #1013: one WELL512 step, returns a uint (0 .. 2**32-1)
  state `_-K49`/`_-L3P`      #1010/#1012: index, then s[0..15] (rollback snapshot order)
Range helpers are static methods of class `_-A6B` that take the generator as an argument.

AVM2 integer semantics reproduced here: `bitand/bitxor/lshift` work on int32 (ToInt32), `urshift`
on uint32, `multiply_i/add_i/subtract_i` wrap to int32, `convert_u` is ToUint32, `modulo` is the
IEEE/JavaScript remainder of two doubles (NaN when the divisor is 0, ToInt32(NaN) = 0).

`emulate()` runs the real method bodies of the pinned ABC with a tiny interpreter that only knows
the opcodes these methods use. It exists to check this port against the bytecode
(`bht.py prng-verify`); it is not a general AVM2 virtual machine.
"""
import math

from . import abc as abcmod

M32 = 0xFFFFFFFF
INIT_MULT = 1812433253  # Random static _-Gz (script59.<init> #1014)
TEMPER_MASK = 0xDA442D24  # Random static _-Y5B, pushed as uint 3661901092 in #1013
STATE_WORDS = 16  # Random static _-w1w


def to_u32(v):
    """AVM2 ToUint32 of an int or a double (NaN/inf -> 0)."""
    if isinstance(v, float):
        if v != v or v in (math.inf, -math.inf):
            return 0
        v = int(v)  # truncate toward zero, then wrap
    return v & M32


def to_i32(v):
    """AVM2 ToInt32 of an int or a double (NaN/inf -> 0)."""
    v = to_u32(v)
    return v - (1 << 32) if v & 0x80000000 else v


def js_mod(a, b):
    """AVM2 `modulo`: remainder of two doubles, sign of the dividend, NaN if b is 0."""
    a, b = float(a), float(b)
    if b == 0 or a != a or b != b or a in (math.inf, -math.inf):
        return math.nan
    return math.fmod(a, b)


def seed_from_header(value):
    """The replay header seed is read as a signed i32 (`_-Lg._-a16`) and stored in a uint slot.

    Accepts the signed (-2**31..-1) or unsigned (0..2**32-1) form and returns the uint.
    """
    if not isinstance(value, int) or isinstance(value, bool) or not -(1 << 31) <= value <= M32:
        raise ValueError(f"seed must be an integer in [-2147483648, 4294967295], got {value!r}")
    return value & M32


class Well512:
    """Port of class `Random` (#1008-#1013). `next_u32()` = `_-f4c`, `seed()` = `_-24O`."""

    def __init__(self, seed):
        self.seed(seed)

    def seed(self, seed):
        if not isinstance(seed, int) or isinstance(seed, bool) or not 0 <= seed <= M32:
            raise ValueError(f"seed must be a uint32 (0..4294967295), got {seed!r}")
        s = [seed]
        for i in range(1, STATE_WORDS):
            prev = s[i - 1]
            s.append((INIT_MULT * (prev ^ (prev >> 30)) + i) & M32)
        self.state = s
        self.index = 0

    def next_u32(self):
        s, i = self.state, self.index
        a = s[i]
        c = s[(i + 13) & 15]
        b = (a ^ c ^ (a << 16) ^ (c << 15)) & M32
        c = s[(i + 9) & 15]
        c ^= c >> 11
        a = s[i] = (b ^ c) & M32
        d = (a ^ ((a << 5) & TEMPER_MASK)) & M32
        i = self.index = (i + 15) & 15
        a = s[i]
        s[i] = (a ^ b ^ d ^ (a << 2) ^ (b << 18) ^ (c << 28)) & M32
        return s[i]

    def getstate(self):
        """(index, 16 state words): the order `_-K49` writes them to a rollback snapshot."""
        return self.index, tuple(self.state)

    def setstate(self, state):
        index, words = state
        if (type(index) is not int or not 0 <= index < STATE_WORDS or len(words) != STATE_WORDS
                or any(type(w) is not int or not 0 <= w <= M32 for w in words)):
            raise ValueError("state must be (index 0..15, 16 uint32 words)")
        self.index, self.state = index, list(words)


# ---------------------------------------------------------------- range helpers (class _-A6B)
def uniform(rng, lo, hi):
    """`_-A6B._-o5L(rng, lo, hi)` #1142 -> Number: lo + next/4294967295 * (hi - lo); both ends reachable."""
    return float(lo) + rng.next_u32() / 4294967295.0 * (float(hi) - float(lo))


def range_u32(rng, lo, hi):
    """`_-A6B._-k1J(rng, lo, hi)` #1143 -> uint: next % (hi - lo + 1) + lo, with uint32 wrap-around.

    When hi - lo + 1 wraps to 0 (lo = 0, hi = 4294967295) the remainder is NaN and the result is lo.
    """
    lo, hi = to_u32(lo), to_u32(hi)
    u = rng.next_u32()
    span = to_u32(to_i32(to_u32(to_i32(hi) - to_i32(lo))) + 1)
    return to_u32(to_i32(to_i32(js_mod(u, span)) + to_i32(lo)))


def range_i32(rng, lo, hi):
    """`_-A6B._-KQ(rng, lo, hi)` #1144 -> int: (next & 0x7FFFFFFF) % (hi - lo + 1) + lo, int32 wrap."""
    lo, hi = to_i32(lo), to_i32(hi)
    u = rng.next_u32()
    span = to_i32(to_i32(hi - lo) + 1)
    return to_i32(to_u32(to_i32(to_i32(js_mod(u & 0x7FFFFFFF, span)) + lo)))


def shuffle(rng, items):
    """`_-A6B._-eV(items, rng)` #1068, in place: for i in 0..n-1 swap items[i] and items[next % n].

    Not Fisher-Yates: every position draws over the whole list (n draws for n items).
    """
    n = len(items)
    for i in range(n):
        j = to_u32(js_mod(rng.next_u32(), n))
        items[i], items[j] = items[j], items[i]
    return items


# ---------------------------------------------------------------- bytecode check
class UintVector(list):
    """`Vector.<uint>`: stores coerce with ToUint32, reads past the end raise (RangeError)."""

    def __setitem__(self, k, v):
        list.__setitem__(self, k, to_u32(v))


class Obj(dict):
    """Instance of a class: slots by name, with the declared slot type applied on store."""

    def __init__(self, cls_name, slot_types, methods):
        super().__init__()
        self.cls_name, self.slot_types, self.methods = cls_name, slot_types, methods

    def store(self, name, v):
        self[name] = coerce(self.slot_types.get(name, "*"), v)


def coerce(type_name, v):
    if type_name == "uint":
        return to_u32(v)
    if type_name == "int":
        return to_i32(v)
    if type_name == "Number":
        return float(v)
    return v


def emulate(abc, method_id, this, args, max_steps=100000):
    """Run one method body of the ABC on Python values. Only the opcodes of the Random methods and
    of the `_-A6B` helpers are implemented; anything else raises NotImplementedError."""
    body = abc.bodies[abc.body_of[method_id]]
    info = abc.methods[method_id]
    ptypes = [abc.mn_name(p, full=True) for p in info["params"]]
    ins = abcmod.decode(body["code"])
    at = {off: k for k, (off, _, _) in enumerate(ins)}
    loc = [this] + [coerce(t, v) for t, v in zip(ptypes, args)]
    loc += [None] * (body["locals"] - len(loc))
    st = []
    name = abc.mn_name
    pc = 0
    for _ in range(max_steps):
        off, op, a = ins[pc]
        nxt = ins[pc + 1][0] if pc + 1 < len(ins) else len(body["code"])
        pc += 1
        if op.startswith("getlocal"):
            st.append(loc[a[0] if op == "getlocal" else int(op[-1])])
        elif op.startswith("setlocal"):
            loc[a[0] if op == "setlocal" else int(op[-1])] = st.pop()
        elif op == "inclocal_i":
            loc[a[0]] = to_i32(to_i32(loc[a[0]]) + 1)
        elif op in ("pushscope", "pop"):
            st.pop()
        elif op in ("label", "nop", "coerce_a"):
            pass
        elif op == "pushnull":
            st.append(None)
        elif op == "pushbyte":
            st.append(a[0])
        elif op == "pushint":
            st.append(abc.ints[a[0]])
        elif op == "pushuint":
            st.append(abc.uints[a[0]])
        elif op == "pushdouble":
            st.append(abc.doubles[a[0]])
        elif op == "dup":
            st.append(st[-1])
        elif op == "convert_u":
            st.append(to_u32(st.pop()))
        elif op == "convert_i":
            st.append(to_i32(st.pop()))
        elif op == "convert_d":
            st.append(float(st.pop()))
        elif op in ("bitand", "bitxor", "bitor", "lshift", "urshift", "add_i", "subtract_i", "multiply_i",
                    "add", "subtract", "multiply", "divide", "modulo"):
            y, x = st.pop(), st.pop()
            st.append(_binop(op, x, y))
        elif op == "bitnot":
            st.append(to_i32(~to_i32(st.pop())))
        elif op == "findproperty":
            st.append(this)
        elif op in ("getproperty", "setproperty", "initproperty"):
            mn = abc.multinames[a[0]]
            v = st.pop() if op != "getproperty" else None
            key = st.pop() if mn[0] in (0x1B, 0x1C, 0x11, 0x12) else name(a[0])
            obj = st.pop()
            if isinstance(obj, list) and key != "length":
                if key != int(key) or not 0 <= int(key) < len(obj):
                    raise IndexError(f"index {key!r} out of range (method #{method_id} at {off})")
                key = int(key)
            if op == "getproperty":
                st.append(len(obj) if key == "length" and isinstance(obj, list) else obj[key])
            elif isinstance(obj, Obj):
                obj.store(key, v)
            else:
                obj[key] = v
        elif op in ("callproperty", "callpropvoid"):
            argv = [st.pop() for _ in range(a[1])][::-1]
            obj = st.pop()
            res = emulate(abc, obj.methods[name(a[0])], obj, argv, max_steps)
            if op == "callproperty":
                st.append(res)
        elif op == "jump":
            pc = at[nxt + a[0]]
        elif op in ("iflt", "iftrue", "iffalse"):
            if op == "iflt":
                y, x = st.pop(), st.pop()
                take = x < y  # NaN compares false, like AVM2
            else:
                take = bool(st.pop()) == (op == "iftrue")
            if take:
                pc = at[nxt + a[0]]
        elif op == "equals":
            y, x = st.pop(), st.pop()
            st.append(x == y)
        elif op == "not":
            st.append(not st.pop())
        elif op == "returnvalue":
            return coerce(abc.mn_name(info["ret"], full=True), st.pop())
        elif op == "returnvoid":
            return None
        else:
            raise NotImplementedError(f"opcode {op} at {off} of method #{method_id}")
    raise RuntimeError("step limit")


def _binop(op, x, y):
    if op == "bitand":
        return to_i32(to_i32(x) & to_i32(y))
    if op == "bitxor":
        return to_i32(to_i32(x) ^ to_i32(y))
    if op == "bitor":
        return to_i32(to_i32(x) | to_i32(y))
    if op == "lshift":
        return to_i32(to_i32(x) << (to_u32(y) & 31))
    if op == "urshift":
        return to_u32(x) >> (to_u32(y) & 31)
    if op == "add_i":
        return to_i32(to_i32(x) + to_i32(y))
    if op == "subtract_i":
        return to_i32(to_i32(x) - to_i32(y))
    if op == "multiply_i":
        return to_i32(to_i32(x) * to_i32(y))
    if op == "modulo":
        return js_mod(x, y)
    x, y = float(x), float(y)
    if op == "divide":
        return x / y if y else (math.nan if x == 0 or x != x else math.copysign(math.inf, x) * math.copysign(1, y))
    return {"add": x + y, "subtract": x - y, "multiply": x * y}[op]


def locate(abc):
    """Find the generator class and helpers in any ABC by name/signature (names change per patch).

    Returns {"class": id, "slots": {name: type}, "seed": m, "next": m,
             "uniform": m, "range_u32": m, "range_i32": m, "shuffle": m} (missing keys = not found).
    """
    found = {}
    sig = lambda m: (tuple(abc.mn_name(p, full=True) for p in abc.methods[m]["params"]),
                     abc.mn_name(abc.methods[m]["ret"], full=True))
    rnd = next(ci for ci in range(len(abc.instances)) if abc.class_name(ci) == "Random")
    found["class"] = rnd
    inst = abc.instances[rnd]
    found["slots"] = {abc.mn_name(t["name"]): abc.mn_name(t["type"], full=True) for t in inst["traits"] if t["kind"] == 0}
    found["methods"] = {}
    roles = {(("uint",), "void"): "seed", ((), "uint"): "next"}
    for t in inst["traits"]:
        if t["kind"] != 1:
            continue
        found["methods"][abc.mn_name(t["name"])] = t["method"]
        role = roles.get(sig(t["method"]))
        if role:
            found[role] = t["method"]
    helpers = {(("Random", "Number", "Number"), "Number"): "uniform", (("Random", "uint", "uint"), "uint"): "range_u32",
               (("Random", "int", "int"), "int"): "range_i32", (("*", "Random"), "void"): "shuffle"}
    for ci in range(len(abc.instances)):
        for t in abc.classes[ci]["traits"]:
            if t["kind"] == 1:
                role = helpers.get(sig(t["method"]))
                if role:
                    found.setdefault(role, t["method"])
    return found


def bytecode_random(abc, found, seed):
    """A `Random` object seeded by emulating the seed method of the ABC."""
    obj = Obj("Random", found["slots"], found["methods"])
    for slot, typ in found["slots"].items():
        obj[slot] = UintVector([0] * STATE_WORDS) if typ.startswith("Vector.<") else 0
    emulate(abc, found["seed"], obj, [seed])
    return obj


def verify(abc, seeds, draws=64):
    """Compare this port with the emulated bytecode. Returns a list of mismatch strings (empty = ok)."""
    found = locate(abc)
    missing = sorted({"seed", "next", "uniform", "range_u32", "range_i32", "shuffle"} - found.keys())
    if missing:
        return ["cannot verify missing methods: " + ", ".join(missing)]
    bad = []
    for seed in seeds:
        ref, port = bytecode_random(abc, found, seed), Well512(seed)
        vec = next(k for k, t in found["slots"].items() if t.startswith("Vector.<"))
        idx = next(k for k, t in found["slots"].items() if t == "uint")
        if list(ref[vec]) != port.state or ref[idx] != port.index:
            bad.append(f"seed {seed}: state after seeding differs")
        for k in range(draws):
            r, p = emulate(abc, found["next"], ref, []), port.next_u32()
            if r != p:
                bad.append(f"seed {seed}: draw {k} bytecode {r} port {p}")
                break
        cases = [(0, 0), (0, 1), (5, 3), (0, M32), (M32, 0), (-7, 7), (-2147483648, 2147483647), (100, 100)]
        for lo, hi in cases:
            for role, fn, conv in (("range_u32", range_u32, to_u32), ("range_i32", range_i32, to_i32),
                                   ("uniform", uniform, float)):
                if role not in found:
                    continue
                r = emulate(abc, found[role], None, [ref, conv(lo), conv(hi)])
                p = fn(port, conv(lo), conv(hi))
                if r != p and not (r != r and p != p):
                    bad.append(f"seed {seed}: {role}({lo}, {hi}) bytecode {r!r} port {p!r}")
        if "shuffle" in found:
            for n in (0, 1, 2, 7, 33):
                ra = list(range(n))
                emulate(abc, found["shuffle"], None, [ra, ref])
                pa = shuffle(port, list(range(n)))
                if ra != pa:
                    bad.append(f"seed {seed}: shuffle({n}) bytecode {ra} port {pa}")
        if emulate(abc, found["next"], ref, []) != port.next_u32():
            bad.append(f"seed {seed}: streams diverged after the helpers")
    return bad
