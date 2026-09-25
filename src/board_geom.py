"""Printed-circuit boards in the CAD, READ BACK FROM THE ROUTED BOARD.

elec/export_geom.py writes elec/geom/<board>.geom.json from the finished .kicad_pcb: every
footprint's position, rotation and F.Fab BODY outline, in the board-centred frame the
CAD uses (+Y up). This module turns that into solids, and answers where each panel
connector's mouth actually is.

⚠ WHY THE BOARDS ARE NOT HAND-TYPED ANY MORE. The output board used to be modelled from
a table of anchors and COURTYARD boxes copied out of elec/output_panel.py, and checked
against that file's own placements -- the numbers layout was GIVEN, not the board it made.
That comparison can only ever agree with itself, and it did, while:
  * both panel connectors' bodies stopped 0.54 mm short of the board edge (the layout
    had put their courtyards flush, and a courtyard is the keep-out, not the part);
  * the 24 V barrel jack faced ALONG the board at the chassis rail -- at 0 degrees that
    footprint's mouth is its local +Y -- and was drawn as a panel inlet;
  * the USB-C hole was cut 7.85 mm above the receptacle it was for, at the TS jack's
    axis height, because every panel hole shared one Z.
None of those is visible in a copy of the placements. All three are visible here.

WHAT KiCad DOES NOT CARRY is kept below, keyed by FOOTPRINT, because it is a fact about the
PART and the same on every board: how tall each body stands, and for a panel connector
which way its mouth faces in the footprint's own frame, how high its axis sits, and what
it needs cut in a panel. Every figure says where it came from.
"""
from __future__ import annotations

import json
import math
import os
from functools import lru_cache

import cadquery as cq

from .helpers import box_at

GEOM_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "elec", "geom")          # tracked: elec/out is git-ignored


@lru_cache(maxsize=None)
def load(board: str) -> dict:
    """The routed board's exported geometry (see elec/export_geom.py)."""
    path = os.path.join(GEOM_DIR, board + ".geom.json")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def fp_name(fpid: str) -> str:
    return fpid.split(":")[-1]


def footprint(board: str, ref: str) -> dict:
    for f in load(board)["footprints"]:
        if f["ref"] == ref:
            return f
    raise KeyError("%s has no %s -- was the board re-routed and re-exported?" % (board, ref))


