# bronner loop worklist (started 2026-09-21)

The /loop re-reads this each tick. Tick = take the top OPEN item, do it, commit, re-render
(copy scratch.step -> assembly.step: the user's "bronner" FreeCAD tab tracks assembly.step),
mark it here. Items needing the user go to NEEDS USER, not skipped silently.

## OPEN
11. motor_ctrl respin -- bus B becomes a 5 V PH pass-through (handed over by branner):
    * J2 -> S8B-PH-SM4-TB (LCSC C265121, SMT side-entry), trunk IN on ways 1-4, OUT on
      5-8, in elec/harness.py's pin order: the controller is a MID-BUS node now (user
      topology option B -- pedals and the lever chain both arrive at -X).
    * J2's +V moves off v24 to the board's 5 V rail (U5 out). CHECK U5 HEADROOM: ~11
      nodes x ~50 mA = ~0.5 A on top of its existing 5 V loads.
    * DROP the bus-B 120 ohm termination (end-of-bus part; the controller is no longer an
      end). Keep bus A's. Termination now = JP1 + R4 closed on exactly two boards, the
      +X-end lever and the far-end pedal.
    * Stale header comment: bus B has 11 sensor boards (6 knee levers + 5 pedals), not 8.
    * Board spec: docs/lever-sensor-respin.md. cad_geom_check lever_sensor MISMATCHES until
      the lever board is re-spun -- that is the handoff, not a regression.
12. LED strip re-spin for direct board-to-board (user, 2026-09-22): 2x3 right-angle
    2.54 mm pair (male PZ254R-12-6P C492431 / female C56182 or SMD C22373944) at both ends,
    in the DRIVER band where the board is empty, so the LED band runs to 5.75 mm of each
    edge and the pitch (~15.9) is UNIFORM ACROSS THE JUNCTION. PH stays on EVERY board
    (user: fit it if spacing allows, else a special section 1) -- it fits in the same free
    driver band, -69.5..-40.5 is empty until driver 1.
10. Next checkpoint submit after 3-7 land.

## DONE
- Output board analog rewrite from datasheets: PCM1808/PCM5102A/CH334F/G6K/ESD5B5, MCLK pin 39,
  VBAT, mid-rail buffers; 0 unconnected 0 violations, all USB groups pass; fab builds (415264e)
- layout.py: all duplicate-numbered pads get their net (USB-C SH); SMD stitch exceptions honoured
- motor_ctrl VBAT tied to 3V3 (e1e2d26)
- Motor ctrl J4 USB-C -> top-entry XH (+ USB-A->XH lead in BOM), re-routed clean (bd63bb4)
- Output-board tray: rectangle not bbox, -X open, J2 pad moved, 45 deg gussets (75dbea2)
- Cable run-throughs 9 -> 0: trunk conductors on their own pins + per-conductor heights (0ee4419)
- Optical 20 courtyard overlaps: already declared + verified intentional (PDnA/PDnB vs own Dn, optical.py docstring) (item 5)
- lever_sensor CAD size: branner-owned (knee_lever.py); handed to lead for branner (item 6)
- Motor ctrl CAD from routed geom; checker box-centre fix -> output 60/60, mctrl 60/60, optical 156/156 (items 3+4)
- Body widened 2.8 -Y (chassis.RAIL_GAP), notch gone, pigtail 9 + bus B rerouted (a1ad309)
- SUBMITTED eabbc571 (4faab2c..a1ad309)
- Pi cradle = column frame cut by keyhead_endplate._slot_shadow (bbda046); ceilings 6587->2582
- M4 through-board ears (a98762e), motor controller frame cradle + ear screws (f52686c)

## NEEDS USER
- Optical re-route after grounding the USB-C shell tabs (layout.py: stitch exceptions skip PTH
  pads too): 25 passes -> TIA_OUT_1B open, 28 -> TIA_IN_8A open (freerouting re-plans every
  net). UNCOMMITTED in the tree (layout.py, optical.py passes 28, optical geom). Superseded by
  the photodiode redesign (SFH 2400 FA-Z + per-channel RC), which re-places and re-routes the
  whole sensing row anyway -- fold it into that.
- Optical sourcing (lcsc_check 2026-09-21): VEMD4110X01 photodiode C3211080 = 95 in stock /
  20 per instrument (4.8 builds); S8B-XH-A C157914 = 88 / 21 (4.2 builds); SPX3819 62,
  USB3343 77, K3A26 108 (1/instrument, fine). Stocked alternate PIN photodiode Everlight
  PD15-22C/TR8 (LCSC C131271, 940 nm, 6 pF, 4.2 uA @1mW/cm2) is 3.3 x 2.8 mm -- does NOT fit
  the 1.6 mm optical pitch (0805 geometry); adopting it means re-doing the sensor layout.
  Choice: order VEMD4110X01 elsewhere + consign, or redesign around a bigger PD.
- Output board analog DESIGN choices to confirm: pickup load 1M (tone), coupling corners
  (1.6 Hz pickup, 16 Hz relay path), DAC -6 dB pad; independent datasheet re-check before fab.
- Optical triplet land narrowing (0.20 -> 0.35/0.45 gap): both widths broke the LED supply
  chain (V5_PRE) the router lays past the lands; reverted to stock. Doing it needs the V5_PRE
  chain given its own deliberate route (inner layer) first.
- keyhead height-prism roof over the merged slot for strings 8-10: 18.3 mm bridge at x -609.5
  (pre-existing; the Pi plate used to cover it). Roof takes the inserts' string load; a 45 deg
  gable needs 9.2 mm and the Pi board is 7.8 above. Options: move the Pi +X ~2 mm, or reshape
  the 8-10 slots (owner of nut_block geometry?).
