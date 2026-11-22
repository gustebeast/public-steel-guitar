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

import stable_fill  # noqa: E402  (PCBFLOW_STABLE_FILL)
import frozen_wall  # noqa: E402  (the one frozen-band wall for post-route copper)
import wx                                       # noqa: E402  (KiCad's python ships it)
wx.DisableAsserts()                             # NO MODAL DIALOGS IN A BUILD STEP -- see route.py

PLATING = 25.0 / 35.0       # quality._Net's via derating: 25 um barrel plating against 35 um foil
STEP = 0.05                 # candidate grid, mm
NEAR_MM = 3.0               # past the search disc by more than this, nothing can refuse a candidate
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
    wall = frozen_wall.FrozenWall(board)    # extra vias stay out of other nets' frozen bands

    def clear_of(nc_a, nc_b):
        na, nb = board.FindNet(nc_a), board.FindNet(nc_b)
        ca = R["cls"].get(na.GetNetClassName() if na else "Default", R["clear"]) if na else R["clear"]
        cb = R["cls"].get(nb.GetNetClassName() if nb else "Default", R["clear"]) if nb else R["clear"]
        return max(ca, cb, R["clear"])

    own_zones = {}
    for z in board.Zones():
        if not z.GetIsRuleArea() and z.GetNetCode() > 0:
            own_zones.setdefault(z.GetNetCode(), []).append(z)
    seg = [(t, t.GetLayer(), t.GetNetCode(), MM(t.GetStart().x), MM(t.GetStart().y),
            MM(t.GetEnd().x), MM(t.GetEnd().y), MM(t.GetWidth())) for t in tracks]
    # ⚠ READ ONCE, TEST ONLY WHAT IS NEAR (brain_board mT3, 2026-11-16): ok() asked SWIG for every
    # via's position, drill and width, and walked every track and every pad's shape, for each of
    # thousands of candidate centres -- plan() took 272 s on 121 vias, and the SWIG churn is
    # what left GetConnectivity() broken afterwards (_fresh). Nothing past NEAR_MM of the search
    # disc can refuse a candidate, so the answers are the same.
    vt = []
    for o in vias:
        try:
            orr = MM(o.GetWidth(o.GetLayer())) / 2.0
        except TypeError:
            orr = MM(o.GetWidth()) / 2.0
        vt.append((o, MM(o.GetPosition().x), MM(o.GetPosition().y), MM(o.GetDrillValue()), orr, o.GetNetCode()))
    pbox = []
    for p in pads:
        bb = p.GetBoundingBox()
        pbox.append((p, MM(bb.GetLeft()), MM(bb.GetRight()), MM(bb.GetTop()), MM(bb.GetBottom())))
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
        # the via's own copper on each layer: same-net tracks whose copper holds its centre --
        # not only an end AT the centre: the router ends a track a few hundredths off it
        # (connector_board d14: 0.06 mm at C12, and that +24V via was never seen)
        mine = {}
        for (t, L, n_, ax, ay, bx, by, w) in seg:
            if n_ == nc and _d_seg(vx, vy, ax, ay, bx, by) <= w / 2.0:
                mine.setdefault(L, []).append((ax, ay, bx, by, w))
        if not mine:
            continue            # a stitch between two pours: quality A1 already sums those
        # ...or the net's own POUR on a layer with no track (connector_board d14: the +24V spine
        # on F.Cu fed down to a B.Cu track through one via -- three motor paths CHOKE POINT).
        # A layer the via reaches by pour joins as that pour's fill.
        pv = pcbnew.VECTOR2I(IU(vx), IU(vy))
        fills = {}
        for z in own_zones.get(nc, ()):
            for L in z.GetLayerSet().CuStack():
                if L not in mine and z.HitTestFilledArea(L, pv):
                    fills.setdefault(L, []).append(z)
        if len(mine) + len(fills) < 2:
            continue            # a pad's own via, or a stitch: not a change of layer between two pieces
        w_need = min(max(s[4] for s in v_) for v_ in mine.values())
        b = barrel_mm(drill)
        want = int(math.ceil(w_need / b - 1e-6))

        # vias of this net already sharing that copper count
        def inside(x, y, L):
            if L in fills:
                q = pcbnew.VECTOR2I(IU(x), IU(y))
                return any(z.HitTestFilledArea(L, q) for z in fills[L])
            return any(_d_seg(x, y, ax, ay, bx, by) <= w / 2.0 for (ax, ay, bx, by, w) in mine[L])
        layers_ = list(mine) + list(fills)
        have = 1 + sum(1 for (o, ox, oy, _od, _or, on) in vt if o is not v and on == nc
                       and all(inside(ox, oy, L) for L in layers_))
        have += sum(1 for (x, y, r, d, n_) in placed if n_ == nc and all(inside(x, y, L) for L in layers_))
        extra = want - have
        if extra <= 0:
            continue
        reach = max(w_need, 2.0 * vr + R["hole_hole"] + drill) * 2.0
        lo_x, hi_x, lo_y, hi_y = vx - reach - NEAR_MM, vx + reach + NEAR_MM, vy - reach - NEAR_MM, vy + reach + NEAR_MM
        vt_n = [q for q in vt if lo_x <= q[1] <= hi_x and lo_y <= q[2] <= hi_y]
        seg_n = [s for s in seg if max(s[3], s[5]) + s[7] / 2.0 >= lo_x and min(s[3], s[5]) - s[7] / 2.0 <= hi_x
                 and max(s[4], s[6]) + s[7] / 2.0 >= lo_y and min(s[4], s[6]) - s[7] / 2.0 <= hi_y]   # a track's copper is w/2 off its line
        pads_n = [q[0] for q in pbox if q[2] >= lo_x and q[1] <= hi_x and q[4] >= lo_y and q[3] <= hi_y]
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
            if not all(inside(x, y, L) for L in layers_):
                return refuse("outside the net's own copper")
            # holes: every drill on the board, this run's included
            for (o, ox, oy, od, orr, on) in vt_n:
                if math.hypot(x - ox, y - oy) < (drill + od) / 2.0 + R["hole_hole"]:
                    return refuse("hole to hole")
                if on != nc:
                    if math.hypot(x - ox, y - oy) < vr + orr + clear_of(nc, on):
                        return refuse("another net's via")
            for (px, py, pr, pd, pn) in placed + [(gx, gy, vr, drill, nc) for gx, gy in got]:
                if math.hypot(x - px, y - py) < (drill + pd) / 2.0 + R["hole_hole"]:
                    return refuse("hole to hole")
            for (t, L, n_, ax, ay, bx, by, w) in seg_n:
                if n_ != nc and _d_seg(x, y, ax, ay, bx, by) < vr + w / 2.0 + clear_of(nc, n_):
                    return refuse("another net's track")
            circ = pcbnew.SHAPE_CIRCLE(pcbnew.VECTOR2I(IU(x), IU(y)), IU(vr))
            for p in pads_n:
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
            if wall and not wall.via_ok_mm(x, y, nc, vr):
                return refuse("another net's frozen band")
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


