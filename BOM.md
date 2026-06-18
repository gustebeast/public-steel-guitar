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
| **M4 cup-tip set screw** | M4 × 0.7 cup-tip, 10 mm, alloy | 13 | [McMaster 91390A114](https://www.mcmaster.com/91390A114/) | $7.28 / pack 100 | clamps each plain string end onto its anvil (10) + 3 pickup-carrier height screws (the pickup rests on their tops; turn to set the string gap) |
| **M4 heat-set insert** | M4 × 0.7 brass heat-set, 4.7 mm | 17 | [McMaster 94459A150](https://www.mcmaster.com/94459A150/) | $10.82 / pack 50 | 10 nut clamps + 4 leg-sleeve pinch collars + 3 pickup-carrier height-screw bosses; deeply buried (no pull-out) |
| **M4 mount screw** | M4 × 0.7, 12 mm, 18-8 SS (button or socket head) | 5 | [McMaster 92095A192](https://www.mcmaster.com/92095A192/) | $14.77 / pack | 1 pickup X/Y clamp screw (pulls the pickup flat to the -Y skirt: Y + yaw + X-lock + anti-fall; slides in its slot for fine X) + 4 leg-sleeve pinch bolts, into 94459A150 inserts; **M4 × 0.7** (coarse) to match the inserts — NOT the M4 × 0.5 fine-thread 90751A120 |
| **M4 hold-down screw** | M4 × 18 mm, thread-forming for plastic | 1 | [McMaster](https://www.mcmaster.com/) | ~$8 / pack | the single +Z screw locking the merged keyhead nut-block endplate down — up from the floor bottom, thread-forming into its PA6-GF boss (the rest of the body is held by joinery) |
| **Fasteners** | M3 (NEMA17 mounts), M2 (belt clamps) | — | [McMaster](https://www.mcmaster.com/) | — | commodity |

## Electronics (compute bay)

The printed tray in the keyhead bay carries tool-free snap mounts for the full
PRO stack; a BASIC build populates only the first two rows and leaves the rest
of the sockets empty (the upgrade is drop-in). Panel I/O (1/4" TS line out, DC
power inlet, USB-C) mounts through the recessed wall in the bridge endplate's
lower corner — the instrument's right face.

Prices verified June 2026 from live listings (qty 1). Build tier in the **B/P**
column: **B** = both basic & pro, **P** = pro only.

| Part | B/P | PN / source | ~Price | URL |
|------|-----|-------------|--------|-----|
| **Teensy 4.1** | B | PJRC via SparkFun | $31.50 | [SparkFun](https://www.sparkfun.com/teensy-4-1.html) |
| **Teensy 4 Audio Shield Rev D** | B | SGTL5000, SparkFun | $9.80 | [SparkFun](https://www.sparkfun.com/teensy-4-audio-shield-rev-d.html) |
| **CAN transceiver** | B | SN65HVD230DR (DigiKey) | $2.45 | [DigiKey](https://www.digikey.com/en/products/detail/texas-instruments/SN65HVD230DR/404367) |
| **Buck 24→5 V 1 A** | B | Pololu D24V10F5 (powers Teensy) | $12.95 | [Pololu](https://www.pololu.com/product/2831) |
| **Signal relay** | B | Omron G5V-1-DC5 SPDT (true-bypass) | $2.74 | [DigiKey](https://www.digikey.com/en/products/detail/omron-electronics-inc-emc-div/G5V-1-DC5/87831) |
| **Buffer op-amp** | B | OPA2134PA DIP + passives | ~$11 | [DigiKey](https://www.digikey.com/en/products/detail/texas-instruments/OPA2134PA/254686) |
| **1/4" TS panel jack** | B | Neutrik NMJ4HCD2 (Ø11.4 hole) | $2.53 | [DigiKey](https://www.digikey.com/en/products/detail/neutrik-americas-inc/NMJ4HCD2/29371256) |
| **DC barrel panel jack** | B | Same Sky PJ-005A (Ø8 hole, 2.0 pin) | $3.07 | [DigiKey](https://www.digikey.com/en/products/detail/same-sky-formerly-cui-devices/PJ-005A/165838) |
| **USB-C panel coupler** | B | Adafruit 4261 F↔F (USB 2.0, Ø30 hole) | $7.50 | [DigiKey](https://www.digikey.com/en/products/detail/adafruit-industries-llc/4261/10287031) |
| **Rotary/4-way joystick** | B | Alps RKJXT1F42001 (sole UI control) | $9.22 | [DigiKey](https://www.digikey.com/en/products/detail/alps-alpine/RKJXT1F42001/19529127) |
| **OLED display** | B | 2.42" 128×64 SSD1309 SPI (UI screen) | ~$17 | [Waveshare](https://www.waveshare.com/2.42inch-oled-module.htm) |
| **USB 2.0 hub** | P | Adafruit CH334F (share 1 port: Teensy+Pi) | $4.50 | [Adafruit](https://www.adafruit.com/product/5999) |
| **Raspberry Pi 5, 8 GB** | P | 10ch A2M + Dexed + USB-audio gadget | $175 ⚠ | [PiShop](https://www.pishop.us/product/raspberry-pi-5-8gb/) |
| **Buck 24→5 V ≥6 A** | P | Pololu D36V50F5 (Pi wants 5.1 V/5 A) | $39.95 | [Pololu](https://www.pololu.com/product/4091) |
| **10-ch audio ADC** | P | TI **PCM1864DBT** ×3 (4-ch each, TDM) on a carrier PCB | $9.57 ea | [DigiKey](https://www.digikey.com/en/products/detail/texas-instruments/PCM1864DBT/5213896) |

⚠ **Pi 5** $175 is the current street price (MSRP ~$80; supply tight). The
**10-ch ADC** replaces the obsolete CS42448: three **PCM1864** (4-ch, built-in
line-level inputs, daisy-chain on one TDM bus → 12 ch, use 10) at ~$2.87/ch —
**these need a small custom carrier PCB** (no stocked 8+ch line-in HAT exists).
A USB-C panel part (Adafruit 4261) and both ADC routes are all orderable on
**DigiKey** to keep the supplier count down. The panel **USB-C** only needs
USB 2.0 (480 Mbps) — both the Teensy and the Pi 5 gadget port are USB 2.0.

The **analog front-end** (buffer + true-bypass relay + driver + local LDO) is a
small board at the bridge end. The relay defaults (de-energized) to passing the
**raw** pickup straight to the TS jack; the Teensy energizes it (UI toggle) to
switch in the **Q-processed** path. The ADC is always fed, and the Teensy
presents itself to a computer as a **USB audio interface** — so the processed
signal records digitally over USB with no analog round-trip. In **pro**, a USB 2.0
hub shares one panel port between the Teensy and the Pi (both as USB devices).

The **analog front-end** (buffer + true-bypass relay + driver + local LDO) is a
small board at the bridge end, on a boss off the bridge cross-rib. The relay
defaults (de-energized) to passing the **raw** pickup straight to the TS jack;
the Teensy energizes it (UI toggle) to switch in the **Q-processed** DAC output.
Buffering at the pickup keeps the long run to the keyhead ADC quiet; the ADC is
always fed (pitch detection runs in either mode).

The motor still does all tuning (the nut block clamps; no manual tuners). The nut
block is **reprintable per string set** — `STRING_GAUGE` in `dimensions.py` swaps
between E9 and C6; the break pins re-gauge so string tops stay coplanar.

Printed parts (no purchase): carriage, bridge_endplate, keyhead_endplate
(merged with the nut block), chassis (×3 segments), belt_clamp, screw_pulley, motor_pulley,
tension_fork (graded belt-tension lock set),
the adjustable legs: leg_socket ×4, leg_segment ×8, leg_sleeve ×4,
leg_shaft ×4 (PCTG/PA6-GF) plus leg_foot ×4 and leg_washer ×12 in **TPU**
(anti-unscrew preload washers + floor-friendly feet), electronics_tray, and
the **removable top deck**: a **pickup-carrier piece** (a tray whose floor runs
under the pickup; 3 M4 height screws set the string gap, 2 M4 clamp screws pin
X/Y — all from the packs above) + swappable fret-marked **filler bands** (one
per slot; print the set) + the UI/keyhead panels (fret lines + dust cover + hand
rest + UI mount) — see `py -3.12 -m src.build --list`.

## Filament (printed parts, both tiers)

Estimated at 2 perimeters (0.8 mm nozzle → 1.6 mm walls) + 15 % infill. Pickup
parts excluded. PCTG $25/kg, PA6-GF $60/kg; PETG≈$25, TPU≈$30 (assumed).

| Material | Mass | Cost | Main parts |
|----------|------|------|-----------|
| PCTG | ~2.9 kg | ~$73 | chassis ×3, bridge endplate, **top deck (pickup piece + bands + UI/keyhead panels, ~0.47 kg)**, legs, tray, pulleys |
| PA6-GF | ~0.13 kg | ~$7 | 10 carriages + keyhead endplate incl. nut block (load-critical) |
| PETG | ~32 g | ~$1 | 20 belt-splice clamps |
| TPU | ~40 g | ~$1 | 4 feet + 12 anti-unscrew washers |
| **Total** | ~3.0 kg | **~$78** | |

## Wire

Modeled internal harness ≈ 5.2 m of single-conductor runs; physically ~10 m once
power/CAN are pairs and audio is shielded. A 45 m hookup spool (~$20) covers
power/CAN/control; ~1.5 m shielded instrument cable (~$16) for the pickup/audio.
**~$35.** Excludes pedal/lever sensor wiring (pedals not yet designed).

## Cost summary (per instrument, June 2026)

Approximate; motors dominate. Re-verify before ordering.

| Group | Basic | Pro |
|-------|------:|----:|
| Filament (printed) | ~$78 | ~$78 |
| Mechanical hardware (motors, screws, bearings, belt, fasteners, dowels) | ~$530 | ~$530 |
| Wire | ~$35 | ~$35 |
| Electronics + UI | ~$110 | ~$335 + carrier PCB |
| **Total** | **~$755** | **~$980** + PCB |

Mechanical detail: 10× MKS SERVO42D (~$240) is the bulk; +10× Tr5×1 screw/nut
(~$60, **confirm 1 mm lead / single-start**), 10× MR85ZZ (~$30), 10× 693ZZ
(~$30), 10× shaft collars (~$25), Ø3 shaft (~$30), dowels (~$22), GT2 belt
6.5 m (~$12–130 depending on genuine-Gates vs generic), M-hardware packs (~$50).
Pro electronics adds the Pi 5 ($175 street), the ≥6 A buck, the USB hub, and the
10-ch ADC (**CS42448 EOL — substitution needed, ~$60**).
