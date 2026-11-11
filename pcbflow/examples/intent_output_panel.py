"""output_panel R2's hand placement, said as intent (PLACEMENT.md (a) proof). Writes op_intent.json."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import place_intent as pi  # noqa: E402

HERE = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))   # the board dir
stem = os.path.join(HERE, "output_panel")
parts = json.load(open(stem + ".parts.json"))["parts"]
notes = json.load(open(stem + ".board.json"))

EDGE_X, EDGE_NX = 49.0, -49.0
PANEL_CLR, PANEL_T = 0.3, 1.6           # src/electronics.py OP_PANEL_CLR / OP_PANEL_T
FACE = EDGE_X + PANEL_CLR + PANEL_T     # the instrument's face, +X
OP = "elec/output_panel.py"

R = []


def r(kind, why, src, hard=True, **kw):
    R.append(dict(kind=kind, why=why, src=src, hard=hard, **kw))


# ---------------------------------------------------------------- mechanical
r("outline", "every part on the laminate, except the panel connectors that pass through the endplate",
  "board outline: %s outline_poly (CAD: src/electronics.py OP_PANEL)" % OP)
r("hole", "the ear's M4: the head clamps the board all round, nothing under it", "user 2026-09-21 (THE MOUNTING EAR)",
  xy=[-53.75, -23.65], d=4.5, keepout=1.8)
r("access", "the single 2.5 mm hex key reaches the ear screw straight down", "memory single-hex-key / stowed-single-key",
  xy=[-53.75, -23.65], tool_d=8.0, side="top")
r("panel", "1/4 in jack: rear-panel mount, shoulder 6.05 behind the face, 3.0 stub", "Neutrik ST-NMJ4HCD2 drawing; user 'all at the same installation x'",
  ref="J5", edge="+X", face=FACE, overhang=-6.05 + 3.0, at=16.95)
r("panel", "USB-C: as far out as its shell legs allow (0.3 to the edge), overmold window in the panel", "%s J1_SETBACK" % OP,
  ref="J1", edge="+X", face=FACE, overhang=-0.40, at=-0.25)
r("panel", "24 V inlet: its 12.9 nose, 4.0 ahead of the body, reaches the face", "Kycon KPJX-4S-S drawing; %s J6_NOSE" % OP,
  ref="J6", edge="+X", face=FACE, overhang=-4.0, at=-18.0)
for j, y in (("J2", 22.0), ("J3", 8.0), ("J4", -6.0)):
    r("panel", "USB-C mouth 0.5 proud of the -X edge: a plug's overmold must not land on laminate", "%s USB_MOUTH_SHIFT" % OP,
      ref=j, edge="-X", face=-EDGE_NX, overhang=0.507, at=-y if False else y)
for j in ("J7", "J9", "J10"):
    r("mate", "top-entry XH: the plug goes straight down onto the header; neighbours clear of its housing",
      "memory tht-connector-install-sweep", ref=j, dir="up", length=0.0, clear=0.2)
for t in ("TP1", "TP2", "TP3", "TP4", "TP5"):
    r("access", "bring-up probe pad: a pogo or probe tip has to land on it", "%s debug pads" % OP, ref=t, tool_d=1.6, side="top")

# ---------------------------------------------------------------- floorplan: the three bands
BANDS = {"analog": [[-49, 14.5], [31, 14.5], [31, 28], [-49, 28]],
         "power24": [[-30, -28], [49, -28], [49, -11.5], [-30, -11.5]]}
for n, p in BANDS.items():
    r("region", "floorplan band", "%s THE FLOORPLAN IS THREE BANDS" % OP, name=n, poly=p)
r("in_region", "the analog chain along +Y, as far from the switching node as 56 mm allows", "%s THE FLOORPLAN IS THREE BANDS" % OP,
  refs=["J8", "U8", "U2", "U7", "R8", "C19", "C13", "C22", "C59", "C20", "C21", "C23", "C24", "C37"], region="analog")
r("in_region", "the 24 V island and its switcher in the -Y corner", "%s THE FLOORPLAN IS THREE BANDS" % OP,
  refs=["U5", "L1", "D6", "Q2", "J7", "U16", "D10"], region="power24")
r("thermal", "the switcher and its inductor off the pickup preamp and ADC", "%s noise bands; LMR33630 layout guide" % OP,
  ref="U5", others=["U8", "U2", "U7", "J8"], apart_mm=30.0, hard=False)
r("thermal", "", "%s noise bands" % OP, ref="L1", others=["U8", "U2", "U7", "J8"], apart_mm=30.0, hard=False)

# ---------------------------------------------------------------- electrical
for c in pi.auto_decaps(parts, notes, pi.read_values(stem + ".net"), cells=R):
    c.pop("_now", None)
    R.append(c)
for spec in notes.get("diff_pairs", ()):
    if len(spec["chain"]) >= 2:
        r("chain", "pair path order: laid straight through its parts", "%s diff_pairs" % OP, hard=False,
          refs=spec["chain"], max_ratio=1.6)
r("near", "THRU's ESD clamps at J1's data pins", "%s THRU ESD; TPD1E10B06 app note" % OP, ref="D2", target="J1", max_mm=8.0, hard=False)
r("near", "", "%s THRU ESD" % OP, ref="D3", target="J1", max_mm=8.0, hard=False)
r("near", "relay coil flyback diode at the coil", "%s" % OP, ref="D4", target="K1", max_mm=10.0, hard=False)
r("near", "hub crystal at the CH334F", "CH334F datasheet: crystal close to XI/XO", ref="Y2", target="U4", max_mm=4.0, hard=False)
r("near", "MCU crystal at the MCU", "CH32V20x datasheet", ref="Y1", target="U1", max_mm=4.0, hard=False)
r("tight", "the buck's switch node: inductor and boot cap on the SW pins, the loop that radiates",
  "TI LMR33630 datasheet, Layout Guidelines", hard=False, nets=["SW", "BOOT"], max_mm=10.0, weight=10.0)
r("tight", "feedback divider at the FB pin, its trace short and off the switch node",
  "TI LMR33630 datasheet, Layout Guidelines", hard=False, nets=["FB"], max_mm=6.0, weight=10.0)
r("tight", "crystal legs short: load caps and crystal at the oscillator pins",
  "CH32V20x / CH334F datasheets", hard=False, nets=["OSC_IN", "OSC_OUT", "HUB_XI", "HUB_XO"], max_mm=6.0, weight=5.0)
for ref in parts:
    r("rot", "as placed", "hand", hard=False, ref=ref, allowed=[notes["placements"][ref][2]])

json.dump(R, open(os.path.join(HERE, "op_intent.json"), "w"), indent=1)
print(len(R), "rules")
