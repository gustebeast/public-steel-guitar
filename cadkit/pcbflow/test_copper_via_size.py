"""Declared copper keeps its via size.  py -3.12 test_copper_via_size.py

An intent `copper` via is [x, y] or [x, y, drill, d]; place_flow._copper must hand layout
[net, x, y, drill, d] (brain_board 2026-11-25: it dropped the size, so every declared via was
laid at 0.3 / 0.6 and +24V_LED's 0.8 / 0.5 ECO vias could not be declared)."""
import place_flow

notes = {}
place_flow._copper(notes, None, [{"kind": "copper", "net": "N", "key": "k", "tracks": [],
                                  "vias": [[1.0, 2.0, 0.5, 0.8], [3.0, 4.0]]}])
want = [["N", 1.0, 2.0, 0.5, 0.8], ["N", 3.0, 4.0]]
ok = notes.get("vias") == want
print("ok " if ok else "BAD", "declared via size reaches notes:", notes.get("vias"))
raise SystemExit(0 if ok else 1)
