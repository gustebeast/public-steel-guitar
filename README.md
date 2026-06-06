# servo-steel

Parametric CAD for an **electro-mechanical pedal steel guitar** — one closed-loop
electric actuator per string, so the copedent becomes software-reconfigurable
instead of a maze of rods and bellcranks. See
[`electromechanical-pedal-steel-spec.md`](electromechanical-pedal-steel-spec.md)
for the full design rationale.

**Status:** mechanical design in CAD; no physical prototype yet.

## The keystone

Each string's pitch is set by a **carriage** on a **self-locking single-start
leadscrew**. Because the screw can't be back-driven, the motor is *off* at rest
and the screw holds the pitch — zero holding current, heat, or standing noise.
The motor only ever supplies the brief torque of a move.

Per-string chain: `motor → twisted belt → vertical leadscrew → carriage → string`.

## Layout (under-string, vertical screw)

Each string turns 90° over a **per-string ball bearing** at the bridge and runs
straight **down** to a short **vertical leadscrew**; the carriage travels in Z
over just the bend range, so the screws are short (~53 mm) with no whip. The
motors lie **flat under the speaking length** in a staircase (stepping along −X
so they don't collide), shaft facing +Y with the body toward the player. A
**twisted GT2 belt** turns each motor pulley (axis Y) to its screw pulley
(axis Z). Envelope ≈ 84 (thick) × 186 (across) × 632 (long) mm.

The carriage travel is sized from string physics (`f ∝ √stretch`): slack→open
take-up plus three whole steps of raise headroom — see `DL_OPEN` /
`CARRIAGE_TRAVEL` in `dimensions.py`.

## Build system

CadQuery (Python 3.12) generates a STEP per printed part plus an `assembly.step`
with per-part colours baked in.

```bash
py -3.12 -m src.build              # all parts + assembly.step
py -3.12 -m src.build --part NAME  # one part (fast iteration)
py -3.12 -m src.build --list       # list part names
py -3.12 -m src.build --geom       # print the belt-geometry report
```

- `src/dimensions.py` — global coordinate system (+X along the strings: +X
  changer, −X nut; +Y across; +Z up) and every constant.
- `src/components.py` — schematic dummies of purchased parts (motor, screw, nut,
  pulleys, support bushing, bridge bearings, belt, tuner) for the assembly only.
- Printed parts: `carriage` (×10), `screw_rail` (shared bottom support),
  `bridge_mount` (bridge-bearing axle support), `motor_bank` (staircase mounts),
  `belt_clamp`, `screw_pulley`, `motor_pulley`.
- `tools/check_overlaps.py` — `py -3.12 -m tools.check_overlaps` reports any
  unintended interpenetration between placed components (the design gate).

**Viewing:** the build writes `assembly.step` and opens (or refreshes) it in the
shared FreeCAD viewer hub (`../freecad/`), which watches the file and auto-reloads
on every rebuild, keeping the camera and hidden parts. To open it manually:
`& ..\freecad\open_viewer.ps1 -Project .`.

## Key dimensions

- 10 strings, fanning from 6.5 mm at the nut to 9.5 mm at the changer.
- 615 mm between a string's two mounting ends (≈24.2″ scale).
- Target envelope: ≤100 mm thick, ≤200 mm wide (single neck), ~800 mm long.
