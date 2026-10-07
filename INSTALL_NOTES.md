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
  nut's travel (8.35 mm, ceiling to floor) has the clamp on the SHORTEST belt (string 10)
  use 116.9 of the 133.8 mm it has between pulleys. The 5 mm gap at this end is yours to set, and where the clamp sits is set here, by hand. Splice it at the wrong end, or
  with the nut somewhere in mid-travel, and it reaches a pulley before the nut reaches its stop.
- **Strings 1-8 are forgiving** (their belts are longer; string 9 has about 15 mm per end),
  but use the same rule everywhere so there is one procedure.
- **Restringing:** always wrap a new string with the nut on the ceiling. Pull it as tight by
  hand as you can: every tenth of open tension taken up by hand is 0.4 mm of travel kept
  for raising pitch. A string wrapped slack and left to break in reaches about 3.4 semitones
  above open; re-wrapped after break-in it reaches 4 with room over.
- **Which run, and which end:** odd strings (near row, the high belt plane) take the clamp on
  the **upper** run of the belt, 5 mm off the **screw** pulley; even strings (far row) on the
  **lower** run, 5 mm off the **motor** pulley. That is the same rule as above, spelled out:
  with the nut on the ceiling those are the pulleys each clamp has been travelling toward.
  The assembly model is drawn in exactly this state. **Check it on the first string:** run
  the nut down a little and the clamp must move AWAY from the pulley it was set beside. If
  it moves toward it, stop: the clamp belongs at the other end of that run.
- **This assumes a RIGHT-HAND leadscrew**, which is the stock part and what the BOM asks for.
  A left-hand screw reverses every belt: odd strings would start at the motor end and even
  strings at the screw end, and strings 2, 4, 6 and 8 would then sit inside the 16-20 mm
  beside their screw pulleys where the clamp meets the next string's pulley. The model
  follows `dimensions.SCREW_HAND`; if the hand ever changes, change it there, rebuild, and
  re-run `tools/clamp_range.py` before trusting any of this.
- **Why the run and the end matter:** neighbouring clamps pass close near the screws, and a
  clamp on the wrong run, or started from the wrong end, can meet its neighbour or a
  neighbour's pulley (`tools/clamp_range.py`, `docs/belt-clamp-travel.md`).
- **Which way round:** the belt's teeth face the INSIDE of its loop and the clamp's ribs are
  on that side, so the key channel in half A ends up on the OUTSIDE of the loop. If the
  channel faces into the loop, the clamp is upside down.
- **Fitting it:** push one cut end of the belt SIDEWAYS into half A's slot until it is in
  past the slot's mouth and against the slot's inner end, teeth between the ribs. Do the
  same with the other end in half B: its slot opens on the opposite face. Drop the M3
  insert into the side pocket in half B. Slide the halves together end to end: each half's
  channel rail runs over the other half's slot mouth and hooks its two lips, which is what
  keeps the belt in and the slot from opening. Then run the M3 × 12 in through half A.
- **Tensioning:** the screw's head faces the belt, so use the BALL END of the 2.5 mm key,
  laid down the channel in the back of half A at about 25° to the belt. The halves start
  4 mm apart and each turn closes them 0.5 mm. If they meet before the belt is tight,
  move one end of the belt one tooth (2 mm) further into its slot and start again.

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
  and that band passes straight over the near-row bores. The rods are 30 mm stock pins
  and stand 5.5 mm short of the board when seated (z 6.65 against 12.20), so the board
  no longer rests on them -- but it is still their lid, and once it is on there is no
  way to reach a rod. Press every rod down until it stops on its socket floor first.
- **Check the fit before pressing any:** try one pin through a nut's ear. It must slide
  freely. The pin is 2.502-2.508 and the ear hole is unmeasured; if it binds, ream the
  ears to 2.6 before assembly.
- **The alternative was measured and is worse.** Ø3.9 access holes in the band let the
  rods go in afterwards, and they neck it to 1.40 mm at five points -- about three traces
  past each rod. Fitting the rods first buys the band its full 5.35 mm for its whole
  length, which is most of the reason the band exists.
- **Not an issue for the far row** (strings 2, 4, 6, 8, 10, at x +20.0): the board does
  not reach them.

## Motor tees: ONE switch ON, nine OFF

Every motor tee carries a 120 ohm terminator behind a small slide switch marked TERM
(SW1, in the strip behind the connectors). The boards arrive with it OFF. Slide it to ON
on **one** tee only: the last one on the trunk, furthest along the cable from the motor
board. A toothpick or a small screwdriver moves it; the switch body prints ON at the end
that closes it. No solder, and it can be reached with every plug in.

Check before the first power-up: 60 ohm between CAN_H and CAN_L on any tee's tails with
the power off. 120 means no tee is ON; 40 means two are, or a motor's own terminator
jumper is fitted (leave those off).

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

