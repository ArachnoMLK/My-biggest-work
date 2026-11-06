"""Typed call graph of an ABC: which methods a method can call, resolved through the receiver's static type.

A research aid (static, approximate, stdlib only). Each method body is walked once in byte order with an
abstract operand stack whose entries carry a static type (class name, "static:Class" for a class object, or
None when unknown) and a short text of where the value came from. Forward branch targets get the stack of
their first branch, so the two arms of `a ? b : c` join correctly; other code after a jump or a return
(loop bodies, reached by a backward branch) starts with an empty stack, as compiled statements do. A call on a receiver of type C resolves to
C's member (walking the superclasses) plus the overrides in C's subclasses, or every implementer when C is
an interface; `findproperty` / `findpropstrict` receivers resolve in the method's own class, then globally.
A receiver of unknown type resolves to nothing (no edge), so the graph under-approximates calls through
untyped values (`*`, Object, Function) and through `[rt]` names. Edges through getters are included.
"""
from collections import deque

from . import abc as abcmod

RT_POPS = {0x0F: 1, 0x10: 1, 0x11: 2, 0x12: 2, 0x1B: 1, 0x1C: 1}
CALLS = {"callproperty": 1, "callproplex": 1, "callpropvoid": 0, "callsuper": 1, "callsupervoid": 0,
         "constructprop": 1}
BIN = {"add", "subtract", "multiply", "divide", "modulo", "lshift", "rshift", "urshift", "bitand", "bitor",
       "bitxor", "equals", "strictequals", "lessthan", "lessequals", "greaterthan", "greaterequals",
       "instanceof", "in", "add_i", "subtract_i", "multiply_i", "astypelate", "istypelate", "nextname",
       "nextvalue", "hasnext"}
UNARY = {"convert_s", "convert_i", "convert_u", "convert_d", "convert_b", "convert_o", "coerce_b", "coerce_a",
         "coerce_i", "coerce_d", "coerce_s", "coerce_u", "coerce_o", "negate", "increment", "decrement",
         "typeof", "not", "bitnot", "increment_i", "decrement_i", "negate_i", "sxi1", "sxi8", "sxi16",
         "esc_xelem", "esc_xattr", "checkfilter", "istype", "li8", "li16", "li32", "lf32", "lf64"}
PUSH = {"pushnull", "pushundefined", "pushbyte", "pushshort", "pushtrue", "pushfalse", "pushnan", "pushstring",
        "pushint", "pushuint", "pushdouble", "pushnamespace", "newactivation", "newfunction", "newcatch",
        "getglobalscope", "getscopeobject", "getouterscope", "getglobalslot", "hasnext2"}
POP1 = {"pop", "pushscope", "pushwith", "iftrue", "iffalse", "lookupswitch", "returnvalue", "throw",
        "setlocal", "setlocal_0", "setlocal_1", "setlocal_2", "setlocal_3", "setglobalslot", "dxnslate"}
POP2 = {"ifeq", "ifne", "iflt", "ifle", "ifgt", "ifge", "ifstricteq", "ifstrictne", "ifnlt", "ifnle", "ifngt",
        "ifnge", "setslot", "si8", "si16", "si32", "sf32", "sf64"}
END = {"jump", "returnvoid", "returnvalue", "throw"}
NUMERIC = {"int", "uint", "Number", "Boolean", "String"}


