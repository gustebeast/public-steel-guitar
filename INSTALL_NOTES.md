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

### KL-4 — The axle stack: +Y bearing pressed, spring and −Y bearing slid in, screw fully tight

- **Where:** the horizontal knee levers (LKL, LKR, RKL, RKR; the vertical lever and the pedals
  are still the old stack: KL-4b). `kl_bearing_0/1`, the
  **preload spring** (McMaster 9714K29 wave disc spring, Ø11.7 × Ø15.4, the thin wavy steel
  ring), the two printed spacers — **`kl_spacer_sprung_n` (3.6 thick) on −Y,
  `kl_spacer_sprung` (2.0) on +Y** — `kl_axle_sprung`, and the M4 × 10 button + **Ø9**
  washer in the axle's −Y tip.
- **Do:**
  1. Press the **+Y** 688 in from the housing's +Y face until its outer race stops on the
     printed shoulder inside the seat (a light press). The inner race must still turn with
     a finger.
  2. Drop the **spring** into the **−Y** seat, flat against the shoulder at its bottom.
  3. Slide the **−Y** 688 in after it, by hand, until it rests on the spring. This seat is a
     SLIDING fit on purpose — do not press it home; the spring has to be able to move it.
  4. Put the lever in its room. Hold the 3.6 spacer against its −Y face and the 2.0 spacer
     against its +Y face, centred on the axle hole.
  5. Slide the axle in from +Y, through the +Y bearing, spacer, lever, spacer and −Y
     bearing, until its land is home on the +Y inner race.
  6. Washer on the screw, drive it into the axle's −Y tip, **holding the lever arm**, not
     the magnet cap. The first fit forms the thread. **Tighten it fully** (firm with the
     2.5 key held by its short arm): as it comes tight it pulls the −Y bearing in against
     the spring, and that is all it does to the bearings.
- **Check:** the lever swings freely with **no Y play at all** — push it ±Y and it should
  not move. The −Y bearing ends flush with the housing's −Y face, give or take the stack's
  print error.
- **Why:** the screw clamps land, inner races, spacers and lever into one turning unit. The
  spring pushes the −Y outer race outboard, which holds that unit hard against the +Y
  shoulder: zero play, at about 9 N of preload the spring sets — however tight the screw is.
  Print error in the stack (±0.15) only changes how far the spring is squeezed. The +Y
  bearing is the hard stop, so the magnet's air gap does not depend on the print. A hard
  +Y shove on the lever can squeeze the spring and move the lever toward the board by at
  most 0.6 (the air gap is 1.5); it springs straight back.
- **Don't** swap the two spacers (they only fit one way round anyway: the 3.6 one reaches
  through two shoulders), leave the spring out (the lever then floats ~0.8 in Y), or use a
  larger washer: anything over Ø9.6 reaches the bearing's shield and rubs.

### KL-4b — The OLD axle stack (vertical lever and pedals): bearings to their shoulders, spacers in, screw clamps the races

- **Where:** the vertical lever and the pedals, until they take KL-4's spring. `kl_bearing_0/1`,
  the two printed `kl_spacer`s, `kl_axle`, and the M4 × 10 button + **Ø9** washer in the
  axle's −Y tip.
- **Do:**
  1. Press each 688 in from the housing's OUTSIDE face until its outer race stops on the
     printed shoulder inside the seat. The shoulder only holds the outer race; the inner
     race must still turn with a finger.
  2. Put the lever in its room. Hold a spacer against each of its flat faces, centred
     on the axle hole (they sit inside the shoulder openings, against the inner races).
  3. Slide the axle in from +Y, through the +Y bearing, spacer, lever, spacer and −Y
     bearing, until its land is home on the +Y inner race.
  4. Washer on the screw, drive it into the axle's −Y tip. **Hold the lever arm**, not
     the magnet cap, to take the torque. The first fit forms the thread: firm, steady
     turns, and stop when the washer is tight on the −Y inner race.
- **Check:** the lever swings freely (the races turn, nothing rubs) and has no Y play
  you can feel. If it stiffens as the screw comes tight, a spacer is off-centre or a
  bearing is not home on its shoulder.
