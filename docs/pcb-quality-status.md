# PCB quality pass: where each board stands

The standard is `cadkit/PCB_QUALITY.md` (rules A1–A11 automated, M1–M42 manual). Run it with

```bash
"C:/Program Files/KiCad/10.0/bin/python.exe" elec/quality.py elec/out/<board>
```

`elec/finish.py` runs it on every route and ends its last line `| quality: N FAIL, M OPEN`.
A board may be ordered only at `0 FAIL, 0 OPEN`. **No board is there yet**: what is left on each is listed
below, and the sections after the scoreboard are the history of how the rules arrived.

## THE LOOP: scoreboard and what is next (updated every tick)

A 15-minute loop is working every board to `0 FAIL, 0 OPEN`. Rules of the road: a hard
finding is fixed, never waived; a soft one is waived only for a case on its rule's
"Break it when" list; a sign-off is written only after the thing was actually read.

Scoreboard, 2026-10-04 (every board listed is `0 unconnected, 0 violation(s)`):

| board | FAIL | OPEN | what is still open |
|---|--:|--:|---|
| `can_tee` | 0 | 7 | M1 (user: the XH pinout decision), M33 / M36 (user: motor current), order-time M12 M30 M37 M42 |
| `leg_pogo_*` (four boards) | 0 | 4 | order-time M12 M30 M37 M42 |
| `pi_cap` | 0 | 7 | M1 (which end of the UI ribbon is way 1: against brenner's `ui_board`), M11 (CAD fit after the build), M29, order-time four |
| `lever_sensor` | 0 | 7 | M11, M35, M29, order-time four |
| `motor_ctrl` | 0 | 10 | M32 / M33 (user: motor current), M23 (USB details), M11, M35, M29, order-time four |
| `output_panel` | 0 | 10 | M3 / M21 (user: grounding, below), M32 (user: motor current), M11, M35, M29, order-time four |
| `optical` | - | - | being re-placed and re-routed: see "Optical" below |
| `ui_board`, `fret_led`, `foot_led` | - | - | brenner's boards, not touched by this loop |

"Order-time" items (M12 the order form, M30 the assembly order, M37 the files sent are the
files checked, M42 stock on the day) can only be signed when an order is being placed. M29
(buildable by this fab) is signed from the fab's own DFM report on the uploaded files. M11
needs the lead's build with the new board geometry. M35 needs each MCU's errata sheet read.
None of these can be closed from the files on hand, so the loop leaves them OPEN on purpose
rather than ticking them.

### Needs the user

1. **Where the instrument's grounds meet (`output_panel` M3 / M21).** The panel keeps `GND`
   (audio, MCU, USB) and `PWR_GND` (the 24 V return) apart and never joins them. Its own
   5 V buck returns to `PWR_GND`, so the current the board's logic draws (up to 257 mA)
   has no way home on the board: it leaves through whichever cable ground reaches a board
   that does join the two (the optical lead, or a USB shield to the Pi, which is bonded to
   the trunk return at `motor_ctrl`). Three consequences: on the bench, with only the
   power inlet plugged in, the board is dead; the audio reference carries the logic
   supply's return current down a signal cable; and the USB link to the Pi already closes
   a loop that lets stepper return current share the audio ground, which is what the split
   was meant to prevent. The choices are (a) one tie on the panel (a 0 ohm link or a bead
   at the buck's output capacitor), making the panel the star point and accepting that the
   USB shield path then parallels the trunk return; (b) an isolated 5 V supply for the
   audio side; (c) keep the split and move the audio reference's bond to the optical board
   only, with the Pi's USB link isolated. (a) is the small change and the loop's
   recommendation; it is not made because it is a decision about the whole instrument.
2. **Motor supply current while slewing** (`motor_ctrl` M32 / M33, `output_panel` M32,
   `can_tee` M33 / M36). Every trunk figure rests on 0.8 A per moving SERVO42D, derived and
   never measured, and on a firmware cap on simultaneous movers that is not written. One
   bench measurement closes all five items.
3. **Two pinouts share the 4-way XH housing** (`can_tee` M1): CAN drops are
   `GND +24V CAN_H CAN_L`, power leads are `GND +24V +24V GND`, and the plugs interchange;
   a power lead in a CAN socket puts 24 V on CAN_H. `motor_ctrl` now carries three
   different 4-way XH sockets. Open in `BOM.md` since 2026-09-18; the recommendation is a
   different way count for the power-only leads.

### What changed on the boards this loop (all routed 0 / 0)

* **`output_panel`**
  * The audio ADC's data came in on a pin with no I2S receiver (PB14 is SPI2_MISO only on
    the CH32V307; the part has two standard I2S blocks and no full-duplex extension). It
    is now on I2S3 (PA15 / PB3 / PB5) as a slave receiver clocked from I2S2's pins.
    Firmware: I2S2 master transmit, I2S3 slave receive, same word clock.
  * The 24 V to 5 V buck was strung out over 15-36 mm; it is now one cell: input capacitors
    0.6 and 1.7 mm from VIN, catch diode 0.8 mm from SW, output capacitor 1.15 mm from the
    inductor, feedback sensed at the output capacitor.
  * A bypass capacitor at every power connector, pin-exact decoupling on the MCU and hub,
    hub crystal capacitors corrected, the power-button switch (a soft-start P-FET in the inlet that
    fails on; 2.55 mA with the instrument off), TS5A3159 in place of SN74LVC1G3157.
* **`lever_sensor`**: MCU and sensor decoupling at the pins, a 2R2 + 100 nF input filter
  ahead of the LDO, SWD pads in a labelled row, crystal changed to a stocked 8 MHz part
  with the right load capacitors, bus ESD diodes with a real part number.
* **`motor_ctrl`**, **`pi_cap`**: power-button pass-through on the existing cables, bus B
  5 V behind a current-limited switch, decoupling and crystal moved to the pins.
* **`leg_pogo_*`**: rails widened to the contact rating, copper cleared from under the M4
  head, short board names on silk.

### Optical

Found by the pass and being fixed in one re-placement (the board was `0 / 0` before it and
has to get back there):

* Sixteen of the STM32H743's supply pins had no capacitor within 5 mm (the decoupling ring
  was evenly spaced on two sides only). Now one 100 nF per VDD pair on all four sides,
  six capacitors added, VDDA / VREF+ capacitors at pins 38 / 39.
