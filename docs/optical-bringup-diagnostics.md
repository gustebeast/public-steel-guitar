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

1. **Nothing reports the power tree.** No status LED, no rail pads, and the buck's **`PG` pin is
   open** (`BUCK_PG_NC`). The MCU's own ADCs were dropped and all 20 converter inputs are
   photodiodes, so **a live MCU cannot measure any of its own rails.**
2. **The shared I2C address is worse than "no readback" — it is "no isolation."** All five
   converters sit at `1001100` (both straps to GND) **and `SHDNZ` (pin 14) is tied hard to
   `+3V3D`** on all five. There is no reset line and no shutdown line. One converter holding
   `SDA` low kills the control bus for the whole board with no way to identify or isolate it.
3. **SWD is the only way in.** No DFU: the ROM bootloader's USB is on OTG_FS (PA11/PA12) and this
   board uses OTG_HS through the PHY; no USART/I2C/SPI/CAN bootloader pin is brought out.
   `BOOT0` was deliberately left off on the grounds that it "only helps if a ROM bootloader
   interface exists, and none does." **Item 3 inverts that premise.**
4. **The diagnostic chain is strictly serial.** Power, MCU, I2C, converters, analog. A fault at
   stage N hides everything past it, and stage 1 is the stage with zero observability.

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

### 2b. `PG` to a bare pad *(0 parts)*

The buck's open-drain power-good is still wired to nothing (`BUCK_PG_NC`). A pad on it costs
no part and lets a meter ask the buck its own opinion of the 5 V rail, rather than inferring
it. Worth folding into the next pad revision.

### 3. USART1 bootloader pads + `BOOT0`  *(0 parts, 3 bare pads, no signal risk)*

Today, if SWD will not attach, **the board is a brick with no second opinion.** USART1 (PA9/PA10
— *verify the pin numbers and the AN2606 H743 interface table*) appears unused and is a ROM
bootloader interface. Three more paste-free pads — TX, RX, `BOOT0` — give a completely
independent way in. This **reverses the original "BOOT0 is deliberately not brought out"
decision, and correctly**: that decision was conditional on no bootloader interface existing.

### 4. Rail test pads: `+24V`, `+5V`, `+3V3A`  *(0 parts, 3 bare pads)*

Paste-free, BOM-free, pick-and-place-free — pure area. Place each over **existing** copper for its
rail so it costs nothing to route.

- `+3V3A`: fine as a *supply* pad (heavily bypassed, not a signal reference) **if placed well away
  from the summing nodes**.
- `+24V`: keep clear of fine-pitch parts — a slipped probe there is destructive.
- **No `MID` pad** (see item 6).

### 5. Heartbeat LED on a spare GPIO  *(2x 0402, digital corner)*

The difference between *"board is dead"* and *"board runs, USB doesn't"* without a debugger. The
LQFP176 has ample deliberately-unconnected IO; pick a pin **already adjacent to free routing** so
it costs no haul. **Constraint, written into firmware:** hold it steady or PWM at 10 kHz or above
— never blink it in the audio band while capturing.

### 6. Converter isolation — the big one, and it hinges on one measurement

Item 2's logic and the `SHDNZ` fix both live on the **same local `+3V3D` node** at pins 14-16,
because `SHDNZ` (14) is *already* strapped to `+3V3D` inside every cell and `ADDR1` (15) is its
immediate neighbour at 0.5 mm pitch. **The whole converter-diagnostics story reduces to: can a pad
or a short strap escape near pins 14-16 inside a cell?** These cells are tight — they had to drop
four 100 nF caps each to route at all — so this needs measuring, not assuming.

Options, best first:

| Option | Cost | Gets you |
|---|---|---|
| **`ADDR1` to `+3V3D`** on some converters | Possibly **0 parts** (jumper to the neighbouring pad's net) | Two address groups. One bit of localization, and the two groups can be written differently to A/B a suspected fault. |
| **Per-cell `SHDNZ` pull-up + pad** | 5x 0402 + 5 pads, all **local** | **Full per-device isolation.** Ground one pad and that converter drops out; with the per-device `SDOUT` lines already present, this is complete localization. The strongest outcome. |
| **One shared `SHDNZ` net + pull-up + one pad** | 1 part, but **one long net across the array** | Block-level reset only. The fallback if per-cell area isn't there. |
| **`SHDNZ` onto an MCU GPIO** | 1 long net through the converter fan | Firmware-driven reset. **Highest routing risk — see below.** |

Full per-device *readback* needs four distinct addresses (2 bits gives only 4 combos for 5 parts)
**plus a second bus for the fifth**, which is what was tried and abandoned: the `ADDR0`/`ADDR1`
straps were among the last 14 nets that would not route, because those pins sit between the I2C
pins on the part's routing side. The escape is the hard part, **not** the destination — `GND` was
reachable only because the EP sits directly underneath.

> **Sequencing.** Item 6 runs a net straight through the converter fan, the same region where
> `SAI_FS` is *still* unconnected. Nothing in item 6 is attempted until `SAI_FS` closes and the
> board is confirmed at 0 unconnected / 0 violations, so the diagnostic change is measured
> against a known-good baseline instead of muddying the FSYNC hunt.

---

## Ordering

1. **Close `SAI_FS`** — FSYNC to all five converters, so all 20 channels are dead until it lands.
   Nothing on this list matters before it.
2. Confirm the clean baseline (audit, SI groups, `cad_geom_check`, gate).
3. Items **1-5** as one change, with its own route. None of them touches the analog region or the
   converter fan.
4. Item **6** as its own change, with its own route and its own before/after SI comparison.
