"""place_geom.py: each footprint's LOCAL geometry, for placing without pcbnew (PLACEMENT.md).

    <KiCad python> place_geom.py <stem>        reads <stem>.kicad_pcb, writes <stem>.parts.json
    <KiCad python> place_geom.py <stem> [pads|courtyard] --from-net
                                               reads <stem>.net and the footprint libraries:
                                               no laid-out board needed (a FRESH board)

⚠ A FRESH BOARD HAS NO LAID-OUT COPY (motor_ctrl trial, 2026-11-11). Reading geometry off
a layout meant laying the board out first -- with placements it does not have -- and the
copy's rotations then rode along in parts.json's `at` into place_init as the default turn
of every part without a `rot` rule: the hand board's decisions, leaking into a placement
meant to be made without them. --from-net loads each component's footprint from the
libraries layout.py uses (PCBFLOW_FOOTPRINT_DIRS), gives its pads the netlist's nets, and
dumps it at the origin, rot 0, front side: geometry and nothing else.

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


def _net_board(stem):
    """A BOARD holding every component of <stem>.net at the origin, rot 0, front side,
    its pads on the netlist's nets -- built from the footprint libraries alone."""
    import re
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import layout                                       # FP_DIRS, _load_footprint, rings
    txt = open(stem + ".net", encoding="utf-8").read()
    notes = {}
    if os.path.exists(stem + ".board.json"):
        notes = json.load(open(stem + ".board.json", encoding="utf-8"))
    comps = {}
    for b in re.split(r"\(comp\s", txt)[1:]:
        m, f = re.search(r'\(ref "?([^")\s]+)', b), re.search(r'\(footprint "([^"]+)"', b)
        if m and f:
            comps[m.group(1)] = f.group(1)
    nodes = {}                                          # (ref, pin) -> net
    nets_txt = txt[txt.find("(nets"):] if "(nets" in txt else ""
    for b in re.split(r"\(net\s", nets_txt)[1:]:
        nm = re.search(r'\(name "([^"]*)"', b)
        if not nm:
            continue
        for r_, p_ in re.findall(r'\(node\s*\(ref "?([^")\s]+)"?\)\s*\(pin "?([^")\s]+)"?\)', b):
            nodes[(r_, p_)] = nm.group(1)
    # a one-pin net (KiCad's unconnected-pin nets, "U7_NC_7") carries nothing: the laid-out
    # board leaves those pads net-less, so the two paths give the same parts.json
    count = {}
    for n in nodes.values():
        count[n] = count.get(n, 0) + 1
    nodes = {k: n for k, n in nodes.items() if count[n] > 1}
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(int(notes.get("layers", 2)))
    netinfo = {}
    for n in sorted(set(nodes.values())):
        ni = pcbnew.NETINFO_ITEM(board, n)
        board.Add(ni)
        netinfo[n] = ni
    for ref, spec in sorted(comps.items()):
        fp = layout._load_footprint(spec)
        fp.SetReference(ref)
        try:
            layout._grow_thin_rings(fp, int(notes.get("layers", 2)), notes)
        except Exception:                               # noqa: BLE001 -- geometry still stands
            pass
        board.Add(fp)
        fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(SHEET[0]), pcbnew.FromMM(SHEET[1])))
        for q in fp.Pads():
            n = nodes.get((ref, q.GetNumber()))
            if n is not None:
                q.SetNet(netinfo[n])
    return board


def dump(stem, anchor="pads", from_net=False):
    board = _net_board(stem) if from_net else pcbnew.LoadBoard(stem + ".kicad_pcb")
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
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dump(os.path.abspath(args[0]), *(args[1:2] or []), from_net="--from-net" in sys.argv)
