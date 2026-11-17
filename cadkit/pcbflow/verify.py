"""Check what DRC cannot: matched-length groups, pair integrity, net lengths.

    "C:/Program Files/KiCad/10.0/bin/python.exe" cadkit/pcbflow/verify.py elec/out/optical

RUNS UNDER KICAD'S PYTHON (it reads tracks, so it needs pcbnew).

WHY THIS EXISTS. DRC answers "is this manufacturable" -- clearances, shorts, board
edges. It does not answer "is this CORRECT", and on a board carrying a 60 MHz
source-synchronous bus and a 480 Mbps differential pair those are different
questions. A router can produce a DRC-perfect board on which the USB pair is split
across two layers and takes two unrelated paths, and nothing in the pipeline would
notice.

THE POINT IS TO REMOVE THE HUMAN, NOT TO ADVISE ONE. The goal for this project is
that someone years from now changes a parameter -- the string spacing, say -- runs
the scripts, and gets a package they can send to a fab without anyone having to
eyeball a layout. That only works if the judgement calls a person would make are
written down as CHECKS. So the budgets live in <board>.board.json beside the design
that has to meet them, and this exits non-zero when they are not met.

⚠ WHAT IS DELIBERATELY NOT CHECKED, so nobody adds it back as an improvement. The CAN
pairs on motor_ctrl, can_tee and lever_sensor declare no group. Measured rather than
assumed: can_tee's pair runs 33.25/32.36 mm and lever_sensor's 39.75/42.23 mm, and
lever_sensor's two rails do NOT share a layer set. At 500 kbit/s a bit is 2,000,000 ps,
so 2.5 mm of skew is 15 ps -- eight millionths of a bit. A budget there would fail builds
for nothing, which is the cargo cult this file's last paragraph is about. Pairness on a
40 mm stub of a 120-ohm bus is in the same category. If the bus ever runs CAN-FD at
5 Mbit/s the arithmetic changes by 10x and is still not close; revisit it then, with a
number, not now.

⚠ A BUDGET NEEDS A REASON, AND THE REASON IS CHECKED TOO. Every entry carries a
`why`; a limit with no stated basis is a number someone will later relax because it
was in the way. The optical board's ULPI budget, for instance, is deliberately
LOOSE and says so: a 34.5 mm bus at 60 MHz has ~207 ps of flight, so even 10 mm of
mismatch is 60 ps against a 16,670 ps bit period. Writing 0.1 mm there would look
rigorous and would be cargo cult -- it would fail builds for a physical effect four
orders of magnitude below what matters.
"""
from __future__ import annotations

import json
import re
import os
import sys

import pcbnew
import wx                                       # noqa: E402  (KiCad's python ships it)
wx.DisableAsserts()                             # NO MODAL DIALOGS IN A BUILD STEP -- see route.py


def net_lengths(board, merge_ref=None, merge_r=4.0, nets=None):
    """{net name: (copper length in mm, {layer name: length}, via count)}."""
    # ⚠ A PAD-MERGE STUB IS NOT PART OF THE TRANSMISSION LINE, and counting it made this
    # check cry wolf twice on the optical board. A USB-C carries D+ on BOTH A6 and B6 and
    # D- on both A7 and B7, so the generator joins each net's two pads at the connector
    # (layout._flip_merge) -- and that join deliberately takes ONE rail down to an inner
    # layer, because which one dives is decided by which link is shorter.
    #
    # Measured on optical: counting every segment, USB_DP read F.Cu+In2.Cu against
    # USB_DM's F.Cu and the pair was reported as SPLIT ACROSS LAYERS, while skew read
    # 3.28 mm against a 2.50 budget. Excluding copper within `merge_r` of the merge
    # connector, the coupled RUN is F.Cu for both rails and the skew is 1.08 mm. The
    # board was fine; the measurement was counting the wrong copper.
    #
    # The exclusion is by NAMED REF, not by guessing which stubs look like merges: a
    # group says where its merge is, or nothing is excluded.
    skip = []
    for ref in ([merge_ref] if isinstance(merge_ref, str) else (merge_ref or ())):
        fp = board.FindFootprintByReference(ref)
        if fp is not None:
            # centred on the pair's OWN pads on the connector, not the footprint origin: a
            # USB-C's origin can sit mm off its pad row (output_panel J2 turned 90: the merge
            # vias 2.6 mm from the pads fell outside a 4 mm circle round the origin)
            pp = [q.GetPosition() for q in fp.Pads() if nets and q.GetNetname() in nets]
            if pp:
                c = (sum(q.x for q in pp) / len(pp), sum(q.y for q in pp) / len(pp))
            else:
                c = (fp.GetPosition().x, fp.GetPosition().y)
            skip.append((c[0], c[1], pcbnew.FromMM(merge_r)))

    def _in_merge(t):
        for cx, cy, r in skip:
            p = t.GetPosition() if t.GetClass() == "PCB_VIA" else t.GetStart()
            q = t.GetPosition() if t.GetClass() == "PCB_VIA" else t.GetEnd()
            mx, my = (p.x + q.x) / 2.0, (p.y + q.y) / 2.0
            if ((mx - cx) ** 2 + (my - cy) ** 2) ** 0.5 < r:
                return True
        return False

    out = {}
    for t in board.GetTracks():
        name = t.GetNetname()
        if not name:
            continue
        if _in_merge(t):
            continue
        total, per_layer, vias = out.get(name, (0.0, {}, 0))
        if t.GetClass() == "PCB_VIA":
            vias += 1
        else:
            mm = pcbnew.ToMM(t.GetLength())
            total += mm
            layer = board.GetLayerName(t.GetLayer())
            per_layer[layer] = per_layer.get(layer, 0.0) + mm
        out[name] = (total, per_layer, vias)
    return out


