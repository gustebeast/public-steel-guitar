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
| **Angle sensor IC** | 8 | ~$1.2–2 ea | [LCSC](https://www.lcsc.com/search?q=MT6701) | MagnTek **MT6701QT-STD**, 14-bit on-axis magnetic encoder. Take the **QFN-16 (3×3×0.75)**, *not* the SOP-8 variant: the air gap is measured to the IC's own top surface, so the package height comes straight out of the gap budget, and the SOP-8 is ~1.5 mm tall — twice the QFN — on the axis where we have the least room. Assembled by JLCPCB onto our sensor PCB alongside the tee boards — no hand soldering |
| **Diametric magnet** | 8 | $0.40 / $0.33 @10 | [DigiKey](https://www.digikey.com/en/products/detail/radial-magnets-inc/8995/5126077) | Radial Magnets **8995** — NdFeB **N35, Ø6 × 2.5 mm, DIAMETRICALLY magnetised**, NiCuNi, 80 °C, 3873 G surface; ~9k in stock. ⚠ **Diametric, NOT axial** — axial discs are far more common and simply do not work here (DigiKey lists the direction in the specs, so it is checkable at order time). Glues onto the printed axle stub |

*(qty 8 = 7 controls + 1 spare)*

**Sizing / sourcing note.** The IC reads field **direction**, not magnitude, so
the magnet only has to land the field inside the sensor's window (this class of
on-axis encoder wants roughly 30–70 mT — confirm against the MT6701 datasheet at
board design). Strength buys no accuracy, which in principle frees us to spend
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
| **XH headers**, THT top-entry | JST **B2B/B4B/B6B-XH-A(LF)(SN)** | ~30 | $0.17 / $0.144 @10 | [DigiKey](https://www.digikey.com/en/products/result?keywords=B4B-XH-A) | on every custom PCB (sensor boards, Teensy carrier, leg breakout); B4B verified, other sizes same class |
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