# ── BODY HEIGHT above the board's top face, per footprint ────────────────────────────
# Carried over from the hand-entered heights the old tables had -- the only height data
# the project holds for these parts. What changed is that each is now a property of the
# PART (one line per footprint, whatever board it is on) and the XY comes from the routed
# board's F.Fab body instead of a courtyard.
HEIGHT = {
    "BarrelJack_CUI_PJ-102AH_Horizontal": 11.0,
    "C_0402_1005Metric": 0.55, "R_0402_1005Metric": 0.50,
    "C_0805_2012Metric": 1.45, "C_1206_3216Metric": 1.60, "C_1210_3225Metric": 1.80,
    "Crystal_SMD_3225-4Pin_3.2x2.5mm": 0.90,
    # the lever board's QFNs: CH32V203G6U6 (QFN-28 4x4, 0.90 max), MT6701QT (QFN-16, 0.80)
    "QFN-28-1EP_4x4mm_P0.4mm_EP2.4x2.4mm": 0.90, "QFN-16-1EP_3x3mm_P0.5mm_EP1.45x1.45mm": 0.80,
    "D_SMA": 2.20, "D_SOD-123": 1.10, "D_SOD-523": 0.75,
    "HVQFN-24-1EP_4x4mm_P0.5mm_EP2.5x2.5mm": 0.80,
    "QFN-68-1EP_8x8mm_P0.4mm_EP5.2x5.2mm": 0.90,
    "JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical": 7.0,
    "JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical": 7.0,
    "JST_PH_B8B-PH-K_1x08_P2.00mm_Vertical": 6.0,   # JST PH top entry (motor ctrl J2 --
                                                    # 8-way since bus B became a mid-bus
                                                    # pass-through; same 6.0 body as the
                                                    # 4-way it replaced, 17.9 long)
    "JST_PH_S8B-PH-SM4-TB_1x08-1MP_P2.00mm_Horizontal": 5.5,   # cadkit PH_SIDE_H
    "Jack_6.35mm_Neutrik_NMJ4HCD2_Horizontal": 15.67,     # Neutrik's STEP: body top
    "L_0603_1608Metric": 0.95, "L_Taiyo-Yuden_NR-30xx": 1.50,
    "Relay_DPDT_FRT5_SMD": 5.10,
    "SOT-23": 1.30, "SOT-23-5": 1.45, "SOT-23-6": 1.10,
    "TSSOP-16_4.4x5mm_P0.65mm": 1.20, "TSSOP-20_4.4x6.5mm_P0.65mm": 1.20,
    "TerminalBlock_MaiXu_MX126-5.0-02P_1x02_P5.00mm": 10.5,
    "USB_A_Receptacle_GCT_USB1046": 6.60,
    # measured off HRO's own model (KiCad demo royalblue54L_feather): shell z 0.05..3.25
    "USB_C_Receptacle_HRO_TYPE-C-31-M-12": 3.25,
    "TestPoint_Pad_D1.5mm": 0.0,       # bare copper
    # the motor controller's (2026-09-21), package max heights off the JEDEC outlines / the
    # makers' drawings -- the old hand table carried the same 1.75 / 1.10 for these
    "SOIC-8_3.9x4.9mm_P1.27mm": 1.75, "SOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.29x3mm": 1.75,
    "D_SMB": 2.45, "Fuse_1206_3216Metric": 1.10, "R_0603_1608Metric": 0.55,
    "L_Bourns-SRN6028": 2.80,
    # the output board's analog rewrite (2026-09-21)
    "TSSOP-14_4.4x5mm_P0.65mm": 1.20,              # PCM1808PWR (TI PW package, 1.20 max)
    "Relay_DPDT_Omron_G6K-2F-Y": 5.20,              # Omron G6K-2F-Y: 10 x 6.5 x 5.2 (p.6)
}
# a top-entry XH with its XHP plug seated: 9.8 over the board (JST's "assembled board
# height"), which is what a housing has to leave room for -- see solid(mated=True)
_XH_MATED_H = 9.8
# ⚠ ESTIMATE, NOT READ: a top-entry PH with its PHR plug seated. 6.0 body + the PHR's
# reach above it; confirm off JST's ePH drawing (the same pages cadkit's PH_SIDE_* were
# rendered from) before a housing is cut to it.
_PH_MATED_H = 8.0

