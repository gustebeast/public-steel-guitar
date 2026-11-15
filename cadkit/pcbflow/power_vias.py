"""power_vias.py <stem>: give a wide net's layer change as many vias as its width needs.

⚠ ONE VIA IS ONE BARREL, WHATEVER THE TRACK (connector_board d10-d12, 2026-11-15). A 4 A
+24V at 2.03 mm changed layer six times, each through a single 0.3 mm via -- about 0.67 mm
of equivalent track (quality A1: pi x drill x 25/35, plating against foil) -- and every
motor path graded CHOKE POINT. The router lays one via per layer change and nothing in the
chain ever laid a second; pricing the via up (OWNROUTE_POWER_VIA) only helps where the
crossing can go to another net, and on two layers something always has to cross.

So, after the route, on the board that won: at each via of a WIDE net -- one whose tracks
on both sides of the via are wider than the via's barrel -- add vias beside it until the
barrels add up to the narrower side's width. A new via goes down only where ALL of these
hold, and every one that cannot is REPORTED (never a silent shortfall):
  * its centre lies in the net's OWN track copper on every layer the first via joins (so it
    joins the same two pieces, and the barrels share the current);
  * its ring clears every other net's track, via and pad by that pair's clearance (the larger
    of the two netclasses'), and no pad of any net is under it (a via in a land wicks);
  * its hole keeps min_hole_to_hole / min_hole_clearance from every other drill;
  * it is min_copper_edge_clearance inside the outline;
  * it is in no rule area that bans vias or tracks -- the keep-outs the router reads
    (router.model._keepouts: "(keepout ... (vias not_allowed)" or tracks).
Pours of other nets are refilled round the new vias. finish.py re-runs the DRC and puts the
board back if unconnected items or violations go up.

quality A1 sums vias that share track copper on both layers (_Net, PARALLEL VIAS), so a
transition laid here grades at its summed barrels.
"""
import _nowindow  # noqa: F401  (no console windows on Windows: _nowindow.py)
import json
import math
import os
import sys

import pcbnew
import wx                                       # noqa: E402  (KiCad's python ships it)
wx.DisableAsserts()                             # NO MODAL DIALOGS IN A BUILD STEP -- see route.py

PLATING = 25.0 / 35.0       # quality._Net's via derating: 25 um barrel plating against 35 um foil
STEP = 0.05                 # candidate grid, mm
MM = pcbnew.ToMM
IU = pcbnew.FromMM


def barrel_mm(drill_mm):
    return math.pi * drill_mm * PLATING


def _rules(stem):
    pro = json.load(open(stem + ".kicad_pro", encoding="utf-8"))
    r = pro["board"]["design_settings"]["rules"]
    cls = {c["name"]: float(c.get("clearance", r.get("min_clearance", 0.127)))
           for c in pro.get("net_settings", {}).get("classes", [])}
    return dict(clear=float(r.get("min_clearance", 0.127)), cls=cls,
                hole_hole=float(r.get("min_hole_to_hole", 0.25)),
                hole_clear=float(r.get("min_hole_clearance", 0.25)),
                edge=float(r.get("min_copper_edge_clearance", 0.3)))


