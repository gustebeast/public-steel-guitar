# Lever sensor board: re-spin spec

**From:** branner (the plastic side). **For:** bronner (the board). **Date:** 2026-09-21.
The housing CAD (`src/knee_lever.py`) is already built to this spec. Until the board is
re-spun, `elec/cad_geom_check.py lever_sensor` will report that the CAD board isn't the
routed board. That report is the handoff, not a regression.

## Summary

The board **stays single-sided**, like every board on the shared panel (`elec/fab.py`).
**J1 stays exactly as routed:** an S8B-XH-A side-entry, through-hole part (the CAN tee's
trunk connector), on the magnet face, standing on end at the −X edge, mouth facing −X.
Only the **outline is trimmed**, plus a handful of parts that trimming displaces. The
plastic now makes room for J1 on its side: the magnet/board stack moved out 0.9 mm, so J1
no longer cuts the housing wall.

## Coordinates

Looking at the **magnet face**. The origin is the MT6701 package centre, which sits on the
axle axis and isn't negotiable. **+X** points toward the lever (the knee side), **+Z** up
(the chassis side). All dimensions in mm. In the routed board's own frame the chip is at
(11.0, −0.6), so routed x = spec x + 11.0 and routed y = spec z − 0.6.

## The spec

| Item | Routed now | **Spec** | Why |
|---|---|---|---|
| +X edge | +6.0 | **+3.0** | the foot pedal's bar-top face, with the cradle web outboard of the edge |
| Top edge | +14.6 | **+10.1** | the pedal installs the board **turned over** (J1 down into the bar), so the top edge faces the player, and there is 10.15 of room there |
| Bottom edge | −13.4 | **−14.3** | so J1's 22.4 still fits on end with the 1.0 edge rule at both ends |
| −X edge | −28.0 | −28.0 | unchanged |
| **Outline** | 34.0 × 28.0 | **31.0 × 24.4** | |
| J1 | S8B-XH-A, on end at the −X edge, mouth −X | **same part, same face, same orientation**, mouth 1.65 in from the −X edge, **re-centred on the new height** (spec z −13.3 … +9.1) | |
| Sides | single | **single** | shared panel settings |

## Parts the trim displaces (routed layout)

- **+X trim:** TP1, TP2, TP3.
- **Top trim:** D1, L1, R1, U1, TP4. J1 also moves down about 0.9 mm with its re-centring.

(The CAD's own pre-route table, `knee_lever.SENSOR_BOM`, reports the same kind of list in
`knee_lever.RESPIN_MOVES`: D1, L1, R1, U1. Those parts aren't drawn on the spec board.)

## Rules on the magnet face (unchanged)

1. **Edge groove bands:** the outermost **1.85** of the ±X edges. No parts except the MT6701.
   The magnet face is seated by these grooves only; the cradle's front plinth is relieved
   over the whole interior.
2. **Part height:** **≤ 1.75** anywhere except J1.
3. **Magnet-cap sweep:** any part taller than 1.5 keeps its whole footprint more than **5.66**
   from the origin.
4. **J1's zone:** its body plus the mated plug's 7.5 run past the mouth (x −33.85 … −20.25 over
   J1's z span) stays clear of other parts.

## Please check

- **Stock:** S8B-XH-A (LCSC C157914) showed **105 in stock** on 2026-09-21, against 21 needed
  (levers + pedals + tees). Check JLCPCB's assembly library too, which draws from its own stock.
- **The planned 5 V lever bus** (user, 2026-09-21) would change this board: no 24 V buck, and
  possibly a different connector to key the 5 V lever bus apart from the 24 V motor tees. If
  that goes ahead, this spec's outline and J1 are up for revision. The housing follows
  whatever envelope the re-spin lands on.