_FRESH = """
import json, sys
import pcbnew
sys.path.insert(0, @HERE@)
import stable_fill
pcb, mode, lst = sys.argv[1], sys.argv[2], sys.argv[3]
drop = set(json.load(open(lst)))
b = pcbnew.LoadBoard(pcb)
for t in list(b.GetTracks()):
    if t.m_Uuid.AsString() in drop:
        b.Delete(t)     # NOT Remove: a removed via left GetConnectivity() a bare SwigPyObject
stable_fill.fill(b, b.Zones())
if mode == "apply":
    b.Save(pcb)
else:
    b.BuildConnectivity()
    print("UNCONNECTED %d" % b.GetConnectivity().GetUnconnectedCount(False))
""".replace("@HERE@", repr(os.path.dirname(os.path.abspath(__file__))))


def _fresh(pcb, mode, drop):
    """In a FRESH KiCad python: load `pcb`, lift the vias whose UUIDs are in `drop`, refill the
    pours, then count the unconnected items (mode "count") or save the board ("apply").

    ⚠ DELETE, NEVER REMOVE (brain_board mT3, 2026-11-16): the per-via loop lifted a via that
    opened a connection with board.Remove(), and every board.GetConnectivity() after that came
    back a bare SwigPyObject -- AttributeError, the step failed, and no via went in anywhere:
    every wide net's layer change read as a single-barrel CHOKE POINT in quality A1. Measured on
    the saved board: the same 121 vias lifted by Delete count right (3), by Remove break it.
    Each count runs on a fresh load, so nothing a lift or a refill leaves behind can reach it."""
    import subprocess
    import tempfile
    fd, lst = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w") as fh:
        json.dump(sorted(drop), fh)
    try:
        p = subprocess.run([sys.executable, "-c", _FRESH, pcb, mode, lst], capture_output=True,
                           text=True, stdin=subprocess.DEVNULL)
    finally:
        os.remove(lst)
    if mode == "apply":
        if p.returncode:
            raise SystemExit("power_vias: the fresh refill failed (%d): %s" % (p.returncode, p.stderr[-400:]))
        return None
    for line in (p.stdout or "").splitlines():
        if line.startswith("UNCONNECTED "):
            return int(line.split()[1])
    raise SystemExit("power_vias: the fresh count failed (%d): %s" % (p.returncode, (p.stderr or "")[-400:]))


