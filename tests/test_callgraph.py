"""Tests of the typed call graph walker (tools/bh/callgraph.py) on a hand-built ABC-like object.
Run: python -I -m unittest discover -s tests"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh import callgraph  # noqa: E402


class FakeAbc:
    """Classes A (method f, slot b: B), B (method g), C extends B (overrides g); script function h."""

    def __init__(self):
        self.names = {1: "A", 2: "B", 3: "C", 4: "f", 5: "g", 6: "b", 7: "h", 8: "Object"}
        self.multinames = [None] + [(0x07, 0, i) for i in range(1, 9)]
        t = lambda n, m: {"name": n, "kind": 1, "method": m}
        self.instances = [
            {"name": 1, "super": 8, "flags": 0, "interfaces": [], "iinit": 10,
             "traits": [t(4, 0), {"name": 6, "kind": 0, "type": 2}]},
            {"name": 2, "super": 8, "flags": 0, "interfaces": [], "iinit": 11, "traits": [t(5, 1)]},
            {"name": 3, "super": 2, "flags": 0, "interfaces": [], "iinit": 12, "traits": [t(5, 2)]},
        ]
        self.classes = [{"cinit": 20, "traits": []}, {"cinit": 21, "traits": []}, {"cinit": 22, "traits": []}]
        self.scripts = [{"init": 30, "traits": [t(7, 3)]}]
        self.methods = [{"ret": 0, "params": []} for _ in range(31)]
        self.bodies = [{"method": 0, "code": b""}]
        self.body_of = {0: 0}

    def mn_name(self, i):
        return self.names.get(self.multinames[i][2]) if i else None

    def class_name(self, ci):
        return self.mn_name(self.instances[ci]["name"])

    def method_owner(self):
        return {0: "A.f", 1: "B.g", 2: "C.g", 3: "script0.h"}


class Graph(unittest.TestCase):
    def setUp(self):
        self.g = callgraph.Graph(FakeAbc())

    def test_virtual_dispatch(self):
        mids, typ = self.g.resolve("B", "g", None)
        self.assertEqual(mids, {1, 2})                          # B.g and the override C.g
        self.assertEqual(self.g.resolve("C", "g", None)[0], {2})

    def test_slot_type_and_scope(self):
        self.assertEqual(self.g.resolve("A", "b", None), (set(), "B"))
        self.assertEqual(self.g.resolve("scope", "f", 0)[0], {0})      # own class member
        self.assertEqual(self.g.resolve("scope", "h", 0)[0], {3})      # script function
        self.assertEqual(self.g.resolve("scope", "B", 0), (set(), "static:B"))
        self.assertEqual(self.g.resolve(None, "g", 0), (set(), None))  # unknown receiver: no edge


if __name__ == "__main__":
    unittest.main()
