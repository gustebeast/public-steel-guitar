"""pour_gate: a pour leg cut before the router is named, with its cutter (brain_board fold15/16, 2026-11-28).

    "C:/Program Files/KiCad/10.0/bin/python.exe" test_pour_gate.py

No board: a synthetic two-layer board, net A's pads at x 0 and 10 under one F.Cu pour.
1. A frozen-style net-B track across the pour at x 5: one POUR CUT, naming B's track, at x ~5.
2. The same board without the track: no cut.
3. The pour on B.Cu, the pads SMD on F.Cu (an inner/back pour, one via from each pin): no cut.
4. The B.Cu pour cut by a net-B B.Cu track, then bridged by declared net-A copper (via, F.Cu
   track, via) round it: the bridge makes it one body -- no cut.
5. legs(): a notes zone with "legs" and an intent pour rule both give the leg.
Exit 0 = PASS.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew  # noqa: E402
import pour_gate as PG  # noqa: E402

F = pcbnew.FromMM


def P(x, y):
    return pcbnew.VECTOR2I(F(x), F(y))


def board(pour_layer, cut=False, bridge=False):
    b = pcbnew.BOARD()
    na, nb = pcbnew.NETINFO_ITEM(b, "A"), pcbnew.NETINFO_ITEM(b, "B")
    b.Add(na)
    b.Add(nb)
    fp = pcbnew.FOOTPRINT(b)
    fp.SetReference("U1")
    b.Add(fp)
    for num, x in (("1", 0.0), ("2", 10.0)):
        pd = pcbnew.PAD(fp)
        pd.SetNumber(num)
        pd.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
        pd.SetShape(pcbnew.PAD_SHAPE_RECT)
        pd.SetLayerSet(pcbnew.PAD.SMDMask())
        pd.SetSize(pcbnew.VECTOR2I(F(1.0), F(1.0)))
        pd.SetPosition(P(x, 0))
        pd.SetNet(na)
        fp.Add(pd)
    L = b.GetLayerID(pour_layer)
    z = pcbnew.ZONE(b)
    z.SetLayer(L)
    z.SetNet(na)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_NEVER)
    o = z.Outline()
    o.NewOutline()
    for x, y in ((-1.5, -1.5), (11.5, -1.5), (11.5, 1.5), (-1.5, 1.5)):
        o.Append(F(x), F(y))
    b.Add(z)
    if cut:
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(P(5, -3))
        t.SetEnd(P(5, 3))
        t.SetWidth(F(0.5))
        t.SetLayer(L)
        t.SetNet(nb)
        b.Add(t)
    if bridge:                          # net A round the cut on F.Cu, through two vias
        for x in (3.5, 6.5):
            v = pcbnew.PCB_VIA(b)
            v.SetPosition(P(x, 0))
            v.SetWidth(F(0.6))
            v.SetDrill(F(0.3))
            v.SetNet(na)
            b.Add(v)
        for (x1, y1, x2, y2) in ((3.5, 0, 3.5, 2.5), (3.5, 2.5, 6.5, 2.5), (6.5, 2.5, 6.5, 0)):
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(P(x1, y1))
            t.SetEnd(P(x2, y2))
            t.SetWidth(F(0.4))
            t.SetLayer(pcbnew.F_Cu)
            t.SetNet(na)
            b.Add(t)
    b.BuildConnectivity()
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    return b


bad = []
leg = [("A", "F.Cu", ["U1.1", "U1.2"])]

# 1. cut on the pour's own layer
got = PG.check(board("F.Cu", cut=True), leg)
print("1:", got)
if len(got) != 1 or "B track" not in got[0] or "U1.2" not in got[0]:
    bad.append("1: wants one POUR CUT naming B's track and U1.2, got %r" % got)
else:
    import re
    m = re.search(r"\[board ([-0-9.]+), ([-0-9.]+)\]", got[0])
    if not m or abs(float(m.group(1)) - 5.0) > 0.5:
        bad.append("1: the cut is at x 5, the line says %r" % got[0])

# 2. uncut
got = PG.check(board("F.Cu"), leg)
print("2:", got)
if got:
    bad.append("2: an uncut pour reported %r" % got)

# 3. a B.Cu pour under F.Cu SMD pins: each pin is one via from it
legB = [("A", "B.Cu", ["U1.1", "U1.2"])]
got = PG.check(board("B.Cu"), legB)
print("3:", got)
if got:
    bad.append("3: a back-layer pour under its pins reported %r" % got)

# 4. cut on B.Cu, bridged by declared copper
got = PG.check(board("B.Cu", cut=True), legB)
print("4a:", got)
if len(got) != 1:
    bad.append("4a: a cut B.Cu leg wants one POUR CUT, got %r" % got)
got = PG.check(board("B.Cu", cut=True, bridge=True), legB)
print("4b:", got)
if got:
    bad.append("4b: a bridged cut still reported %r" % got)

# 5. legs() from notes and from intent
n = PG.legs({"zones": [{"net": "A", "layer": "F.Cu", "poly": [], "legs": [["U1.1", "U1.2"], ["U1.2", "U9.1"]]},
                       ("GND", "In1.Cu", 0.3)]})
i = PG.legs([{"kind": "pour", "net": "A", "layer": "B.Cu", "along": ["U1.1", "U1.2"]}, {"kind": "near"}])
print("5:", n, i)
if n != [("A", "F.Cu", ["U1.1", "U1.2"]), ("A", "F.Cu", ["U1.2", "U9.1"])] or i != legB:
    bad.append("5: legs() read %r / %r" % (n, i))

print("\n".join(bad) if bad else "PASS")
sys.stdout.flush()
os._exit(1 if bad else 0)
