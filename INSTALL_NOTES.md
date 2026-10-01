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
inserts, two M4 × 10 button-head screws (TENSION and POSITION), and two M3 DIN 9021
washers (the spring seat, and the position stop in the housing). Everything here
turns on the 2.5 mm hex key. See `BOM.md` and
`knee_lever.py` (`feel_dummies`).

### KL-1 — Threadlock the POSITION screws

- **Where:** `<lane>_position_screw`, the upper of the two screws in each
  cartridge's back wall. Both lanes (`main_`, `half_stop_`), on every knee lever
  and pedal.
- **What:** a reusable, **plastic-safe** thread locker: **Vibra-Tite VC-3**, or an
  equivalent pre-applied nylon-patch screw. Apply it to the screw's threads,
  then thread the screw into the cartridge's insert **before** the cartridge goes
  into its housing pocket (see KL-3). The head faces out of the cartridge's back
  face.
- **Why:** this screw is the cartridge's X stop: how far its head stands off the
  cartridge sets where the follower meets the lever, which is the rest bias on MAIN
  and the engagement angle on HALF-STOP. The HALF-STOP cartridge carries **no load
  at rest**, because its follower is off the lobe until 15°. So nothing clamps its
  position screw, and vibration can walk it and slowly move the engagement point.
  VC-3 resists that while staying adjustable: the 2.5 hex key still turns it
  through the key way in the housing's back face.
- **Don't** use an anaerobic threadlocker (the Loctite 2xx family) here. The
  insert is brass, but any liquid that wicks onto the printed PETG-GF / PCTG can
  stress-craze it.
- **Not needed** on the TENSION screw: the spring loads it permanently, and that
  friction holds it.

### KL-3 — Cartridge order: washer, position screw, cartridge, then the tension screw

- **Where:** each feel cartridge and its housing pocket, every knee lever and pedal.
- **Do, in this order:**
  1. **Position washer first.** Push the 2.5 key in through the small (Ø3.4) key way
     in the housing's back face until it shows in the pocket, hang the washer on it,
     and draw the key back: the washer rides it down into the recess at the back of
     the pocket. It cannot be fitted once the cartridge is in.
  2. **Position screw into the cartridge**, upper insert, head out (KL-1). Leave the
     head about 1.6 mm off the cartridge's back face for a first setting. Its head
     is too big for the key way, so it also has to be in before the cartridge.
  3. **Slide the cartridge in** from the front until the position head lands on the
     washer.
  4. **Tension screw last**, from behind, through the large (Ø8.4) way in the back
     face into the lower insert. Run it in until its end just meets the spring's
     seat washer; that is zero preload.
- **Why:** the position head sits in a recess in the housing's rear wall with the
  washer under it, so both are trapped by the cartridge. The tension screw is the
  only one of the four parts that can go in, or come out, with the lever assembled.
- **Range:** the tension screw has **4.2 mm** of travel, from its end flush with the
  cartridge wall to its head down on the cartridge. Stop when the head lands; forcing
  it further only strips the insert.

### KL-4 — The axle's end screw: seat it on the AXLE, and hold the lever while you do

- **Where:** `kl_axle_screw` / `kl_axle_washer` (and `kv_`, and each pedal's), in the
  −Y end of the printed axle. One M4 × 10 button head and one **Ø9** M4 washer.
- **Do:** after the axle is slid through bearing / lever / bearing and its flange is
  home on the +Y bearing, put the washer on the screw and drive it into the bore in
  the axle's −Y tip. **Hold the lever arm**, not the magnet cap, to take the torque.
  The first fit forms the thread in the plastic: firm, steady turns, and stop when the
  washer is tight on the axle's end.
- **Check:** the washer should NOT be clamped on the bearing. The axle's tip stands
  0.2 mm past the bearing's inner race, so a correctly seated washer leaves the axle
  about that much end float, and the lever still swings freely. If the lever stiffens
  as the screw comes tight, the axle is not fully home at the +Y end.
- **Why:** this is the only thing that stops the axle sliding back out the way it
  went in. It replaces the M2 grub that used to go through the lever's hub.
- **Don't** substitute a larger washer: anything over Ø9.6 reaches the bearing's
  shield and rubs.

## Belt clamps: splice each one with the nut ON THE CEILING, 5 mm off the pulley

- **Where:** every string's belt-tension clamp (`belt_tensioner_*`), all ten belts.
- **Do:** run the string's nut UP until it stops against the endplate ceiling (the hard top
  stop, and the restringing position). Then splice the clamp onto the belt **5 mm from the
  pulley it has just been travelling toward**. From there the nut's whole travel carries the
  clamp away from that pulley and stops it about 5 mm short of the other one on string 10.
