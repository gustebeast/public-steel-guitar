# Bill of Materials — purchased parts

Sourcing for the bought parts (printed parts are built from `src/`). Links were
checked for a real, in-stock listing at the spec; prices are approximate and per
the date of writing — re-validate before ordering. Avoid Amazon per project
preference. See `electromechanical-pedal-steel-spec.md` §12 for the fuller
rationale. The **motors dominate cost** (10 × ~$35 ≈ ~$350); everything else
is commodity.

| Part | Spec | Qty | Source (verify stock) | ~Price | Notes |
|------|------|-----|--------|--------|-------|
| **Drive belt** | GT2 (2 mm pitch) open, **5 mm wide** | ~6.5 m | [Bulkman3D GT2 open belt](https://bulkman3d.com/product/gt000-gt0003/) | ~$0.5–1.7/m | cut-to-length, splice into loops with the printed clamp |
| **Drive motor** | MKS SERVO42D closed-loop stepper, NEMA17, **CAN MT** (board + motor) | 10 | [P3D](https://p3d.mx/products/makerbase-mks-servo42d-nema17-foc-motor) · [ElectroPeak](https://electropeak.com/mks-servo42d-nema17-closed-loop-stepper-motor) | $35 ea | get **MT** (board + motor = the working actuator). The cheaper **MB ($22) is the board ONLY** — only worth it if sourcing bare 48 mm NEMA17s under ~$13 ea. makerbase3d.com sells direct ≈ $34 |
| **Lead screw + nut** | Tr5×1 trapezoidal (5 mm, 1 mm lead, 1-start, self-locking) + brass nut | 10 | [eBay Tr5×1 + brass nut](https://www.ebay.com/itm/396869709608) · mfr [ALM](https://www.autolinearmotion.com/5mm-trapezoidal-lead-screw.html) | ~$3 ea | cut to ~61 mm; eBay listings rotate—AliExpress/ALM are stable fallbacks |
| **Screw support bearing** | MR85ZZ deep-groove, Ø5 × Ø8 × 2.5 | 10 | [Bearings Direct](https://bearingsdirect.com/mr85-zz-mini-ball-bearing-5x8x2-5-shielded-l850zz/) · [Trianglelab](https://trianglelab.net/products/mr85zz) | $0.5–4 ea | + a Ø5 thrust washer for the axial string pull |
| **Axial retainer** | Ø5 set-screw shaft collar (or a 2nd Tr5 nut) | 10 | [ServoCity 5 mm collar](https://www.servocity.com/2920-series-steel-set-screw-collar-5mm-bore-2-pack/) | ~$2.5 ea | locks the screw against the support bearing |
| **Bridge bearing** | 693ZZ deep-groove, Ø3 × Ø8 × 4 | 10 | [VXB 693ZZ ×10](https://vxb.com/products/693zz-3x8-shielded-3x8x4-miniature-bearing-pack-of) · [Bearings Direct](https://bearingsdirect.com/693-zz-mini-ball-bearing-3x8x4-shielded-r830zz/) | ~$1 ea | one per string; string rides the Ø8 OD |
| **Bridge axle** | Ø3 **g6/h6 precision shaft**, ~105 mm (e.g. hardened ground shafting) | 1 | [McMaster 3 mm shafts](https://www.mcmaster.com/products/linear-shafts/) | ~$3 | NOT an m6 dowel — m6 is press-fit in a 693ZZ bore; the shaft must slide through all 10 bearings + 9 comb fingers + both arms. Glue dab at the arms retains it |
| **Guide rod** | Ø2.5 × 28 mm hardened/ground dowel (DIN 6325, standard length) | 10 | [McMaster](https://www.mcmaster.com/products/hardened-dowel-pins/) · [eBay DIN6325 2.5 mm](https://www.ebay.com/itm/303389911894) | ~$0.5 ea | anti-rotation; drops in from the top through the stop bar's snug hole + the carriage's C-bore, landing in a blind socket — friction-held both ends (dab of glue optional) |
| **Nut break dowel** | Ø2 × 4 mm steel dowel (52100) | 10 | [McMaster 91595A018](https://www.mcmaster.com/91595A018/) | $12.70 / pack | gauged break pins (the scale "0"); drop into their slots from above. (Clamps bear on solid PETG-GF — no anvil.) |
| **M4 cup-tip set screw** | M4 × 0.7 cup-tip, 10 mm, alloy | 11 | [McMaster 91390A114](https://www.mcmaster.com/91390A114/) | $7.28 / pack 100 | clamps each plain string end onto its anvil (10) + 1 pickup -Y retention grub (threads its heat-set insert, cup tip pushes the pickup +Y against the plate's +Y wall — locks the pickup to the plate only, so the plate still travels) |
| **M4 pickup-jack screw** | M4 × 0.7, 20 mm, 18-8 SS button head (hex drive) | 3 | [McMaster 92095A-series](https://www.mcmaster.com/92095A192/) | ~$12 / pack | pickup height LEADSCREW jacks: the button head is captured in a deck counterbore (free to rotate, axially fixed), the shank threads the plate's heat-set nut so turning it from +Z walks the pickup up/down; 20 mm spans the height-adjust range across the 15–22 mm pickup depths + string gap. **Confirm the ×20 length suffix (…A196-class) at purchase.** NEW part — replaces the stale "3 cup-tip height screws" (those pre-date the leadscrew jack) |
| **M4 heat-set insert** | M4 × 0.7 brass heat-set, 4.7 mm | 18 | [McMaster 94459A150](https://www.mcmaster.com/94459A150/) | $10.82 / pack 50 | 10 nut clamps + 4 leg-sleeve pinch collars + 3 pickup-carrier jack nuts + 1 pickup -Y retention grub; deeply buried (no pull-out) |
| **M4 mount screw** | M4 × 0.7, 12 mm, 18-8 SS (button or socket head) | 4 | [McMaster 92095A192](https://www.mcmaster.com/92095A192/) | $14.77 / pack | 4 leg-sleeve pinch bolts, into 94459A150 inserts; **M4 × 0.7** (coarse) to match the inserts — NOT the M4 × 0.5 fine-thread 90751A120. (The old "pickup X/Y clamp screw" is retired — the pickup Y-lock is now the -Y cup-tip retention grub above) |
| **M4 hold-down screw** | M4 × 18 mm, thread-forming for plastic | 1 | [McMaster](https://www.mcmaster.com/) | ~$8 / pack | the single +Z screw locking the merged keyhead nut-block endplate down — up from the floor bottom, thread-forming into its PETG-GF boss (the rest of the body is held by joinery) |
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
the adjustable legs: leg_socket ×4, leg_segment ×8, leg_shaft ×4 (PETG-GF),
leg_sleeve ×4 (PCTG — the pinch collar must flex) plus leg_foot ×4 and leg_washer ×12 in **TPU**
(anti-unscrew preload washers + floor-friendly feet), electronics_tray, and
the **removable top deck**: a **pickup-carrier piece** (a tray whose floor runs
under the pickup; 3 M4 height screws set the string gap, 2 M4 clamp screws pin
X/Y — all from the packs above) + swappable fret-marked **filler bands** (one
per slot; print the set) + the UI/keyhead panels (fret lines + dust cover + hand
rest + UI mount) — see `py -3.12 -m src.build --list`.

## Control sensors (knee levers + pedals)

Every player input — 4 knee levers + 3 pedals — is a **contactless magnetic
angle sensor** rather than a switch or a pot: a diametrically-magnetised magnet
rides the control's axle and an MT6701 reads its angle across an air gap. There
is no wiper to wear out and no mechanical calibration. The boards are our own
(they panelise with the tee PCBs — see Connectors); these are the two parts that
populate them.

| Part | Qty | ~Price | Source | Notes |
|------|-----|--------|--------|-------|
| **Angle sensor IC** | 8 | ~$1.2–2 ea | [LCSC](https://www.lcsc.com/search?q=MT6701) | MagnTek **MT6701QT-STD**, 14-bit on-axis magnetic encoder. Take the **QFN-16**, *not* the SOP-8 variant: the air gap is measured to the IC's own top surface, so the package height comes straight out of the gap budget, and the SOP-8 is ~1.5 mm tall — twice the QFN — on the axis where we have the least room. Datasheet §9.2: D = E = 2.900–3.100, **A (total height) = 0.700–0.800** (the model carries the 0.800 max). §1.2: *"Sensing Center at Geometry Center"* — so the package body centres on the axle axis with no per-package offset. Assembled by JLCPCB onto our sensor PCB alongside the tee boards — no hand soldering |
| **Diametric magnet** | 8 | $0.40 / $0.33 @10 | [DigiKey](https://www.digikey.com/en/products/detail/radial-magnets-inc/8995/5126077) | Radial Magnets **8995** — NdFeB **N35, Ø6 × 2.5 mm, DIAMETRICALLY magnetised**, NiCuNi, 80 °C, 3873 G surface; ~9k in stock. ⚠ **Diametric, NOT axial** — axial discs are far more common and simply do not work here (DigiKey lists the direction in the specs, so it is checkable at order time). It is also the datasheet's own **recommended magnet** (§5: "Ø6mm x 2.5mm"), so this pair is the configuration the IC was characterised in. Drops into the axle's end pocket; `kl_magnet_cap` screws over it — no adhesive |

*(qty 8 = 7 controls + 1 spare)*

**Board spec (ours, for layout).** Outline **17 × 19 × 1.6 mm**, strongly
*asymmetric* about the sensor: the chip sits on the axle axis just **3.0 mm from
the +X edge**, 14.0 mm from the −X edge and 7.0 mm below the top edge. The 3.0 is
deliberately tight — the QFN body ends at 1.5, leaving 1.5 of edge keepout, over
JLCPCB's 1.0 mm component-to-edge rule — because every millimetre there is
millimetres off the lever's +X extent, which is the face nearest the player. **No mounting
holes** — the board drops into two grooves in the housing's printed cradle, rests
on its floor, and the instrument's own underside closes over it as the lid. So
**1.85 mm of each side edge is mechanical** — keep copper and parts out of it.

**SINGLE-SIDED: everything goes on the −Y (magnet-facing) face**, which is what
keeps this to one assembly setup. The QFN sits on the axle axis. The CAN drop is
an **S4B-XH-SM4-TB**, mouth facing −X, its body occupying x −11.9 to −5.8 and
z −8.0 to +7.0. Both of those placements are forced, not chosen: the board is
installed by lowering it past the rotating magnet cap, so anything on this face
deeper than 1.5 mm must keep its whole footprint outside the cap's 5.4 mm radius.
The housing is relieved 0.85 mm behind the connector and tunnelled through the
−X web so the plug has a run-in; it needs 7.5 mm of straight travel to come off,
and there is 10.75 mm.

Routed-outline-to-copper tolerance matters here: the datasheet's max
sensing-centre-to-magnet-axis misalignment is **0.3 mm**, and JLCPCB's ±0.2 mm
outline tolerance plus the cradle's 0.15 mm slip fit spends most of it. Overrunning
it slightly costs INL only (±1.0° typ → ±1.5° max), which the per-control
calibration map removes; repeatability is untouched.

**Sizing / sourcing note.** The IC reads field **direction**, not magnitude, so
the magnet only has to land the field inside the sensor's window (datasheet §5:
**200–1,000 Gauss measured at the IC surface**, air gap **0.5 / 1.0 / 2.0 mm**
min/typ/max). Strength buys no accuracy, which in principle frees us to spend
the magnet's geometry on the axis that is actually scarce: **+Y room is tight**
(the sensor cluster sits inboard, under the body) while lateral room is free. A
diametric disc's poles sit on its curved flanks, so pole separation — and with it
how slowly the field decays across the gap — scales with **diameter**, meaning a
Ø8 × 2.0 would save 0.5 mm of Y *and* read stronger than a Ø6 × 2.5.

We are **not** doing that, on sourcing grounds: no supplier we already buy from
stocks Ø8 × 2.0. DigiKey's Ø8 diametric is 2.5 thick (saves nothing) and the
Ø8 × 2.0 is a 100-pack from a magnet specialist — a new vendor and a 12× overbuy
to save 0.5 mm, at a moment when re-anchoring the sensor cluster to the real
housing face has already reclaimed 2.6 mm of +Y. Ø6 × 2.5 is also the **reference
geometry** for this sensor class (ams' own AS5000-MD6H is D6 × 2.5), so the
published app notes apply directly rather than us estimating the field. Final
trim is the **air gap** (a printed dimension, currently 1.5 mm): measure on the
first board and adjust the gap in the model rather than re-buying magnets.

⚠ **Temperature:** the 8995 is plain N35, rated **80 °C**. That is fine in normal
use but marginal for an instrument left in a hot car; if that becomes a real duty
cycle, step up to an **N35H/SH** in the same Ø6 × 2.5 geometry (~120–150 °C).
Partial demagnetisation would weaken the field but not corrupt the angle — the
sensor reads direction — so the failure mode is graceful, not silent.

## Filament (printed parts, both tiers)

Estimated at 2 perimeters (0.8 mm nozzle → 1.6 mm walls) + 15 % infill. Pickup
parts excluded. PCTG $25/kg, PETG-GF $30/kg, TPU≈$30 (assumed). The build
exports each part into its **material folder** (`petg-gf/`, `pctg/`, `tpu/`):
PETG-GF = every stiffness/creep-critical part (sustained string-tension +
ground-reaction paths); PCTG = compliant / snap-fit / fine-feature parts, and
the WHOLE deck — panels are PAIRS (transparent-PCTG base with embossed fret
lines + colour-PCTG layer) printed as one two-filament object. The deck is the
forearm rest: no glass fiber on skin-contact surfaces (abrasion exposes fiber
ends), and same-resin pairs weld/purge cleanest.

| Material | Mass | Cost | Main parts |
|----------|------|------|-----------|
| PETG-GF | ~2.3 kg | ~$69 | chassis ×3, bridge + keyhead endplates, 10 carriages, leg tubes/shafts/sockets, knee housing, pickup Z-plate |
| PCTG | ~0.65 kg | ~$16 | full deck (transparent bases + colour layers), tray, pulleys, belt clamps, knee arm, small compliant parts |
| TPU | ~40 g | ~$1 | 4 feet + 12 anti-unscrew washers |
| **Total** | ~3.0 kg | **~$88** | |

Chosen spools:

- **PCTG — [3D-Fuel Pro PCTG](https://www.3dfuel.com/collections/1-75mm-pro-pctg)**:
  [Natural/Clear](https://www.3dfuel.com/products/pro-pctg-natural-1-75mm) for the
  transparent deck bases (the fret-line light path wants the clear grade), plus a
  colour of choice for the deck colour layers + the rest of the PCTG parts.
  Publishes a TDS; AMS-compatible spool — the deck's clear+colour pair can run
  from one AMS.
- **PETG-GF — [Tinmorry PETG-GF](https://tinmorry.net/en-us/collections/petg-gf)** (~$30/kg).
  No published TDS, so **verify the first spool** with a bend coupon before
  committing the chassis: 10×10×140 mm bar, 120 mm span, 1 kg at centre —
  ~0.5 mm deflection ⇒ ~2.8 GPa (buy); ~0.9 mm ⇒ plain-PETG stiffness (return).
  Elegoo PETG-GF (flex modulus 3345 MPa, published) is the documented fallback.
  Vendor recommends a hardened ≥0.4 mm (ideally 0.6 mm) nozzle.
- **TPU — [Tinmorry TPU 95A](https://tinmorry.net/en-us/products/filament-tpu-1-75-mm-tinmorry-3d-printing-materials-tpu-filament-for-fdm-3d-printer-1-kg-1-spool-black)**
  (Shore 95A±2 — right grade for floor grip + preload washers; 68D "AMS-safe"
  TPU is 5–10× stiffer and grips poorly). Dry 70 °C / 8 h before printing;
  **not AMS-compatible** — run the feet + washers from the external spool.

## Wire

Modeled internal harness ≈ 5.2 m of single-conductor runs; physically ~10 m once
power/CAN are pairs and audio is shielded. Gauges (the SERVO42D driver rides the
motor, so there are **no stepper phase leads** — noise defence is shielding +
twisting + the bridge-side AFE buffer, not conductor size):

| Net | Cable | OD |
|---|---|---|
| 24 V bus | 20 AWG silicone pair, twisted/flat (fleet slew staggered <5 A; ~0.3 V drop over the run) | ~2.4 |
| CAN | 26 AWG twisted pair, 120 Ω terminated | ~2.2 |
| pickup / audio / DAC / out | 28 AWG **shielded** pair (mA signals — the shield is the spec) | ~2.0 |
| USB panel → Pi | slim shielded USB-2 | ~2.6 |
| logic (relay, link, TDM, OLED, joystick) | 28 AWG | ~1.4 |

A 45 m hookup spool (~$20) covers power/CAN/control; ~1.5 m shielded pair
(~$16) for the pickup/audio runs. **~$35.** Excludes pedal/lever sensor wiring
(pedals not yet designed). All cross-rib raceways pass ≤ Ø2.6 and sit above the
knee-lever mortise plane — route no fatter cable through the floor trunk.

## Connectors (wiring strategy, July 2026)

Rule: **solder only happens on factory-assembled PCBs; every field connection
is a connector** (no bare wire ever meets a bare module pin; never
inline-splice — user priorities: damage-free un/re-mating beats install
speed, and **no personal soldering work**: the only bench work is XH
crimping). Two classic-CAN buses at 500 kbps: **bus A motors** (Teensy CAN1 →
10× SERVO42D over their native XH pigtails — power AND CAN; ~1–1.5 A input
at 24 V sits inside XH's 3 A rating, so no separate motor power connector —
120 Ω fixed at both ends) and **bus B inputs**, a **TRUNK-AND-DROP** bus:
crimped 4-wire XH jumpers run point-to-point between **TEE PCBs** (one per
pedal/lever station: 3× B4B-XH-A — trunk in, trunk out, drop — plus a 120 Ω
terminator behind a 2-pin shunt jumper, closed only on the last tee), and
each device hangs off its tee by ONE short XH drop — so unplugging any
device NEVER breaks the bus, and every trunk segment is individually
replaceable. The trunk crosses the instrument's only TWO TRRS joints, both
SELF-MATING: the leg↔bar auto-mate (latch-driven) and the leg↔body joint
(the column-top plug blind-mates the chassis jack during the final thread
turn — deterministic clocking sets the depth, and the plug's annular
contacts rotate freely, so threading twists no wires). The SERVO42D is classic-CAN-only, which is why any bus with
motors runs classic; sensor boards still get FD-capable transceivers to keep
the FD option on bus B. XT30 only at the PSU trunk joints.

**PCB buying plan**: tee PCBs + sensor PCBs ship as ONE panel (V-score /
mouse-bite, snap apart — never hand-cut FR4), ONE assembly job, **full paid
assembly including the THT headers** (accept the standard-tier fee if
economic PCBA rejects THT; incremental tee assembly ≈ $7–12). Zero personal
soldering also applies to the former "bench-once pigtail" points: every
TRRS is either factory-molded-on-cable (Tensility, cut + crimp) or
factory-assembled on the leg carrier PCB, and XT30 arrives as **pre-wired
pigtails** (or XT30PW board-mount on the power distribution PCB) — pick
whichever quotes cleaner at order time. NO consignment anywhere: all PCB
parts are LCSC-library.

Prices **verified on DigiKey 2026-07-09** (stock healthy unless noted);
re-check at order time. XH harness = crimp-your-own (contacts ~$0.03 vs
$0.59–0.78 per pre-crimped lead — 20×; needs a ~$25–45 tool, below).

| Role | Part | Qty | Price (verified) | URL | Notes |
|------|------|-----|------------------|-----|-------|
| **TRRS plug + cable** (bar cradle) | Tensility **CA-354S** (053-0113R): molded plug Ø10, barrel Ø3.5×14, 1.83 m Ø3.7 shielded 26 AWG cable, tinned ends | 2 | $3.53 / $3.00 @10 | [DigiKey](https://www.digikey.com/en/products/detail/tensility-international-corp/CA-354S/382910) | zero-solder: cut cable to length, crimp XH on the cut end. #1 = bar cradle → first bar tee; +1 spare. (The old #2 "leg-column riser" is DELETED — the column is an off-the-shelf extension cable now, next row.) [Drawing](https://tensility.s3.us-west-2.amazonaws.com/uploads/pdffiles/053-0113R.pdf) |
| **TRRS M→F EXTENSION cable** (the WHOLE wired leg column) | Off-the-shelf 3.5 mm 4-pole (TRRS) headset extension, ~1.2 m, shielded; **pick at purchase & verify**: molded plug handle ≤ Ø10 (head seat), inline jack barrel ≈ Ø9.1–9.7 × ≤40 (shaft seat, 10-03404-class envelope) | 1 | ~$5–8 | (commodity; e.g. DigiKey/Amazon 4-pole extension) | ZERO connections on the leg (user): the molded PLUG sits captive in the latch head (blind-mates the chassis jack), the molded FEMALE barrel seats mouth-down in the shaft block (receives the bar tower's plug), the middle gets the heat-set slack COIL (Ø8 mandrel, 85 °C). No solder, no crimps, no junction anywhere in the column. |
| **TRRS jack + cable** (chassis, above the -X/+Y socket) | Tensility **10-03404**: molded jack Ø9.1×39.4, 0.91 m Ø3.8 shielded 28 AWG cable | 1 | $5.15 / $4.4 @10 | [DigiKey](https://www.digikey.com/en/products/detail/tensility-international-corp/10-03404/11196637) | embedded VERTICALLY above the socket — the column-top plug BLIND-MATES on the latch press (plug spins freely in the jack → no wire twist); cable → tee 12 (crimp XH at the cut end — off-leg). [Drawing](https://tensility.s3.us-west-2.amazonaws.com/uploads/pdffiles/10-03404.pdf) |
| **TRRS jack, SMT** (leg-shaft auto-mate, on the leg carrier PCB) | LCSC-library compact SMT jack, **pick at PCB design** (SJ-4351X-class, ~13×6×5) | 2 | ~$0.30 | LCSC | the only form factor that fits the Ø20 shaft; factory-assembled on the carrier (no consignment). Pocket gets rebuilt around the chosen part's drawing. Fallback: Same Sky SJ-43514-SMT-TR via JLCPCB global sourcing |
| **XH crimp contacts** | JST **SXH-001T-P0.6** | 300 | ~$0.024–0.047 | [DigiKey](https://www.digikey.com/en/products/result?keywords=SXH-001T-P0.6) | 22–30 AWG; qty includes learning-curve scrap |
| **XH housings** | JST **XHP-2 / XHP-4 / XHP-6** | ~30 | ~$0.10 | [DigiKey](https://www.digikey.com/en/products/result?keywords=XHP-4) | contacts click in by hand, extractable; XHP-6 mates the SERVO42D pigtail |
| **XH header**, SMT side-entry | JST **S4B-XH-SM4-TB** | 8 | $0.65 / $0.28 @800 | [LCSC C161861](https://lcsc.com/product-detail/Wire-To-Board-Connector_JST-S4B-XH-SM4-TB-LF-SN_C161861.html) | **Sensor boards only**, and it earns the second part number: it is the piece that lets the board be SINGLE-SIDED. SMT (no post tails through a face that has to seat), side entry (a top-entry plug would have to be inserted from inside the housing). B = 15.0, 7.0 tall, 6.1 body depth, 4.5 mouth. Mates the same XHP-4 plugs and crimps as everything else, so the harness is unaffected. ~40k in LCSC stock; in JLC's library as C161861 — check it is orderable for assembly at quote time |
| **XH headers**, THT top-entry | JST **B2B/B4B/B6B-XH-A(LF)(SN)** | ~30 | $0.17 / $0.144 @10 | [DigiKey](https://www.digikey.com/en/products/result?keywords=B4B-XH-A) | on every custom PCB (sensor boards, Teensy carrier, leg breakout); B4B verified, other sizes same class. Modelled from JST's own drawing (`cadkit.pcb.jst_xh_header`): B4B is **12.4 × 5.75**, **7.0 mm** tall bare and **9.8 mm mated** — the mated figure is the one clearances must use — with □0.64 posts reaching 3.4 mm below the seating plane, i.e. **1.8 mm proud** of a 1.6 mm board's far face. The pin row is **2.0 mm from one long edge, 3.75 from the other**, so the part is not symmetric about its pins and which way it faces is a real layout decision |
| **Power connector** (PSU trunk only) | XT30 pair — DFRobot **FIT0586** | 4 pr | $1.90 | [DigiKey](https://www.digikey.com/en/products/detail/dfrobot/FIT0586/9559255) | 15 A/30 A pk, gold; pigtails bench-soldered ONCE, field = plug/unplug only |
| **CAN terminator R** | Yageo **CFR-25JB-52-120R** (120 Ω ¼ W) | 10 | $0.10 / $0.036 @10 | [DigiKey](https://www.digikey.com/en/products/result?keywords=CFR-25JB-52-120R) | Teensy carrier + last motor; bus-B termination lives ON the tees (SMT 120R there) |
| **Tee PCB** | custom: 3× B4B-XH-A + 120 Ω + shunt jumper | 12 | ~$2 assembled (est.) | JLCPCB | panelized with the sensor boards; close the jumper on the LAST tee = bus-B termination |
| **Leg carrier PCB** | custom: LCSC SMT jack + B4B-XH-A header | 2 | ~$2 assembled (est.) | JLCPCB | rides the same panel; sits in the shaft pocket — auto-mate jack's terminals land on XH, fully factory-soldered |
| **FD-capable transceiver** (new PCBs) | Microchip **MCP2562FD-E/SN** | ~10 | $1.29 / $1.07 @25 | [DigiKey](https://www.digikey.com/en/products/result?keywords=MCP2562FD-E%2FSN) | rides the sensor-PCB assembly order (LCSC ~$0.50 there); VIO pin suits 3.3 V logic |

≈ **$40 of connectors + ~$25 of tee/carrier boards** (board figures are
estimates until the JLCPCB quote; tools live in the Tools section — per
project policy they're shop infrastructure, not a line item weighed against
any one approach). Fallback if crimping
frustrates: JST pre-crimped leads [ASXHSXH22K203](https://www.digikey.com/en/products/detail/jst-sales-america-inc/ASXHSXH22K203/9961918)
($0.78 / $0.588 @50, 200 mm socket-socket — cut in half = 2 pigtails).
Molded TRRS cables were dropped: DigiKey's are special-order/obsolete
(SparkFun 14163/14164) and the lean topology needs none — if an external
TRRS hop ever appears, any consumer 4-pole aux cable serves. Audio stays as
already pinned above (Neutrik NMJ4HCD2 + shielded pair, single-point ground).
The SERVO42D's own I/O is **XH2.54 native**, so the XH standard needs no
adapting at the motors.

## Optical pickup PCB (per-string sensing + on-board audio→MIDI)

One custom board, hanging **face-down from the bridge endplate's tie bar**, that
reads all ten strings optically. It replaces nothing in the signal path — the
magnetic pickup is untouched — and does two jobs: per-string **pitch** (tuning
calibration + audio→MIDI) and per-string **audio**.

**The canonical part list is `src/optical_pickup.py::PARTS`.** The table below is
generated from it, so the 3D model, the clearance assertions and this BOM cannot
disagree about what is on the board. Every package is a real JEDEC/IPC outline at
max dimensions; placement in the model is representative (block order and X
columns are deliberate, exact XY of an 0402 is layout's business).

**Architecture.** Each string gets an IR emitter flanked by two photodiodes in Y.
SUM tracks vertical motion (the audio signal); DIFF tracks lateral. Both are
needed: with symmetric detectors SUM is an *even* function of lateral
displacement, so as the vibration plane precesses toward horizontal — which it
does over this instrument's long sustain — SUM's f₀ collapses and **2f₀ takes
over**, handing the detector a confident octave-up error rather than a dropout.
Each photodiode therefore gets its own transimpedance amp and its own ADC input
(20 of each); SUM/DIFF are one add and one subtract in firmware, cheaper in parts
than analog sum *and* difference stages.

Two rates share one ADC stream: **audio** = SUM at 48 kHz × 10 ch = 960 kB/s
straight out over USB; **pitch** = decimated to ~6–8 kHz, detected on-chip, MIDI
out over the same cable. The expensive stage is the only one not running at 48 k,
which is why both fit in ~15 % of the MCU.

**Why an external USB PHY.** 960 kB/s needs USB high-speed (isochronous
full-speed tops out near 1023 kB/s theoretical, with MIDI still to send). Survey
at time of writing:

| Candidate | HS PHY | Fits a 20 mm board | Verdict |
|---|---|---|---|
| STM32H7 (LQFP100) | external ULPI | yes | **chosen** — M7, 3× 16-bit ADC |
| STM32F723/733 | internal | no — ≥144 pins, 22×22 over leads | too wide |
| AT32F435/437 | none (full-speed only) | yes | no HS |
| GD32F470 | external ULPI | yes | M4 240 MHz, 12-bit ADC |
| CH32V307 | internal | yes | 144 MHz, 16 ADC ch — can't run the detector |

The only part with an integrated HS PHY that fits cannot run the detector, so the
extra PHY chip is unavoidable. LQFP100 is likewise a floor, not a preference: 20
ADC inputs plus a 12-signal ULPI bus will not fit a 64-pin part.

| Qty | Ref | Part / role | Package | Envelope (mm) |
|-----|-----|-------------|---------|---------------|
| 1 | U6 | MCU — Cortex-M7, 3× 16-bit ADC, USB OTG_HS via ULPI | LQFP100 | 16.00 × 16.00 × 1.60 |
| 1 | J1 | USB-C receptacle — 10 ch audio + MIDI + DFU | USB-C | 8.94 × 7.35 × 3.16 |
| 1 | J2 | power in, 5 V from the instrument rail — side entry, −X edge | XH-SM-2 | 6.10 × 10.00 × 7.00 |
| 5 | U1–U5 | quad op-amp — 4× transimpedance amp | SOIC-14 | 6.00 × 8.65 × 1.75 |
| 1 | U7 | USB 2.0 high-speed ULPI PHY | QFN-24 | 4.00 × 4.00 × 0.90 |
| 1 | U8 | LDO — 3V3 digital | SOT-23-5 | 2.90 × 2.80 × 1.45 |
| 1 | U9 | LDO — 3V3 analog (low noise) | SOT-23-5 | 2.90 × 2.80 × 1.45 |
| 1 | U11 | single op-amp — TIA mid-rail reference buffer | SOT-23-5 | 2.90 × 2.80 × 1.45 |
| 1 | Y1 | 25 MHz crystal — MCU HSE | 3225 | 3.20 × 2.50 × 0.90 |
| 1 | Y2 | 24 MHz crystal — PHY reference | 3225 | 3.20 × 2.50 × 0.90 |
| 1 | Q1 | N-ch MOSFET — LED row driver | SOT-23 | 2.90 × 2.40 × 1.30 |
| 1 | U10 | USB data-line ESD array | SOT-563 | 1.60 × 1.60 × 0.60 |
| 10 | D1–D10 | IR emitter, 940 nm — **narrow beam, see below** | 0805 (opto) | 2.00 × 1.25 × 0.85 |
| 10 | PD1A–PD10A | PIN photodiode, +Y of string | 0805 (opto) | 2.00 × 1.25 × 0.85 |
| 10 | PD1B–PD10B | PIN photodiode, −Y of string | 0805 (opto) | 2.00 × 1.25 × 0.85 |
| 5 | R1–R5 | LED current-set — **per-string value**, plain strings | 0603 | 1.60 × 0.80 × 0.95 |
| 5 | R6–R10 | LED current-set — **per-string value**, wound strings | 0603 | 1.60 × 0.80 × 0.95 |
| 1 | FB1 | ferrite bead — analog rail isolation | 0603 | 1.60 × 0.80 × 0.95 |
| 4 | C130–C133 | bulk caps — VBUS / 3V3D / 3V3A / reference | 0805 | 2.00 × 1.25 × 1.45 |
| 20 | Rf11–Rf54 | TIA feedback resistor — **per-string value** | 0402 | 1.00 × 0.50 × 0.55 |
| 4 | C140–C143 | power-input decoupling | 0402 | 1.00 × 0.50 × 0.55 |
| 20 | Cf11–Cf54 | TIA feedback cap (sets the anti-alias pole) | 0402 | 1.00 × 0.50 × 0.55 |
| 12 | C100–C111 | MCU decoupling | 0402 | 1.00 × 0.50 × 0.55 |
| 10 | Cd11–Cd52 | op-amp decoupling | 0402 | 1.00 × 0.50 × 0.55 |
| 4 | C123–C126 | crystal load caps | 0402 | 1.00 × 0.50 × 0.55 |
| 3 | C120–C122 | PHY decoupling | 0402 | 1.00 × 0.50 × 0.55 |
| 2 | R34–R35 | mid-rail divider | 0402 | 1.00 × 0.50 × 0.55 |
| 2 | R32–R33 | USB-C CC pull-downs, 5k1 | 0402 | 1.00 × 0.50 × 0.55 |
| 1 | R30 | BOOT0 pull-down | 0402 | 1.00 × 0.50 × 0.55 |
| 1 | R31 | NRST pull-up | 0402 | 1.00 × 0.50 × 0.55 |
| 1 | R36 | LED driver gate resistor | 0402 | 1.00 × 0.50 × 0.55 |
| — | — | SWD programming pads (no component; first flash before USB DFU works) | pads | — |

**141 placed parts**, all on ONE side (single-sided, per project rule: one
stencil, one reflow, no back-side placement). The model tracks 35 distinct
(description, package) lines; the table above merges four bulk-cap variants and
the two CC pull-downs into single rows.

**Board**: STEPPED outline, 4-layer, 1.6 mm FR4, 3408 mm² — **30 × 49 mm** over
the plain strings (+Y) and **20 × 96.9 mm** over the wound strings and the
digital block (−Y). Two blocks, split electrically rather than for packing — the
20 TIAs sit in the X band immediately beside the sensor row (the summing node is
the noise-critical point on a board reading tens of nanoamps), everything digital
lives in the −Y room past the last string. Single-sided is what makes it long;
double-siding would save roughly 35 mm if that ever becomes worth the second
assembly setup.

### The thin-string signal budget — why the outline steps

Optical signal scales with the string's **diameter**: the string *is* the target,
and what comes back is set by how much of the beam it intercepts. Across this set
that is .014 against .070 = 5.1× = **14.0 dB**, and the thin strings sit up to
0.71 mm further from the sensor plane (which references the *thickest* string's
top), so call it **~16 dB**. That deficit lands on exactly the strings the player
uses most. Note the hard string for *latency* (low C, long analysis window) and
the hard string for *SNR* (string 2, .014) are opposite ends of the set.

Four levers, spent in order of cost:

1. **Emitter beam angle — the largest and it is free.** At the 3 mm standoff a
   ±60° emitter throws a ~10.4 mm spot and a 0.356 mm string intercepts ~3 % of
   it; the rest returns as pedestal and crosstalk. ±30° → 3.5 mm spot, ~10 %,
   **+9.5 dB**. ±20° → **+13.6 dB**. Do not go tighter: below ~±20° the alignment
   budget (fab ±0.2, string position, board seating) starts eating the gain.
   **Beam angle is the primary selection criterion for D1–D10**, ahead of package
   or price. The VSMB1940X01 whose outline the model uses is a placeholder chosen
   for its dimensions, not its optics.
2. **Per-string LED current** (R1–R10, already ten independent parts). Roughly
   linear in signal. This is what forces J2 — see below.
3. **Per-string TIA gain** (Rf, already twenty independent parts). Bounded by the
   op-amp's gain–bandwidth product, not by the resistor: thin strings want more
   gain *and* more bandwidth, and Rf × Cin trades one against the other.
4. **Distance from the termination** — the worst lever, and the only one with a
   playing cost. Signal is linear in distance, so gain is 20·log10(d/12) dB while
   the cost in playing space is linear. Equalising .014 would need d = 60 mm,
   putting the board edge at −66.5. Spent anyway, as a **step**: plain strings
   (1–5) go to 22 mm for **+5.3 dB**, wound strings stay at 12 mm. A step rather
   than a taper because a taper would interpolate and hand string 5 almost
   nothing.

**What the step costs in playing.** The tie bar's underside is only 3.00 mm above
the strings, so nothing can be picked *under* it — the bar's −X face is the
picking-zone boundary. Stepping keeps that boundary at **14.5 mm** from the
termination over the wound strings and moves it to **24.5 mm** only over the
plain ones. A uniform 22 mm row would have pushed all ten out to 24.5.

**Power (J2): 5 V from the instrument rail, not USB VBUS.** MCU ~200–300 mA, PHY
~50, 21 op-amp channels ~40 — already past a USB port's 500 mA before a single
emitter is lit. Since LED current is the second-best SNR lever, capping it at
what a host port will give up would throw away the thing the design most needs.
J2 is side-entry on the **−X edge**: the −Y edge is taken by the USB receptacle
and the floor-ledge lane, and −X of the board is open air (the optical relief
removes the tie bar's wall there), so that mouth is reachable. It plugs in after
the board slides home.

**All ten emitters are driven by ONE FET.** Ambient subtraction sweeps the whole
row on, then the whole row off, which gives the front end ~10 µs to settle
instead of ~1 µs. Per-string *current* is still set individually by R1–R10; what
is common is only the on/off gate. The cost is optical crosstalk between
neighbouring strings — one of the things the prototype needs to measure.

**Open sourcing items** (project rule: NO consignment, all PCB parts
LCSC-library — none of the below is confirmed orderable for assembly yet):
- the exact **STM32H7 LQFP100** variant, and whether it exposes **20 ADC input
  pins** on that package. If it comes up short, the fallback is muxing the ten
  DIFF channels (they only run at the decimated rate) into one input.
- a **ULPI PHY** in JLC's library — USB3343-class QFN-24 is the envelope modelled.
- the **PIN photodiode**. JLC's readily-available optoelectronics skew toward
  *phototransistors*, which would undermine the linearity the audio path needs.
  This is the part most likely to force a redesign.
- the **IR emitter's beam angle** — ±20–30° at 940 nm in an 0805-class package.
  Worth more dB than anything else on this list; if the library has nothing
  narrow, that changes the signal budget more than any other substitution.
- **quad op-amp** with low enough input bias current for a nanoamp TIA.
- **J2**: JST S2B-XH-SM4-TB class, SMT side-entry 2-way. The envelope in the
  model is scaled from the S4B figures already in this BOM — confirm against
  JST's drawing before layout, as the S4B was.

**Prototype: the first measurement is now string 2, not `SENSE_D`.** Specifically
a **.014 plain string at 22 mm with a narrow-beam emitter at a realistic drive
current**. Testing with a wide-angle emitter would understate the design by ~10 dB
and could argue for playing-space intrusion that isn't needed.

**Cost (estimate, not yet quoted)**: ~$30/board in parts — the MCU (~$9), 20
photodiodes (~$7), 5 quad op-amps (~$4) and the PHY (~$2.50) dominate; ~95
passives total about $1. Assembly follows the same per-*order* economics as the
tee/sensor panel ($25 setup + ~$1.50 per unique feeder), so it should ride the
**same JLCPCB panel** — the 0402 R/C and generic parts overlap with the existing
boards, and only the specialised lines add feeders.

## Tools (shop infrastructure — NOT per-instrument cost)

One-time purchases that outlive this project; documented here so nothing is
a surprise at build time, but **excluded from the cost summary and from
pros/cons when weighing approaches** (project policy).

| Tool | For | ~Price | Notes |
|------|-----|--------|-------|
| **JST crimp tool** | XH harness (contacts SXH-001T-P0.6) | $25–45 | IWISS SN-01BM or Engineer PA-09 (mfr/eBay — not DigiKey); covers XH/PH/most small JST; budget a dozen practice crimps |
| **Soldering iron** | bench-once pigtails (SP-3541, XT30), PCB touch-up | — | presumed owned |
| **Heat-set insert tips** | M4 (94459A150) + M2 insert pockets | ~$15 | fits the soldering iron |
| **Hardened nozzle ≥0.4 (ideally 0.6)** | PETG-GF (vendor recommendation) | ~$15–30 | glass fiber eats brass nozzles |
| **Wire strippers 20–30 AWG** | all harness work | — | presumed owned |

## Cost summary (per instrument, June 2026)

Approximate; motors dominate. Re-verify before ordering.

| Group | Basic | Pro |
|-------|------:|----:|
| Filament (printed) | ~$78 | ~$78 |
| Mechanical hardware (motors, screws, bearings, belt, fasteners, dowels) | ~$640 | ~$640 |
| Wire | ~$35 | ~$35 |
| Electronics + UI | ~$110 | ~$335 + carrier PCB |
| **Total** | **~$865** | **~$1,090** + PCB |

Mechanical detail: 10× MKS SERVO42D CAN MT (~$350) is the bulk; +10× Tr5×1 screw/nut
(~$60, **confirm 1 mm lead / single-start**), 10× MR85ZZ (~$30), 10× 693ZZ
(~$30), 10× shaft collars (~$25), Ø3 shaft (~$30), dowels (~$22), GT2 belt
6.5 m (~$12–130 depending on genuine-Gates vs generic), M-hardware packs (~$50).
Pro electronics adds the Pi 5 ($175 street), the ≥6 A buck, the USB hub, and the
10-ch ADC (**3× PCM1864 on a small carrier PCB, ~$30 + PCB** — already substituted
for the obsolete CS42448; see the electronics table).
