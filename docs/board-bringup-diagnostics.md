# The other boards: bring-up diagnostics — work items

**The question (user, 2026-09-30):** do for the other PCBs the analysis
`docs/optical-bringup-diagnostics.md` did for the optical board. *"What tools will we want to
have to be able to diagnose failures and how can we plan them into the boards ahead of time.
Like with optical we should avoid LEDs as diagnosing tools."*

**Answer, in one paragraph.** The three MCU boards can already be debugged once their MCU runs
(all three have SWD pads). What they lack is the same thing optical lacked — observability
**upstream of a running MCU** — plus two things optical did not need: a way to see a **CAN bus**
from outside it, and a way to program **eleven identical sensor boards** without hand-probing
each one. Most of the value is in things that cost no board area at all: a pinout audit, a
written procedure, firmware that reports what it already knows, and six tools on the bench.

**Scope.** `motor_ctrl`, `output_panel`, `lever_sensor`, `can_tee`, `pi_cap` are analysed and
are bronner's to change. The LED boards (`led_strip`, `fret_led`, `foot_led`) and `ui_board`
are **brenner's**: section 7 is recommendations only, nothing here modifies them.

## The constraints every item is gated on

Carried over from optical unchanged, plus the user's LED rule:

- **No board growth** for a debug feature, and nothing that hurts pitch detection or audio.
- **No LEDs as diagnostic tools.** Optical's sequencing argument applies to every board here: a
  virgin board has no firmware to drive one, and by the time firmware is on it you are holding
  a probe that reports more than one bit. (The LED boards' own LEDs are the product, not a
  diagnostic — see section 7.)
- **Nothing new switches in the audio band** on `output_panel`, and **no pad on a high-impedance
  audio node** (`PICKUP_IN`, `VMID`, the op-amp inputs). A pad there is an antenna.