### KL-3 — Right-hand levers (LKR, RKR): the board goes in turned over

- **What:** the same sensor board as every other lever, lowered into the right-hand
  housing's grooves **turned over about the axle**: connector toward +X, the board's
  long end UP. There is no mirrored board. The right-hand housing (`knee_housing_r`) is
  its own printed part and its grooves, floor and plug tunnel are cut for the board this
  way round; it does not fit the other way.
- **No shim** in a right-hand housing: turned over, the board's top edge already stands
  0.4 mm under the chassis. Left-hand and vertical levers keep theirs.
- **Way 1 changes ends with the board.** On LKL, VKL and RKL way 1 (GND in) is the TOP
  contact of J1 and way 8 the bottom; on LKR and RKR way 1 is the BOTTOM contact. The
  crimped harness is the same either way — a PH housing only plugs in one way round — so
  this matters only when probing J1 with a meter.

---

## Pedal bar wiring (bus B)

The bar's wiring trough carries bus B from the −X (wired) leg tower to the five
pedal sensor boards, daisy-chained: leg → pedal 1 → … → pedal 5. Each board's J1 is
an 8-way PH, bus **in** on ways 1–4 and **out** on 5–8, so the chain runs through
the board. Pedal 5 is the far end of the bus: it is the one pedal whose terminator
switch is ON.

### PB-0 — Set the terminator switch BEFORE the board goes into its housing

Every lever and pedal sensor board carries a 120 ohm terminator behind a small slide
switch marked TERM (SW1, in the corner below the sensor chip) -- the same switch as the
motor tees'. It faces the magnet, so it cannot be reached once the board is in its
housing. Bus B has two far ends: the last pedal (pedal 5) and the last knee lever on the
lever chain. On those two boards slide the switch to ON (printed on its body); on the
other nine leave it off. No solder.

To check with a meter: with the board unplugged, measure between CAN_H and CAN_L on J1
(ways 3 and 4). 120 ohm is ON; open circuit is OFF. With the whole bus plugged up and
the power off, any board reads 60 ohm when exactly two are ON.

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

### PB-2 — The trough is closed at every pedal except along its floor

- **What:** each pedal's board shim stands from the board's edge to the lid, so with the
  cradle under it it is a plate across the trough at every station. The only way past is
  **under the shim, on the trough floor, against the lid side** — a gap 3 mm high and
  5 mm wide. Lay the four conductors there two deep (the model draws them: GND and
  CAN_H on the floor, +5 V and CAN_L on top of them).
- **Order:** board in, plugs on, wires laid on the floor past the station, **then** the
  shim down its grooves over them, then the lid. A shim that will not seat is sitting on
  a wire.
- **At the plug:** J1 points down into the bay and there is 2.5 mm under it. The wires
  turn out of the plug along the floor inside the plug tunnel (6 mm wide) — arriving
  four on the −X side of the pin row, departing four on the +X side.
- **Way 1** (GND in) is the contact nearest the **player-side face** of the bar (−Y);
  way 8 is nearest the lid.
- **From the leg:** the four wires out of the bar's blind-mate board (ZH plug) come
  along the chamber at mid-height and drop to the floor once they are over the trough.

---

## Bus B under the body (no port)

Everything on bus B lives **below** the chassis floor, and so does the connector it lands
on: the motor controller stands through the floor behind string 1's motor, and its J2
hangs below the slab where a hand reaches it from outside. So bus B **never crosses the
floor**. (There was a 7.2 × 21.6 port through the slab at x −597.3 for it; it went on
2026-10-02, when string 1's motor moved over that spot.)

### BB-2 — The pedal cable

One cable from the female pogo board's ZR, down the leg, out of the body adapter's
channel, along the instrument's **underside**, and up into **J2** (4-way PH, the one
nearer the -Y rail) from below. 28 AWG the whole way — the leg's 2.4 channel is what sets
the gauge, not the 26 AWG the lever segments use between boards. **There is no connector
at the adapter's face**, so the run is continuous; the only exposed length is the
underside crossing. It passes J6 on the endplate side of it (5 mm toward the keyhead), so
the lever chain's plug can come out without moving it.

### BB-3 — The lever chain's head

Four conductors from **J6** (4-way PH, 16 mm +Y of J2) to **LKL's J1 ways 1–4** — the end
of the lever chain the controller feeds. A flat four-way: out of LKL along its plug's
axis, level under the floor to below J6, and up into it. Way 1 at the lever is way 1 at
the controller, like every other lead.

J2 and J6 are two separate 4-way housings (they were one 8-way until 2026-10-03), so
either cable unplugs on its own. Both take the same plug and nothing is damaged by
swapping them — the board passes the bus straight through — but put them back as built.

## The lights lead leaves the motor board through a slot in the floor