def merge_refs(board, nets):
    """The footprints that carry EVERY net of a pair on exactly two pads -- a USB-C
    receptacle, whose duplicated D+/D- pads layout._flip_merge joins. Read off the
    netlist, so the exclusion stays by named ref: a group that declares no merge_at gets
    these. (output_panel, 2026-11-11: a placement-chosen turn of J3 let the merge be laid
    where it never had been, and HUB_UP read 4 vias and a split layer set off the
    merge's own stub.) CONNECTORS ONLY: a pass-through part (a USBLC6's IO1 in and out)
    also carries each net on two pads, but its die joins them and its copper IS the line."""
    out = []
    for fp in board.GetFootprints():
        if not re.match(r"J\d", fp.GetReference()):
            continue
        n = {}
        for q in fp.Pads():
            n[q.GetNetname()] = n.get(q.GetNetname(), 0) + 1
        if all(n.get(x) == 2 for x in nets):
            out.append(fp.GetReference())
    return out


def _copper_order(board):
    """The board's copper layers top to bottom, as layer ids."""
    ids = [pcbnew.F_Cu] + [getattr(pcbnew, "In%d_Cu" % i) for i in range(1, 31)] + [pcbnew.B_Cu]
    return [L for L in ids if board.IsLayerEnabled(L)]


def _ref_switch_vias(board, net, ground=("GND", "AGND")):
    """[(x mm, y mm, (layer names)), ...]: the vias on `net` where its copper changes between
    layers that share no reference -- a layer's reference is the copper next to it in the
    stack (F.Cu: In1; In2: In1 and B.Cu; B.Cu: In2 on a 4-layer board) -- so the return
    current must jump planes there."""
    order = _copper_order(board)
    ref = {L: {order[i - 1] for i in [k] if i > 0} | {order[i + 1] for i in [k] if i + 1 < len(order)}
           for k, L in enumerate(order)}
    out = []
    tracks = [t for t in board.GetTracks() if t.GetNetname() == net and t.GetClass() != "PCB_VIA"]
    for v in board.GetTracks():
        if v.GetClass() != "PCB_VIA" or v.GetNetname() != net:
            continue
        c = v.GetPosition()
        r = v.GetWidth(pcbnew.F_Cu) / 2 if hasattr(v, "GetWidth") else 0
        lay = set()
        for t in tracks:
            for p in (t.GetStart(), t.GetEnd()):
                if (p - c).EuclideanNorm() <= r + 1:
                    lay.add(t.GetLayer())
        lay = sorted(lay)
        if len(lay) >= 2 and any(not (ref[a] & ref[b]) for i, a in enumerate(lay) for b in lay[i + 1:]):
            out.append((pcbnew.ToMM(c.x), pcbnew.ToMM(c.y), tuple(board.GetLayerName(L) for L in lay)))
    return out


