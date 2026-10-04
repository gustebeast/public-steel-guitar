# PCB quality pass: where each board stands

The standard is `cadkit/PCB_QUALITY.md` (rules A1–A8 automated, M1–M32 manual). Run it with

```bash
"C:/Program Files/KiCad/10.0/bin/python.exe" elec/quality.py elec/out/<board>
```

`elec/finish.py` runs it on every route and ends its last line `| quality: N FAIL, M OPEN`.
A board may be ordered only at `0 FAIL, 0 OPEN`. **No board is there yet** — the pass is
new (2026-10-04) and no board has declared its `BOARD_NOTES["quality"]` record.

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

## What each board still needs

1. Declare `power_paths` (entry pad, load pads, amps) for every rail; fix what A1 then
   measures.
2. Fix or waive the A2 list above (move / add capacitors, regenerate, re-route).
3. Read every multi-pin part's pinout against its datasheet and cite it (`pinouts`).
4. Work the manual list M1–M32 and sign each with what was checked against.

The optical board goes first: it is the next order.
