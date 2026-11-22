"""return_vias.py <stem>: a GND via beside every layer change of a declared pair that switches
reference plane.

⚠ A PAIR'S RETURN CURRENT CHANGES PLANE WITH IT (lead, 2026-11-17, brain_board USB groups at
max_vias 4). A high-speed pair that drops from F.Cu (referenced to the In1 GND plane) to B.Cu
(referenced to In2) leaves its return current on a plane it has no way off; the loop it then
finds is the EMI and the impedance step. The rule: every such via has a GND via within the
group's `return_via_mm` (verify.py / quality A3 checks it), and nothing in the chain laid one --
the router routes signals, and the stitches go in before it, nowhere near a pair's vias.

So, after the route, on the board that won: for each group in notes["match"] that declares
return_via_mm, at each of its nets' vias whose copper joins layers with no reference plane in
common (verify._ref_switch_vias), when no GND via stands within return_via_mm, one is laid at
the nearest legal point within it. A GND via must land in a GND fill on a plane layer (it joins
the plane, not nothing) and clear every other net's copper, drill and pad as power_vias' are;
the board is counted once, refilled, in a fresh process (power_vias._fresh), and if anything
opened, the vias are split in halves to find and lift the ones that did. Every via that cannot
be placed is REPORTED.
"""
import _nowindow  # noqa: F401  (no console windows on Windows: _nowindow.py)
import json
import math
import os
import sys

import pcbnew

import stable_fill  # noqa: E402  (PCBFLOW_STABLE_FILL)
import frozen_wall  # noqa: E402  (the one frozen-band wall for post-route copper)
import wx                                       # noqa: E402
wx.DisableAsserts()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import power_vias as PV                         # noqa: E402  (its checks, its fresh count)
import verify                                   # noqa: E402  (which vias switch reference)

MM, IU = pcbnew.ToMM, pcbnew.FromMM


def plan(stem, board, notes):
    """[(net, (x, y) of the pair via, (gx, gy) or None, why-not)] for every reference-switching
    pair via with no GND via within its group's return_via_mm."""
    R = PV._rules(stem)
    groups = [g for g in notes.get("match", ()) if g.get("return_via_mm")]
    if not groups:
        return []
    cu = list(board.GetEnabledLayers().CuStack())
    keep = PV._keepouts(board)
    outline = pcbnew.SHAPE_POLY_SET()
    board.GetBoardPolygonOutlines(outline, False)
    gnd_names = set()
    for g in groups:
        gnd_names |= set(g.get("return_nets", ("GND", "AGND")))
    gnd = board.FindNet("GND")
    if gnd is None:
        return []
    gnc = gnd.GetNetCode()
    planes = [z for z in board.Zones() if not z.GetIsRuleArea() and z.GetNetname() == "GND"]
    tracks = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK"]
    seg = [(t.GetLayer(), t.GetNetCode(), MM(t.GetStart().x), MM(t.GetStart().y),
            MM(t.GetEnd().x), MM(t.GetEnd().y), MM(t.GetWidth())) for t in tracks]
    vt = []
    for o in board.GetTracks():
        if o.GetClass() != "PCB_VIA":
            continue
        try:
            orr = MM(o.GetWidth(o.GetLayer())) / 2.0
        except TypeError:
            orr = MM(o.GetWidth()) / 2.0
        vt.append((MM(o.GetPosition().x), MM(o.GetPosition().y), MM(o.GetDrillValue()), orr,
                   o.GetNetCode(), o.GetNetname()))
    pads = list(board.GetPads())
    pro = json.load(open(stem + ".kicad_pro", encoding="utf-8"))
    dflt = {c["name"]: c for c in pro.get("net_settings", {}).get("classes", [])}.get("Default", {})
    vd, drill = float(dflt.get("via_diameter", 0.6)), float(dflt.get("via_drill", 0.3))
    vr = vd / 2.0
    wall = frozen_wall.FrozenWall(board)    # a return via stays out of other nets' frozen bands

    def clear_of(nc_b):
        nb = board.FindNet(nc_b) if nc_b else None
        cb = R["cls"].get(nb.GetNetClassName(), R["clear"]) if nb else R["clear"]
        return max(R["cls"].get("Default", R["clear"]), cb, R["clear"])

    placed = []
    out = []
    for g in groups:
        rad = float(g["return_via_mm"])
        for net in g["nets"]:
            for (x0, y0, lay) in verify._ref_switch_vias(board, net):
                have = [(x, y) for (x, y, _d, _r, _n, nm) in vt if nm in gnd_names] + placed
                if any(math.hypot(x - x0, y - y0) <= rad for x, y in have):
                    continue
                why = {}

                def refuse(k):
                    why[k] = why.get(k, 0) + 1
                    return False

                def ok(x, y):
                    pv = pcbnew.VECTOR2I(IU(x), IU(y))
                    # ⚠ THE VIA'S RING JOINS THE PLANE, NOT ITS CENTRE (brain_board mV18,
                    # 2026-11-17): the pair's own through vias clear the In1 GND fill by the
                    # zone clearance, and the two holes merge -- a 0.8 mm-radius hole round
                    # each pair via. Testing the candidate's centre refused every point
                    # within 1.0 mm (GADGET_DM, MCU_DP: "no GND plane fill there") while In1
                    # was solid GND. A GND via joins the plane where its ring reaches the
                    # fill (the refill flows into it); the other checks keep it clear of
                    # the pair's copper, and the fresh count below catches anything worse.
                    ring = [pv] + [pcbnew.VECTOR2I(IU(x + 0.95 * vr * math.cos(a * math.pi / 4)),
                                                   IU(y + 0.95 * vr * math.sin(a * math.pi / 4)))
                                   for a in range(8)]
                    if not any(z.HitTestFilledArea(L, q) for z in planes for L in z.GetLayerSet().CuStack()
                               if L != pcbnew.F_Cu and L != pcbnew.B_Cu
                               for q in ring):
                        return refuse("no GND plane fill there")
                    for (ox, oy, od, orr, on, _nm) in vt:
                        if abs(ox - x) > 3 or abs(oy - y) > 3:
                            continue
                        if math.hypot(x - ox, y - oy) < (drill + od) / 2.0 + R["hole_hole"]:
                            return refuse("hole to hole")
                        if on != gnc and math.hypot(x - ox, y - oy) < vr + orr + clear_of(on):
                            return refuse("another net's via")
                    for (px, py) in placed:
                        if math.hypot(x - px, y - py) < drill + R["hole_hole"]:
                            return refuse("hole to hole")
                    for (L, n_, ax, ay, bx, by, w) in seg:
                        if (n_ == gnc or min(ax, bx) - w > x + 2 or max(ax, bx) + w < x - 2
                                or min(ay, by) - w > y + 2 or max(ay, by) + w < y - 2):
                            continue
                        if PV._d_seg(x, y, ax, ay, bx, by) < vr + w / 2.0 + clear_of(n_):
                            return refuse("another net's track")
                    circ = pcbnew.SHAPE_CIRCLE(pv, IU(vr))
                    for p in pads:
                        pp = p.GetPosition()
                        if abs(MM(pp.x) - x) > 6 or abs(MM(pp.y) - y) > 6:
                            continue
                        for L in cu:
                            if not p.IsOnLayer(L):
                                continue
                            gap = 0.0 if p.GetNetCode() == gnc else clear_of(p.GetNetCode())
                            if p.GetEffectiveShape(L).Collide(circ, IU(gap)):
                                return refuse("a pad")
                    for a in range(16):
                        q = pcbnew.VECTOR2I(IU(x + (vr + R["edge"]) * math.cos(a * math.pi / 8)),
                                            IU(y + (vr + R["edge"]) * math.sin(a * math.pi / 8)))
                        if not outline.Contains(q):
                            return refuse("the board edge")
                    for poly, _layers in keep:
                        if poly.Collide(circ, 0):
                            return refuse("a keep-out")
                    if wall and not wall.via_ok_mm(x, y, gnc, vr):
                        return refuse("another net's frozen band")
                    return True

                cands = []
                n = int(rad / PV.STEP)
                for i in range(-n, n + 1):
                    for j in range(-n, n + 1):
                        x, y = x0 + i * PV.STEP, y0 + j * PV.STEP
                        d = math.hypot(x - x0, y - y0)
                        if d <= rad:
                            cands.append((d, x, y))
                cands.sort()
                got = next(((x, y) for _d, x, y in cands if ok(x, y)), None)
                if got:
                    placed.append(got)
                out.append((net, (x0, y0), got, ", ".join("%s x%d" % kv for kv in
                                                          sorted(why.items(), key=lambda kv: -kv[1])[:3])))
    return out


