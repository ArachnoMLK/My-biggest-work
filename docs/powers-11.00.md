# Powers (attacks) — parser and column map (Q7, patch 11.00)

Pin: patch 11.00, abc `7d308423eaebcc82dfdda4ecc0e57d3abe78569534023aa7f9d776f626356db9`.

## Result

**[V]** `powerTypes.csv` (Game.swz) is parsed by **`PowerType.static._-A3R` #6483** (6,943 instructions).
The `Template` row returns at **@155**, the same offset brawlhalla-sim found for its 10.09 parser
(#6294 `PowerType._-L4o`, PC 155): the parser's start is unchanged between the two patches.

| | 10.09 (brawlhalla-sim) | 11.00 (here) |
|---|---|---|
| `powerTypes.csv` columns | 182 | **184** |
| `powerTypes.csv` records | 3,671 | **3,768** |
| `hurtboxTypes.csv` columns / records | 10 / 906 | **10 / 916** |

All 184 columns are read: 163 by name (table below), 21 `CastGfx.*`, `FireGfx.*`, `HitGfx.*` columns
through a prefix (`indexOf`, @1199–1946). Gfx columns are presentation only (brawlhalla-sim #34).

Re-check: `abc-find CastTime` (→ #6483 and its users), `abc-disasm --method 6483`, and for the map,
pair each `pushstring 'Column'` with the next `initproperty`/`setproperty` field.

## Column → engine field (11.00 only: names change every patch)

Built by pairing each column-name comparison with the next field assignment in #6483 (simple columns).
**Comma-separated vector columns are not in the table**: they are split into locals first and stored
later, e.g. `CastTime` @2349 (`split(',')` → local 6), `CenterOffsetX` @2390, `AoERadiusX` @1153;
`TargetMethod` is read @8711 (10.09: PC 8694). Check a field with `abc-disasm --method 6483` before
relying on it.

137 of the 163 named columns map directly to one field (the others are vectors or are
handled by code paths that do not store them right away).

| Column | Field | Column | Field | Column | Field |
|---|---|---|---|---|---|
| `AcceptInput` | `_-t2j` | `FixedMinChargeTime` | `_-5e` | `LoseInvulnTime` | `_-C3D` |
| `AirTimeMultOnly` | `_-h5f` | `FixedRecoverTime` | `_-f5c` | `MinCancelTime` | `_-i2o` |
| `AllowBGInterrupt` | `_-j3T` | `FixedStunTime` | `_-7Z` | `MinTimeBetweenHits` | `_-ue` |
| `AllowHitOnZeroDamage` | `_-B40` | `ForceFaceRight` | `_-m31` | `MinimumImpulse` | `_-A6P` |
| `AllowJumpDuringRecover` | `_-c34` | `ForceHitThroughSoftPlat` | `_-P4O` | `MirrorImpulseOffset` | `_-D1l` |
| `AllowLeaveGround` | `_-k2B` | `ForcePowerFacing` | `_-O3Q` | `MirrorOffsetCenter` | `_-36u` |
| `AllowMove` | `_-Y5V` | `GCVersion` | `_-E2S` | `MissionTags` | `_-W4t` |
| `AllowRecoverMove` | `_-r4W` | `GCancelTime` | `_-aO` | `MomentumVersion` | `_-j5c` |
| `AnimSourceMidLinePos` | `_-Z1v` | `GrabAnim` | `_-d3c` | `NoSlideCeilingBuffer` | `_-V67` |
| `AntigravTime` | `_-q12` | `GrabAnimSpeed` | `_-M0` | `OnHitCooldownTime` | `_-eQ` |
| `BGCastIdx` | `_-m3X` | `GrabForceUpdate` | `_-B32` | `OnlyOnceHitGfx` | `_-s3C` |
| `BGPowerOnFire` | `_-I3X` | `GrabInterpolateTime` | `_-f56` | `OnlyShakeOnce` | `_-o22` |
| `BackwardAccelMult` | `_-x21` | `HeldDirOffsets` | `_-i2e` | `OriginOverrideIfInMode` | `_-w3H` |
| `CanAssist` | `_-65m` | `HitAnimSource` | `_-66V` | `OriginPower` | `_-c5M` |
| `CanChangeDirection` | `_-J4b` | `HitReactAnim` | `_-x4D` | `OwnerFacingHitGfx` | `_-iM` |
| `CanDamageEveryone` | `_-g14` | `HitSoundEvent` | `_-z3M` | `ParentItem` | `_-g1L` |
| `CancelGravity` | `_-q1G` | `HoldHitEnts` | `_-i4o` | `PlayHitGfxBehind` | `_-M1i` |
| `CannotAttackAroundCorners` | `_-y2` | `HoldOffsetX` | `_-n56` | `PopulateActivePowerHits` | `_-a5o` |
| `CastImpulseX` | `_-C6Z` | `HoldOffsetY` | `_-R4P` | `PopulateBGHits` | `_-I3y` |
| `CastImpulseY` | `_-8S` | `Hurtbox` | `_-c5b` | `PostHitDamageMultiplier` | `_-C1s` |
| `CollisionPowerOffSetX` | `_-is` | `IgnoreButtonOnHit` | `_-x3C` | `PostHitImpulseMultiplier` | `_-Z4b` |
| `CollisionPowerOffSetY` | `_-96U` | `IgnoreButtonOnMiss` | `_-a3g` | `PowerID` | `_-H4O` |
| `ComboName` | `_-35E` | `IgnoreCDOverride` | `_-J5z` | `PowerName` | `_-f2O` |
| `ComboOverrideIfDir` | `_-f4j` | `IgnoreForcedFallTime` | `_-t2b` | `Priority` | `_-p3s` |
| `ComboOverrideIfHit` | `_-S1T` | `IgnoreGroundRestrict` | `_-41F` | `RecoverTime` | `_-Sp` |
| `ComboOverrideIfInterrupt` | `_-CD` | `IgnoreStrength` | `_-d6x` | `SelfImpulseOnHit` | `_-E4y` |
| `ComboOverrideIfRelease` | `_-D40` | `ImpulseMaxOnDCOnly` | `_-V2F` | `ShakeAllCams` | `_-Y6O` |
| `ComboOverrideIfWall` | `_-16G` | `ImpulseOffsetMaxX` | `_-l27` | `ShakeTime` | `_-I10` |
| `ComboUseSameSourcePos` | `_-424` | `ImpulseOnHeavy` | `_-4r` | `ShowCloudTime` | `_-t4z` |
| `ComboUseTargetAsSource` | `_-Ik` | `InheritAlreadyHit` | `_-54E` | `SigModeSwapsMove` | `_-o2p` |
| `ConsumesWeapon` | `_-M4f` | `InterruptThreshold` | `_-ro` | `SpeedLimit` | `_-u1G` |
| `CooldownTime` | `_-46C` | `IsAirPower` | `_-NT` | `SpeedLimitAttack` | `_-V43` |
| `CustomArtCastGfx` | `_-J4i` | `IsAntiair` | `_-Z1W` | `SpeedLimitAttackBackward` | `_-S2Y` |
| `CustomArtFireGfx` | `_-U3p` | `IsAttackFireGfx` | `_-42n` | `SpeedLimitBackward` | `_-M2J` |
| `DIMaxAngle` | `_-x1F` | `IsMultihit` | `_-s5N` | `SpeedLimitY` | `_-d5b` |
| `DelayCastGFXCleanUp` | `_-np` | `IsSignature` | `_-f3B` | `TeamTauntPower` | `_-W2E` |
| `DelayCastGfxToFirstFire` | `_-n5t` | `IsThrow` | `_-X6L` | `ToPointChangeDmg` | `_-W1P` |
| `DestroysItemOnHit` | `_-MS` | `IsWorldCastGfx` | `_-VH` | `ToPointChangeX` | `_-g1N` |
| `DisableShake` | `_-T4q` | `IsWorldFireGfx` | `_-55J` | `ToPointChangeY` | `_-k3P` |
| `DoNotBounceOffNoSlideCeiling` | `_-m5a` | `IsWorldHitGfx` | `_-R1j` | `TurnOffDampening` | `_-ud` |
| `DoNotSendSync` | `_-c6r` | `ItemHitElasticity` | `_-25X` | `Uninterruptable` | `_-C5G` |
| `DownwardForceMult` | `_-V13` | `ItemHitSoundEvent` | `_-T39` | `UpdateHeldEnts` | `_-n3i` |
| `EndOnHit` | `_-a3G` | `ItemSpeedDamage` | `_-538` | `UseCollisionAsTargetPos` | `_-T6m` |
| `ExhaustedVersion` | `_-M1g` | `ItemSpeedImpulse` | `_-w4x` | `UseCustomArtsFromCostume` | `_-D1B` |
| `FireGfxRotation` | `_-M2c` | `KeepGroundFriction` | `_-y25` | `WallCancel` | `_-Cb` |
| `FireImpulseMaxX` | `_-l27` | `LockTo45Degrees` | `_-U3z` |  |  |

## Clash arbitration

**[V]** `Priority` (`_-p3s`) is read by **`_-26u._-d3s` #1665**, the global phase that Q2 places in the
16 ms step after `_-E1V._-s4H` (see `docs/tick-loop-11.00.md`). For two hit records (`_-P6X`, locals 5 and
14) whose powers are `_-K6M`:

1. **different `Priority`**: the record with the lower priority gets `_-fP = true` (@1916–1953);
2. **equal `Priority`**: compare `_-P3I` of two entities (locals 7 and 6, looked up from the records'
   `_-82K` and `_-l18`) (@1810–1908): the higher one wins. `_-P3I` is the fighter's **Strength level**
   (`Entity._-p1E` #3049 @522–527, `docs/stats-11.00.md`);
3. **equal `_-P3I`**: compare `_-W22` (@1825–1869), the lower one wins; equal → no loser here.

[H] `_-fP` marks the loser of the clash, and locals 6/7 are the owners of the two clashing powers
(10.09: "Priority, then `_-F5f`, then `_-V6R`, then loser marking"); check the record fields
`_-82K` / `_-l18` before relying on the roles.

## Repeated hits (`MinTimeBetweenHits`)

**[V]** In `_-F5N._-T5A` #1731 (two copies of the gate, @340–413 and @671–744, for two target kinds),
with `t` = the power (local 3), `now` = parameter 2 and `prior` = the last hit time of this target
(`_-168(_-03K())` on the hit history, local 9):

- `present` = the target is in the hit history list (`_-x3r.indexOf(target) >= 0`, @342–356);
- if `present` and `MinTimeBetweenHits` (`_-ue`) `!= 0`: blocked = `prior + MinTimeBetweenHits > now`
  (`add_i`: int addition), so **equality admits**;
- if `present` and `MinTimeBetweenHits == 0`: **blocked** (one hit per target);
- not present: admitted.

Same rule as brawlhalla-sim on 10.09 (`_-M5v._-D3h`). `IsMultihit` is `_-s5N` and `InheritAlreadyHit`
`_-54E` (read in `_-l4X._-R63` #46 @3931).

## Knockback formula

**[V]** `_-26u._-u1x` #1674 `(PowerType, Entity attacker, Entity target, Number impulse, Number damage) → Number`
(the only caller is `_-26u._-76s` #1675, the hit application of the same system):

```
f       = (base + target.HPOffset + damage) / 100          base = target._-W22, or 50 when ScoringType._-U6g == 5
mult    = attacker.ImpulseMult (Strength), or 1.0          (1.0 when the power has _-Rc or _-d6x)
impulse = impulse * 0.75                                    when attacker and target are on the same team (_-25G)
                                                            and the power has no _-Rc (and attacker != target)
result  = max(impulse * (f + f * f / 2) * attacker._-Kc._-G4s * mult / target._-Kc._-13t - target.ImpulseNegation, 0)
```

`HPOffset` is `_-w3F` and `ImpulseNegation` `_-P1r` (StatTypes fields, `docs/stats-11.00.md`); `ImpulseMult`
is `_-z4f`. [H] `_-W22` is the target's **damage taken** (it is also the third tie-break of the clash
arbitration above); `_-Kc._-G4s` / `_-Kc._-13t` are the handicap "damage dealt" / "damage taken" factors
(brawlhalla-sim #26: handicap words); `_-U6g == 5` is a mode with fixed knockback.

**[V] Caller #1675** builds the two inputs:
- `damage` = the phase's damage `power._-L69[phase]` times several multipliers (@472–706), times the charge
  factor `1 + charge / power._-I6c * 0.25` (@1100–1132; ≥ 1.25 sets flag `4194304`), times the match
  setting `damage_multiplier / 100` (`_-I3W._-04o`, settings word 8) (@1152–1174);
- `impulse` = `power._-W1a[phase] + power.ImpulseOnHeavy (_-4r)` (@920–949), plus a charge term
  `0.5 * _-w4x * …` (@1038–1074), times the same charge factor (@1126–1132).

**[V] After the formula** (#1675 @1192–1644):
```
knock = u1x(...) + fixed + chargeExtra          fixed = power._-C7[phase] (+ charge term, capped when _-Q1u) (@951–1033)
knock = MinimumImpulse                          when MinimumImpulse (_-A6P) != 0, impulse != 0 and knock < it (@1213–1260)
knock *= 0.9                                    when the target has entity flag Entity._-B6B and ... (@1484–1532)
direction.normalize(knock)                      the knockback vector (@1640–1644)
```
So the **fixed part is added after the damage scaling**, the variable part is scaled by `f + f²/2`.

[H] `_-L69`, `_-W1a`, `_-C7` are the per-phase damage, variable-impulse and fixed-impulse vectors built
from `BaseDamage`, `VariableImpulse`, `FixedImpulse` (stored raw as `_-f5`, `_-c6N`, `_-A2b` by #6483
@10477–10560); `MinimumImpulse` = `_-A6P` is [V] from the column map.

## Damage and stun (#1675 @1692–1942) [V]

```
damage *= 2.0                       in one mode hook (_-N1k._-s3D._-H1g._-06A._-Z3E(target._-11)) (@1700–1756)
_-B6t(power, attacker, target, damage, ...)   applies the damage when damage != 0 (@1758–1781)
stun   = (power._-T6p[phase] if the vector exists else FixedStunTime) * 16     (multiply_i, @1785–1824)
stun  -= 5                          when power._-g4i == 11, damage > 0, power._-538 > 0, local 15 == 1, stun > 5
```
**`FixedStunTime` is in ticks**: the game multiplies it by 16 ms. [H] `_-T6p` is a per-phase stun vector.

## Next

- Phase vectors (`CastTime`, `AoERadiusX/Y`, `CenterOffsetX/Y`) and the active-power tick (10.09 #46
  `_-M5v._-81I`): find the 11.00 readers of their fields from the table above with `abc-find --member`.
- Arbitration by `Priority` (field in the table) and the repeated-hit rules (`MinTimeBetweenHits`,
  `IsMultihit`, `InheritAlreadyHit`).
