"""Take out the declared vias the route did not use and the track runs straight through.

⚠ A DECLARED VIA IS AN OFFER TO THE ROUTER, NOT A PROMISE FROM IT (optical +3V3D at
U7, 2026-11-10). The generator drops vias beside fine-pitch pins ("each through a via
standing in the lane between the pin and its capacitor") so the router has a way down.
When the route reaches that copper some other way -- on optical it ran F.Cu down from
the north instead of B.Cu in from the pour -- the via is left carrying one layer: a
0.3 mm hole in the middle of a track, and a DRC "via_dangling" warning on every finish.
It was first read as the router's fill model disagreeing with KiCad's. It is not: the
via is in the UNROUTED board, the router's model of it was right, and the net is closed.

tidy_router_vias keeps declared vias on purpose -- close_last needs them as starting
copper -- so this runs AFTER close_last, on the board that won, and removes a via only
when all of these hold:
  * KiCad's own dangling test says so, with the zones FILLED (a stitch is attached to a
    zone, which no track-end test can see -- tidy_router_vias' first version got that
    wrong six times in seven);
  * on the one layer it carries, EITHER two or more track ends meet at ONE point at its
    centre -- the track runs straight through, so only the hole goes and the ends stay
    joined -- OR one track ends there: a pin escape the route did not take. Then the via
    goes WITH the spur that leads only to it, back to the first point where anything else
    holds the copper (another track, a pad, a via, a filled zone). That spur reaches
    nothing but a via that reaches nothing, so taking it up cannot open the net -- and
    leaving it trades a dangling via for a millimetre of antenna on, at optical, ULPI;
  * it is not inside a pad (a via in a land is the land's business: unwick.py).
finish.py re-runs the DRC and puts the board back if the count of unconnected items or
violations goes up.
"""
import json
import math
import os
import subprocess
import sys

import pcbnew
import wx                                       # noqa: E402  (KiCad's python ships it)
wx.DisableAsserts()                             # NO MODAL DIALOGS IN A BUILD STEP -- see route.py

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from layout import _via_r                       # noqa: E402


def spent(board):
    """[(uuids, description)] for the declared-and-unused vias on a zone-filled `board`:
    each via, with the dead spur of track that leads only to it."""
    conn = board.GetConnectivity()
    tracks = [t for t in board.GetTracks() if not isinstance(t, pcbnew.PCB_VIA)]
    vias = [t for t in board.GetTracks() if isinstance(t, pcbnew.PCB_VIA)]
    pads = list(board.GetPads())
    zones = list(board.Zones())
    tol = pcbnew.FromMM(0.001)
    out = []

    def near(a, b, r):
        return math.hypot(a.x - b.x, a.y - b.y) <= r

    def anchored(p, layer, nc, skip):
        """Is the point p held by anything but tracks: a pad, another via, a zone fill?"""
        if any(q.GetNetCode() == nc and q.IsOnLayer(layer) and q.HitTest(p) for q in pads):
            return True
        if any(w is not skip and w.GetNetCode() == nc and near(w.GetPosition(), p, _via_r(w))
               for w in vias):
            return True
        return any(z.GetNetCode() == nc and z.IsOnLayer(layer)
                   and z.HitTestFilledArea(layer, p) for z in zones)

    for v in vias:
        if not conn.TestTrackEndpointDangling(v, False):
            continue
        vp, r, nc = v.GetPosition(), _via_r(v), v.GetNetCode()
        if any(p.GetNetCode() == nc and p.HitTest(vp) for p in pads):
            continue                    # a via in a land is the land's business (unwick)
        mine = [t for t in tracks if t.GetNetCode() == nc]
        ends = [(t, e) for t in mine for e in (t.GetStart(), t.GetEnd()) if near(e, vp, r)]
        if len({t.GetLayer() for t, _e in ends}) > 1:
            continue                    # two layers meet here: not dangling after all
        if len(ends) >= 2:
            # a track running straight through: take the hole, keep the copper -- but only
            # when the ends meet at one point, so they stay joined without the via's pad
            if any(not near(e, ends[0][1], tol) for _t, e in ends):
                continue
            gone = [v.m_Uuid.AsString()]
            what = "%d track ends on %s" % (len(ends), board.GetLayerName(ends[0][0].GetLayer()))
        else:
            # a spur (or nothing): the via and the chain of track that leads ONLY to it,
            # back to the first point where anything else holds the copper
            gone, seen, length = [v.m_Uuid.AsString()], set(), 0.0
            t, e = ends[0] if ends else (None, None)
            while t is not None and t.m_Uuid.AsString() not in seen:
                seen.add(t.m_Uuid.AsString())
                gone.append(t.m_Uuid.AsString())
                length += t.GetLength()
                far = t.GetEnd() if near(t.GetStart(), e, tol) else t.GetStart()
                nxt = [u for u in mine if u is not t and u.GetLayer() == t.GetLayer()
                       and (near(u.GetStart(), far, tol) or near(u.GetEnd(), far, tol))]
                if len(nxt) != 1 or anchored(far, t.GetLayer(), nc, v):
                    break
                t, e = nxt[0], far
            what = "with %.2f mm of spur" % pcbnew.ToMM(length) if len(gone) > 1 else "bare"
        out.append((gone, "%s at %.2f,%.2f (%s)" % (
            v.GetNetname(), pcbnew.ToMM(vp.x), pcbnew.ToMM(vp.y), what)))
    return out


