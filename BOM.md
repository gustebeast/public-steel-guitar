# Bill of Materials — purchased parts

Sourcing for the bought parts (printed parts are built from `src/`). Links were
checked for a real, in-stock listing at the spec; prices are approximate and per
the date of writing — re-validate before ordering. Avoid Amazon per project
preference. See `electromechanical-pedal-steel-spec.md` §12 for the fuller
rationale. The **motors dominate cost** (10 × ~$35 ≈ ~$350); everything else
is commodity.

## Price verification — full sweep, 2026-08-01

Every line item in this file was pushed at a live listing on **2026-08-01**.
Rows carrying **[v]** were confirmed against a fetched product page; rows
carrying **[m]** could not be fetched and need a **manual check by a human** —
see "Cannot verify — needs a manual check" at the bottom of this file for the
list and the reason for each. Anything with neither marker is an internal
estimate (printed-part filament mass, PCB fab terms) with no listing to check.

**Six rows moved.** Four were priced too low, one vendor is out of stock, and
one part is not stocked at all in the library we committed to:

| Row | Was | Now | Impact |
|---|---|---|---|
| Optical photodiode (VEMD4110X02) | ~$0.35 ea | **not on LCSC**; use **X01**, same filter, **$0.58 @100+** | +$4.6/board; ⚠ 72 in stock vs 200 needed |
| Optical MCU STM32H743ZIT6 | $7.63 | **$11.07 / $9.93 @10**, 7 in stock | +$2.30/board, and a stock block |
| TRRS jack Tensility 10-03404 | $5.15 | **$8.19 / $6.96 @10** | +$3 |
| Bridge bearing 693ZZ | ~$1 ea | **$3.00 ea** (VXB 10-pack) | row was wrong; summary was right |
| PCTG filament | $25/kg | **$29.95/kg** | +$3 |
| Pi buck ≥3 A | ~$25 | **$29.95** (D24V50F5) | +$5 |

Two of those are **availability**, not price, and they matter more than the
dollars: the photodiode and the 144-pin MCU are the two parts the optical board
is designed around, and **neither can currently supply a run of ten** (72 and 7
units in stock, against 200 and 10 needed). Both now have correct part numbers —
the constraint is stock, not selection. See the optical-pickup section.

