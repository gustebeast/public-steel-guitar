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

## The UI station (deck mid panel) — 2026-09-28

The display, the encoder and the board that carries them are ONE assembly, plugged
together, and **one M4 holds it in the deck panel**. Plastic takes every other direction:
the display's pocket walls and the window ledge catch it in X, Y and +Z; the board's
cradle wall and four columns catch it in X, Y and +Z. The one direction left is the one
you install along, and that is the screw's whole job. The display's own downward stop is
the board's header — which is what makes one screw cover both.

**Building the panel up**

1. Heat-set an M4 insert into the boss on the panel's underside, from the boss's open
   end. It is the only insert on the panel.
2. Solder the 1×20 **female** socket (KH-2.54FH-1X20P-H8.5) to the BACK of the Newhaven
   module, opening facing away from the glass. The module ships with plated holes and no
   header — Newhaven's own drawing only recommends one — so this is the one hand-solder
   step in the station, and it is on a PCB, which the project's no-solder rule allows.
3. Plug the module onto the board's 1×20 male header. They stay together from here.
4. Offer the assembly up: the module enters the pocket in the panel's underside, the
   board enters its cradle. The module seats against the 1.6 mm window ledge — the header
   stack is deliberately **0.3 mm long**, so it always presses up into that ledge rather
   than rattling under it.
5. Run the M4 button screw up through the board into the insert, from underneath.
6. Press the printed knob onto the switch's shaft through the hole in the deck. **The
   shaft is a D** — Ø2.5 milled to 1.79 across — and so is the knob's bore. The cap is
   unindexed, so any clocking is fine; it only has to go on square.

**Taking it out — the screw first, then the panels.**

1. Undo the one M4 from underneath. The whole assembly — screen, board and all — is now
   free to come down.
2. Let it down about 20 mm onto the chassis floor. There is **57.5 mm of clear air**
   under the station's entire footprint, so it lands on bare floor with nothing to catch
   on, and its highest point then sits ~39 mm below the lowest feature hanging off any
   deck panel.
3. Reach in and unplug the 14-way ribbon at the board's −X edge.
4. Now slide the deck panels out. They pass over the assembly with room to spare.
5. Lift the assembly out from above once the panels are gone. **It will not come out
   through the deck** with the panels on: the module is 82 × 47.5 and the window is
   66 × 33.

**Before the first panel is printed**, confirm the right-angle ribbon header's height
against the real part. `src/board_geom.HEIGHT` carries 10.0 mm for it as an ESTIMATE —
ZHOURI publish no drawing through LCSC — and there is 11.40 mm between the board's top
face and the deck's underside.
