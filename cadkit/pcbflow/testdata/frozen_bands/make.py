"""Builds b.kicad_pcb / b.kicad_pro / b.board.json: the frozen-band router fixture
(test_router_frozen_edge.py, test_router_frozen_neighbour.py). KiCad python:

    "C:/Program Files/KiCad/10.0/bin/python.exe" make.py

A 30 x 20 mm two-layer board, every band a pour zone NAMED "frozen" (pour_around's own name):
  * BAND on B.Cu: a 1.45 mm band at 30 degrees from (4, 4) to (20, 13.24) -- off-axis, so its
    outline crosses the 0.05 grid between cell centres everywhere.
  * NEAR (own) and FAR (foreign) on F.Cu: NEAR y 15.0..15.35, FAR y 15.75..17.0 -- NEAR's own band
    is nearer than FAR's along y 15.4..15.6, the case where the nearest band hid a neighbour.
  * one short track each on SIG, NEAR, FAR and BAND so the router names the nets.
"""
import json
import os
import math
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
MM = pcbnew.FromMM
b = pcbnew.BOARD()
b.SetCopperLayerCount(2)
nets = {}
for n in ("BAND", "NEAR", "FAR", "SIG"):
    ni = pcbnew.NETINFO_ITEM(b, n)
    b.Add(ni)
    nets[n] = ni


def edge(x0, y0, x1, y1):
    """Four gr_lines (repair_search._edges reads lines and arcs, not a gr_rect)."""
    for (ax, ay), (bx, by) in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)),
                               ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        s = pcbnew.PCB_SHAPE(b)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(pcbnew.VECTOR2I(MM(ax), MM(ay)))
        s.SetEnd(pcbnew.VECTOR2I(MM(bx), MM(by)))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(MM(0.1))
        b.Add(s)


def zone(net, layer, pts):
    z = pcbnew.ZONE(b)
    z.SetLayer(layer)
    z.SetNet(nets[net])
    z.SetZoneName("frozen")
    z.SetLocalClearance(MM(0.5))
    ol = z.Outline()
    ol.NewOutline()
    for x, y in pts:
        ol.Append(MM(x), MM(y))
    b.Add(z)


def track(net, layer, x0, y0, x1, y1, w=0.2):
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(pcbnew.VECTOR2I(MM(x0), MM(y0)))
    t.SetEnd(pcbnew.VECTOR2I(MM(x1), MM(y1)))
    t.SetWidth(MM(w))
    t.SetLayer(layer)
    t.SetNet(nets[net])
    b.Add(t)


edge(0, 0, 30, 20)
a = math.radians(30)
ux, uy, hw = math.cos(a), math.sin(a), 1.45 / 2
x0, y0, L = 4.0, 4.0, 18.5
zone("BAND", pcbnew.B_Cu, [(x0 - uy * hw, y0 + ux * hw), (x0 + uy * hw, y0 - ux * hw),
                           (x0 + ux * L + uy * hw, y0 + uy * L - ux * hw),
                           (x0 + ux * L - uy * hw, y0 + uy * L + ux * hw)])
zone("NEAR", pcbnew.F_Cu, [(3, 15.0), (27, 15.0), (27, 15.35), (3, 15.35)])
zone("FAR", pcbnew.F_Cu, [(3, 15.75), (27, 15.75), (27, 17.0), (3, 17.0)])
track("BAND", pcbnew.B_Cu, 5, 4.6, 6, 5.2)
track("NEAR", pcbnew.F_Cu, 5, 15.2, 6, 15.2)
track("FAR", pcbnew.F_Cu, 5, 16.4, 6, 16.4)
track("SIG", pcbnew.F_Cu, 25, 2, 27, 2)
pcbnew.SaveBoard(os.path.join(HERE, "b.kicad_pcb"), b)
json.dump({"net_settings": {"classes": [{"name": "Default", "clearance": 0.127, "via_diameter": 0.6,
                                         "via_drill": 0.3}]},
           "board": {"design_settings": {"rules": {"min_copper_edge_clearance": 0.3}}}},
          open(os.path.join(HERE, "b.kicad_pro"), "w"), indent=1)
json.dump({"plane_layers": [], "quality": {}}, open(os.path.join(HERE, "b.board.json"), "w"), indent=1)
prl = os.path.join(HERE, "b.kicad_prl")
if os.path.exists(prl):
    os.replace(prl, prl + "_dead")              # KiCad's per-user file: not part of the fixture
print("frozen_bands fixture written")
import sys; sys.stdout.flush(); os._exit(0)