The motor board hangs through the chassis floor, and J7 (lights, 4-way XH) is low on it:
its ways 3 and 4, the two button wires, are **below the floor's top**. A slot in the
floor beside the plug lets those two wires out. Plug J7 with the four wires already
dressed toward the Pi (+X), and press the two lower ones into the slot before the board
is pushed home; a wire trapped between the plug's face and the floor keeps the board from
seating.

## The power button's wiring rides on cables that already exist

The power button is on the UI board, and the switch it controls is on the output panel
(it switches the 24 V inlet). No new cable was added; its two wires travel on three
existing ones:

| cable | from | to | ways |
|---|---|---|---|
| UI ribbon, 16-way IDC | UI board J2 | Pi cap J5 | ways 15 / 16 are the button |
| lights lead, 4-way XH | Pi cap J4 | motor board J7 | `GND, 24V, button, button` |
| power link, **6-way** XH | motor board J3 | output panel J10 | `GND, 24V, button, button, 24V, GND` |

* All three are straight leads: way 1 at one end is way 1 at the other.
* The power link is the only 6-way XH in the instrument, so it cannot go in a wrong socket.
* **Plug and unplug the power link with the supply's plug out of the panel.** The motor
  board's 5 V converter has ceramic capacitors on its input, and a lead that is already
  live rings them above the supply for a few microseconds as it makes contact. The board
  is built to take it (the converter's own fuse and the rail clamp hold the worst case to
  31 V at a part rated 38), but it is a stress with no purpose: power down first.
* The 4-way XH plugs on the motor board (J1 bus A, J7 lights) and on the Pi cap (J4 lights,
  J3 / J6 light drops) fit each other's sockets. None of the swaps damages anything; what
  each one does is in the table in the next section. Each socket's way names are printed
  beside it.