* The MCU crystal was 35 mm from its pins through 3-4 vias; it is now 2 mm away. It was
  also a 20 pF part, at or past the H7's start-up limit (gm_crit 1.37-1.85 mA/V against a
  guaranteed 1.5); now a 10 pF, 30 ohm part (0.50 mA/V worst case).
* The PHY crystal's ESR was 30 ohm only in the distributor's listing; its maker's sheet
  says 40, and the PHY's limit is 30. Replaced by a part whose own sheet says 30.
* U11 (the reference buffer all twenty channels share) had no supply bypass; one added.
  The VBUS clamp's capacitor moved to its rail pin; VCAP1's capacitor moved from 8 mm to
  2.6 mm from its pin.
* All fourteen pinouts read against the makers' documents and cited; supply paths declared.

## Earlier ticks (history)

### New in A12 this tick: vias in pads, and copper under a screw head

* **A via hole inside a soldered SMD pad now fails** (cadkit `c6013c5`): the barrel takes
  the paste. Excepted by arithmetic: exposed pads, pads with no paste (test pads), lands
  of 4 mm2 or more. Found on `lever_sensor` (3), `optical` (8), `output_panel` (7),
  `motor_ctrl` (2) -- mostly crystal ground pads, where the layout's own ground-stitch
  rule put them; that rule now uses the same area test, so they move off the pad at each
  board's next route. `close_last` can still close a net with a via in a pad (it did on
  `leg_pogo_female_top`): to fix in cadkit.
* **Copper under a screw head** (cadkit `d3ff0c5`, cutout `head_d`): the female pogo
  boards had tracks and a via up to 0.8 mm inside the M4 head's circle on the face it
  bears on. Kept out now, re-routed 0 / 0. EVERY board with a screw through it needs the
  same look (M11): `can_tee`'s ear is bare (checked); the others are to do.

### Findings from the pogo boards, 2026-10-04

* **Bus B's 5 V is not current-limited.** `src/leg_pogo.py` and the wiring notes say bus B
  runs "behind a current-limited switch"; `elec/motor_ctrl.py` ties J2 / J6 way 2 straight
  to the Pi's `+5V` rail, behind only the 4 A output fuse. The leg joints expose that rail
  on gold lands whenever a leg is off, through 1 A contacts. To fix on `motor_ctrl`: a
  current-limited load switch on the bus-B feed (about 0.5 A: eleven boards at ~30 mA is
  0.33 A). Until then M33 / M36 stay open on the pogo boards.
