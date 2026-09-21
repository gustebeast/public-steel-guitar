# bronner loop worklist (started 2026-09-21)

The /loop re-reads this each tick. Tick = take the top OPEN item, do it, commit, re-render
(copy scratch.step -> assembly.step: the user's "bronner" FreeCAD tab tracks assembly.step),
mark it here. Items needing the user go to NEEDS USER, not skipped silently.

## OPEN
2. Widen the instrument body -Y so string 10's motor + its wiring fit WITHOUT the chassis
   wall cutout (M9 notch) (user). keyhead_endplate / chassis / wiring trough (WT_SKIP) all
   derive from it -- find the datum (rail Y) and move it; widen live set if needed.
3. Motor controller CAD vs routed board: 52/60 (hand MCTRL_BOM table). Migrate
   motor_ctrl_pcb to board_geom.solid like the output board (keep MCTRL_J/mctrl_pt API).
4. Optical board CAD vs routed: 25/156 footprints match. Rebuild the CAD from geom.
5. Optical board DRC: 20 courtyards_overlap errors -- verify intentional (sensor triplets)
   or fix; document.
6. lever_sensor CAD board 21.4x28 vs routed 34x28 -- fix the CAD board (housing re-cut is
   OWNER branner: message them rather than editing their part).
7. Pre-existing cable-vs-cable run-throughs (tools/check_cable_pairs.py: 9 pairs, worst
   wire_canh_0 x wire_pwr_hot_2 9.5 mm3, wire_canh_1 x wire_canl_0 9.2).
8. Output board open design items: D5 clamp has no part number; J1 USB-C shield SH pads
   <no net>; audio section (DAC/ADC pinouts invented, DAC on 5V, SCKI/BCK, buffer clipping)
   -- fix what can be verified from datasheets, list the rest.
9. Optical sourcing blocks (VEMD4110X02 not on LCSC, H743 stock 7) -- look for in-stock
   alternates; decision likely NEEDS USER.
10. Checkpoint: agent_sync submit once 1-2 land (commits 4faab2c..f52686c + later).

## DONE
- Pi cradle = column frame cut by keyhead_endplate._slot_shadow (bbda046); ceilings 6587->2582
- M4 through-board ears (a98762e), motor controller frame cradle + ear screws (f52686c)

## NEEDS USER
- keyhead height-prism roof over the merged slot for strings 8-10: 18.3 mm bridge at x -609.5
  (pre-existing; the Pi plate used to cover it). Roof takes the inserts' string load; a 45 deg
  gable needs 9.2 mm and the Pi board is 7.8 above. Options: move the Pi +X ~2 mm, or reshape
  the 8-10 slots (owner of nut_block geometry?).