* With the button out the instrument is off and draws 2.55 mA from the supply (through the
  button's own pull-up). The supply brick can stay plugged in.
* **It fails ON.** The button says "off" by shorting its wire to ground, so with the UI
  ribbon or either lead unplugged, or a wire broken, the instrument runs whenever the
  supply is plugged in and the button does nothing. An instrument that will not turn OFF
  has an open in this chain.
* The output panel's jumper JP1 picks which of the button's two throws is used. It is made
  bridged 1-2 (off with the button out), from the switch maker's drawing. If a real switch
  works the other way round, cut 1-2 and bridge 2-3.

## The optical board's USB plug goes in cable-DOWN

The lead from the output panel's J4 is a flat ribbon with the same right-angle USB-C at
both ends. At the optical board (J1) plug it with the ribbon pointing **down**, into the
conduit behind the board; the endplate is notched under the plug for it. USB-C goes in
either way up, so if the ribbon points at the strings, turn the plug over.

* Under J1, fold the ribbon once at 45 degrees so it runs toward the keyhead standing on
  edge. On edge is the only way it leaves the endplate beside the rail.
* The optical board's 24 V pair goes into the conduit FIRST: it crosses under the ribbon
  in the trench in the conduit's floor.
* At the output panel (J4) the plug goes in with the ribbon pointing **up**. Lay the ribbon
  over away from the board on top of the plug's boot, so it rises OUTSIDE the loop of the
  24 V pair, and fold it once toward the rail.
* The lead is about 160 mm longer than the route. Run the spare along the rail past J4
  and double it back.

## Every JST lead: one way order, and the family tells you the voltage

The rule (user, 2026-10-04; the tuples are in `elec/harness.py`):

* **XH (2.5 mm, white, the bigger one) carries 24 V. PH (2.0 mm) carries 5 V.** An XH plug
  does not enter a PH socket or the other way round, so 24 V cannot reach a 5 V contact.
* **Ways are always `GND, power, data, data`.** A 6-way adds `power, GND` on ways 5 and 6,
  so it reads the same from either end. A lead with no data leaves ways 3 and 4 empty.
* Every lead is straight: way 1 at one end is way 1 at the other.

| lead | family, ways | from | to | ways |
|---|---|---|---|---|
| motor trunk head | XH 4 | output panel J7 | east tee trunk | `GND, 24V, -, -` |
| power link | XH 6 | output panel J10 | motor board J3 | `GND, 24V, button, button, 24V, GND` |
| optical feed | XH 2 / XH 4 | output panel J9 | optical board J2 | `GND, 24V` (`-, -`) |
| bus A head and every motor drop | XH 4 | motor board J1, tee J2 | tees, motors | `GND, 24V, CAN_H, CAN_L` |
| tee trunk | XH 8 | tee J1 | next tee | the 4-way order twice, in then out |
| lights lead | XH 4 | motor board J7 | Pi cap J4 | `GND, 24V, button, button` |
| fret light drop | XH 4 | Pi cap J3 | fret board J1 | `GND, 24V, SCK, SDT` |
| foot light drop | XH 4 | Pi cap J6 | foot board J1 | `GND, 24V, SCK, SDT` |
| Pi 5 V | PH 6 | motor board J5 | Pi cap J2 | `GND, 5V, -, -, 5V, GND` |
| USB to the Pi | PH 4 | motor board J4 | Pi USB-A | `GND, VBUS (unused), D-, D+` |
| bus B drops | PH 4 | motor board J2 / J6, leg boards | pedal and lever chains | `GND, 5V, CAN_H, CAN_L` |
| lever / pedal trunk | PH 8 | sensor board J1 | next sensor board | the 4-way order twice |

**The USB lead is the one lead whose far end has somebody else's numbering.** A USB-A plug's
own contacts are 1 VBUS, 2 D-, 3 D+, 4 GND (USB 2.0, the order the plug's maker prints);
the PH housing's ways are GND, VBUS, D-, D+. So it is NOT contact 1 to way 1:

| USB-A contact | usual wire | PH way |
|---|---|---|
| 4 GND | black | 1 |
| 1 VBUS | red | 2 (crimped or left out: the board does not connect it) |
| 2 D- | white | 3 |
| 3 D+ | green | 4 |

Wire colours are a habit, not a standard: meter each wire to its plug contact before crimping.
Crimped contact 1 to way 1, the Pi's 5 V lands on the motor board's ground.

Not JST, and not confusable with any of the above: the UI ribbon (16-way IDC), the leg
boards' ZH tail (5 V, inside the leg only), the inlet barrel jack.

### What a wrong plug does

Ground meets ground and power meets power in every case below; only ways 3 and 4 differ.
"24 V" is two nets, the trunk and the fused lighting feed; joining them through a wrong
lead bypasses the motor board's lighting fuse F3 for as long as it is plugged, and nothing
else.

**4-way XH** (five kinds of socket: CAN drop, lights, light drop, trunk head, optical inlet):

| ways 3 / 4 of the lead | meet | result |
|---|---|---|
| CAN_H, CAN_L | button lines (lights sockets) | The button lines idle at 10 V behind 9.4 k (2.6 mA at most), which the bus's 60 ohm swallows. The panel reads the line as held low: **the instrument turns off or will not turn on**, and bus A does not talk. No damage. |
| CAN_H, CAN_L | SCK, SDT at the Pi cap's J3 / J6 | The Pi's two SPI pins, each behind 68 ohm, meet the CAN pair. A 5 V CAN transceiver (the motor drivers', if they are 5 V parts -- not checked) drives CAN_H to 3.5 V typical, 4.5 V worst case, against a 3.3 V pin: up to about 9 mA into the pin's clamp, and the pin itself drives about 25 mA into the bus against its 16 mA. **A stress for as long as it is left plugged, not an over-voltage**; lights and bus A both misbehave at once. |
| CAN_H, CAN_L | SCK, SDT inputs of a fret / foot board | The LED driver's inputs see the bus's 1.5 to 3.5 V. No damage; the lights show noise. |
| button, button | SCK, SDT at the Pi cap's J3 / J6 (the plug next to its own socket) | 10 V behind 9.4 k through 68 ohm into a Pi pin: 0.7 mA into its clamp. When the Pi drives the pin low the panel reads "off": **the instrument turns itself off.** No damage. |
| button, button | SCK, SDT inputs of a fret / foot board | The same 0.7 mA at most into the LED driver's input clamps. No damage. |
| button, button | CAN_H, CAN_L | as the first row |
| SCK, SDT (a light drop, live) | CAN drop, lights socket | as the rows above, from the other side |
| anything | trunk head (panel J7) or optical inlet (J2) | Ways 3 and 4 are empty on the board: nothing. The lead is powered from the wrong 24 V point (see F3 above). |
| trunk head or optical feed lead | any socket | The lead has no wire on ways 3 and 4: nothing. |

**6-way XH**: only the power link. It enters no 4-way socket and there is no second 6-way XH.

**4-way PH** (bus B drops, the USB lead):

| lead | in | result |
|---|---|---|
| USB lead | a bus-B drop | The Pi's USB 5 V meets the bus's 5 V (the bus side is behind a 0.5 A limited switch); CAN_H / CAN_L, 0 to 3.3 V, meet the Pi's D- / D+. No damage; neither link works. |
| bus-B drop | motor board J4 (USB) | Way 2 is not connected on the board; the CAN pair meets the MCU's USB pins at 0 to 3.3 V. No damage. |

**6-way PH**: only the Pi's 5 V lead. **8-way** XH and PH: only the two trunks.

The one row worth a label is the second: a motor drop or the bus-A head plugged into a light
drop on the Pi cap. Mark the two light-drop leads at the Pi cap end.
