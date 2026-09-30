# Public Steel Guitar

Open-source parametric CAD for an **electro-mechanical pedal steel guitar**:
one closed-loop electric actuator per string, so the copedent — the mapping
from pedals and knee levers to pitch changes — becomes **software
configuration** instead of a hand-built maze of rods and bellcranks.

**Status:** CAD and electronics in progress; no physical prototype yet. The
mechanism is build-verified geometry (every commit is gated for part collisions,
swept collisions, wall thickness and unsupported overhangs), and **ten custom
PCBs are generated, routed and fab-packaged from source** — see `elec/`. What
does not exist yet is firmware: the copedent lives in a data table the 3D viewer
reads, and nothing commands a motor. [`docs/design-validation.md`](docs/design-validation.md)
tracks what the instrument can and cannot yet be shown to do, behaviour by
behaviour, including the open items. See
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
fixed in hardware. Here, each of the 10 strings terminates on the **nut of its
own self-locking leadscrew**, driven by a **closed-loop stepper** (MKS SERVO42D).
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
- String termination is a **wrap capstan**: over a Ø2 break dowel, around a
  shared Ø8 rod for ~3 turns, then into one clamp screw. The capstan is the
  point — Euler-Eytelwein takes 147 N at the bridge down to ~5-9 N at the
  clamp, so the clamp holds a tail rather than a string.
- **There is no printed carriage.** The leadscrew's own H-nut does both jobs:
  its +X ear anchors the string (ball end underneath, tension pulling it up
  against the ear, exactly a guitar bridge plate) and its -X ear rides the
  guide rod. That deleted a printed part ×10, twenty M2 screws and ten spacers.
- ⚠ **Travel stops are NOT built.** Both hard stops and the guide rod's upper
  retention are deferred, so nothing mechanical bounds a commanded move and the
  instrument needs firmware soft limits before it is driven. The nut stays
  fully engaged for 17.4 mm of over-travel — twice the whole travel — and the
  ears reach structure 4 mm up, so a runaway stalls rather than escapes, but
  that is a backstop and not a design. See `docs/design-validation.md` B11.

## How the mechanism works

**The string's path** (from the player's left): each string's plain end runs
over a Ø2 steel **break dowel** in the **nut block** — a removable, reprintable
PETG-GF block — then takes about three turns around a shared **Ø8 wrap rod**
before one cup-point set screw clamps the tail. The capstan is the whole point:
Euler-Eytelwein takes 147 N at the bridge down to **~5-9 N at the clamp**, so
the screw holds a tail rather than a string, and the clamp is no longer asked
for 490 N. The speaking length (615 mm, ≈24.2″ scale) runs to the bridge, turns
90° over a **per-string 688ZZ bearing** on a Ø8 ground shaft (so the bend is
near-frictionless and tension equalizes across it), and drops vertically to the
**leadscrew's own nut**. The ball end sits under that nut's +X ear with the
string up through a Ø3 hole — tension pulls the ball against the ear, exactly a
guitar bridge plate — so restringing needs no tools at the moving end.

**The drive** (per string): `MKS SERVO42D closed-loop stepper (CAN) → GT2 belt
(twisted 90°, 1:1) → screw pulley → Tr8×2 vertical leadscrew (37.7 mm) → its
own H-nut → string`. **There is no printed carriage**: the nut's two mounting
ears do both jobs one did — the +X ear anchors the string, the -X ear rides a
**Ø3.5 hardened guide rod** for anti-rotation. An axial thrust path (support
bearing + a second bearing up in the endplate slab) carries the string pull,
which is off-axis by 8 mm and therefore a standing ~956 N·mm couple.

The screw is what holds tune with the motors unpowered, and that is a friction
argument rather than a property of the part: mean Ø7, 2 mm lead, a **5.20° lead
angle**, so it is self-locking while μ ≥ 0.088 — comfortable dry or greased, and
**not** self-locking on a PTFE-loaded lubricant. Do not lubricate these screws.

