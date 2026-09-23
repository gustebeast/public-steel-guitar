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