def _hop_layers(board, net, a_ref, b_ref):
    """The copper layers `net` runs on from its pad on part a_ref to its pad on b_ref, in
    order, repeats collapsed: ("F.Cu", "B.Cu", "F.Cu"). None when no copper path joins them.
    A breadth-first walk over the net's pads, tracks and vias, items joined where an end
    lies within the other's width (a pad: inside its shape on that layer)."""
    items = [t for t in board.GetTracks() if t.GetNetname() == net]
    pads = [p for p in board.GetPads() if p.GetNetname() == net]
    if not items:
        return None
    ends = []                              # (item, layer or None for a via, point, radius)
    for t in items:
        if t.GetClass() == "PCB_VIA":
            ends.append((t, None, t.GetPosition(), t.GetWidth(pcbnew.F_Cu) / 2))
        else:
            for p in (t.GetStart(), t.GetEnd()):
                ends.append((t, t.GetLayer(), p, t.GetWidth() / 2))
    adj = {id(t): set() for t in items}
    for i, (ti, li, pi_, ri) in enumerate(ends):
        for tj, lj, pj, rj in ends[i + 1:]:
            if tj is ti or (li is not None and lj is not None and li != lj):
                continue
            if (pi_ - pj).EuclideanNorm() <= max(ri, rj) + 1:
                adj[id(ti)].add(id(tj))
                adj[id(tj)].add(id(ti))
    byid = {id(t): t for t in items}

    def touching(ref):
        out = set()
        for p in pads:
            if p.GetParentFootprint().GetReference() != ref:
                continue
            for t, L, pt, _r in ends:
                lays = [L] if L is not None else [x for x in board.GetEnabledLayers().CuStack() if p.IsOnLayer(x)]
                if any(p.IsOnLayer(x) and p.HitTest(pt, 0, x) if hasattr(p, "HitTest") else False
                       for x in lays):
                    out.add(id(t))
        return out
    src, dst = touching(a_ref), touching(b_ref)
    if not src or not dst:
        return None
    prev = {k: None for k in src}
    q = list(src)
    hit = None
    while q:
        k = q.pop(0)
        if k in dst:
            hit = k
            break
        for m in adj[k]:
            if m not in prev:
                prev[m] = k
                q.append(m)
    if hit is None:
        return None
    path = []
    while hit is not None:
        path.append(byid[hit])
        hit = prev[hit]
    seq = []
    for t in reversed(path):
        if t.GetClass() == "PCB_VIA":
            continue
        nm = board.GetLayerName(t.GetLayer())
        if not seq or seq[-1] != nm:
            seq.append(nm)
    return tuple(seq)


