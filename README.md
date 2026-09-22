# Public Steel Guitar

Open-source parametric CAD for an **electro-mechanical pedal steel guitar**:
one closed-loop electric actuator per string, so the copedent — the mapping
from pedals and knee levers to pitch changes — becomes **software
configuration** instead of a hand-built maze of rods and bellcranks.

**Status:** CAD in progress (build-verified geometry, no
physical prototype yet). See
[`electromechanical-pedal-steel-spec.md`](electromechanical-pedal-steel-spec.md)
for the full design rationale and history, and [`BOM.md`](BOM.md) for sourced
purchased parts (~$865 basic / ~$1,090 pro, dominated by the ten closed-loop steppers).

**View it in 3D** (no install, no account):
<https://gustebeast.github.io/public-steel-guitar/> — an interactive model of the
instrument body, strings, nut block, and motor/changer drivetrain.

**License:** [CERN-OHL-S 2.0](LICENSE) (strongly reciprocal open hardware).

## The concept, in one paragraph

A traditional pedal steel changes string pitch by pulling the string's anchor
with a mechanical changer; which pedal pulls which string, and by how much, is
fixed in hardware. Here, each of the 10 strings terminates on a **carriage
riding a self-locking leadscrew** driven by a **closed-loop stepper** (MKS SERVO42D).
Pedals and levers are just **sensors**; firmware looks up the active copedent
and commands the relevant motors to new positions. Any pedal can bend any
combination of strings by any interval, changeable between songs. Because the
fine-pitch single-start screw is **non-back-drivable**, string tension cannot
move it: the motors are completely unpowered at rest — no holding current, no
heat, no idle noise — and the instrument holds its tuning even switched off.

## System concepts

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
clamped in the **nut block** — a removable, reprintable PETG-GF block whose
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
round bolt holes, packed 1.6 mm apart — a screw-driven clamp on each belt
takes up the tension, so the motors never slide. Every printed part is self-supporting at
45° for a 0.8 mm nozzle. Materials (the build exports into per-material
folders): **PETG-GF** for every stiffness/creep-critical part — chassis,
both endplates, carriages, leg tubes — **PCTG** for compliant, snap-fit and
fine-feature parts and the whole deck — the panels print as two-filament
pairs (transparent-PCTG base whose fret lines run full-depth through the
plate + a colour-PCTG layer between them; no glass fiber on the forearm-rest
surface).

**Legs**: four quick-attach legs join the body at the corners with slide-in
octagon joinery and a cross-pin — no glue anywhere in the instrument, so every
part comes apart again. Each leg-to-leg junction is a cadkit octagon slide
joint retained by a single M4 (extraction only — the joinery takes the force),
so the instrument breaks down for transport in seconds. The legs must
print in pieces for build volume anyway, so the pieces double as the coarse
height adjustment: each stackable segment steps the height 142 mm, and a
clamped sliding shaft at the bottom spans 150 mm — more than one step — so
the bands overlap and **any** height from ~240 mm up is reachable (two
segments cover 525–675 mm; add or drop segments from there).

**Electronics** (architecture level; firmware not in this repo): a Teensy 4.1
reads pedal/lever angle sensors and speaks CAN to the ten servos. The compute
bay — a printed tray that stands on end against the keyhead endplate, so the
motor bank packs right up to it — has mounts for the full **pro** stack (Teensy 4.1 + audio shield,
CAN transceiver, Raspberry Pi 5, 3× PCM1864 TDM ADCs, buck converter); a
**basic** build populates only the Teensy row and leaves the other sockets
empty as the upgrade path. Panel I/O (1/4" TS line out, DC power inlet,
USB-C audio-interface port) mounts through a recessed wall in the bridge
endplate — the instrument's right face. A small **analog front-end** board at
the bridge end carries a JFET buffer and a true-bypass signal relay: by
default (relay de-energized) the raw pickup runs straight to the TS jack with
no converters in the path; the Teensy energizes the relay from the UI to
switch in the Q-processed (ADC→DSP→DAC) output instead. Buffering at the
pickup keeps the long run to the keyhead ADC quiet, and the ADC is fed in
either mode so pitch detection always works. The modeled harness is
color-coded per electrical net (spliced runs share a color; every unique
source→dest pairing differs) and routed through diamond raceways in the
cross-ribs; the overlap gate verifies the wires touch nothing but their own
endpoints. A **removable top deck** (PCTG panels riding grooves in the rail tops so they
can't fall off when inverted, yet pull out toward -X for motor service once the
keyhead endplate is off) covers the motors + electronics, carries printed
fret-position lines, doubles as a hand rest, and mounts the UI: a 2.42 in OLED
and a single Alps multi-control (rotary + 4-way + push). The bridge end of the
deck is split into 20 mm slots. A 4-slot **pickup-carrier piece** holds the
pickup as a tray: the pickup pokes up through an opening and rests on three M4
height screws standing on a **floor that runs under it** (turn them to set the
string gap), while a single M4 clamp screw pulls it flat to the -Y skirt —
locating Y, blocking yaw, locking X in its slot, and retaining it against
falling out when inverted. Height is adjustable in place — loosen the clamp,
slide the pickup off the screws, set them, slide back, retighten — without
pulling any deck panel. The clamp's slot gives ±11 mm of fine X (tone) while the
pickup stays on its 3 height screws; re-slotting the piece among its 4 positions
moves the pickup coarsely bridge-to-neck, and the fine range bridges the slot
step so the whole range (well past the 50 mm minimum) is continuous. The remaining slots take swappable
fret-marked **filler bands**; the region's fixed total width keeps the UI/keyhead
panels from shifting.
The playing path is pure feed-forward — pedal moves map directly to motor
positions, so there is no pitch-tracking latency while playing. A per-string
pickup (e.g. a hex/multichannel pickup) feeds slow pitch detection used only
when calibrating: it measures each open string and corrects the
position→pitch map, absorbing drift from temperature, creep, or string aging.
The servos retune the instrument on demand; there are no manual tuning
machines anywhere.

