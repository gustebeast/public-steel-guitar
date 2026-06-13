# Bill of Materials — purchased parts

Sourcing for the bought parts (printed parts are built from `src/`). Links were
checked for a real, in-stock listing at the spec; prices are approximate and per
the date of writing — re-validate before ordering. Avoid Amazon per project
preference. See `electromechanical-pedal-steel-spec.md` §12 for the fuller
rationale. The **motors dominate cost** (~$220 of ~$370 total); everything else
is commodity.

| Part | Spec | Qty | Source (verify stock) | ~Price | Notes |
|------|------|-----|--------|--------|-------|
| **Drive belt** | GT2 (2 mm pitch) open, **5 mm wide** | ~6.5 m | [Bulkman3D GT2 open belt](https://bulkman3d.com/product/gt000-gt0003/) | ~$0.5–1.7/m | cut-to-length, splice into loops with the printed clamp |
| **Drive motor** | MKS SERVO42D, NEMA17, **CAN** variant | 10 | [P3D](https://p3d.mx/products/makerbase-mks-servo42d-nema17-foc-motor) · [ElectroPeak](https://electropeak.com/mks-servo42d-nema17-closed-loop-stepper-motor) | $22 ea | pick the "CAN MB/MT" option; in stock |
| **Lead screw + nut** | Tr5×1 trapezoidal (5 mm, 1 mm lead, 1-start, self-locking) + brass nut | 10 | [eBay Tr5×1 + brass nut](https://www.ebay.com/itm/396869709608) · mfr [ALM](https://www.autolinearmotion.com/5mm-trapezoidal-lead-screw.html) | ~$3 ea | cut to ~61 mm; eBay listings rotate—AliExpress/ALM are stable fallbacks |
| **Screw support bearing** | MR85ZZ deep-groove, Ø5 × Ø8 × 2.5 | 10 | [Bearings Direct](https://bearingsdirect.com/mr85-zz-mini-ball-bearing-5x8x2-5-shielded-l850zz/) · [Trianglelab](https://trianglelab.net/products/mr85zz) | $0.5–4 ea | + a Ø5 thrust washer for the axial string pull |
| **Axial retainer** | Ø5 set-screw shaft collar (or a 2nd Tr5 nut) | 10 | [ServoCity 5 mm collar](https://www.servocity.com/2920-series-steel-set-screw-collar-5mm-bore-2-pack/) | ~$2.5 ea | locks the screw against the support bearing |
| **Bridge bearing** | 693ZZ deep-groove, Ø3 × Ø8 × 4 | 10 | [VXB 693ZZ ×10](https://vxb.com/products/693zz-3x8-shielded-3x8x4-miniature-bearing-pack-of) · [Bearings Direct](https://bearingsdirect.com/693-zz-mini-ball-bearing-3x8x4-shielded-r830zz/) | ~$1 ea | one per string; string rides the Ø8 OD |
| **Bridge axle** | Ø3 **g6/h6 precision shaft**, ~105 mm (e.g. hardened ground shafting) | 1 | [McMaster 3 mm shafts](https://www.mcmaster.com/products/linear-shafts/) | ~$3 | NOT an m6 dowel — m6 is press-fit in a 693ZZ bore; the shaft must slide through all 10 bearings + 9 comb fingers + both arms. Glue dab at the arms retains it |
| **Guide rod** | Ø2.5 × 28 mm hardened/ground dowel (DIN 6325, standard length) | 10 | [McMaster](https://www.mcmaster.com/products/hardened-dowel-pins/) · [eBay DIN6325 2.5 mm](https://www.ebay.com/itm/303389911894) | ~$0.5 ea | anti-rotation; drops in from the top through the stop bar's snug hole + the carriage's C-bore, landing in a blind socket — friction-held both ends (dab of glue optional) |
| **Nut break dowel** | Ø2 × 4 mm steel dowel (52100) | 10 | [McMaster 91595A018](https://www.mcmaster.com/91595A018/) | $12.70 / pack | gauged break pins (the scale "0"); drop into their slots from above. (Clamps bear on solid PA6-GF — no anvil.) |
| **M4 cup-tip set screw** | M4 × 0.7 cup-tip, 10 mm, alloy | 10 | [McMaster 91390A114](https://www.mcmaster.com/91390A114/) | $7.28 / pack 100 | clamps each plain string end onto its anvil |
| **M4 heat-set insert** | M4 × 0.7 brass heat-set, 4.7 mm | 20 | [McMaster 94459A150](https://www.mcmaster.com/94459A150/) | $10.82 / pack 50 | 10 nut clamps + 6 nut-block/pickup + 4 leg-sleeve pinch collars; deeply buried (no pull-out) |
| **M4 mount screw** | M4 × 0.7, 12 mm, 18-8 SS (button or socket head) | 10 | [McMaster 92095A192](https://www.mcmaster.com/92095A192/) | $14.77 / pack | 4 nut-block corner bolts + 2 pickup X-lock stations (printed knobs pressed on their heads) + 4 leg-sleeve pinch bolts, all into 94459A150 inserts; **M4 × 0.7** (coarse) to match the inserts — NOT the M4 × 0.5 fine-thread 90751A120 |
| **Fasteners** | M3 (NEMA17 mounts), M2 (belt clamps) | — | [McMaster](https://www.mcmaster.com/) | — | commodity |

## Electronics (compute bay)

The printed tray in the keyhead bay carries tool-free snap mounts for the full
PRO stack; a BASIC build populates only the first two rows and leaves the rest
of the sockets empty (the upgrade is drop-in). Panel I/O (1/4" TS line out, DC
power inlet, USB-C) mounts through the recessed wall in the bridge endplate's
lower corner — the instrument's right face.

| Part | Role | Qty | Source | ~Price |
|------|------|-----|--------|--------|
| **Teensy 4.1** | basic+pro: sensors, CAN servo loop, UI, USB audio | 1 | [PJRC](https://www.pjrc.com/store/teensy41.html) | $32 |
| **Teensy Audio Shield** | line-in ADC + line out (SGTL5000) | 1 | [PJRC](https://www.pjrc.com/store/teensy3_audio.html) | $16 |
| **CAN transceiver** | SN65HVD230 breakout (logic ↔ CAN-H/L) | 1 | [Adafruit/DigiKey](https://www.digikey.com/) | $3 |
| **Raspberry Pi 5** (pro) | 10ch audio→MIDI + Dexed + USB audio gadget | 1 | [official resellers](https://www.raspberrypi.com/products/raspberry-pi-5/) | $60–80 |
| **CS42448 TDM board** (pro) | 6-in ADC each; ×2 stacked = 10ch analog in | 2 | community boards / [Tindie](https://www.tindie.com/) | ~$35 ea |
| **Buck module** | 24 V → 5 V for Pi + Teensy | 1 | DigiKey/Pololu | $5 |
| **1/4" TS panel jack** | analog line out | 1 | [Switchcraft via Mouser](https://www.mouser.com/) | $4 |
| **DC barrel panel jack** | 24 V power inlet (servo bus + buck) | 1 | Mouser/DigiKey | $2 |
| **USB-C panel module** | panel-mount extension (2× M3 flange) | 1 | Mouser/DigiKey | $6 |

The motor still does all tuning (the nut block clamps; no manual tuners). The nut
block is **reprintable per string set** — `STRING_GAUGE` in `dimensions.py` swaps
between E9 and C6; the break pins re-gauge so string tops stay coplanar.

Printed parts (no purchase): carriage, bridge_endplate, chassis (×3 segments),
nut_block, belt_clamp, screw_pulley, motor_pulley, tension_fork (graded
belt-tension lock set), pickup_bar/pickup_jaw/pickup_shim (adjustable pickup
mount — all its hardware comes from the M4 insert/set-screw packs above),
and the adjustable legs: leg_socket ×4, leg_segment ×8, leg_sleeve ×4,
leg_shaft ×4 (PCTG/PA6-GF) plus leg_foot ×4 and leg_washer ×12 in **TPU**
(anti-unscrew preload washers + floor-friendly feet)
— see `py -3.12 -m src.build --list`.