- **Why:** the screw clamps land, inner races, spacers and lever into one turning unit,
  and the two shoulders hold that unit in Y, so neither the lever nor a bearing can walk
  (and the magnet can't reach the board). The housing is not in the clamp, so a tight
  screw cannot preload the bearings. It replaces the M2 grub that used to go through
  the lever's hub.
- **Don't** substitute a larger washer: anything over Ø9.6 reaches the bearing's
  shield and rubs.

## Belt clamps: put each one together insert, screw, then B

- **Where:** every belt-tension clamp (`belt_tensioner_half_a` / `_b`), before it goes on a belt.
- **Do:** 1. drop the M3 insert into half B's side pocket (the U in its +y face), from the side,
  by hand -- it is not heat-set. 2. Drop the M3 x 12 socket head into half A from A's TOP face:
  head into the window, shank into the seat's slot. 3. Slide B onto A along the rails until the screw's tip meets B's bore, and start the
  thread with the 2.5 ball end through the key bore.
- **Why:** the screw is 15 long and A's window 6.4, so it cannot be fed in along its axis; it
  drops in sideways. Once B is on, B's rail covers the slot and A's rail covers the insert's
  pocket, so each half's rail is what keeps the other's part in.

## Belt clamps: splice each one with the nut ON THE CEILING, 5 mm off the pulley

- **Where:** every string's belt-tension clamp (`belt_tensioner_*`), all ten belts.
- **Do:** run the string's nut UP until it stops against the endplate ceiling (the hard top
  stop, and the restringing position). Then splice the clamp onto the belt **5 mm from the
  pulley it has just been travelling toward**, and within **two teeth (4 mm)** of that
  mark: the belt is cut to a tooth count, so count teeth rather than measure. From there the nut's whole travel carries the
  clamp away from that pulley and stops it about 5 mm short of the other one on string 10.
- **Why:** the clamp is part of the belt and moves 14 mm for every 1 mm of nut travel. The
  nut's travel (8.35 mm, ceiling to floor) has the clamp on the SHORTEST belt (string 10)
  use 116.9 of the 131.8 mm it has between pulleys (the clamp is 51.2 long). A clamp
  spliced two teeth past its mark still ends 6 mm short of the far pulley on string 10. The 5 mm gap at this end is yours to set, and where the clamp sits is set here, by hand. Splice it at the wrong end, or
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
- **Cut length:** each belt is cut to a TOOTH COUNT, and the build prints the ten counts
  (`src.build.geometry_report`, from `belt_tensioner.belt_fit`): 573, 553, 484, 463, 395,
  374, 305, 285, 216, 195 teeth for strings 1 to 10 (390.4 mm for string 10). Both ends are cut 0.2 mm past a
  tooth's centre, so the cut is that many pitches plus 0.4 mm, and each end goes through a
  tooth. At that count the halves stand 2 to 4 mm apart with the belt tight, which leaves
  the screw at least 2 mm more to close. ⚠ The counts are the model's: neither the pitch
  line under tension nor the choice of the longer of the two counts that fit has been
  tried on a bench.

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
  and that band passes straight over the near-row bores. The rods are Ø3.5 x 29.8 stock
  needle rollers and stand 5.75 mm short of the board when seated (z 6.45 against 12.20).
  Press every rod down until it stops on its socket floor, then drop one printed ROD PLUG
  (Ø3.2 x 5.6) down each bore on top of it -- all ten bores, both rows. The plug fills the bore
  to 0.15 under the board, so the board is what holds the rod down. A plug that stands
  proud of the endplate means its rod is not home: the board will not seat on it.
- **Ream the nut ears first:** run a 9/64" reamer (McMaster 2995A116) through BOTH ears of
  all ten H-nuts, by hand in a tap wrench, and blow the brass out. As bought the ears are
  Ø3.5 (measured 2026-10-16) -- line-to-line on a 3.490-3.500 roller, i.e. it binds or
  stick-slips. Reamed (3.572-3.576) the roller must slide through under its own weight
  with no felt play; that 0.07-0.09 clearance is 0.6-0.75 cent of backlash, which the
  firmware can take out. Ream both ears so no nut can go in the wrong way round.
- **The alternative was measured and is worse.** Ø3.9 access holes in the band let the
  rods go in afterwards, and they neck it to 1.40 mm at five points -- about three traces
  past each rod. Fitting the rods first buys the band its full 5.35 mm for its whole
  length, which is most of the reason the band exists.
- **Not an issue for the far row** (strings 2, 4, 6, 8, 10, at x +20.0): the board does
  not reach them.

## Motors: wire the screw terminals on the bench, with a 2.0 mm flat blade (2026-10-20)

The SERVO42D's power and CAN go into its OWN screw terminals, not a plug: the green 6-way on
one side of the driver (V+, GND) and the green 5-way on the other (CANH, CANL). Wires enter
from the SIDE of each block and the slotted screws are turned from the BACK. A 2.0 x 0.4 mm
flat blade fits the screw wells; a wider blade does not reach the screw. This is the one job
on the instrument the 2.5 mm key does not do (see BOM, Tools).

* Ferrule every stripped end before it goes in, and tug each one after tightening.
* The blue 4-way on the top edge carries the motor's own coil lead and comes wired from the
  factory: leave it alone. If it has been undone, the order from -X to +X (from behind,
  left to right) is red, black, blue, green.
* Fold each wire flat against the block at a right angle, right where its insulation ends
  (bare wire in the terminal, the bend at the insulation), so nothing stands past the motor's
  square. 22 AWG folds this way cleanly (user, 2026-10-20).
* Wire the motor on the bench, then lower it into its bay with the wires on. Beside each
  green block the bay's side wall is cut down below the block -- both sides and the back
  wall stand 11.2 -- so the folded wires clear it (docs/servo42d-fit.md).
