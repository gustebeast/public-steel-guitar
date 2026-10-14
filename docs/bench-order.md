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
| `output_panel` | Standard when quoted; **Economic since 2026-10-08** (relay ordered as C47190: 26.75 less in the cart) | 195.85 |
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
| Bus A trunk | `motor_ctrl` J1, XH 4 | `can_tee` J1, XH 8, ways 1-4 | 24 V, GND, CAN_H, CAN_L. Ways 5, 6 and 7 of the 8-way housing take the USB-CAN adapter's three tails (Tools); way 8 empty |
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
housing, and it is **split, and half of it is crossed**: two wires go to one block and two
to the other. The power pair lands in the tee's order (way 1 to terminal 1); the CAN pair
lands in the opposite order.

| `can_tee` J2 way | Wire | Motor block | Its terminal, by the schematic | Silk label |
|---|---|---|---|---|
| 1 +24 V | red | 6-way | 1 | V+ |
| 2 GND | black | 6-way | 2 | GND |
| 3 CAN_H | yellow | 5-way COMM | 2 | CAN H |
| 4 CAN_L | green | 5-way COMM | 1 | CAN L |

Left empty on the motor: the 6-way's COM, EN, STP and DIR (3 to 6), and the 5-way's IN1,
GND and 5V (3 to 5). **The 5-way's 5V is an output of the motor: nothing goes on it.**

