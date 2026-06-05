"""Electro-Mechanical Pedal Steel Guitar — cadquery model.

Split into focused modules:

  dimensions  — coordinate system + all dimensional/material/fit constants
  helpers     — geometric helpers (cyl, box_at, nema17 bolt pattern, heal)
  components  — purchased-part DUMMIES (motor, screw, nut, pulleys, bearings,
                guide rod, roller bridge, locking tuner, belt) for the
                assembly only; not exported as printable STEPs
  carriage    — the moving carriage (PA6-GF, load-critical) ×10
  bearing_block — driven-end bearing cradle (single deep-groove bearing) ×10
  bridge_mount  — roller-bridge holder + string-anchor geometry
  base_rail   — chassis base + near-support walls (screw + guide-rod seats)
  motor_brick — the §5 belt-offset 2-layer motor holder
  build       — composes one actuator axis ×10 + the motor brick into an
                assembly, writes per-part STEPs + assembly.step, and pushes
                the assembly to Onshape.

Run from the repo root:
  py -3.12 -m src.build              # build all parts + assembly + push
  py -3.12 -m src.build --part NAME  # build one part (fast iteration)
  py -3.12 -m src.build --list       # list part names
"""