* Then its tee: the seat has a 45 deg lip over the board's FAR end (the end away from the
  ear). Tilt the board, slide that edge under the lip, lay the ear down onto the post and run
  the M4 x 10 in through the ear. Dropped in flat it will not go; out, it comes ear-first.
  The lip is what stops the board's far end lifting off the motor (coupon, user 2026-10-20).

## Motors: cut each shaft to length BEFORE its pulley goes on (2026-10-29) -- HELD, DO NOT CUT YET

**HELD (lead, 2026-10-29).** The motors still stand at the 17.2 standoff, where the shaft as bought fits
and nothing needs cutting. The 15.6 cut belongs to the 12.0 standoff (branch `branner-standoff12`),
which waits on the foot-LED boards and the output board being re-placed. Cutting a shaft is
irreversible: do not cut until that lands and this note loses its HELD mark.

The SERVO42D's shaft comes 21.5 mm long off the faceplate. The instrument uses it only to the
pulley's outer face (`components.MOTOR_SHAFT_CUT_L`: 15.6 at the 12.0 standoff), and the motors sit closer to their
belts for it. Cut every motor once, on the bench, with the two-part printed jig
(`tools/motor_shaft_saw_jig.step` and `tools/motor_shaft_saw_jig_cap.step`), one Quick-Grip and
the 6927A16 hacksaw blade. It works like the leadscrew saw jig, and nothing screws into the motor.

1. Set the jig on the table near the edge, so the clamp's lower jaw reaches under it.
2. Turn the shaft by hand until its D FLAT faces straight up.
3. Drop the motor into the jig's bay: driver cover down, shaft into the U channel. It is the
   chassis bay's own shape, so it goes in only one way.
4. Push the motor forward until its faceplate sits on the wall. The cut is measured from that
   wall.
5. Drop the cap in. Its tongue lands on the flat; if it won't seat, the flat isn't up. Turn the
   shaft and try again.
6. Clamp the Quick-Grip on the cap's flat top and under the table, and squeeze. The stack is
   cap, motor, jig, table.
7. Saw down the slot. It has a wall on both sides of the blade, and its motor-side face is the
   cut line, so the stub can only come out long, never short. The offcut stays in the channel.
8. **With the cap still on**, pick every filing off the slot and the stub's end with a magnet.
   The cap closes the boss slot and the shaft channel, so this is the moment the bearing and
   the magnet gap are covered.
9. Undo the clamp, lift the cap, lift the motor out.
10. File the cut end back to `MOTOR_SHAFT_CUT_L` and square, then add a small 45° chamfer all round, so the
    pulley's bore starts on it without shaving plastic. Wipe the stub and check the faceplate
    round the boss for filings.
11. Drop in the next motor (step 2). The jig stays where it is; only the clamp comes off.

## Motors: push each pulley on to the end of the shaft's flat (2026-10-28)

* The pulley's bore is a D the whole way through: line its flat up with the shaft's flat and
  push it on until it stops. It stops where the shaft's flat ends and the round part starts,
  and that is its place -- no shim, no gauge. The cut shaft's end then sits about 0.4 inside
  the pulley's outer face.
* It seats where the flat starts, 3.5 mm off the faceplate (the bought shaft's flat is 18 mm
  of its 21.5, dimensions.MOTOR_SHAFT_FLAT_L), 1.5 short of the motor's boss. If a motor's flat differs, the pulley's place moves
  with it: measure it and the pulley gets re-drawn.

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

0. **Probe wiring, once per board.** WCH-LinkE in RISC-V mode. Four SOLDERED tails:
   SWDIO to TP1, SWCLK to TP2, GND to TP4, **reset to TP3, always**. Nothing on the
   LinkE's 5V pin, ever; nothing from its 3V3 pin to TP5 while 24 V is on (TP5 is for the
   meter). Ohm +3V3 to GND on both assembled `motor_ctrl` boards first.
1. **First power, one board at a time, down the instrument's own chain** (user,
   2026-10-13: no bench supply): the brick into `output_panel` J6, then `optical` from
   the panel's J9, `motor_ctrl` from its J10, the lever boards from `motor_ctrl` J6.
   Order, power-off meter checks and what is risked: `docs/bench-order.md`, "Power
   without a bench supply". The rest of this step is the bench-supply way, which is
   optional and safer (one XHP-4 pigtail: way 1 24 V, way 2 GND, ways 3 and 4 empty,
   polarity metered, into `motor_ctrl` J1 or `output_panel` J7).
   **`motor_ctrl` starts at 8 to 12 V, limit 50 mA** (only 3V3 exists; flash here), then
   24.0 V, then 5.02 V checked on a 10 ohm load on J5 with the limit raised to 0.3 A,
   **before the Pi is plugged in.** `output_panel` at 24.0 V, limit 250 mA. If its
   start stalled or sagged, or it was switched off and straight on again, switch off for
   2 s and start again before judging the sound: the gain pot takes its mid-scale setting
   only from a clean power-up, and can otherwise sit silent. The
   steps and the readings are in `docs/board-bringup-diagnostics.md`, "First power,
   staged". Do this for every first-article board, before it ever meets the instrument.