A straight four-wire lead into either block is wrong whichever block it is: into the
6-way it puts the CAN pair on COM and EN, and into the 5-way it puts 24 V on CAN L. (Until
2026-10-07 the tee's way 1 was ground and this table had the power pair crossed. A lead
made to the old table puts 24 V backwards into the motor: meter the four ferrules against
the XHP-4 before first power.) Go by the labels printed on the motor's board
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
| the motor | its own 120 ohm | a push-on jumper beside the CAN terminals (the figure in manual section 1.4: "JUMPER ON = CAN 120") |

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
| KPJX-4S-S, 24 V inlet jack (no other listing or maker in the catalogue: it mates the supply's own plug) | C2875467 | `output_panel` | 1 | 19 (2026-10-08) | 19 |
| G6K-2F-Y-DC5, signal relay, the tape-and-reel listing (the tube listing C326376 fell to 44) | C47190 | `output_panel` | 1 | 64,883 (2026-10-08) | - |
| TLV320ADC3140, audio converter | C1852021 | `optical` | 5 | 304 | 60 |
| LMR33630BRNXR, 1.4 MHz buck | C2071384 | `optical` 1, LED supplies 3 | 4 | 260 | 65 |
| AD8402ARZ10, digital pot (replaced the MCP4261-103E/ST, which stood at 96 with no thicker listing) | C578716 | `output_panel` | 1 | 2,460 (2026-10-08) | - |
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
| WCH-LinkE (MuseLab, Tindie: kit 2, the probe + four 20 cm leads + a USB-C cable; $5.00, 950 in stock 2026-10-12) | flashing and debugging `motor_ctrl` and `output_panel` (CH32V307); later, the eleven `lever_sensor` boards (CH32V203, through their jig) | the only probe that talks to CH32V parts, **in its RISC-V mode**. Four wires, always including reset. **Its header is a 2x5 with no pin numbers.** As the listing's picture names it, one end to the other: front row `U_RX, U_TX, GND, 3V3, RST`; back row `SWCLK, GND, SWDIO, 3V3, 5V`. WCH's own manual shows the layout only as a figure: **read the silkscreen of the probe that arrives before the first wire.** Its 3V3 and 5V pins are power OUTPUTS and take no lead. WCH's manual: lines to the target at most 30 cm. It is also the day-one console: SDI printf over the same two debug wires |
| ST-LINK/V2 (genuine, DigiKey), 20-pin 2.54 mm header | flashing and debugging `optical` (STM32H743) | Five leads, by ST's own table (UM1075 rev 8, table 4): **pin 1 VAPP** to TP5 (3V3; a sense INPUT, it powers nothing), **pin 7 SWDIO** to TP1, **pin 9 SWCLK** to TP2, **pin 15 NRST** to TP3 (always wired: connect-under-reset is the way back), **pin 8 GND** to TP4 (any of 4, 6, 8, 10, 12, 14, 16, 18, 20 is ground; 8 sits between the two signals). Before the first flash, watch TP3 go low on a tool-commanded reset. The board can also be loaded with no probe over I2C2 (TP6 / TP7) with TP8 held high |
| 13 jumper leads, 2.54 mm female, one end cut off and soldered to a pad: one 20-pack of 150 mm female/female, cut to suit (Adafruit 1950, $1.95, in stock; or DigiKey 1568-12796-ND, SparkFun PRT-12796, 28 AWG, $3.17, 1,290 in stock; both read 2026-10-12) | every lead between a board and a probe | **The count:** 4 on `motor_ctrl` (TP1 SWDIO, TP2 SWCLK, TP3 NRST, TP4 GND), 4 on `output_panel` (the same four), 5 on `optical` (TP1 SWDIO, TP2 SWCLK, TP3 NRST, TP4 GND, TP5 3V3). The 20-pack leaves seven, four of which are for the lever jig later. The LinkE kit's own four leads are female/female and go spare. Each tail's female end goes straight onto its probe pin, so there is no adapter and no second joint. Solder the tails once and leave them on; keep every one under 30 cm. The pads are bare 1.5 mm lands: no clip holds on any of them, and a wire only stays on one soldered |
| USB leads to the Pi: USB-A to USB-C (in the LinkE kit), USB-A to mini-B (for the ST-LINK/V2; whether one is in its box is not confirmed), and the instrument's own three (USB-A to PHR-4 for `motor_ctrl` J4, USB-A to USB-C for `output_panel` J3, USB-C to USB-C for `optical` J1 to the panel's J4) | the probes into the Pi, and each board's own USB once it has firmware | "The Pi as the flashing host", below |
| WCH-LinkUtility 3.1 (WCH, Windows) or `wlink` (open source, native Windows driver) | flashing the CH32V boards through the LinkE | WCH lists CH32V20x and CH32V30x for the utility; `wlink` names the LinkE as its recommended probe and lists CH32V203 and CH32V307 as tested. Neither is installed yet |
| STM32CubeProgrammer (ST; Windows, Linux, macOS) | flashing `optical` through the ST-LINK/V2 | not installed yet |
| Arm GNU Toolchain 14.2.rel1 (`arm-none-eabi-gcc`) | building the `optical` firmware (Cortex-M7) | Arm's own zip from developer.arm.com, checked against its published SHA-256; unpacked under `C:/Users/gus/tools`, not on PATH. **The CH32V boards (307 and 203) need WCH's RISC-V toolchain instead, and it is still NOT installed**: nothing can be built for them until it is |
| OPTIONAL: four AA alkaline cells in a holder, leads into an XHP-4 (way 1 +, way 2 -) | the optical board's 6 V start | the one bench-only lead. Alkaline only. "Power without a bench supply", below |
| OPTIONAL: bench pigtail, XHP-4, way 1 red (24 V), way 2 black (GND), ways 3 and 4 EMPTY | powering each 24 V board alone from a bench supply | only with the optional bench supply: `motor_ctrl` J1, `output_panel` J7, `optical` J2. Meter its polarity before it meets a board. A crimp in way 3 or 4 would put 24 V on a CAN pin |
| 10 ohm 5 W resistor on a PHR-6 (ways 1 and 2) | loading the Pi's 5 V before the Pi sees it | `motor_ctrl` J5, 0.5 A |
| USB-CAN adapter, `candump`-class | watching bus A from outside | **three tails crimped into ways 5 (CAN_L), 6 (CAN_H) and 7 (GND) of the bench trunk's XHP-8, way 8 EMPTY** (way 8 is 24 V). Not clipped to a motor's screw terminals: a slip there lands on V+. The adapter's own 120 ohm is ON only when the adapter is the far end of the bus (no tee switched in) |
| OPTIONAL, SAFER: bench supply, 0 to 24 V, adjustable current limit | first power of each board, staged, with a fault held to a reading | not needed: the boards are powered down the instrument's own chain (below). With one, the staged limits in `docs/board-bringup-diagnostics.md`, "First power, staged", and the optical board's 6 V start still apply as written |
| Multimeter | rails, the 60 ohm bus check, the brick's plug before first power, and every power-off check that stands in for a current limit | |
| Thermocouple or thermal camera | `optical` U13, U8; `motor_ctrl` U5 | `docs/optical-bringup-diagnostics.md`, first power-up table |

**Every conductor in this table is drawn**, pad to pin, in a viewer tab of its own: `py -3.12 -m tools.flash_bench_view` (`src/flash_bench.py`; it prints the list). A lead that is not in that picture is not in the plan.

Order of work is below ("Power without a bench supply"); what each reading means is in
`INSTALL_NOTES.md` (board bring-up), `docs/board-bringup-diagnostics.md` and
`docs/optical-bringup-diagnostics.md`.

## The Pi as the flashing host (user, 2026-10-13)

**The instrument's own Raspberry Pi 4 does the flashing**, bare on the bench: no cap on its
header, no 5 V lead from `motor_ctrl`, **powered by its own USB-C supply** (the rule above
about no USB-C supply applies once the 5 V lead is in; here it is not). Both probes plug
into its USB-A ports. `py -3.12 -m tools.flash_bench_view` draws every lead.