def main(stem):
    pcb = stem + ".kicad_pcb"
    notes = json.load(open(stem + ".board.json", encoding="utf-8"))
    if not any(g.get("return_via_mm") for g in notes.get("match", ())):
        print("  return vias: no group declares return_via_mm")
        return 0
    board = pcbnew.LoadBoard(pcb)
    stable_fill.fill(board, board.Zones())
    rows = plan(stem, board, notes)
    gnd = board.FindNet("GND")
    proto = next((v for v in board.GetTracks() if v.GetClass() == "PCB_VIA" and v.GetNetname() == "GND"), None)
    added = []
    for net, _xy, got, _why in rows:
        if got is None or proto is None:
            continue
        nv = proto.Duplicate()
        nv.SetPosition(pcbnew.VECTOR2I(IU(got[0]), IU(got[1])))
        nv.SetNet(gnd)
        board.Add(nv)
        added.append(nv.m_Uuid.AsString())
    lifted = set()
    if added:
        board.Save(pcb)
        base = PV._fresh(pcb, "count", added)

        def ok_(laid):
            return PV._fresh(pcb, "count", [u for u in added if u not in laid]) <= base

        def search(group, laid):
            if ok_(laid | set(group)):
                return set(group)
            if len(group) == 1:
                return set()
            h = len(group) // 2
            good = search(group[:h], laid)
            return good | search(group[h:], laid | good)
        lifted = set(added) - search(added, set())
        PV._fresh(pcb, "apply", lifted)
        try:
            import layout
            layout._canonical_uuids(pcb)
        except Exception:                       # noqa: BLE001
            pass
    n_ok = sum(1 for r in rows if r[2] is not None) - len(lifted)
    print("  return vias: %d pair via(s) switching reference with no GND via near, %d added%s"
          % (len(rows), n_ok, (", %d lifted (opened a connection)" % len(lifted)) if lifted else ""))
    for net, (x, y), got, why in rows:
        if got is None:
            print("  return vias: COULD NOT FIT one for %s at %.2f,%.2f (blocked by %s)" % (net, x, y, why or "nothing found"))
    return n_ok


if __name__ == "__main__":
    main(os.path.abspath(sys.argv[1]))
