"""Tests of the match PRNG port (tools/bh/prng.py). See docs/prng-11.00.md.

Golden numbers below were produced by `prng.emulate` running the real method bodies of patch 11.00
(abc 7d308423...: Random #1011 seed, #1013 next, _-A6B #1142/#1143/#1144/#1068 helpers), not by the
port. The pure tests also check the port against two implementations that share no code with it:
`Reference` below (ctypes 32-bit integers, written from the bytecode equations) and `swz.SwzRandom`
(derived from bhswz-rs and proven on real .swz files). Game tests are skipped without an install.

Run: python -I -m unittest discover -s tests   (from the repository root)
"""
import ctypes
import hashlib
import json
import math
import os
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from bh import abc, prng, swf, swz  # noqa: E402

GAME = os.environ.get("BRAWLHALLA_DIR", r"C:\Program Files (x86)\Steam\steamapps\common\Brawlhalla")
HAVE_GAME = os.path.exists(os.path.join(GAME, "BrawlhallaAir.swf"))
ABC_11_00 = "7d308423eaebcc82dfdda4ecc0e57d3abe78569534023aa7f9d776f626356db9"

# seed -> (first 8 draws, draw #999), from the emulated bytecode of patch 11.00
GOLDEN = {
    0: ([1235243591, 1711835756, 2513842311, 3569570657, 1005723082, 4279345956, 3036286900, 2517474578], 763145073),
    1: ([427107241, 3478131665, 1329158148, 4270539161, 922294098, 2377131999, 436603839, 2428934785], 381084624),
    0x7FFFFFFF: ([1974431311, 797314759, 2354315625, 3666172209, 2311912210, 1511392640, 3256793499, 534772540],
                 1721749431),
    0x80000000: ([3075216646, 54117710, 461350139, 3918886878, 2933583530, 3045189890, 1840413570, 3719072737],
                 4103615850),
    0xFFFFFFFF: ([2828776810, 748994816, 1966439253, 401916937, 2502688468, 2331435604, 365881798, 4017688952],
                 640925513),
    123456789: ([1040815684, 517538044, 2501316615, 155272286, 3383848223, 3764305460, 332755895, 644335988],
                2163120824),
}


class Reference:
    """Second implementation of #1011/#1013 with ctypes int32/uint32 (no shared code with prng.py)."""

    def __init__(self, seed):
        u, i32 = ctypes.c_uint32, ctypes.c_int32
        self.t = [u(seed).value]
        for k in range(1, 16):
            p = self.t[-1]
            x = i32(p ^ (p >> 30)).value                      # bitxor -> int
            m = i32(i32(1812433253).value * x).value          # multiply_i
            self.t.append(u(i32(u(m).value + k).value).value)  # convert_u, add_i, & 0xFFFFFFFF
        self.e = 0

    def next(self):
        u, t, e = ctypes.c_uint32, self.t, self.e
        a = t[e]
        c = t[(e + 13) & 15]
        b = u(a ^ c ^ u(a << 16).value ^ u(c << 15).value).value
        c = t[(e + 9) & 15]
        c = u(c ^ (c >> 11)).value
        t[e] = a = u(b ^ c).value
        d = u(a ^ (u(a << 5).value & 3661901092)).value
        self.e = e = (e + 15) & 15
        a = t[e]
        t[e] = u(a ^ b ^ d ^ u(a << 2).value ^ u(b << 18).value ^ u(c << 28).value).value
        return t[e]


class Stub:
    """A generator that returns chosen values, to hit exact edges of the helpers."""

    def __init__(self, *values):
        self.values = list(values)

    def next_u32(self):
        return self.values.pop(0)


