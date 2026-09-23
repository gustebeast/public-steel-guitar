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
   threading: a fitted PHR-4 will not pass the bores it has to travel.
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