## Building the CAD

CadQuery on Python 3.12 generates a STEP file per printed part plus a colored
`assembly.step`. The assembly places ~900 components: the printed parts, every
purchased-part dummy, the PCBs, and the wiring harness drawn as real cable.

```bash
py -3.12 -m src.build              # all parts + assembly.step (the guaranteed full build)
py -3.12 -m src.build --part NAME  # one part, but still pays the ~26s module-level import
py -3.12 -m src.build --list       # list part names
py -3.12 -m src.build --geom       # belt-geometry report
py -3.12 -m tools.fast_build NAME  # ITERATION: rebuild one part in <1s-9s — imports ONLY that
                                   #   part's module, not all of src.build. Builds FRESH (no
                                   #   stale cache); handles 59/71 parts, falls back for the rest.
py -3.12 -m tools.check_overlaps   # design gate: any unintended interpenetration.
                                   #   A full build runs this gate ITSELF on the model it just
                                   #   made, so you rarely need it standalone. The scan is a few
                                   #   seconds (an incremental cache keyed on each part's
                                   #   geometry — only changed pairs are re-measured); standalone
                                   #   cost is dominated by rebuilding the model first.
                                   #   --no-gate opts out.
py -3.12 -m tools.check_sweep      # rotating parts swept through a full turn (the overlap
                                   #   gate is structurally blind to this)
py -3.12 -m tools.check_ceilings   # unsupported overhangs, per part, in its own print pose
py -3.12 -m tools.check_walls      # thin walls / minimum material
py -3.12 -m tools.check_beads      # dimensions on the nozzle-width grid
py -3.12 -m tools.check_dead       # source drift: definitions nothing names any more
py -3.12 -m tools.build_profile    # per-part/module build-cost + face-count regression gate
py -3.12 -m tools.export_glb       # simplified colored GLB for the web viewer (docs/)
```

- `src/dimensions.py` — the coordinate frame (+X along the strings toward the
  bridge, +Y across, +Z up) and **every** dimension as a named constant.
- `src/components.py` — schematic dummies of purchased parts (motor, screw,
  nut, bearings, pulleys, belt, strings, dowels) used only in the assembly.
- Printed parts, by area (`py -3.12 -m src.build --list` is the authoritative
  list — it is generated, this is a map):
  - **body**: `chassis_0/1/2` (+ `_light` variants), `bridge_endplate`,
    `keyhead_endplate` (nut block fused in)
  - **top deck**: `top_plate_*` segments and their colour inlays,
    `pickup_zplate` (the pickup's height plate)
  - **drivetrain**: `screw_pulley_hi`/`_lo`, `motor_pulley`, `tension_fork`,
    and the belt-tension clamp (one `clamp_half` SKU fitted twice per string)
  - **controls**: `knee_housing`/`knee_lever`, `kv_housing`/`kv_lever`,
    `pedal_bar_a/b/c`, `pedal_lever`, and the shared feel cartridge
    (`cart_base`/`cart_piston`)
  - **legs**: `fixed_sleeve`/`adjust_sleeve`, `fixed_tenon`/`adjust_tenon`,
    `body_adapter*`, `leg_foot` (TPU), and the latch set
  - **coupons**: `test_*` — print-fit test pieces, not part of the instrument
- Every gate exits non-zero on a finding, and `src.build` runs the overlap and
  sweep gates itself on the model it just built.

Envelope ≈ 100 × 200 × 655 mm (thick × across × long) — thin enough to sit on
a keyboard rig. 10 strings at 9.5 mm pitch at the bridge.

## Repository layout

| Path | What |
|---|---|
| `src/` | CadQuery source — one module per printed part + helpers |
| `tools/` | the checkers (`check_*.py` — overlaps, sweep, ceilings, walls, beads, dead code), `fast_build` (fast single-part iteration), `build_profile` (build-cost/regression gate), the web-viewer exporters |
| `elec/` | the PCB sources — schematic + layout + autoroute + fab output, generated with skidl/KiCad, one module per board |
| `cadkit/` | shared CAD library, vendored as a git subtree from its own repo and used by ten projects — edit it there, not here |
| `docs/` | GitHub Pages 3D viewer (`index.html` + `assembly.glb`) |
| `INSTALL_NOTES.md` | installation steps the CAD can't show (thread lock, order, settings) — raw notes for the future install doc |
| `BOM.md` | purchased parts with sourcing links and prices |
| `electromechanical-pedal-steel-spec.md` | the full design specification and rationale |
| `*.step` | generated geometry (per part + full assembly) |

---

Copyright © 2026 gustebeast. Licensed under CERN-OHL-S 2.0 — you may build,
modify, and sell hardware from these sources, but modified sources must remain
available under the same license.