* The female boards' 0.30 mm rails measured a hair under what 1 A (the contact rating)
  needs; now 0.35 mm, re-routed 0 / 0, contact order re-proved on all four.
* `leg_pogo_female_top` had been routed before its M4 hole was cut (the CAD check said
  so); the re-route fixed it. All four now pass the CAD check.
* No room for test-pad names or pin legends on a 10-13 mm board: each carries a short
  name (`POGO FEM BOT r1`, 1.0 mm or larger) and a `G` at the ground pad; recorded as a
  marking decision (M31) with what is relied on instead.

cadkit changes this loop has made (all propagated): A12 fab check `efdd75f`;
`finish.py --keep-route` `bc45fad`; jumper / `silk_labels` labels `fff67d7`; small-label
fallback `3a67ff7`; automatic annular-ring growth in the layout `ea916d4`; short silk name,
squarer name blocks and legible footprint text `7195078`.

### New automated rule, 2026-10-04: A12, the board measured against the fab's page

The fab's capability page was read (JLCPCB, standard service) and compared with the rules
loaded in the boards. The rule file was looser than the fab in five places, so the pass
now measures the finished board instead of trusting it (cadkit `efdd75f`). First run:

* **silk text was 0.8 mm on every board; the fab's legible minimum is 1.0 mm.** Fixed in
  cadkit (`kicad_silk` and the layout's designators). `finish.py --keep-route` (cadkit
  `bc45fad`) re-does everything after the route without placing or routing, so the hard
  routes are not disturbed.
* **`ui_board` J2 and `pi_cap` J5 (1.27 mm 2x7 header): annular ring 0.175 mm, the fab's
  absolute minimum on two layers is 0.18** (14 pads each). Hard.
* **`pi_cap`: a via 0.296 mm from the hole of J5.8; the fab wants 0.45 between a pad hole
  and any other hole.** Hard.
* `lever_sensor`: 20 vias drilled under 0.30 mm, which the fab charges for (a note: the
  order form has to say so).

### What the loop changed first

* `can_tee`: the pass measured the 1.2 mm stubs from the 2 mm rail bar to each connector
  pad as a choke point at the 3 A contact rating (1.37 mm needed at a 10 C rise, and the
  stub is 3.5 mm long, so it is not a short neck). Widened to 1.5 mm, 0.90 mm to the
  neighbouring pads; re-routed `0 unconnected, 0 violation(s)`.
* `can_tee` pinouts read against JST eXH.pdf p.5 (side-entry drawing): No. 1 circuit and
  KiCad pad 1 are the same post. Covers every other board's S4B / S8B-XH-A.

## First run, 2026-10-04 (nothing declared yet)

| board | A1 supply paths | A2 bypass caps | A3 pairs | A4 pinouts | manual OPEN |
|---|---|---|---|---|---|
| `can_tee` | 1 | 2 | 0 | 2 | 12 |
| `lever_sensor` | 2 | 2 | 0 | 6 | 12 |
| `motor_ctrl` | 7 | 10 | 1 | 7 | 12 |
| `optical` | 5 | 19 | 0 | 14 | 12 |
| `output_panel` | 3 | 20 | 0 | 17 | 12 |
| `pi_cap` | 3 | 4 | 0 | 5 | 12 |
| `ui_board` | 1 | 1 | 0 | 3 | 12 |

How to read it:

* **A1** counts are all "this rail declares no `power_paths`". They are bookkeeping until
  each rail's entry, loads and amps are written down; only then does the choke-point and
  voltage-drop measurement run. Trial declarations showed the measurement works: `can_tee`
  +24 V is a 1.20 mm track where 3 A needs 1.37 mm (10 °C rise, 1 oz).
* **A4** counts are all "no pinout citation": one per distinct multi-pin part. Each needs
  its pinout read against the maker's document and the page cited. This is the mirrored-
  pinout guard and it is real work, not paperwork.
* **A2** is where the pass found things DRC never could. These are measured distances on
  the routed boards:

### A2 findings worth acting on before an order

* **`optical` U6 (STM32H743, LQFP-176)** — twelve `+3V3D` supply pins, bypass capacitors
  within 5 mm of none of them; six pins are 10–16 mm from the nearest (pins 62, 72, 82,
  127, 136, 159). The analog pins 38/39 (`+3V3A`, VDDA/VREF+) are 17 mm from theirs. A
  176-pin MCU wants a capacitor at each supply pin pair.
