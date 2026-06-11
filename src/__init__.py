"""Electro-Mechanical Pedal Steel Guitar — cadquery model.

Split into focused modules:

  dimensions      — coordinate system + all dimensional/material/fit constants
  helpers         — geometric helpers (cyl, cyl_y, box_at, nema17 cutter, heal)
  components      — purchased-part DUMMIES (motor, screw, nut, pulleys,
                    bearings, guide rod, dowels, set screws, belt) for the
                    assembly only; not exported as printable STEPs
  carriage        — the moving carriage (PA6-GF, load-critical) ×10
  screw_rail      — shared bottom screw-support rail (fused into the endplate)
  bridge_endplate — one-piece bridge end: box closure + bearing arms + axle
                    comb + guide ledges (absorbs screw_rail)
  chassis         — the rigid frame (rails, ribs, keyhead), split into 3
                    dovetailed segments; absorbs motor_bank
  motor_bank      — under-string staircase motor faceplate walls
  nut_block       — removable gauged keyhead string termination
  belt_clamp      — GT2 splice clamp (closes each cut belt into a loop)
  tension_fork    — graded belt-tension lock plugs for the motor slots
  build           — composes everything into a colour-coded assembly, writes
                    per-part STEPs + assembly.step (the refresh signal for the
                    shared FreeCAD live viewer).

Run from the repo root:
  py -3.12 -m src.build              # build all parts + assembly.step
  py -3.12 -m src.build --part NAME  # build one part (fast iteration)
  py -3.12 -m src.build --list       # list part names
"""
