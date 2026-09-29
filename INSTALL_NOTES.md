# Installation notes

Raw material for the eventual **installation document**. Record here every step an
assembler needs that the CAD can't show — an order, a compound, a setting, a check.
The final document will be written from these notes, so each note says what to do,
where it applies, which part names it touches (as `build.py` / the assembly names
them), and **why**. The why is what lets the final document be reordered or trimmed
safely.

Group notes by subassembly. Add to the end of a group; don't renumber old notes.

---

## Knee levers and foot pedals (feel cartridges)

Every knee lever and foot pedal carries two identical cartridges: MAIN and
HALF-STOP. Hardware per cartridge: one Ø10 × 30 die spring, two M4 heat-set
inserts, two M4 × 10 cup set screws (TENSION and POSITION), and two M3 DIN 9021
washers (the spring seat, and the position stop in the housing). See `BOM.md` and
`knee_lever.py` (`feel_dummies`).

### KL-1 — Threadlock the POSITION set screws

- **Where:** `<lane>_position_setscrew`, the upper of the two set screws in each
  cartridge's back wall. Both lanes (`main_`, `half_stop_`), on every knee lever
  and pedal.
- **What:** a reusable, **plastic-safe** thread locker: **Vibra-Tite VC-3**, or an
  equivalent pre-applied nylon-patch set screw. Apply it to the screw's threads,
  then thread the screw into the cartridge's insert **before** the cartridge goes
  into its housing pocket. The screw's socket end must face out of the cartridge's
  back face.
- **Why:** this screw is the cartridge's X stop: its protrusion sets where the
  follower meets the lever, which is the rest bias on MAIN and the engagement angle
  on HALF-STOP. The HALF-STOP cartridge carries **no load at rest**, because its
  follower is off the lobe until 15°. So nothing clamps its position screw, and
  vibration can walk it and slowly move the engagement point. VC-3 resists that
  while staying adjustable: the 2.0 hex key still turns it through the Ø3.2 hole in
  the housing's back face.
- **Don't** use an anaerobic threadlocker (the Loctite 2xx family) here. The
  insert is brass, but any liquid that wicks onto the printed PETG-GF / PCTG can
  stress-craze it.
- **Not needed** on the TENSION screw: the spring loads it permanently, and that
  friction holds it.

## Guide rods go in BEFORE the optical pickup board

- **Do:** seat all five near-row guide rods (strings 1, 3, 5, 7, 9) in their endplate
  bores before the optical board is fitted.
- **Why:** the board is an O rather than a C -- its sensing strip runs +X across the
  endplate block to give the digital nets a path that does not cross the analog strip --
  and that band passes straight over the near-row bores. The rods themselves never touch
  it: they top out at z 2.80, and the board's underside is at 9.53, so there is 6.73 mm
  of air between them. What the band covers is the MOUTH each rod is dropped through.
- **The alternative was measured and is worse.** Ø3.9 access holes in the band let the
  rods go in afterwards, and they neck it to 1.40 mm at five points -- about three traces
  past each rod. Fitting the rods first buys the band its full 5.35 mm for its whole
  length, which is most of the reason the band exists.
- **Not an issue for the far row** (strings 2, 4, 6, 8, 10, at x +20.0): the board does
  not reach them.

## Optical board first power-up (bring-up order)

The board's diagnostic chain is **strictly serial**: power, MCU, I2C, converter framing,
analog, emitters, USB. A fault at any stage hides everything past it, so **work these in
order** and do not skip ahead -- a "dead analog channel" at stage 5 is meaningless if
stage 4 never framed. `docs/optical-bringup-diagnostics.md` is the companion: what the
board can and cannot observe, and the pads that would widen it.

### The pads, and what each one is for

| pad | net | what it answers |
|---|---|---|
| `TP1` `TP2` `TP3` `TP4` `TP5` | SWDIO, SWCLK, NRST, GND, +3V3D | the debugger |
| `TP6` `TP7` | I2C2 SDA, I2C2 SCL | **the ROM bootloader, when SWD will not attach** |
| `TP8` | BOOT0 | selects that bootloader; hold it at +3V3D through reset |
| `TP9` `TP10` `TP11` | +24V, +5V, +3V3A | a meter on each rail, without probing a 0402 |