| Board | First flash, from the Pi | Its own USB path to the Pi | Can a BLANK chip be reached over that USB? |
|---|---|---|---|
| `motor_ctrl` (CH32V307) | **WCH-LinkE**; four soldered tails (TP1 to TP4) | **J4** (PHR-4) to a Pi USB-A port: the instrument's own lead | **yes by WCH's manual, not yet tried.** BOOT0 (pad TP6) at 3V3 through a power-up, then `wchisp`: "Flashing the CH32V307 boards without the LinkE", below |
| `output_panel` (CH32V307) | **WCH-LinkE**; four soldered tails | **J3** (USB-C) to a Pi USB-A port: the hub's upstream, the MCU behind the hub | **probably, not yet tried.** BOOT0 has no pad: tweezers from R7 pad 1 to R6 pad 2 through a power-up, and the loader has to come up through the hub (same section) |
| `optical` (STM32H743) | **ST-LINK/V2** in a Pi USB-A port; five soldered tails (TP1 to TP5) | **J1** (USB-C) to the panel's **J4**, through the hub and J3 | **no.** ST's ROM loader speaks USB only on the full-speed port (PA11/PA12), which this board does not wire; its high-speed port has no loader |

So for a blank `optical` board the probe is the only way in; the two CH32V307 boards have
WCH's ROM loader as a second way, written up below. The USB leads are in
the picture because they are how each board TALKS to the Pi once it has firmware (the
day-one check that a flash worked), and how it would take an update if its first
firmware carries a loader of its own. Nothing here changes a revision 1 board.

**Software on the Pi (set up 2026-10-13).** The bench Pi is `psg-pi` (Raspberry Pi OS
Lite 64-bit, Debian 13, image of 2026-10-06; a Pi 4 Model B Rev 1.5 that reports 2 GB),
on Wi-Fi, reached by `ssh gus@psg-pi.local` with a key: no password login. Installed from
the distribution's own packages: `openocd` 0.12 (it has `stm32h7x.cfg`, `stlink.cfg` and
the Pi's own `raspberrypi-swd.cfg`), `stlink-tools`, `dfu-util`, `can-utils`, `git`.
None of it has been run against a board yet.
Kept current (user, 2026-10-13): every package is at the distribution's latest (kernel
6.18.50), and Rust is the current stable from `rustup` (1.99.0), not Debian's 1.85.
**`wlink` 0.1.2, its newest release, is on it, built there from source** (`~/src/wlink`
at tag v0.1.2, installed as `/usr/local/bin/wlink`): its releases carry no Linux build
for 64-bit ARM. Its README lists the CH32V203 and CH32V307 with the WCH-LinkE. A udev
rule lets the `gus` user reach the probe without sudo. **It starts and lists its commands; it has NOT talked to a probe or a chip
yet**: that is the first thing to check when the LinkE arrives (`wlink list`, then
`wlink status` on a board). If it fails there, the CH32V boards are flashed from a
Windows PC with the same probe and leads (`wlink` for Windows, or WCH-LinkUtility).

**Not drawn, because not tried: no probe at all for the optical board.** `openocd` can
bit-bang SWD from a Pi 4's own header pins, and that is a real, documented way to flash an
STM32. It would replace the ST-LINK/V2 with three more jumper leads from the Pi's header
to TP1, TP2 and TP4. The ST-LINK is already on the order and is the path in the picture.
For the CH32V parts' two-wire debug the nearest thing is `swindle` on an RP2040 (next
section); the WCH-LinkE stays.

## Flashing the CH32V307 boards without the LinkE (2026-10-13)

Every WCH-LinkE source is one to four weeks out. The LinkE **stays on the order**: it is
the debugger, the day-one console and the fallback. This is how to get firmware onto the
two boards before it arrives. No board changes.

**Confirmed, from primary sources**
- **WCH's ROM loader answers on USB at PA11 / PA12 or PB6 / PB7, and on serial at PA9 /
  PA10.** WCH's "CH32V3xx Evaluation Board Reference" V1.9, page 13, under "WCHISPTool
  Download" (the copy in `~/src/ch32v307/EVT/PUB` on the Pi). Its steps: BOOT0 to VCC and
  BOOT1 to ground, connect, download, BOOT0 back to ground.
  `motor_ctrl`'s J4 is PA11 / PA12; `output_panel`'s MCU is PB6 / PB7 behind the hub.
  BOOT1 is held low on both boards.
- **`wchisp` 0.3.0 is on the Pi**, built there from source (`~/src/wchisp`, installed as
  `/usr/local/bin/wchisp`), with a udev rule so `gus` needs no sudo. Its README lists
  CH32V307 VCT6 and RCT6 as tested. It looks for a USB device `4348:55e0` or `1a86:55e0`.
  It has not talked to a chip yet.

**Only claimed, to be found out on the bench**
- That the WCU6 (QFN-68) package behaves as the VCT6 that `wchisp` and WCH's board use.
  Same family and the same manual; nobody's list names the WCU6.
