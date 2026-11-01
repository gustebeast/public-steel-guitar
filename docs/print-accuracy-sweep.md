# Print accuracy sweep, 2026-11-01

Report only. No geometry changed. Fixes follow only from measured error (user rule), and
this is slicer output, not a print: nothing here has been measured on a real part.

**Run:** `py -3.12 tools/slicer_sweep.py`, about 7 minutes. `cadkit.slicer_check` on main at
a1bb0d999, every exported printed part except `test_*`, in print pose, on the 0.8 nozzle
profile (0.40 mm PETG GF). 61 parts. The two pedal lids are 330 long and do not fit the bed
as exported, so they were measured turned 45 degrees.

**Update, same day, after the follow-ups below:** the 0.010 seam film is gone, the lids run at 45
degrees in the tool, and the pulleys ran on both nozzles. Real runs went from 393 to 386 and their
error volume from 5,174 to 703 mm3. The tables below keep their first-pass ranks; the follow-up
section overrides ranks 1, 4 and 6.

## How to read the numbers

Two things produced impossible first results (errors of 40 to 60 mm) and were corrected:

- **Base and colour STEPs do not line up.** Each is re-centred on export. Deck panels and
  chassis segments are measured from the build cache, fused, in assembly pose.
- **Layer rounding read as lateral error.** A bridge or ceiling one layer off the mid-layer
  section reads as its whole span. A lateral error now counts only if beads of layer i miss
  the model at layers i-1, i and i+1. This hides ordinary stair-stepping on purpose; shelf
  heights stay visible as ZSTEP.

Site counts: 844 lateral sites, of which 451 are spots under 0.5 long on 1 or 2 layers, mostly
single bead ends, not ranked. 393 are real runs, 229 of them with typical error 0.3 or more.
457 ZSTEP. Functional and cosmetic below are my judgement from the face each site sits on and
the plots; I did not trace every site to its feature, so treat those labels as inferred.

## Ranked: functional surfaces

| Rank | Part | Where | Typical error | Note |
| --- | --- | --- | --- | --- |
| 1 | `chassis_0/1` | Ø5.1 feature, x -200.2 and -418.7 near each seam, both rails (17 sites) | 1.5 EXCESS, 6.9 long | Beads fill a thin lens of void beside the bore. Feature not identified: check whether anything enters that bore |
| 2 | `adjust_tenon` | acute notch, flat face at (-58.0, -72.1) | 0.81 EXCESS, 9.6 long | Bead fills the notch. Matters only if the notch is a mating relief |
| 3 | `pedal_bar_a` | Ø4.4 holes (3 sites) | 0.79 EXCESS, 1.6 long | Short, one bead intruding |
| 4 | `chassis_2` | Ø8.4 at x -626.9, four sites | 0.59 MISSING, 9.7 long | Bottom 10 mm of the bore. Feature not identified |
| 5 | `pedal_bar_a/b` | R8.05 (5 sites) | 0.49 MISSING, 2.5 long | Short |
| 6 | `screw_pulley_hi/lo`, `motor_pulley` | tips at Ø8.4, about 14 per pulley | 0.40 MISSING, 4.9 long | Belt teeth under a 0.8 bead; see below |
| 7 | `belt_tensioner_half_a/b` | rib tips, every 2.0 | 0.45 MISSING, 4.8 long | Not an open issue: these are printed on 0.4 and bench-proven |
| 8 | `body_adapter*` | R0.8 fillets (26 sites) | 0.36 MISSING, 1.7 long | Bead rounding a small fillet |

**Pulleys:** if these are printed on 0.8, tooth tips stand 0.4 short on every tooth, the only
repeated error on a surface that transmits load. This sweep used the 0.8 profile and I did not
establish which nozzle they print on. Re-run them on 0.4 before reading anything into it.

**Shelf heights (ZSTEP), worst by area:** chassis floor at 9.84 is 0.161 off a layer on all
three segments; `kv_housing` 46.60 is 0.200 off; `pedal_bar_a/b` 41.75 is 0.150 off;
`keyhead_endplate` 26.66 is 0.137 off. Worth a look only where a part seats on that face.

## Ranked: cosmetic or no effect

