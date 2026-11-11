"""optical R1 as intent (PLACEMENT.md generality proof). Writes opt_intent.json.

What is FIXED is what the instrument fixes (the optics, the comb, the connectors at the
-Y face) and the two designed cells (string cell x10, converter cell x5) as rigid groups on
their mechanically fixed anchors. EVERY compute-section part (86) is free: the MCU, its
ring, the PHY and its cell, the USB chain, the buck, the LDOs, the MID divider -- placed by
place_init from the rules below, with no hand xy and no rot rules.

Sources: op = src/optical_pickup.py, eo = elec/optical.py (line refs from the 11-11
extraction; board frame = CAD + (3.55, 28.315)).
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np  # noqa: E402
import place_intent as pi  # noqa: E402

HERE = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))   # the board dir
stem = os.path.join(HERE, "optical")
parts = json.load(open(stem + ".parts.json"))["parts"]
notes = json.load(open(stem + ".board.json"))
H = notes["placements"]
R = []


def r(kind, why, src, hard=True, **kw):
    R.append(dict(kind=kind, why=why, src=src, hard=hard, **kw))


def pin_of(ref, net):
    return "%s.%s" % (ref, next(q["num"] for q in parts[ref]["pads"] if q["net"] == net))


# ------------------------------------------------------------------ mechanical
r("outline", "every part on the laminate (J1 overhangs the -Y face by design)", "op PCB_X1S / TAIL_X1_R1 / PCB_YP / PCB_YM", **{"except": ["J1"]})
X0, X1, Y0, Y1 = -28.6058, 28.6058, -94.265, 94.265
EK = 1.2                                                     # op EDGE_KEEP
for poly in ([[X0, Y0], [X0 + EK, Y0], [X0 + EK, Y1], [X0, Y1]], [[X1 - EK, Y0], [X1, Y0], [X1, Y1], [X1 - EK, Y1]],
             [[X0, Y1 - EK], [X1, Y1 - EK], [X1, Y1], [X0, Y1]]):
    r("keepout", "body >= EDGE_KEEP 1.2 to the edge", "op EDGE_KEEP, check at ~4004", poly=poly)
r("keepout", "-Y face: EDGE_KEEP except J1/J2 (fixed, stamped over it)", "op ~4015",
  poly=[[X0, Y0 - 1.0], [X1, Y0 - 1.0], [X1, Y0 + EK], [X0, Y0 + EK]])
for c in notes["cutouts"]:
    r("hole", "M4 board screw: the O7.6 head + PKG_CLR 0.25", "op mount_points ~3225, check ~4091",
      xy=c["xy"], d=c["d"], keepout=(7.6 - c["d"]) / 2 + 0.25)
r("keepout", "the bridge bearings stand over the comb: no component", "op ~1724-1729",
  poly=[[-12.45, -20.7], [3.55, -20.7], [3.55, 79.3], [-12.45, 79.3]])
for s in notes["outline_slots"]:
    r("keepout", "comb slot", "op O_SLOTS ~3173", poly=s["poly"])
r("region", "compute section: south of the sensing strip (the strip is the analog field)", "op floorplan ~1432-1520",
  name="compute", poly=[[X0, Y0], [X1, Y0], [X1, -19.0], [X0, -19.0]])

# the optics: fixed by the string fan and the termination
for n in range(1, 11):
    for ref in ("D%d" % n, "PD%dA" % n, "PD%dB" % n, "R%d" % n):
        r("fixed", "sensing column at string %d (string_y_at SENSE_X, pitch 9.3634)" % n, "op ~578-620, 1360-1380",
          ref=ref, xy=H[ref][:2], rot=H[ref][2])
for j, w in (("J1", "USB-C at the -Y face, x off TAIL_X1 by the chain"), ("J2", "24 V XH: hard -X, flush with -Y face")):
    r("fixed", w, "op ~2387-2412", ref=j, xy=H[j][:2], rot=H[j][2])
# converter anchors: x = O_SLOT_X1 + ADC_BUS_CH + 2.8, y = midpoint of its string pair - CELL_NEAR
for k in range(1, 6):
    u = "U%d" % (13 + k)
    r("fixed", "converter %d: x off the comb's bus channel, y on its string pair's centre line" % k,
      "op ~2100-2118", ref=u, xy=H[u][:2], rot=H[u][2])


# ------------------------------------------------------------------ the two designed cells
def group(anchor, members, why, src):
    ax, ay, ar = H[anchor]
    m = {}
    for ref in members:
        x, y, rr = H[ref]
        d = pi._rot([[x - ax, y - ay]], -ar)[0]
        m[ref] = [round(float(d[0]), 4), round(float(d[1]), 4), (rr - ar) % 360.0]
    r("group", why, src, anchor=anchor, members=m)


for n in range(1, 11):
    group("D%d" % n, ["U%d" % (20 + n), "Rf%dA" % n, "Rf%dB" % n, "Cf%dA" % n, "Cf%dB" % n, "Cd%d" % n],
          "string cell: one dual TIA per string, -IN facing each PD, Rf/Cf on their channel's side, Cd under V+",
          "op ~936-961, 1385-1416")
for k in range(1, 6):
    u = "U%d" % (13 + k)
    # Csk9 and Rsk1 (the SHDNZ filter cap and pull-up) belong to the cell too, when the board
    # carries them as ordinary parts (fresh flow: no post_route_refs) -- PLACEMENT.md
    group(u, sorted(x for x in parts if re.fullmatch(r"C[ims]%d\d" % k, x) or x == "Rs%d1" % k),
          "converter cell: each cap at its own pin, input fan only widens, SAI corridor under the bottom row",
          "op ~1968-1993, 2123-2153")

CELLS = bool(os.environ.get("CELLS"))
if CELLS:
    # the two compute-section cells, free-anchor: designed round their pins, placed whole
    group("U13", ["C160", "C161", "C163", "C166", "C165", "R41", "R40", "L1", "C162", "C167"],
          "buck cell: VIN/PGND bypasses tight each side, bootstrap at SW/BOOT, FB at pin 7", "op ~2280-2317")
    group("U7", ["C121", "R39", "C119", "C145", "C136", "C139", "R37", "C122", "C120", "Y2", "C125", "C138", "C137"],
          "PHY cell: socket-face row, -X decap column with a gap at XO/XI, crystal level with XI", "op ~2500-2573")

# ------------------------------------------------------------------ free: the compute section
fixedset = {x["ref"] for x in R if x["kind"] == "fixed"} | {m for x in R if x["kind"] == "group" for m in x["members"]
                                                            if x["anchor"] in {y["ref"] for y in R if y["kind"] == "fixed"}}
free = sorted(set(parts) - fixedset)
r("in_region", "the compute section", "op floorplan", refs=free, region="compute")

AUTO = bool(os.environ.get("AUTO_FLOOR"))
if AUTO:
    R.extend(pi.auto_floorplan(parts))
else:
    # the compute floorplan: power on -X beside its inlet, USB on +X along the PHY -> socket path
    BUCK = ["U13", "L1", "C160", "C161", "C162", "C163", "C165", "C166", "C167", "R40", "R41", "R44"]
    USB = ["U7", "U10", "Y2", "R39", "C130", "R32", "R33"]
    QUIET = ["U11", "R34", "R35", "C114", "U9", "C132", "C140"]          # MID reference + analog LDO
    r("region", "power band: the 24 V inlet's side", "op ~2206-2222 (_BUCK_X0), eo ~1198-1201",
      name="power", poly=[[X0, Y0], [-6.0, Y0], [-6.0, -55.0], [X0, -55.0]])
    r("in_region", "the buck and its inlet resistor beside J2, as far from the photodiodes as possible",
      "op ~2206-2220", refs=BUCK, region="power")
    r("region", "USB band: PHY -> ESD -> socket in a straight line", "op ~2451-2499",
      name="usb", poly=[[2.0, Y0], [X1, Y0], [X1, -55.0], [2.0, -55.0]])
    r("in_region", "the USB chain on +X, out of the buck's way", "op ~2206-2220, 2451-2499", refs=USB, region="usb")
    r("apart", "the switch node off the PHY and its crystal", "op ~2206-2220", hard=False,
      a=["U13", "L1"], b=USB, min_mm=12.0)
    r("apart", "the switch node off the MID reference (feeds all twenty TIAs) and the analog LDO",
      "op ~1884-1898; eo ~1072-1078", hard=False, a=["U13", "L1"], b=QUIET, min_mm=10.0)

ANALOG = ["PD%d%s" % (n, s) for n in range(1, 11) for s in "AB"] + ["U%d" % (20 + n) for n in range(1, 11)]
for ref in ("U13", "L1"):
    r("thermal", "buck + inductor as far from the photodiodes and TIAs as the board allows",
      "op ~2206-2220; eo ~1198", hard=False, ref=ref, others=ANALOG, apart_mm=45.0)
r("near", "the buck beside the 24 V inlet (power on -X, USB on +X)", "op ~2206-2220", hard=False,
  ref="U13", target="J2", max_mm=15.0)
r("near", "R44 between the 24 V inlet and the buck", "op ~2391-2401", hard=False, ref="R44", target="J2", max_mm=8.0)
r("tight", "the buck's switch node: L1 and the boot cap on SW/BOOT", "TI datasheet layout guidelines; op ~2280-2296",
  hard=False, nets=["SW", "BOOT"], max_mm=10.0, weight=10.0)
r("tight", "FB divider at the FB pin", "TI datasheet; op ~2262", hard=False, nets=["FB"], max_mm=6.0, weight=10.0)
r("tight", "crystal legs short", "STM32 / PHY datasheets; op ~1701", hard=False,
  nets=["OSC_IN", "OSC_OUT", "PHY_XI"], max_mm=6.0, weight=5.0)
r("tight", "MID_RAW divider short: it feeds all twenty TIAs", "op ~1884-1898", hard=False,
  nets=["MID_RAW"], max_mm=6.0, weight=5.0)
for spec in notes.get("diff_pairs", ()):
    r("chain", "USB pair: PHY -> ESD -> socket in signal order", "op ~2451-2499; eo diff_pairs", hard=False,
      refs=spec["chain"], max_ratio=1.3)
r("near", "the ESD clamp inboard of J1's pad row, first thing on the pair", "op ~2340-2362; eo M10", hard=False,
  ref="U10", target="J1", max_mm=4.0)
r("decap", "a rail clamp dumps a strike into this capacitor", "op ~2596-2601", hard=False,
  cap="C130", pin=pin_of("U10", "VBUS"), max_mm=2.0, weight=1.0)
for cc, net in (("R32", "USB_CC1"), ("R33", "USB_CC2")):
    r("near", "CC 5k1 at its CC pin", "op ~2413-2427", hard=False, ref=cc, target=pin_of("J1", net), max_mm=6.0)
r("near", "PHY near the socket: 480 Mb/s does not tolerate length, ULPI does", "op ~1845-1851", hard=False,
  ref="U7", target="J1", max_mm=15.0)
for t in sorted((x for x in parts if re.fullmatch(r"TP\d+", x)), key=lambda x: int(x[2:])):
    r("access", "SWD/bring-up pad: a probe tip lands on it", "op ~1821-1844", ref=t, tool_d=1.6, side="top")

for c in pi.auto_decaps(parts, notes, pi.read_values(stem + ".net"), cells=R):
    c.pop("_now", None)
    if c.get("cap") in fixedset or c.get("ref") in fixedset:
        continue
    R.append(c)
R.extend(x for x in pi.auto_singles(parts) if x["ref"] not in fixedset)
r("current", "24 V inlet", "J2 / buck input", net="+24V", amps=0.5)
r("current", "5 V pre-regulator rail", "buck output", net="V5_PRE", amps=1.0)

json.dump(R, open(os.path.join(HERE, ("opt_intent_cells.json" if CELLS else "opt_intent_auto.json") if AUTO else "opt_intent.json"), "w"), indent=1)
print(len(R), "rules;", len(free), "free parts")