All eleven are bare copper: no paste, no component, and not in the BOM or the
pick-and-place. `TP6`/`TP7` are 1.0 mm, the rest 1.5 mm.

**There is a second way in, and it was on the board before the pads were.** There is no
DFU -- the ROM bootloader's USB is on OTG_FS and this board uses OTG_HS through the PHY --
but AN2606 Rev 61 Table 113 puts the H74x bootloader's **I2C2 interface on PF1 (SCL) and
PF0 (SDA)**, which is exactly the bus this board already runs to all five converters.

- Pull **`TP8` (BOOT0) to +3V3D** (`TP5` is right there) and reset. The ROM bootloader
  then listens on every interface it has, I2C2 among them.
- Talk to it at **slave address `0b1001110` (0x4E)**, 7-bit, up to 400 kHz. **The
  converters are at `0b1001100` (0x4C)**, so they cannot answer for the bootloader and it
  cannot answer for them -- nothing has to be disconnected first.
- The protocol is **AN4221** (I2C protocol used in the STM32 bootloader), not the AN3155
  USART one. A Pi is the obvious master and this instrument already has one; an
  STLINK-V3 in bridge mode is the bench alternative.
- **Take BOOT0 back to GND afterwards.** R30 is a 10k pull-down, so removing the jumper is
  enough -- but a jumper left on means a board that never runs its own firmware again.

⚠ **This is untested silicon-side.** The pins, the address and the protocol are read out of
AN2606/AN4221 and the board is confirmed to wire PF0/PF1 to nothing but the converter bus
and these pads. Nobody has yet driven this bootloader on this board, so prove it on the
first article while SWD still works -- not on the board whose SWD has failed.

### 0. Before applying power

- **Measure each rail to GND with a meter, board unpowered:** `+24V`, `+5V`, `+3V3D`,
  `+3V3A`. A near-zero reading is an assembly short; find it now rather than with 24 V
  behind it.
- **Current-limit the bench supply.** The board's normal draw is ~0.3 A and up, so a
  ~0.6 A limit still lets it run while stopping a short from cooking anything.

### 1. Power tree

Apply 24 V at `J2`. Then confirm, in order: `+5V` out of the buck (U13), then `+3V3D` and
`+3V3A` out of the LDOs, then `PHY_1V8`.

**`TP9` is +24V, `TP10` is +5V, `TP11` is +3V3A** -- put the meter there rather than on a
0402. There is no pad on `+3V3D` because `TP5` already is one, and none on `MID`, which is
the reference all twenty TIAs sit on.

> **What is still blind here.** There is no status LED, and the buck's `PG` (power-good)
> pin stays unconnected -- not by choice: pad 8 is mid-row on the VQFN-HR between the
> buck's own +24V pads, and no track of any width escapes it legally (measured; see the
> `BUCK_PG_NC` note in `elec/optical.py`). And because the MCU's own ADCs were dropped and
> all 20 converter inputs are photodiodes, **a running MCU still cannot measure one of its
> own rails** -- the pads are for a meter, not for firmware.

### 2. Is the MCU alive?

Attach SWD on `TP1`/`TP2`/`TP4`. **Use connect-under-reset via `TP3`** -- PA13/PA14 are
ordinary GPIO after reset, so any firmware that reconfigures them takes SWD away, and
under-reset is the only way back. If it will not attach: check the crystal (`OSC_IN`/
`OSC_OUT`), the `VCAP1`/`VCAP2` core-regulator capacitors, and that `NRST` is released.

### 3. I2C to the converters

All five converters answer at **one address, `1001100`**, on I2C2 (`PF0` SDA, `PF1` SCL)
-- the same bus `TP6`/`TP7` land on, so a scope or a Pi can sit on it without soldering.

> **Read this before you interpret a NACK.** The five open-drain ACKs are wired together,
> so an ACK means *at least one* part answered and a NACK means *at least one* is missing
> -- **there is no way to tell which** from the bus alone.

**But a converter CAN now be taken off the bus, one at a time.** `SHDNZ` is no longer tied
hard high: each converter has its own 10k pull-up, `Rs11`..`Rs51` (U14..U18 in order), sitting
about 2 mm from pin 14 in its own cell.

- **Ground pad 1 of `Rs<k>1`** -- the pad on the converter side, not the rail side -- and that
  converter alone goes into shutdown and lets go of `SDA`/`SCL`.