def check(stem):
    board = pcbnew.LoadBoard(stem + ".kicad_pcb")
    notes = json.load(open(stem + ".board.json", encoding="utf-8"))
    lens = net_lengths(board)
    groups = notes.get("match", [])
    if not groups:
        print("%s: no matched-length groups declared -- nothing to check"
              % os.path.basename(stem))
        return 0

    # ⚠ SKEW IS MEANINGLESS ON AN UNROUTED BOARD, and reporting it anyway is actively
    # misleading. The first real run printed "ULPI skew 56.08 mm" -- alarming, and
    # nonsense: four of the twelve nets were 1 mm stubs the router had not finished, so
    # the number was measuring incompleteness, not mismatch. Say which it is.
    board.BuildConnectivity()
    try:
        rn = board.GetConnectivity().GetUnconnectedCount(False)
    except TypeError:          # the signature gained aVisibleOnly somewhere in KiCad 9/10
        rn = board.GetConnectivity().GetUnconnectedCount()
    if rn:
        print("⚠ %s has %d unconnected item(s): the board is NOT fully routed, so the "
              "lengths below measure how far the router got, not how well matched the "
              "groups are. Finish routing before reading them as skew.\n"
              % (os.path.basename(stem), rn))

    bad = 0
    for g in groups:
        # a group measured through a pad-merge connector says so; see net_lengths
        mr = g.get("merge_at") or merge_refs(board, g["nets"])
        lens = net_lengths(board, mr, g.get("merge_r", 4.0), set(g["nets"])) if mr else net_lengths(board)
        nets = g["nets"]
        missing = [n for n in nets if n not in lens]
        if missing:
            print("FAIL %-10s nets carry no copper at all: %s"
                  % (g["name"], ", ".join(missing)))
            print("     (%s)" % g["why"])
            bad += 1
            continue
        ls = {n: lens[n][0] for n in nets}
        skew = max(ls.values()) - min(ls.values())
        ok = skew <= g["max_skew_mm"] + 1e-9
        print("%s %-10s skew %6.2f mm (budget %5.2f)  %s"
              % ("ok  " if ok else "FAIL", g["name"], skew, g["max_skew_mm"],
                 "%.1f..%.1f mm over %d nets" % (min(ls.values()), max(ls.values()),
                                                 len(nets))))
        if not ok:
            print("     (%s)" % g["why"])
            for n in sorted(ls, key=ls.get):
                print("       %-12s %6.2f mm" % (n, ls[n]))
            bad += 1
        # ⚠ A PAIR THAT SPLITS ACROSS LAYERS IS NOT A PAIR. Differential impedance is
        # a property of two conductors' geometry RELATIVE TO EACH OTHER; put one on
        # F.Cu and the other on In2.Cu and the number the stack-up was designed for
        # stops describing anything. DRC has no opinion about this, and it is exactly
        # the kind of thing an autorouter does when a direct path is congested.
        if g.get("same_layer"):
            layersets = {n: frozenset(lens[n][1]) for n in nets}
            if len(set(layersets.values())) != 1:
                print("FAIL %-10s the group does not share a layer set:" % g["name"])
                for n in nets:
                    print("       %-12s %s" % (n, ", ".join(sorted(layersets[n]))))
                print("     (%s)" % g["why"])
                bad += 1
        if g.get("max_vias") is not None:
            for n in nets:
                if lens[n][2] > g["max_vias"]:
                    print("FAIL %-10s %s has %d vias (budget %d) -- every via on a "
                          "high-speed net is an impedance discontinuity"
                          % (g["name"], n, lens[n][2], g["max_vias"]))
                    bad += 1
        # ⚠ A PAIR'S RAILS CHANGE LAYER TOGETHER (lead, 2026-11-17, brain_board max_vias 2 -> 4):
        # a looser budget on a long USB pair holds only if each discontinuity is the same on
        # both rails -- equal_vias: both rails carry the same count.
        if g.get("equal_vias"):
            cnt = {n: lens[n][2] for n in nets}
            if len(set(cnt.values())) > 1:
                print("FAIL %-10s the rails carry different via counts (%s) -- a pair changes "
                      "layer as a pair" % (g["name"], ", ".join("%s %d" % kv for kv in cnt.items())))
                bad += 1
            # ⚠ EQUAL TOTALS HID SINGLE-RAIL DIVES (lead, 2026-11-17, brain_board mV18):
            # GADGET_DM dropped to B.Cu alone under a crossing while GADGET_DP stayed on F.Cu,
            # and MCU_DP did the same -- the totals still matched across the chain. So each
            # hop of the pair's declared chain (notes["diff_pairs"]) is walked on both rails
            # and the layer SEQUENCES must be the same.
            spec = next((d for d in notes.get("diff_pairs", ()) or ()
                         if set(d.get("nets", ())) == set(nets)), None)
            for a_, b_ in zip((spec or {}).get("chain", ())[:-1], (spec or {}).get("chain", ())[1:]):
                seqs = {n: _hop_layers(board, n, a_, b_) for n in nets}
                if None in seqs.values():
                    continue                   # an open: reported as one, not as a layer mismatch
                if len(set(seqs.values())) > 1:
                    print("FAIL %-10s %s -> %s: the rails run different layers (%s) -- one rail "
                          "changes layer without its mate" % (g["name"], a_, b_, "; ".join(
                              "%s %s" % (n, ">".join(v)) for n, v in seqs.items())))
                    bad += 1
        # ...and where a layer change switches reference plane, the return current needs a way
        # across: return_via_mm -- a GND via within that distance of every such via.
        if g.get("return_via_mm"):
            rad = float(g["return_via_mm"])
            gv = [(pcbnew.ToMM(v.GetPosition().x), pcbnew.ToMM(v.GetPosition().y))
                  for v in board.GetTracks() if v.GetClass() == "PCB_VIA"
                  and v.GetNetname() in g.get("return_nets", ("GND", "AGND"))]
            for n in nets:
                for (x, y, lay) in _ref_switch_vias(board, n):
                    d = min((((x - a) ** 2 + (y - b) ** 2) ** 0.5 for a, b in gv), default=1e9)
                    if d > rad:
                        print("FAIL %-10s %s changes %s at (%.2f, %.2f) with no GND via within %.1f mm "
                              "(nearest %.2f) -- the return current has no way across"
                              % (g["name"], n, "/".join(lay), x, y, rad, d))
                        bad += 1
    print("\n%s: %d group(s) checked, %d problem(s)"
          % (os.path.basename(stem), len(groups), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(check(os.path.abspath(sys.argv[1])))