- **Why:** the clamp is part of the belt and moves 14 mm for every 1 mm of nut travel. The
  nut's travel (7.97 mm, ceiling to floor) is sized so the clamp on the SHORTEST belt
  (string 10) uses 111.6 of the 121.6 mm it has between pulleys. Those two 5 mm gaps are the
  whole margin, and where the clamp sits is set here, by hand. Splice it at the wrong end, or
  with the nut somewhere in mid-travel, and it reaches a pulley before the nut reaches its stop.
- **Strings 1-8 are forgiving** (their belts are longer; string 9 has about 15 mm per end),
  but use the same rule everywhere so there is one procedure.
- **Restringing:** always wrap a new string with the nut on the ceiling. Pull it as tight by
  hand as you can: every tenth of open tension taken up by hand is 0.4 mm of travel kept
  for raising pitch. A string wrapped slack and left to break in reaches about 3.4 semitones
  above open; re-wrapped after break-in it reaches 4 with room over.

## Leadscrew nuts: LOOK at the top edge of each string ear hole

- **Where:** every H-nut (`nut_*`), the ear the string passes through (the ear WITHOUT the
  guide rod), top face.
- **Do:** run a fingernail round that hole's top edge. If it is smooth, do nothing. Only if
  it catches (a raised burr from drilling) knock the burr off with a twist of a larger drill
  bit held in the fingers. This is an inspection, not a machining step.
- **Why:** the ball end seats centred under a Ø3.5 hole and the string leans 9-13° toward the
  bridge bearing, so a string heavier than about .030 bears on the hole's top rim on the
  bearing side. That is an ordinary break point (every ball-end anchor has one), but a burr
  there would cut a wound string.

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

## Control boards first power-up (motor_ctrl, output_panel, lever sensors)

Companion: `docs/board-bringup-diagnostics.md` (what each step can and cannot tell you, and
the tools — all listed in `BOM.md` Tools). **No LEDs are used for diagnosis on any board.**
Like the optical board, the chain is serial: work in order, one new thing per step.

1. **Bare board on the bench supply, 24 V with the current limit at ~100 mA.** Read the
   current at rest, then each rail with a meter. A supply that hits its limit is a short —
   stop there. Do this for every first-article board, before it ever meets the instrument.
2. **`motor_ctrl` alone.** WCH-LinkE attaches → flash → the board enumerates on the Pi's USB.
   Its CAN error counters should read "no acknowledge" on both buses. That is CORRECT: nothing
   else is on a bus yet.
3. **Add one CAN node at a time.** The counters go clean when the first node acknowledges.
   After each addition, power off and measure **60 Ω between CAN_H and CAN_L** on that bus —
   120 Ω means one terminator is missing or the bus is open, 40 Ω means a third is fitted.
4. **`output_panel`.** First the USB tree as the Pi sees it (hub, then MCU, then the optical
   board behind it). Then the audio loopback: the TS lead from the output jack back into the
   pickup terminal tests ADC, Pi, DAC, relay and buffer in one measurement.
   If the loopback is silent, meter the output panel's rails at the parts that already sit on
   them — no test pads exist for these: `+5V` at **FB1 pin 2**, `DAC_VNEG` at **C33 pin 1**
   (expect −3.3 V; if it is missing the DAC is silent with every digital signal correct),
   `DAC_LDOO` at **C30 pin 1** (1.8 V), `ADC_VREF` at **C19 pin 1** (2.5 V).
5. **Lever and pedal sensors.** Each board reports its ID; the magnet field status is in
   range; moving a lever moves its own ID and no other. A sensor that never answers on I2C:
   check its `MODE` strap (R5) is to +3V3 — to ground it is in ABZ mode and silent.

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

## The flat Pi: seat it, then clamp it with the spacer (2026-09-29)

The Pi is **not** held by a screw head on its laminate any more. It is held by a printed
**spacer** (`pi_spacer`) that bridges from the board's edge out to a screw 12.50 mm away,
because no position beside the board had room for that screw's anchor below the floor — the
levers' mortise/tenon joinery is under it.

