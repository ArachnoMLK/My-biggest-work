# Match PRNG — patch 11.00 (Q3)

Pin: **patch 11.00 / abc `7d308423eaebcc82dfdda4ecc0e57d3abe78569534023aa7f9d776f626356db9`**.
Method ids and obfuscated names are only valid for this ABC. "@N" = instruction offset printed by
`abc-disasm`. Port: [`tools/bh/prng.py`](../tools/bh/prng.py); tests: [`tests/test_prng.py`](../tests/test_prng.py).

Reproduce (repository root, game installed):

```
python -I tools/bht.py abc-extract --game "<Brawlhalla folder>"   # prints the sha256 above
python -I tools/bht.py abc-disasm --class Random                   # #1008-#1013
python -I tools/bht.py abc-disasm --method 3348                    # where the replay seed goes
python -I tools/bht.py abc-disasm --method 4908                    # ItemManager seeding
python -I tools/bht.py abc-find _-24O --member                     # every seeding site (5)
python -I tools/bht.py abc-find _-f4c --member                     # every draw site (154 methods)
python -I tools/bht.py prng-verify                                 # port == emulated bytecode
python -I tools/bht.py prng 123456789 --count 4                    # the stream for a seed
```

## 1. Summary

- [V] There is **one PRNG algorithm** in the game code: class `Random` (readable name, class #59),
  a **WELL512** generator (16 × uint32 state + index), the same algorithm as the `.swz` decryptor
  (`swz.SwzRandom`, from bhswz-rs) — checked by running both for 2,000 draws on 10 seeds
  (`tests/test_prng.py`, `test_independent_reference_and_swz`). The `.swz` decryption itself is
  *not* in this ABC (`abc-find 771006925` = 0 methods), so that agreement is algorithmic, not a
  runtime oracle.
- [V] The replay `random_seed` seeds **two separate `Random` instances**, both with the same value:
  `RulesManager._-22` and `ItemManager._-22` (§3). They produce the same stream; the item one is
  2 draws ahead right after seeding.
- [V] Three other `Random` instances exist and are **not** seeded from the replay (§4). The global one
  (`_-A6B._-PW`, seeded from `Math.random()`) has 278 draw sites in 116 methods.
- [H] Everything replay-relevant should therefore come from the two match instances; whether some
  global-generator draws still influence simulated state is **not established** (§5).
- No game/runtime equivalence is claimed: the port equals the *bytecode* under AVM2 semantics
  (emulated, §6), not an observed in-game value. The only oracle would be Q10.

## 2. The algorithm (class `Random`, #1008–#1014)

| Item | Where | Status |
|---|---|---|
| Fields: `_-T1X : Vector.<uint>` (16 words, fixed), `_-E6G : uint` (index) | traits of class #59; ctor #1008 @2–21 | [V] |
| Statics `_-B2N = 0xFFFFFFFF`, `_-Y5B = 3661901092 (0xDA442D24)`, `_-Gz = 1812433253`, `_-w1w = 16`; the methods use inlined copies | script59.<init> #1014 @16–51 | [V] |
| `new Random()` seeds with `uint(int(floor(Math.random() * 2147483647)))` → **non-deterministic** until reseeded | #1008 @25–52 | [V] |
| **Seed** `_-24O(seed:uint)`: `index = 0`; `s[0] = seed & 0xFFFFFFFF`; for i = 1..15: `s[i] = uint(int32(1812433253 * (s[i-1] ^ (s[i-1] >>> 30))) + i)`. Every word and the index are overwritten, so the previous state is irrelevant. | #1011 @5–117 | [V] |
| **Next** `_-f4c():uint`: one WELL512 step (Lomont's formulation): `a=s[i]; c=s[(i+13)&15]; b=a^c^(a<<16)^(c<<15); c=s[(i+9)&15]; c^=c>>>11; a=s[i]=b^c; d=a^((a<<5)&0xDA442D24); i=(i+15)&15; a=s[i]; s[i]=a^b^d^(a<<2)^(b<<18)^(c<<28); return s[i]` | #1013 @2–267 | [V] |
| Snapshot `_-K49(bytes)`: `writeUnsignedInt(index)` then the 16 words in order; `_-L3P(bytes)` reads them back. Byte order = the caller's `ByteArray.endian` (not checked). | #1010, #1012 | [V] order, unknown endianness |

AVM2 semantics that matter, and how the port reproduces them (`prng.to_i32/to_u32/js_mod`):

- [V] opcodes: `lshift` and `bitxor`/`bitand` act on ToInt32 values and give an int; every
  intermediate is followed by `convert_u` or stored into `Vector.<uint>` (ToUint32). Net effect:
  plain 32-bit unsigned arithmetic; `>>>` is `urshift` (logical).
- [V] opcode / [H] semantics: the seeding multiply is **`multiply_i`** (#1011 @99). The port assumes
  the Tamarin/AVM2 behaviour "ToInt32 both operands, 32-bit wrapping product". If the runtime
  computed the product in double precision first, low bits would differ for large products. The
  seeding then equals the standard MT19937-style init used by the external `.swz` WELL512, which is
  proven on real files, so the assumption is consistent with the game's other WELL512 use.
- [V] `0xDA442D24` is pushed as a uint (`pushuint 3661901092`); `bitand` turns it into the int32
  with the same bits, so the mask is exact.
- [V] Seed input: the replay header field is read as **signed i32** (`_-24q._-b2L` #6699 @660–762,
  via `_-Lg._-a16`) into `_-24q._-669 : uint`, then passed as `uint` to `_-h3U._-T12(replay, seed:uint)`
  #3624 → `_-Y3u(level, seed:Object)` → `_-h3U._-669 : uint`. So the seed is `header_i32 & 0xFFFFFFFF`
  (`prng.seed_from_header`; the CLI accepts both forms). `tools/bh/replay.py` already reads it as u32.

## 3. The two replay-seeded instances

`_-h3U._-Y3u(level, seed)` #3348:

| Offset | What | Status |
|---|---|---|
| @46–79 | if `seed == null`: `seed = _-A6B._-PW._-f4c() % 2147483647` (the global generator). Not taken on the replay path, which always passes a uint. | [V] |
| @80–85 | `_-h3U._-669 = seed` (uint slot) | [V] |
| @89–105 | `_-h3U._-3z._-13p(_-669)` → ItemManager | [V] |
| @110–127 | `_-h3U._-s3D._-22._-24O(_-669)` → RulesManager's generator, seeded directly | [V] |
| @131–137 | then `_-h3U._-s3D._-76j()` (creates the per-mode rule objects; no direct draw in it) | [V] no direct `_-f4c`; indirect draws not traced |

| Instance | Owner / field | Created | Seeded | Status |
|---|---|---|---|---|
| **R (rules)** | `_-h3U._-s3D : _-99` → `_-99._-22 : Random`. `_-99` = **RulesManager** (string `[RulesManager.hx] mCurrRules is null.` in `_-99._-76j` #7133) | `_-99.<init>` #7124 @31–41 | #3348 @110–127, nothing drawn at seeding time | [V] |
| **R alias** | `_-P4P._-22` = `this._-N1k._-s3D._-22` (same object as R). `_-P4P` holds `HordeMode_*` strings ([H] Horde mode) | `_-P4P.<init>` #6597 @56–71; set to null in `_-P4P._-x3O` #6616 @27–34 | — | [V] alias |
| **I (items)** | `_-h3U._-3z : _-E1V` → `_-E1V._-22 : Random`. `_-E1V` = **ItemManager** (string `[ItemManager.as]: items missing ` in `_-E1V._-v2w` #4895; method `SpawnImportantItem2`) | `_-E1V.<init>` #4870 @2–12 | `_-E1V._-13p(seed)` #4908: @2–9 `_-22._-24O(seed)`, then **draw 0 → `_-Y1h`** (@13–27), **draw 1 → `_-5J`** (@30–44), then `_-A1o(...)` (@61–103, no draw: its only call is `push`) | [V] |

Both instances are saved/restored with the rollback snapshots: `_-E1V._-Z3n` #4872 @328–335 and
`_-99._-Z3n` #7126 @419–426 call `_-K49`; `_-E1V._-B5T` #4900 @611–618 and `_-99._-B5T` #7135
@788–795 call `_-L3P`. [V] calls; [H] that `_-Z3n`/`_-B5T` are the rollback save/load pair (fits Q1's
rollback machinery).

`prng.py` therefore models a match as: `rules = Well512(seed)`, `items = Well512(seed)` with
`items._-Y1h = items.next_u32()`, `items._-5J = items.next_u32()`. What `_-Y1h`/`_-5J` are used for is
unknown.

### Draw sites (consumers), classified by receiver

Script: every `getproperty _-22/_-PW/_-kK/_-m` whose next call is `_-f4c` or one of the helpers
below; the receiver is resolved from the preceding instruction (`getproperty _-s3D` → R,
`getproperty _-3z` → I, `findproperty` → the method's own class, `getlocal N` → the type of the
last `coerce T; setlocal N`). [V] for the listed sites; dynamic receivers not of these shapes are not
counted, so the lists may be incomplete.

| Generator | Sites | Methods (id, draws) |
|---|---|---|
| R direct (`…_-s3D._-22` or a local of type `_-99`) | 36 in 21 | `_-t2d` rule (D20 mode strings, [H]) #7078 1, #7080 1, #7085 2, #7086 3, #7094 6, #7095 3; `_-41Q` #7230 1, #7233 1; `_-32a._-Fr` #7206 1; `_-33m._-Sd` #7066 1; `_-B4v._-D4b` #7250 1; `_-h2C._-f40` #7272 2; `_-I4N._-8V` #7280 1; `_-zK._-768` #7052 1 (all `_-QA` rule subclasses built by `_-76j`); `_-Z36._-u1W` #3805 2; `_-33J._-A4x` #3836 2; `_-F5N.<init>` #1683 1; `_-b2h._-k5r` #3758 1; `_-X6R._-b3x` #6777 1 + 1 shuffle; `MessageTrigger.Tick` #5809 1; `_-9D._-Y15` #13733 2 (`_-9D` extends the UI widget class `_-x1d`) |
| R via `_-P4P._-22` | 20 in 7 | #6601 5, #6608 3, #6612 1, #6613 3, #6614 1, #6615 5, #6619 2 |
| I (`_-E1V` methods) | 7 in 6 | `_-13p` #4908 2 (at seeding), `_-96d` #4876 1, `_-u43` #4880 1, `_-p1K` #4888 1, `_-K5X` #4911 1, `_-e4H` #4892 1 shuffle |

## 4. Instances not seeded from the replay

| Instance | Seed | Users | Status |
|---|---|---|---|
| `_-A6B._-PW` (static, "global") | `new Random()` in `_-y2E.init` #15351 @12061–12065 → `Math.random()`; never passed to `_-24O` or `_-L3P` (all 5 `_-24O` sites; of the 5 `_-L3P` call sites, 2 are on R/I and 3 are same-named methods of other types: `_-X51`/`_-B3C` with 2 args in `_-h3U._-01I` #3336 @1369/@1623, `_-B1z` in `_-E1V._-v2w` #4895 @367) | 278 sites / 116 methods: bot AI `_-v5Q` (incl. `Think`, 13 methods), `_-y30` (14), `Entity` (#2887 `<init>`, #3002, #3115), `BombsketballState`/`SoccerState`/`VolleyBattleState._-c1u`, `HeroType._-r1l`, menus (`ScreenLevelSelect`…), helpers `_-A6B.Random()` #1148 etc. | [V] seeding and site count; [H] that none of them changes simulated state (they cannot be reproduced from a replay, so a replay-faithful engine must not depend on them) |
| `_-h3U._-kK` (static) | `new Random()` #15351 @30914–30918; reseeded in `_-h3U._-425` #3389 @100–138 with a draw of `_-PW` | only `_-425` (28 draws: random positions ±7000, written to a `ByteArray` with `writeDouble`; guarded by `_-22B`) | [V]; [H] a debug/determinism self-test |
| `_-Mr._-m` (static) | `_-Mr.static._-n5z(_-h3U._-v4J)` #9974, called from `_-Mr._-r5q` #9902 @203–225; `_-v4J` is a uint time counter (`getTimer` / multiples of 16 in `_-h3U._-L5y` #3310) | one shuffle in `_-Mr._-r5q`; `_-Mr` is a screen class (`OnInitDisplay`, extends `_-E6N`) | [V] calls; [H] UI only |

Also [V]: `_-1R`/`_-H1W`/`_-b3I` (#3207, #3217–#3225), used by `Entity.<init>` for field `_-Z2G`,
take `_-PW` draws as random offsets into a 128-slot `Vector.<Number>`; read (`_-U13`) and write
(`_-E1t`) go through the same slot formula, so the draws change where values are stored, not the
values ([H] memory-scrambling against value editing). Not a second generator.

## 5. Ported helpers (static methods of `_-A6B`, the generator passed as an argument)

| Bytecode | Port | Behaviour | Status |
|---|---|---|---|
| `_-o5L(r, lo:Number, hi:Number):Number` #1142 | `uniform` | `lo + r.next()/4294967295.0 * (hi - lo)` in doubles; both ends reachable | [V] |
| `_-k1J(r, lo:uint, hi:uint):uint` #1143 | `range_u32` | `uint(int(next % uint(hi-lo+1)) + lo)`; if `hi-lo+1` wraps to 0 (`lo=0, hi=0xFFFFFFFF`) the remainder is NaN → result `lo` | [V] |
| `_-KQ(r, lo:int, hi:int):int` #1144 | `range_i32` | `int((next & 0x7FFFFFFF) % int32(hi-lo+1) + lo)`; span 0 → `lo`; `hi < lo` gives JS-remainder results (e.g. span −1 → `lo`) | [V] |
| `_-eV(list, r)` #1068 | `shuffle` | for i in 0..n−1: swap `list[i]`, `list[next % n]` (n draws; **not** Fisher–Yates, biased) | [V] |
| `_-2P(n, r)` #1069, `_-W6l(n, r)` #1070 | not ported | random bit-set walk / random single-cycle permutation; no `R`/`I` caller found by the receiver script | [V] signatures only |

## 6. How the port is checked

1. `prng.emulate` runs the **actual method bodies** of the pinned ABC (#1011, #1013, #1142–#1144,
   #1068) with a ~100-line interpreter that knows only the opcodes those bodies use (unknown opcode →
   error) and applies AVM2 conversions (slot/param/return coercion, `Vector.<uint>` stores).
   `bht.py prng-verify` compares it with `prng.py` on 6 seeds × 256 draws, the 4 helpers on edge
   ranges, and the stream position afterwards. [V] `prng-verify --draws 1000` → OK.
2. Mutation check (done once, not committed): changing the index step, the `range_u32` wrap, the
   `range_i32` path or using Fisher–Yates each made `verify` report mismatches. [V]
3. Golden values in `tests/test_prng.py` were produced by the emulated bytecode (seeds 0, 1,
   0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, 123456789: draws 0–7 and 999; helpers on seed 42); the pure
   tests also compare with a ctypes reference written from the equations and with `swz.SwzRandom`.
   The game-gated test re-derives the goldens from the bytecode.

Limit: the emulator and the port share the conversion helpers (`to_i32`, `to_u32`, `js_mod`); those are
unit-tested against ECMAScript values, and the ctypes reference and `SwzRandom` use none of them.

## 7. Open points

- [H] → to check in Q2: which of the R/I draw sites run inside the fixed 16 ms step, and in what
  order (stream positions depend on it). Draws in `_-9D` (UI widget) and `MessageTrigger.Tick` from
  R are suspicious for determinism: find out whether they run during replay playback.
- Unknown: meaning of `_-Y1h`/`_-5J` (ItemManager, first two item draws).
- Unknown: whether any global-generator draw (§4) reaches simulated state (e.g. `Entity._-W2b` #3002
  uses `% 24` and a bit mask on `_-PW` draws).
- Not checked: `ByteArray.endian` of rollback snapshots; the runtime's `multiply_i` product width (§2).