# ── PANEL CONNECTORS: the facts a panel is cut to ───────────────────────────────────
#   mouth   the mouth's direction in the footprint's OWN frame (KiCad's, +Y DOWN)
#   axis_h  mouth axis above the board's top face
#   nose    what stands IN FRONT of the F.Fab body, along the mouth (None: nothing)
#   opening the panel hole: ("round", d) | ("stadium", w, h) | ("rect", w, h)
#   mount   "rear": the body's shoulder bears on the panel's INSIDE and a nut clamps it
#           (so the body front sits AT the panel's inner face);
#           "through": the body itself passes into the panel toward its outer face
PANEL = {
    # Neutrik NMJ4HCD2, off Neutrik's own STEP (d-nmj4hcd2.stp) and drawing (ST-NMJ4HCD2),
    # both read 2026-09-21: bore axis 8.14 above the PCB (the old 9.5 was a flagged guess,
    # 1.36 high); a 3.0 mm O11.4 STUB in front of the body's shoulder, which F.Fab draws as
    # the last 3.0 of the outline, and which locates in the panel's O11.4 hole; and a
    # separate NOSE NUT -- a 2.05 hex head, A/F 11, on a 3.74 shank -- that screws into the
    # jack and clamps the panel against the shoulder. Clamped thickness 3.0..4.7 (the
    # drawing's three 1.2 washers build thin panels up to it).
    #   stub     (d, length) in front of the shoulder, INSIDE the F.Fab outline
    #   nut      (head A/F, head thickness, shank d, shank length)
    #   clamp    the thickness the nut clamps, chosen in that window
    #   boss_d   the pad the endplate stands behind the panel for the shoulder to bear on
    #   cbore_d  the face counterbore the nut's head sits in, flush: 15.6, a thin-wall
    #            11 mm socket (OD <= 15.2) plus 0.2 a side. Wider could not be had -- at an
    #            8.14 axis a O16.5 dips 0.11 below the board's top at the panel.
    #   boss_d   the counterbore plus a 1.6 wall all round, flat underneath at the
    #            counterbore's own bottom so no sliver is left between them
    "Jack_6.35mm_Neutrik_NMJ4HCD2_Horizontal": dict(
        mouth=(1.0, 0.0), axis_h=8.14, nose=None, stub=(11.4, 3.0),
        nut=(11.0, 2.05, 9.0, 3.74), clamp=4.0, boss_d=18.8, cbore_d=15.6,
        opening=("round", 11.8), mount="rear"),
    # HRO TYPE-C-31-M-12, measured off HRO's model: shell 8.94 x 3.20 on the board, so
    # the axis is 1.65 up. Mouth is the footprint's +Y. The OPENING is overmold-sized
    # (USB-C plug overmold max 12.35 x 6.50), not shell-sized: this receptacle cannot
    # reach the face (see J1_SETBACK in elec/output_panel.py), so the plug has to be able
    # to follow it in.
    "USB_C_Receptacle_HRO_TYPE-C-31-M-12": dict(
        mouth=(0.0, 1.0), axis_h=1.65, nose=None,
        opening=("stadium", 12.8, 7.0), mount="through"),
    # CUI / Same Sky PJ-102AH, mechanical drawing dated 09/12/2024: body 9.00 wide x
    # 11.00 tall x 14.40 long, axis 6.50 +-0.10 above the PCB, plug opening O6.5, O2.0
    # centre pin, front face 7.70 ahead of pin 2 (10.70 - 3.00) -- which is what the
    # KiCad footprint has, so the placement arithmetic stands. Mouth is the footprint's
    # +Y: what faced the chassis rail at 0 degrees. It passes THROUGH the panel to the
    # face, so the window is the body's own section plus 0.3 a side -- centred on the
    # BODY (5.5 up), not the axis (6.5 up): the body is not symmetric about its bore.
    "BarrelJack_CUI_PJ-102AH_Horizontal": dict(
        mouth=(0.0, 1.0), axis_h=6.5, nose=None,
        opening=("rect", 9.6, 11.6, 5.5), mount="through"),
}