Total travel is **8.35 mm**, budgeted as 4.00 mm of slack-to-pitch take-up when
the string goes on, 2.35 mm for four semitones of raise, and 2.00 mm of margin
for break-in. A semitone is about 0.5 mm at the modelled stretch — but the real
figure varies several-fold per string with gauge and construction, which is one
of the open items in `docs/design-validation.md`.

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
both endplates, leg tubes — **PCTG** for compliant and
fine-feature parts and the whole deck (nothing snaps: no flex fitting anywhere
in the instrument, by design) — the panels print as two-filament
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

**Electronics** (firmware not in this repo — see `elec/` for the boards): a
**CH32V307** on the motor-controller board reads the control sensors and speaks
CAN to the ten servos, and a **Raspberry Pi 5** does everything else — audio,
UI, copedent. The split is a latency decision: the MCU runs only the
sensor→motor loop with saved offsets, so nothing in the playing path waits on
Linux. There is no Teensy and no ADC stack; the CH32V307 absorbed the first and
the optical pickup board the second. The two live in the keyhead bay, mounted
on cradles fused into the endplate rather than on a tray.

**Two CAN buses**, both classic at 500 kbps because the SERVO42D is
classic-only: **bus A** carries 24 V and CAN to the ten motors on their own
pigtails, fed from **both ends** of the trunk so the worst-loaded segment
carries about half the fleet. **Bus B** is a 5 V trunk-and-drop for the control
sensors, so unplugging a control never breaks the bus.

