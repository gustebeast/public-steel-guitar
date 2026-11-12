"""motor_ctrl R2 from scratch (PLACEMENT.md authoring trial, 2026-11-11).

Written from the netlist (part descriptions, nets) and the mechanical facts in
src/electronics.py ONLY -- the hand placement was not read. Frame: board centre origin,
+X = the edge that stands on the floor (the bus-B side-entry plugs come in through it),
-Y = the side facing the Pi (USB and 5 V leads to it). 61.8 x 55.0, single-sided, no holes.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import place_intent as pi  # noqa: E402

HERE = os.path.abspath(sys.argv[1])
stem = os.path.join(HERE, "motor_ctrl")
parts = json.load(open(stem + ".parts.json"))["parts"]
notes = json.load(open(stem + ".board.json"))
W, L = notes["outline_mm"]
X1, Y1 = W / 2.0, L / 2.0                      # 30.9, 27.5
MC, EL = "elec/motor_ctrl.py (netlist descriptions)", "src/electronics.py"
R = []


def r(kind, why, src, hard=True, **kw):
    R.append(dict(kind=kind, why=why, src=src, hard=hard, **kw))


# ---------------------------------------------------------------- mechanical
r("outline", "every part on the laminate", "notes outline_mm")
for j, at in (("J2", -13.0), ("J6", 13.0)):
    r("panel", "bus B side-entry PH: the plug comes in through the floor edge (+X)",
      "%s: 'the board's bottom edge sits at the floor so its two bus-B plugs can enter it'" % EL,
      ref=j, edge="+X", face=X1, overhang=-0.5, at=at)   # MP pads off the edge: copper_edge_clearance (v1)
for j in ("J1", "J3", "J7", "J5", "J4"):
    r("mate", "top-entry plug goes straight down; neighbours clear of its housing",
      "memory tht-connector-install-sweep", ref=j, dir="up", length=0.0, clear=0.3)
for t in ("TP1", "TP2", "TP3", "TP4", "TP5", "TP6"):
    r("access", "SWD / BOOT0 probe pad", "%s TP descriptions" % MC, ref=t, tool_d=1.6, side="top")

# ---------------------------------------------------------------- floorplan
REG = {
    # the cable edge opposite the floor: the vertical XH headers whose leads leave upward
    "top": [[-X1, -Y1], [-X1 + 9.0, -Y1], [-X1 + 9.0, Y1], [-X1, Y1]],
    # the Pi-facing edge: USB-C and the Pi's 5 V
    "pi": [[-X1 + 9.0, -Y1], [X1 - 8.0, -Y1], [X1 - 8.0, -Y1 + 11.0], [-X1 + 9.0, -Y1 + 11.0]],
    # the 3 A buck between the 24 V inlet (top edge) and the Pi feed (-Y edge); disjoint
    # from both bands (overlapping regions crowded J4 and U5 out: "no room")
    "power": [[-X1 + 9.0, -Y1 + 11.0], [2.0, -Y1 + 11.0], [2.0, 16.0], [-X1 + 9.0, 16.0]],
    # the MCU, its crystal and the USB bridge: the +X half, clear of the 5 V buck's 10 mm
    # (v2: unregioned, U4 landed beside the buck and the crystal was pushed 15 mm off it)
    "logic": [[6.0, -Y1 + 11.0], [X1 - 1.0, -Y1 + 11.0], [X1 - 1.0, Y1], [6.0, Y1]],
}
for n, p in REG.items():
    r("region", "floorplan band", "trial floorplan", name=n, poly=p, exclusive=(n in ("pi", "top")))
r("in_region", "24 V in, bus A out, lights out: XH headers on the top edge", "cable directions", refs=["J1", "J3", "J7"],
  region="top")
r("in_region", "the Pi's USB-C and 5 V leads leave -Y", "%s: Pi -Y of the motor board" % EL, refs=["J4", "J5"], region="pi")
r("in_region", "MCU, crystal, USB bridge and mux: away from the switchers", "auto_floorplan zones; v2",
  refs=["U4", "Y1", "U7", "U8"], region="logic")
r("in_region", "24 V -> 5 V 3 A buck and its protection, by the inlet and the Pi feed", "LMR33630 layout guide; F1/F2/D9 roles",
  refs=["U5", "L2", "C16", "C17", "C18", "C19", "C20", "C21", "C22", "C31", "C32", "D9", "F1", "F2", "R10", "R11",
        "R12", "R13", "R23"], region="power")

# ---------------------------------------------------------------- electrical
r("near", "inlet TVS at the 24 V inlet", "D8 description", ref="D8", target="J3", max_mm=8.0, hard=False)
r("near", "bus A clamp at its connector", "D2 description", ref="D2", target="J1", max_mm=6.0, hard=False)
r("near", "bus A transceiver by its connector", "U2 description", ref="U2", target="J1", max_mm=12.0, hard=False)
r("near", "bus A termination at the transceiver", "R5 description", ref="R5", target="U2", max_mm=5.0, hard=False)
for d, j in (("D4", "J2"), ("D5", "J2"), ("D10", "J6"), ("D11", "J6")):
    r("near", "bus B ESD clamp at its connector pin", "%s description" % d, ref=d, target=j, max_mm=5.0, hard=False)
r("near", "pedal-arm switch at J2", "U9 description", ref="U9", target="J2", max_mm=10.0, hard=False)
r("near", "lever-arm switch at J6", "U10 description", ref="U10", target="J6", max_mm=10.0, hard=False)
r("near", "pedal-arm 5 V limit at J2", "U6 description", ref="U6", target="J2", max_mm=12.0, hard=False)
r("near", "lever-arm 5 V limit at J6", "U11 description", ref="U11", target="J6", max_mm=12.0, hard=False)
r("near", "bus B transceiver between the two arm switches", "U3 description", ref="U3", target="U9", max_mm=12.0, hard=False)
r("near", "USB data ESD at the receptacle", "D6 description", ref="D6", target="J4", max_mm=5.0, hard=False)
r("near", "", "D7 description", ref="D7", target="J4", max_mm=5.0, hard=False)
r("near", "CC pull-downs at the CC pins", "R24/R25", ref="R24", target="J4.A5", max_mm=5.0, hard=False)
r("near", "", "R24/R25", ref="R25", target="J4.B5", max_mm=5.0, hard=False)
r("near", "link/flash mux by the receptacle", "U8 description", ref="U8", target="J4", max_mm=10.0, hard=False)
r("near", "USB-serial bridge between the mux and the MCU", "U7 description", ref="U7", target="U8", max_mm=14.0, hard=False)
r("near", "crystal at the MCU's OSC pins", "Y1: CAN bit timing wants a crystal", ref="Y1", target="U4.5", max_mm=4.0, hard=False)
r("near", "lights fuse and bypass at J7", "F3/C26 descriptions", ref="F3", target="J7", max_mm=8.0, hard=False)
r("near", "", "C26 'at J7'", ref="C26", target="J7", max_mm=5.0, hard=False)
r("near", "24 V HF bypass at the inlet", "C29 'at the inlet J3'", ref="C29", target="J3", max_mm=5.0, hard=False)
r("near", "bus B 5 V bulk at J2", "C28 description", ref="C28", target="J2", max_mm=6.0, hard=False)
r("near", "lever arm 5 V bulk at J6", "C41 description", ref="C41", target="J6", max_mm=6.0, hard=False)
r("near", "5 V local bulk for J5", "C27 description", ref="C27", target="J5", max_mm=8.0, hard=False)
r("near", "BOOT0/NRST drivers by the bridge's DTR/RTS", "Q1/Q2 descriptions", ref="Q1", target="U7", max_mm=10.0, hard=False)
r("near", "", "Q1/Q2", ref="Q2", target="U7", max_mm=10.0, hard=False)
r("tight", "3V3 buck switch node and bootstrap", "LMR16006 layout guide", hard=False, nets=["SW", "CB"], max_mm=8.0,
  weight=10.0)
r("tight", "3V3 buck feedback divider at FB", "LMR16006 layout guide", hard=False, nets=["FB"], max_mm=5.0, weight=10.0)
r("tight", "5 V buck switch node and bootstrap", "LMR33630 layout guide", hard=False, nets=["SW5", "BOOT5"], max_mm=10.0,
  weight=10.0)
r("tight", "5 V buck feedback divider at FB", "LMR33630 layout guide", hard=False, nets=["FB5"], max_mm=6.0, weight=10.0)
r("tight", "crystal legs", "CH32V307 datasheet", hard=False, nets=["OSC_IN", "OSC_OUT"], max_mm=6.0, weight=5.0)
r("pour", "2.9 A of the motors' 24 V from the inlet to bus A: more than a track carries; B.Cu is free "
  "(single-sided board), the pour outranks the GND pour there",
  "quality.power_paths +24V J3.1 > J1.1", net="+24V", layer="B.Cu", along=["J3.1", "J1.1"])
r("pour", "3 A from the 5 V buck's inductor to the output fuse: a pour, F.Cu (the parts' side)",
  "quality.power_paths +5V_RAW L2.2 > F2.1", net="+5V_RAW", layer="F.Cu", along=["L2.2", "F2.1"])
r("pour", "3 A from the fuse to the Pi's 5 V header", "quality.power_paths +5V F2.2 > J5.1",
  net="+5V", layer="F.Cu", along=["F2.2", "J5.1"])
for c in pi.auto_decaps(parts, notes, pi.read_values(stem + ".net"), cells=R,
                        descriptions=pi.read_descriptions(stem + ".net")):
    c.pop("_now", None)
    R.append(c)

json.dump(R, open(os.path.join(HERE, "intent.json"), "w"), indent=1)
print(len(R), "rules")