1. **Drop the Pi into its cradle, straight down.** The four corner pads carry it; its
   underside never touches the floor slab (it has solder tails and SMD parts on the back).
   The walls locate it in plane; the **+X end is open** — that is the I/O end, and it is also
   the only way the board goes in or out.
2. **Lay the spacer across the board's +Y edge.** It is stepped, and the step tells you which
   way round it goes: the **thin end (2.40 mm) lies on the board's top face**, the **thick end
   (4.00 mm) sits outboard on the chassis boss**. The step's vertical face butts the board's
   edge — if it will not sit flat, it is on backwards or the board is not fully down.
3. **One M4 × 10 button head, 2.5 mm hex**, through the spacer into the insert in the boss.
   Same screw and same key as everywhere else; no new SKU and no second length.
4. **Do not overtighten.** The spacer clamps 50 mm² of the laminate's edge (against the
   1.30 mm arc a bare head used to reach), so it does not need much to hold — and what it is
   resisting is the board lifting, not sliding: the walls already stop that.

⚠ **Removal order:** the spacer comes off before the Pi, and the Pi comes out along **+X**.

## Leg blind-mate boards (src/leg_pogo.py) — ORDER MATTERS

The male board goes into the tenon's end **as a unit, from the mating face, and it
only fits one way round**. The order below is not a preference; steps 2 and 4 cannot
be swapped.

1. **Heat-set the coil first**, on `coil_mandrel`, before anything is crimped — the
   coil has to pass over a bare wire end.

   **The harness is not a jacketed cable, so LAY IT UP as one** (this was an open
   item until 2026-09-23). Twist each pair at its own short lay — CAN_H with CAN_L,
   and 5V with GND — then twist the **two pairs around each other** at roughly five
   times that lay. That is what a 4-core cable is, and it is what makes the bundle
   self-binding at the Ø2.4 the bores are cut for (`leg_pogo.HARNESS_D`). Nothing is
   added over the coil, which matters: the coil lives in a Ø24.7 bore with the
   stretched turns already near the floor, and any sleeve or spiral wrap would have
   been spent out of that clearance.

   **Then cap the lay at each crimped end with a 6 mm adhesive-lined heat-shrink
   collar**, behind the fan-out, threaded on BEFORE the contacts are crimped. A lay
   only unwinds from a FREE END, and after step 2 the only free ends are at the two
   connectors — capture those and the twist cannot back off anywhere along the run.
   A collar out in the coiled section would have been the obvious place to put one
   and is the wrong one twice over: at the leg's lowest position only about 5 mm of
   straight run survives at each end of the coil, and a collar caught on the barrel
   sets as a stiff spot in a part whose whole job is to flex.

   **Splay during the set is the mandrel's job, not the binding's** — `coil_mandrel`
   is two pieces for exactly this reason, and the Ø23.0-bore sleeve holds every turn
   through the heat and the cool (see its BOM row).
2. **Thread the harness down the leg, then crimp.** Both ends are crimped AFTER
   threading: a fitted PHR-4 will not pass the bores it has to travel. The body
   adapter's channel is a TUNNEL on a single diagonal, not an open groove you can
   lay a wire into from above, so it is threaded like every other bore -- which is
   why it can run buried, under the body tenons instead of through one of them.
   It is SQUARE, 2.4 x 2.4 over 35 mm: feed the four conductors through it one at a
   time rather than as a bundle, and they will lie two and two in the corners.
3. **Plug the PHR-4 onto the male board** while the board is still in your hand. The
   PH's room is swept the whole depth of the slot, so the board can go in with its
   plug already on — and that is the easy way round, because the plug's mouth faces
   up the leg and is hard to reach once the board is seated.
4. **Slide the board in** until it seats. Watch the pins: the free tips rest 2.5
   INSIDE the tenon's face, so nothing should ever be proud. (It was 4.1 before the
   female board was recessed into its host — `leg_pogo.TIP_REST` is the live number.)
5. **Fit the M4 × 20 sideways** through the recess in one tenon flat, across the
   board, into the insert in the opposite flat. That is what holds the board.
