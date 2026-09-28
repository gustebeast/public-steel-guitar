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

The only instrument on the board is **SWD** (`TP1` SWDIO, `TP2` SWCLK, `TP3` NRST,
`TP4` GND, `TP5` +3V3D). **There is no DFU fallback** -- the ROM bootloader's USB is on
OTG_FS and this board uses OTG_HS through the PHY -- so if SWD will not attach there is
currently no second way in.

### 0. Before applying power

- **Measure each rail to GND with a meter, board unpowered:** `+24V`, `+5V`, `+3V3D`,
  `+3V3A`. A near-zero reading is an assembly short; find it now rather than with 24 V
  behind it.
- **Current-limit the bench supply.** The board's normal draw is ~0.3 A and up, so a
  ~0.6 A limit still lets it run while stopping a short from cooking anything.

### 1. Power tree

Apply 24 V at `J2`. Then confirm, in order: `+5V` out of the buck (U13), then `+3V3D` and
`+3V3A` out of the LDOs, then `PHY_1V8`.

> **This stage is the board's blind spot.** There is no status LED, no rail test pads, and
> the buck's `PG` (power-good) pin is unconnected -- so every reading here means probing a
> 0402 beside 0.5 mm-pitch parts. And because the MCU's own ADCs were dropped and all 20
> converter inputs are photodiodes, **a running MCU cannot measure a single one of its own
> rails.** Items 2 and 4 of the diagnostics doc exist to fix exactly this.

### 2. Is the MCU alive?

Attach SWD on `TP1`/`TP2`/`TP4`. **Use connect-under-reset via `TP3`** -- PA13/PA14 are
ordinary GPIO after reset, so any firmware that reconfigures them takes SWD away, and
under-reset is the only way back. If it will not attach: check the crystal (`OSC_IN`/
`OSC_OUT`), the `VCAP1`/`VCAP2` core-regulator capacitors, and that `NRST` is released.

### 3. I2C to the converters

All five converters answer at **one address, `1001100`**, on I2C2 (`PF0` SDA, `PF1` SCL).

> **Read this before you interpret a NACK.** The five open-drain ACKs are wired together,
> so an ACK means *at least one* part answered and a NACK means *at least one* is missing
> -- **there is no way to tell which.** And `SHDNZ` (pin 14) is tied hard to +3V3D on all
> five with no reset line, so **no converter can be removed from the bus.** If one part
> holds `SDA` low the whole control bus is dead, the only recovery is cutting power to the
> board, and the only diagnosis is a scope on `SDA`/`SCL`. This is the single largest
> diagnostic gap on the board; item 6 of the diagnostics doc is the fix.

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
