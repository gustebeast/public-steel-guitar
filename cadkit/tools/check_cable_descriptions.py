"""Gate on the viewer's part DESCRIPTIONS, and every cable's length in one.

    py -3.12 cadkit/tools/check_cable_descriptions.py     # from a project root; exit 0 = holds

Draws a cable of each kind cadkit.cables makes, plus a part that is not one, sends them the
way a build does -- saved to an assembly STEP and read back by name, the trip on which both
the objects and their names are lost to cables.py -- through cadkit.web.export, and reads
the descriptions out of the .glb it wrote.
"""
from __future__ import annotations

import json
import math
import pathlib
import struct
import sys
import tempfile

# run as a script: the folder holding the cadkit package goes on the path
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import cadquery as cq  # noqa: E402

from cadkit import cables as C  # noqa: E402
from cadkit.web.export import export  # noqa: E402
from cadkit.web.view import step_parts  # noqa: E402


def _extras(glb):
    """The .glb's asset extras."""
    b = pathlib.Path(glb).read_bytes()
    n = struct.unpack_from("<I", b, 12)[0]
    return json.loads(b[20:20 + n])["asset"].get("extras", {})


def main():
    bent = [(0, 0, 0), (40, 0, 0), (40, 30, 0), (40, 30, 25)]          # 95 mm
    ribbon = [(0, 60, 0), (50, 60, 0), (50, 90, 0)]                     # 80 mm, one fold
    want = {"wire_bent": 95.0, "ribbon": 80.0,
            "coil": 3 * math.hypot(2 * math.pi * 6.0, 20.0 / 3)}      # 3 turns, r 6, 20 tall
    solids = {"wire_bent": C.oct_cable(bent, 1.7),
              "wire_twin": C.oct_cable([(0, -10, 0), (95, -10, 0)], 1.7),
              "ribbon": C.flat_cable(ribbon, 8.0, 1.0, across=(0, 0, 1)),
              "coil": C.helix_cable(80, -40, 0, 20, 3, 6.0, 1.2),
              "bracket": cq.Workplane("XY").box(10, 10, 10).translate((-30, 0, 0)),
              # drawn, then MOVED: its centroid is new, so it is not found (by design)
              "wire_moved": C.oct_cable([(0, 120, 0), (30, 120, 0)], 1.7).translate((0, 0, 40))}
    want["wire_twin"] = 95.0
    asm = cq.Assembly()
    for n, s in solids.items():
        asm.add(s, name=n)
    bad = 0
    with tempfile.TemporaryDirectory() as td:
        step = pathlib.Path(td) / "assembly.step"
        asm.save(str(step))
        parts = step_parts(str(step))
        glb, _side, _done = export(parts, pathlib.Path(td) / "out", quiet=True,
                                   extras={"notes": {"bracket": "an old-style note"}},
                                   descriptions={"wire_twin": "cut 120 mm"})
        d = _extras(glb).get("descriptions", {})

    def row(what, ok, got):
        print("  %-40s %-28r %s" % (what, got, "ok" if ok else "FAIL"))
        return 0 if ok else 1

    for n in ("wire_bent", "ribbon", "coil"):
        bad += row("%s says its drawn length" % n, d.get(n) == C.describe_length(want[n]),
                   d.get(n))
    # two cables of one length are told apart by WHERE they are, not by their volume
    bad += row("the project's own line outranks the cable's", d.get("wire_twin") == "cut 120 mm",
               d.get("wire_twin"))
    bad += row("the old 'notes' spelling is still read", d.get("bracket") == "an old-style note",
               d.get("bracket"))
    bad += row("a cable moved after drawing is not guessed", "wire_moved" not in d,
               d.get("wire_moved"))
    bad += row("nothing else is described", set(d) <= set(solids), sorted(set(d) - set(solids)))
    page = (pathlib.Path(C.__file__).parent / "web" / "viewer" / "index.html").read_text(
        encoding="utf-8")
    ok = ("about.descriptions" in page and 'class="desc"' in page and ".panel .desc" in page)
    bad += row("the page reads them and draws them as .desc", ok, ok)
    print("\n%s" % ("descriptions hold" if not bad else "*** %d FAILURE(S) ***" % bad))
    return bad


if __name__ == "__main__":
    sys.exit(main())
