# Optical board: bring-up diagnostics — work items

**The question (user, 2026-09-26):** *"When the optical PCB arrives, if we're lucky we plug it
in and it just works. If it doesn't, will we have the tools we need to know why?"*

**Answer:** we can diagnose almost everything **downstream of a running MCU**, and almost
nothing **upstream of it** — which is where a first-article board fails.

**The constraints every item below is gated on (user, 2026-09-26):**

> Any debugging change is welcome **so long as it does not make the board larger** and does
> **not reduce the board's ability to detect pitch accurately or to output high-quality audio.**

So each item carries an explicit **area** cost and an explicit **signal** risk, and an item that
cannot pass both is not on the list. Two rules fall straight out of the constraints and apply to
every item:

- **Indicators live on `+3V3D` or `+5V`, never on `+3V3A`.** `+3V3A` is the quiet LDO that feeds
  the TIAs and the converters' AVDD; nothing decorative belongs on it.
- **Nothing new switches in the audio band.** A DC-static line beside the analog cells is
  harmless; a line toggling at 1 Hz-20 kHz beside them is an injector.

`MID` deserves its own rule: it is the reference all 20 TIAs sit on, so anything on it appears on
**every channel at once** and calibration cannot tell it from signal. **No test pad goes on
`MID`** — see item 6 for why none is needed.

---

## What already exists

| Present | Notes |
|---|---|
| `TP1`-`TP5` = SWDIO, SWCLK, NRST, GND, +3V3D | Bare pads, no paste, excluded from BOM and pick-and-place. `NRST` is the one that looks optional and isn't: PA13/PA14 are ordinary GPIO after reset, so connect-under-reset is the only way back in. |
| Per-converter `SDOUT` to `SAI_SD1`..`SD5` | A silent TDM slot **localizes to one converter**. Per-device *data* visibility already exists. |
| The converters themselves | Each is a 24-bit voltmeter on 4 channels. Per-channel DC at rest = dark current + MID offset, which finds opens, shorts and wrong `Rf` without a single probe. |

## What is missing, and why it matters

1. ~~**Nothing reports the power tree.**~~ **FIXED in part** (item 4): `TP9`/`TP10`/`TP11` put a
   meter on +24V, +5V and +3V3A. What remains true is the half that no pad can fix — the MCU's
   own ADCs were dropped and all 20 converter inputs are photodiodes, so **a live MCU still
   cannot measure one of its own rails**, and the buck's `PG` pin stays open because it cannot
   be escaped (item 2b). These pads answer a person with a meter, not firmware.
2. **The shared I2C address is worse than "no readback" — it is "no isolation."** All five
   converters sit at `1001100` (both straps to GND) **and `SHDNZ` (pin 14) is tied hard to
   `+3V3D`** on all five. There is no reset line and no shutdown line. One converter holding
   `SDA` low kills the control bus for the whole board with no way to identify or isolate it.
3. ~~**SWD is the only way in.**~~ **FIXED (item 3), and the sentence that used to be here was
   simply WRONG.** "No USART/I2C/SPI/CAN bootloader pin is brought out" was written without
   checking AN2606: the H74x bootloader's I2C2 is on PF0/PF1, which is this board's converter
   control bus and has been routed the whole time. `TP6`/`TP7` land on it and `TP8` brings out
   `BOOT0`, which is what selects the bootloader. No DFU still: the ROM USB is on OTG_FS
   (PA11/PA12) and this board uses OTG_HS through the PHY.
   ⚠ **The cost of not checking was four routing runs** spent on USART1 pads that cannot escape
   PA9/PA10, plus the pressure those pads put on the USB PHY.
4. **The diagnostic chain is strictly serial.** Power, MCU, I2C, converters, analog. A fault at
   stage N hides everything past it — and stage 1, which had zero observability when this list
   was written, now has three pads on it.

---

## The work items, highest value first

### 1. Write the bring-up procedure down  *(0 parts, 0 area, 0 signal risk)*

The cheapest item by a wide margin, and pure gain: it converts observability the board **already
has** into observability someone can actually use. Into `INSTALL_NOTES.md` or its own doc, in
order:

- read per-channel DC at rest, which finds opens, shorts, wrong `Rf`, and reads `MID` indirectly;
- a silent `SAI_SDn` slot names the converter;
- all 20 channels quiet but framed means emitters, not sensors (**and a phone camera sees the IR**);
- attach-under-reset via `TP3` before assuming a dead part.

Do this **regardless of whether any hardware item below lands.**

### 2. ~~Indicator LEDs~~ — DROPPED, and the reason is sequencing

Two LEDs were planned: a power-good indicator and a firmware heartbeat. **Both are out.**

The user's constraint was that an LED must be **off during normal operation** — an always-lit
one is an eyesore. That is satisfiable (flash ~200 ms at boot, then dark, solid only on
fault, never blinking, because a 1 Hz blink sits in the audio band beside twenty TIAs). So
the constraint was not what killed it.

**What killed it is that its value never lands where it was needed.** A virgin board has no
firmware, so the LED cannot flash. Getting firmware onto it means attaching SWD or USART —
and by then you are holding a tool that reports strictly more than one bit of light. Every
question the LED answers is already answered:

