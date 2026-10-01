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
| SN74LVC1G3157 | output_panel U12 | ✅ cited in-file (SCES424O Table 4-1) — after being wrong once |
| CH32V307 / CH32V203 | all three MCU boards | ✅ read from `.ins/*.json` |
| SN65HVD230 | motor_ctrl, lever_sensor | ✅ read 2026-09-30, TI SLOS346O §7: matches |
| PCM1808, PCM5102A | output_panel U2, U3 | ✅ read, SLES177B §5 and SLAS859C §7, all 14 + 20 pins: match |
| TLV9061 (SOT-23) | output_panel U7/U8/U9/U11 | ✅ read, SBOS839N Table 5-1: matches (the SC70 column differs — same part number, different pins) |
| AP2112K (SOT25) | lever_sensor U1, output_panel U6 | ✅ read, Diodes DS39724: matches |
| MCP4261 | output_panel U10 | ✅ already cited (DS22059 Table 3-1) and cross-checked against KiCad's symbol |
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
| **WCH-LinkE** | everything downstream of a live MCU | CH32V parts use WCH's two-wire debug; an ST-Link or J-Link will not talk to them. It also carries a USB-serial port |
| **USB-CAN adapter** (CANable-class, `candump`) | what is actually on the bus, from outside it | `motor_ctrl` is the head of BOTH buses and the Pi is not on either — so if `motor_ctrl` is the thing that is broken, nothing in the instrument can see the bus at all |
| **8-channel logic analyser** | CAN TX/RX at the MCU side, SPI to the pot, I2S framing | splits "the MCU is not transmitting" from "the transceiver or the wire is dead" |
| **Multimeter** | rails, continuity, and **60 Ω across CAN_H/CAN_L with power off** | that one reading proves both terminators are present and the bus is unbroken, on either bus, from any connector |
| **Oscilloscope** | buck ripple, CAN wave shape, I2S clock quality | only needed when the cheaper tools say "present but wrong" |

Plus three cables to make once: an **XH and a PH Y-cable** (the bus tap for the CAN adapter),
and a **¼″ TS → bare-wire loopback lead** (section 3).

---

## 2. `motor_ctrl` — head of both CAN buses, three regulators, the Pi's 5 V

**What exists:** TP1–TP5 (SWDIO, SWCLK, NRST, GND, +3V3). `+24V`, `+5V`, `+5V_LED` and both
buses are on connector pins. USB to the Pi on J4.

**What is missing:** no access to `CAN1/2_TX/RX` (the MCU ↔ transceiver side), none to the
pre-filter `+5V_RAW` / `+5V_LED_RAW`, `BOOT0` goes only to its pull-down, and the bucks' PG
pins were unconnected (and until today mis-numbered).