def main(stem):
    pcb = stem + ".kicad_pcb"
    board = pcbnew.LoadBoard(pcb)
    stable_fill.fill(board, board.Zones())              # plan() reads the pours' fills
    rows = plan(stem, board)
    # ⚠ A VIA THAT OPENS A CONNECTION COMES BACK OUT (connector_board d14, 2026-11-15).
    # Clearance-legal is not enough: a new via's antipad can cut the neck of another net's pour,
    # and 22 vias laid together left one GND fill island -- finish then put the whole step back.
    # ⚠ BUT NOT ONE REFILL PER VIA (brain_board mT3, 2026-11-16): that loop refilled every pour
    # after each of 121 vias, in the process plan() had worn out (see _fresh). Now every planned
    # via is laid and the board is counted once, refilled, in a fresh process; only if the count
    # rose are the vias split in halves to find the ones that opened it -- one count when none
    # does, a couple of dozen when one does -- and those are lifted and reported.
    added = []                              # (uuid, row index, x, y)
    for i, r in enumerate(rows):
        v = r[0]
        for gx, gy in r[7]:
            nv = v.Duplicate()
            nv.SetPosition(pcbnew.VECTOR2I(IU(gx), IU(gy)))
            board.Add(nv)
            added.append((nv.m_Uuid.AsString(), i, gx, gy))
    lifted = set()
    if added:
        board.Save(pcb)
        ids = [a[0] for a in added]
        base = _fresh(pcb, "count", ids)     # the board as it was
        n_counts = [1]

        def ok(laid):
            n_counts[0] += 1
            return _fresh(pcb, "count", [u for u in ids if u not in laid]) <= base

        def search(group, laid):
            """The members of `group` that may be laid beside `laid` without opening anything."""
            if ok(laid | set(group)):
                return set(group)
            if len(group) == 1:
                return set()
            h = len(group) // 2
            good = search(group[:h], laid)
            return good | search(group[h:], laid | good)
        kept_ids = search(ids, set())
        lifted = set(ids) - kept_ids
        _fresh(pcb, "apply", lifted)        # the board with the kept vias, its pours refilled
        try:
            import layout
            layout._canonical_uuids(pcb)
        except Exception:                       # noqa: BLE001
            pass
        print("  power vias: %d fresh count(s) against %d unconnected before" % (n_counts[0], base))
    short = []
    n_added = 0
    for i, (v, net, (vx, vy), w, b, want, have, got, why) in enumerate(rows):
        mine = [a for a in added if a[1] == i]
        kept = sum(1 for a in mine if a[0] not in lifted)
        n_added += kept
        for a in mine:
            if a[0] in lifted:
                why = (why + ", " if why else "") + "a via at %.2f,%.2f that opened a connection" % (a[2], a[3])
        if have + kept < want:
            short.append("%s at %.2f,%.2f: %.2f mm of track wants %d barrel(s) of %.2f, has %d "
                         "(blocked by %s)" % (net, vx, vy, w, want, b, have + kept, why or "nothing found"))
    print("  power vias: %d wide-net via(s) short of barrels, %d via(s) added" % (len(rows), n_added))
    for s in short:
        print("  power vias: COULD NOT FIT %s" % s)
    return n_added


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    main(os.path.abspath(sys.argv[1]))
