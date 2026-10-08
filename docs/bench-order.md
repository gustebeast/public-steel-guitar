# Bench order: one motor, one string

The string-physics test bench is a subset of the instrument's own boards, wired with the
instrument's own leads. Nothing here is a bench-only design.

## Boards

| Board | Generator | Quality pass (2026-10-06) | What it does on the bench |
|---|---|---|---|
| `output_panel` | `elec/output_panel.py` | 0 FAIL | 24 V inlet and power switch, USB hub, magnetic pickup input, audio out |
| `motor_ctrl` | `elec/motor_ctrl.py` | 0 FAIL | head of the motor bus (bus A), 5 V for the Pi |
| `can_tee` | `elec/can_tee.py` | 0 FAIL | trunk-to-motor junction; one, and it is the last tee |
| `pi_cap` | `elec/pi_cap.py` | 0 FAIL | carries the Pi's 5 V in; its UI ribbon and lighting outputs stay empty |
| `optical` | `elec/optical.py` | 0 FAIL | the optical pickup |
| Raspberry Pi 4 | bought | - | host |
| MKS SERVO42D, CAN | bought | - | the one motor |

Every board is 0 unconnected, 0 violations. What stays OPEN on each is the fab's own
manufacturability report on the uploaded files and the four order-day checks (order form,
assembly tier, files sent are the files checked, stock on the day), plus the motor-current
figure on `motor_ctrl`, `output_panel` and `can_tee`. `docs/pcb-quality-status.md` has the
table.

**Not on the bench, and what that leaves open:**

* No UI board. The power button's two throws are therefore open, and the output panel is
  built to read that as ON: the bench is live whenever the supply is plugged in.
* No lever or pedal sensors. Bus B (`motor_ctrl` J2 / J6) is empty and unterminated; its
  error counter reading "no acknowledge" is correct.
* No lighting. `pi_cap` J3 / J6 and `motor_ctrl` J7 -> `pi_cap` J4 can be left out.

## What the boards cost (quoted 2026-10-06, nothing ordered)

Two assembled of each, which is the least the fab assembles; five bare boards of each,
which is the least it makes. The other three of each five are taken to come bare (the
form prices paste and placement for two; it does not say).

| Board | Tier | 5 bare / 2 assembled |
|---|---|--:|
| `can_tee` | Economic | 23.69 |
| `pi_cap` | Economic | 48.44 |
| `motor_ctrl` | Economic | 105.82 |
| `output_panel` | Standard | 195.85 |
| `optical` | Standard | 256.45 |
| **boards, before shipping** | | **630.25** |

At five assembled the same five were 910.63. Of the 630.25, 406.15 is charged per design
whatever the quantity (setup, stencil, the per-part-type fees, the optical board's
engineering and colour charges): one assembled of each, were it offered, would save little.
`docs/jlcpcb-order-walk.md` has every line. The bench uses one `can_tee`; an instrument
takes ten, which is a later order.

## Leads

Way order is `elec/harness.py`; every JST lead is crimped 1:1, way n to way n. XH carries
24 V, PH carries 5 V.