- **Pads go down AFTER routing** (`post_route_refs`, the mechanism optical's TP9–TP11 use).
  This matters more here than it did there: `output_panel`'s route does not survive
  perturbation (three changes, three dirty routes, 2026-09-30), so a pad the router can see is
  a pad that can cost a net.

Each item carries an **area** cost and a **signal** risk, as in the optical doc.

---

## 0. Read every pin table before the board is made  *(0 area, 0 risk — and it already paid)*

**This analysis found a board-killing fault before it wrote a single recommendation.** Asking
"what would report the 5 V rail?" led to the LMR33630's power-good pin, which `motor_ctrl.py`
listed as `NC`. TI SNVSAN3F Table 6-1 says otherwise — and says **seven of the eight pins were
wrong**, on both U5 (the Pi's 5 V) and U6 (the LED 5 V): +24 V was on the power-ground pin. The
board routed, passed DRC and passed ERC, because every check in the pipeline compares the board
to the netlist and the netlist was the thing that was wrong. First power would have blown F1.
**Fixed 2026-09-30** (`_LMR33630_DDA_PINS`, connections now by name).

So the first diagnostic tool is the datasheet. The audit, finished 2026-09-30:

| part | boards | status |
|---|---|---|
| LMR33630 HSOIC (DDA) | motor_ctrl U5, U6 | ❌ **was wrong, fixed**, read from SNVSAN3F Table 6-1 |
| LMR33630 VQFN (RNX) | optical U13, fret/foot U10 | ✅ checked against the same table: correct |
| LMR16006 | motor_ctrl, output_panel | ✅ cited in-file (SNVSA24 §6) |
| TS5A3159 (was SN74LVC1G3157) | output_panel U12 | ✅ replaced 2026-10-04 (the logic-level review): same SC-70-6 land pattern, pinout cited in-file |
| CH32V307 / CH32V203 | all three MCU boards | ✅ read from `.ins/*.json` |
| SN65HVD230 | motor_ctrl, lever_sensor | ✅ read 2026-09-30, TI SLOS346O §7: matches |
| PCM1808, PCM5102A | output_panel U2, U3 | ✅ read, SLES177B §5 and SLAS859C §7, all 14 + 20 pins: match |
| TLV9061 (SOT-23) | output_panel U7/U8/U9/U11 | ✅ read, SBOS839N Table 5-1: matches (the SC70 column differs — same part number, different pins) |
| AP2112K (SOT25) | lever_sensor U1, output_panel U6 | ✅ read, Diodes DS39724: matches |
| AD8402ARZ10 (the MCP4261 until 2026-10-08) | output_panel U10 | ✅ Analog Devices Rev. C, pin configuration drawing and pin function table, which agree: 1 AGND, 2 B2, 3 A2, 4 W2, 5 DGND, 6 SHDN, 7 CS, 8 SDI, 9 CLK, 10 RS, 11 VDD, 12 W1, 13 A1, 14 B1 |
| G6K-2F-Y, AO3400A | output_panel K1, Q1 | ✅ read off the rendered drawings (Omron p. B-83, AOS rev 3 p.1): match, including coil polarity and which contact is NC |
| CH334F | output_panel U4 | ✅ read, WCH V2.91 Table 1-3: every pin the board uses matches. One label differs from the V2.5 the file cites — **pin 18 is PSELF, not NC**. Harmless as built (own pull-up, open = self-powered) but it must never be grounded as a spare |
| **MT6701QT** | lever_sensor U4 | ❌ **pins right, STRAP WRONG — fixed.** All eight pin numbers match rev 1.9 §1.2. But `MODE` was strapped to **GND**, and the reference circuits (fig. 18 vs fig. 7) show GND = **ABZ**, VDD = I2C: all eleven sensors would have been silent on I2C. The file said "confirm polarity on the first board"; the pin *table* does not say, the *figures* do. R5 now goes to +3V3 |

**The audit is complete: 14 part types read, 2 faults.** Both faults were in places the file
itself flagged as unsure (`NC`, "confirm on the first board") — an honest doubt in a comment is
a work item, and both of these sat as comments for weeks.

Two things the MT6701 read turned up that are not pin errors:
* **Its EEPROM cannot be programmed on this board.** §8.2 requires 4.5 V < VDD < 5.5 V for
  programming and the board runs it at 3.3 V. Zero position, direction and hysteresis therefore
  stay at factory values and the MCU holds the offsets — which is the architecture anyway, but it
  means "fix it in the sensor's EEPROM" is not an available bring-up move.
* `Z/CSN` (pin 8) is left open. Fig. 18 ties it to VDD; the pin has its own 200 k pull-up, so open
  reads high, which is what I2C wants. If a sensor ever answers intermittently, this is the first
  pad to tie up.

**The rule that falls out:** a pin list in `elec/*.py` carries its datasheet document number and
table, or it is unverified. Two of the three wrong pinouts this project has had were typed from
memory, and both looked exactly like the right ones.

---

## 1. The bench: six tools, none of them on a board

Tool purchases are shop infrastructure (the project's standing rule) — list them in `BOM.md`'s
Tools section; they are not weighed against anything.

| tool | what it answers | why it is not optional |
|---|---|---|
| **Current-limited bench supply** (24 V, set to ~100 mA for first power) | is anything shorted, before it burns | the LMR33630 fault above becomes a number on a display instead of a blown fuse. First power on every first article goes through this, not the instrument's own supply |
| **WCH-LinkE** | everything downstream of a live MCU | CH32V parts use WCH's two-wire debug; an ST-Link or J-Link will not talk to them. It also carries a USB-serial port. RISC-V mode, four soldered tails (the reset wire always), its 3V3 and 5V pins unused: the probe rule at the end of this document |
| **USB-CAN adapter** (CANable-class, `candump`) | what is actually on the bus, from outside it | `motor_ctrl` is the head of BOTH buses and the Pi is not on either — so if `motor_ctrl` is the thing that is broken, nothing in the instrument can see the bus at all |
| **8-channel logic analyser** | CAN TX/RX at the MCU side, SPI to the pot, I2S framing | splits "the MCU is not transmitting" from "the transceiver or the wire is dead" |
| **Multimeter** | rails, continuity, and **60 Ω across CAN_H/CAN_L with power off** | that one reading proves both terminators are present and the bus is unbroken, on either bus, from any connector |
| **Oscilloscope** | buck ripple, CAN wave shape, I2S clock quality | only needed when the cheaper tools say "present but wrong" |

Plus cables to make once: for bus A, **three tails for the CAN adapter crimped into ways
5 to 7 of the bench trunk's XHP-8** (`docs/bench-order.md`, Tools; this replaces the XH
Y-cable first written here); for bus B, a **PH Y-cable**; and a **¼″ TS → bare-wire
loopback lead** (section 3).

---

## 2. `motor_ctrl` — head of both CAN buses, three regulators, the Pi's 5 V

**What exists:** TP1–TP5 (SWDIO, SWCLK, NRST, GND, +3V3). `+24V`, `+5V` and both
buses are on connector pins. (This section was written when the board also made the
lights' 5 V: `+5V_LED`, `+5V_LED_RAW` and a second buck's PG are no longer on it.) USB to the Pi on J4.

**What is missing:** no access to `CAN1/2_TX/RX` (the MCU ↔ transceiver side), none to the
pre-filter `+5V_RAW`, `BOOT0` goes only to its pull-down, and the bucks' PG
pins were unconnected (and until today mis-numbered).

| # | item | area | signal risk |
|---|---|---|---|
| 2.1 | **Firmware reports the CAN controllers' own error state over USB** — TEC/REC, bus-off, and the last-error code per bus. "No ACK" means nobody else is on the bus; "bit/stuff error" means a short or a missing terminator; clean counters with no data means the far end is silent. This distinguishes most bus faults with no hardware at all | 0 | 0 |
| 2.2 | **PG → two MCU GPIOs** (U5.4, U6.4, each with a pull-up to +3V3). PG is open-drain and on an SOIC gull-wing pin, so unlike optical's VQFN it escapes trivially. Firmware can then say *"the Pi's 5 V is out of regulation"* — the single most likely reason a Pi misbehaves | 2× 0402 | 0 (no audio here) |
| 2.3 | **Rail sense into two spare ADC pins** (dividers on +24V and +5V). Optical's MCU "cannot measure one of its own rails"; this one can, for four resistors. Catches a sagging trunk under motor load, which no static meter reading shows | 4× 0402 | 0 |
| 2.4 | **`BOOT0` to a bare pad.** With USB already on J4 that is a second way in (WCH's ROM ISP) that needs no probe on a board mounted in the keyhead. ⚠ **Verify against WCH's reference manual which USB port and which UART the ROM loader uses BEFORE routing to it** — optical lost four routing runs to exactly this assumption | 1 pad | 0 |
| 2.5 | **Four pads on `CAN1_TX/RX`, `CAN2_TX/RX`**, post-route, on existing copper. The logic-analyser hook that separates MCU from transceiver | 4 pads | 0 |

**Status 2026-09-30:** 2.2 and 2.3 are ON THE BOARD and routed 0 / 0 — PG → PA6 (Pi 5 V; it was PC1 until 2026-10-07) and PC6 (LED 5 V) on the MCU's internal pull-ups (no parts), +24 V → PA4 through 100k/10k (PC0 until 2026-10-07), +5 V → PA5 through 10k/10k (PA4 until 2026-10-07) (R18–R21, in two strips that were already free; the board did not grow). The ADC channels are confirmed off the datasheet's pin drawing (PC0 = ADC10, PA4 = ADC4).

**And later the same day U6 left the board** (docs/lighting-bus.md: every lit board makes its own rail, so the motor board owes the lights 24 V and nothing else). PG_LED and PC6 went with it; PG_5V → PC1 (PA6 since 2026-10-07) and both rail-sense dividers stay. The lighting bus is F3 (3 A) → J7, and its health is read at the LED boards, not here.

**2.4 (BOOT0 pad) — NOT DONE, on purpose.** Reading WCH's datasheet first, as this item demanded, is what stopped it. §2.5.2 says only that the ROM loader works "through the USART1 and USB interface" — it does not say WHICH USB, and this part has two (PA11/PA12, which J4 uses, and PB6/PB7, which nothing here reaches). And on the QFN68 package BOOT1 is a real pin (PB2, pin 28) that floats on this board, so "boot from system memory" (BOOT0 = 1, BOOT1 = 0) is not even well defined without a second part. A pad that might select a loader on a port that might be the right one is not a second way in. SWD on TP1–TP5 is the way in, and the WCH-LinkE is on the tools list. If a USB-only reflash path is ever wanted: pull PB2 down with 10k, then test the ROM loader on J4 on a first-article board BEFORE relying on it.

**2.4, 2026-10-06 (pre-order review): the strap and the pad are on the board now, and SWD is still the only way in to rely on.** BOOT1 (PB2, pin 28) is tied to GND at the pin, a 0.9 mm track into the belly land with no part, so "boot from system memory" is defined; and BOOT0 has a 1.0 mm pad, TP6, labelled, beside the SWD pads. Bridging TP6 to TP5 (3V3) through a reset starts WCH's ROM loader. What is still not known is the thing this item stopped on: which USB port that loader enumerates on (PA11 / PA12, which J4 carries, or PB6 / PB7, which nothing here reaches). Try it on the first board; until it has been seen to work, the WCH-LinkE on TP1 to TP5 is the path the board depends on.

**2.5 (CAN TX/RX pads) — CLOSED WITH NO HARDWARE.** Both transceivers are SOIC-8 at 1.27 mm pitch with gull-wing leads: pin 1 (D) and pin 4 (R) take a logic-analyser grabber directly. The pads would have duplicated probe points the package already provides.

**Not recommended:** pads on the buses themselves — they are already on five connectors.

---

## 3. `output_panel` — USB hub, MCU, ADC, DAC, the analog output chain

**What exists:** TP1–TP5. `+24V` on four connectors. The jack and the pickup terminal are the
two ends of the whole audio chain.

**What is missing:** `+5V` is reachable only on J4's VBUS pin; `V5_PRE`, `ADC_VREF`, `DAC_LDOO`,
`DAC_VNEG` have no access; the pot is write-only (the 14-lead AD8402 has no data output); neither converter has a control
port, so a silent DAC and a silent pot look identical.

| # | item | area | signal risk |
|---|---|---|---|
| 3.1 | **The USB tree is a free three-stage probe.** From the Pi: the hub enumerates → U4, its 12 MHz crystal and +3V3 are alive. The MCU appears behind it → firmware is running. The optical board appears on the other port → that cable and board are alive. Each absence localises to one stage. Write it into the procedure; it costs nothing | 0 | 0 |
| 3.2 | **Analog loopback with a cable, not a circuit.** A TS lead from the output jack back into the pickup terminal (J8): play a tone from the DAC, record it on the ADC. One measurement exercises DAC → filter → pot → buffer → relay → jack → input buffer → ADC → I2S, and repeating it across the relay states, both jack modes and a pot sweep tests every switched path and reads the gain. It replaces most of the pads this board would otherwise want — and adds nothing to a board that cannot spare the area | 0 (one cable) | 0 — it is not connected in use |
| 3.3 | **Rail pads, post-route: `+5V`, `DAC_VNEG`, `ADC_VREF`.** `DAC_VNEG` is the PCM5102's charge-pump output: if it is missing the DAC is silent with every digital signal correct, which is otherwise a long hunt. All three are low-impedance DC nodes | 3 pads | none on `+5V`; `DAC_VNEG`/`ADC_VREF` are decoupled DC nodes — site the pad AT the cap, no stub |
| 3.4 | **`BOOT0` to a bare pad** — same argument and same ⚠ as 2.4; this MCU sits behind the hub, so the ROM loader would enumerate through it | 1 pad | 0 |
| 3.5 | ~~Pot readback~~ **not available since 2026-10-08:** the 14-lead AD8402 has no data output, so there is nothing to read back; 3.2 is the test of the pot. As written for the earlier part: wire `POT_SDO` to a MISO pin. Proves the SPI link and the pot's registers. ⚠ Needs a net out of U1's 0.4 mm QFN, which a post-route repair cannot do (recorded limit) — so it is a placement-time change on a board that currently loses its route to any change. **Rank below 3.2, which answers the same question from outside** | 0 parts, 1 net | 0 (SPI idles between volume changes) |

**Status 2026-09-30 — this board takes NO hardware changes, and that is the finding.** Six
placement changes were routed on it (a diode move, five USB overhang values); every one split
a USB pair, because `HUB_DN1` and `THRU` are routed one conductor at a time and the pair layer
cannot yet declare them. So 3.4 and 3.5 wait on that tooling, and 3.3 is answered without pads:

| rail | probe at | expect |
|---|---|---|
| `+5V` | **FB1 pin 2** (the bead's output), or relay K1 pin 1 | 5.0 V |
| `V5_PRE` | **FB1 pin 1** / L1 pin 2 | 5.0 V, before the bead |
| `DAC_VNEG` | **C33 pin 1** (it is the only other thing on the net) | **−3.3 V**; missing = a silent DAC with every digital signal correct |
| `DAC_LDOO` | **C30 or C31 pin 1** | 1.8 V |
| `ADC_VREF` | **C19 or C20 pin 1** | 2.5 V (half of 5 V) |

Each is the hot pad of a decoupling part already sitting at the pin, which is exactly where a
test pad would have gone. A meter probe on an 0402 pad is fiddly but it is a first-article
measurement made once, not a production step.

**Deliberately NOT done:** no pad on `VMID`, `PICKUP_IN` or any op-amp input. Read `VMID`
indirectly — every buffer output rests at it — which is optical's `MID` rule for the same reason.

---

## 4. `lever_sensor` — eleven of them, buried in the chassis and the legs

**What exists:** TP1–TP4 (SWDIO, SWCLK, GND, NRST). `+5V` and the bus on J1.

**What is missing:** **no `+3V3` pad** — the only MCU board without one. No bootloader path at
all (no USB, no UART, `BOOT0` strapped): SWD is the only way in, and it needs the board in hand.
And the four pads are scattered — pitches of 2.40, 3.32 and **9.94 mm** — where `motor_ctrl`'s
and `output_panel`'s are scattered differently again.

| # | item | area | signal risk |
|---|---|---|---|
| 4.1 | **One SWD pad pattern, the same on every board.** Eleven boards flashed by hand-probing four scattered pads is eleven chances to slip; a fixed footprint (say 5 pads on a 2.54 mm line: 3V3, SWDIO, SWCLK, NRST, GND) takes one pogo clip for all thirteen MCU boards in the instrument. Same pads, moved — the outline is branner's re-spin spec and does not change | 0 net (adds the +3V3 pad, item 4.2) | 0 |
| 4.2 | **`+3V3` pad** — folded into 4.1's pattern. Separates "LDO dead" from "MCU dead" with a meter | 1 pad | 0 |
| 4.3 | **A CAN bootloader in flash** (firmware, not ROM — WCH's ROM loader is USB/UART only). These boards sit inside knee-lever housings and pedal legs; without this, every firmware fix is a disassembly ×11. It is the highest-value item on this board and it is not hardware | 0 | 0 |
| 4.4 | **Report the MT6701's field-strength status over CAN.** The sensor flags a magnet that is too weak or too strong. A missing magnet, a wrong gap or a flipped magnet is the likeliest *mechanical* fault on a lever, and this reads it out without opening anything | 0 | 0 |
| 4.5 | **Report the MCU's unique ID and a firmware version on boot.** With eleven identical boards, "which one is misbehaving" is a diagnosis in itself; wiggle a lever, see which ID moves | 0 | 0 |
| 4.6 | **Independent watchdog on, always.** One node whose firmware hangs with its transmit pin dominant silences the bus for all eleven, and the daisy chain means the only isolation is unplugging. ⚠ Check whether the SN65HVD230 has a dominant-timeout (I believe it does not — verify); if not, the watchdog is the only thing bounding that fault | 0 | 0 |

**Checked against the datasheets 2026-09-30, and two rows above change:**

* **4.4 is NOT available on the board as built.** The MT6701 reports field status (`Mg[1:0]`: too
  strong / too weak; `Mg[3]`: over-speed) only in its **SSI** frame (§7.8); the I2C registers
  carry the angle and nothing else. SSI uses the same two wires but needs `CSN` driven, and
  pin 8 is open. The fix is one track — `Z/CSN` → PB5 (pin 26, table 3-1-3) — no parts, and the
  bus stays plain I2C while PB5 is an input.
  **DONE 2026-09-30.** The first attempt was reverted: the chip-select routed but `NRST` then
  failed on five placements running. `NRST` (U3 pin 4) sits between the crystal pins (2, 3)
  with its cap and pad on the far side of the chip from the crystal, so on F.Cu it must cross
  both oscillator tracks at a 0.4 mm-pitch escape, and the router only found the hop on some
  rolls. The cure was to DECLARE the hop: one NRST via beside the pin, laid before routing.
  With it the board closes first pass with the chip-select in: 0 unconnected, 0 violations.
* **4.1 / 4.2 — CLOSED AS A JIG, NOT A PAD PATTERN.** A shared 5-pad line at 2.54 mm is
  10.2 mm of pads, and this board's own source records it as full (six free 2.0 mm sites, four
  already spent on TP1–TP4; a single extra 0402 failed to place three times). The pads stay
  where they are. Two things replace the recommendation:
  * **A printed programming jig** — a nest the 31.0 × 21.9 board drops into, with four pogo
    pins at TP1–TP4's positions (read from `elec/geom/lever_sensor.geom.json`, so it follows a
    re-route) wired to the WCH-LinkE. Scattered pads stop mattering once nothing is
    hand-probed; eleven boards become eleven drops. **Designed: `src/lever_jig.py`**, listed in
    `BOM.md` Tools.
  * **`+3V3` is probed at U1 pin 5** (the AP2112K's output, a SOT-23-5 leg) — no pad needed.
    That is the "LDO dead vs MCU dead" measurement.
* **4.6 is confirmed.** TI's SN65HVD230 datasheet (SLOS346O) has no dominant-timeout — the
  term does not appear in it. The independent watchdog is the only thing bounding a node that
  hangs with its transmit pin dominant.
* **`BOOT0` is NOT open — I had this wrong.** Pin 1 (BOOT0, shared with PB8) is tied hard to GND in `lever_sensor.py`; I read a stale comment higher in the file and reported it as floating. WCH's datasheet (table 3-1-3, note 6) confirms pin 1 is BOOT0/PB8 and wants it low at power-on, which a hard tie does. **Two firmware rules follow from the same table:** never drive PB8 as an output (it is shorted to ground), and never drive PA10 — on the 28-pin package PA10 and PA11 are ONE pin (19), which this board uses as CAN RX (note 7).

**Isolating a bad node** stays a matter of unplugging along the daisy chain — the buses are
connectorised end to end, so a binary search is at most four unplugs for eleven boards. The
optical board had no equivalent, which is why it needed item 6 there and this board does not.

---

## 5. `can_tee` ×9 and `pi_cap` — passive, nothing hidden

Every net on both boards is on a connector pin, so there is nothing a pad could add.

- **`can_tee`:** build **one spare tee into the harness as a permanent sniff port** (or leave a
  drop unpopulated). Bus A then has a place to plug the USB-CAN adapter without unplugging a
  motor — and unplugging a motor to listen changes the thing being listened to. Zero board
  change: it is a tenth copy of a board already being ordered in nines.
- **`can_tee` — MEASURE ONE MOTOR'S SLEW CURRENT, FIRST BRING-UP, BEFORE THE FLEET MOVES.**
  The trunk's +24 V crosses each tee on one 3 A XH contact. With the dual feed at 54 / 46
  that allows **5.5 A** on bus A; the budget is < 5 A (slew staggered) and the supply is
  6.5 A for the whole instrument. Every one of those rests on **0.8 A per moving motor,
  which is derived, never measured.** Put a clamp meter (or the bench supply's readout) on
  one motor's drop through a full-speed, full-load move and write the peak here. Then set
  the firmware's hard cap on simultaneous movers to floor(5.0 / that number) — six at
  0.8 A. `docs/can-tee-power-tap.md` has the arithmetic.
- **`pi_cap`:** the diagnostic is on the Pi. `vcgencmd get_throttled` reports under-voltage
  **since boot**, which is the definitive test of the 5 V feed under real load and catches
  cable drop that a meter at the regulator never sees. Pair it with 2.2's PG.

## 6. The procedure  *(0 parts, 0 area — and worth more than any pad)*

As in the optical doc, the cheapest item is writing the order down (into `INSTALL_NOTES.md`):

0. **Meter the supply's plug BEFORE it ever meets the panel (added 2026-10-01).** The inlet is a 4-pin Kycon jack and each rail is a COLUMN of it: looking into the jack with its key up, the two right-hand pins (Kycon 2 and 4) are +24 V and the two left-hand ones (1 and 3) the return. Mean Well numbers its R7B plug differently (its 1 and 2 are Kycon's 2 and 1); until 2026-10-06 the board was laid out from Mean Well's numbers on Kycon's pads, a dead short across the supply. A wrong reading swaps or shorts the rails, and nothing on `output_panel` survives 24 V backwards. Looking into the PLUG with its key up, confirm which two pins are positive, then check them against J6's pads with the board unpowered: pads 2 and 4 are joined to each other and to Q2's source lead, pads 1 and 3 to each other, to the jack's shell and to J7 pin 1.
1. **Bare board, bench supply at 24 V / 100 mA limit.** Current at rest, then each rail with a meter. **Plug the lead first, THEN switch the supply's output on** — never push a live 24 V lead into a board. A live lead into ceramic input capacitors rings toward 48 V, and the LMR33630 on `motor_ctrl` is a 36 V part (38 V absolute). In the instrument the rail arrives through the output panel's switch at about 2 V/ms and cannot ring; on the bench nothing stops it but this habit. (`optical` has a 2 Ω series resistor, R44, for exactly this and survives it; `motor_ctrl` carries 3 A on that input and cannot have one — its TVS and fuse are not a substitute for the order of operations.)
2. **`motor_ctrl` alone:** SWD attaches → flash → USB enumerates on the Pi → 2.1's counters read "no ACK" (correct: nothing else is on the bus yet).
3. **Add one node at a time**; the counters go clean when the first one acknowledges. Power off, **60 Ω** across each bus.
4. **`output_panel`:** the USB tree (3.1), then the loopback (3.2).
5. **Levers:** IDs appear (4.5), field status is in range (4.4), each lever moves its own ID.

## 7. Recommendations only — brenner's boards

Not mine to change; offered because the same lens applies.

- **The TLC59711 chain is write-only**, so there is no readback — but a broken chain localises
  itself: everything past the break is dark. That is the one case where the product's own LEDs
  do the diagnosing, and it needs no added part.
- **`fret_led` / `foot_led` bucks:** their LMR33630 (VQFN) pinout is correct (section 0). PG is
  parked on `BUCK_PG_NC`; optical measured that pin unescapable on its own layout, so a rail
  pad at each buck's output is the realistic equivalent.
- **`ui_board`:** no MCU; the Pi reads every line directly, so a Pi-side script that reports
  each switch and encoder edge is the whole test.

## Ordering

1. **Finish section 0** — CH334F and MT6701 first, then the eight uncited parts. Nothing else on this list is worth doing on a board with a wrong pinout.
2. **Section 6**, and the firmware items (2.1, 4.3–4.6, 3.1): no hardware, no route.
3. **`motor_ctrl` 2.2–2.5** as one change. That board routes cleanly and is being re-routed for the pinout fix anyway.
4. **`lever_sensor` 4.1–4.2** with branner, since the outline is theirs.
5. **`output_panel` 3.3–3.4** only as post-route pads, and only once that board routes clean under change.

## Leg blind-mate boards (elec/leg_pogo.py)

Four passive boards, four conductors each (GND, +5V, CAN_H, CAN_L). Each carries four bare
test pads, TP1-TP4 in that order, so nothing has to probe a spring pin or a gold face.

1. **Before fitting: each board alone.** Meter TP1-TP4 to the connector's ways 1-4. Any
   other pairing is a wrong board, not a bad one.
2. **The joint, mated, leg unplugged at the far end.** Meter TP-to-TP across the joint:
   TP1 to TP1 ... TP4 to TP4, under 1 ohm each, and open between neighbours. THIS IS THE
   TEST THAT THE MIRRORED PAIR IS THE RIGHT PAIR -- the top and bottom joints use
   mirror-image boards, and a bottom board in a top pocket reverses the row (5 V onto
   CAN_H). The female's notch is on opposite sides in the two, so it should not go in; the
   meter is the proof.
3. **Loaded.** With bus B powered, +5V at the far female's TP2 should sit within 0.1 V of
   the near one. More than that is a contact, not copper (the boards are under 20 mOhm).

## Output panel: three things to know before the first power-up (2026-10-04)

* **The two grounds meet at R60.** `GND` and `PWR_GND` are joined by one 0 ohm link beside
  the 5 V buck (2026-10-04), so the board runs from the inlet alone. If hum from the
  motors ever shows in the audio, R60 is the part to swap for a bead.
* **The inlet is switched, and it fails on.** Q2 passes 24 V unless the UI board's power
  button shorts its wire (J10 way 5 or 6, picked by JP1) to ground. With J10's button ways
  open, as on a bench, the panel is on whenever the supply is plugged in. To test OFF, short
  the selected way to `PWR_GND` (J10 way 1): the output should fall and the supply current
  drop to 2.55 mA. Turn-on is a 16 ms ramp, not a step.
* **The audio ADC is on I2S3, not I2S2.** The CH32V307 has two standard I2S blocks and no
  full-duplex extension, so the DAC is I2S2 (master transmit) and the ADC's data is I2S3
  (PB5) as a slave receiver, with I2S3's clock pins (PA15 word clock, PB3 bit clock) tied
  on the board to I2S2's. Firmware has to enable both and start I2S3 before I2S2.

## Pre-order review, 2026-10-06: what the bench and the firmware must know

Nothing here changes copper. It is the part of the review that lands on whoever powers the
first boards and writes their first firmware.

* **SWD is the only programming path to rely on, on every MCU board.** `motor_ctrl` has a
  second one that is untested (2.4 above), `output_panel` and `lever_sensor` have none, and
  `optical` has one through its own I2C bus that has never been run
  (`docs/optical-bringup-diagnostics.md`, item 3). Have the probe and the pads working
  before anything else is tried.
* **`motor_ctrl`: two inputs read "fault" until firmware turns their pull-ups on.**
  `PG_5V` (PA6, from the 5 V buck) and `BUSB_FAULT_N` (PC6, from bus B's switch) are
  open-drain outputs with no resistor on the board. Both pins must be inputs WITH the
  internal pull-up; as plain inputs they float low and say the Pi's 5 V is bad and bus B
  is shorted on a healthy board.
* **Nothing fuses the 24 V trunk.** The brick's own limit (6.67 A, hiccup) is the
  protection for the trunk and for the ten motors on it. What IS fused or limited is every
  branch that leaves it: the optical board (F1 on `output_panel`, 1 A), the 5 V buck (F1 on
  `motor_ctrl`), the lights (F3), the Pi's 5 V (F2, 4 A) and bus B (U6, 0.52 A). So first
  power is from a current-limited bench supply, not the brick: a short on the trunk has
  6.67 A behind it.
* **The rail clamp is a 24 V part.** D8 on `motor_ctrl` and D6 on `output_panel` are
  SMCJ24A: they start to conduct between 26.7 and 29.5 V. A bench supply set above 26 V
  will warm them, and one left at 30 V will destroy them (they fail short, and the supply
  current-limits into them). Set 24.0 V.
* **Wrong socket.** Which plugs fit which sockets, and what each swap does, is tabled in
  `INSTALL_NOTES.md` ("fit each other's sockets"). None of the swaps does damage. The motor
  drop is the exception that can: it is split across two terminal blocks on the motor and
  crossed on the CAN pair (`docs/bench-order.md`, "The motor drop").

## Review run 3, 2026-10-07: firmware and first-power notes (no board change)

**motor_ctrl**
* `PG_5V` (PA6) and `BUSB_FAULT_N` (PC6) are both on EXTI line 6: one of them can have
  the edge interrupt, the other is polled. Both need the internal pull-up.
* PB2 (BOOT1) is tied hard to ground. Never drive it as an output.
* CAN2 only works with CAN1's clock on (CAN1 owns the shared filters), even where CAN1
  itself is idle.
* Same-shell pairs that will accept each other's plug: J1 and J7 (both 4-way XH), and
  J4 (the USB lead, 4-way PH) against the bus-B leads on J2 / J6. The silk names them;
  read it.

**motor_ctrl and output_panel, before first power:** ohm +3V3 to GND. A mask-covered
+3V3 track still runs 3.06 to 3.20 mm from the CH32V307's centre, inside the reach of
the largest slug the package drawing allows (3.25 mm). No signal via stands in that
band any more; the track is under mask, so this is a check, not an expected fault.

**output_panel:** J4's VBUS has no current limit of its own and the rail behind it is
0.6 A. Only the optical board plugs in there.

**pi_cap:** measure the Pi's 3V3 pin current with the UI ribbon attached (the estimate is
345 to 375 mA and the Pi publishes no rating for that pin). The ribbon header J5 is
unkeyed: way 1 is marked on the silk.

**Hardware-only, still to measure:** the trunk contact at 97 % of its 3 A rating; the
SMCJ24A's stand-off and the LMR33630's 38 V under an all-motor stop (scope trace on the
24 V rail).

**Stock seen thin on 2026-10-07** (the relay and the pot have since been changed for well-stocked parts: C47190 and the AD8402)**:** KPJX-4S-S 19, G6K relay 48, MCP4261 96,
LMR33630BRNXR about 260.

## Bring-up review, 2026-10-07: the first evening on `motor_ctrl` and `output_panel`

One copper change came out of this review: on `output_panel`, PB2 (BOOT1, U1 pin 28) is
joined to JACK_MODE, so R37 holds it low at reset. Everything else is what to do and what
not to do. The optical board's own list is in `docs/optical-bringup-diagnostics.md`.

### The probe rule (all three MCU boards)

* **Four wires, soldered: SWDIO (TP1), SWCLK (TP2), GND (TP4) and ALWAYS the reset wire
  (TP3).** `optical` with a genuine ST-Link wants a fifth, TP5 to the probe's
  target-voltage sense pin (UNVERIFIED for clones, which may source 3.3 V there: leave a
  clone's pin off). Flashing works without the reset wire; getting back from a bad flash does not.
  Fit it on day one, not when it is first needed.
* **Soldered tails, not a clip.** The pads are bare lands. On the two CH32V307 boards the
  four wired pads are two pairs 3 mm apart, the pairs 18 to 29 mm from each other; on
  `optical` the pads are 8.9 mm apart. Tails under 30 cm, left on the board. A wire
  loop soldered to TP4 is the ground a scope clip can hold.
* **WCH-LinkE in RISC-V mode** for the two CH32V307 boards.
* **The LinkE's 3V3 and 5V pins are power OUTPUTS, side by side on its header.** Never a
  wire on the 5V pin. No wire from the 3V3 pin to TP5 while 24 V is on. On `motor_ctrl`,
  5 V on TP5 is 5 V on the MCU, which stops at 4.0 V (the two CAN transceivers, TCAN3413
  and SN65HVD230, stand 6 V): one of two assembled boards. TP5 is where the METER goes. (The generators
  called it "target sense", which is an ST-Link's word for an input. Corrected.)
* **Never press "Disable Two-Line Interface" in WCH-LinkUtility** (manual 5.2.8), which
  MounRiver calls "Disable 2-wire SDI" (4.3.3). The same button under two names.

### Getting back from a bad flash

CH32V307 (`motor_ctrl`, `output_panel`):

| what the firmware did | symptom | way back | needs |
|---|---|---|---|
| wrong clock tree, dead PLL, fault at start | runs wrong or not at all | attach and reflash | the three wires |
| remapped PA13 / PA14, or entered sleep / stop / standby at start | "cannot connect" | WCH-LinkUtility, **"Clear All Code Flash", the by-reset-pin form** (WCH-Link manual V2.7, 5.2.4; the menu's exact wording, "By Pin NRST", is read off a screenshot there) | the reset wire on TP3 |
| the same, and the reset erase does not take | "cannot connect" | **"Clear All Code Flash - By Power Off"** (same section): the Link powers the chip | a fifth tail soldered to TP5 for this and taken off afterwards, LinkE 3V3 on it with the board's own power OFF. `motor_ctrl`: J1 / J3 / J5 / J7 unplugged (see back-feed below). `output_panel`: J3, J4, J7, J9 and J10 unplugged, and prefer the BOOT0 row there |
| the same, no reset wire | "cannot connect" | BOOT0 high through a reset, then the Link as usual | `motor_ctrl`: a soldered wire from TP6 (BOOT0) to TP5 (solder a fifth tail to TP5 for this; take both off afterwards). `output_panel`: tweezers from R7 pad 1 to R6 pad 2 |
| debug closed for good | the Link is dead | the ROM loader with WCHISPTool over USB | BOOT0 high as above, and a USB lead |

* **The ROM loader's USB is on PA11 / PA12 or PB6 / PB7** (WCH's CH32V307 evaluation-board
  reference V1.6; its serial side is PA9 / PA10, brought out on neither board). That
  closes open question 2.4: `motor_ctrl`'s J4 is on PA11 / PA12, and `output_panel`'s MCU
  is reached through its hub on J3.
* **`output_panel` has no BOOT0 pad.** R7 pad 1 is BOOT0 and R6 pad 2 is +3V3, 3.5 mm
  apart beside the crystal: bridge them with tweezers through a reset. **The reset is an
  NRST reset or a power cycle, not a software reset.** BOOT1 is PB2, which the board now
  holds low, so this recovery is deterministic (before this change PB2 floated, and BOOT0
  high with BOOT1 high starts from SRAM, not the loader). On `motor_ctrl` BOOT1 is tied
  to ground.
* **Prove the ROM loader on the first evening**, while the debug wires still work. It is
  the one recovery nobody has run, and on `motor_ctrl` it also tests the hand-made USB
  lead.

### Seeing the firmware run, with no LED and no UART pad

* **printf over the two debug wires.** The WCH-LinkE's "SDI virtual serial port" (manual
  5.2.11; CH32V30x is listed; WCH's `SDI_Printf` example). No pin, and it does not depend
  on the clock tree being right. This is the console on both CH32V307 boards.
* **`motor_ctrl`: PA6 is also UART7_TX (remap 1) and USART1_TX (remap 3).** PA6 is PG_5V,
  and its only other node is U5 pin 4, an SOIC lead a grabber holds. Open-drain only: U5
  pulls the same line low when the 5 V rail is bad.
* **`motor_ctrl`, scope points firmware can wiggle:** PA5 on the pad R18 and R19 share
  and PA4 on the pad R20 and R21 share (the two rail-sense dividers, 5k and 9k1 of source
  impedance behind them), besides PA6 at U5 pin 4.
* **`output_panel`: toggle PC5.** The relay clicks.
* **`motor_ctrl`, with no firmware at all:** a 10k from TP5 to PA6 (at U5 pin 4) or to PC6
  (at U6 pin 4) is the pull-up the firmware would have supplied, and a meter then reads
  PG and FAULT directly.
* **`output_panel`: PB2 reads back what PB1 drives.** The two pins are one net now, so the
  JACK_MODE output has a free self-test.

### The first firmware: rules that protect the board and the way back in

* **A 2 s delay at the top of `main()`, before any sleep, standby or debug-pin remap.**
  It is the window the probe always has.
* **Never drive PB2**, on either board. On `output_panel` it is tied to PB1 (JACK_MODE):
  an output there fights PB1 and moves the jack mode. It stays an input for ever, with
  no pull-up.
* **`motor_ctrl`: PA6 and PC6 are never push-pull** (U5's PG and U6's FAULT are open-drain
  outputs on those lines; inputs with the internal pull-up). **PB13 held low stops bus B
  and nothing times it out**: the SN65HVD230 has no dominant time-out.
* **`motor_ctrl`: PB8 and PB12 (the two CAN RX lines) stay inputs.** Each is driven by
  its transceiver.
* **`output_panel`: the gain pot (U10, AD8402) has no memory.** It wakes with both
  wipers at mid-scale. Firmware keeps the gain in the MCU's flash, writes BOTH channels
  at boot, and saves a moment after the last change, not on every step. The word is 10
  bits, MSB first: two address bits (00 = the tip channel, 01 = the ring channel) then
  eight data bits, clocked on the rising edge and latched when CS rises. CS idles high
  on the board's own divider (3.0 V) while the MCU is in reset; drive it push-pull.
  Nothing on the MCU reaches the pot's RS or SHDN pins.
* **`output_panel`: PA15 and PB3 stay inputs.** They are tied on the board to PB12 / PB13
  (I2S2 WS / CK). An "unused pins to outputs" loop shorts them.

### First power, staged

**One bench pigtail serves all three 24 V boards**: an XHP-4 with way 1 = 24 V, way 2 =
GND, ways 3 and 4 empty, into `motor_ctrl` J1, `output_panel` J7 or `optical` J2. Meter
its polarity first. Plug it with the supply's output OFF.

`motor_ctrl`:

0. **Power off, meter:** 120 ohm across J1 ways 3 / 4 (R5), no terminator across J2 ways 3 / 4
   (tens of kilohms or more: the SN65HVD230's own input),
   and +3V3 to GND not a short.
1. **8 to 12 V, limit 50 mA.** Only the 3V3 converter runs (U5 holds off until 18.1 V).
   TP5 reads 3.31 V at 10 to 25 mA. Attach the probe and flash here: a wrong 5 V rail
   cannot exist yet.
2. **24.0 V, limit 150 mA.** 5.02 V on J5's outer posts, 5 to 15 mA from the supply
   with the MCU erased and nothing plugged in.
3. **Raise the limit to 0.3 A, then load the 5 V rail**: 10 ohm 5 W on J5 (0.5 A), still
   5.0 V. Below 0.3 A the supply folds back as U5 starts, the trunk falls under U5's
   turn-off, and the rail motorboats: it looks like a broken converter and is the bench
   supply.
4. **Only then the Pi**, at a 1.5 A limit; `vcgencmd get_throttled` must read `0x0`. Its
   header has no protection.

(Readings are datasheet estimates, not measurements: replace them with the first board's.)

`output_panel`:

1. **The pigtail into J7, 24.0 V, limit 100 mA.** Not J6: the inlet takes only the brick's
   plug and the brick has 6.67 A behind it. J7 is behind the power switch (Q2), so this
   bypasses it; the jack's pins go live through Q2's body diode, which is harmless. The
   switch is tested later, on the brick, after J6's polarity has been metered.
2. **If the supply sits in current limit with 5 to 8 V on the rail, raise the limit to
   250 mA before calling it a short.** The buck stalls in a 100 mA limit once the hub and
   the MCU are running.
3. **Before any firmware:** the hub enumerates on a PC through J3, and the direct path
   J8 to the jack plays (relay released, both wipers at mid-scale, about -6 dB: the pot's own reset network puts them there 10 ms after the rail stands). Neither needs the
   MCU, and with both proven a later fault is the firmware's.
4. **No K1, no sound, in any mode.** If the relay was not placed (stock was thin), bridge
   its pads 2-3 and 6-7 to go on.
5. **Plug J4 with the power off, and only the optical board goes there.** A hot plug dips
   +5V far enough to brown the MCU out mid-flash.

### Back-feed

* **No USB-C supply on the Pi once the J5 to J2 lead is in.** It reaches the 24 V trunk at
  about 4.3 V through U5 and F1. No supply and no PC in the Pi's USB-C; the one lead
  that belongs there is the C-to-C from `output_panel` J2, whose VBUS is dead-ended. Tag
  the port; do not tape it.
* **3.3 V on `motor_ctrl`'s TP5 reaches the 24 V net through U1.** For a power-off erase,
  unplug J1, J3, J5 and J7 first, or the probe is charging the motor trunk and the erase
  "does not work".

### The ohm check, corrected

On `motor_ctrl` a mask-covered +3V3 segment at (113.11 .. 113.84, 110.56) in the board
file's millimetres, with U4's centre at (112.60, 107.50), lies 0.16 mm
INSIDE the nominal exposed slug of the CH32V307, not only inside the largest the drawing
allows. It is under solder mask; a pinhole there is a +3V3 to ground short under the
part. **Meter +3V3 to GND on both assembled boards before either meets 24 V.**

### pi_cap

In the fab's placement preview, J5's pins must point off the board edge: its placement
frame was entered by hand.
