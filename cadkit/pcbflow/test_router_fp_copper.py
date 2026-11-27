"""A footprint's copper graphic is copper to the router (brain_board fold11, 2026-11-26).

    py -3.12 test_router_fp_copper.py [<dir holding fold11's placed board as b.kicad_pcb /
        b.kicad_pro / b.board.json (the .unrouted board)>]

NT22's net-tie bridge is an fp_poly on F.Cu, not a pad. The model read pads only, so a PB_VCC
via went down at (41.0, 118.5) with its hole 0.12 mm from the bridge (DRC hole_clearance, wants
0.25) and its copper over it.
1. (no files) _fp_copper reads a rotated net tie's fp_poly in board coordinates, with the two
   pads' nets; a footprint with copper pads only gives nothing.
2. (with the board) NT22's bridge is in the model at x 40.235..40.735, y 118..119; a via of any
   net is refused at (41.0, 118.5) and allowed at (41.6, 118.5); on F.Cu each tie net reaches
   its own pad and not the other's, and GND reaches neither.
Exit 0 = PASS.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from router import model as M  # noqa: E402

bad = []
TIE = '''
	(footprint "NetTie-2_SMD_Pad0.5mm"
		(layer "F.Cu")
		(at 40.485 118.5 90)
		(property "Reference" "NT22"
			(at 0 -1.2 90)
		)
		(fp_poly
			(pts
				(xy -0.5 -0.25) (xy 0.5 -0.25) (xy 0.5 0.25) (xy -0.5 0.25)
			)
			(fill yes)
			(layer "F.Cu")
		)
		(pad "1" smd circle
			(at -0.5 0 90)
			(size 0.5 0.5)
			(layers "F.Cu")
			(net "PB_VCC")
		)
		(pad "2" smd circle
			(at 0.5 0 90)
			(size 0.5 0.5)
			(layers "F.Cu")
			(net "PB_VCC_K")
		)
	)
	(footprint "R_0402"
		(layer "F.Cu")
		(at 10 10)
		(fp_line
			(start 0 0)
			(end 1 0)
			(layer "F.SilkS")
		)
		(pad "1" smd roundrect
			(at -0.5 0)
			(size 0.5 0.5)
			(layers "F.Cu" "F.Paste" "F.Mask")
			(net "A")
		)
	)
'''
g = M._fp_copper(TIE)
if len(g) != 1:
    bad.append("_fp_copper found %d graphics, not NT22's one" % len(g))
else:
    xs, ys = [q[0] for q in g[0]["pts"]], [q[1] for q in g[0]["pts"]]
    box = (min(xs), max(xs), min(ys), max(ys))
    print("parsed: %s x %.3f..%.3f y %.3f..%.3f %s" % ((g[0]["layer"],) + box + (g[0]["pads"],)))
    if any(abs(a - b) > 1e-6 for a, b in zip(box, (40.235, 40.735, 118.0, 119.0))):
        bad.append("NT22's bridge is not at x 40.235..40.735, y 118..119 (rotation)")
    if sorted(n for n, _x, _y in g[0]["pads"]) != ["PB_VCC", "PB_VCC_K"]:
        bad.append("the bridge does not carry its two pads' nets")

if len(sys.argv) > 1:
    m = M.Model(os.path.join(os.path.abspath(sys.argv[1]), "b"))
    if not any(min(q[0] for q in x["pts"]) == 40.235 and min(q[1] for q in x["pts"]) == 118.0
               for x in m.fp_cu):
        bad.append("the model holds no NT22 bridge")
    for net in ("PB_VCC", "GND"):
        vf = m.via_free(net)
        if vf[m.ij(41.0, 118.5)]:
            bad.append("a %s via is legal at (41.0, 118.5), its hole 0.12 off NT22's bridge" % net)
        if not vf[m.ij(41.6, 118.5)]:
            bad.append("a %s via is refused at (41.6, 118.5), clear of the bridge" % net)
    k = m.route_layers.index("F.Cu")
    for net, ok, no in (("PB_VCC", (40.485, 119.2), (40.485, 117.8)),
                        ("PB_VCC_K", (40.485, 117.8), (40.485, 119.2))):
        f = m.free(net, 0.2)[k]
        if not f[m.ij(*ok)]:
            bad.append("%s cannot reach its own NT22 pad" % net)
        if f[m.ij(*no)]:
            bad.append("%s may run onto the other tie net's pad end" % net)
    f = m.free("GND", 0.2)[k]
    if f[m.ij(40.485, 118.5)]:
        bad.append("GND may cross NT22's bridge")
else:
    print("(no board given: the parse checks only)")
for b_ in bad:
    print("  FAIL:", b_)
print("PASS" if not bad else "FAIL")
sys.stdout.flush()
os._exit(1 if bad else 0)
