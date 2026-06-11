# servo-steel

Open-source parametric CAD for an **electro-mechanical pedal steel guitar**:
one closed-loop electric actuator per string, so the copedent — the mapping
from pedals and knee levers to pitch changes — becomes **software
configuration** instead of a hand-built maze of rods and bellcranks.

**Status:** CAD in progress (build-verified geometry, no
physical prototype yet). See
[`electromechanical-pedal-steel-spec.md`](electromechanical-pedal-steel-spec.md)
for the full design rationale and history, and [`BOM.md`](BOM.md) for sourced
purchased parts (~$370, dominated by the ten servos).

**License:** [CERN-OHL-S 2.0](LICENSE) (strongly reciprocal open hardware).

## The concept, in one paragraph

A traditional pedal steel changes string pitch by pulling the string's anchor
with a mechanical changer; which pedal pulls which string, and by how much, is
fixed in hardware. Here, each of the 10 strings terminates on a **carriage
riding a self-locking leadscrew** driven by a **closed-loop servo motor**.
Pedals and levers are just **sensors**; firmware looks up the active copedent
and commands the relevant motors to new positions. Any pedal can bend any
combination of strings by any interval, changeable between songs. Because the
fine-pitch single-start screw is **non-back-drivable**, string tension cannot
move it: the motors are completely unpowered at rest — no holding current, no
heat, no idle noise — and the instrument holds its tuning even switched off.

## Disclosed system concepts

For avoidance of doubt, the publicly disclosed ideas include (without
limitation):

- Per-string servo/stepper actuation of a pedal-steel changer, with a
  **software-reconfigurable copedent** (pedal/lever sensors → lookup →
  per-string position targets).
- A **self-locking (non-back-drivable) leadscrew per string** holding pitch
  with zero motor power, and serving as the tuning machine (no manual tuners).
- **Two nested control loops**: a fast feed-forward path (pedal position →
  copedent → motor position) with no pitch detection in the playing path, and
  a slow calibration loop using per-string pickup **pitch detection to correct
  the position→pitch map** (drift correction without touching the copedent).
- A **CAN-bus network of closed-loop actuators** (one node per string)
  commanded by a central controller reading pedal/lever angle sensors.
- The **vertical under-string actuator layout**: each string turns 90° over a
  per-string bridge bearing and runs down to a short vertical screw, motors
  lying flat under the speaking length in a staircase, driven by twisted
  belts — yielding a thin instrument (~100 mm).
- Per-string **gauged break-pin string termination** (reprintable nut block
  with steel pins sized so string tops sit coplanar) and **ball-end capture
  cages** on the carriages (tension-only retention, no clamps at the moving
  end).
- **Printed hard stops at both travel extremes** protecting the precision
  parts from motor faults, with the upper stop doubling as the guide-rod
  installation jig, and **drop-in friction-held guide rods** that capture the
  carriages during assembly.

## How the mechanism works

**The string's path** (from the player's left): each string's plain end is
clamped in the **nut block** — a removable, reprintable PA6-GF block whose
per-string steel **break pins** are gauged so every string's top lies in one
plane; a cup-point set screw clamps the dead end. The speaking length (615 mm,
≈24.2″ scale) runs to the bridge, turns 90° over a **per-string Ø8 ball
bearing** (so the bend is near-frictionless and tension equalizes across it),
and drops vertically to the **carriage**. The ball end sits in a **cage** in
the carriage: the string threads up through a roof slot narrower than the
ball, so tension alone captures it — restringing needs no tools at the moving
end.

**The drive** (per string): `MKS SERVO42D closed-loop stepper (CAN) → GT2 belt
(twisted 90°) → screw pulley → Tr5×1 vertical leadscrew (61 mm) → brass nut
pressed into the carriage → string`. The screw's 1 mm lead at Ø5 is deeply
self-locking; ~1.5 mm of carriage travel is a semitone, and total travel
(10 mm) covers slack-to-pitch take-up plus three whole steps of raise. An
axial thrust path (support bearing + locknut) carries the string pull; the
carriage rides a **Ø2.5 hardened guide rod** through a closed bore for
anti-rotation. Travel is bounded by **printed hard stops** at both extremes —
the top stop keeps the carriage off the bridge bearings, the bottom stop keeps
it off the pulleys and belts — so a runaway servo cannot damage the machine.

**The structure**: two deep I-beam side rails (3 printed segments joined by
sliding dovetails), per-motor cross-ribs, and a one-piece **bridge endplate**
that closes the box and carries the bridge-bearing axle on two arms plus a
nine-finger **support comb** (the Ø3 axle alone would bend under ~1.5 kN of
string wrap load; the comb cuts its free span to one string pitch *and* acts
as the assembly jig — drop the ten bearings into the comb slots and slide the
shaft through everything in one pass). Motors mount on faceplate walls with
slotted holes for belt tensioning. Every printed part is self-supporting at
45° for a 0.8 mm nozzle; the big parts are PCTG, the load-critical small parts
(carriage, nut block) PA6-GF.

**Electronics** (architecture level; firmware not in this repo): a Teensy-class
controller reads pedal/lever angle sensors and speaks CAN to the ten servos.
The playing path is pure feed-forward — pedal moves map directly to motor
positions, so there is no pitch-tracking latency while playing. A per-string
pickup (e.g. a hex/multichannel pickup) feeds slow pitch detection used only
when calibrating: it measures each open string and corrects the
position→pitch map, absorbing drift from temperature, creep, or string aging.
The servos retune the instrument on demand; there are no manual tuning
machines anywhere.

## Building the CAD

CadQuery on Python 3.12 generates a STEP file per printed part plus a colored
`assembly.step` (~156 placed components including purchased-part dummies).

```bash
py -3.12 -m src.build              # all parts + assembly.step
py -3.12 -m src.build --part NAME  # one part (fast iteration)
py -3.12 -m src.build --list       # list part names
py -3.12 -m src.build --geom       # belt-geometry report
py -3.12 -m tools.check_overlaps   # design gate: any unintended interpenetration
```

- `src/dimensions.py` — the coordinate frame (+X along the strings toward the
  bridge, +Y across, +Z up) and **every** dimension as a named constant.
- `src/components.py` — schematic dummies of purchased parts (motor, screw,
  nut, bearings, pulleys, belt, strings, dowels) used only in the assembly.
- Printed parts: `carriage` ×10, `bridge_endplate`, `chassis_0/1/2`,
  `nut_block`, `belt_clamp`, `screw_pulley`, `motor_pulley`, `tension_fork`
  (graded belt-tension lock set), `pickup_saddle`/`pickup_bar`/`pickup_jaw`
  (adjustable pickup mount: rail-sliding X position for bridge↔neck tone,
  slotted ±6 mm height, width-clamping jaws for ~22–40 mm pickups).
- `tools/check_overlaps.py` exits non-zero on any unintended part
  interpenetration; carriage geometry is additionally swept through both
  travel extremes during design review.

Envelope ≈ 100 × 200 × 655 mm (thick × across × long) — thin enough to sit on
a keyboard rig. 10 strings at 9.5 mm pitch at the bridge.

## Repository layout

| Path | What |
|---|---|
| `src/` | CadQuery source — one module per printed part + helpers |
| `tools/` | the overlap-check design gate |
| `BOM.md` | purchased parts with sourcing links and prices |
| `electromechanical-pedal-steel-spec.md` | the full design specification and rationale |
| `*.step` | generated geometry (per part + full assembly) |

---

Copyright © 2026 gustebeast. Licensed under CERN-OHL-S 2.0 — you may build,
modify, and sell hardware from these sources, but modified sources must remain
available under the same license.
