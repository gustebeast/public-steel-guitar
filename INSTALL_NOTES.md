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

---

## Knee lever wiring (bus B)

Bus B daisy-chains through every lever board: in on J1 ways 1–4, out on 5–8. A lever
is **not** at a fixed station — its tenons drop into the chassis bottom's mortise grid
(`D.LEVER_PITCH`, 10.4 mm) so it steps along X, and the rib mortise lets it slide to
any knee depth over 197.5 mm in Y.

### KL-2 — Cut the lever segments long and tie the hank to the lever

- **Where:** the lace loop on each lever housing's **+Y cheek** (`knee_lever.lace_loop`,
  on both `kl_housing` and `kv_housing`) — the side the plug leaves the board on —
  **flush with the housing's back end**, the screw end. It is well clear of the plug's
  full withdrawal (`knee_lever.CONN_UNPLUG`), so a tied hank never blocks unplugging,
  and the wire runs the length of the cheek before it is tied.
- **What:** cut each lever-to-lever segment for the **widest** spacing you would use,
  fold the excess into a flat hank, pass it through the loop and tie it there with a
  reusable tie. The bore takes a doubled bundle.
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