| Part | Where | Typical error | Note |
| --- | --- | --- | --- |
| `top_plate_3/4` | V between the fret board M4 boss and its wall | 2.15 EXCESS, 5.4 long | Gap fill closes the V, above the board |
| `top_plate_3/4` | -X end of the +Y wall, x -358 and -605 | 1.5 to 2.5 EXCESS, 3.4 long | Same junction shape |
| `keyhead_endplate` | stub ribs at x 19.0, x -33.3 | 0.82 to 1.1 EXCESS, 11 long | Bead overruns a small T junction |
| `pickup_zplate` | near (4.3, -55.3) | 2.14 EXCESS, 2.6 long | One layer |
| `kv_housing` | flat at y -18.8 | 0.68 EXCESS, 2.8 long | Short |

## Not print error: model quirks that top a raw ranking

- **`chassis_0/1/2` seam film, about 4,400 of the 5,174 mm3 total. FIXED.** A wall 0.010 thick
  closed the seam cavity's mouth (x -426.829 to -426.819 on `chassis_1`, 443 mm2). `_seg_box` runs
  each segment 0.01 past its split and the cavity started on the split. The cavity now starts
  0.02 back (`_SEG_OVER`, through `halves(drop=)`). It never printed, so no part changes.
- **`bridge_endplate` R5.9, 6.1 MISSING, 23.6 long, z 9.8 to 11.0.** The section runs along the
  crown of a horizontal cylinder, so the outline is a long thin strip. Not 6 mm of missing
  material. Not confirmed by section beyond the one layer plotted.
- **`chassis` R11.4, 2.0 MISSING, one layer at z 25.4**, four sites. Same shape of result.

## Should `print_corners.Printed` be wired in?

**No, not across the board.** After the film, nearly all the remaining error is small and on
vertical corners: 352 runs stand up the layers and 238 of them are typical error under 0.5.
`Printed` redraws a corner at the radius it prints. That makes the model agree with the print
and moves no bead, so it would shrink this report without changing one part. The fits that
matter are already tuned on printed coupons. None of the ranked functional items above is a
plain corner on a joint, which is the case `Printed` exists for.

Use it only where a specific fit binds at a corner, on a real print.

## Follow-ups

**The Ø5.1 is not a bore.** It is the R2.55 corner of the seam joint's cavity, axis Z, at
(-201.62, 59.40) and (-201.62, -109.85) on `chassis_0`, the same on `chassis_1` at x -420.02.
The tenon of the next segment enters it: `chassis_1`'s into `chassis_0`, `chassis_2`'s into
`chassis_1`. Drawn clearance is 0.55 (`_SEG_CLR`). Measured from the sliced beads against the
tenon, layer by layer: **0.34 at the tightest**, so 1.5 of EXCESS sits in the cavity's narrow tip
and the tenon does not reach it. No fix: 0.34 is thinner than drawn, but 0.35 and 0.40 are known
to fit on this joint (plate 8 D3). Nothing else is within 3.85 of those faces.

**The Ø8.4 is the nut-height screw recess** in the `chassis_2` floor, R4.20, axis Z, z -81.19 to
-71.35, at x -623.26 and the other stations. `nut_height_screw_N` enters it: a head of Ø7.6, 0.40
radial clearance drawn, and 0.40 is also what the build reports to `nut_height_screw_2` and `_8`.
The error is MISSING, so the printed wall stands back from the head and clearance goes up, not
down. No fix.

**Pulleys, PCTG, both nozzles. They print on 0.4 (user, 2026-11-01), so the 0.8 column does not apply:**

| Part | 0.8 nozzle | 0.4 nozzle |
| --- | --- | --- |
| `motor_pulley` | 13 tooth runs, 0.41 MISSING | no site over 0.20 |
| `screw_pulley_hi` | 14 tooth runs, 0.40 MISSING | no site over 0.20 |
| `screw_pulley_lo` | 14 tooth runs, 0.40 MISSING | no site over 0.20 |

**Pedal lids:** `pedal_lid_b` has no lateral site, `pedal_lid_a` one short run, 0.93 over 3.1.
Whether they really print diagonally is still open: 330 long does not fit the bed square.

**After the film, the largest real runs are** the `bridge_endplate` crown (not print error), the
fret board boss V on `top_plate_3/4` (cosmetic), then the `chassis_2` recesses above. Nothing left
on a fit calls for a geometry change.