| # | item | area | signal risk |
|---|---|---|---|
| 2.1 | **Firmware reports the CAN controllers' own error state over USB** — TEC/REC, bus-off, and the last-error code per bus. "No ACK" means nobody else is on the bus; "bit/stuff error" means a short or a missing terminator; clean counters with no data means the far end is silent. This distinguishes most bus faults with no hardware at all | 0 | 0 |
| 2.2 | **PG → two MCU GPIOs** (U5.4, U6.4, each with a pull-up to +3V3). PG is open-drain and on an SOIC gull-wing pin, so unlike optical's VQFN it escapes trivially. Firmware can then say *"the Pi's 5 V is out of regulation"* — the single most likely reason a Pi misbehaves | 2× 0402 | 0 (no audio here) |
| 2.3 | **Rail sense into two spare ADC pins** (dividers on +24V and +5V). Optical's MCU "cannot measure one of its own rails"; this one can, for four resistors. Catches a sagging trunk under motor load, which no static meter reading shows | 4× 0402 | 0 |
| 2.4 | **`BOOT0` to a bare pad.** With USB already on J4 that is a second way in (WCH's ROM ISP) that needs no probe on a board mounted in the keyhead. ⚠ **Verify against WCH's reference manual which USB port and which UART the ROM loader uses BEFORE routing to it** — optical lost four routing runs to exactly this assumption | 1 pad | 0 |
| 2.5 | **Four pads on `CAN1_TX/RX`, `CAN2_TX/RX`**, post-route, on existing copper. The logic-analyser hook that separates MCU from transceiver | 4 pads | 0 |

**Status 2026-09-30:** 2.2 and 2.3 are ON THE BOARD and routed 0 / 0 — PG → PC1 (Pi 5 V) and PC6 (LED 5 V) on the MCU's internal pull-ups (no parts), +24 V → PC0 through 100k/10k, +5 V → PA4 through 10k/10k (R18–R21, in two strips that were already free; the board did not grow). The ADC channels are confirmed off the datasheet's pin drawing (PC0 = ADC10, PA4 = ADC4).

**And later the same day U6 left the board** (docs/lighting-bus.md: every lit board makes its own rail, so the motor board owes the lights 24 V and nothing else). PG_LED and PC6 went with it; PG_5V → PC1 and both rail-sense dividers stay. The lighting bus is F3 (3 A) → J7, and its health is read at the LED boards, not here.

**2.4 (BOOT0 pad) — NOT DONE, on purpose.** Reading WCH's datasheet first, as this item demanded, is what stopped it. §2.5.2 says only that the ROM loader works "through the USART1 and USB interface" — it does not say WHICH USB, and this part has two (PA11/PA12, which J4 uses, and PB6/PB7, which nothing here reaches). And on the QFN68 package BOOT1 is a real pin (PB2, pin 28) that floats on this board, so "boot from system memory" (BOOT0 = 1, BOOT1 = 0) is not even well defined without a second part. A pad that might select a loader on a port that might be the right one is not a second way in. SWD on TP1–TP5 is the way in, and the WCH-LinkE is on the tools list. If a USB-only reflash path is ever wanted: pull PB2 down with 10k, then test the ROM loader on J4 on a first-article board BEFORE relying on it.

**2.5 (CAN TX/RX pads) — CLOSED WITH NO HARDWARE.** Both transceivers are SOIC-8 at 1.27 mm pitch with gull-wing leads: pin 1 (D) and pin 4 (R) take a logic-analyser grabber directly. The pads would have duplicated probe points the package already provides.

**Not recommended:** pads on the buses themselves — they are already on five connectors.

---

## 3. `output_panel` — USB hub, MCU, ADC, DAC, the analog output chain

**What exists:** TP1–TP5. `+24V` on four connectors. The jack and the pickup terminal are the
two ends of the whole audio chain.

**What is missing:** `+5V` is reachable only on J4's VBUS pin; `V5_PRE`, `ADC_VREF`, `DAC_LDOO`,
`DAC_VNEG` have no access; the pot is write-only (`POT_SDO_NC`); neither converter has a control
port, so a silent DAC and a silent pot look identical.

| # | item | area | signal risk |
|---|---|---|---|
| 3.1 | **The USB tree is a free three-stage probe.** From the Pi: the hub enumerates → U4, its 12 MHz crystal and +3V3 are alive. The MCU appears behind it → firmware is running. The optical board appears on the other port → that cable and board are alive. Each absence localises to one stage. Write it into the procedure; it costs nothing | 0 | 0 |
| 3.2 | **Analog loopback with a cable, not a circuit.** A TS lead from the output jack back into the pickup terminal (J8): play a tone from the DAC, record it on the ADC. One measurement exercises DAC → filter → pot → buffer → relay → jack → input buffer → ADC → I2S, and repeating it across the relay states, both jack modes and a pot sweep tests every switched path and reads the gain. It replaces most of the pads this board would otherwise want — and adds nothing to a board that cannot spare the area | 0 (one cable) | 0 — it is not connected in use |
| 3.3 | **Rail pads, post-route: `+5V`, `DAC_VNEG`, `ADC_VREF`.** `DAC_VNEG` is the PCM5102's charge-pump output: if it is missing the DAC is silent with every digital signal correct, which is otherwise a long hunt. All three are low-impedance DC nodes | 3 pads | none on `+5V`; `DAC_VNEG`/`ADC_VREF` are decoupled DC nodes — site the pad AT the cap, no stub |
| 3.4 | **`BOOT0` to a bare pad** — same argument and same ⚠ as 2.4; this MCU sits behind the hub, so the ROM loader would enumerate through it | 1 pad | 0 |
| 3.5 | **Pot readback: wire `POT_SDO` to a MISO pin.** Proves the SPI link and the pot's registers. ⚠ Needs a net out of U1's 0.4 mm QFN, which a post-route repair cannot do (recorded limit) — so it is a placement-time change on a board that currently loses its route to any change. **Rank below 3.2, which answers the same question from outside** | 0 parts, 1 net | 0 (SPI idles between volume changes) |

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
- **`pi_cap`:** the diagnostic is on the Pi. `vcgencmd get_throttled` reports under-voltage
  **since boot**, which is the definitive test of the 5 V feed under real load and catches
  cable drop that a meter at the regulator never sees. Pair it with 2.2's PG.

## 6. The procedure  *(0 parts, 0 area — and worth more than any pad)*

As in the optical doc, the cheapest item is writing the order down (into `INSTALL_NOTES.md`):

1. **Bare board, bench supply at 24 V / 100 mA limit.** Current at rest, then each rail with a meter.
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
