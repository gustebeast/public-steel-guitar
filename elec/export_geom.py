"""Read a ROUTED board back and write the geometry the CAD needs: <stem>.geom.json.

    "C:/Program Files/KiCad/10.0/bin/python.exe" elec/export_geom.py elec/out/output_panel

writes elec/geom/output_panel.geom.json -- TRACKED, unlike elec/out, because the CAD builds
from it and a checkout without KiCad has to be able to. finish.py runs this at the end of
every board run, so the file is rewritten whenever the board is.

WHY THIS EXISTS. Every other file in the pipeline flows ONE way: the netlist and
board.json go INTO layout, and the routed board comes out. Nothing ever read the
finished board back. So the CAD modelled each board from a hand-typed table of anchors
and COURTYARD boxes -- and cad_geom_check compared that table to board.json's
placements, which are the same numbers layout was GIVEN. A copy checked against its
source always passes. It passed while:

  * both panel connectors' BODIES stopped 0.54 mm short of the board edge (the layout
    had put their courtyards flush, and a courtyard is the keep-out, not the part), and
  * the 24 V barrel jack faced ALONG the board at the chassis rail, because at 0 degrees
    that footprint's mouth is its local +Y. The CAD drew it as a panel inlet.

This file is the other direction: it reads what KiCad actually placed.

FRAME: board-centred millimetres, +X right, +Y UP (KiCad's Y is down; flipped here so
the numbers are the ones src/ uses). "fab" is the part's F.Fab outline -- the drawn
BODY -- and "crtyd" its courtyard. A footprint with no F.Fab gets null and the CAD has to
say what to do about it rather than quietly use the courtyard.
"""
import json
import os
import sys

import pcbnew

GEOM_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "geom")


def _bbox(fp, layer, cx, cy):
    xs, ys = [], []
    for it in fp.GraphicalItems():
        if it.GetLayerName() != layer:
            continue
        b = it.GetBoundingBox()
        xs += [b.GetLeft() / 1e6 - cx, b.GetRight() / 1e6 - cx]
        ys += [-(b.GetTop() / 1e6 - cy), -(b.GetBottom() / 1e6 - cy)]
    if not xs:
        return None
    return [round(min(xs), 3), round(max(xs), 3), round(min(ys), 3), round(max(ys), 3)]


def export(stem):
    board = pcbnew.LoadBoard(stem + ".kicad_pcb")
    edge = board.GetBoardEdgesBoundingBox()
    cx = (edge.GetLeft() + edge.GetRight()) / 2e6
    cy = (edge.GetTop() + edge.GetBottom()) / 2e6
    # the Edge.Cuts LINE has width; the board's edge is its centre, so take the
    # stroke back off (outline_mm in board.json is the same centre-line figure)
    lw = 0.0
    for d in board.GetDrawings():
        if d.GetLayerName() == "Edge.Cuts":
            lw = max(lw, d.GetWidth() / 1e6)
    out = {
        "outline_mm": [round(edge.GetWidth() / 1e6 - lw, 3),
                       round(edge.GetHeight() / 1e6 - lw, 3)],
        "thickness_mm": round(board.GetDesignSettings().GetBoardThickness() / 1e6, 3),
        "footprints": [],
    }
    for fp in board.GetFootprints():
        p = fp.GetPosition()
        out["footprints"].append({
            "ref": fp.GetReference(),
            "fpid": fp.GetFPIDAsString(),
            "x": round(p.x / 1e6 - cx, 3),
            "y": round(-(p.y / 1e6 - cy), 3),
            "rot": round(fp.GetOrientationDegrees(), 3),
            "side": "B" if fp.IsFlipped() else "F",
            "fab": _bbox(fp, "B.Fab" if fp.IsFlipped() else "F.Fab", cx, cy),
            "crtyd": _bbox(fp, "B.CrtYd" if fp.IsFlipped() else "F.CrtYd", cx, cy),
        })
    out["footprints"].sort(key=lambda f: f["ref"])
    dst = os.path.join(GEOM_DIR, os.path.basename(stem) + ".geom.json")
    os.makedirs(GEOM_DIR, exist_ok=True)
    with open(dst, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1)
        fh.write("\n")
    missing = [f["ref"] for f in out["footprints"] if f["fab"] is None]
    print("%s.geom.json: %d footprints, board %.2f x %.2f%s"
          % (os.path.basename(stem), len(out["footprints"]), out["outline_mm"][0],
             out["outline_mm"][1],
             ("; NO F.Fab body on " + ", ".join(missing)) if missing else ""))


if __name__ == "__main__":
    for a in sys.argv[1:]:
        export(os.path.abspath(a))