2. **`motor_ctrl` alone.** WCH-LinkE attaches → flash → the board enumerates on the Pi's USB.
   (The console on day one is SDI printf over the two debug wires. The first firmware
   waits 2 s at the top of `main()` and never drives PB2.)
   Its CAN error counters should read "no acknowledge" on both buses. That is CORRECT: nothing
   else is on a bus yet.
3. **Add one CAN node at a time.** The counters go clean when the first node acknowledges.
   After each addition, power off and measure **60 Ω between CAN_H and CAN_L** on that bus —
   120 Ω means one terminator is missing or the bus is open, 40 Ω means a third is fitted.
4. **`output_panel`.** Before any firmware: its hub enumerates on a PC through J3, and the
   direct path J8 to the jack plays. (No relay K1 on the board means no sound in any
   mode: bridge K1 pads 2-3 and 6-7 to go on.) Plug J4 with the power off; only the
   optical board goes there. Then the USB tree as the Pi sees it (hub, then MCU, then the optical
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
| `TP12` | PA2, USART2_TX | the debug serial output (3.3 V, transmit only), 3 mm west of the MCU |

All twelve are bare copper: no paste, no component, and not in the BOM or the
pick-and-place. `TP6`/`TP7`/`TP12` are 1.0 mm, the rest 1.5 mm.

**There is a second way in, and it was on the board before the pads were.** There is no
DFU -- the ROM bootloader's USB is on OTG_FS and this board uses OTG_HS through the PHY --
but AN2606 Rev 61 Table 113 puts the H74x bootloader's **I2C2 interface on PF1 (SCL) and
PF0 (SDA)**, which is exactly the bus this board already runs to all five converters.

- Pull **`TP8` (BOOT0) to +3V3D** (the nearest is **C106 pad 1, 2.6 mm east of TP8**: a
  3 mm wire or a solder blob. TP5 is 31 mm away) and reset. The ROM bootloader
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
- **Look for R44** (the 2512 beside J2). Unplaced, nothing comes up.
- **First power is 6.0 V at a 0.3 A limit, not 24 V**: TP10 must read 5.0 V before the
  supply goes any higher (a dry joint in the buck's feedback would otherwise put 24 V on
  the 5 V rail). Then 24.0 V: **limit 100 mA with the MCU erased, 250 mA once it is
  flashed.** Never feed the board through TP10 or TP5. The four steps are in
  `docs/optical-bringup-diagnostics.md`, "First power at 6 V, not 24 V".

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

## The Pi: what it must be told, and two checks before 5 V (2026-10-07)

`/boot/firmware/config.txt`, before the cap goes on (set the Pi up on its own supply,
with SSH or a screen: with the cap on there is no serial console):

```
[all]
dtparam=spi=on                      # SPI0, fret lights: GPIO10, GPIO11
dtoverlay=spi1-1cs                  # SPI1, display: GPIO20, GPIO21, CS on GPIO18
dtoverlay=spi5-1cs                  # SPI5, foot lights: GPIO14, GPIO15
dtoverlay=dwc2,dr_mode=peripheral   # the USB-C port is the gadget port
```

**Must NOT appear:** `enable_uart=1`, `dtoverlay=disable-bt`, `dtoverlay=miniuart-bt`
(all three put a UART on GPIO14 / 15, the foot lights' pins), `dtoverlay=spi1-2cs` or
`-3cs` (a second chip select lands on a UI switch), `dtoverlay=w1-gpio` (GPIO4 is the
display's DC line). Take `console=serial0,115200` out of `cmdline.txt`.

**If a console is ever needed with the cap on**, it borrows the foot lights' pins, so
for as long as it is wanted: the foot-light lead off J6, `dtoverlay=spi5-1cs` out,
`enable_uart=1` in. GPIO14 (TXD) is J6 way 4 and GPIO15 (RXD) is J6 way 3, each through
68 ohm, ground on way 2. **Never way 1: that is 24 V.** Afterwards put all three back.

**Then remove the Pi's own USB-C supply for good.** With the 5 V lead from the motor board
plugged into the cap, a supply (or a PC) on the Pi's USB-C feeds the whole 24 V trunk
backwards at about 4.3 V. The one lead that belongs in that port is the C-to-C from the
output panel's J2, whose VBUS goes nowhere. Tag the port; do not tape it. The cap says so
on the face you can see.

**Seating check, before 5 V.** The 40-way socket is not keyed. One row off puts 5 V on
the Pi's 3V3 rail. Look for a bare header pin at either end and along either side: there
must be none. Then meter: cap tail 6 to the Pi's USB shell reads 0 ohm; cap tail 1 to
tail 2 does not.

## The flat Pi: lead in first, drop it in, one M3 through its own hole (2026-10-29)

The Pi is held by **one M3 × 12 socket head through its own mounting hole** (the +X, −Y one:
the hole nearest the USB/Ethernet end on the HDMI side), into a heat-set M3 insert in the
chassis boss under it. It is the belt clamps' screw, insert and key (2.5 mm hex): no new
SKU. The printed spacer bar that used to bridge out to an M4 beside the board is gone.

1. **Heat-set the M3 insert into the boss first**, from the top, before anything else is in
   the bay (McMaster 94459A130; its pocket is 4.8, so it drops in before it is melted home).
   Flush with the boss's top: the Pi's underside rests on it.
2. **Plug the USB-C lead into the Pi on the bench** (see below). It cannot be plugged in
   afterwards: the angled head and its shell need 17.65 mm in front of the socket to go in,
   and the rail is about 12 mm away.
3. **Lower the Pi straight down into its cradle, the lead's head going down the −Y wall's
   notch with it.** The corner pads and the boss carry it, 13.6 mm off the floor: its +X
   end stands over motor 3's bay back wall and 0.5 off that motor's driver, so it goes in
   **before string 3's motor** if that motor is in the way of your hands, or with it in
   place if not — nothing of the Pi touches it.
4. **Put the printed ring (`pi_spacer`, Ø6 × 3.2) on the hole and drive the M3 × 12
   through it and the Pi's hole into the insert.** The Pi's hole is 2.7 mm and the screw is
   M3: **it is a forced thread and tight by design — do not ream the hole.** The crests cut
   about 0.15 mm into the hole's plated barrel (user, on the bench, 2026-10-29). The ring is
   what makes the 12 mm screw the right length: without it the screw bottoms out.
5. Do not overtighten: the ring bears on the Pi's own Ø6 keep-out pad round the hole.

⚠ **Removal order:** the screw, then the Pi straight up with its lead, then unplug the lead.

### The Pi's USB-C lead: angled plug, cable toward −X (2026-10-28, order changed 2026-10-29)

The lead from `output_panel` J2 is a StarTech USB2CC1MR, and its **angled** end goes in the Pi.
The head lies flat between the Pi's −Y edge and the rail, in a notch in the cradle wall, with
0.5 mm to the rail — the rail is set off this plug (`dimensions.PI_PLUG_Y0`), and it is not
cut for it. **Turn the plug so its cable leaves toward the Pi's SD-card end (−X)**, then
take the cable up the rail past that end of the board, into the cable trough. USB-C is
reversible, so either way up plugs in; only one way round sends the cable where the route
has room.

**Plug it in BEFORE the Pi goes in** (step 2 above), on the bench: there is no room in front
of the socket to push a plug in once the Pi is seated.

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

Bus B daisy-chains through every lever board: in on **J1**, out on **J2** — two 4-way PH
on the board's end, J1 the upper (see KL-5). A lever is **not** at a fixed station — its tenons drop into the chassis bottom's mortise grid
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
- **Everything changes ends with the board.** On LKL, VKL and RKL, J1 (bus in) is the
  UPPER connector and way 1 (5 V) is the top contact of each; on LKR and RKR, J1 is the
  LOWER one and way 1 is each one's bottom contact. The crimped harness is the same either
  way — a PH housing only plugs in one way round — so this matters only when probing with
  a meter, or when telling in from out (and in and out may be swapped without effect:
  both are the same four nets on the board).

### KL-5 — Every hop is its own straight 4-way jumper (2026-10-19)

- **What:** each board carries **J1 (bus in)** and **J2 (bus out)**, two 4-way PH
  (`S4B-PH-K-S`) standing end to end, mouths toward the plug tunnel. The cable from one
  board's J2 to the next one's J1 is a **PHR-4 at each end, way 1 to way 1, 2 to 2, 3 to
  3, 4 to 4** — no crossover, the same for every hop. Crimp `5V, GND, CAN_H, CAN_L` on
  ways 1–4 at both ends.
- **Pulling one lever:** unplug its J1 and J2 and lift it out; nothing else moves. To run
  the instrument without it, replace the two cables either side with one jumper long
  enough for the gap (any straight PHR-4 lead works).
- **Moving one lever further than the keeper's slack** (KL-2): re-make only the one or
  two cables that touch it. With one 8-way housing both cables were crimped into the same
  PHR-8, so either neighbour's cable had to be re-made with it.
- **The last board** in each chain (the far pedal, the far lever) has J2 empty; its
  terminator switch is ON (PB-0).

---

## Pedal bar wiring (bus B)

The bar's wiring trough carries bus B from the −X (wired) leg tower to the five
pedal sensor boards, daisy-chained: leg → pedal 1 → … → pedal 5. Each board has the bus
**in** on J1 and **out** on J2, two 4-way PH (KL-5), so the chain runs through the
board; every segment is a straight PHR-4 jumper. Pedal 5 is the far end of the bus: it is the one pedal whose terminator
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
- **What:** plug the arriving segment onto J1 and the departing one onto J2 in the bay,
  bring the wire up through the spur into the trough, and run it along to the next
  station.
- **Why:** the bay is a closed pocket otherwise. The 2026-09-21 board re-spin moved J1,
  and the bay follows the posed hardware, so it stopped reaching the trough and left each
  plug sealed in. Nothing caught it — a cavity that doesn't reach another cavity isn't an
  overlap.
- **No slack cleat here**, unlike the knee levers: a pedal's X station is printed into the
  bar, so nothing about it moves. Cut these segments to fit.
- **Order:** wire the trough **before** the lid slides in. The lid is a full-length sliding
  dovetail entering from the −X end; once it's on, nothing in the trough is reachable.
- **Leave the last one out:** pedal 5 has no onward segment. Its J2 stays empty: the bus end.

### PB-2 — The trough is closed at every pedal except along its floor

- **What:** each pedal's board shim stands from the board's edge to the lid, so with the
  cradle under it it is a plate across the trough at every station. The only way past is
  **under the shim, on the trough floor, against the lid side** — a gap 3 mm high and
  5 mm wide. Lay the four conductors there two deep (the model draws them: GND and
  CAN_H on the floor, +5 V and CAN_L on top of them).
- **Order:** board in, plugs on, wires laid on the floor past the station, **then** the
  shim down its grooves over them, then the lid. A shim that will not seat is sitting on
  a wire.
- **At the plugs:** J1 and J2 point down into the bay and there is 2.5 mm under them. The
  wires turn out of the plugs along the floor inside the plug tunnel (6 mm wide) — the
  arriving four (J1) on the −X side, the departing four (J2) on the +X side.
- **Way 1** (5 V) of each is its contact nearest the **player-side face** of the bar (−Y),
  way 4 the one nearest the lid; the board is turned over here, so J1 is the connector
  nearer the lid.
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

**Cut it long enough for restringing: 178 mm, ZR to PH** (`wiring.pedal_cable_cut`,
2026-10-22). Strings change with **no JST unplugged**: the leg's adapter slides 25.6 mm
outboard (legs.SERVICE_SLIDE) with this cable still in both plugs. Pulled taut, the
underside run is 91.8 mm with the leg home and 116.1 mm with it slid out
(`tools/route_cables.py`). The cable is cut for the slid-out pose, plus its run inside
the adapter, the drop into J2 and 15 mm for the crimps. So **with the leg home it
carries about 24 mm of slack**. Let that slack lie as a loose bow under the body; don't
pull it tight or tie it down short, or the leg will drag the plugs when it slides.

### BB-3 — The lever chain's head

Four conductors from **J6** (4-way PH, 16 mm +Y of J2) to **LKL's J1** (its bus in) — the end
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
| lights lead, 4-way XH | Pi cap J4 | motor board J7 | `24V, GND, button, button` |
| power link, **6-way** XH | motor board J3 | output panel J10 | `24V, GND, button, button, GND, 24V` |

* All three are straight leads: way 1 at one end is way 1 at the other.
* The power link is the only 6-way XH in the instrument, so it cannot go in a wrong socket.
* **Plug and unplug the power link with the supply's plug out of the panel.** The motor
  board's 5 V converter has ceramic capacitors on its input, and a lead that is already
  live rings them above the supply for a few microseconds as it makes contact. The board
  is built to take it (the converter's own fuse and the rail clamp hold the worst case to
  33.4 V at a part that works to 36 and survives 38), but it is a stress with no purpose: power down first.
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

The rule (user, 2026-10-07; the tuples are in `elec/harness.py`):

* **XH (2.5 mm, white, the bigger one) carries 24 V. PH (2.0 mm) carries 5 V.** An XH plug
  does not enter a PH socket or the other way round, so 24 V cannot reach a 5 V contact.
* **Ways are always `power, GND, data, data`.** A lead with no data leaves ways 3 and 4
  empty.
* **A wider housing adds the same four mirrored.** A 6-way is `power, GND, data, data, GND,
  power`; the motor tees' 8-way trunk is `power, GND, H, L, L, H, GND, power`. Either reads
  the same from both ends, and its power ways are the two outside ones.
* **Why ground is second.** In every housing the way next to a power way is ground or
  empty, never a data way. The two faults that put neighbours together -- a strand of wire
  between two crimps, a contact pushed into the next cavity -- then blow a fuse instead of
  putting 24 V on a 3.3 V pin.
* A 4-way or 6-way lead is straight: way 1 at one end is way 1 at the other.
* **A motor-tee trunk hop is not.** It leaves one tee on ways 5 to 8 (the out half) and
  arrives at the next on ways 1 to 4 (the in half): **way 8 to way 1, 7 to 2, 6 to 3, 5
  to 4.** Count each half from its own end of the housing and the two halves read the
  same: power outermost, then ground, then CAN_H, then CAN_L. (The lever and pedal boards'
  hops are straight: their in and out are two 4-way connectors since 2026-10-19, KL-5.)

| lead | family, ways | from | to | ways |
|---|---|---|---|---|
| motor trunk head | XH 4 | output panel J7 | east tee trunk | `24V, GND, -, -` |
| power link | XH 6 | output panel J10 | motor board J3 | `24V, GND, button, button, GND, 24V` |
| optical feed | XH 2 / XH 4 | output panel J9 | optical board J2 | `24V, GND` (`-, -`) |
| bus A head and every motor drop | XH 4 | motor board J1, tee J2 | tees, motors | `24V, GND, CAN_H, CAN_L` |
| tee trunk | XH 8 | tee J1 | next tee | `24V, GND, CAN_H, CAN_L` in on 1-4, its mirror out on 5-8 |
| lights lead | XH 4 | motor board J7 | Pi cap J4 | `24V, GND, button, button` |
| fret light drop | XH 4 | Pi cap J3 | fret board J1 | `24V, GND, SCK, SDT` |
| foot light drop | XH 4 | Pi cap J6 | foot board J1 | `24V, GND, SCK, SDT` |
| Pi 5 V | PH 6 | motor board J5 | Pi cap J2 | `5V, GND, -, -, GND, 5V` |
| USB to the Pi | PH 4 | motor board J4 | Pi USB-A | `VBUS (unused), GND, D-, D+` |
| bus B drops | PH 4 | motor board J2 / J6, leg boards | pedal and lever chains | `5V, GND, CAN_H, CAN_L` |
| lever / pedal hop | PH 4 | sensor board J2 (out) | next sensor board J1 (in) | `5V, GND, CAN_H, CAN_L`, straight |

**The optical feed has a different housing at each end**: a 2-way XH at the output panel
(J9), a 4-way XH at the optical board (J2) with ways 3 and 4 left empty. Way 1 is 24 V at
both. The optical board has no reverse protection: meter the lead before it is first
plugged in.

**Only the optical board plugs into the output panel's USB-C (J4).** Its VBUS has no
current limit of its own, on a 0.6 A rail.

**Two pairs of sockets on the motor board take each other's plug**: J1 and J7 (both
4-way XH), and J4 (the USB lead) against the bus-B leads on J2 / J6 (all 4-way PH). The
table further down says what each wrong pairing does; the silk names every socket.

**At a motor the drop ends on screw terminals, not a housing**: 24 V to V+, ground to GND,
and the pair to CANH / CANL by the names printed on the driver. The lead's colours (red,
black, yellow, green) are the check; there is no way number at that end.

**The USB lead is the one lead whose far end has somebody else's numbering.** A USB-A plug's
own contacts are 1 VBUS, 2 D-, 3 D+, 4 GND (USB 2.0, the order the plug's maker prints);
the PH housing's ways are VBUS, GND, D-, D+. So it is NOT contact n to way n:

| USB-A contact | usual wire | PH way |
|---|---|---|
| 1 VBUS | red | 1 (crimped or left out: the board does not connect it) |
| 4 GND | black | 2 |
| 2 D- | white | 3 |
| 3 D+ | green | 4 |

Wire colours are a habit, not a standard: meter each wire to its plug contact before crimping.
Crimped contact n to way n, the Pi's D- lands on the motor board's ground and the lead's
ground on D+: the link is dead and nothing is damaged.

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
| CAN_H, CAN_L | SCK, SDT at the Pi cap's J3 / J6 | The Pi's two SPI pins, each behind 68 ohm, meet the CAN pair. A 5 V CAN transceiver (the motor drivers' is one: TJA1051T/3 on a 5 V supply, U9 on the maker's schematic) drives CAN_H to 3.5 V typical, 4.5 V worst case, against a 3.3 V pin: up to about 9 mA into the pin's clamp, and the pin itself drives about 25 mA into the bus against its 16 mA. **A stress for as long as it is left plugged, not an over-voltage**; lights and bus A both misbehave at once. |
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
| bus-B drop | motor board J4 (USB) | Way 1, the bus's 5 V, is not connected on the board; the CAN pair meets the MCU's USB pins at 0 to 3.3 V. No damage. |

**6-way PH**: only the Pi's 5 V lead. **8-way** XH: only the motor-tee trunk.

The one row worth a label is the second: a motor drop or the bus-A head plugged into a light
drop on the Pi cap. Mark the two light-drop leads at the Pi cap end.

## Pickup piece: set the retention screw on the bench, and clear the leads before it slides

- **The retention screw is an M4 x 20 button head driven from -Y, through a slot in the
  piece's -Y skirt.** With a short pickup (96.5 mm) it is screwed right in and its head sits
  inside the skirt; with the longest (102 mm) it is backed out 5.5 mm and the head stands
  3 mm OUTSIDE the skirt. Either is right. Set it with the piece on the bench, before the
  piece goes into the body: once the piece is in, the head is under the deck.
- **The piece slides the whole length of the body, in and out the keyhead end**
  (`py -3.12 -m tools.check_deck_slide`). Nothing fixed stands in its way, but two leads
  do unless you move them: the UI ribbon and the fret-light lead stay in the body when the
  mid and keyhead panels come off, and both lie at the height of the pickup's plate
  (6-16 mm under the deck). Push them down against the chassis floor, or lift them out
  over the rail, before the pickup piece moves.
- **Order out:** strings, nut block and keyhead endplate, keyhead panel (slide it about
  253 mm out, then unplug the fret lead at the Pi cap; see below), mid panel with the UI station on it (unplug the ribbon), then the bands and the
  pickup piece (unplug the pickup lead). In is the reverse.
- **Tight spots on the way** (as drawn, plate at the bottom of its travel): the jack
  screws' tips pass 0.3-0.4 mm over the foot-light lead, and the deck's -Y edge passes
  0.3 mm from the optical board's USB cable. Dress both flat.

## The fret-light lead is plugged in before the keyhead panel slides home

The keyhead panel carries the fret board, and once it is home the Pi cap's J3 is under it.
So the lead goes in with the panel partway on (`src/led_leads.py`, fret_plug_slide):

1. The mid panel is home and the UI ribbon is already in the Pi cap's J5.
2. Slide the keyhead panel on until its +X edge stops about **253 mm short of home**: 40 mm
   -X of J3, enough for fingers and the XHP-4 housing.
3. Plug the lead into the fret board's J1 (the panel's underside, -X end) and the cap's J3.
4. Slide the panel home. The lead is cut 312 for step 3, so about 174 mm of it is spare at
   home: lay it down flat in the bay as the panel goes, below the panel's underside
   (z -18.8; nothing higher than the cable trough's lip).

Out is the reverse: slide the panel 253 mm out, then unplug J3.

## The Pi's USB-A plugs go in after the mid deck panel is on

The UI station rides the mid deck panel, and that panel slides on from the keyhead end
past the Pi. The two leads that plug into the Pi's USB-A ports (from the motor board and
from the output panel's hub) stand up out of the bay to reach those ports, into the path
the station's underside sweeps.

* Before sliding the mid panel on: leave both USB-A plugs unplugged and lay the leads down
  in the bay. Nothing should stand higher than the cable trough's lip.
* After the panel is home: plug the UI ribbon into the Pi cap, then the two USB-A plugs.
  The keyhead panel is still off, so the Pi is open from above.
* Coming apart is the reverse: both USB-A plugs and the ribbon out, leads laid down, then
  slide the panel off.

## The display's ribbon: into the module first, and check pin 1 before power (2026-10-19)

The display (NHD-2.7-12864WDW3-M) joins the UI board by a 50 mm, 20-way flat cable
between two sockets: the Molex on the module's back and J1 on the board's +Y edge. Both
are slide-lock sockets: pull the dark actuator out about 1 mm, slide the cable in fully,
push the actuator home. Build the station with the mid panel upside down on the bench.

1. **Cable into the module first**, before the module goes into its pocket. The bare
   contacts face the MODULE's board (it is a bottom-contact socket), and the blue stiffener
   faces away from it.
2. **Module face-down into the deck's pocket.** The cable now leaves its socket toward
   the module's centre.
3. **Other end into J1.** Hold the UI board near its posts, contacts DOWN toward the UI
   board (also bottom contact). It is a same-side cable, so it goes in this way without
   twisting. If the contacts face up at this end, the cable is a reverse (type B) one:
   it is the wrong cable.
4. **Board onto its posts and spigots**, and let the slack form a loop under the
   module's centre, away from the board. Do not fold it flat or crease it.
5. **Clamp on.** Its two arms go either side of the loop, not across it. Then the screw.
6. **Before the first power-up, check pin 1 with a meter.** The module's socket has its
   pin 1 marked on the module's board. It must ring through to GND on the UI board, which
   is way 8 of J2, the Pi ribbon header. If it rings to +3V3 (way 10) instead, the cable
   is reversed end to end and would put 3.3 V on the module's mode pins: stop. The
   module's pin-1 side is confirmed (Newhaven's drawing and their photo of the -M's
   back agree), so a wrong reading here means a wrong cable, not a wrong design.

Coming apart: clamp off, board off its posts, then release J1's actuator before pulling
the cable. Molex rate the module's socket for 30 insertions, so take the cable out of
the module only when the module itself is being replaced.

## The motor controller drops in from above; the -X/-Y leg is its floor (2026-10-29)

The motor board slides straight down (+Z to -Z) into its guides behind string 1's motor:
- a channel takes its -Y edge (the edge away from the motor);
- two short posts on the floor take its +Y edge;
- its face sits flush on string 1's motor.

Nothing is screwed. The keyhead deck panel's rib, 0.3 above the board's top edge, stops it
lifting, so **seat the board before that panel goes on**. Sight down both faces as it drops:
nothing on the board should touch a guide on the way in.

**Its -Z stop is the -X/-Y leg's body adapter, not the chassis.** The board's bottom edge sits
0.34 above the underside (so J2/J6 can be squeezed from below), and with that leg fitted, the
adapter's top face is what it rests on. With the leg off, nothing stops the board from dropping
toward the floor port except its cables and the plugs resting on the table. So:
- **fit the -X/-Y leg before standing the instrument upright with the deck on**;
- **never carry it legs-off with the deck on** unless the controller is unplugged and secured
  (tape it to the guides, or lift it out).
