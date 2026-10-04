"""Silkscreen a FINISHED board: its name and revision, what each test pad is, what each
connector pin carries. Run after routing (finish.py does), on the board already on disk.

    "C:/Program Files/KiCad/10.0/bin/python.exe" elec/silk.py elec/out/motor_ctrl [...]

The labeller is cadkit's (`cadkit/kicad_silk.py` -- what it prints, and why no label can
add a DRC finding, are documented there). This is the project's entry point: it supplies
the revision, and each board's `strip_silk` note as the parts no ink may come near (the
optical board strips its sensors' own outlines and is ordered in black mask).

WHY THE PROJECT HAS IT AT ALL (user, 2026-10-02: a friend's board had "silkscreen labels
for all of the components, not sure if that's valuable for us"): surveyed that day, not
one board here carried a single character of board-level text -- see
docs/pcb-order-review.md.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cadkit import kicad_silk  # noqa: E402

REV = "r1"                 # bumped by hand when a board is RE-ORDERED with changed copper


def silk(stem):
    try:
        with open(stem + ".board.json", encoding="utf-8") as fh:
            notes = json.load(fh)
    except OSError:
        notes = {}
    return kicad_silk.silk(stem, REV, tuple(notes.get("strip_silk", ())))


if __name__ == "__main__":
    # one board per process -- see cadkit.kicad_silk.main
    _stems = [a[:-10] if a.endswith(".kicad_pcb") else a for a in sys.argv[1:]]
    if len(_stems) == 1:
        silk(_stems[0])
    else:
        for _stem in _stems:
            _p = subprocess.run([sys.executable, os.path.abspath(__file__), _stem],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            sys.stdout.write("".join(ln + chr(10) for ln in _p.stdout.splitlines()
                                     if "image handler" not in ln and "memory leak" not in ln))
            if _p.returncode:
                raise SystemExit("silk.py failed on %s" % _stem)