def holes(board: str):
    """[(x, y, d)] the board's cut holes (its mounting hole), board frame."""
    out = []
    for h in load(board).get("holes", []):
        # the BOX centre, not the vertex mean: KiCad spaces an arc's points unevenly, and
        # the mean of the motor controller's came out 0.8 mm off its hole
        xs, ys = [p[0] for p in h], [p[1] for p in h]
        out.append(((min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0,
                    max(max(xs) - min(xs), max(ys) - min(ys))))
    return out


def _plate(board: str) -> cq.Workplane:
    """The laminate itself: the routed OUTLINE (an L where the board has a mounting ear)
    minus its holes -- not the outline's bounding box, which would lay a slab under
    everything beside the ear."""
    g = load(board)
    t = g["thickness_mm"]
    poly = g.get("outline_poly")
    if not poly:
        w, l = g["outline_mm"]
        return box_at(w, l, t, x=0.0, y=0.0, z=t / 2.0)
    plate = cq.Workplane("XY").polyline([tuple(p) for p in poly]).close().extrude(t)
    for h in g.get("holes", []):
        plate = plate.cut(cq.Workplane("XY").polyline([tuple(p) for p in h]).close()
                          .extrude(t + 2.0).translate((0, 0, -1.0)))
    return plate


def _rot(v, deg):
    """A footprint-frame vector (KiCad, +Y down) into the board frame (+Y up), for a
    footprint at KiCad orientation `deg` (counter-clockwise as drawn on screen)."""
    t = math.radians(deg)
    lx, ly = v
    x = lx * math.cos(t) + ly * math.sin(t)
    y = -lx * math.sin(t) + ly * math.cos(t)
    return (round(x, 9), round(-y, 9))


def mouth(board: str, ref: str) -> dict:
    """Where a panel connector's mouth is, in the board frame: direction, the body's
    FRONT along that direction, the axis's position across it, and its height above
    the board top. Plus the part's panel facts."""
    f = footprint(board, ref)
    spec = PANEL[fp_name(f["fpid"])]
    d = _rot(spec["mouth"], f["rot"])
    x0, x1, y0, y1 = f["fab"]
    if abs(d[0]) > 0.5:          # mouth along X
        front = x1 if d[0] > 0 else x0
        # the axis sits mid-body across the mouth for all three parts: the USB-C shell
        # and the barrel are symmetric, and the NMJ4's T/TN pad pair straddles it
        across = (y0 + y1) / 2.0
    else:
        front = y1 if d[1] > 0 else y0
        across = (x0 + x1) / 2.0
    return dict(dir=d, front=front, across=across, axis_h=spec["axis_h"], spec=spec)


def solid(board: str, mated: bool = False) -> cq.Workplane:
    """The board in its OWN frame: centred on the origin in XY, underside at z = 0, parts
    rising +Z. Every part is its routed F.Fab body extruded to its HEIGHT, and a panel
    connector with a nose gets that too. `mated=True` stands every top-entry XH at its
    plugged height -- the envelope a housing has to clear, not the bare header."""
    g = load(board)
    t = g["thickness_mm"]
    out = _plate(board)
    missing = sorted({fp_name(f["fpid"]) for f in g["footprints"]
                      if f["fab"] and fp_name(f["fpid"]) not in HEIGHT})
    if missing:
        raise KeyError("%s: no HEIGHT for %s -- a part with no height is a part the CAD "
                       "would silently leave out" % (board, ", ".join(missing)))
    for f in g["footprints"]:
        if not f["fab"]:
            continue                               # solder jumpers: flat copper
        h = HEIGHT[fp_name(f["fpid"])]
        if mated and fp_name(f["fpid"]).startswith("JST_XH_") and "Vertical" in f["fpid"]:
            h = _XH_MATED_H
        elif mated and fp_name(f["fpid"]).startswith("JST_PH_") and "Vertical" in f["fpid"]:
            h = _PH_MATED_H
        if h <= 0.0:
            continue
        x0, x1, y0, y1 = f["fab"]
        z0 = -h if f["side"] == "B" else t
        spec = PANEL.get(fp_name(f["fpid"]))
        if spec and spec.get("stub"):
            # the body box stops at the SHOULDER; the stub is a O11.4 cylinder, not the body's
            # full 18.2 width -- drawn as a box it could never pass the panel's O11.4 hole
            m = mouth(board, f["ref"])
            sd, sl = spec["stub"]
            assert m["dir"][0] > 0.99, "a stubbed panel part must face +X"
            x1 = m["front"] - sl
            ax_z = t + m["axis_h"]
            out = out.union(cq.Workplane("YZ").circle(sd / 2.0).extrude(sl)
                            .translate((x1, m["across"], ax_z)))
            af, ht, shd, shl = spec["nut"]
            head0 = x1 + spec["clamp"]                  # the head bears on the clamp's face
            out = out.union(cq.Workplane("YZ").polygon(6, af / math.cos(math.pi / 6))
                            .extrude(ht).translate((head0, m["across"], ax_z)))
            out = out.union(cq.Workplane("YZ").circle(shd / 2.0).extrude(shl)
                            .translate((head0 - shl, m["across"], ax_z)))
        out = out.union(box_at(x1 - x0, y1 - y0, h, x=(x0 + x1) / 2.0,
                               y=(y0 + y1) / 2.0, z=z0 + h / 2.0))
        if spec and spec["nose"]:
            m = mouth(board, f["ref"])
            kind, d, length = spec["nose"]
            assert kind == "round" and abs(m["dir"][0]) > 0.5
            sx = m["front"] if m["dir"][0] > 0 else m["front"] - length
            out = out.union(cq.Workplane("YZ").circle(d / 2.0).extrude(length)
                            .translate((sx, m["across"], t + m["axis_h"])))
    return out