| Lead | From | To | Ways |
|---|---|---|---|
| Supply | Mean Well GST160A24-R7B | `output_panel` J6 | the supply's own plug. Meter J6 before first power |
| Power link | `output_panel` J10, XH 6 | `motor_ctrl` J3, XH 6 | 24 V, GND, SW_UP, SW_DN, GND, 24 V |
| Optical power | `output_panel` J9, XH 2 | `optical` J2, XH 4 housing | 24 V, GND on ways 1 and 2; ways 3 and 4 of the 4-way housing empty |
| Pi 5 V | `motor_ctrl` J5, PH 6 | `pi_cap` J2, PH 6 | 5 V, GND, -, -, GND, 5 V |
| Bus A trunk | `motor_ctrl` J1, XH 4 | `can_tee` J1, XH 8, ways 1-4 | 24 V, GND, CAN_H, CAN_L. Ways 5-8 of the 8-way housing empty |
| Motor drop | `can_tee` J2, XH 4 | the motor's screw terminals | see below |
| Motor board USB | `motor_ctrl` J4, PH 4 | a Pi USB-A host port | VBUS (not connected at the board), GND, D-, D+ |
| Hub upstream | `output_panel` J3, USB-C | a Pi USB-A host port | stock A-to-C lead |
| Pi gadget port | `output_panel` J2, USB-C | the Pi's USB-C | stock C-to-C lead, about 1 m on the bench. ⚠ In the instrument the Pi's USB-C faces the -Y rail about 4.5 mm away: no plug goes in there as the Pi is placed today (open design item) |
| Optical USB | `output_panel` J4, USB-C | `optical` J1, USB-C | [Amazon B0FKYR7V34](https://www.amazon.com/dp/B0FKYR7V34), $9.99: **0.3 m, USB 2.0, the same up/down-angle plug at both ends** (user, 2026-10-07). The optical end's limits are overmould 12 mm deep at most, 22 mm at most from the plug's axis to the cable; this one is 5.2 and about 14 (seller's photo). On the bench any C-to-C lead does; the angle is for the endplate |
| Pickup | magnetic pickup | `output_panel` J8 | two screw terminals, hot and ground, marked on the silk |

### The motor drop

The SERVO42D has no single plug. Makerbase's schematic (*MKS SERVO42D_CAN V1.0_003
Schematic.pdf*, in its GitHub repository under Hardware) and its CAN manual (V1.0.9,
section 1.4) show two terminal blocks on opposite edges of the driver board: a 6-way with
power on it and a 5-way, "COMM", with CAN on it. The drop is four wires from one XHP-4
housing, and it is **split and crossed**: two wires go to one block and two to the other,
and on both blocks the pair is in the opposite order to the tee's.

| `can_tee` J2 way | Wire | Motor block | Its terminal, by the schematic | Silk label |
|---|---|---|---|---|
| 1 GND | black | 6-way | 2 | GND |
| 2 +24 V | red | 6-way | 1 | V+ |
| 3 CAN_H | yellow | 5-way COMM | 2 | CAN H |
| 4 CAN_L | green | 5-way COMM | 1 | CAN L |

Left empty on the motor: the 6-way's COM, EN, STP and DIR (3 to 6), and the 5-way's IN1,
GND and 5V (3 to 5). **The 5-way's 5V is an output of the motor: nothing goes on it.**

A straight four-wire lead into either block is wrong whichever block it is: into the
6-way it puts ground on V+ and 24 V on GND. Go by the labels printed on the motor's board
and check each wire against them before the first power-up; the terminal numbers above
are the schematic's and have not been read off a unit in hand, and whether the blocks take
bare wire or a plug has not either (`can_tee` item M1 is open for exactly this). The manual
asks for the host's ground and the motor's ground to be common, which this lead does
through the 6-way's GND, and for the CAN pair to be twisted.

### What closes bus A

A CAN bus wants 120 ohm at each end: 60 ohm between CAN_H and CAN_L with the power off.

| End | Terminator | How it is switched in |
|---|---|---|
| `motor_ctrl` | R5 | always in: wired straight across the pair |
| the last tee | R1 | SW1, a slide switch marked TERM; it ships OFF |
| the motor | its own 120 ohm | a push-on jumper beside the CAN terminals (manual section 1.1: "JUMPER ON = CAN 120") |

`motor_ctrl` terminates its end with nothing to do. For the far end: slide SW1 to **ON**
on the last tee of the trunk (on the bench, the only tee) with a toothpick or a small
screwdriver, and leave it OFF on every other tee. The body prints ON at the end that
closes it. Leave every motor's own jumper OFF.

Do not use both the tee's switch and a motor's jumper: three terminators load the pair
to 40 ohm. The meter reads 60 ohm between CAN_H and CAN_L with the power off when it is
right, 120 with the switch still OFF.

## Stock on the day (read 2026-10-06, JLCPCB parts API)