- That the loader keeps running once BOOT0 is let go (boot pins are normally read
  only at a reset; WCH's sentence for it was not found), so the reset `wchisp` issues after writing starts
  the new firmware. If it does not, leave the link on to write, then take it off and
  power-cycle.
- That the loader's USB on PB6 / PB7 comes up **through the CH334F hub**. A USB 2.0 hub
  passes a full-speed or a high-speed device alike, and the hub is how this board's own
  firmware reaches the Pi, so there is no reason it should not; no source says anyone
  has done it. WCH's board has an 8 MHz crystal, as both of ours do.
- That a second `wchisp` command works without a power-cycle. `wchisp` issue 22 (open)
  reports time-outs on repeat runs under Linux on this chip: the first command after the
  loader starts is the reliable one. So go straight to `flash`.
- **Write the `.bin`, never the `.elf`.** `wchisp` issue 28: an ELF with a segment in RAM
  made an older `wchisp` erase past the end of flash and take the ROM loader with it (on
  a CH32V203; put back only with a WCH-Link). `make isp` writes the `.bin`.

**The route to try first: `motor_ctrl` from the Pi over J4.** Nothing to buy.
1. Solder one jumper tail to **TP6** (BOOT0, marked B0) and one to **TP5** (3V3), 25 mm
   apart. Join their female ends with a header pin or a cut resistor leg. (Two of the
   seven spare leads. TP5's "no probe wire" rule is about a probe's 3V3 output; this is
   not one.)
2. J4 to a Pi USB-A port with the instrument's own USB-A to PHR-4 lead. J4 carries no
   power: the board needs its 24 V on J1, down the same chain as any other first power
   ("Power without a bench supply"), with its staged checks done first.
3. Power the board with the link joined. On the Pi, `lsusb` shows `4348:55e0` (or
   `1a86:55e0`). If it does not, the lead or the loader is at fault and nothing has been
   written: stop there.
4. **Pull the link apart** (both tails stay on the board), then
   `cd ~/psg/firmware/motor_ctrl && make isp`. It erases, writes, verifies and resets.
5. `lsusb` now shows the firmware's own serial port, and `/dev/ttyACM0` answers `?`.
6. To flash again: join the link, power-cycle, pull it apart, `make isp`.

**`output_panel`, the same way, no soldering.** BOOT0 has no pad: R7 pad 1 is BOOT0 and R6
pad 2 is 3V3, 3.5 mm apart beside the crystal, both 0402 lands (about 0.5 x 0.6 mm).
Hold tweezers across the two **while the board's 24 V is switched on**, then let go.
J3 to a Pi USB-A port; `lsusb` shows the hub and, behind it, `4348:55e0`. A soldered link
instead would be 4 mm of 30 AWG wire across those two lands, on for the power-up and
then cut: finer work than the tweezers and no better. There is no bench firmware for
this board yet, so for now this only proves the loader answers through the hub
(`wchisp info`).

**A different probe: `swindle` on an RP2040.** Real and maintained
(`github.com/mean00/swindle`, a Black Magic Probe derivative, GPL-3.0, commits dated
2026-10-13). Its README names WCH's two-wire debug on CH32V3xx, has a `ch32v307` preset,
and its author's demonstration is an RP2040-Zero debugging a CH32V307 board. A Raspberry
Pi Pico is stocked everywhere in the US. Wiring per its wiki: SWDIO GPIO13, SWCLK GPIO12,
reset GPIO10; it is driven from `gdb` (`mon rvswdp_scan`, `attach 1`, `load`), at no more
than 1000 kHz for these chips. **Against it:** its releases page is empty, so the
firmware has to be built from source (CMake, ARM GCC, Rust), which has not been tried;
its author says the two-wire protocol is not fully reverse-engineered and calls his
version good enough; it would be one more unproven thing between us and the chip. It is
the second choice, worth the evening only if the ROM loader fails on `motor_ctrl`.
`minichlink` / `ch32fun` need a WCH-Link for this chip.

## The bench test's software (user, 2026-10-13)

What the bench is for: does the motor, belt, pulley and leadscrew change a string's tension
quickly, accurately and reliably. The software to find out is in two places.

**`firmware/motor_ctrl`** is the motor controller's bench firmware: a USB serial port that
sends CAN frames at a time on the board's own microsecond clock and reports every received
frame with its time. It knows nothing about the motors (its line protocol is at the top of
`main.c`). Built on the Pi with Debian's RISC-V GCC against WCH's library, which is not in
this repository: `make` in that folder, with `~/src/ch32v307` a checkout of
`github.com/openwch/ch32v307`; `make flash` writes it through the WCH-LinkE. **It compiles
and links (11 kB); it has not run on a board.**

**`bench/psgbench`** is the test side, in Python, run on the Pi (`cd bench; python3 -m
pytest`):
- `link.py`: the CAN bus through the motor controller's USB, or through a USB-CAN adapter.
  Either way a test gets frames and send times on one clock.
- `servo.py`: the SERVO42D's commands, checked against Makerbase's CAN manual V1.0.5 (its
  example frames are tests). Not yet against a motor; the motors' firmware version is
  unknown. Commands over the bus need the motor in an SR_ work mode (`set_mode`).
- `optical.py`: the optical board's sample stream, and the lock-in that turns each
  photodiode's 48 kHz carrier into its signal at 48 kHz, on the same clock as the motors.
- `run.py`: a test is a list of timed moves ("at 0.3 s, motor 1, +4096 counts at 600 rpm");
  it runs them, polls every motor's encoder throughout, and returns it all.
- `pitch.py`: pitch against time from a recording of one string, and for one tension change
  the delay, the settling time, the overshoot and the size of the change in cents.
- `sim.py`: a pretend motor and string. The seven tests in `tests/` pass against them and
  against made-up converter samples. That proves the plumbing and nothing about the mechanism.

**`firmware/optical`** is the optical board's bench firmware: two USB serial ports, one for
commands and one carrying the converters' samples untouched (192 kHz, whichever of the five
converters are asked for), each block stamped with its sample count. No demodulation and no
pitch detection on the board: that is all done afterwards on the Pi. Built on the Pi with
Debian's ARM GCC against TinyUSB and ST's HAL (`~/src/tinyusb`, not in this repository);
`make flash` writes it with `openocd` through the ST-LINK. Start-up reports each step on
TP12 (115200 baud). **It compiles and links (31 kB); it has not run on a board.** The
converter registers were read off TI's datasheet; the frame format between the converters
and the MCU is the likeliest thing to need its `F` command on the bench.