| question | what answers it without the LED |
|---|---|
| are the rails up? | TP9/TP10/TP11 and a meter (item 4, zero parts) |
| is the MCU alive? | SWD, or the USART console, or the Pi seeing a USB device |
| did firmware boot? | the Pi enumerates it — free, and the Pi is always attached |
| what fault? | the USART console says WHICH, where the LED says only THAT |

The one slice it uniquely buys is distinguishing *MCU alive but USB/ULPI broken* from *MCU
dead* without attaching a probe. ULPI is a 12-signal parallel bus and a plausible
first-article failure — but if USB will not enumerate, SWD comes out anyway, and SWD
answers it completely.

**What is given up:** a GPIO stays free, and there is no at-a-glance "it is powered" once the
board is installed in the instrument and awkward to probe. Small, and the least-noticed case.

**Not to be re-proposed** without a use that survives the sequencing argument above.

### 2b. `PG` to a bare pad — **MEASURED IMPOSSIBLE (2026-09-28), not deferred**

The buck's open-drain power-good stays wired to nothing. The pad SITE is fine (3.032 mm of
headroom, 5.9 mm away); **the PIN cannot be escaped.** U13 pad 8 is mid-row on the VQFN-HR
with the buck's own +24V pads 9 and 10 either side of the only way out, and C165's +24V land
beyond them. Mazed at 0.05 mm on every layer, with a via hop allowed:

| track width | result |
|---|---|
| 0.24, 0.20, 0.18 mm | **no path at all** (326, 495, 669 cells explored) |
| 0.16 mm | a path whose centreline comes 0.159 mm from +24V — DRC: **0.0900 mm**, 7 violations |
| 0.14 mm | a path at 0.135 mm — worse |

A 0.127 mm track needs 0.191 mm of centreline clearance and the widest corridor out of that
pin is 0.159. **There is no width that fits**, and a via-in-pad is no better: a 0.6 mm annulus
does not fit between 0.5 mm pitch pads either. So this is a placement or part-choice question,
and a debug pad does not get to move the buck.

⚠ **`verify_path.py` said ALL CLEAR on a path DRC then rejected**, and the reason is worth
keeping: its reported gap is centreline-to-obstacle and does **not** subtract the track's own
half-width, so it has to be given `rule + w/2`, not the rule. That is why its default is 0.26
for a 0.25 mm track. Given 0.127 it passes everything by 0.08 mm too much.

### 3. A second way in — **DONE (2026-09-28), and not the way this item was written**

`TP6` I2C2 SDA, `TP7` I2C2 SCL, `TP8` BOOT0. Three paste-free pads, no parts, no new copper.

**The instruction to "verify the pin numbers and the AN2606 H743 interface table" was the whole
item, and doing it changed the answer.** AN2606 Rev 61 Table 113, for STM32H74xxx: USART1 on
PA9/PA10 **or PB14/PB15**, USART2 on PA2/PA3, USART3 on PB10/PB11, I2C1 on PB6/PB9, **I2C2 on
PF1 (SCL) / PF0 (SDA)**, I2C3 on PA8/PC9, four SPIs, FDCAN1 on PH13/PH14, DFU on PA11/PA12.

**I2C2's bootloader pins are PF0/PF1 — this board's converter control bus.** It was already
routed to all five converters before any of this started, so the second way in needed no escape,
no route and no area: two pads on copper that already exists. The bootloader answers at
`0b1001110` (0x4E) and the converters at `0b1001100` (0x4C), so nothing has to be isolated and
the bus does not have to be free — I2C is multi-slave and only one device is addressed.

**The USART1 pads on PA9/PA10 were designed, sited and searched first, and they cannot be
built.** Those pins sit mid-row on the LQFP176's east face: the maze router explores 65 cells
out of the pad and finds every lane walled by the escape fan, which is the verdict the
autorouter reached four times in its own way. The lesson is the cheap one — **read the
interface table before routing to it.**

This still **reverses the original "BOOT0 is deliberately not brought out" decision, and
correctly**: that decision was conditional on no bootloader interface existing, and one does.
Without `TP8` the I2C2 pads lead nowhere.

⚠ **Untested silicon-side.** The pins, the address and the protocol (AN4221, not AN3155) are
read out of the application notes; the board is confirmed to wire PF0/PF1 to nothing but the
converter bus and these two pads. Prove it on the first article while SWD still works.

### 4. Rail test pads: `+24V`, `+5V`, `+3V3A` — **DONE (2026-09-28)**

`TP9`, `TP10`, `TP11`. Paste-free, BOM-free, pick-and-place-free. Each sits ON its own rail's
copper, so not one millimetre of track was added; headroom over the 0.127 rule is 4.747, 1.214
and 1.956 mm. No pad on `MID` (see item 6) and none on `+3V3D`, which already has `TP5`.

**They only work because they are placed AFTER routing.** The same three pads, in the DSN, cost
a net in four consecutive runs — always at the USB PHY, once on a rail whose own pad had been
REMOVED. See `post_route_refs` in `elec/optical.py`: layout skips them, `route.py` drops them in
after the session import, and DRC still checks every clearance. Sites are searched rather than
chosen, by `scratchpad/padsite.py`: a clear circle that already overlaps its own net's copper and
lies outside every courtyard, because a pad under a part is legal and unprobeable.