"Instruments" is stock divided by the count one full instrument needs. A bench order is
a few boards of each design, far inside every row.

| Part | LCSC | Board | Per instrument | In stock | Instruments |
|---|---|---|--:|--:|--:|
| KPJX-4S-S, 24 V inlet jack | C2875467 | `output_panel` | 1 | 39 | 39 |
| G6K-2F-Y-DC5, signal relay | C326376 | `output_panel` | 1 | 54 | 54 |
| TLV320ADC3140, audio converter | C1852021 | `optical` | 5 | 304 | 60 |
| LMR33630BRNXR, 1.4 MHz buck | C2071384 | `optical` 1, LED supplies 3 | 4 | 260 | 65 |
| MCP4261-103E/ST, digital pot | C185580 | `output_panel` | 1 | 96 | 96 |
| LTE-C9901, IR emitter | C2683614 | `optical` | 10 | 1,717 | 171 |
| CH32V307WCU6, MCU | C5142795 | `motor_ctrl`, `output_panel` | 2 | 413 | 206 |
| PD15-22B, photodiode | C161211 | `optical` | 20 | 6,818 | 340 |
| PNR3015-150M, 15 uH | C19634062 | `motor_ctrl`, `output_panel` | 2 | 906 | 453 |
| STM32H743IIT6, MCU | C89597 | `optical` | 1 | 2,073 | 2,073 |

The photodiode is the PD15-22B. The VEMD4110X01 it replaced (95 in stock) is on no board.

Across the whole instrument, boards outside the bench included, the scarcest part is the
fret boards' side-mount spring contact (YZF0002-38080-02, C5203987: 16 an instrument, 594
in stock, 37 instruments). Nothing limits a ten-instrument order.

LCSC sells the lead housings and contacts in minimum lots (read 2026-10-07): XHP-2 and
PHR-4 in 50s, XHP-6, XHP-8 and PHR-6 in 20s, XHP-4-M in 10s, crimp contacts in 100s.

JLCPCB does not hold stock for an order that has not been placed. The five parts under
100 instruments are the ones to look at again on the day; `tools/lcsc_prices.py` re-reads
all of them.

## Tools

| Tool | For | Notes |
|---|---|---|
| WCH-LinkE | flashing and debugging `motor_ctrl` and `output_panel` (CH32V307) | the only probe that talks to CH32V parts. SWD pads TP1-TP5 on each board, labelled |
| ST-Link (V2 or V3) | flashing and debugging `optical` (STM32H743) | SWD pads TP1 SWDIO, TP2 SWCLK, TP3 NRST, TP4 GND, TP5 3V3. The board can also be loaded with no probe over I2C2 (TP6 / TP7) with TP8 held high |
| Arm GNU Toolchain 14.2.rel1 (`arm-none-eabi-gcc`) | building the `optical` firmware (Cortex-M7) | Arm's own zip from developer.arm.com, checked against its published SHA-256; unpacked under `C:/Users/gus/tools`, not on PATH. The CH32V307 boards need WCH's RISC-V toolchain instead, not installed |
| Spring-pin probe clip or hook leads | reaching the SWD pads | the pads are bare 1.5 mm lands, not a header |
| USB-CAN adapter, `candump`-class | watching bus A from outside | H and L share the motor's CAN terminals, ground to the motor's GND |
| Bench supply, 24 V, adjustable current limit | first power of each board at about 100 mA | `INSTALL_NOTES.md`, board bring-up step 1 |
| Multimeter | rails, the 60 ohm bus check, J6's polarity before first power | |
| Thermocouple or thermal camera | `optical` U13, U8; `motor_ctrl` U5 | `docs/optical-bringup-diagnostics.md`, first power-up table |

Order of work is in `INSTALL_NOTES.md` (board bring-up) and
`docs/optical-bringup-diagnostics.md`: one board at a time on the current-limited supply,
then `motor_ctrl` alone, then the motor, then the output panel, then the optical board.
