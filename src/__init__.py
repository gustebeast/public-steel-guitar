"""Electro-Mechanical Pedal Steel Guitar — cadquery model.

The instrument is the direct-drive one (src.direct_bench, user 2026-11-13); the v1
belt-drive instrument is at the git tag v1-instrument. The main modules:

  dimensions      — coordinate system + the dimensional/material/fit constants
  helpers         — geometric helpers (cyl, cyl_y, box_at, heal, ...)
  components      — purchased-part DUMMIES for the assembly; never exported as prints
  direct_bench    — the instrument: body, endplates, drives, and its own gate rules
  keyhead_v2, nut_block_v2, motor_coupler — the keyhead and the drive's printed parts
  deck_v2, deck_v2_region, deck_layout, fret_light, ui_panel, optical_pickup — the deck,
                    its lights, the UI station and the optical pickup board
  build           — composes everything into a colour-coded assembly, writes
                    per-part STEPs and the web viewer's model, runs the gates.

Run from the repo root:
  py -3.12 -m src.build              # build all parts + the viewer's model
  py -3.12 -m src.build --part NAME  # build one part (fast iteration)
  py -3.12 -m src.build --list       # list part names
"""