**The tests** are `bench/psgbench/scenarios.py`, run one at a time:

    python3 -m psgbench.bench <scenario> --motor 1 --string 3 --counts 400 --limit 2000         --link motor:/dev/ttyACM0 --optical /dev/ttyACM1,/dev/ttyACM2 --out runs/

| scenario | what it does | what it answers |
|---|---|---|
| `hold` | nothing, for 10 s | how steady the pitch reading is by itself |
| `step` | one step up, one back | delay, settling time, overshoot, does it come back |
| `sizes` | steps of 1/4 to 4 times the base, each up and back | cents per count; are small moves as true as large |
| `speeds` | the same step at 300 to 3000 rpm | what speed buys |
| `accels` | the same step at five acceleration settings | what the motor's 0..255 means |
| `approach` | one place from below and from above, five times | lost motion |
| `repeat` | fifty steps up and back | drift, and faults that happen only sometimes |
| `rapid` | up-and-back pairs 300 ms down to 10 ms apart | how closely moves can follow each other |
| `retarget` | a new place commanded 5, 15, 40 ms into a move | the lever that changes its mind |

Each prints one row per move (how late the command left, the motor's own travel time, encoder
error, and from the string: cents moved, delay, settling time, overshoot) and totals: cents
per 1000 counts, how far the rest pitch wandered, lost motion, worst encoder error. Listening
to a string other than the moved motor's (`--motor 2 --string 1`) is the cross-talk test.
`--sim` runs any of them on the pretend motor and string. `--out` keeps the raw recording so
a run can be measured again without being run again.

**`--limit` is required on hardware**: the furthest, in encoder counts, the run may send the
motor from where it stands. A run that would pass it is refused before anything moves. The
base step (`--counts`) is a guess until `sizes` has said what a count is worth on that
string: start small. After every run the motor's encoder is compared with where it began,
and it is sent back if it is off (`rapid` and `retarget` can leave it so).

Nothing judges pass or fail yet: the first real runs have to say what good looks like.
Until the optical board streams, `--wav` takes a recording made some other way.

## Power without a bench supply (user, 2026-10-13)

**The plan now: the instrument's own brick powers the output panel, and every other board
is powered from the board before it, through the lead the instrument uses there.** No
bench supply, no pigtail, no 5 V source. `py -3.12 -m tools.flash_bench_view` draws it.

| Lead (make these FIRST: nothing can be flashed without them) | From | To | Ways |
|---|---|---|---|
| the brick's own plug | Mean Well GST160A24-R7B | `output_panel` **J6** | fixed |
| optical feed | `output_panel` **J9** (XHP-2) | `optical` **J2** (XHP-4) | 1 = 24 V, 2 = GND; ways 3 and 4 of the XHP-4 EMPTY |
| power link | `output_panel` **J10** (XHP-6) | `motor_ctrl` **J3** (XHP-6) | 24 V, GND, button, button, GND, 24 V |

All three are the instrument's leads (`INSTALL_NOTES.md`, the cable table), made to their
real lengths, so nothing here is bought or made for the bench alone.

**What is being accepted.** A bench supply turns a fault into a reading: at a 100 mA limit
a solder bridge or a reversed part is a number on a display and nothing gets hot. The brick
holds 6.67 A (160 W) into whatever is wrong, for as long as it is plugged in. What stands
between a fault and that current:

| Board | What limits a fault on first power from the brick |
|---|---|
| `output_panel` | **nothing.** Its 24 V rail is the brick's, through Q2 |
| `motor_ctrl` | F1 (1.5 A) ahead of the 5 V converter only. The 24 V trunk on it, and whatever else hangs off that, has nothing |
| `optical` | the panel's F1, 1 A: a chip fuse, soldered. It blows; it does not reset. **And it does not help the one fault that matters here** (below): 24 V on the 5 V rail draws well under 1 A while it destroys the board |

