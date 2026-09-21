# Lever sensor board: re-spin spec

**From:** branner (the plastic side). **For:** bronner (the board). **Date:** 2026-09-21.
The housing CAD (`src/knee_lever.py`) is already built to this spec. Until the board is
re-spun, `elec/cad_geom_check.py lever_sensor` will report that the CAD board isn't the
routed board. That report is the handoff, not a regression.

## Why re-spin

The routed board (`elec/geom/lever_sensor.geom.json`, 34 × 28) puts J1, an S8B-XH-A
side-entry header, on the **magnet face**. That face sits 6.4 mm from the housing's +Y
wall, and the XH body stands 7.0, so the cradle had to cut into the housing wall. The cut
went through the 1.6 mm wall beside the half-stop spring pocket. The 34 × 28 outline also
doesn't fit the housings. Measured from the sensor chip, it reaches up 14.6 (LKL allows
11.3), down 13.4 (the foot pedal allows 10.1), and 6.0 toward the lever (the pedal allows
about 3).

## Coordinates

Looking at the **magnet face** (the MT6701 side). The origin is the MT6701 package centre,
which sits on the axle axis and isn't negotiable. **+X** points toward the lever, i.e. the
player's knee face. **+Z** points up, toward the chassis. All dimensions in mm.

## The spec

| Item | Spec |
|---|---|
| Outline | x −25.0 … +3.0, z −10.1 … +11.3 → **28.0 × 21.4**, the pre-route envelope, checked against all four in-plane orientations of LKL, LKV and the foot pedal |
| Sensor | MT6701 centred on the origin (as now) |
| **J1 part** | **B8B-XH-A**: top-entry, 8-way, 2.5 mm pitch. **The CAN tee's own trunk connector** (`elec/can_tee.py` J1): same XH family, crimps and 8-way housing. **Pinout unchanged**: `harness.xh_trunk_pins()`. |
| **J1 side** | **BACK face** (away from the magnet). The plug exits straight out the back. |
| J1 placement | Pin row **along X at z = +8.3**, pins at x −20.4 … −2.9 (centre −11.65). Body x −22.85 … −0.45, z +4.55 … +10.3: the body's short side (2.0 from the row) toward the top edge, 1.0 in from it. |
| Why up there | The board drops into its slot past the spinning magnet cap. J1's post tails stand **1.8 proud of the magnet face**. Anything below the axle passes the cap on the way down; the top band never does. |

## Keep-outs on the magnet face

1. **J1 pad row:** x −21.4 … −1.9, z +7.3 … +9.3. No parts. The pre-route layout in the CAD
   (`knee_lever.SENSOR_BOM`) has **C1, C2, D1, L1, U1** there (`knee_lever.CONN_PAD_CONFLICTS`).
   The overlap gate carries the U1/L1 tail contacts as DEFERRED, owner bronner.
2. **Edge groove bands:** the outermost **1.85** of the ±X edges (x −25.0 … −23.15 and
   +1.15 … +3.0). No parts except the MT6701 itself. The board's magnet face is seated
   **only** by these grooves now; the cradle's front plinth is relieved over the whole interior.
3. **Part height:** **≤ 1.75** anywhere on the magnet face (the plinth relief's depth).
4. **Magnet cap sweep:** any part **taller than 1.5** must keep its whole footprint more
   than **5.66** from the origin (unchanged rule).

## Please check

- **Assembly cost.** The old layout put the connector on the magnet face on purpose, to keep
  the board **single-sided**, because double-sided assembly carries a per-order setup fee.
  J1 on the back is a through-hole part on the bottom side: confirm how JLCPCB prices that
  (a hand-solder or second-side fee) before routing.
- **Whether the circuit fits** 28 × 21.4 once only J1's pad row takes space on the magnet
  face. The pre-route layout held the whole circuit **plus** an 8-way PH on that face.

## Not in the spec (the plastic side will handle these)

- On the **foot pedal**, the board installs turned over (180°), so J1 lands low and its plug
  runs along the bar. That cable route is branner's to check.
- The plug sticks out about 10 mm behind the board, plus the cable's bend. That costs some of
  the knee-depth slide's +Y travel, which the user accepted when choosing this option.