6. **The female board DROPS INTO A POCKET** — in the mortise roof (top joint) or the
   bar's floor (bottom) — and finishes flush with that face. It goes in one way only,
   and the pocket's four walls set its orientation before the screw is anywhere near
   it. Seat it, check it is flat, then the M4 × 8 straight down into its insert. The
   screw's ONLY job is to stop it lifting back out along the install direction; if you
   find yourself using it to pull the board into position, the pocket is wrong.
7. **Heat-set the female's insert BEFORE step 6.** It presses in from the
   mortise side, down the same axis the screw later uses, through a bored channel sized
   to the insert. That channel notches the pocket's wall beside the screw -- that is
   deliberate, not damage.

**Why step 3 works at all:** the PH stands 5.5 off the board's face, and cutting its
pocket only where it ends up left it gouging up to 396 mm³ of the tenon on the way
past. The pocket is now swept along the whole install stroke. The part reads CLEAN at
rest and CLEAN fully withdrawn, which is exactly why no static check caught it —
`leg_pogo` now sweeps the stroke instead.

## Latches — ALL ON ONE SIDE

Every latch in the instrument faces the same way: the leg-to-body-adapter latch
(`leg_latch.BUTTON_SIDE`) and the pedal bar's collar yoke (`bar_latch.PAD_SIDE`), and
the two are asserted equal so they cannot drift apart. Both constants are the single
place each module says which way round it is.

- **Where:** `leg_latch`, `bar_latch`. Currently **+Y**.
- **Why that side:** the latches are not worked in playing position. They are worked with
  the instrument **upside down in its case**, taking parts off for storage, and the plan
  is for the **pedal bar to be the near side** as you do that — you approach from the
  playing side, grab the instrument, flip it, and it goes into the case bar-first. The
  old arrangement put the bar on the far side, which meant walking round the instrument
  before the flip. One side for every latch is what makes the pass work without
  reaching over.
- **Why it is not just ergonomics:** the latch and the leg harness share the tenon. Each
  takes one of the tenon's Y middles (`leg_pogo.DROP_OFF`, `ROUTE_OFF`), so moving a
  latch moves the harness with it. They cannot be changed independently.
- ⚠ **Watch the bar's seat stop on a first print.** With the pad on +Y the collar's rail
  slots open at the bed, so their closed end — the face the collar seats against — is a
  14.3 mm² ceiling 31.45 in from the bed. It is left flat because the collar must seat on
  a face, not a ridge. If it droops, the collar seats slightly deep.

---

## Knee lever wiring (bus B)

Bus B daisy-chains through every lever board: in on J1 ways 1–4, out on 5–8. A lever
is **not** at a fixed station — its tenons drop into the chassis bottom's mortise grid
(`D.LEVER_PITCH`, 10.4 mm) so it steps along X, and the rib mortise lets it slide to
any knee depth over 197.5 mm in Y.

### KL-2 — Cut the lever segments long and tie the hank to the lever

- **Where:** the cable keeper on each lever housing's **+Y cheek**
  (`knee_lever.cable_keeper`, on both `kl_housing` and `kv_housing`) — the side the plug
  leaves the board on — **flush with the housing's back end**, the screw end.
- **What:** cut each lever-to-lever segment to the length in `build.cable_cut_list()`,
  coil the excess and **press it into the keeper** past the nub.
- **It comes back out.** The keeper is an open pocket whose mouth (2.4 mm) is narrower
  than the cable, not a closed loop: a closed loop can only be threaded before the
  connectors are crimped on and never released. Lever the coil out with a screwdriver
  tip under it.
- **Why:** moving a lever is a thing you do to the *instrument*, not to the loom. The
  harness is the crimped, tooled, contacts-ordered part; it should survive a
  re-placement. Tying the hank to the **lever** rather than to the chassis is what makes
  that work at any station — the stow point travels with the lever.
- **Sized for a tweak, not a relocation** (user: two grid steps either way, plus knee
  depth). Two neighbours moving 2 steps apart each is 41.6 mm. Moving a lever the length
  of the mortise needs a new segment, and always did.
- **Not on the back face.** That was the first attempt and it was wrong (user): the back
  face is how the 2.0 key reaches both feel screws, and a hank tied across it would cover
  them for the life of the instrument.
- **Do this before** the lever goes up into the chassis — easier with it in your hand.

---

## Pedal bar wiring (bus B)

