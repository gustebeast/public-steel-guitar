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
| `can_tee` | 0 | 9 | record declared 2026-10-04; rail stubs widened 1.2 -> 1.5 mm and re-routed 0 / 0 |
| `leg_pogo_female_bottom` | 3 | 22 | not started |
| `leg_pogo_female_top` | 3 | 22 | not started |
| `leg_pogo_male_bottom` | 3 | 22 | not started |
| `leg_pogo_male_top` | 3 | 22 | not started |
| `ui_board` | 5 | 22 | not started |
| `pi_cap` | 8 | 21 | not started |
| `lever_sensor` | 10 | 36 | not started |
| `led_strip` | 11 | 35 | not started |
| `motor_ctrl` | 26 | 39 | not started |
| `optical` | 40 | 41 | not started |
| `output_panel` | 42 | 42 | not started |

**NEXT:** the shared evidence that closes the same five rules on every board, once:
M29 (read the fab's capability page and compare with the rules loaded in the `.kicad_pro`),
M12 / M42 (run `elec/lcsc_check.py`, stock and lifecycle today), M30 (assembly tier and
extended-part count from the fab BOM), M37 (run `elec/fab.py` on a board and look at the
gerbers layer by layer). Then `can_tee` M31 (the solder jumper JP1 has no silk saying
what it is for: add "TERM"), then the four pogo boards, then upward by size.

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
