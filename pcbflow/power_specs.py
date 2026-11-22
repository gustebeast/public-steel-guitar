"""power_specs.py STEM OUT.json -- one widepath spec per quality.power_paths entry, for the
rasterpath pre-order gate (and the same ends close_last's CLOSE_POUR_GUARD=2 builds).

    KiCad-python cadkit/pcbflow/power_specs.py elec/out/brain_board OUT.json

Each END is every pad of the named part on the path's net (a USB-C socket's four VBUS pins, a
FET's four drain pins), as polygons in BOARD mm (y down) per copper layer; `need` is
quality.required_width_mm(amps) on an outer layer; `scale` turns inner-layer width into
outer-equivalent width (IPC-2221: k 0.024 vs 0.048 and the inner copper weight), so one `need`
judges every layer.
"""
import json
import math
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from quality import required_width_mm  # noqa: E402

_CU = (("F", "F.Cu"), ("I1", "In1.Cu"), ("I2", "In2.Cu"), ("B", "B.Cu"))


def _to_b(x, y):
    """layout's frame (notes' tracks / pin_escapes, y up) -> board IU, as layout._to_board."""
    import re as _re
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "layout.py"), encoding="utf-8").read()
    ox, oy = [float(v) for v in _re.search(r"^SHEET_ORIGIN\s*=\s*\(([-\d.]+),\s*([-\d.]+)\)", src, _re.M).groups()]
    return pcbnew.FromMM(ox + x), pcbnew.FromMM(oy - y)


def _escape_polys(notes, ref, net, lid):
    """{layer key: [polygon]} of the declared pin-escape stubs (place_intent.pin_escapes, notes band_escapes) of `ref`
    on `net`, in board mm: the gate counts them as the pad (a stub no longer than 2 x pitch)."""
    out = {}
    for e in (notes or {}).get("band_escapes", ()) or ():
        if e["net"] != net or e["key"].split(".", 1)[0] != ref or e.get("beyond", 0) > 2 * e.get("pitch", 0) + 1e-6:
            continue
        k = next((k for k, L in _CU if L == e["layer"] and k in lid), None)
        if k is None:
            continue
        (ax, ay), (bx, by) = [pcbnew.ToMM(v) for v in _to_b(*e["pts"][0])], [pcbnew.ToMM(v) for v in _to_b(*e["pts"][1])]
        dx, dy = bx - ax, by - ay
        L_ = math.hypot(dx, dy) or 1.0
        nx_, ny_ = -dy / L_ * e["width"] / 2.0, dx / L_ * e["width"] / 2.0
        out.setdefault(k, []).append([[ax + nx_, ay + ny_], [bx + nx_, by + ny_], [bx - nx_, by - ny_], [ax - nx_, ay - ny_]])
    return out


def end_polys(board, ref, net, lid):
    """{layer: [polygon [[x, y], ...] mm]} of every pad of `ref` on `net`."""
    TM = pcbnew.ToMM
    fp = board.FindFootprintByReference(ref)
    out = {}
    for p in fp.Pads():
        if p.GetNetname() != net:
            continue
        for k, L in lid.items():
            if not p.IsOnLayer(L):
                continue
            sps = pcbnew.SHAPE_POLY_SET()
            p.TransformShapeToPolygon(sps, L, 0, pcbnew.FromMM(0.005), pcbnew.ERROR_INSIDE)
            for i in range(sps.OutlineCount()):
                o = sps.Outline(i)
                out.setdefault(k, []).append([[TM(o.CPoint(j).x), TM(o.CPoint(j).y)]
                                              for j in range(o.PointCount())])
    return out


def _merge(a, b):
    for k, v in b.items():
        a.setdefault(k, []).extend(v)
    return a


def specs(board, notes):
    q = notes.get("quality") or {}
    lid = {k: board.GetLayerID(L) for k, L in _CU if board.IsLayerEnabled(board.GetLayerID(L))}
    one = required_width_mm(1.0, "F.Cu", q)
    scale = {k: (1.0 if L in ("F.Cu", "B.Cu") else one / required_width_mm(1.0, L, q))
             for k, L in _CU if k in lid}
    # ⚠ ONE PATH PER PART PAIR, NOT PER PIN (brain_board rPS_g1, 2026-11-21): U221.7>F202.1 and
    # U221.8>F202.1 were judged as two 2 A paths, each FAIL at 0.34 mm. An end is already every
    # pad of the part on the net (end_polys), so the two were the same path counted twice: the
    # parallel pins are one pad-group end, and the current through them is the path's, not each
    # pin's. Same net + same two parts -> one path at the largest declared current.
    by = {}
    for e in q.get("power_paths") or ():
        amps = float(e.get("amps", 0) or 0)
        if amps <= 0:
            continue
        to = e["to"][0] if isinstance(e["to"], list) else e["to"]
        k = (e["net"], e["from"].split(".")[0], to.split(".")[0])
        if k not in by:
            by[k] = dict(net=e["net"], amps=amps, frm=[e["from"]], to=[to])
        else:
            by[k]["amps"] = max(by[k]["amps"], amps)
            by[k]["frm"] += [x for x in [e["from"]] if x not in by[k]["frm"]]
            by[k]["to"] += [x for x in [to] if x not in by[k]["to"]]
    out = []
    for (net, ra, rb), v in by.items():
        out.append(dict(name="%s %s>%s" % (net, "+".join(v["frm"]), "+".join(v["to"])), net=net,
                        amps=v["amps"], need=round(required_width_mm(v["amps"], "F.Cu", q), 3),
                        a=_merge(end_polys(board, ra, net, lid), _escape_polys(notes, ra, net, lid)),
                        b=_merge(end_polys(board, rb, net, lid), _escape_polys(notes, rb, net, lid))))
    return dict(scale=scale, specs=out)


if __name__ == "__main__":
    stem = sys.argv[1]
    b = pcbnew.LoadBoard(stem + ".kicad_pcb")
    d = specs(b, json.load(open(stem + ".board.json", encoding="utf-8")))
    json.dump(d, open(sys.argv[2], "w"))
    print("power_specs: %d paths, scale %s" % (len(d["specs"]), d["scale"]))
    sys.stdout.flush()
    os._exit(0)