* **`optical` U7 (USB PHY)** pins 16 and 22 at 5.0 / 6.2 mm; **U10** (VBUS ESD) at 6.8 mm.
* **`output_panel` U1 (CH32V307, QFN-68)** — nine `+3V3` pins, nearest capacitor 5.4–10.5 mm.
* **`output_panel` +24 V connectors J6, J9, J10** are 39–54 mm from the only +24 V
  capacitor; **J4 (USB-C, +5 V)** is 46 mm from one. Power leaving the board down a cable
  with no local charge.
* **`motor_ctrl`** — `+5V` has no capacitor to ground at all on the net that feeds J2, J5
  and J6; U4 (CH32V307) pins 31/32 at 10.5 mm; U5.6 (`VCC5`) at 9.7 mm; J3 (+24 V) 28 mm.
* **`motor_ctrl` USB_DP / USB_DM** are in no `match` group (A3).
* **`pi_cap`** — `+3V3_PI` has no capacitor anywhere (J1 and the J5 ribbon); `+5V_PI` at J1
  is 38 mm from one.
* Passive pass-through boards (`can_tee`, the leg pogo boards) fail A2 because a tee has
  no capacitor. That is a waiver with a reason, or a decision to add one per tee.

## Second batch of rules, same day (A5-A8, M13-M32)

Added from a survey of published design-review checklists. On our boards A5 (net labels),
A7 (I2C pull-ups) and A8 (exposed pads) pass everywhere. One new finding:

* **`output_panel` J2 (USB-C)** - both CC pins are unconnected (A6). If J2 is a
  downstream port that a USB-C device plugs into with a C-to-C cable, it needs a pull-up
  on each CC pin to advertise itself as a source; if it only ever takes an A-to-C cable
  from a host, it needs 5.1 k to ground on each. Decide which, then fix or waive.

The manual list is now M1-M32 (32 OPEN per board). M13 onward are per-circuit-kind and
most boards sign several in one line as not applicable.

## Third batch (A9, M33-M38)

From sources read through the browser (an open review checklist, a first-board guide, TI
notes in full). One new automated rule, and it found something:

* **`optical` Y1** - the crystal is **35 mm** from the STM32's oscillator pins (U6.29/30);
  the rule's limit is 10 mm. A trace that long is stray load capacitance and a pickup,
  and this clock sets the audio sample rate and USB timing. Move Y1 and its load
  capacitors up against U6 before the order.
* **`motor_ctrl` Y1** - 12.2 mm to U4.6: marginal, tighten it when the board is next placed.

## Fourth batch (A10, A11, M39-M42; A9 extended)

From a community review FAQ (schematic, layout and bill-of-materials pages).

* **Crystal traces change layer** (A9 now fails a via on a crystal net): `optical`
  OSC_IN 3 vias, OSC_OUT 4, PHY_XO 2; `output_panel` OSC_IN/OSC_OUT 2 each; `motor_ctrl`
  OSC_IN 3; `lever_sensor` OSC_OUT 2. With the crystal beside its pins these go away.
* **`optical` J1 VBUS** has 0.1 uF directly on it (a note, not a failure: common guidance
  is 1-10 uF on a USB device's VBUS; over 10 uF is the hard limit).
* A11 (one value, one spelling) passes on every board.

## Review pass on the rules themselves (same day)

The rules were checked against how these boards are actually made, and four were changed:

* A1's voltage-drop limit is 2 % of the rail (was a flat 50 mV, meaningless on 24 V).
* A2 no longer fails a rail that only passes between connectors (`can_tee`, `pi_cap`,
  the pogo boards): reported as a note.
* A9 reports a via on a crystal net as a note instead of failing it; the distance limit
  still fails (`optical` Y1 at 35 mm, `motor_ctrl` Y1 at 12 mm).
* Manual rules about a kind of circuit are marked `n/a` by the script when the board has
  none of its parts: `can_tee` and `ui_board` drop to 22 open items, `pi_cap` 21,
  `lever_sensor` 36, `optical` 41.

## What each board still needs

1. Declare `power_paths` (entry pad, load pads, amps) for every rail; fix what A1 then
   measures.
2. Fix or waive the A2 list above (move / add capacitors, regenerate, re-route).
3. Read every multi-pin part's pinout against its datasheet and cite it (`pinouts`).
4. Work the manual list M1–M42 and sign each with what was checked against.

The optical board goes first: it is the next order.