So the two boards that meet the brick first have no protection. **That is accepted (user,
2026-10-13): there are five of each board, and a board lost on first power is a spare
used.** A bench supply stays the safer way and is still listed, as optional.

**TWO CHECKS ARE REQUIRED, because five spares do not cover a mistake that repeats on every
board:**

1. **Meter the brick's plug before it ever goes into J6** (step 0 below). The pin positions
   were read off drawings, never off the part, and no board has reverse protection: a plug
   that is the other way round kills the panel, and then the next panel, and the next.
2. **Check every crimped lead, end to end, against `elec/harness.py` before it carries
   power**: way n at one end is way n at the other, way 1 is the rail, and no way is
   shorted to its neighbour. One lead feeds every board of its kind, so a lead with 24 V
   and ground crossed takes all five. The three leads are in the table above.

**Everything else below is OPTIONAL**: the power-off "not a short" readings, the in-circuit
resistor checks, and both battery steps. Each saves a board from one fault on that board;
skip them and the cost of that fault is one spare. Adding one board at a time is still
the recommended order, because it says which board a fault is on.

**There is no power switch on the bench.** The button is on the UI board, and with nothing
on J10's ways 3 and 4 the panel's switch (Q2) reads "not off" and turns ON, soft-started,
whenever the brick is in. Off means the brick's mains plug out. Every lead is plugged and
unplugged with it out, and after pulling it meter J7 way 1 to see the 24 V gone
before touching a lead (there is no bleeder on that rail; the converters drain it).

### The order, one board added at a time (recommended)

**What "not a short" reads (OPTIONAL).** Ohms range, either polarity, read once the number has
stopped moving (every capacitor on these rails is ceramic, tens of microfarads at most: a
second, not a minute). **CALCULATED from the resistors on each rail, not measured:** the
"at most" column is the resistor paths alone, and the chips on the rail can only pull the
reading lower. Write the first board's readings beside these.

| Board | Between | At most (resistors alone) | Stop if steady under |
|---|---|---|---|
| `output_panel` | J6 24 V lands to ground lands (ahead of the switch) | megohms: R33 + R34 end in a 10 V zener the meter cannot turn on | 1 k |
| `output_panel` | J7 way 1 to way 2 (24 V behind the switch) | megohms: only converter inputs and the TVS | 1 k |
| `output_panel` | +5 V to GND | 60 k (R11 + R12 118 k, R17 + R18 200 k, R39 + R40 250 k) | 50 ohm |
| `output_panel` | +3V3 (TP5) to GND | not calculable: the MCU, hub and codecs | 50 ohm |
| `optical` | J2 way 1 to way 2 | megohms, through R44's 2 ohm | 1 k |
| `optical` | +5 V (TP10) to GND | 125 k (R40 + R41) | 50 ohm |
| `optical` | +3V3 (TP5, TP11) to GND | not calculable: the MCU, PHY and converters | 50 ohm |
| `motor_ctrl` | J3 way 1 to way 2 (24 V) | 63 k (R12 + R13 147 k, R20 + R21 110 k) | 1 k |
| `motor_ctrl` | J5 outer posts (5 V) to GND | 17 k (R18 + R19 20 k, R10 + R11 125 k) | 50 ohm |
| `motor_ctrl` | +3V3 (TP5) to GND | 130 k (R1 + R2), less with the MCU | 50 ohm |

A reading far ABOVE the "at most" figure is a fault too: the resistor path it was
calculated from is open (on `motor_ctrl`'s 24 V that is the 5 V converter's enable divider
or the sense divider).

Each step: power off, the meter checks (optional, but for step 0), then power, then the
readings, then flash, then power off again before the next lead goes in. Rail readings are the ones in
`docs/board-bringup-diagnostics.md` ("First power, staged") and
`docs/optical-bringup-diagnostics.md`; they are not repeated here.

**0. The brick, alone. REQUIRED.** Plug it into the wall with nothing on its lead and meter the plug:
looking into the plug's pins with the flat/key as the panel's jack takes it, 24 V must
appear between the pair that lands on J6's +24V_IN lands and the pair that lands on
PWR_GND, **the right way round**, and the shell must be 0 V. The panel has no reverse
protection. (`elec/output_panel.py` at J6 gives the pin positions; they were read off
drawings, never off the part.)