def main(stem):
    pcb = stem + ".kicad_pcb"
    # decide on a FILLED copy, then remove from a fresh load: the board on disk keeps
    # whatever fill state it had, and no proxy is held across a removal (tidy_router_vias)
    probe = pcbnew.LoadBoard(pcb)
    pcbnew.ZONE_FILLER(probe).Fill(probe.Zones())
    probe.BuildConnectivity()
    found = spent(probe)
    if not found:
        return 0
    # ⚠ AND THEN ASK THE BOARD WHETHER IT STILL HOLDS TOGETHER, one candidate at a time
    # (output_panel V5_PRE at C6, 2026-11-10). KiCad called that via dangling and the
    # geometry said spur -- and taking it up opened the net: an In2.Cu track reached the
    # via without ending inside its pad, which neither test sees. So each candidate is
    # lifted off the filled probe, the unconnected count is read, and it goes back if
    # the count rose. Remove + Add, never Delete: the probe keeps the objects alive.
    base = probe.GetConnectivity().GetUnconnectedCount(False)
    by_id = {t.m_Uuid.AsString(): t for t in probe.GetTracks()}
    kept, refused = [], []
    for us, d in found:
        items = [by_id[u] for u in us if u in by_id]
        for it in items:
            probe.Remove(it)
        probe.BuildConnectivity()
        if probe.GetConnectivity().GetUnconnectedCount(False) > base:
            for it in items:
                probe.Add(it)
            probe.BuildConnectivity()
            refused.append(d)
        else:
            kept.append((us, d))
    items = None
    del by_id, items
    del probe
    for d in refused:
        print("  spent vias: KEPT %s -- lifting it opened a connection" % d)
    found = kept
    if not found:
        return 0
    # ⚠ AND THE REMOVAL HAPPENS IN A FRESH PROCESS. With the probe's items lifted and put
    # back, the next LoadBoard in this one returned a bare SwigPyObject for its track
    # list -- the same corruption tidy_router_vias records. A second python costs a
    # second; a corrupted board costs the route.
    want = sorted({u for us, _d in found for u in us})
    lst = stem + ".spent.json"
    json.dump(want, open(lst, "w"))
    rc = subprocess.run([sys.executable, os.path.abspath(__file__), "--apply", stem, lst]).returncode
    os.remove(lst)
    if rc:
        raise SystemExit("spent_vias --apply failed (%d)" % rc)
    n = len(found)
    print("  spent vias: removed %d via(s) the route did not use -- %s"
          % (n, "; ".join(d for _u, d in found[:6])))
    return n


def apply(stem, lst):
    """Delete the listed items from the board on disk, in this (fresh) process."""
    pcb = stem + ".kicad_pcb"
    want = set(json.load(open(lst)))
    board = pcbnew.LoadBoard(pcb)
    hits = [t for t in board.GetTracks() if t.m_Uuid.AsString() in want]
    for h in hits:
        board.Delete(h)
    del hits
    board.Save(pcb)
    try:
        import layout
        layout._canonical_uuids(pcb)
    except Exception:                           # noqa: BLE001
        pass


if __name__ == "__main__":
    if sys.argv[1] == "--apply":
        apply(os.path.abspath(sys.argv[2]), sys.argv[3])
        sys.exit(0)
    sys.exit(0 if main(os.path.abspath(sys.argv[1])) >= 0 else 1)