### 5. Heartbeat LED on a spare GPIO  *(2x 0402, digital corner)*

The difference between *"board is dead"* and *"board runs, USB doesn't"* without a debugger. The
LQFP176 has ample deliberately-unconnected IO; pick a pin **already adjacent to free routing** so
it costs no haul. **Constraint, written into firmware:** hold it steady or PWM at 10 kHz or above
— never blink it in the audio band while capturing.

### 6. Converter isolation — **BUILT (2026-09-28): a pull-up per cell, no shared net**

`Rs11`..`Rs51`, one 10k per converter, `SHDNZ` to its own IOVDD. Ground `Rs<k>1` pad 1 and that
converter alone drops off the control bus; with the per-device `SDOUT` lines already present
that is complete localization, which is the strongest of the four options this item listed.

**The question this item said everything hinged on — can a pad or a strap escape near pins
14-16 — is answered YES**, and the measurement is worth keeping:

| what was tried | result |
|---|---|
| maze pin 14 → the next cell's pin 14, 0.26 mm track | no path (19 cells explored) |
| the same at **0.20 mm** | **21.5 mm and 2 vias** |
| an 0402's site, modelled as its circumscribed CIRCLE | 0.090 mm of headroom, take it or leave it |
| the same site modelled as a **RECTANGLE** | **(-3.462, +3.50) in cell frame, legal in all five cells at 0.510 mm** |

**Per-cell pull-up, not a shared `SHDNZ` spine**, and the honest reason is not the first one I
gave. I argued the spine's **8 new vias through In1** — the analog reference plane, 0 cuts and a
0.266 mm thinnest web — were the deciding cost; the per-cell version needs **5**, which is better
and not decisively so. The real argument is the other one: the spine wanted **~86 mm of digital
line** down the converter column, and this is two short stubs inside each cell (2.4 mm for
`SHDNZ`, 7.3 mm for `+3V3D` with one via).

**The plane was measured before and after**, since five new vias north of the border is exactly
the kind of change that quietly degrades something nobody checks. At the via's first position it
left a **0.160 mm** web where the board documents 0.266 — `check_north_si` still passed, and a
halved web is still a halved web. Moving the via 0.10 mm out along its own diagonal puts the
thinnest web back at **0.266 mm**, i.e. exactly where it was: 138 foreign vias against 139,
0 cuts either way.

**No pad of its own.** A 1.0 mm pad does fit — searched, (-3.810, +6.950), 0.348 mm of headroom
— but it lands 3.45 mm from the resistor and needs its own stub to reach the net: ~4 mm more
copper per cell in the analog strip, 20 mm over five. The resistor's own land is the access
point instead, and the honest cost is that grounding it is a solder-iron action rather than a
probe action. That is acceptable for a deliberate last-resort step in a way it would not be for
a rail reading during normal bring-up.

**Both stubs are placed after routing**, like the bring-up pads, and the resistors are too: a
part the router never sees cannot cost it a net, and a site verified clear on the finished board
is as safe for an 0402 as it is for a bare pad. The fab still builds them — it builds from the
board.

#### Three things this cost, all of them mechanism rather than design

1. **The old `SHDNZ` channel had to go, and it fought back twice.** It carried pin 14 to IOVDD,
   so with the pull-up in the way it feeds nothing — but left in place its head via went
   dangling, `tidy_router_vias` removed it, and that orphaned the B.Cu leg as **ten unconnected
   `+3V3D` items**. Attaching a repair track to keep the via alive was worse: the via then sat
   in **the only escape from pin 14** and produced five `SHDNZ`-to-`+3V3D` shorts. No track
   width clears a 0.6 mm via whose centre is 0.383 mm off the line.
2. **The FOOT via is not the head via.** `_v3_trunk`'s B.Cu spine lands on exactly that point in
   every cell, so it is how each converter's IOVDD reaches the digital rail. It was removed with
   the head for one edit — which would have disconnected all five supplies — and caught by
   reading `_v3_trunk`, not by any check.
3. **The second stub has to be searched against the first.** Mazed independently the two cross:
   the router cannot see copper that is not laid yet. `lay.py` puts the first one down and the
   second is searched against a board carrying it.

**Status, 2026-09-28: items 1, 3 and 4 are IN, on a board at 0 unconnected / 0 violations.
Item 2 is dropped on merit, 2b is measured impossible, 5 is dropped with 2, and item 6 is the
only one left — and it now has the clean baseline it was gated on, plus a way to test a change
against the finished board in two minutes rather than thirty.**

## Ordering

1. **Close `SAI_FS`** — FSYNC to all five converters, so all 20 channels are dead until it lands.
   Nothing on this list matters before it.
2. Confirm the clean baseline (audit, SI groups, `cad_geom_check`, gate).
3. Items **1-5** as one change, with its own route. None of them touches the analog region or the
   converter fan.
4. Item **6** as its own change, with its own route and its own before/after SI comparison.