The bar's wiring trough carries bus B from the −X (wired) leg tower to the five
pedal sensor boards, daisy-chained: leg → pedal 1 → … → pedal 5. Each board's J1 is
an 8-way PH, bus **in** on ways 1–4 and **out** on 5–8, so the chain runs through
the board. Pedal 5 is the far end of the bus: it is the one pedal that closes its
termination jumper.

### PB-1 — Route each pedal segment through its spur

- **Where:** the spur at each pedal station — the short passage from the board bay up
  into the bar's wiring trough (`foot_pedal.cut_wire_ways`).
- **What:** plug the segment onto J1 in the bay, bring the wire up through the spur into
  the trough, and run it along to the next station.
- **Why:** the bay is a closed pocket otherwise. The 2026-09-21 board re-spin moved J1,
  and the bay follows the posed hardware, so it stopped reaching the trough and left each
  plug sealed in. Nothing caught it — a cavity that doesn't reach another cavity isn't an
  overlap.
- **No slack cleat here**, unlike the knee levers: a pedal's X station is printed into the
  bar, so nothing about it moves. Cut these segments to fit.
- **Order:** wire the trough **before** the lid slides in. The lid is a full-length sliding
  dovetail entering from the −X end; once it's on, nothing in the trough is reachable.
- **Leave the last one out:** pedal 5 has no onward segment. Its J1 out-half is the bus end.

---

## Bus B into the body (the wiring port)

Everything on bus B lives **below** the chassis floor and the motor controller lives
above it. The knee levers hang under the body (LKL's J1 sits at z −95, the floor slab is
−81.9 to −71.4) and the pedal bar's four conductors come up the −X/+Y leg and out of the
body adapter onto the **underside**. So bus B crosses the floor exactly once, through one
port, and both cables make that crossing.

### BB-1 — The port

- **Where:** in the floor slab on **mortise station 3's own slot line** (x −597.3), 7.2
  wide like the station itself, running 21.6 along Y from y 17.95 down to −3.65.
- **Why there:** stations 1–3 are the ones the −X/+Y leg's foot tenons take, so no lever
  can stand there whatever the port does; station 4 is the first one a lever can use.
  Putting the port on station 3's centre at station 3's width leaves the **grid's own
  wall** (3.20) to station 4 — there is no clearance to pick and nothing to keep in step
  if the pitch moves.
- **It passes a made-up connector**, not just bare wire: 21.6 × 7.2 takes the 8-way PH
  head (19.9 × 5.5) with 0.85 a side. Build the harness on the bench, crimp it, and feed
  the head through — unlike the leg's own channel, which is a 2.4 tunnel and has to be
  threaded bare.

### BB-2 — The pedal cable

One cable from the female pogo board's ZR, down the leg, out of the body adapter's
channel, across ~32 mm of the instrument's **underside**, up through the port, and onto
J2 ways 1–4. 28 AWG the whole way — the leg's 2.4 channel is what sets the gauge, not the
26 AWG the lever segments use between boards. **There is no connector at the adapter's
face**, so the run is continuous; the only exposed length is the underside crossing.

### BB-3 — The lever chain's head

Four new conductors from J2 ways 5–8 to **LKL's J1 ways 1–4** — the end of the lever
chain the controller feeds. Out of LKL along its plug's axis past the housing, along
under the instrument, up through the port beside the pedal cable, then inboard to the
controller.

- **Route it −Y first, then inboard.** Motor 0 fills x −583.6..−541.3 over y −41.2..28.8
  at this height. The run stays outboard of the bank until it is past it in Y.
- **Order:** both cables want to be in before the tray goes in over them.

> ⚠ **The controller has ONE 8-way J2, not two jacks.** Both cables land on it — pedals
> on ways 1–4, levers on 5–8 — which is the mid-bus pass-through its netlist describes,
> but it is one PHR-8 housing, so the two cables have to share it: eight contacts, four
> from each, crimped into one shell. Two separate 4-way jacks would make each cable its
> own assembly and let either be unplugged alone. That is a motor-controller decision,
> not a mechanical one.

## The deck's swappable bands — 2026-09-29

**There are TWO filler bands and they are the same part.** Slide the pickup piece to the
slot position you want and drop the two fillers into whichever slots it leaves; either
band goes in either slot, and there is no set of spares to keep track of. That is what
the fillers losing their fret lines bought — a marked band fits one slot only.

