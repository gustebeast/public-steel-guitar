"""Builds b.kicad_pcb / b.kicad_pro / b.board.json: the pour-island fixture for
test_close_island.py. KiCad python:

    "C:/Program Files/KiCad/10.0/bin/python.exe" make.py

brain_board fold12's BST_SW in small, on a 24 x 16 mm two-layer board:
  * SW's switch-node pour on F.Cu, x 2..20, y 2..10, holding L1.2 (5, 5) and Q1.1 (15, 5);
  * a second SW pour, a sliver x 10..12, y 10.2..11.2 -- 0.2 mm below the first -- holding only
    U1.18 (11, 10.7), the driver's SW pin (gate-drive return);
  * quality.power_paths: SW L1.2 > Q1.1 at 6.5 A, nothing to U1.18.
DRC names the break by the big zone's first corner (2, 2); the big piece's first pad (L1.2) is
~7.6 mm from the sliver, the real gap 0.2 mm.
"""
import json
import os
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
MM = pcbnew.FromMM
b = pcbnew.BOARD()
b.SetCopperLayerCount(2)
nets = {}
for n in ("SW", "GATE"):
    ni = pcbnew.NETINFO_ITEM(b, n)
    b.Add(ni)
    nets[n] = ni
for (ax, ay), (bx, by) in (((0, 0), (24, 0)), ((24, 0), (24, 16)), ((24, 16), (0, 16)), ((0, 16), (0, 0))):
    s = pcbnew.PCB_SHAPE(b)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(pcbnew.VECTOR2I(MM(ax), MM(ay)))
    s.SetEnd(pcbnew.VECTOR2I(MM(bx), MM(by)))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(MM(0.1))
    b.Add(s)


def part(ref, pads):
    f = pcbnew.FOOTPRINT(b)
    f.SetReference(ref)
    b.Add(f)
    for num, net, x, y, sz in pads:
        p = pcbnew.PAD(f)
        p.SetNumber(num)
        p.SetShape(pcbnew.PAD_SHAPE_RECTANGLE)
        p.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
        p.SetLayerSet(p.SMDMask())
        p.SetSize(pcbnew.VECTOR2I(MM(sz), MM(sz)))
        p.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
        p.SetNet(nets[net])
        f.Add(p)


def zone(pts):
    z = pcbnew.ZONE(b)
    z.SetLayer(pcbnew.F_Cu)
    z.SetNet(nets["SW"])
    z.SetZoneName("whole")
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    z.SetMinThickness(MM(0.2))
    ol = z.Outline()
    ol.NewOutline()
    for x, y in pts:
        ol.Append(MM(x), MM(y))
    b.Add(z)


part("L1", [("2", "SW", 5.0, 5.0, 1.5)])
part("Q1", [("1", "SW", 15.0, 5.0, 1.5)])
part("U1", [("18", "SW", 11.0, 10.7, 0.4), ("1", "GATE", 11.0, 13.5, 0.4)])
zone([(2, 2), (20, 2), (20, 10), (2, 10)])
zone([(10, 10.2), (12, 10.2), (12, 11.2), (10, 11.2)])
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(os.path.join(HERE, "b.kicad_pcb"), b)
json.dump({"net_settings": {"classes": [{"name": "Default", "clearance": 0.127, "via_diameter": 0.6,
                                         "via_drill": 0.3}]},
           "board": {"design_settings": {"rules": {"min_copper_edge_clearance": 0.3}}}},
          open(os.path.join(HERE, "b.kicad_pro"), "w"), indent=1)
json.dump({"plane_layers": [], "quality": {"power_paths": [
    {"net": "SW", "from": "L1.2", "to": ["Q1.1"], "amps": 6.5}]}},
    open(os.path.join(HERE, "b.board.json"), "w"), indent=1)
prl = os.path.join(HERE, "b.kicad_prl")
if os.path.exists(prl):
    os.replace(prl, prl + "_dead")              # KiCad's per-user file: not part of the fixture
print("close_island fixture written")
import sys; sys.stdout.flush(); os._exit(0)