def _d_seg(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _keepouts(board):
    """[(SHAPE_POLY_SET, layer ids)] for rule areas that ban vias or tracks."""
    out = []
    for z in board.Zones():
        if z.GetIsRuleArea() and (z.GetDoNotAllowVias() or z.GetDoNotAllowTracks()):
            out.append((z.Outline(), set(z.GetLayerSet().CuStack())))
    return out


def wide_nets(stem, board):
    """Nets the board's notes give a width or a current: net_widths and quality.power_paths."""
    try:
        notes = json.load(open(stem + ".board.json", encoding="utf-8"))
    except (OSError, ValueError):
        notes = {}
    out = set((notes.get("net_widths") or {}).keys())
    for p in ((notes.get("quality") or {}).get("power_paths") or ()):
        out.add(p["net"])
    return out


def plan(stem, board):
    """[(via, [new centres (x, y) mm], wanted extra, why-short)] for every wide-net via."""
    R = _rules(stem)
    nets = wide_nets(stem, board)
    cu = list(board.GetEnabledLayers().CuStack())
    tracks = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK"]
    vias = [t for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
    pads = list(board.GetPads())
    keep = _keepouts(board)
    outline = pcbnew.SHAPE_POLY_SET()
    board.GetBoardPolygonOutlines(outline, False)

    def clear_of(nc_a, nc_b):
        na, nb = board.FindNet(nc_a), board.FindNet(nc_b)
        ca = R["cls"].get(na.GetNetClassName() if na else "Default", R["clear"]) if na else R["clear"]
        cb = R["cls"].get(nb.GetNetClassName() if nb else "Default", R["clear"]) if nb else R["clear"]
        return max(ca, cb, R["clear"])

    seg = [(t, t.GetLayer(), t.GetNetCode(), MM(t.GetStart().x), MM(t.GetStart().y),
            MM(t.GetEnd().x), MM(t.GetEnd().y), MM(t.GetWidth())) for t in tracks]
    placed = []                 # (x, y, r, drill, netcode) laid this run
    out = []
    for v in vias:
        net = v.GetNetname()
        if net not in nets:
            continue
        nc = v.GetNetCode()
        vx, vy = MM(v.GetPosition().x), MM(v.GetPosition().y)
        drill = MM(v.GetDrillValue())
        try:
            vr = MM(v.GetWidth(v.GetLayer())) / 2.0
        except TypeError:
            vr = MM(v.GetWidth()) / 2.0
        # the via's own copper on each layer: same-net tracks with an end at its centre
        mine = {}
        for (t, L, n_, ax, ay, bx, by, w) in seg:
            if n_ == nc and (math.hypot(ax - vx, ay - vy) < 0.01 or math.hypot(bx - vx, by - vy) < 0.01):
                mine.setdefault(L, []).append((ax, ay, bx, by, w))
        if len(mine) < 2:
            continue            # a stitch into a pour, or a pad's own via: not a track-to-track change
        w_need = min(max(s[4] for s in v_) for v_ in mine.values())
        b = barrel_mm(drill)
        want = int(math.ceil(w_need / b - 1e-6))
        # vias of this net already sharing that copper count
        def inside(x, y, L):
            return any(_d_seg(x, y, ax, ay, bx, by) <= w / 2.0 for (ax, ay, bx, by, w) in mine[L])
        have = 1 + sum(1 for o in vias if o is not v and o.GetNetCode() == nc
                       and all(inside(MM(o.GetPosition().x), MM(o.GetPosition().y), L) for L in mine))
        have += sum(1 for (x, y, r, d, n_) in placed if n_ == nc and all(inside(x, y, L) for L in mine))
        extra = want - have
        if extra <= 0:
            continue
        reach = max(w_need, 2.0 * vr + R["hole_hole"] + drill) * 2.0
        cands = []
        n = int(reach / STEP)
        for i in range(-n, n + 1):
            for j in range(-n, n + 1):
                x, y = vx + i * STEP, vy + j * STEP
                d0 = math.hypot(x - vx, y - vy)
                if d0 <= reach:
                    cands.append((d0, x, y))
        cands.sort()
        got, why = [], {}

        def refuse(k):
            why[k] = why.get(k, 0) + 1
            return False

        def ok(x, y):
            if not all(inside(x, y, L) for L in mine):
                return refuse("outside the net's own copper")
            # holes: every drill on the board, this run's included
            for o in vias:
                ox, oy = MM(o.GetPosition().x), MM(o.GetPosition().y)
                od = MM(o.GetDrillValue())
                if math.hypot(x - ox, y - oy) < (drill + od) / 2.0 + R["hole_hole"]:
                    return refuse("hole to hole")
                if o.GetNetCode() != nc:
                    try:
                        orr = MM(o.GetWidth(o.GetLayer())) / 2.0
                    except TypeError:
                        orr = MM(o.GetWidth()) / 2.0
                    if math.hypot(x - ox, y - oy) < vr + orr + clear_of(nc, o.GetNetCode()):
                        return refuse("another net's via")
            for (px, py, pr, pd, pn) in placed + [(gx, gy, vr, drill, nc) for gx, gy in got]:
                if math.hypot(x - px, y - py) < (drill + pd) / 2.0 + R["hole_hole"]:
                    return refuse("hole to hole")
            for (t, L, n_, ax, ay, bx, by, w) in seg:
                if n_ != nc and _d_seg(x, y, ax, ay, bx, by) < vr + w / 2.0 + clear_of(nc, n_):
                    return refuse("another net's track")
            circ = pcbnew.SHAPE_CIRCLE(pcbnew.VECTOR2I(IU(x), IU(y)), IU(vr))
            for p in pads:
                for L in cu:
                    if not p.IsOnLayer(L):
                        continue
                    gap = 0.0 if p.GetNetCode() == nc else clear_of(nc, p.GetNetCode())
                    if p.GetEffectiveShape(L).Collide(circ, IU(gap)):
                        return refuse("a pad" if p.GetNetCode() == nc else "another net's pad")
                if p.HasHole() and math.hypot(x - MM(p.GetPosition().x), y - MM(p.GetPosition().y)) < (
                        drill / 2.0 + max(MM(p.GetDrillSize().x), MM(p.GetDrillSize().y)) / 2.0 + R["hole_clear"]):
                    return refuse("a pad's hole")
            for a in range(16):
                q = pcbnew.VECTOR2I(IU(x + (vr + R["edge"]) * math.cos(a * math.pi / 8)),
                                    IU(y + (vr + R["edge"]) * math.sin(a * math.pi / 8)))
                if not outline.Contains(q):
                    return refuse("the board edge")
            for poly, layers in keep:
                if poly.Collide(circ, 0):
                    return refuse("a keep-out")
            return True

        for _d, x, y in cands:
            if len(got) >= extra:
                break
            if ok(x, y):
                got.append((x, y))
        for gx, gy in got:
            placed.append((gx, gy, vr, drill, nc))
        short = "" if len(got) >= extra else ", ".join("%s x%d" % kv for kv in
                                                       sorted(why.items(), key=lambda kv: -kv[1])[:3])
        out.append((v, net, (vx, vy), w_need, b, want, have, got, short))
    return out


def main(stem):
    pcb = stem + ".kicad_pcb"
    board = pcbnew.LoadBoard(pcb)
    rows = plan(stem, board)
    added, short = 0, []
    for v, net, (vx, vy), w, b, want, have, got, why in rows:
        for gx, gy in got:
            nv = v.Duplicate()
            nv.SetPosition(pcbnew.VECTOR2I(IU(gx), IU(gy)))
            board.Add(nv)
            added += 1
        if have + len(got) < want:
            short.append("%s at %.2f,%.2f: %.2f mm of track wants %d barrel(s) of %.2f, has %d "
                         "(blocked by %s)" % (net, vx, vy, w, want, b, have + len(got), why or "nothing found"))
    if added:
        filler = pcbnew.ZONE_FILLER(board)
        filler.Fill(board.Zones())
        board.Save(pcb)
        try:
            import layout
            layout._canonical_uuids(pcb)
        except Exception:                       # noqa: BLE001
            pass
    print("  power vias: %d wide-net via(s) short of barrels, %d via(s) added" % (len(rows), added))
    for s in short:
        print("  power vias: COULD NOT FIT %s" % s)
    return added


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    main(os.path.abspath(sys.argv[1]))