| Part | Spec | Qty | Source (verify stock) | ~Price | Notes |
|------|------|-----|--------|--------|-------|
| **Drive belt** | GT2 (2 mm pitch) open, **5 mm wide** | ~6.5 m | [Bulkman3D GT2 open belt](https://bulkman3d.com/product/gt000-gt0003/) | **$0.54–1.73/m** [v] | cut-to-length, splice into loops with the printed clamp. Verified 2026-08-01: range confirmed, 5 mm width is GT2-5W-1000, sold 1 m per piece |
| **Drive motor** | MKS SERVO42D closed-loop stepper, NEMA17, **CAN MT** (board + motor) | 10 | [P3D](https://p3d.mx/products/makerbase-mks-servo42d-nema17-foc-motor) · [ElectroPeak](https://electropeak.com/mks-servo42d-nema17-closed-loop-stepper-motor) | $35 ea [m] | get **MT** (board + motor = the working actuator); **MB is the board ONLY**. MB/MT confirmed 2026-08-01 from Makerbase's own listings — all four SKUs are SERVO42D {RS485,CAN} × {MB,MT}. **⚠ MANUAL CHECK — the MT price is behind a variant dropdown that no fetch can read.** What is confirmed: ElectroPeak's linked page is the **driver only at $12.50** (motor explicitly not included) — that link is WRONG for this row and should be replaced. P3D lists "from $22.00" and makerbase3d.com "from $22.99", both of which are the **MB** floor. $35 for MT is therefore *plausible* (MB ~$22 + a bare 42 mm NEMA17 ~$13) but is **not a verified figure**. This is the largest line in the BOM (10 × $35 = $350); select CAN MT in the cart and record the real number before ordering. |
| **Lead screw + nut** | Tr5×1 trapezoidal (5 mm, 1 mm lead, 1-start, self-locking) + brass nut | 10 | [eBay Tr5×1 + brass nut](https://www.ebay.com/itm/396869709608) · mfr [ALM](https://www.autolinearmotion.com/5mm-trapezoidal-lead-screw.html) | ~$3 ea [m] | cut to ~61 mm; eBay listings rotate—AliExpress/ALM are stable fallbacks. **MANUAL CHECK 2026-08-01:** the eBay listing timed out on fetch and eBay item IDs rotate anyway; ALM (the manufacturer) publishes **no prices at all** — quote-only, "Inquire" button, sales@autolinearmotion.com. There is no fetchable listing for this row. |
| **Screw support bearing** | MR85ZZ deep-groove, Ø5 × Ø8 × 2.5 | 10 | [Bearings Direct](https://bearingsdirect.com/mr85-zz-mini-ball-bearing-5x8x2-5-shielded-l850zz/) · [Trianglelab](https://trianglelab.net/products/mr85zz) | **$0.49–4.38 ea** [v] | + a Ø5 thrust washer for the axial string pull. Verified 2026-08-01 — the spread is real and worth acting on: **Trianglelab $0.49 ea** (71 sold, in stock) vs **Bearings Direct $4.38 ea** (160 in stock, 5 % off @10). Same bearing, 9× the price; buy Trianglelab unless you want the US warehouse. 10 off ≈ **$5**, not $30. |
| **Axial retainer** | Ø5 set-screw shaft collar (or a 2nd Tr5 nut) | 10 | [ServoCity 5 mm collar](https://www.servocity.com/2920-series-steel-set-screw-collar-5mm-bore-2-pack/) | **$2.50 ea** [v] | locks the screw against the support bearing. Verified 2026-08-01: $4.99 / 2-pack, in stock — figure was exactly right |
| **Bridge bearing** | 693ZZ deep-groove, Ø3 × Ø8 × 4 | 10 | [VXB 693ZZ ×10](https://vxb.com/products/693zz-3x8-shielded-3x8x4-miniature-bearing-pack-of) · [Bearings Direct](https://bearingsdirect.com/693-zz-mini-ball-bearing-3x8x4-shielded-r830zz/) | **$3.00 ea** [v] ⚠ | one per string; string rides the Ø8 OD. **Corrected 2026-08-01 — the old "~$1 ea" was wrong by 3×.** VXB sells a 10-pack at **$29.99** = $3.00 ea (5–10 business days to ship); Bearings Direct is **$4.38 ea**, 298 in stock, 5 % off @10. Note the cost summary's "10× 693ZZ ~$30" was already right — it was this row that disagreed with it. Unlike the MR85ZZ there is no $0.49 source here |
| **Bridge axle** | Ø3 **g6/h6 precision shaft**, ~105 mm (e.g. hardened ground shafting) | 1 | [McMaster 3 mm shafts](https://www.mcmaster.com/products/linear-shafts/) | ~$3 [m] | NOT an m6 dowel — m6 is press-fit in a 693ZZ bore; the shaft must slide through all 10 bearings + 9 comb fingers + both arms. NO GLUE: the −Y arm's bore is blind (the 1.6 wall is the −Y stop) and one M2 grub down the +Y arm's free top closes +Y — length must land between y −52.5 and past the grub at +51.75 |
| **Guide rod** | Ø2.5 × 28 mm hardened/ground dowel (DIN 6325, standard length) | 10 | [McMaster](https://www.mcmaster.com/products/hardened-dowel-pins/) · [eBay DIN6325 2.5 mm](https://www.ebay.com/itm/303389911894) | ~$0.5 ea [m] | anti-rotation; drops in from the top through the stop bar's snug hole + the carriage's C-bore, landing in a blind socket — friction-held both ends, and the ledges are hard stops at both ends of travel (no glue: the rod is captive between the upper bar it threads through and the blind lower socket) |
| **Nut break dowel** | Ø2 × 4 mm steel dowel (52100) | 10 | [McMaster 91595A018](https://www.mcmaster.com/91595A018/) | $12.70 / pack [m] | gauged break pins (the scale "0"); drop into their slots from above. (Clamps bear on solid PETG-GF — no anvil.) |
| **M4 cup-tip set screw** | M4 × 0.7 cup-tip, 10 mm, alloy | 11 | [McMaster 91390A114](https://www.mcmaster.com/91390A114/) | $7.28 / pack 100 [m] | clamps each plain string end onto its anvil (10) + 1 pickup -Y retention grub (threads its heat-set insert, cup tip pushes the pickup +Y against the plate's +Y wall — locks the pickup to the plate only, so the plate still travels) |
| **M4 pickup-jack screw** | M4 × 0.7, 20 mm, 18-8 SS button head (hex drive) | 3 | [McMaster 92095A-series](https://www.mcmaster.com/92095A192/) | ~$12 / pack [m] | pickup height LEADSCREW jacks: the button head is captured in a deck counterbore (free to rotate, axially fixed), the shank threads the plate's heat-set nut so turning it from +Z walks the pickup up/down; 20 mm spans the height-adjust range across the 15–22 mm pickup depths + string gap. **Confirm the ×20 length suffix (…A196-class) at purchase.** NEW part — replaces the stale "3 cup-tip height screws" (those pre-date the leadscrew jack) |
| **M4 heat-set insert** | M4 × 0.7 brass heat-set, 4.7 mm | 18 | [McMaster 94459A150](https://www.mcmaster.com/94459A150/) | $10.82 / pack 50 [m] | 10 nut clamps + 4 leg-sleeve pinch collars + 3 pickup-carrier jack nuts + 1 pickup -Y retention grub; deeply buried (no pull-out) |
| **M4 mount screw** | M4 × 0.7, 12 mm, 18-8 SS (button or socket head) | 4 | [McMaster 92095A192](https://www.mcmaster.com/92095A192/) | $14.77 / pack [m] | 4 leg-sleeve pinch bolts, into 94459A150 inserts; **M4 × 0.7** (coarse) to match the inserts — NOT the M4 × 0.5 fine-thread 90751A120. (The old "pickup X/Y clamp screw" is retired — the pickup Y-lock is now the -Y cup-tip retention grub above) |
| **M4 hold-down screw** | M4 × 18 mm, thread-forming for plastic | 1 | [McMaster](https://www.mcmaster.com/) | ~$8 / pack [m] | the single +Z screw locking the merged keyhead nut-block endplate down — up from the floor bottom, thread-forming into its PETG-GF boss (the rest of the body is held by joinery) |
| **Fasteners** | M3 (NEMA17 mounts), M2 (belt clamps) | — | [McMaster](https://www.mcmaster.com/) | — | commodity |
| **M2 grub screw** | M2 × 0.4 cup-tip set screw, 3 mm | 3 | [McMaster](https://www.mcmaster.com/) | commodity | axial retention where no shoulder can exist because the shaft installs THROUGH its bearings: 1 per knee-lever axle (onto the D-flat) × 2 levers + 1 in the bridge endplate's +Y arm onto the Ø3 bridge shaft. Self-tapped — the walls (2.9 / 2.0) are too thin for a heat-set pocket, and the load is only "stop it sliding" |

## Electronics (compute bay)

The printed tray in the keyhead bay carries tool-free snap mounts for the whole
stack. **There is no longer a basic/pro split** — every instrument gets a Pi, so
the B/P column below is historical and every row is fitted. Panel I/O (1/4" TS line out, DC
power inlet, USB-C) mounts through the recessed wall in the bridge endplate's
lower corner — the instrument's right face.

**Price verification status.** Every row in this table was checked against a live
listing on **2026-08-01**; see the sweep summary at the top of the file. The
**B/P** column is a leftover from the retired basic/pro split; every row is now
fitted on every instrument.

| Part | B/P | PN / source | ~Price | URL |
|------|-----|-------------|--------|-----|
| **Teensy 4.1** | B | PJRC via SparkFun | **$31.50** [v] | [SparkFun](https://www.sparkfun.com/teensy-4-1.html) |
| **Teensy 4 Audio Shield Rev D** | B | SGTL5000, SparkFun | **$9.80** [v] | [SparkFun](https://www.sparkfun.com/teensy-4-audio-shield-rev-d.html) |
| **CAN transceiver** | B | SN65HVD230DR (DigiKey) | **$2.45** [v] ⚠ **stock 0** | [DigiKey](https://www.digikey.com/en/products/detail/texas-instruments/SN65HVD230DR/404367) |
| **Buck 24→5 V 1 A** | B | Pololu D24V10F5 (powers Teensy) | **$12.95** [v] | [Pololu](https://www.pololu.com/product/2831) |
| **Signal relay** | B | Omron G5V-1-DC5 SPDT (true-bypass) | **$2.74** [v] | [DigiKey](https://www.digikey.com/en/products/detail/omron-electronics-inc-emc-div/G5V-1-DC5/87831) |
| **Buffer op-amp** | B | OPA2134PA DIP + passives | **~$11** [v] | [DigiKey](https://www.digikey.com/en/products/detail/texas-instruments/OPA2134PA/254686) |
| **1/4" TS panel jack** | B | Neutrik NMJ4HCD2 (Ø11.4 hole) | **$2.53** [v] | [DigiKey](https://www.digikey.com/en/products/detail/neutrik-americas-inc/NMJ4HCD2/29371256) |
| **DC barrel panel jack** | B | Same Sky PJ-005A (Ø8 hole, 2.0 pin) | **$3.07** [v] | [DigiKey](https://www.digikey.com/en/products/detail/same-sky-formerly-cui-devices/PJ-005A/165838) |
| **USB-C panel coupler** | B | Adafruit 4261 F↔F (USB 2.0, Ø30 hole) | **$7.50** [v] | [DigiKey](https://www.digikey.com/en/products/detail/adafruit-industries-llc/4261/10287031) |
| **Rotary/4-way joystick** | B | Alps RKJXT1F42001 (sole UI control) | **$9.22** [v] | [DigiKey](https://www.digikey.com/en/products/detail/alps-alpine/RKJXT1F42001/19529127) |
| **OLED display** | B | 2.42" 128×64 SSD1309 SPI (UI screen) | ~$17 [m] | [Waveshare](https://www.waveshare.com/2.42inch-oled-module.htm) |
| **USB 2.0 hub** | B | Adafruit CH334F (share 1 port: Teensy+Pi) | **$4.50** [v] | [Adafruit](https://www.adafruit.com/product/5999) |
| **USB cable, optical board → Pi** | B | **USB-A ↔ USB-C, 1 m, USB 2.0, STRAIGHT plug** | ~$5–8 [m] | commodity |
| **Raspberry Pi 4, 2 GB** | B | Dexed + USB gadget (MIDI/audio/DFU) + USB host for the optical board | **$55.00** [v] | [PiShop](https://www.pishop.us/product/raspberry-pi-4-model-b-2gb/) |
| **Buck 24→5 V ≥3 A** | B | Pololu **D24V50F5** (5 V, 5 A, in up to 24 V). Pi 4 draws ~3 A, but see note | **$29.95** [v] ⚠ | [Pololu 2851](https://www.pololu.com/product/2851) |
| ~~10-ch audio ADC~~ | — | **DELETED.** Three PCM1864 + a carrier PCB existed to digitise ten string signals for the Pi. The optical pickup board now does its own 20-channel conversion (STM32H743ZIT6, 20× 16-bit) and sends audio over USB, so this whole path is redundant — ~$29 of ICs plus an entire board's fab, assembly and feeder cost removed | — | — |

⚠ **The buck, and the "smaller unit" idea behind it, did not survive checking.**
The row assumed the Pi-4 downgrade would also buy a cheaper regulator. It does
not: Pololu's 5 V step-down line at ≥3 A and 24 V in **starts at the 5 A
D24V50F5 at $29.95** (the next one up, the 9 A D24V90F5, is $36.82). There is no
3 A part in between — so the ~$25 estimate was $5 low and the "smaller unit"
saving is **zero**. The Pi-4 change still saves real money on the Pi itself;
it just does not save anything here. If $30 matters, a non-Pololu 5 V/3 A module
is the lever, at the cost of leaving a vendor the rest of the file already uses.

⚠ **OLED [m]:** both the Waveshare product page and RobotShop return **HTTP 403**
to automated fetches, so the ~$17 is unconfirmed. A German reseller lists the
yellow variant at €18.00, which is at least consistent. Needs a manual look.

**Why the Pi dropped from a 5/8 GB to a 4/2 GB:** audio→MIDI now runs on the
optical pickup's own MCU, so the Pi's remaining jobs are Dexed (a DX7 emulation,
light), USB gadget duty, and hosting the optical board. None of that is Pi 5 work.
Pi 4 is the floor rather than a Zero 2 W because the design needs USB **host and
gadget simultaneously** — host for the optical board, gadget to the computer — and
the Zero's single OTG port can only be one at a time. The panel **USB-C** still
only needs USB 2.0 (480 Mbps).

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

Every player input — **5 knee levers + 5 pedals** — is a **contactless magnetic
angle sensor** rather than a switch or a pot: a diametrically-magnetised magnet
rides the control's axle and an MT6701 reads its angle across an air gap. There
is no wiper to wear out and no mechanical calibration. The boards are our own
(they panelise with the tee PCBs — see Connectors); these are the two parts that
populate them.

| Part | Qty | ~Price | Source | Notes |
|------|-----|--------|--------|-------|
| **Angle sensor IC** | 11 | **$1.68 ea** [v] | [LCSC C2913974](https://www.lcsc.com/product-detail/Position-Sensor_Magn-Tek-MT6701QT-STD_C2913974.html) | ⚠ **Corrected 2026-08-04: $1.6815 at the 10+ break** (4,207 in stock). The $1.1139 recorded on 08-01 came from a search snippet, which reports LCSC's *volume-floor* price (the 1,000+ break is $1.1161) — not the price at the 11 pieces we buy. See the snippet-bias note in the optical section. Note the QFN part is **C2913974**; the more commonly cited **C2856764 is the MT6701*C*T-STD**, the SOP-8, which is the variant this row explicitly rejects — do not let the wrong LCSC code onto the BOM line. MagnTek **MT6701QT-STD**, 14-bit on-axis magnetic encoder. Take the **QFN-16**, *not* the SOP-8 variant: the air gap is measured to the IC's own top surface, so the package height comes straight out of the gap budget, and the SOP-8 is ~1.5 mm tall — twice the QFN — on the axis where we have the least room. Datasheet §9.2: D = E = 2.900–3.100, **A (total height) = 0.700–0.800** (the model carries the 0.800 max). §1.2: *"Sensing Center at Geometry Center"* — so the package body centres on the axle axis with no per-package offset. Assembled by JLCPCB onto our sensor PCB alongside the tee boards — no hand soldering |
| **Diametric magnet** | 11 | **$0.40 / $0.332 @10** [v] | [DigiKey](https://www.digikey.com/en/products/detail/radial-magnets-inc/8995/5126077) | Radial Magnets **8995** — NdFeB **N35, Ø6 × 2.5 mm, DIAMETRICALLY magnetised**, NiCuNi, 80 °C, 3873 G surface; ~9k in stock. ⚠ **Diametric, NOT axial** — axial discs are far more common and simply do not work here (DigiKey lists the direction in the specs, so it is checkable at order time). It is also the datasheet's own **recommended magnet** (§5: "Ø6mm x 2.5mm"), so this pair is the configuration the IC was characterised in. Drops into the axle's end pocket; `kl_magnet_cap` screws over it — no adhesive |

*(qty 11 = **10 controls** + 1 spare. The controls are not modelled yet — only
two knee levers exist in `src/` — but the count is fixed by the instrument: 5
foot pedals + 5 knee levers, each with its own sensor board. An earlier revision
of this section said 4 knee levers + 3 pedals and was sized for 7.)*

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

## Filament (printed parts)

Estimated at 2 perimeters (0.8 mm nozzle → 1.6 mm walls) + 15 % infill. Pickup
parts excluded. **Prices verified 2026-08-01: PCTG $29.95/kg** (was $25 — 3D-Fuel
Pro PCTG Natural), **PETG-GF $25.99/kg on sale, $29.99 list** (Tinmorry — the
$30 assumption was right at list), **TPU $22.99** (Tinmorry 95A, ⚠ **currently
SOLD OUT**). Net effect on the filament line is about **+$3**; the masses below
are model estimates and were not re-derived. The build
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
  — **$22.99 (from $24.99), but ⚠ SOLD OUT as of 2026-08-01.** Only ~40 g is
  needed, so any 95A spool serves; pick a substitute at order time rather than
  waiting on this SKU.
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
(~$16) for the pickup/audio runs. **~$35.** Excludes the **10 control sensor drops** (5 pedals + 5 knee levers,
not yet modelled) and the optical pickup's USB + 5 V feed. All cross-rib raceways pass ≤ Ø2.6 and sit above the
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

Prices **re-verified on DigiKey/LCSC 2026-08-01** (stock healthy unless noted).
This whole table held up except the chassis TRRS jack, which was **$3 low**. XH harness = crimp-your-own (contacts ~$0.03 vs
$0.59–0.78 per pre-crimped lead — 20×; needs a ~$25–45 tool, below).

| Role | Part | Qty | Price (verified) | URL | Notes |
|------|------|-----|------------------|-----|-------|
| **TRRS plug + cable** (bar cradle) | Tensility **CA-354S** (053-0113R): molded plug Ø10, barrel Ø3.5×14, 1.83 m Ø3.7 shielded 26 AWG cable, tinned ends | 2 | **$3.53 / $2.996 @10** [v] | [DigiKey](https://www.digikey.com/en/products/detail/tensility-international-corp/CA-354S/382910) | zero-solder: cut cable to length, crimp XH on the cut end. #1 = bar cradle → first bar tee; +1 spare. (The old #2 "leg-column riser" is DELETED — the column is an off-the-shelf extension cable now, next row.) [Drawing](https://tensility.s3.us-west-2.amazonaws.com/uploads/pdffiles/053-0113R.pdf) |
| **TRRS M→F EXTENSION cable** (the WHOLE wired leg column) | Off-the-shelf 3.5 mm 4-pole (TRRS) headset extension, ~1.2 m, shielded; **pick at purchase & verify**: molded plug handle ≤ Ø10 (head seat), inline jack barrel ≈ Ø9.1–9.7 × ≤40 (shaft seat, 10-03404-class envelope) | 1 | ~$5–8 | (commodity; e.g. DigiKey/Amazon 4-pole extension) | ZERO connections on the leg (user): the molded PLUG sits captive in the latch head (blind-mates the chassis jack), the molded FEMALE barrel seats mouth-down in the shaft block (receives the bar tower's plug), the middle gets the heat-set slack COIL (Ø8 mandrel, 85 °C). No solder, no crimps, no junction anywhere in the column. |
| **TRRS jack + cable** (chassis, above the -X/+Y socket) | Tensility **10-03404**: molded jack Ø9.1×39.4, 0.91 m Ø3.8 shielded 28 AWG cable | 1 | **$8.19 / $6.96 @10** [v] ⚠ | [DigiKey](https://www.digikey.com/en/products/detail/tensility-international-corp/10-03404/11196637) | embedded VERTICALLY above the socket — the column-top plug BLIND-MATES on the latch press (plug spins freely in the jack → no wire twist); cable → tee 12 (crimp XH at the cut end — off-leg). [Drawing](https://tensility.s3.us-west-2.amazonaws.com/uploads/pdffiles/10-03404.pdf) |
| **TRRS jack, SMT** (leg-shaft auto-mate, on the leg carrier PCB) | LCSC-library compact SMT jack, **pick at PCB design** (SJ-4351X-class, ~13×6×5) | 2 | ~$0.30 | LCSC | the only form factor that fits the Ø20 shaft; factory-assembled on the carrier (no consignment). Pocket gets rebuilt around the chosen part's drawing. Fallback: Same Sky SJ-43514-SMT-TR via JLCPCB global sourcing |
| **XH crimp contacts** | JST **SXH-001T-P0.6** | 300 | **$0.0235–0.047** [v] | [DigiKey](https://www.digikey.com/en/products/result?keywords=SXH-001T-P0.6) | 22–30 AWG; qty includes learning-curve scrap |
| **XH housings** | JST **XHP-2 / XHP-4 / XHP-6** | ~30 | **$0.10** [v] | [DigiKey](https://www.digikey.com/en/products/result?keywords=XHP-4) | contacts click in by hand, extractable; XHP-6 mates the SERVO42D pigtail |
| **XH header**, SMT side-entry | JST **S4B-XH-SM4-TB** | 8 | **$0.6577 / $0.2889 @800** [v] | [LCSC C161861](https://lcsc.com/product-detail/Wire-To-Board-Connector_JST-S4B-XH-SM4-TB-LF-SN_C161861.html) | **Sensor boards only**, and it earns the second part number: it is the piece that lets the board be SINGLE-SIDED. SMT (no post tails through a face that has to seat), side entry (a top-entry plug would have to be inserted from inside the housing). B = 15.0, 7.0 tall, 6.1 body depth, 4.5 mouth. Mates the same XHP-4 plugs and crimps as everything else, so the harness is unaffected. ~40k in LCSC stock; in JLC's library as C161861 — check it is orderable for assembly at quote time |
| **XH headers**, THT top-entry | JST **B2B/B4B/B6B-XH-A(LF)(SN)** | ~30 | **$0.17** [v] | [DigiKey](https://www.digikey.com/en/products/result?keywords=B4B-XH-A) | on every custom PCB (sensor boards, Teensy carrier, leg breakout); B4B verified, other sizes same class. Modelled from JST's own drawing (`cadkit.pcb.jst_xh_header`): B4B is **12.4 × 5.75**, **7.0 mm** tall bare and **9.8 mm mated** — the mated figure is the one clearances must use — with □0.64 posts reaching 3.4 mm below the seating plane, i.e. **1.8 mm proud** of a 1.6 mm board's far face. The pin row is **2.0 mm from one long edge, 3.75 from the other**, so the part is not symmetric about its pins and which way it faces is a real layout decision |
| **Power connector** (PSU trunk only) | XT30 pair — DFRobot **FIT0586** | 4 pr | **$1.90** [v] | [DigiKey](https://www.digikey.com/en/products/detail/dfrobot/FIT0586/9559255) | 15 A/30 A pk, gold; pigtails bench-soldered ONCE, field = plug/unplug only |
| **CAN terminator R** | Yageo **CFR-25JB-52-120R** (120 Ω ¼ W) | 10 | **$0.10 / $0.036 @10** [v] | [DigiKey](https://www.digikey.com/en/products/result?keywords=CFR-25JB-52-120R) | Teensy carrier + last motor; bus-B termination lives ON the tees (SMT 120R there) |
| **Tee PCB** | custom: 3× B4B-XH-A + 120 Ω + shunt jumper | 12 | ~$2 assembled (est.) | JLCPCB | panelized with the sensor boards; close the jumper on the LAST tee = bus-B termination |
| **Leg carrier PCB** | custom: LCSC SMT jack + B4B-XH-A header | 2 | ~$2 assembled (est.) | JLCPCB | rides the same panel; sits in the shaft pocket — auto-mate jack's terminals land on XH, fully factory-soldered |
| **FD-capable transceiver** (new PCBs) | Microchip **MCP2562FD-E/SN** | ~10 | **$1.29 / $1.07 @25** [v] | [DigiKey](https://www.digikey.com/en/products/result?keywords=MCP2562FD-E%2FSN) | rides the sensor-PCB assembly order (LCSC ~$0.50 there); VIO pin suits 3.3 V logic |

≈ **$40 of connectors + ~$25 of tee/carrier boards** (board figures are
estimates until the JLCPCB quote; tools live in the Tools section — per
project policy they're shop infrastructure, not a line item weighed against
any one approach). Fallback if crimping
frustrates: JST pre-crimped leads [ASXHSXH22K203](https://www.digikey.com/en/products/detail/jst-sales-america-inc/ASXHSXH22K203/9961918)
(**$0.78 / $0.5878 @50** [v], 200 mm socket-socket — cut in half = 2 pigtails).
Molded TRRS cables were dropped: DigiKey's are special-order/obsolete
(SparkFun 14163/14164) and the lean topology needs none — if an external
TRRS hop ever appears, any consumer 4-pole aux cable serves. Audio stays as
already pinned above (Neutrik NMJ4HCD2 + shielded pair, single-point ground).
The SERVO42D's own I/O is **XH2.54 native**, so the XH standard needs no
adapting at the motors.

## Optical pickup PCB (per-string sensing + on-board audio→MIDI)

One custom board lying **under the strings, firing up**, on a carrier that is part
of the bridge endplate and **rides on top of the deck**, that reads all ten
strings optically.

It spent a while hanging face-DOWN from the endplate's tie bar. Optically that is
better — a down-firing sensor is shaded by its own mount, free, and sheds debris
instead of collecting it — but it put structure 3 mm over the strings starting
14.5 mm out from the termination, straight through the **palm blocking** zone.
Blocking is core right-hand technique, so that mount lost.

Riding on the deck rather than taking a deck slot is what keeps the magnetic
pickup whole: there is a **14.0 mm clear band** between the pickup cavity's +X
edge (−30.62) and the deck's end at the endplate (−16.60), and the entire sensing
section lives in it. The carrier is monolithic with the endplate so the sensor
standoff — the signal-critical dimension — references the bridge directly rather
than through the deck panel's tolerance stack. It replaces nothing in the signal path — the
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
| 1 | U6 | MCU — **STM32H743ZIT6**, 20× 16-bit ADC ch, USB OTG_HS via ULPI | LQFP144 | 22.00 × 22.00 × 1.60 |
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
| 20 | PD1A–PD10B | PIN photodiode — **Vishay VEMD4110X01**, daylight filter (740–1040 nm) | 0805 (opto) | 2.00 × 1.25 × 0.85 |
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

### Was magnetic ruled out too early? — feasibility check, 2026-08-02

The question asked: *can JLCPCB assemble magnetic coils at specific locations, so
a per-string magnetic board is orderable the way this optical one is?*

**The fabrication answer is better than hoped — and it is not about a part.**

**You do not want an assembled coil, you want an etched one.** Planar spiral
coils are **copper on the board itself**: free, positioned to layout tolerance
(±0.05 mm, far better than a placed part's ±0.2 mm), and perfectly repeatable
between boards. This is established prior art in exactly this application —
the patent literature describes PCB-coil pickups directly (*"manufactured with
high precision and highly reproducible results"*), and Cycfi's hexaphonic work
uses the approach commercially. Positioning, which is the thing the question was
worried about, is the part magnetic does **better** than optical.

An assembled inductor would be strictly worse: JLCPCB's SMD inductors are wound
on ferrite for **power conversion**, and many are **magnetically shielded** —
built to reject external flux, which is precisely backwards for a pickup.

So the question moves from "can it be built" to "would it work". Here the news
is mixed, and worth having on record.

**Turns budget — 44–50 dB down, which is survivable.** Each string owns
**9.40 mm** of pitch at the sensing row. A square spiral filling ~8.5 mm of that:

| Process | Turns/layer | Layers | N | N·A |
|---|--:|--:|--:|--:|
| 0.127/0.127 (standard) | 8 | 4 | 32 | 1,290 mm² |
| 0.09/0.09 (fine) | 11 | 4 | 44 | 1,773 mm² |
| 0.09/0.09 | 11 | 6 | 66 | 2,660 mm² |
| *reference single-coil* | — | — | *6,000* | *432,000 mm²* |

That is **162× down at best (44 dB), 335× at standard process (50 dB)** — so
roughly **0.5–1 mV** against a normal pickup's ~150 mV. That is moving-coil
cartridge territory: entirely amplifiable. And the coil is only ~6 Ω, so its
Johnson noise is ~61 nV over 20 kHz — an **~84 dB** thermal SNR. **Thermal noise
is not the problem.** Six layers instead of four is the obvious lever, at real
but modest cost.

**Interference is the problem, and it is the same objection as before.** The
coil is a 17.7 cm² effective loop antenna sitting above **ten SERVO42D steppers
with PWM current control, directly under the deck**. A rough estimate — 0.1 µT
of switching ripple over a microsecond — gives ~180 µV induced, i.e. only
**10–15 dB below the string signal**. That estimate is soft by an order of
magnitude in either direction, which is exactly why it cannot be settled on
paper. Optical coupling to that source is **zero**, not small.

The standard mitigation is real and is visible in the prior art: hex pickups
carry a **dedicated noise coil** with no string over it, subtracted from every
channel (the 13-coil array in the patent is 6 strings × 2 + 1 noise reference).
That works well against uniform fields and less well against ten independent
near-field sources at varying distances.

**Two things that do *not* favour magnetic, contrary to first instinct:**

1. **It would not halve the channel count.** A single coil over a pole has the
   *same* even-function problem in lateral motion that drove SUM/DIFF here — so
   hex pickups use **two coils per string** for exactly our reason. 10 × 2 + 1
   noise = **21 channels against optical's 20**. No MCU saving, so the LQFP144
   stock problem is not solved by switching.
2. **It does not fix the thin-string deficit.** Output rises with frequency,
   which helps the high strings, but it also scales with ferromagnetic material,
   which hurts them — the two partly cancel. Real pickups still need staggered
   pole heights. This is not the escape from the .014 problem it looks like.

**And one thing that is a genuine strike against it on *this* instrument:**
magnets **pull on the strings**. Damping and pitch-pulling ("Stratitis") are
tolerated on a guitar; on an instrument built around motorised tuning to a few
cents and long sustain, adding a bridge-end magnetic load works directly against
two of its headline goals. Optical exerts **no force on the string at all** —
and there is already a Lace Alumitone in the instrument for the audio path,
which ten new magnets at the bridge would sit right beside.

**Verdict: optical stays, but the case is narrower than "no magnetic crosstalk".**
Magnetic is manufacturable, cheaper in parts (coils free, ~$4 of magnets against
$11.88 of emitters and detectors), and better positioned. It loses on motor
interference, string loading, and — decisively for the effort involved — it
would not simplify the channel count or the MCU.

**The cheap experiment that would settle it**, if the optical prototype
disappoints: etch a two-layer test coil, put it at the sensing station, and
measure the induced voltage with the motors slewing. That is a $2 board and an
afternoon, and it converts the one soft number above into a measurement. Worth
doing *before* any magnetic redesign, not after.

### Orderability, 2026-08-01 — every part is now a real LCSC line

Asked directly: is every part in LCSC's catalogue, in stock, in quantities that
support a preassembled build? **Every part now has a real MPN; two lines are
short on stock; one schematic decision is outstanding.**

The starting position was worse than a stock problem. **Only three of the 35
distinct lines carried a manufacturer part number at all** — the other 32 were a
*functional description plus a package envelope* ("quad op-amp, SOIC-14"), which
is exactly what the geometry model needs and is not something you can put on a
JLCPCB BOM line. And all three that did have numbers failed:

| Line | Was | Now |
|---|---|---|
| U6, MCU | `STM32H743ZIT6`, **7 in stock** (need 10) | unchanged — ⚠ still short |
| PD ×20 | `VEMD4110X02`, **not in catalogue** | **`VEMD4110X01`** — same filter, in catalogue ✓ ⚠ 72 in stock (need 200) |
| D ×10 | `VSMB1940X01`, **not in catalogue**, ±60° | **`IR17-21C/TR8`** — in catalogue ✓ but ~120° |

**Two items closed that had been open for a while:** the **ULPI PHY** is
Microchip `USB3343-CP`, in LCSC stock at **$1.78** (C633347; `-TR` reel C112967
at $2.07), QFN-24, matching the modelled envelope — the part the survey table
assumed existed. And the **quad op-amp** is `TLV9064IDR`, below.

### ⚠ Search snippets report the VOLUME-FLOOR price — every one of them was wrong

Re-checked 2026-08-04 by fetching each LCSC product page directly, after another agent
flagged that they could not read stock and would rather report unresolved than quote an
unread number. That caution was right, and checking proved it: **every price taken from a
web-search snippet was wrong, systematically in the same direction.**

LCSC's pages advertise **"from $X"**, which is the *highest volume break* — the 1,000+ or
6,000+ price. Search snippets quote that figure. It is not the price at the ten or fifty
pieces this project buys. The gap is large:

| Part | Recorded (snippet) | Actual at our qty | |
|---|--:|--:|--|
| `USB3343-CP` PHY | $1.78 | **$2.6398** @10 | +48 %, **and OUT OF STOCK** |
| `TLV9064IDR` ×5 | $0.2161 | **$0.3297** @30 | +53 % |
| `PCM1808PWR` | $0.3419 | **$0.642** @10 | +88 % |
| `MT6701QT-STD` ×11 | $1.1139 | **$1.6815** @10 | +51 % |
| `X322525MSB4SI` ×2 | $0.0334 | **$0.0959** @5 | +187 % |
| `USBLC6-2SC6` | $0.0983 | **$0.1829** @5 | +86 % |
| `AO3400A` | $0.0487 | **$0.0849** @5 | +74 % |
| `SPX3819` | $0.30 | **$0.1903** @10 | −37 % (one of two that went the other way) |

**Two part numbers were outright wrong**, which no amount of price-checking would have
caught: `C693480` is a **P6KE39CA TVS diode**, not the `TLV9061IDCKR` op-amp it was recorded
as (correct code: **`C398357`**); and `C1017`, recorded for the ferrite bead, **404s** — that
part number does not exist. FB1 is now an explicit OPEN.

Board parts cost **$26.96 → $29.07**, per instrument **$42.58 → $44.69**.

**Method that works**, for anyone repeating this:

* **Fetch `lcsc.com/product-detail/C<number>.html`** — the short canonical form. It returns
  the full quantity-break table *and* exact stock. It is not client-side rendered.
* **Never fetch `lcsc.com/search?q=…`** — that one *is* client-side and returns only page
  furniture, which is what makes LCSC look unfetchable.
* **Use web search only to find the C-number**, never to read a price off the snippet.
* **Take the break matching your build quantity**, not the headline. Ten instruments means
  10 of a per-board part and 100–200 of a per-string part — different breaks.
* ⚠ **LCSC stock ≠ JLCPCB assembly stock.** Everything here is LCSC's figure. For a PCBA
  order JLC's own inventory governs, and that is on `jlcpcb.com/partdetail/…`, which *is*
  client-side. Treat these as a strong proxy and confirm at quote time.

### Part selection — done 2026-08-01, and now enforced by the model

**Every one of the 141 placed parts now maps to an orderable line.** The mapping
lives in `src/optical_pickup.py::_MPN_RULES`, and `_assert_every_part_orderable()`
runs at import: **add a part without a sourcing decision and the build fails.**
The 141 parts collapse to **18 distinct order lines**, of which 5 are JLCPCB
Basic classes (no feeder charge):

| Line | MPN | LCSC | Qty | Ext. | Note |
|---|---|---|--:|--:|---|
| PD1A–PD10B | `VEMD4110X01` | C3211080 | 20 | **$11.60** | filtered ✓ · ⚠ 72 in stock, 200 needed |
| U6 | `STM32H743ZIT6` | C114408 | 1 | $9.93 | ⚠ 7 in stock |
| U7 | `USB3343-CP` | C633347 | 1 | $1.78 | ULPI PHY, QFN-24 ✓ |
| U1–U5 | `TLV9064IDR` | C388176 | 5 | $1.08 | **the TIA part** — see below ✓ |
| U9 | `SPX3819M5-L-3-3/TR` | C9055 | 1 | $0.30 | 3V3 **analog**, 40 µVrms ✓ |
| U8 | `AMS1117-3.3` | C6186 | 1 | $0.10 | 3V3 **digital**, SOT-223 tab — 0.51 W ✓ |
| J2 | `S6B-XH-SM4-TB` | C191914 | 1 | $0.44 | 6-way, −Y edge: 2×5V, 2×PWR_GND, AUDIO, AUDIO_GND ✓ |
| U11 | `TLV9061IDCKR` | C693480 | 1 | $0.36 | single of the U1–U5 family ✓ |
| U12 | `PCM1808PWR` | C55513 | 1 | $0.34 | 24-bit audio ADC — magnetic pickup → I²S ✓ |
| D1–D10 | `IR17-21C/TR8` | C131250 | 10 | $0.28 | 940 nm 0805 · ⚠ ~120°, confirm at layout |
| J1 | `TYPE-C-31-M-12` | C165948 | 1 | $0.20 | the modelled envelope *is* this part ✓ |
| U10 | `USBLC6-2SC6` | C7519 | 1 | $0.10 | ⚠ SOT-23-6, not the modelled SOT-563 |
| Cf×20 | 0402 **C0G** MLCC | Basic | 20 | $0.08 | C0G not X7R — the anti-alias pole must not drift with bias |
| C×7 | 0805 X7R MLCC | Basic | 7 | $0.07 | bulk + audio ADC bypass |
| Y1, Y2 | `X322525MSB4SI` | C13740 | 2 | $0.07 | 25 MHz 3225, **Basic** ✓ |
| C×34 | 0402 X7R MLCC | Basic | 34 | $0.07 | decoupling |
| R×29 | 0402 thick-film | Basic | 29 | $0.06 | TIA feedback + pulls |
| Q1 | `AO3400A` | C20917 | 1 | $0.05 | logic-level FET ✓ |
| R1–R10 | 0603 thick-film | Basic | 10 | $0.03 | per-string LED ballast |
| FB1 | `GZ2012D601TF` | C1017 | 1 | $0.02 | 600 Ω @100 MHz ✓ |
| | | | **148** | **$26.96** | **`open_lines()` is empty** |

**The op-amp is the happy surprise.** `TLV9064IDR` is a 4× CMOS RRIO part with
**10 MHz GBW and 500 fA input bias current** — the bias figure is what a nanoamp
TIA actually needs, and 500 fA against tens of nA is four orders of margin. It is
SOIC-14 (the package already modelled, chosen for its 6.00 mm across-leads in a
14 mm band), 10,148 in stock, and **$0.2161** — so all five cost **$1.08**
against the $4 assumed. Cheapest part of the front end and the one with the most
performance riding on it.

**Parts cost is computed, not estimated: `parts_cost()` = $26.66/board.** The
run of that figure — $29 assumed → $41.60 extrapolated → $36.95 on first
selection → **$26.66 resolved** — is worth reading as a caution about estimates
built from part *counts*: it was wrong by up to 56 % in both directions, and it
only settled once every line had a real part number behind it. BOM.md can no
longer drift from the model here.

### The three blockers, resolved 2026-08-01 — `open_lines()` is now empty

**1. Photodiode — the dilemma was a false alarm.** The choice looked like
"break the no-consignment rule, or give up the daylight filter". Neither is
needed: **`VEMD4110X01` carries the same filter.** Its LCSC page specifies a
*"silicon PIN photodiode with daylight blocking filter"*, 740–1040 nm, matched
to 830–950 nm emitters — the same 0.42 mm² area, same ±55°, same 0805
2.0 × 1.25 × 0.7 as the absent X02. It is a drop-in, and it is the part LCSC
stocks. The whole consignment-vs-filter argument in the previous revision was
built on the assumption that X01 was the unfiltered variant. It is not.

It is also **cheaper than recorded**: 10 boards need 200 pieces, which clears
the 100+ break at **$0.58** (vs $0.9334 @1). That takes the detector line from
$18.67 to **$11.60/board**.

⚠ **Stock is still 72 against 200 needed** — the one genuine constraint left on
this part. It must recover, or be pre-ordered ahead of the run.

**2. Emitter — chosen, and the budget's first lever is confirmed DEAD.**
`IR17-21C/TR8` (C131250), Everlight, 0805, 940 nm, **$0.0283** — against the
$0.35 the BOM assumed, so the emitter line drops from $3.50 to **$0.28/board**.

The important part is not the price. **Narrow-beam is not made in 0805.** Every
candidate checked is wide: Kingbright KP-2012F3C 120°, APT2012F3C 120°, and
Everlight's `IR19-21C` is **150° — and 0603**, wrong on both counts. So lever 1
of the signal budget (*"the largest and it is free"*, +9.5 dB at ±30°, +13.6 at
±20°) is **unavailable in this package**, not merely unchosen.

⚠ **Correction to the previous revision of this file, which proposed
collimating in the printed cover to recover the gain. That does not work, and
the reason is worth stating because the idea is intuitive and wrong.** An
aperture *discards* off-axis flux; it does not redirect it. The on-axis
intensity heading for the string is unchanged, so the returned signal is
unchanged — a tube costs light and gains none. The +9.5/+13.6 dB in the budget
comes from a **lensed** emitter, which redirects the *same total flux* into a
narrower cone and so genuinely raises on-axis intensity. Geometry cannot
substitute for optics here.

What cover apertures *do* buy is real but different: **crosstalk between
adjacent strings, and ambient rejection**. Both worth having, neither is signal.
The cover is therefore left as one slot per string. (A split three-aperture lid
was worked through and rejected on printability: with `PD_DY` = 1.6 and a 0.8 mm
minimum wall, the webs between emitter and detector apertures come out at
0.2–0.4 mm — under one bead.)

So the deficit moves to **levers 2 and 3**, per-string LED current and per-string
TIA gain, which are already ten and twenty independent parts. Both are more
valuable now than when they were ranked second and third. That also raises the
stakes on J2: drive current is the lever, and the 5 V rail is what feeds it.

**3. J2 — refitted and done.** `S2B-XH-SM4-TB` is not a JST part; the SMT
side-entry XH line **starts at 4-way**. Now `S4B-XH-SM4-TB` (C161861) — already
the sensor boards' connector, so **no new part number and no new feeder**, and
four ways suits a rail pulling >500 mA better than two would have (2× 5 V,
2× GND). Cost is **5.0 mm of board length**: 184.4 → **189.4 mm**, area 69.0 →
**70.8 cm²**, about $0.18/board of fab. The model carries the real JST envelope
(`XH-SM-4`, 6.10 × 15.00 × 7.00) and all clearance assertions pass.

### The digital rail — resolved, and NOT with the buck I proposed

The MCU draws 200–300 mA, so 5 V → 3.3 V burns **0.51 W**. In a SOT-23-5 at
~250 °C/W that is a >100 °C rise — past the package, not marginally. So U8 could
not stay an SPX3819. Correct.

**But "make it a buck", which the previous revision recommended, is the wrong
fix for this board.** A switching regulator at ~1 MHz sitting alongside **20
transimpedance amps reading tens of nanoamps** trades a thermal problem for a
noise problem on the axis this design is most sensitive to. The file already
worries about exactly this in another place — the LED driver's switching noise
being *synchronous with sampling* so ambient subtraction cannot remove it. Adding
a second switcher to fix a heat problem is solving the cheap problem with the
expensive one.

**The heat is the cheap problem: spend package area on it.** U8 is now
**`AMS1117-3.3` in SOT-223** (C6186, $0.1045) — a tab package at ~50 °C/W with a
copper pour, so 0.51 W is a **~25 °C rise**. The board stays switcher-free.
Headroom is fine: 1.7 V available against AMS1117's 1.3 V max dropout — though
that is the one number to watch if the 5 V rail sags over the cable and the XH
connector, and it is an argument for keeping J2's doubled pins.

U8 and U9 are now **different parts**, which costs one line: U9 stays the
low-noise `SPX3819` (40 µVrms) on the analog rail, where its ~40 mA load makes
SOT-23-5 fine. The split is the point — the noisy cheap regulator feeds the MCU,
the quiet one feeds the front end. Cost: **+0.7 mm of board**, and parts actually
fall $0.20 because the AMS1117 is cheaper than a second SPX3819.

**Nothing is now outstanding on this board's schematic.**

**141 placed parts**, all on ONE side (single-sided, per project rule: one
stencil, one reflow, no back-side placement). The model tracks 35 distinct
(description, package) lines; the table above merges four bulk-cap variants and
the two CC pull-downs into single rows.

**Board**: 4-layer, 1.6 mm FR4, two sections. A **13.6 mm-wide sensing strip**
(X −30.4…−16.8) running the string field, carrying the row, the ten ballast
resistors and all five quad op-amps; then a **30 mm-wide tail** (X −46.8…−16.8,
Y −104.2…−56.1) for the digital block, which widens only past the pickup cavity's
−Y edge where the deck is solid again and nothing is overhead. The MCU is 16 mm
over its leads and simply does not fit the band — that is what forces the tail.
Single-sided, every part on the TOP face, so the whole underside bears on a solid
plinth: no ledges, no floor to fuse back.

### The thin-string signal budget — why the outline steps

Optical signal scales with the string's **diameter**: the string *is* the target,
and what comes back is set by how much of the beam it intercepts. Across this set
that is .014 against .070 = 5.1× = **14.0 dB**, and the thin strings sit up to
0.71 mm further from the sensor plane (which references the *thickest* string's
top), so call it **~16 dB**. That deficit lands on exactly the strings the player
uses most. Note the hard string for *latency* (low C, long analysis window) and
the hard string for *SNR* (string 2, .014) are opposite ends of the set.

Four levers, spent in order of cost:

1. ~~**Emitter beam angle — the largest and it is free.**~~ ⚠ **UNAVAILABLE — see
   the emitter note above.** The arithmetic still holds: at the 3 mm standoff a
   ±60° emitter throws a ~10.4 mm spot and a 0.356 mm string intercepts ~3 % of
   it; ±30° → 3.5 mm spot, ~10 %, **+9.5 dB**; ±20° → **+13.6 dB**. But **narrow
   beam is not made in 0805**, so none of it is purchasable. D1–D10 are
   `IR17-21C/TR8` at ~120°, i.e. the ±60° row of that table — the worst case the
   analysis was written against. **Levers 2 and 3 are therefore the first and
   second levers, not the second and third**, and are correspondingly more
   important than their position here suggests.
2. **Per-string LED current** (R1–R10, already ten independent parts). Roughly
   linear in signal. This is what forces J2 — see below. **Now lever 1.**
3. **Per-string TIA gain** (Rf, already twenty independent parts). Bounded by the
   op-amp's gain–bandwidth product, not by the resistor: thin strings want more
   gain *and* more bandwidth, and Rf × Cin trades one against the other.
4. **Distance from the termination** — the worst lever: signal is linear in
   distance, so gain is only 20·log10(d/d₀) dB. Equalising .014 would need 60 mm.

**The stepped row was dropped, and the 14 mm band is why.** The band holds ONE
sensor row plus the transimpedance amps — not two rows plus the amps. Keeping
every TIA within a few mm of its photodiode beat the step's +5.3 dB: the summing
node is the noise-critical point on a board reading tens of nanoamps, and the
alternative was a ~90 mm trace sharing a board with a 96 kHz LED driver whose
switching noise is **synchronous with sampling**, so ambient subtraction would not
cancel it. The single row sits at **15.5 mm** for all ten — further out than the
old wound row, so every string gains ~+1.9 dB and the thin ones give up 3.4 dB
relative to the stepped plan.

**The cover (printed part `optical_cover`).** Up-firing is what makes this
necessary: the detector looks at the sky, and ambient subtraction fixes flicker
and offset but **not saturation**. An up-firing sensor also collects the skin and
string shed a down-firing one sheds. The lid gives each string its own aperture
and closes the shallow-angle path with a −X wall (from +X the endplate already
does it). Be honest about the limit: at a 3 mm standoff a slot cannot collimate
much — geometric rejection is a few dB. Print it **dark**: it is the one surface
facing the detectors.

**The spectral filtering is NOT in the cover — it is inside the detector**, and
that is the better place for it. An earlier revision of this section named a
bonded IR-pass window as "the obvious next addition if the prototype says sun is
a problem". That is now largely done for free: the `VEMD4110X01` carries a
**daylight-blocking filter, 740–1040 nm**, and the 940 nm emitter sits inside
that window. See "optical filtering" below for what it does and does not cover.

**What the slits actually are.** They are the **optical apertures** — one per
string, 5.0 mm wide in Y and running −X from the triplet, each centred on its
string and serving that string's emitter plus both photodiodes. The lid is
otherwise solid, so without them the sensors see nothing: they are the hole the
light goes out and comes back through, not an optional feature. On a 9.40 mm
string pitch that leaves a **4.40 mm web** between neighbours.

**Their −X end is open, not a flat wall** — see "the aperture's printable end"
below for the two shapes that failed first.

**Why the triplet runs along Y (across the string) and not along X (down it).**
This is forced, and the reason is *not* humbucking — there is no magnetic
circuit here to hum-cancel. It is that **Y is the axis DIFF has to resolve**.

The two detectors flank the emitter so that SUM is an *even* function of lateral
displacement and DIFF is *odd*; DIFF is what tracks the string's Y motion, and
DIFF is the whole defence against the 2f₀ octave error when the vibration plane
precesses toward horizontal. Put the same three parts along **X** instead and
both detectors sit under the *same* point of the string's lateral motion —
they see the same signal, **DIFF collapses to nearly zero**, and the octave-error
defence goes with it. What little difference remained would be the small
amplitude change from sensing at two distances from the termination: common-mode,
not lateral information.

There is a second, weaker reason pointing the same way: the sensing band is only
14 mm in X and has to hold the row *and* the transimpedance amps. Three 2.0 mm
packages in a line would spend 6 mm of it.

Worth noting the one thing an X-wise row would actually do better: it would keep
both detectors on their own string's axis, so **neighbour crosstalk would drop**.
At ±1.6 mm the detectors sit 1.6 mm nearer the adjacent string (7.8 mm away
instead of 9.4). That is a real cost, and it is the right trade — crosstalk is a
few dB of pedestal, while losing DIFF means confidently reporting the wrong
octave.

The nearest thing here to humbucking is real but axis-independent: both
detectors see the **same ambient**, so it appears as common mode and DIFF
rejects it. That works whichever way the pair is oriented, so it is not what
sets the orientation.

They are **not** a filter and not a substitute for one — the two do different
jobs. The detector's filter is **spectral** (which wavelengths get in); the
slits are **geometric** (from which directions, and whether dust lands on the
optics). Their three jobs are: pass the beam; cut the shallow-angle ambient path
and the crosstalk from neighbouring strings; and close the board off as a debris
lid, which up-firing optics need because they collect the skin and string shed a
down-firing sensor would simply drop.

### The aperture's printable end — an open notch, after two shapes that failed

The endplate builds **+X → −X**, so each layer is a Y–Z slice and anything it
adds must sit within 45° of the layer at +X of it. Two shapes were tried and
both were caught from renders before printing:

**1. A closed rectangular slot bridges.** The roof resumes across the full
5.0 × 1.6 mm face over void, anchored only at its two Y edges — a **5 mm bridge
directly over the optics**, the worst place for one, since sag lands in the
aperture. A layer-walk probe measures **33 unsupported samples** along one
aperture.

**2. A 45° V ("/\") fixes the bridge but does not fit.** The void must close in
**Y, not Z** — Z is *in-plane* for these layers, so tapering the roof's thickness
only makes the bridge thinner, still a bridge. Tapering in Y gives the real 45°
stepover. But the apex needs `SLOT_DY`/2 = 2.50 mm of X from the packages' −X
edge at −20.50, landing at −23.00, and **the roof stops at −22.00** because the
quad op-amps stand taller than the roof underside. Truncated there, the flank
crosses the roof's −X boundary at 45° and leaves an acute **wedge of roof
material tapering 1.50 → 0.00 mm** — a knife edge, under the 1.6 mm floor for its
entire length. Measured, not estimated.

**3. What is built: the aperture runs out of the −X edge, sides parallel to X.**
Nothing ever closes over the void, so there is no bridge; the sides are parallel
to the build direction, so there is no stepover at all; and the material outboard
of every aperture is the full 4.40 mm web rather than a taper. The roof becomes a
comb of stubby teeth (4.40 × 5.40 × 1.60) joined at +X, which is where it fuses
into the endplate's comb brace anyway.

Every feature now clears the two-bead floor, including one that did **not**
before and was nothing to do with the V — the strip of roof at +X of the aperture
was **1.40 mm**, left over from the original 3.0 mm-wide slot. The aperture's +X
edge is now derived (`APER_X1 = BAND_X0 − MIN_WALL_2P`) so it is 1.60 by
construction, and it still clears the packages by 0.30 mm:

| Feature | Size |
|---|--:|
| +X strip, roof edge to aperture | **1.60** |
| web between adjacent apertures | 4.40 |
| outboard of the outermost aperture | 1.60 |
| roof thickness (Z) | 1.60 |

**What the open end costs:** the −X end is no longer partly closed. Cheap — the
shallow-angle ambient path was already handled by the 0.30 mm gap over 5.4 mm of
depth rather than by this edge, and −X of the cover is instrument interior, not
sky.

**If a true gable is wanted**, the op-amp column would have to move ~1.5 mm −X so
the roof could reach −23.50. That trades the TIA's distance from its photodiode —
the noise-critical summing node this layout is organised around — for lid
geometry, which is the wrong way round unless something else independently wants
the op-amps moved.

### PCB thickness — 1.6 mm, and the tolerance was landing on a clearance

**1.6 mm is correct and is not a layer-count question:** it is JLCPCB's standard
thickness at 4 layers *and* at 6, so even the 6-layer option raised in the
magnetic study would not move it.

⚠ **But 1.6 is a nominal with ±10 % (±0.16 mm), and the model was using the
nominal on a dimension where the tolerance is a clearance.** The board's *top*
is the design datum, derived downward from the string. The thing that physically
exists is the printed *plinth* underneath. So a board at the +10 % limit carries
its own components **0.16 mm higher than modelled**, straight into the 0.30 mm
gap it has to slide through under the cover — leaving **0.14 mm**, over 5.4 mm of
travel, with parts on the board. The model would have called that fine.

**Fixed by datuming the plinth off the worst-case board, not the nominal one**
(`PLINTH_TOP = PCB_TOP − PCB_T_MAX`, 9.501). That makes the tolerance one-sided
in the harmless direction:

| Board | Sensor face | Roof gap | Optical gap |
|---|--:|--:|--:|
| −10 % (1.44) | 11.79 | **0.62** | 3.32 |
| nominal (1.60) | 11.95 | **0.46** | 3.16 |
| +10 % (1.76) | 12.11 | **0.30** | 3.00 |

Clearance is now **never worse than designed**; what varies instead is standoff,
which is benign — signal is linear in it, and per-string gain trims it anyway.
The cost is ~0.16 mm of extra nominal standoff, about **0.45 dB**. Trading half a
dB against a mechanical interference is the right way round. `PCB_TOP` now means
*the highest the board top can be*, so the roof-clearance assertion tests the
thickest board the fab may ship rather than the one the model draws.

Z stack (nominal board): deck 6.00 → plinth 9.50 → board 9.50–11.10 → sensor
faces 11.95 → cover 12.41–14.01 → lowest string 15.11. That leaves **1.10 mm**
over the cover. Install order is board, cover, then strings.

### The magnetic pickup reaches the Pi through THIS board

The magnetic pickup has to feed two places: the **TS jack** (which must not be degraded)
and the **Pi**. Rather than run a second analog cable the length of the instrument, it is
digitised here and travels to the Pi on the USB link this board already has. **Digitising
early is the point** — once it is bits, the Pi's ground noise has no analog path back into
the audio.

**Split AFTER the buffer, never at the coil.** The tap comes off the AFE's buffer output,
in parallel with the relay → TS branch. This is not fussiness: a magnetic pickup's tone is
set by its L, R and **total C including cable**, so hanging a second cable directly on the
coil adds capacitance, lowers and damps the resonant peak, and **changes the TS output's
tone** with zero added noise. Buffering first makes the tap physically incapable of
affecting the direct path — which is what actually delivers the "TS unaffected" requirement,
not any amount of shielding downstream.

**The audio gets its own ADC (U12), deliberately not the MCU's.** Two independent reasons,
and the first is the real one:

* **Crosstalk.** The MCU's SAR is multiplexed across 20 inputs reading **tens of
  nanoamps**. The magnetic signal is line-level — four to five orders of magnitude louder.
  Through the same sample-and-hold mux, that is exactly the contamination the whole board
  is organised to prevent, and no downstream care undoes it.
* **Pin count.** All 20 ADC channels are already one-per-photodiode. There is no 21st.

`PCM1808PWR` sidesteps both and is better on merit: 24-bit delta-sigma, ~99 dB SNR, on the
signal a listener actually hears — against a 16-bit SAR shared twenty ways. It arrives over
I²S, a *peripheral* rather than an ADC pin. The mid-rail reference the TIAs already use
(U11) is what an audio input wants for biasing, so that infrastructure is free.

### All cabling exits −Y, and it made the board smaller

Both connectors now sit on the **−Y edge with their mouths flush**, so the two plugs present
as a single cable exit instead of two at different depths (a −X exit could not be routed
cleanly). That required widening the compute section **25.40 → 32.34 mm**, derived from the
edge budget rather than typed — the −Y edge, not the LQFP144, is now what sets that width.

**Both changes were free or better than free:**

* The widening costs **nothing in billed area**. The sensing strip already sets the bounding
  box's −X extreme at −30.42; the compute section lands at −25.34, inside it, with 5.08 mm
  of headroom before the box would move.
* The board got **shorter**: 190.1 → **182.1 mm**. Moving J2 off the −X edge freed a whole
  15 mm row; the audio ADC added ~6 mm back. Then the MCU/tail-screw swap below took
  another 9.75 mm, landing at **172.4 mm**, area 71.1 → **64.5 cm²**.

### The MCU and the tail screw swap sides — another 9.75 mm off the cantilever

The MCU used to start *below* `WRAP_Y`, clear of the wrap-band seam, which cost ~9.75 mm of
board for nothing. The wrap band is **wider in X** (−30.42) than the compute section
(−25.34), and the only thing occupying it was the tail M4. So the two now share it: the
LQFP144 tucks hard −X and climbs **into** the band, and the tail screw moves hard +X to get
out of its way.

| | Before | After |
|---|--:|--:|
| MCU | X −20.17…1.83, Y −87.75…−65.75 | **X −24.14…−2.14, Y −78.00…−56.00** |
| Tail screw | (−12.00, −59.60) | **(+2.40, −59.60)** |
| Board | 182.1 mm | **171.6 mm** |
| Cantilever past the tail screw | 51.75 | **48.00 mm** |

Both screws keep the full **4.60 mm of plinth wall**; the MCU clears the tail screw's
keep-out by 1.34 mm and stops 1.00 mm below the seam. Length taken off *this* end is worth
more than the same length taken off anywhere else, because this end is the cantilever.

**The two grips are no longer at the same X, and that is deliberate.** The head screw stays
hard −X, nearest the sensor row; only the tail one moved. The mount-symmetry assertion
caught this immediately — it was written to catch exactly "one of them moved alone" — and
was **narrowed rather than disabled**: mirrored **Y** still matters (equal leverage about the
sensing field; a stale one-sided derivation is how the −Y wrap once ended up 1.05 mm
slacker), but X never was part of the datum — two points at different X locate the board
just as well, the line between them is merely skewed.

It also gained a check it never had: that **each grip actually lands in the wrap plinth**
with its full wall. That is the real requirement — a screw with nothing to thread into is
the failure that matters — and until now the X-equality test had been standing in for it by
accident.

### Routing headroom — the funnel was fine, the MCU escape was not

Two questions that look like one, with opposite answers.

**The sensor → compute funnel was never tight.** Everything from the sensing strip has to
pass through its 13.62 mm width: **20 TIA outputs + ~5 power/reference nets = 25**. At
JLCPCB's standard 0.127/0.127 that is **49 traces per layer**, so ~98 across two
inner/bottom routing layers (L2 stays a solid ground plane for the analog). **~4× margin**,
and the fine 0.09/0.09 tier is not needed. This had been worked out in discussion but never
written down, which is why it kept being re-asked.

⚠ **The MCU's escape annulus was the real constraint**, and briefly it was bad:

| Side | Stepped-in compute | −X edge straightened |
|---|--:|--:|
| **−X** | **1.20 mm** — 4 lanes | **6.62 mm** — 26 lanes |
| +X | 9.14 | 8.80 |
| **+Y** | **1.00** | **1.00** |
| −Y | 29.60 | 28.85 |

1.20 mm on a side carrying **36 pins** is not merely tight — it is under what a staggered via
fanout needs (36 vias at 0.65 mm pitch want 23.4 mm of run against a 22.0 mm package side).
Two of the LQFP144's four sides were effectively blocked.

**Fixed by running the compute section −X to `PCB_X1S`**, so the board's −X side is **one
straight line end to end** rather than stepping in near −Y. Free, because the strip already
sets the bounding box there — and the board came out marginally *shorter* (172.4 → 171.6 mm)
because the wider section packs its rows better.

**The MCU had to be re-anchored for that to help.** It was placed at `x0 + half-width`, i.e.
relative to the section edge — so widening the section would have slid the package along
with it and preserved the same useless 1.20 mm. It is now anchored to the **tail screw's
keep-out**, the only hard obstacle on that row, which is what converts the new width into
annulus instead of travel.

⚠ **+Y is still 1.00 mm and is not fixed.** Only 7.00 mm of the MCU's 22 mm top edge sits
under the sensing strip; the rest has 1 mm before the board ends. Those pins must via down at
their pads and route back south — normal practice, and viable *because* −X and −Y now have
room to receive them. If layout disagrees, the lever is moving the MCU −Y, paid for in board
length, which is the opposite of what straightening the edge just bought.

**J2 is now a 6-way `S6B-XH-SM4-TB`** (C191914, $0.4417): **2×5V, 2×PWR_GND, AUDIO,
AUDIO_GND**. Going from 4-way to 6-way adds **no harness part** — `XHP-6` housings are
already bought to mate the ten SERVO42D pigtails, and `SXH-001T-P0.6` contacts are common to
every XH size. The only new line is the board-side part itself, one feeder.

⚠ The 6-way's 20.0 mm width is **derived** from XH's 2.5 mm pitch (4-way B = 15.0, plus two
ways). Confirm against JST's drawing before layout, exactly as the S4B figures were.

**Why AUDIO_GND is a dedicated pin.** Not USB ground, and not the power ground either. USB
ground carries the Pi's return and its supply noise; a single-ended ADC measures its input
*relative to its own ground*, so any difference between source and ADC ground **is** signal —
routing the audio return through USB would sum the Pi's noise into the very signal the
architecture exists to keep clean. The power ground is no better here: the **LED row driver
switches at 96 kHz synchronously with sampling**, and that current flows in the power return,
so sharing it would inject the one noise source ambient subtraction cannot remove.

*(A 2-way THT header was considered and rejected: its post tails would protrude through the
board's underside — the face that bears flat on the plinth.)*

### Cable conduit — connectors reach the body without touching the pickup panel

Both plugs leave the board at −Y and have to get down into the instrument. The requirement
was a channel that passes a **connector**, one at a time — not merely a cable — and **no
cut-out in the magnetic pickup's top panel**.

**The deck is never touched, and that falls out of the geometry rather than needing a
dodge:** the deck's +X edge is `TP.PX0` = −16.60 and the **endplate begins exactly there**,
so out past the board the endplate's own top face is open sky. The conduit is a plain
vertical shaft in that face, dropping through the fill slab into the foot box. Verified open
at every z from +5 down to −24, and its −X edge sits **7.85 mm clear of the deck**.

**Sized by what must pass:**

| | Envelope | Source |
|---|--:|---|
| XHP-6 plug | 17.40 × 5.75 | JST's 4-way drawing (12.4) + 2.5 mm pitch × 2 |
| USB-C overmold | 12.35 × 6.50 | **USB-IF maximum** — so *any* cable passes |
| **Shaft** | **9.50 (X) × 23.00 (Y)** | +3.75 / +3.00 clearance |

**Orientation is the whole trick.** Plugs feed through with their **wide axis along Y** —
the direction the endplate has 27 mm to spare — so X only has to clear the plug's *thin*
axis. Sized the other way up the shaft needed 20.40 of X and left **2.40 mm walls in a
structural slab**; this way X needs 9.50 and the walls are **7.85**. Y has to be long
anyway, because the shaft must span past the back face of a *mated* plug so the cable can
turn down without doubling back.

**Cables and male connectors are modelled at true diameter** (`optical_cables`: USB-2 slim
shielded 2.6 mm, 6-way XH bundle 4.0 mm, plus both plug bodies) so the route is *planned*
rather than assumed. They are in the overlap gate — 391 components, no new collisions — so
if the conduit or the plinth ever moves into the cable's path, the gate says so.

The model makes one thing visible that a side view would hide: **the USB-C socket sits
entirely −X of the endplate**, so its lead travels +X as well as −Y to reach the shaft.

### The USB cable — STRAIGHT, and 1 m; the right-angle idea was wrong

A right-angle USB-C looked obviously better and **is not**, because of where J2 sits.

J1 is −X of J2, so its lead must cross J2's footprint to reach the shaft. A right-angle
leaves +X **at the plug** — which is exactly where J2's body is. Modelled, the lead turned
+X at y −112.85, dead inside J2's −120.85…−106.85 span, and drove straight through it
(caught from a render).

**The escape is a longer plug, not a detour.** A straight USB-C's own back face lands at
−126.85, already clear of J2's −120.85, so the lead turns +X in free space with a **single
bend**. The right-angle would have needed exit +X → turn −Y → turn +X: three bends to solve
a problem the straight plug does not have. "Angled saves a bend" was true only in isolation;
with the neighbour in the picture it costs two.

The lead now turns at −128.35, clearing J2 by **7.50 mm**. An assertion enforces it: any lead
crossing a neighbour in X must turn −Y of that neighbour's back face, so a future change to
plug length or socket position fails at import instead of in a render.

**J2 stays straight** for its own reason — it sits nearly over the shaft already.

**Length = 1.0 m**, from the routed path rather than a guess. `usb_run_length()` walks it
orthogonally — a harness follows the box, it does not fly point to point:

| Segment | mm |
|---|--:|
| +X to the shaft | 18.6 |
| down the shaft | 22.8 |
| along Y | 109.3 |
| **−X to the keyhead** | **568.8** |
| up into the Pi | 40.2 |
| **Total** | **759.7** |

| Stock length | |
|---|---|
| 0.5 m | **too short by 260 mm** |
| **1.0 m** | **240 mm spare — 32 % slack** ✅ |
| 1.5 m | 98 % slack — 744 mm to hide |

At 2.6 mm OD it is exactly the **Ø2.6 raceway limit the chassis already publishes**, so it
uses the existing route rather than needing a new one.

**A latent bug this turned up:** the conduit's Y length answers **two** requirements — get a
plug *through* (20.40, set by the XH's 17.40 width) and reach *past* a mated plug's back
face (17.00). It was sized on the span alone, and only happened to be large enough because
the straight USB-C plug was longer than the XH is wide. Shortening a plug — exactly what the
right-angle does — would have quietly made the shaft too narrow to pass one. Now `max()` of
both.

⚠ **`PLUG_L` (USB-C 20.0, XHP-6 14.0) is an assumption.** Overmold *length* is not
specified by USB-IF — only the cross-section is — and it sets the shaft's Y extent. Measure
a real cable before this is final; everything else above is from a drawing or a spec.

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

### Two items that were closed, and are open again after the 2026-08-01 check

**MCU — package still right; price and stock both wrong.** The LQFP100
`STM32H743VIT6` brings out only **16** ADC channels; this board digitises **20**
(one per photodiode). The 144-pin **`STM32H743ZIT6`** has exactly 20, and 22 × 22
over its leads fits the 30 mm tail with 4.0 mm clear. That reasoning stands.

⚠ **The ~$7.63 does not.** Verified on LCSC 2026-08-01 (**C114408**): **$11.07
@1, $9.93 @10 — and 7 units in stock.** Ten boards need ten parts. So it is
$2.30 dearer than budgeted *and* not presently orderable at the project's
10-instrument convention. It also loses the "cheaper than the 100-pin part"
argument that justified stopping the search here. Re-check at quote time; if
stock has not recovered, the thing to attack is the **20-channel ADC
requirement**, since that is what forced 144 pins to begin with.

**Photodiode — `VEMD4110X01` (C3211080).** Si **PIN** photodiode (not a
phototransistor, so the linearity the audio path needs survives), 0805, 0.42 mm²
active area, ±55°, with a **daylight-blocking filter, 740–1040 nm**, matched to
830–950 nm emitters. **$0.58** at the 100+ break; ⚠ 72 in stock against 200 for a
run of ten. The X02 named in earlier revisions is not in LCSC's catalogue; the
X01 has the same filter and the same outline, so nothing about the design changes.

### The optical filtering — what it is and what it actually rejects

**There is no separate filter part on this board, and none is needed: the filter
is inside the detector package.** That is the better place for it — a bonded
window in the cover would be an extra part, an extra process, and would sit
3 mm from the sensor instead of on it.

The filter passes **740–1040 nm** and blocks the rest. The emitter is 940 nm,
comfortably inside. So everything the detector sees outside that band — which is
the whole visible spectrum — is gone before it becomes photocurrent.

**Why that matters more than it sounds.** The board's own LED-on/LED-off
subtraction already removes ambient *offset and flicker*. What it cannot remove
is **shot noise** (∝ √photocurrent, irreducible once the photons are converted)
and **saturation** — a detector pinned by sunlight has no headroom left for the
string signal, and subtracting two saturated readings gives zero, not signal.
The filter attacks both at the only point where they can be attacked: before
conversion.

**Ambient sources, ranked by how much trouble they actually cause:**

| Source | Gets through the filter? | Why |
|---|---|---|
| **Sunlight** | ⚠ **the real threat** | ~50 % of solar energy is IR and it is broadband — a large fraction lands inside 740–1040 nm |
| **Incandescent / halogen** | ⚠ **bad** | a ~2800 K blackbody peaks *in the near-IR*; these emit more 940 nm than visible |
| **Fluorescent** | ✅ **almost entirely blocked** | output is overwhelmingly visible phosphor emission plus mercury lines at 405/436/546/578 nm — all outside the passband. Only a weak mercury IR line near 1014 nm creeps in at the band edge |
| **White LED** | ✅ **blocked** | blue pump + phosphor; there is very little IR to pass |

So **modern indoor lighting is the easy case** and the filter handles it. Note
too that fluorescent flicker (100/120 Hz on magnetic ballasts, 20–60 kHz on
electronic ones) is the part that would otherwise be dangerous — the electronic
ballast rate lands squarely in a 48 kHz sampler's band and could alias — and
blocking the light removes the problem at the source rather than relying on
subtraction to catch it.

**Sun and halogen are what remain**, and there the design gets one piece of luck
it did not plan for: **940 nm sits in a water-vapour absorption band**, so solar
irradiance is genuinely depressed there relative to 850 nm. That is a standard
reason to choose 940 nm for IR sensing outdoors, and this design already picked
940 nm for other reasons.

**If the prototype still says sun is a problem**, the next step is a *narrow*
bandpass (940 ± 25 nm interference filter) rather than the broad 300 nm
daylight filter — that would be a bonded window in the cover slots, the part the
earlier revision of this file anticipated. Worth measuring before buying: a
gigging instrument mostly lives under stage and room lighting, which the table
above says is already covered.

**Still open** (project rule: NO consignment, all PCB parts LCSC-library):
- ~~a **ULPI PHY** in JLC's library~~ — **CLOSED 2026-08-01.** Microchip
  **`USB3343-CP`** is in LCSC stock at **$1.78** (C633347), QFN-24, exactly the
  envelope modelled. The `-TR` reel variant is C112967 at $2.07.
- ~~the **IR emitter's beam angle**~~ — **CLOSED, unfavourably.** ±20–30° at
  940 nm **is not made in 0805**. `IR17-21C/TR8` (C131250) is the chosen part at
  ~120°. See "the three blockers" above for why the cover cannot make this up.
- ~~**32 of the 35 part lines have no MPN**~~ — **CLOSED.** All 141 placed parts
  map to an orderable line, enforced at import by
  `optical_pickup._assert_every_part_orderable()`.
- ~~**quad op-amp** with low enough input bias current for a nanoamp TIA~~ —
  **CLOSED 2026-08-01. `TLV9064IDR`** (C388176), SOIC-14, 10 MHz GBW,
  **500 fA** input bias, RRIO CMOS, 10k in stock, **$0.2161**. Four orders of
  margin on bias against a tens-of-nA signal, in the package already modelled.
- ~~**J2**~~ — **CLOSED.** `S4B-XH-SM4-TB` (C161861), 4-way, already a project
  part. Board grew 5 mm; the model carries the real JST envelope.
- ⚠ **NEW, and the last thing before a quote: U8 cannot be an LDO** — see above.

**Prototype: the first measurement is now string 2, not `SENSE_D`.** Specifically
a **.014 plain string at 22 mm at a realistic drive current** — and now
necessarily with a **~120° emitter**, since that is what is available. The
earlier version of this note said "with a narrow-beam emitter"; that test cannot
be run with a stocked 0805 part, so the measurement will show the design at its
*worst* case for lever 1 rather than its best. Read the result accordingly: it
is a floor, not a representative figure.

**Cost (resolved 2026-08-01)**: **$26.66/board in parts**, computed by
`parts_cost()` from the table above. The MCU ($9.93) and the 20 photodiodes
($11.60 at the 100+ break) are 81 % of it; everything else together is $5.13.
Assembly follows the same per-*order* economics as the
tee/sensor panel ($25 setup + ~$1.50 per unique feeder), so it should ride the
**same JLCPCB panel** — the 0402 R/C and generic parts overlap with the existing
boards, and only the specialised lines add feeders.

### PCB cost basis — 10 instruments per order (PROJECT CONVENTION)

**Every PCB cost in this BOM is the cost to build 10, divided by 10.** One
JLCPCB order, use what each instrument needs, discard the extras. Other hardware
bought in packs (screws, inserts, dowels) keeps its **per-unit** price as
elsewhere in this file — pack overage is not amortised. PCBs are different because
their fixed costs are large and genuinely per-order.

**Why 10, and why the number matters.** JLCPCB's PCBA quantity ladder is **2, 5,
then multiples of 5** — you cannot order 3. So the per-instrument curve is a
**sawtooth, not a smooth decay**, and three instruments cost *more each* than two:

| Instruments | Order | Waste | Order total | Per instrument |
|--:|--:|--:|--:|--:|
| 1 | 2 | 1 | $155.38 | $155.38 |
| 2 | 2 | 0 | $155.38 | $77.69 |
| 3 | 5 | 2 | $264.70 | **$88.23** ↑ |
| 5 | 5 | 0 | $264.70 | $52.94 |
| 6 | 10 | 4 | $446.90 | **$74.48** ↑ |
| **10** | **10** | **0** | **$446.90** | **$44.69** |
| 15 | 15 | 0 | $629.10 | $41.94 |
| 20 | 20 | 0 | $811.30 | $40.57 |

*(Recomputed on the $82.50 fixed / $36.44 variable. The
**shape** is unchanged — it comes from the quantity ladder, not the rates — so
both conclusions below still hold; only the absolutes moved.)*

Two consequences worth acting on:

* **Build in ladder multiples.** 3 and 5 have the *same order total*; 6 and 10 do
  too. If you are planning 3, build 5 — the boards are already paid for.
* **10 is the knee.** It is the first quantity within 30 % of the variable-cost
  floor; past 15 the gains are slow. Hence the convention.

### Optical pickup board at that basis — $44.69 per instrument

Board is **37.4 × 171.6 mm = 64.2 cm²**, 4-layer, 148 parts, ~560 solder joints.
(Earlier revisions said 47.5 cm², which predates the +X wraps and the M4 bands,
then 184.4 mm long, which predates J2 becoming a 4-way.)

| | | |
|---|---|---:|
| **Fixed, per order** | PCBA setup $25 + feeder loading **$22.50** (15 Extended lines × $1.50; **5 of the 20 lines are Basic**) + component MOQ overage ~$20 + 4-layer fab tooling ~$15 | **$82.50** |
| **Variable, per board** | parts **$29.07** (computed, quantity-correct) + fab $6.42 (64.2 cm² × $0.10) + assembly $0.95 (~560 joints) | **$36.44** |
| **Order of 10** | 82.50 + 10 × 36.44 | **$446.90** |
| **Per instrument** | ÷ 10 | **$44.69** |

*(The magnetic-pickup channel and the single-ended cable exit together cost **$0.53 per
instrument**. The audio ADC and the 6-way connector add $0.78 of parts and one feeder, and
the board getting 8 mm shorter gives $0.30 of it back.)*

*(History: $46.72 → $59.32 → $52.72 → **$42.61**. The spike was the photodiodes
at their @1 price; the fall is resolution — detectors at the 100+ break, the
op-amps $2.90 under budget, the emitters $3.22 under, and a feeder estimate that
was **overstated by half** because it counted part *variety* before anyone
counted the actual lines. 5 of the 18 lines are Basic and carry no feeder charge
at all. The one thing that went the other way is J2's refit: +5 mm of board,
+$0.18/board of fab.)*

**Soft in this:** the fab terms ($15 tooling + $0.10/cm²) are estimates — worth a
JLC quote before trusting the absolutes, though the *shape* of the curve comes
purely from the quantity ladder and does not depend on them. Parts now use the
**@10 price** where verified ($9.93 MCU) and @1 where not ($0.9334 photodiode,
because LCSC showed no break at the quantity we need — and cannot supply it
anyway).

**Photodiodes alone are now $18.67 of the $41.60** — they have overtaken the MCU
as the most expensive thing on the board, which was not true when the design was
settled. Worth noting the sensitivity: the detector count is **two per string by
choice**, for the SUM/DIFF pair that defends against the 2f₀ octave error. That
choice now costs ~$9.30/board rather than ~$3.50. It is still the right call —
a confident octave-up error is worse than any price — but it is no longer a
rounding error, and a cheaper 0805 PIN diode is the highest-value substitution
on this board.

**Per-string audio remains about $9/board**: pitch-only would fit USB full-speed,
deleting the PHY and allowing a cheaper MCU.

**One free saving at layout:** the outline uses far less copper than its billed
bounding rectangle. Two boards nested head-to-tail on the panel should recover a
useful slice of the $6.90 fab line.

**Layer count is a PANEL decision — and ONE 4-LAYER PANEL WINS.** This board needs
4 layers (20 analog channels wanting a ground reference, a 96 kHz switching driver
to isolate from them, a 60 MHz ULPI bus). The tee and sensor boards do not. But
panelising everything at 4 layers is *cheaper* than splitting the orders:

| | Cost at 10 instruments |
|---|---:|
| Upgrade the 220 small boards (12 tee + 2 carrier + 8 sensor, ×10) to 4-layer | **$2 – $13** |
| Second order to keep them 2-layer ($25 PCBA setup + ~$8 duplicated feeders) | **~$33** |

So one panel saves roughly $20–30 across ten instruments — about $2–3 each, i.e.
marginal, but it also keeps the "one assembly job" simplicity. 4 layers costs a tee
board nothing but planes it does not need.

*This corrects an earlier note in this file that said splitting was cheaper.* That
used a $0.10/cm² fab rate, which is the PROTOTYPE regime; JLCPCB quotes 4-layer at
**$70.60/m²** at panel quantities, an order of magnitude lower, and at that rate
the fixed cost of a second order dominates. The conclusion inverted once the rate
was real rather than assumed.

**Measured, no longer an estimate:** the tee board is **22.0 × 24.0 = 5.28 cm²**
(`electronics.tee_pcb`), so 220 small boards ≈ **0.117 m²** — within 6 % of the
0.11 m² the table above assumes. The conclusion holds with margin; it would take
the small boards being roughly *double* their modelled size to make splitting
worthwhile.

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

## Cost summary (per instrument)

**One model only** — the basic/pro split is gone, every instrument is fully
populated. PCB lines use the 10-instruments-per-order basis above; everything
else is per-unit. Motors still dominate. **Prices below are approximate and
several are unverified — re-verify the whole file before ordering.**

| Group | Per instrument | Confidence |
|-------|---------------:|------------|
| Filament (printed) | ~$81 | estimate; **spool prices verified**, masses are model estimates |
| Mechanical hardware (motors, screws, bearings, belt, fasteners, dowels) | ~$620 | belt/collar/bearings **verified**; motor + all McMaster **[m]** |
| Wire | ~$35 | estimate, excludes 10 control drops |
| Electronics + UI (Teensy, audio shield, Pi 4, bucks, hub, jacks, joystick, OLED) | ~$190 | **all verified except the OLED [m]** |
| Optical pickup board (148 parts, 4-layer, ÷10 basis) | **~$45** | parts cost **computed from the model**; all 18 lines have real MPNs |
| Control sensors, 10 controls (MT6701 + magnet + board) | ~$50 | IC + magnet **verified**; boards not yet quoted |
| Tee / carrier PCBs | ~$25 | estimate |
| **Total** | **~$1,060** | |

**The total barely moved, and that is a coincidence worth spelling out.** The
optical board went **up** $6 net (photodiodes +$12, part selection −$6) and the
buck up $5; the bearings came **down** about $25 once the MR85ZZ was sourced at
$0.49 instead of $4.38. Those roughly cancel. Do not read the unchanged total as
"the estimate was fine" — six individual lines were wrong, two of them badly,
and the offsets were luck.

**The largest remaining uncertainty is still the motors**, at ~$350 of the
~$620 mechanical figure and **not verified** — see the drive-motor row. If the
MT bundle is not $35, this total moves more than everything found today combined.

Mechanical detail: 10× MKS SERVO42D CAN MT (~$350) is the bulk; +10× Tr5×1 screw/nut
(~$60, **confirm 1 mm lead / single-start**), 10× MR85ZZ (**~$5** at Trianglelab,
~$42 at Bearings Direct), 10× 693ZZ (**~$30**), 10× shaft collars (**$25**,
verified), Ø3 shaft (~$30), dowels (~$22), GT2 belt 6.5 m (**~$3.50–11**
verified at $0.54–1.73/m; the old "$12–130" range was wrong at both ends —
it appears to have conflated per-metre with per-spool), M-hardware packs (~$50).
Electronics detail: the Pi 4 + its buck replace the Pi 5 + 6 A buck (~$130 saved,
since audio→MIDI moved onto the optical board), and the 10-channel PCM1864 ADC
path is **deleted outright** for the same reason — the optical board digitises its
own twenty channels. Those two changes together take roughly **$160** off what
this section previously totalled.

## Cannot verify — needs a manual check [m]

Everything below was attempted on **2026-08-01** and could not be confirmed from
a fetchable listing. These are not "probably fine" — they are unchecked. Ranked
by how much money rides on each.

| # | Row | Why it could not be checked | What to do |
|--:|---|---|---|
| 1 | **Drive motor, SERVO42D CAN MT** — $350/instrument | Price sits behind a **variant dropdown**; all three vendors publish only a "from" price, which is the **MB (board-only)** floor. The ElectroPeak link in the row is the **wrong SKU** — driver only, $12.50, motor explicitly excluded | Add CAN MT to a cart at [P3D](https://p3d.mx/products/makerbase-mks-servo42d-nema17-foc-motor) or [makerbase3d](https://makerbase3d.com/product/servo42d-nema17-closed-loop-stepper-motor-driver-cnc-3d-printer-for-gen_l-foc-quiet-and-efficient/), record the real number, and **replace the ElectroPeak link** |
| 2 | **All eight McMaster rows** — dowels, cup-tip screws, heat-set inserts, mount screws, hold-down, shafts, guide rods, M2 grubs (~$50–70) | mcmaster.com serves **no product content** to automated fetches — every part URL returns the bare catalogue navigation. This is a site-wide block, not a bad URL | Open each part number in a browser. Part numbers themselves are stable and were previously correct |
| 3 | **Tr5×1 lead screw + nut** — ~$30 | The eBay listing **timed out**, and eBay item IDs rotate regardless. The manufacturer (ALM) publishes **no prices at all** — quote-only, "Inquire" button | Get a quote from ALM, or re-source on AliExpress and paste a fresh link |
| 4 | **2.42" OLED module** — ~$17 | Both Waveshare and RobotShop return **HTTP 403** to fetches | Check in a browser. A German reseller at €18.00 suggests ~$17 is close |
| 5 | **Ø3 g6/h6 precision shaft** — ~$30 | McMaster (see #2); also the row points at a **category page**, not a part | Pick an actual part number while you are there |

Two rows verified but flagged for **availability**, not price:

* **SN65HVD230DR** — $2.45 correct, but DigiKey stock is **0** (backorder only).
* **Tinmorry TPU 95A** — $22.99 correct, but **sold out**. Only ~40 g is needed,
  so any 95A spool substitutes.

Plus the two optical-board parts that cannot supply a run of ten — the
**STM32H743ZIT6** (7 in stock, need 10) and the **VEMD4110X01** (72, need 200).
Both are correctly specified now; only stock is short. Documented in full in the
optical pickup section.
