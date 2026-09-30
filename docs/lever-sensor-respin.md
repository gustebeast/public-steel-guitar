# Lever sensor board: re-spin spec

**From:** branner (the plastic side). **For:** bronner (the board). **Date:** 2026-09-21.
The housing CAD (`src/knee_lever.py`) is already built to this spec. Until the board is
re-spun, `elec/cad_geom_check.py lever_sensor` will report that the CAD board isn't the
routed board. That report is the handoff, not a regression.

## Summary (user decisions, 2026-09-21)

1. **The lever bus runs at 5 V**, not 24 V. The board can lose its 24 V buck.
2. **J1 is PH, not XH: S8B-PH-SM4-TB** (LCSC C265121), SMT side-entry, 8-way. Using a
   different family from the 24 V XH motor tees means **no harness can put 24 V on a lever
   board**. Stock is deep too: 19,469, against S8B-XH-A's 105. brenner's leg wiring uses PH as
   well.
3. **Single-sided**, like every board on the shared panel (`elec/fab.py`). J1 goes on the
   magnet face. The PH stands 5.5, so it fits the existing 6.4 gap to the housing with 0.9
   to spare: it never cuts the housing wall, and the magnet stack didn't have to move.
4. **Trim the top**, not the bottom. The foot pedal installs the board **turned over** so J1
   points down into the bar (the wiring hides in the trough). That puts the board's top edge
   toward the player-side face, where there's 10.15 of room.

## Coordinates

Looking at the **magnet face**. The origin is the MT6701 package centre, which sits on the
axle axis and isn't negotiable. **+X** points toward the lever (the knee side), **+Z** up
(the chassis side). All dimensions in mm. In the routed board's frame the chip is at
(11.0, −0.6), so routed x = spec x + 11.0 and routed y = spec z − 0.6.

## The spec

| Item | Routed now | **Spec** | Why |
|---|---|---|---|
| +X edge | +6.0 | **+4.025** | the groove grips CR_ENG (1.85) of this edge and U4's courtyard reaches +2.175, so the edge is the part plus the grip. Was +3.0, set against the 1.0 component-to-edge rule instead, which put the groove 0.87 inside the sensor's courtyard and 0.35 inside its bare body — the board fouled the slot on the way in |
| Top edge | +14.6 | **+10.1** | the turned-over pedal board's top faces the player: 10.15 of room |
| Bottom edge | −13.4 | **−11.8** | J1's 19.9 on end + the 1.0 edge rule at both ends |
| −X edge | −28.0 | −28.0 | unchanged; an upper bound, so shrink it if the 5 V board allows |
| **Outline** | 34.0 × 28.0 | **≤ 32.025 × 21.9** | the +X edge moved out 1.025; the −X edge and both Z edges are unchanged |
| **J1** | S8B-XH-A (THT) | **S8B-PH-SM4-TB** (SMT), on the **magnet face**, standing **on end** (length along Z, spec z −10.8 … +9.1), **mouth facing −X**, mouth face at x −24.95 (3.05 in from the −X edge) | |
| J1 pinout | `harness.xh_trunk_pins()` | the same four nets, **in on 1–4, out on 5–8**; +V is the **5 V** lever bus | |
| Sides | single | **single** | shared panel settings |

## Parts the outline displaces (routed layout)

- **+X trim:** TP1, TP2, TP3.
- **Top trim:** D1, L1, R1, U1, TP4. The 5 V bus removes the buck, which is likely where
  several of these live.
- J1 is a different part now, so its footprint is new in any case.

(The CAD's own pre-route table, `knee_lever.SENSOR_BOM`, reports the same kind of list in
`knee_lever.RESPIN_MOVES`: D1, L1, R1, U1. Those parts aren't drawn on the spec board.)

## Rules on the magnet face

1. **Edge groove bands:** the outermost **1.85** of the ±X edges. No parts except the MT6701.
   The magnet face is seated by these grooves only; the cradle's front plinth is relieved
   over the whole interior.
2. **Part height:** **≤ 1.75** anywhere except J1.
3. **Magnet-cap sweep:** any part taller than 1.5 keeps its whole footprint more than **5.66**
   from the origin.
4. **J1's zone:** its body, its 2.6 solder tabs, and the mated plug's 3.6 run past the mouth
   (x −28.55 … −16.35 over J1's z span) stay clear of other parts.

## Please check

- **J1's dimensions** are from JST's ePH datasheet, **side-entry** sections: p.4 (19.9 long,
  5.5 tall, 6.0 deep + 2.6 tabs), p.2 (mated 9.6 × 5.5), p.3 (PHR-8: 6.85 × 4.5). Note that
  B4B-PH-SM4-TB (6.6 tall, 5.0 deep) is the *top-entry* part on the same page, not this one.
- **Harness side:** PHR-8 housings, SPH-002T-P0.5S contacts and a PH crimp tool. Stock for
  those hasn't been checked yet.

## The +X edge is a MECHANICAL keep-out, not a fabrication one (2026-09-29)

JLCPCB's component-to-edge rule is 1.0 mm and every part on this board clears it. That
is not the rule that binds here. The board is retained by sliding down a GROOVE, and the
groove is material that grips `CR_ENG` = 1.85 mm of each X edge — so anything standing
within 1.85 mm of an edge has to pass through the housing on the way in.

U4 is centred on the axle axis by definition (it is the sensor), its courtyard reaches
2.175, and the edge was at 3.0. The groove's inner face therefore sat at 1.30: 0.87
inside the courtyard, and 0.35 inside even the bare 3.0 mm QFN body. Measured by sliding
the populated board up its own install axis, the sensor fouled the housing by 3.05 mm³
about 11 mm up the stroke, on both levers.

`src/knee_lever.py` now asserts this against the generated BOM, both edges, so a part
that moves into a groove band stops the build instead of being found in a render.
