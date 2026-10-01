# The real SERVO42D in the bay we drew for it (2026-10-01)

**Status: a finding and a proposal. Nothing in the build has changed.** The motor bank and
the chassis are the lead's; `src/servo42d.py` is a standalone model, not in `src.build`.

## What the part is, against what the CAD draws

| | `components.motor()` (in the build) | the part (`src/servo42d.py`) | source |
|---|---|---|---|
| motor body | 42.3 sq x 48 | 42.3 sq x **40** | makerbase3d.com listing, "nema17 motor 40mm long" (user) |
| driver behind it | 36.3 sq x 22, a plain box | **42.3 sq x ~11**, a shrouded board the full size of the motor | scaled off the user's side-on photo, +-2 mm |
| faceplate to back | **70.0** (`D.MOTOR_BODY_L`) | **~51** | |
| what leaves the 42.3 square | nothing | the motor's coil plug and its lead, **~5 mm proud on ONE side** of the rear cap; the terminal blocks, 0.35 proud on two opposite sides; three buttons, ~0.85 proud on the fourth | user's photos and video |
| connections | "one 6-pin XH pigtail, power and CAN" | **screw terminals**: a 6-way (V+, GND, COM, EN, STP, DIR) on one edge, a 5-way (5V, GND, IN1, CANH, CANL) on the OPPOSITE edge, a 4-way coil block on a third | Makerbase schematic `MKS SERVO42D_CAN V1.0_003`; the user's video |

Every dimension of the driver is an estimate off photographs. **One motor in hand settles
all of it**, and the same motor answers the slew-current question the power budget rests on.

## The fit, measured (motor 5, its own bay, both neighbours)

The unit placed with its faceplate where `components.motor()` puts it, in each of the four
rotations about its shaft, intersected with `motor_bank.plates`, the neighbouring units, the
tee board and the floor:

| coil side faces | own bay | neighbour bays | neighbour units | floor |
|---|---|---|---|---|
| **+Z (up)** | 0 | 0 | 0 | 20 mm3 (the buttons, 0.85 under the square) |
| +X | 333 mm3 | 333 | 481 each | 34 |
| -Z (down) | 0 | 0 | 0 | 1002 mm3 |
| -X | 333 mm3 | 333 | 104 each | 28 |

**Only coil-up goes in.** The bay is a slip fit round a 42.3 prism (0.4 a side, 1.6 walls,
2.4 between motors) and the coil plug needs 5 mm that only the open top has. The tee board
covers the front 9.6 mm of the motor's top; the plug is 35 mm behind the faceplate, clear
of it.

**...and coil-up puts both terminal blocks against the bay's side walls.** With the driver
in its factory rotation the 6-way and 5-way face +X and -X. Their wire faces are at
x +-21.50; the walls are at +-21.55. A screw terminal takes its wire from the side, so
neither can be wired in the bay, and neither can be pre-wired and dropped in: there is no
room for a wire to leave sideways and turn.

What is actually open round the driver:
* **+Z**, the whole top.
* **-X, for the last 9.5 mm only**: the bank is staggered one string pitch, so the -X
  neighbour's unit has ended there. The terminal zone (1-7 mm from the unit's back) is
  inside it, behind a wall that could be windowed.
* **-Y**: 19 mm of bay that the 70 mm model occupied and the 51 mm part does not.
* Not +X (the +X neighbour's rear cap, 2.05 away) and not -Z (the 10.5 mm floor).

## One arrangement that works, for the lead to accept or replace

Turn the DRIVER a quarter turn on the motor (four screws on a 31 mm square; the motor
stays coil-plug-up):

* the 6-way and 5-way land on **+Z and -Z**. The top one is open. The bottom one needs a
  relief in the floor under the last ~11 mm of the unit and takes its two wires before the
  motor is lowered; they leave downward, turn -Y and climb the 19 mm now free behind it;
* the coil block lands on **-X**, in the stagger's open band, behind a window in that wall;
* the coil lead has to reach from the top plug round to -X: ~65 mm against the factory
  lead's ~45. A made lead, crimped JST at the motor end and bare into the screw terminal;
* the buttons face +X and cannot be reached in the bay. They are a bench-setup control.

Chassis cost: bays 19 mm shorter (and `Y_LO`, the -Y rail, with them, if the lead wants
the depth back), a window per bay on -X, a floor relief per bay. All of it is in
`motor_bank.py` / `chassis.py`.

## What this does NOT change: the tee

The motor never had a pigtail, so the harness makes one: **four wires, ferruled into the
two screw-terminal blocks (V+, GND; CANH, CANL), gathered into one XHP-4** in the order the
tee's drop already has (GND, 24 V, CAN-H, CAN-L). That is the cable `wiring.py` draws as
`motor_pigtail_*` today, and it plugs into the merged tee unchanged. The trunk, the tee
board, its pinout and brenner's fret boards over it are all untouched.

So the two-connector finding is a PIGTAIL and BAY-ACCESS finding, not a reason to redesign
the tee. The power-only tee (option 6b in `docs/can-tee-power-tap.md`) stays shelved: the
supply the user chose (160 W, ~4.6 A for the motors) is inside what the merged tee carries
(5.5 A), and 6b only pays if all ten motors must slew together.

Termination: the driver carries its own 120 R behind a jumper (R13 / SW1 on the schematic).
The tee's R1 / JP1 does the same job at the same two ends; use one or the other, not both.