class Graph:
    def __init__(self, abc):
        self.abc = abc
        self.owner = abc.method_owner()
        self.classes = {}                # name -> class index
        self.method_class = {}           # method id -> class index (instance or static member, init)
        self.subclasses = {}             # class index -> direct subclasses
        self.implementers = {}           # interface name -> class indices
        for ci, inst in enumerate(abc.instances):
            name = abc.mn_name(inst["name"])
            self.classes.setdefault(name, ci)
        for ci, inst in enumerate(abc.instances):
            sup = abc.mn_name(inst["super"]) if inst["super"] else None
            if sup in self.classes:
                self.subclasses.setdefault(self.classes[sup], []).append(ci)
            for i in inst["interfaces"]:
                self.implementers.setdefault(abc.mn_name(i), []).append(ci)
            self.method_class[inst["iinit"]] = ci
            self.method_class[abc.classes[ci]["cinit"]] = ci
            for t in inst["traits"] + abc.classes[ci]["traits"]:
                if "method" in t:
                    self.method_class[t["method"]] = ci
        self.globals = {}
        for s in abc.scripts:
            for t in s["traits"]:
                self.globals.setdefault(abc.mn_name(t["name"]), t)
        self._edges = {}

    # ------------------------------------------------------------ type lookups
    def _trait(self, ci, name, static):
        while ci is not None:
            traits = self.abc.classes[ci]["traits"] if static else self.abc.instances[ci]["traits"]
            for t in traits:
                if self.abc.mn_name(t["name"]) == name:
                    return ci, t
            if static:
                return None, None
            sup = self.abc.instances[ci]["super"]
            ci = self.classes.get(self.abc.mn_name(sup)) if sup else None
        return None, None

    def _type_of_trait(self, t):
        if t is None:
            return None
        k = t["kind"]
        if k in (0, 6):
            return self.abc.mn_name(t["type"]) if t["type"] else None
        if k == 2:
            ret = self.abc.methods[t["method"]]["ret"]
            return self.abc.mn_name(ret) if ret else None
        if k == 4:
            return "static:" + self.abc.class_name(t["class"])
        return None

    def _overrides(self, ci, name, out):
        for sub in self.subclasses.get(ci, ()):
            for t in self.abc.instances[sub]["traits"]:
                if "method" in t and self.abc.mn_name(t["name"]) == name:
                    out.add(t["method"])
            self._overrides(sub, name, out)

    def resolve(self, typ, name, scope_ci):
        """(method ids, result type) of member `name` on a value of type `typ`."""
        if typ is None:
            return set(), None
        if typ == "scope":
            if scope_ci is not None:
                for static in (False, True):
                    ci, t = self._trait(scope_ci, name, static)
                    if t is not None:
                        return self._targets(ci, t, name, static), self._type_of_trait(t)
            t = self.globals.get(name)
            if t is None:
                if name in self.classes:
                    return set(), "static:" + name
                return set(), None
            return ({t["method"]} if "method" in t else set()), self._type_of_trait(t)
        static = typ.startswith("static:")
        cname = typ[7:] if static else typ
        ci = self.classes.get(cname)
        if ci is None:
            return set(), None
        inst = self.abc.instances[ci]
        if not static and inst["flags"] & 0x04:                 # interface: every implementer
            out = set()
            for impl in self.implementers.get(cname, ()):
                owner_ci, t = self._trait(impl, name, False)
                if t is not None and "method" in t:
                    out.add(t["method"])
                    self._overrides(impl, name, out)
            return out, None
        owner_ci, t = self._trait(ci, name, static)
        if t is None:
            return set(), None
        return self._targets(owner_ci, t, name, static, ci), self._type_of_trait(t)

    def _targets(self, owner_ci, t, name, static, from_ci=None):
        if "method" not in t:
            return set()
        out = {t["method"]}
        if not static:
            self._overrides(from_ci if from_ci is not None else owner_ci, name, out)
        return out

    def _method_ret(self, mids):
        for m in mids:
            ret = self.abc.methods[m]["ret"]
            return self.abc.mn_name(ret) if ret else None
        return None

    # ------------------------------------------------------------ walk
    def walk(self, mid):
        """[(offset, op, name, receiver type, receiver text, argument texts, targets)] for every member
        reference (argument texts only for calls)."""
        bi = self.abc.body_of.get(mid)
        if bi is None:
            return []
        abc = self.abc
        ci = self.method_class.get(mid)
        this = abc.class_name(ci) if ci is not None else None
        info = abc.methods[mid]
        local = {0: (this, "this")}
        for i, p in enumerate(info["params"], 1):
            local[i] = (abc.mn_name(p) if p else None, f"arg{i}")
        try:
            ins = abcmod.decode(abc.bodies[bi]["code"])
        except ValueError:
            return []
        targets_at = {}
        stack, dead, out = [], False, []

        def pop(n=1):
            vals = []
            for _ in range(n):
                vals.append(stack.pop() if stack else (None, "?"))
            return vals[::-1]

        for off, op, a in ins:
            if off in targets_at and (dead or not stack):
                stack = list(targets_at[off])
                dead = False
            elif dead:                  # code after a jump / return: a loop body or a statement start
                stack, dead = [], False
            rt = 0
            name = None
            if op in abcmod.MULTINAME_OPS and a:
                mn = abc.multinames[a[0]]
                rt = RT_POPS.get(mn[0], 0) if mn else 0
                name = abc.mn_name(a[0])
            if op.startswith("if") or op == "jump":
                n = 1 if op in ("iftrue", "iffalse") else (0 if op == "jump" else 2)
                pop(n)
                target = off + 4 + a[0] if op != "jump" else off + 4 + a[0]
                targets_at.setdefault(target, list(stack))
                if op == "jump":
                    dead = True
                continue
            if op in PUSH:
                stack.append((None, op))
            elif op in ("getlocal", "getlocal_0", "getlocal_1", "getlocal_2", "getlocal_3"):
                n = a[0] if op == "getlocal" else int(op[-1])
                stack.append(local.get(n, (None, f"local{n}")))
            elif op in ("setlocal", "setlocal_0", "setlocal_1", "setlocal_2", "setlocal_3"):
                n = a[0] if op == "setlocal" else int(op[-1])
                v = pop()[0]
                if v[0] is not None or n not in local:
                    local[n] = v
            elif op in POP1:
                pop()
            elif op in POP2:
                pop(2)
            elif op == "dup":
                v = pop()[0]
                stack += [v, v]
            elif op == "swap":
                x, y = pop(2)
                stack += [y, x]
            elif op in ("findproperty", "findpropstrict"):
                stack.append(("scope", "find " + name))
            elif op == "getlex":
                pop(rt)
                _, typ = self.resolve("scope", name, ci)
                stack.append((typ, name))
            elif op in ("getproperty", "getsuper"):
                pop(rt)
                recv = pop()[0]
                mids, typ = self.resolve(recv[0], name, ci)
                if mids:
                    out.append((off, op, name, recv[0], recv[1], (), mids))
                stack.append((typ, f"{recv[1]}.{name}"[-60:]))
            elif op in ("setproperty", "initproperty", "setsuper"):
                pop(1 + rt)
                recv = pop()[0]
                mids, _ = self.resolve(recv[0], name, ci)
                if mids:
                    out.append((off, op, name, recv[0], recv[1], (), mids))
            elif op == "deleteproperty" or op == "getdescendants":
                pop(1 + rt)
                stack.append((None, op))
            elif op in CALLS:
                args = tuple(v[1] for v in pop(a[1]))
                pop(rt)
                recv = pop()[0]
                if op == "constructprop":
                    _, ctyp = self.resolve(recv[0], name, ci)
                    cls = ctyp[7:] if ctyp and ctyp.startswith("static:") else name
                    c = self.classes.get(cls)
                    mids = {abc.instances[c]["iinit"]} if c is not None else set()
                    out.append((off, op, name, recv[0], recv[1], args, mids))
                    stack.append((cls, "new " + cls))
                    continue
                mids, typ = self.resolve(recv[0], name, ci)
                out.append((off, op, name, recv[0], recv[1], args, mids))
                if CALLS[op]:
                    stack.append((self._method_ret(mids) if mids else None, f"{recv[1]}.{name}()"[-60:]))
            elif op in ("callmethod", "callstatic"):
                pop(a[1] + 1)
                stack.append((None, op))
            elif op == "call":
                pop(a[0] + 2)
                stack.append((None, op))
            elif op == "construct":
                args = pop(a[0] + 1)
                t = args[0][0]
                stack.append((t[7:] if t and t.startswith("static:") else None, "new"))
            elif op == "constructsuper":
                pop(a[0] + 1)
            elif op == "applytype":
                pop(a[0] + 1)
                stack.append((None, "applytype"))
            elif op == "newobject":
                pop(2 * a[0])
                stack.append(("Object", "{}"))
            elif op == "newarray":
                pop(a[0])
                stack.append(("Array", "[]"))
            elif op == "newclass":
                pop()
                stack.append((None, "newclass"))
            elif op in ("coerce", "astype"):
                v = pop()[0]
                stack.append((abc.mn_name(a[0]), v[1]))
            elif op == "getslot":
                pop()
                stack.append((None, "slot"))
            elif op in BIN:
                pop(2)
                stack.append((None, op))
            elif op in UNARY:
                v = pop()[0]
                stack.append((None, v[1]))
            if op in END:
                dead = True
        return out

    def edges(self, mid):
        if mid not in self._edges:
            s = set()
            for *_, mids in self.walk(mid):
                s |= mids
            self._edges[mid] = s
        return self._edges[mid]

    def reach(self, roots, stop=()):
        """{method: parent} of every method reachable from `roots` (BFS), not entering `stop`."""
        prev = {r: None for r in roots}
        q = deque(roots)
        while q:
            m = q.popleft()
            if m in stop:
                continue
            for n in self.edges(m):
                if n not in prev:
                    prev[n] = m
                    q.append(n)
        return prev

    def path(self, prev, m):
        out = []
        while m is not None:
            out.append(f"#{m} {self.owner.get(m, '?')}")
            m = prev[m]
        return out
