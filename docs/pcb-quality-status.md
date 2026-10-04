# PCB quality pass: where each board stands

The standard is `cadkit/PCB_QUALITY.md` (rules A1–A11 automated, M1–M42 manual). Run it with

```bash
"C:/Program Files/KiCad/10.0/bin/python.exe" elec/quality.py elec/out/<board>
```

`elec/finish.py` runs it on every route and ends its last line `| quality: N FAIL, M OPEN`.
A board may be ordered only at `0 FAIL, 0 OPEN`. **No board is there yet**; the scoreboard
below is current, the sections after it are the history of how the rules arrived.

## THE LOOP: scoreboard and what is next (updated every tick)

A 15-minute loop is working every board to `0 FAIL, 0 OPEN`. Rules of the road: a hard
finding is fixed, never waived; a soft one is waived only for a case on its rule's
"Break it when" list; a sign-off is written only after the thing was actually read.

| board | FAIL | OPEN | state |
|---|--:|--:|---|
| `can_tee` | 0 | 7 | open: M1 (user), M33 (user), M36, and the order-time four M12 M30 M37 M42 |
| `leg_pogo_female_top` | 3 | 22 | not started; test-pad and pinout labels have no site even at 0.8 mm |
| `leg_pogo_male_top` | 3 | 22 | not started; same |
| `leg_pogo_female_bottom` | 4 | 22 | not started; name only fits at 0.8 mm; CAD plate has a hole the routed board lacks |
| `leg_pogo_male_bottom` | 4 | 22 | not started; name only fits at 0.8 mm |
| `ui_board` | 7 | 22 | brenner is changing it (power button, 2x8 header): leave until that merges |
| `pi_cap` | 10 | 21 | waits on brenner's ribbon change (J5 becomes 2x8); ring and via findings go with the re-route |
| `lever_sensor` | 11 | 36 | not started; J1 pinout legend only fits at 0.8 mm: make room |
| `led_strip` | 11 | 35 | not started; CAD and fab data disagree (pre-existing) |
| `motor_ctrl` | 27 | 39 | not started; J1 pinout legend at 0.8 mm |
| `optical` | 40 | 41 | not started |
| `output_panel` | 43 | 42 | not started; power-button inlet switch to design (see bronner-work-items) |

All twelve were re-finished with `--keep-route` on 2026-10-04: every one still reads
`0 unconnected, 0 violation(s)`; silk is 1.0 mm wherever a site exists.

**NEXT:** (1) the four pogo boards: declare power_paths and pinouts (pogo pin C5280862
datasheet), find room for the test-pad names and pinouts or decide what replaces them,
and look at the female-bottom cutout disagreement. (2) `can_tee` M36 (what limits a short
on a motor drop: read the PSU's protection from BOM.md) and the order-time four -- run
`elec/fab.py` on `can_tee` and see what the package step already proves for M12 / M30 /
M37 / M42. (3) `lever_sensor`. (4) `output_panel` power-button design (lead's request)
together with its quality record, since the board is re-routed for it anyway; `pi_cap`
when brenner's `harness.UI_RIBBON` change is on main. (5) `motor_ctrl`, `led_strip`,
`optical`. (6) the XH power-lead way count (user: fine if it creates no other issue and
stays in the XH family): try 2-way / 6-way inside the current outlines.

cadkit changes this loop has made (all propagated): A12 fab check `efdd75f`;
`finish.py --keep-route` `bc45fad`; jumper / `silk_labels` labels `fff67d7`; small-label
fallback `3a67ff7`; automatic annular-ring growth in the layout `ea916d4`.

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

### Needs the user (cannot be signed from files on hand)

* **Two pinouts share the 4-way XH housing (M1, every board with an XH).** Pattern A is
  `GND +24V CAN_H CAN_L` (tee drop, motor_ctrl J1/J2), pattern B is `GND +24V +24V GND`
  (panel J7/J9/J10, motor_ctrl J3, optical J2). The plugs are interchangeable, and a
  power lead in a CAN socket puts 24 V on CAN_H (SN65HVD230 bus pin: 16 V). Open in
  `BOM.md` since 2026-09-18 with three options. M1 stays OPEN on those boards until one
  is chosen; the loop's working recommendation is option (a), a different way count for
  the power-only leads, and it will take that if nothing else is said by the time the
  other items are closed.
* **Motor current (M33, `can_tee`, `motor_ctrl`, `output_panel`).** The trunk contact is
  3 A; the budget case is 2.7 A, and that rests on 0.8 A per moving motor (derived, never
  measured) and a firmware cap on simultaneous movers (not written). Needs one
  measurement of a SERVO42D's supply current while slewing.

### What the loop has changed

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
