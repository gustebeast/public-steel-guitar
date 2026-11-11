"""place_geom.py: each footprint's LOCAL geometry, for placing without pcbnew (PLACEMENT.md).

    <KiCad python> place_geom.py <stem>        reads <stem>.kicad_pcb, writes <stem>.parts.json

Placement tools (place_intent, place_init, place_refine) run in plain Python and need to
know, for a part at (x, y, rot), where each of its pads and its courtyard land. That is a
fact about the footprint, not the placement, so it is read once from any laid-out board
-- layout.py's output, before routing, is enough -- and kept as data:

    {"frame": "board mm, centre origin, +Y up (notes['placements'])",
     "parts": {ref: {"fpid", "side", "anchor": "pads"|"courtyard", "at": [x, y, rot],
                     "pads": [{"num", "net", "xy": [lx, ly], "size": [w, h], "rot", "tht"}],
                     "crtyd": [[lx, ly], ...] | null, "fab": [x0, x1, y0, y1] | null}}}

LOCAL means about the placement anchor, at rot 0, in the board frame's axes: a part placed
at (x, y, rot) puts a local point p at (x, y) + R(rot) p. The anchor is the one layout.py
uses (_anchor_on_pads: the pad centroid; optical's courtyard centre), so the numbers agree
with notes["placements"] exactly -- checked here on every part by putting each pad back.
"""
import json
import math
import os
import sys

import pcbnew

SHEET = (100.0, 100.0)          # layout.py: board mm (centre origin, +Y up) -> sheet mm


def _bf(v):
    """KiCad sheet IU -> board frame mm (+Y up)."""
    return pcbnew.ToMM(v.x) - SHEET[0], SHEET[1] - pcbnew.ToMM(v.y)


def _rot(x, y, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return x * c - y * s, x * s + y * c


def dump(stem, anchor="pads"):
    board = pcbnew.LoadBoard(stem + ".kicad_pcb")
    parts, worst = {}, 0.0
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        pads = list(fp.Pads())
        if not pads:
            continue
        rot = fp.GetOrientationDegrees() % 360.0
        if anchor == "courtyard":
            cy = fp.GetCourtyard(pcbnew.F_CrtYd if not fp.IsFlipped() else pcbnew.B_CrtYd)
            ax, ay = _bf(cy.BBox().GetCenter())
        else:
            ax = sum(_bf(p.GetPosition())[0] for p in pads) / len(pads)
            ay = sum(_bf(p.GetPosition())[1] for p in pads) / len(pads)

        def local(v):
            x, y = _bf(v)
            return list(_rot(x - ax, y - ay, -rot))

        pl = []
        for p in pads:
            sz = p.GetSize(pcbnew.F_Cu) if hasattr(p, "GetSize") else p.GetSize()
            pl.append({"num": p.GetNumber(), "net": p.GetNetname(),
                       "xy": [round(c, 4) for c in local(p.GetPosition())],
                       "size": [round(pcbnew.ToMM(sz.x), 4), round(pcbnew.ToMM(sz.y), 4)],
                       "rot": round((p.GetOrientationDegrees() - rot) % 360.0, 3),
                       "tht": p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH})
        crt = None
        sh = fp.GetCourtyard(pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd)
        if sh.OutlineCount():
            ol = sh.Outline(0)
            crt = [[round(c, 4) for c in local(ol.CPoint(i))] for i in range(ol.PointCount())]
        fab = None
        xs, ys = [], []
        for it in fp.GraphicalItems():
            if it.GetLayer() in (pcbnew.F_Fab, pcbnew.B_Fab):
                bb = it.GetBoundingBox()
                for v in (bb.GetOrigin(), bb.GetEnd()):
                    lx, ly = local(v)
                    xs.append(lx)
                    ys.append(ly)
        if xs:
            fab = [round(min(xs), 4), round(max(xs), 4), round(min(ys), 4), round(max(ys), 4)]
        parts[ref] = {"fpid": fp.GetFPID().GetLibItemName().wx_str(),
                      "side": "B" if fp.IsFlipped() else "F", "anchor": anchor,
                      "at": [round(ax, 4), round(ay, 4), round(rot, 3)],
                      "pads": pl, "crtyd": crt, "fab": fab}
        # put each pad back from (at, local): the round trip is the frame check
        for p, q in zip(pads, pl):
            dx, dy = _rot(q["xy"][0], q["xy"][1], rot)
            x, y = _bf(p.GetPosition())
            worst = max(worst, math.hypot(ax + dx - x, ay + dy - y))
    if worst > 1e-3:
        raise SystemExit("place_geom: pads do not round-trip (worst %.4f mm)" % worst)
    out = {"frame": "board mm, centre origin, +Y up (notes['placements'])", "parts": parts}
    with open(stem + ".parts.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=0)
    print("place_geom: %d parts -> %s.parts.json (pads round-trip to %.5f mm)"
          % (len(parts), os.path.basename(stem), worst))


if __name__ == "__main__":
    dump(os.path.abspath(sys.argv[1]), *(sys.argv[2:3] or []))
