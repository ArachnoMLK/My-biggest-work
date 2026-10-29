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

## Next

- Phase vectors (`CastTime`, `AoERadiusX/Y`, `CenterOffsetX/Y`) and the active-power tick (10.09 #46
  `_-M5v._-81I`): find the 11.00 readers of their fields from the table above with `abc-find --member`.
- Arbitration by `Priority` (field in the table) and the repeated-hit rules (`MinTimeBetweenHits`,
  `IsMultihit`, `InheritAlreadyHit`).