**1. `output_panel`, nothing plugged into it.** Power off, meter:
- J7 way 1 to way 2 (the 24 V rail behind the switch): not a short (table above).
- J6's two 24 V lands to its two ground lands: the same.
- +5 V to GND and +3V3 to GND (TP5): not a short.
- Diode range, red on GND, black on the 24 V rail: one diode drop or more (the TVS and the
  buck's own diodes), not 0.00.
Then the brick in. Rails; the hub enumerates on a PC through J3; the direct path plays;
solder its four tails and flash it. **Any smell, any part too hot to keep a finger on:
brick out.** After a fast off-and-on, wait 2 s (the gain pot's reset).

**2. `optical`.** Power off, on the bare board, meter:
- R44 is on the board (the 2512 in series with J2; without it no rail comes up).
- **R40 and R41, in circuit.** These set the 5 V rail, and R40 open is the fault that puts
  24 V on it. Across R41 (FB to GND): 24.9 k or a little under. Across R40 (the 5 V rail
  to FB): under 100 k (the rest of the rail is in parallel with it through R41). If either
  reads open or far over its value, stop. Look at both under a glass: a tombstoned 0402
  stands on one end. **This checks the resistors, not U13's own FB joint, which sits under
  the part.** A dry FB pad passes this check and still follows its input.
- J2 way 1 to way 2, +5 V (TP10) to GND, +3V3 (TP5, TP11) to GND: not a short.
- The 6 V start, on four AA cells (optional; next section).
Then the optical feed from J9 to J2, brick in. TP9 24 V, **TP10 at once: 4.9 to 5.1 V, or
brick out.** Then the rest of its table, its five tails, flash.

**3. `motor_ctrl`.** Power off, meter: 120 ohm across J1 ways 3 and 4, +3V3 to GND and
J5's outer posts (5 V) to GND not a short, J3 way 1 to way 2 not a short. Nothing on J5,
J2, J6, J4 or J7. (Optionally the 3V3-only step on a 9 V battery, next section.) Then the
power link from J10 to J3, brick in: TP5 3.31 V, **5.02 V on J5's outer posts before
anything is plugged into J5, J2 or J6.** The 10 ohm load on J5 as before. Its four tails,
flash.

**4. Then the rest as before:** bus A with the tee and no motor, one motor, the Pi.

### The two low-voltage steps, on batteries (OPTIONAL)

**`optical`: four ALKALINE AA cells in a holder, into J2 (way 1 +, way 2 -).** This is the
one fault with no fuse behind it; skipping the step risks one optical board. It holds:
- U13 (LMR33630) runs from 3.8 V. Four fresh alkaline cells are 6.4 V open and about 5.8 V
  at the 0.15 to 0.3 A an erased board takes; R44 drops another 0.3 to 0.6 V.
- If U13 is NOT regulating, the 5 V rail gets at most the cells' voltage: 6.4 V. The parts
  on that rail are rated 6.0 V and survive 6.5 V (U8, U9). **Alkaline only:** four lithium
  primaries are 7.2 V and four NiMH are too low to tell anything.
- **Read it as a difference, not as a number.** Meter the buck's own input (R44's far pad,
  or C160) and TP10. Regulating: input 5.4 V or more, TP10 4.9 to 5.1. Following: TP10
  within 0.15 V of the input, whatever the input is. If the input is under 5.4 V the cells
  are tired and the reading means nothing: fresh cells.
- The holder's two leads go into an XHP-4 (ways 1 and 2), which is the one bench-only lead
  left; or onto J2's posts with two clip leads, way 1 being 24 V/+.
The board must not be flashed or run on the cells; this is a ten-second reading.

**`motor_ctrl`: a 9 V battery into J3 or J1 (way 1 +, way 2 -), optional.** It holds: the
3V3 converter (LMR16006) starts at 4 V and takes 10 to 25 mA; the 5 V converter stays off
below 17.6 V; a 9 V battery cannot deliver more than an amp or two into a short. What it
buys is small: with nothing plugged into J5, J2 or J6, a wrong 5 V rail can only hurt the
board's own bus B switch (U6) and the 5 V converter. Do it if a battery snap is to hand;
the 5 V reading in step 3, before anything is plugged in, does the same job at 24 V.

## Later: the lever sensor boards (user, 2026-10-13)

**Not part of the first flash and not on its shopping list.** The `lever_sensor` board has
not been ordered; it is worked on once the first prototype is validated. Nothing below is
bought, printed or made until then. It is kept here so it is not lost.

| Tool | For | Notes |
|---|---|---|
| Lever jig: two prints, four pogo pins (Adafruit 2430, pack of 10, $4.95), one M4 x 10 button screw and one M4 brass insert from the instrument's own stock | flashing the eleven `lever_sensor` boards | `tools/lever_prog_jig.step` + `tools/lever_prog_jig_base.step` (`src/lever_jig.py`). **No glue:** each pin stands on the base plate and is held by its own soldered lead, nipped under the ear by the screw. The pin's figures are Adafruit's published ones (body 1 mm, head 0.7 mm, 16 mm long, 13 mm compressed); **measure the pins and one jumper lead's insulation on arrival, before printing** (`POGO_L`, `LEAD_OD`) |
| The bus B drop from `motor_ctrl` J6 (the instrument's own lead, PHR-4 to PHR-8 ways 1 to 4) | powering a `lever_sensor` board in the jig | 5 V from `motor_ctrl`'s bus B switch, limited to 0.52 A. Not a bench lead: "Power without a bench supply", below |
| 4 jumper leads, 2.54 mm female, one end cut off | the jig's four pins to the WCH-LinkE | from the same 20-pack as the first flash's thirteen; each is soldered to a pin's foot, once |

| Lead | From | To | Ways |
|---|---|---|---|
| one bus B drop | `motor_ctrl` **J6** (PHR-4) | `lever_sensor` **J1** ways 1 to 4 (PHR-8) | 5 V, GND, CAN_H, CAN_L |

The bus B drop is the J6 lead to the first lever (LKL), the instrument's own; it reaches
the jig through its end window.

**Flashing them:** the WCH-LinkE in a Pi USB-A port, four leads soldered to the feet of
the jig's pogo pins. The board has no USB of its own, so the probe is the only way in.

**Power, and why this is the well-protected step:** from `motor_ctrl` J6 through the bus B
drop, with `motor_ctrl` already flashed and powered down the chain: 5 V through its bus B
switch (TPS2553), a 0.52 A constant-current limit. The drop may be plugged into a lever
board with the power on (the switch limits the inrush and a short alike); seat the board in
the jig first, then plug J1. The lead also carries CAN_H and CAN_L to the board: that is
harmless before either end has firmware, and once both have it the lever board is simply
on the bus it belongs to.

**Before it is ordered:** it is the natural first board to make operational over USB alone
(`docs/lever-sensor-respin.md`), which would retire the jig, the pins and the probe for it.

## Before the first power-up (bring-up review, 2026-10-07)

**No USB-C supply on the Pi once the Pi 5 V lead (J5 to the cap's J2) is in.** The Pi's own
supply would feed backwards through that lead into `motor_ctrl`'s 5 V rail, through U5 and
its fuse onto the 24 V trunk at about 4.3 V: ten motor drivers and the output panel half
alive on a phone charger. Set the Pi up on its own supply with no cap, then take that
supply away for good. **That port is not left empty: it takes the C-to-C lead from
`output_panel` J2** (the gadget lead; its VBUS is dead-ended on the panel, so it feeds
nothing). The rule is no SUPPLY and no PC in the Pi's USB-C once the 5 V lead is in, only
the J2 lead. Tag the port; do not tape it. The cap's seen face says so.

**Every SERVO42D leaves its box as CAN ID 01, 500K, in the pulse-input mode** (maker's CAN
manual V1.0.9, sections 3.2, 3.11, 3.12). On the bench the tee's drop IS the motor's
supply, so each motor is set up **as the only motor on the tee**: set its ID from
its own screen and buttons, one motor at a time; set the bus-control mode (SR_vFOC);
calibrate it with nothing on the shaft, before the belt goes on. Never plug or unplug a
motor's power or CAN with the trunk live (manual 14.1): the tee is there to swap motors,
with the power off.

**Bus A with no motor first, and the tee is part of it.** The adapter's tails sit in
ways 5 to 7 of the trunk's XHP-8 and meet ways 1 to 4 only on the tee's copper: without
the tee the adapter is on nothing. So: the bench trunk plugged INTO the tee, nothing on
the tee's J2, SW1 OFF, the adapter's own terminator ON. 60 ohm H to L with the power
off, and the board's first frame is acknowledged by the adapter, so "no ACK" cannot be
mistaken for wrong bit timing. Then one motor on J2, the adapter's terminator OFF and
SW1 ON: 60 ohm again. Read SW1 before trusting it: "ships OFF" is what the reel is
expected to do, not something measured.

**Where 24 V goes in once J1 holds the trunk.** It already comes in at the panel's J6
and crosses on the power link (J10 to `motor_ctrl` J3): J3 and J1 are one net on the
motor board, so the trunk on J1 is live as soon as the link is in. A motor calibrating
takes about 2 A (an estimate from the driver's default phase current, not a
measurement). (With the optional bench supply: the pigtail goes into the panel's J7,
limit 2 A with one motor; at 0.3 A the supply folds back and it looks like a fault.)

**The Pi's gadget port has never been run with VBUS absent.** The panel's J2 leaves VBUS
open on purpose. If the Pi does not appear as a gadget through that lead, the first
question is `dr_mode` and VBUS sensing on the Pi, not a dead panel.

**Meter only, before either meets power.** The tee: J1 way 1 = way 8 = J2 way 1; 2 = 7 =
J2 way 2; 3 = 6 = J2 way 3; 4 = 5 = J2 way 4; 24 V to GND open; CAN_H to CAN_L open with
SW1 OFF and 120 ohm with it ON. The cap, off the Pi: J2's lands 1 and 6 to header tails
2 and 4; 5 V to GND open; J6 tail 1 (24 V) to GND open.

**The Pi stage.** Cap seated and checked (`INSTALL_NOTES.md`), the 5 V lead in (bench
limit 1.5 A, if a bench supply is in use). `vcgencmd get_throttled` must read `0x0`.