- So the stuck-bus case is diagnosable by elimination: ground them one at a time until the bus
  comes back, and the one that freed it is the fault. Five tries, worst case.
- **This is a solder-iron action, not a probe action.** The land is 0.54 x 0.64 mm in a dense
  cell -- tack a wire to it. It is deliberately not a 1.5 mm pad: a pad of its own would have
  needed 4 mm of extra copper per cell inside the analog strip, and keeping copper out of there
  is the whole reason the pull-up is per-cell instead of one shared shutdown net.
- ⚠ **The firmware rule is unchanged.** A 10k pull-up leaves the part out of shutdown as IOVDD
  rises, exactly as the hard tie did, so firmware must still issue the software reset (P0_R1
  `SW_RESET`) over the I2C broadcast once both rails are up, before configuring.

### 4. Converter framing (the stage that names a part)

Bring up SAI with `SAI_SCK` (BCLK) and `SAI_FS` (FSYNC) running, and check the DMA is
moving TDM frames.

**This is where per-device visibility finally exists:** each converter drives its own
`SDOUT` into its own line, `SAI_SD1`..`SD5`. **A silent slot names its converter** --
U14 to U18 in order. That is the one localization the board gives for free, and it is why
stage 3's ambiguity is survivable.

### 5. Analog at rest -- the converters are the instrument

With framing up, read **per-channel DC on all 20 channels with the emitters off**. Each
should sit at `MID` plus the photodiode's dark current through `Rf`. No probe is needed and
none should be used: the converters are 24-bit voltmeters already wired to every node worth
measuring.

- at or near a rail -> that TIA's input is open, or `Rf` is wrong
- exactly at `MID`, unmoving -> dead or shorted photodiode
- all four channels of one quad wrong -> that converter or its `+3V3A` feed, not the sensors

**This also reads `MID` indirectly**, as the common rest level of all 20 channels -- which is
why no test pad goes on `MID`. It is the reference all 20 TIAs sit on, so anything coupled
into it lands on **every channel at once**, and calibration cannot tell it from signal.

**Record these 20 values.** They are both the diagnostic baseline and the at-rest
calibration the lock-in needs.

### 6. Emitters -- the one end-to-end test

`LED_GATE` (PB3, through Q1 to `LED_ROW`) switches **all ten emitters together**. Toggle it
and watch the 20 channels from stage 5 move:

- **all 20 shift** -> the whole chain works, sensor to converter
- **all 20 unchanged** -> emitter side: Q1, `LED_ROW`, the current set. Not the sensors
- **one quad unchanged** -> that converter or its supply
- **one channel unchanged** -> that photodiode or its TIA

The emitters are infrared, so there is nothing to see by eye. A phone camera **may** show
them as a faint violet glow -- front cameras more often than rear ones, which filter IR
harder -- so treat it as a quick hint, never as evidence they are off.

### 7. USB to the Pi

Enumerate over `J1`. The path is 20 channels -> 5 converters -> SAI TDM -> H743 -> ULPI PHY
-> USB-C, carrying the audio plus MIDI from on-chip pitch detection. If it does not
enumerate, SWD is the only way to inspect it, and the only way to reflash.

### 8. Dress the LED strip cable around the nut height-adjust block

The six-conductor lead from the Pi cap's `J3` to LED section 0's `J1` runs 171 mm along the
keyhead, and the model draws it as a STRAIGHT LINE through the nut height-adjust block
(y -38.91..33.20). That is a modelling artefact, not a routing instruction: **dress it around
the block during assembly**, on whichever side the harness falls, and clip it clear of the ten
slide inserts so nothing bears on the height screws.

WHY IT IS NOT MODELLED AS A DRESSED CABLE -- the same reason the pickup lead gives one function
away in src/wiring.py: modelling a service loop "would only invent a shape nobody has to build
to". The straight line is honest about the ENDPOINTS, which are what the build has to match.

AND WHY THERE IS NO CHANNEL FOR IT. Measured, 2026-09-29: a channel at the cable's own envelope
would pass through ALL TEN nut slide inserts (~594 mm3 of heat-set brass, the height adjustment
for every string). Going round the block is no better -- every x from -613 to -634 and every z
from -56 to -18 still crosses keyhead_endplate, 57..539 mm3. There is nowhere for a machined
route to go, which is exactly why this is an assembly step instead.
