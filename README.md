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

Per-string chain: `motor → belt → leadscrew → carriage → string`.

## Build system

CadQuery (Python 3.12) generates a STEP per printed part plus an `assembly.step`,
then pushes the assembly to Onshape.

```bash
py -3.12 -m src.build              # all parts + assembly + Onshape push
py -3.12 -m src.build --part NAME  # one part (fast iteration)
py -3.12 -m src.build --list       # list part names
py -3.12 -m src.build --geom       # print the §5 belt-geometry report
```

- `src/dimensions.py` — global coordinate system (+X across strings, +Y
  bridge→motor, +Z up) and every constant.
- `src/components.py` — schematic dummies of purchased parts (motor, screw,
  nut, bearing, pulley, belt, tuner) for the assembly only.
- Printed parts: `carriage`, `bearing_block` (open cradle), `bridge_mount`,
  `base_rail`, `motor_brick`.
- `tools/check_overlaps.py` — `py -3.12 -m tools.check_overlaps` reports any
  unintended interpenetration between placed components (the design gate).
- Onshape push is configured via `tools/onshape_credentials.json` (gitignored).

## Variants

A `COMPACT` switch in `dimensions.py` (env `PSG_COMPACT=0/1`, default on):

- **Compact (default):** small Ø5 hardware — leadscrew Ø5×1 (self-locking),
  slim nut, GT2 14T pulleys, single deep-groove support bearing + locknut. The
  carriages sit **inline in one Z plane** at the changer pitch.
- **Standard:** larger Ø8/T8 hardware in a 2-bank Y-stagger + Z-split.

## Key dimensions

- 10 strings, fanning from 6.5 mm at the nut to 9.5 mm at the changer.
- 615 mm between a string's two mounting ends (≈24.2″ scale).
- Target envelope: ≤100 mm thick, ≤200 mm wide (single neck), ~800 mm long.

## Driven end (current)

`screw → single deep-groove bearing → locknut → pulley`. The bearing sits in an
**open cradle** (saddle below + a −Y backstop) rather than an enclosing bore, so
all screws share one Z plane while neighbours clear. The bearing takes both the
radial location and the axial string load (~93 N, near-static); the locknut on
the screw thread is the axial retainer.