Panel I/O (1/4" TS line out, DC inlet, USB) is on the **output + panel board**
at the bridge end, which also carries the whole magnetic audio path: ADC, DAC,
USB hub, and a **true-bypass relay** — de-energized, the raw pickup runs
straight to the jack with no converters in the path; energized, the processed
output goes instead. The ADC is fed either way, so pitch detection always
works. The modeled harness is
color-coded per electrical net (spliced runs share a color; every unique
source→dest pairing differs) and routed through diamond raceways in the
cross-ribs; the overlap gate verifies the wires touch nothing but their own
endpoints. A **removable top deck** (PCTG panels riding grooves in the rail tops so they
can't fall off when inverted, yet pull out toward -X for motor service once the
keyhead endplate is off) covers the motors + electronics, carries printed
fret-position lines, doubles as a hand rest, and mounts the **UI station**: a
display and one Alps multi-control (rotary + 4-way + push) on their own routed
board, held by two deck spigots for X, Y and rotation with a single M4 for Z.

The bridge end of the deck is split into 20 mm slots. A **pickup-carrier piece**
holds the pickup as a tray: it pokes up through an opening and rests on three M4
leadscrew jacks standing on a **floor that runs under it** — turn them from
above to set the string gap, with the heads captured in the deck and the plate
riding the thread as a heat-set nut, for about 12 mm of travel. The pickup is
retained to the plate alone: a +Y wall it butts against, and a horizontal M4
grub pushing it into that wall, so the plate still travels. Coarse
bridge-to-neck position comes from re-slotting the piece; the plate slides ±17
on it for fine tone position. The remaining slots take **swappable filler
bands** — and they are now one part, not three: the bands carry no fret lines,
so any band fits any slot.

⚠ The deck's lighting is in flight: a body strip along the +Y rail, fret-marker
boards behind the deck panels, and a down-firing foot strip, all generated in
`elec/` and all of them newer than this paragraph.
The playing path is pure feed-forward — pedal moves map directly to motor
positions, so there is no pitch-tracking latency while playing. A per-string
pickup (e.g. a hex/multichannel pickup) feeds slow pitch detection used only
when calibrating: it measures each open string and corrects the
position→pitch map, absorbing drift from temperature, creep, or string aging.
The servos retune the instrument on demand; there are no manual tuning
machines anywhere.

## Building the CAD

CadQuery on Python 3.12 generates a STEP file per printed part plus a colored
`assembly.step`. The assembly places ~960 components: the printed parts, every
purchased-part dummy, the ten PCBs read back from their own routed geometry, and
the wiring harness drawn as real cable — every conductor, with its connectors.

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
py -3.12 -m tools.check_cable_pairs # two cables sharing one lane -- the overlap gate treats
                                   #   wire-on-wire as an insulated crossing, so it cannot see it
py -3.12 -m tools.check_part_specs # the CAD's board dimensions against the ROUTED boards
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
  - **UI**: `ui_clamp`, `ui_knob` — the deck's control station, a display and
    one Alps multi-control, clamped by plastic with a single M4 for Z only
  - **legs**: `fixed_sleeve`/`adjust_sleeve`, `fixed_tenon`/`adjust_tenon`,
    `body_adapter*`, `leg_foot` (TPU), and the latch set
  - **coupons**: `test_*` — print-fit test pieces, not part of the instrument
- Every gate exits non-zero on a finding, and `src.build` runs the overlap and
  sweep gates itself on the model it just built.

Envelope ≈ 100 × 200 × 655 mm (thick × across × long) — thin enough to sit on
a keyboard rig. 10 strings at 9.5 mm pitch at the bridge.

## The electronics

Ten boards, each generated from Python rather than drawn: schematic in
[skidl](https://github.com/devbisme/skidl), placement and autoroute driven from
the same source, then DRC and a fab package. The CAD reads every board back from
its own routed geometry (`elec/geom/*.geom.json`), so the plastic cannot drift
from the board it has to hold.

| Board | What it does |
|---|---|
| `optical` | per-string optical pickup + the analog front end; pitch detection for the calibration loop |
| `output_panel` | the front panel and the whole magnetic audio path — ADC, DAC, USB hub, true-bypass relay |
| `motor_ctrl` | CH32V307 + two CAN transceivers: the sensor→motor loop, and both buses' upstream end |
| `lever_sensor` | one per control — an MT6701 reading a diametric magnet on the control's axle |
| `can_tee` | a bus junction so unplugging any device never breaks the trunk |
| `ui_board` | the deck's display + multi-control station |
| `led_strip` | body lighting, four sections along the +Y rail |
| `fret_led_mid` / `fret_led_key` | fret-marker lighting, one board per deck panel |
| `foot_led` | down-firing foot lighting |

```bash
py -3.12 elec/finish.py elec/out/BOARD   # place, route, DRC and package one board
py -3.12 -m elec.audit_board BOARD       # the checks that outlive a DRC report
py -3.12 -m elec.cad_geom_check          # every board against the CAD that holds it
```

⚠ A `*-drc.rpt` in the repository root is **not** evidence — those files go stale
silently. `finish.py` and `audit_board.py` are the record.

## Repository layout

| Path | What |
|---|---|
| `src/` | CadQuery source — one module per printed part + helpers |
| `tools/` | the checkers (`check_*.py` — overlaps, sweep, ceilings, walls, beads, dead code), `fast_build` (fast single-part iteration), `build_profile` (build-cost/regression gate), the web-viewer exporters |
| `elec/` | the PCB sources — schematic + layout + autoroute + DRC + fab output, generated with skidl/KiCad, one module per board |
| `elec/geom/` | each routed board's measured geometry, committed — what the CAD reads so the plastic tracks the board |
| `cadkit/` | shared CAD library, vendored as a git subtree from its own repo and used by ten projects — edit it there, not here |
| `docs/` | GitHub Pages 3D viewer (`index.html` + `assembly.glb`), and the design notes below |
| `docs/design-validation.md` | what the instrument can and cannot yet be shown to do, behaviour by behaviour, with the open items |
| `INSTALL_NOTES.md` | installation steps the CAD can't show (thread lock, order, settings) — raw notes for the future install doc |
| `BOM.md` | purchased parts with sourcing links and prices |
| `electromechanical-pedal-steel-spec.md` | the full design specification and rationale |
| `*.step` | generated geometry (per part + full assembly) |

---

Copyright © 2026 gustebeast. Licensed under CERN-OHL-S 2.0 — you may build,
modify, and sell hardware from these sources, but modified sources must remain
available under the same license.