class Conversions(unittest.TestCase):
    def test_to_int32_uint32(self):
        self.assertEqual(prng.to_u32(-1), 0xFFFFFFFF)
        self.assertEqual(prng.to_u32(1 << 32), 0)
        self.assertEqual(prng.to_i32(0x80000000), -0x80000000)
        self.assertEqual(prng.to_i32(0xFFFFFFFF), -1)
        self.assertEqual(prng.to_i32(-1.9), -1)  # truncation toward zero
        self.assertEqual(prng.to_u32(4294967296.5), 0)
        for v in (math.nan, math.inf, -math.inf):
            self.assertEqual((prng.to_i32(v), prng.to_u32(v)), (0, 0))

    def test_js_modulo(self):
        self.assertEqual(prng.js_mod(-7, 3), -1.0)  # sign of the dividend
        self.assertEqual(prng.js_mod(7, -3), 1.0)
        self.assertTrue(math.isnan(prng.js_mod(5, 0)))
        self.assertEqual(prng.js_mod(0xFFFFFFFF, 10), 5.0)

    def test_header_seed(self):
        self.assertEqual(prng.seed_from_header(-1), 0xFFFFFFFF)
        self.assertEqual(prng.seed_from_header(-0x80000000), 0x80000000)
        self.assertEqual(prng.seed_from_header(0xFFFFFFFF), 0xFFFFFFFF)
        for bad in (1 << 32, -(1 << 31) - 1, 1.0, True, "1"):
            with self.assertRaises(ValueError):
                prng.seed_from_header(bad)


class Well512(unittest.TestCase):
    def test_golden_sequences(self):
        for seed, (first, d999) in GOLDEN.items():
            rng = prng.Well512(seed)
            seq = [rng.next_u32() for _ in range(1000)]
            self.assertEqual(seq[:8], first, seed)
            self.assertEqual(seq[999], d999, seed)

    def test_seeding_state(self):
        index, words = prng.Well512(0).getstate()
        self.assertEqual((index, words[:4]), (0, (0, 1, 1812433255, 1900727105)))
        self.assertEqual(prng.Well512(0xFFFFFFFF).getstate()[1][:4], (4294967295, 1340201581, 3941791902, 3241351924))

    def test_independent_reference_and_swz(self):
        for seed in list(GOLDEN) + [42, 0xDEADBEEF, 0x40000000, 2147483646]:
            port, ref, ext = prng.Well512(seed), Reference(seed), swz.SwzRandom(seed)
            self.assertEqual(port.state, ref.t)
            for _ in range(2000):
                v = port.next_u32()
                self.assertEqual(v, ref.next())
                self.assertEqual(v, ext.next())
                self.assertTrue(0 <= v <= 0xFFFFFFFF)

    def test_reseed_forgets_everything(self):
        a = prng.Well512(5)
        for _ in range(37):
            a.next_u32()
        a.seed(1)
        self.assertEqual([a.next_u32() for _ in range(8)], GOLDEN[1][0])

    def test_state_roundtrip(self):
        a = prng.Well512(77)
        for _ in range(13):
            a.next_u32()
        b = prng.Well512(0)
        b.setstate(a.getstate())
        self.assertEqual([a.next_u32() for _ in range(40)], [b.next_u32() for _ in range(40)])
        before = b.getstate()
        for bad in ((16, (0,) * 16), (0, (0,) * 15), (0, (1 << 32,) + (0,) * 15),
                    (0.5, (0,) * 16), (True, (0,) * 16), (0, (1.5,) + (0,) * 15),
                    (0, (False,) + (0,) * 15)):
            with self.assertRaises(ValueError):
                b.setstate(bad)
            self.assertEqual(b.getstate(), before)

    def test_seed_validation(self):
        for bad in (-1, 1 << 32, 1.5, None, True):
            with self.assertRaises(ValueError):
                prng.Well512(bad)