The deck is therefore marked to **fret 24** (the octave quad, on the mid panel). Frets
25–30 are unmarked, because they fall in the region that moves.

## The UI station (deck mid panel) — 2026-09-28

The display, the encoder and the board that carries them are ONE assembly, and the
**clamp plate, two spigots and one M4×12** hold the whole of it to the deck panel. Plastic takes
every other direction: the display's pocket walls and the window ledge, the board's
cradle wall and its four bearings. **The station is built onto the panel with the panel
off the instrument**, and the panel then goes on with all of it attached.

**Building the station onto the panel** (panel off the instrument, face down)

1. Heat-set an M4 insert into the boss on the panel's underside, from the boss's open
   end. It is the only insert on the panel.
2. Solder the 1×20 **female** socket (KH-2.54FH-1X20P-H8.5) to the BACK of the Newhaven
   module, opening facing away from the glass. The module ships with plated holes and no
   header — Newhaven's own drawing only recommends one — so this is the one hand-solder
   step in the station, and it is on a PCB, which the project's no-solder rule allows.
3. Drop the module face-first into the pocket. It seats against the 1.6 mm window ledge.
4. Plug the UI board onto the module's socket and lower it onto the deck's four bearing
   posts — two of which carry **spigots** that pass through the board's two Ø4.6 locating
   holes. Those spigots are what hold the station in X, Y and rotation.
   **Press the module up against the ledge as you do it.** The header stack is
   deliberately long, so the socket has 0.6 mm still to go before it bottoms; the module
   must end up flat on the ledge, not hanging on its pins.
5. Plug the 14-way ribbon onto J2 at the board's −X edge. **Do this now** — it is much
   harder once the clamp is on.

   **The ribbon is creased twice, 45° each, and the creases are not optional.** The run
   is flat all the way — width across the instrument, thickness vertical, because there
   is only 10.70 mm of headroom under the deck and 17.78 mm of ribbon on edge does not
   fit — so both of its 90° turns are in the cable's own plane, and flat cable turns in
   plane by being folded. Fold them before the panel goes on, with the red stripe on the
   outside of each turn, and the cable lies flat the whole way; fold them after and you
   are creasing a cable that is already plugged in at both ends. 500 mm of cable against
   a 449.6 mm run is what pays for getting a fold wrong once.
6. Offer the clamp plate up under the board. The two spigots enter its sockets, its
   reliefs go over the through-hole tails, and its arm runs +Y under the display so the
   two posts on the crossbar land on the module's back at the far mounting-hole row —
   that is what stops the screen drooping. Run the single **M4×12** button screw up
   through the middle of it into the insert. The screw only holds Z; the plastic holds
   everything else.
7. Press the printed knob onto the switch's shaft through the hole in the deck. **The
   shaft is a D** — Ø2.5 milled to 1.79 across — and so is the knob's bore. The cap is
   unindexed, so any clocking is fine; it only has to go on square.

**Onto the instrument**

8. Slide the mid panel on, station and all.
9. Plug the ribbon's other end onto the Pi's GPIO header. ⚠ **WHICH SEVEN PIN-PAIRS IS
   NOT DECIDED YET** — see the UI board section of `BOM.md`. No block of seven on the
   Pi's header carries all fourteen of these ways, so this step is waiting on either an
   adapter or a shorter signal list, and a socket pushed onto pins 1–14 would land on the
   motor controller's 5 V feed.
10. Slide the keyhead panel on.
11. Fit the keyhead endplate.

Out is the reverse, and nothing has to be reached blind: every step that touches a
connector happens with the panel off or with the keyhead end open.

**Two things to confirm against the real parts before printing a panel:**

* **The clamp's arm bears on the module's back** at the two far mounting-hole pads,
  because that is the one region of a module's back guaranteed to be clear of
  components. Newhaven's rear view shows parts and their drawing does not dimension
  them — check it.
* **The right-angle ribbon header's height.** `src/board_geom.HEIGHT` carries 10.0 mm for
  it as an ESTIMATE (ZHOURI publish no drawing through LCSC) and there is 11.40 mm
  between the board's top face and the deck's underside.


## Fret lighting boards (2026-09-30, seam joint built the same day)

Two boards, one per deck panel, ONE cable: it lands on the keyhead board, and the mid board
is fed across the panel seam by six tip-to-tip pogo pins (`docs/fret-led.md` §9.1f).

