"""Electro-Mechanical Pedal Steel Guitar — cadquery model.

Split into focused modules:

  dimensions  — coordinate system + all dimensional/material/fit constants
  helpers     — geometric helpers (cyl, cyl_y, box_at, nema17 cutter, heal)
  components  — purchased-part DUMMIES (motor, screw, nut, pulleys, bearings,
                guide rod, bridge bearings, locking tuner, belt) for the
                assembly only; not exported as printable STEPs
  carriage    — the moving carriage (PA6-GF, load-critical) ×10
  screw_rail  — shared bottom rail holding all 10 screw support bushings
  bridge_mount — bridge-bearing axle support (uprights + tie bar)
  motor_bank  — under-string staircase motor mounts (faceplate walls + floor)
  build       — composes 10 actuator axes + the bridge + motor bank into a
                colour-coded assembly, writes per-part STEPs + assembly.step
                (the refresh signal for the shared FreeCAD live viewer).

Run from the repo root:
  py -3.12 -m src.build              # build all parts + assembly.step
  py -3.12 -m src.build --part NAME  # build one part (fast iteration)
  py -3.12 -m src.build --list       # list part names
"""