class Helpers(unittest.TestCase):
    def test_golden_helpers_seed_42(self):
        rng = prng.Well512(42)  # same call order as the bytecode run that produced these numbers
        self.assertEqual([prng.range_u32(rng, lo, hi) for lo, hi in
                          [(0, 9), (10, 20), (0, 0xFFFFFFFF), (5, 3), (0xFFFFFFFF, 0xFFFFFFFF)]],
                         [5, 20, 0, 3943717265, 4294967295])
        self.assertEqual([prng.range_i32(rng, lo, hi) for lo, hi in
                          [(-5, 5), (0, 0), (0, -1), (5, 3), (-2147483648, 2147483647)]], [-5, 0, 0, 5, -2147483648])
        self.assertEqual([prng.uniform(rng, 0.0, 1.0), prng.uniform(rng, -1.5, 2.5)],
                         [0.23208877635935526, -0.842762168343822])
        self.assertEqual(prng.shuffle(rng, list("abcdefg")), list("fgebacd"))
        self.assertEqual(rng.next_u32(), 2936622485)

    def test_edges(self):
        self.assertEqual(prng.uniform(Stub(0), -3.0, 5.0), -3.0)
        self.assertEqual(prng.uniform(Stub(0xFFFFFFFF), -3.0, 5.0), 5.0)  # both ends reachable
        self.assertEqual(prng.range_u32(Stub(0xFFFFFFFF), 0, 0xFFFFFFFF), 0)  # span wraps to 0 -> NaN -> lo
        self.assertEqual(prng.range_u32(Stub(0xFFFFFFFF), 7, 7), 7)
        self.assertEqual(prng.range_u32(Stub(9), 0xFFFFFFFE, 1), (9 % 4 + 0xFFFFFFFE) & 0xFFFFFFFF)  # wrap
        self.assertEqual(prng.range_i32(Stub(0xFFFFFFFF), -10, 10), (0x7FFFFFFF % 21) - 10)  # high bit dropped
        self.assertEqual(prng.range_i32(Stub(123), 5, 3), 5)  # span -1: remainder 0
        stub = Stub(1, 2, 3)
        prng.range_u32(stub, 0, 0xFFFFFFFF)  # still consumes exactly one draw
        self.assertEqual(stub.values, [2, 3])

    def test_shuffle_is_not_fisher_yates(self):
        stub = Stub(2, 2, 2)  # i=0 swaps with 2, i=1 with 2, i=2 with 2
        self.assertEqual(prng.shuffle(stub, [0, 1, 2]), [2, 0, 1])
        self.assertEqual(prng.shuffle(Stub(), []), [])


class Cli(unittest.TestCase):
    def test_verification_requires_all_methods(self):
        roles = {role: 0 for role in ("seed", "next", "uniform", "range_u32", "range_i32", "shuffle")}
        for missing in roles:
            with self.subTest(missing=missing), patch.object(prng, "locate", return_value={
                    k: v for k, v in roles.items() if k != missing}):
                self.assertEqual(prng.verify(None, [0]), ["cannot verify missing methods: " + missing])

    def run_cli(self, *args):
        return subprocess.run([sys.executable, "-I", os.path.join(ROOT, "tools", "bht.py"), *args],
                              capture_output=True, text=True)

    def test_prng_command(self):
        out = self.run_cli("prng", "-1", "--count", "2", "--skip", "998", "--json")
        self.assertEqual(out.returncode, 0, out.stderr)
        data = json.loads(out.stdout)
        self.assertEqual(data["seed"], 0xFFFFFFFF)
        self.assertEqual([d["u32"] for d in data["draws"]][1], GOLDEN[0xFFFFFFFF][1])
        state = json.loads(self.run_cli("prng", "0", "--state").stdout)
        self.assertEqual(state["state"][:3], [0, 1, 1812433255])

    def test_prng_rejects_bad_input(self):
        for args in (["prng", "4294967296"], ["prng", "x"], ["prng", "1", "--count", "0"],
                     ["prng", "1", "--skip", "-1"]):
            self.assertEqual(self.run_cli(*args).returncode, 2, args)


@unittest.skipUnless(HAVE_GAME, "Brawlhalla not installed")
class Bytecode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(GAME, "BrawlhallaAir.swf"), "rb") as f:
            main = swf.Swf(f.read())
        data = max(main.abc_blocks(), key=lambda b: len(b[1]))[1]
        cls.sha = hashlib.sha256(data).hexdigest()
        cls.abc = abc.Abc(data)

    def test_port_matches_emulated_bytecode(self):
        self.assertEqual(prng.verify(self.abc, sorted(GOLDEN) + [42], draws=300), [])

    def test_golden_numbers_come_from_the_bytecode(self):
        if self.sha != ABC_11_00:
            self.skipTest("goldens are pinned to patch 11.00")
        found = prng.locate(self.abc)
        self.assertEqual([found[k] for k in ("seed", "next", "uniform", "range_u32", "range_i32", "shuffle")],
                         [1011, 1013, 1142, 1143, 1144, 1068])
        for seed, (first, d999) in GOLDEN.items():
            obj = prng.bytecode_random(self.abc, found, seed)
            seq = [prng.emulate(self.abc, found["next"], obj, []) for _ in range(1000)]
            self.assertEqual((seq[:8], seq[999]), (first, d999))


if __name__ == "__main__":
    unittest.main()