1. **Attach each LED board to its own panel, off the instrument** -- the retainer strips
   and the one M4, below. The board must not move in X once seated.
2. **Slide the mid panel on** (it goes first and furthest, butting the bridge endplate).
3. **Slide the keyhead panel on until the two panels BUTT.** The pogos meet in the last
   ~3.4 mm before the panels touch: from first contact to flush they compress 1.70 each
   and push back with about **1.2 kg** in all. Flush IS the preload -- if the panels meet,
   the joint is made (§9.1e). A visible seam gap means it is not.
4. **Plug the one cable into the keyhead board's J1** -- its plug faces -X at the keyhead
   cluster, in the bay at the board's far end.
5. **Fit the keyhead endplate**, which holds the panels butted against the pogos' push.

⚠ **Never force the panels closer than flush.** The pogos bottom at 5.70 and are designed to
sit at 6.30 when the panels touch, only 0.60 above that limit.

⚠ **Every part on these boards stands inside a light cell except the bay's.** Do not add
anything tall to the fret field without asking what it does to that cell's floor bounce.


## Foot lighting strip (2026-09-30)

Two boards of one design, end to end in a channel on the chassis bottom, firing down
through the light window. **It goes in before the −X endplate.**

1. **Join the two boards with the SH jumper**, outside the instrument: the −X board's J2
   to the +X board's J1. Attach the −X board's J1 cable at the same time.
2. **Assemble the chassis, leaving the −X endplate off.**
3. **Slide the pair in from −X, far board first**, until the −X board's end is flush with
   the window's −X end. The channel holds it on five faces; nothing screws down.
4. **Run the J1 cable to the Pi daughter board** and plug it.
5. **Fit the −X endplate**, which closes the channel and is what stops the strip sliding
   back out.

⚠ **The +X board's J2 is a spare** — it exists because both boards are the same part
number. Leave it unplugged.

⚠ **Nothing on these boards may stand more than 3.40 mm off the PCB.** The channel's
trough is 1.90 (the LED sets it) with a 1.50 relief under the component lane, and the
board is installed face DOWN. That is why the connectors are JST SH rather than the PH
used everywhere else on the instrument.


## Fret lighting boards (2026-09-30)

Each fret board is retained by two RETAINER STRIPS, not by tabs and not by the screw
alone. Assemble the panel **face down on the bench**, before it goes on the instrument.

1. **Lay the panel deck-face down.** The comb points up at you.
2. **Drop the board into the comb**, LEDs into their cells. Gravity seats it against the
   cell walls -- that is the +Z datum and it needs no force.
3. **Slide a retainer strip along each long edge**, into the groove in the edge wall. They
   go in along X from either end and trap the board's underside.
4. **Fit the M4** through the board into the deck boss at the bay end.
5. Turn the panel over and install it.

⚠ **THE BOARD MUST NOT BE SLID ALONG X ONCE IT IS SEATED.** An LED and a cell wall share
the same Z band, so any X motion drives every LED into a wall -- fret 24's cell allows the
LED 1.27 mm and that is the whole budget. The strips move; the board does not. This is why
the earlier lift-and-shift tab scheme was retracted (docs/fret-led.md 8.6).

⚠ **THE MID PANEL TAKES ONE STRIP, THE KEYHEAD PANEL TWO.** The CAN trunk runs diagonally
under the boards and leaves only 1.00 mm under the mid panel's -Y edge, which is not enough
for a groove (docs/fret-led.md 8.7). Mid's single strip goes on its **+Y** edge. That is
sufficient on its own -- it turns the 206 mm cantilever into the board's 70.4 mm width and
deflection goes as the fourth power, so the unsupported edge droops about 15 um.

All three strips are the same section, 1.60 thick, cut to their panel's board length.

## Set the pickup's retention screw on the bench, before the pickup piece goes in

The pickup is locked to its height plate by ONE horizontal M4 x 12 button head at the plate's
-Y end (2.5 mm key). Its head faces -Y and is reached through the key slot in the pickup
piece's -Y skirt, on the screw's axis. Once the piece is in the deck that slot faces the
chassis, so: seat the pickup against the plate's +Y wall, run the screw in until its tip
bears on the pickup, and only then slide the piece in. Height and tilt (the three jack
screws, from above) stay adjustable afterwards; this one does not.
