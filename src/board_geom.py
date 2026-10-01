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
from cadkit import pcb as _CK

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
    "Kycon_KPJX-4S-S": 15.0,                     # 14.4 of body + the 0.6 top boss
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
    "JST_PH_B6B-PH-K_1x06_P2.00mm_Vertical": 6.0,   # JST PH top entry (pi_cap J3)
    # LED strip section (elec/led_strip.py). The 5050 LED is the part that has to be right:
    # it is what the chassis seat aims, and the seat's lips clear the board face by 1.9.
    "XINGLIGHT_XL-5050RGBW": 1.6,                   # 5.0 x 5.0 x 1.6 (LCSC C7371891)
    "HTSSOP-20-1EP_4.4x6.5mm_P0.65mm_EP3.4x6.5mm_Mask2.75x3.43mm": 1.2,   # TLC59711 PWP
    "JST_PH_S6B-PH-SM4-TB_1x06-1MP_P2.00mm_Horizontal": 5.5,   # cadkit PH_SIDE_H
    "JST_XH_S4B-XH-SM4-TB_1x04-1MP_P2.50mm_Horizontal": 5.75,  # XH side entry (JST eXH p.4)
    # ⚠ THE 2x20 SOCKET IS THE STRUCTURE, NOT A COMPONENT ON TOP OF ONE. 8.5 is its body
    # height, and it faces DOWN: the pi_cap hangs off the Pi's header by it, so this figure
    # is the standoff between the Pi's top face and the cap's underside, not a bump on the
    # cap. src/electronics.py uses the same number to place the cap; it is written once here.
    "PinSocket_2x20_P2.54mm_Vertical": 8.5,
    # ⚠ THE UI RIBBON'S HEADER, AND THE NUMBER IS FROM THE LISTING RATHER THAN A DRAWING.
    # LCSC gives HX PZ1.27-2x7P ZZ (C22438122) as "3.9 mm"; 4.0 is that rounded up, which is
    # the safe direction for an envelope. It is not load-bearing either way -- the part lives
    # inside the cap's own 8.5 mm socket standoff, so it has 4.5 mm of headroom -- but a part
    # with no height is a part the CAD leaves out, which is what this table exists to stop.
    "PinHeader_2x07_P1.27mm_Horizontal": 4.0,
    "JST_PH_S8B-PH-SM4-TB_1x08-1MP_P2.00mm_Horizontal": 5.5,   # cadkit PH_SIDE_H
    "JST_PH_S4B-PH-SM4-TB_1x04-1MP_P2.00mm_Horizontal": 5.5,   # cadkit PH_SIDE_H --
                                    # motor_ctrl J2/J6, the bus-B pair on the edge
                                    # that faces the instrument's underside. Same
                                    # body height as the 8-way above; only the
                                    # length differs (11.9 against 19.9).
    "Jack_6.35mm_Neutrik_NMJ4HCD2_Horizontal": 15.67,     # Neutrik's STEP: body top
    # ⚠ THE TRS SIBLING IS THE SAME HOUSING. NMJ4HCD2 and NMJ6HCD2 differ in their
    # CONTACTS, not their body: same shell, same bushing, same panel cut-out, same
    # 15.67 mm to the body top. So this is an alias and not a second measurement --
    # and it has to be here at all because a part with no height is a part the CAD
    # silently leaves out, which is what cad_geom_check caught on the first route.
    "Jack_6.35mm_Neutrik_NMJ6HCD2_Horizontal": 15.67,
    # SC-70-6 (TI DCK): 1.10 mm max body height, SCES424O section 11. It is here because
    # cad_geom_check refused the board without it -- "a part with no height is a part
    # the CAD would silently leave out" -- which is the right way round.
    "SOT-363_SC-70-6": 1.10,
    "L_0603_1608Metric": 0.95, "L_Taiyo-Yuden_NR-30xx": 1.50,
    "Relay_DPDT_FRT5_SMD": 5.10,
    "SOT-23": 1.30, "SOT-23-5": 1.45, "SOT-23-6": 1.10,
    "TSSOP-16_4.4x5mm_P0.65mm": 1.20, "TSSOP-20_4.4x6.5mm_P0.65mm": 1.20,
    "TerminalBlock_MaiXu_MX126-5.0-02P_1x02_P5.00mm": 10.5,
    "USB_A_Receptacle_GCT_USB1046": 6.60,
    # measured off HRO's own model (KiCad demo royalblue54L_feather): shell z 0.05..3.25
    "USB_C_Receptacle_HRO_TYPE-C-31-M-12": 3.25,
    "TestPoint_Pad_D1.5mm": 0.0, "TestPoint_Pad_D1.0mm": 0.0,       # bare copper
    # ...and so is a solder jumper: two pads and a gap. It has no F.Fab body either,
    # which is right -- there is no part. A zero here is what keeps it out of the solids
    # a housing has to clear, rather than a special case at each call site.
    "SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm": 0.0,
    # the motor controller's (2026-09-21), package max heights off the JEDEC outlines / the
    # makers' drawings -- the old hand table carried the same 1.75 / 1.10 for these
    "SOIC-8_3.9x4.9mm_P1.27mm": 1.75, "SOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.29x3mm": 1.75,
    "D_SMB": 2.45, "Fuse_1206_3216Metric": 1.10, "R_0603_1608Metric": 0.55,
    "L_Bourns-SRN6028": 2.80,
    # the output board's analog rewrite (2026-09-21)
    "TSSOP-14_4.4x5mm_P0.65mm": 1.20,              # PCM1808PWR (TI PW package, 1.20 max)
    # the UI board (2026-09-25)
    # THE BODY ONLY -- 8.30, not the catalogue's 10.5, which is over the COLLAR. Read
    # off Alps' own 3D model (the one LCSC ship with C160841) by slicing its mesh: the
    # 17 x 17 case tops out at 8.30, a two-step collar carries on to 10.20, and the
    # D-shaft runs 11.10 to 17.10. src/ui_panel.py draws the collar and the shaft,
    # because a 17 x 17 box 17 tall would read as a collision with the deck the shaft
    # passes cleanly through.
    "Alps_RKJXT1F42001": 8.30,
    "PinHeader_1x20_P2.54mm_Vertical": 8.54,   # 2.54 insulator + 6.0 of pin
    # ESTIMATED, NOT READ: a 2.54 right-angle shrouded IDC header. ZHOURI publish no
    # drawing through LCSC and the KiCad footprint carries no Z. 10.0 is a generous
    # standard body, and elec/ui_board.py asserts the deck clears it -- CONFIRM IT
    # AGAINST THE PART BEFORE THE DECK IS PRINTED, because 11.74 is all the room there
    # is under that panel.
    "IDC-Header_2x07_P2.54mm_Horizontal": 10.0,
    "Relay_DPDT_Omron_G6K-2F-Y": 5.20,              # Omron G6K-2F-Y: 10 x 6.5 x 5.2 (p.6)
    # the fret LED boards (2026-09-29). Every one of these stands INSIDE a light cell
    # unless it is in the bay, so the height is not just a clearance number here -- it
    # is how much of the cell's floor the part takes out of the bounce.
    "XINGLIGHT_XL-5050RGBW": 1.60,     # LCSC C7371891: "Dimensions (L/W/H) 5.0x5.0x1.6"
    "HTSSOP-20-1EP_4.4x6.5mm_P0.65mm_EP3.4x6.5mm_Mask2.75x3.43mm": 1.20,   # TI PWP max
    "Texas_RNX0012_VQFN-HR-12_2x3mm_P0.5mm": 0.90,  # TI RNX0012B outline, 0.8 +0.1
    "L_Sunlord_SWPA4030S": 3.00,                    # SWPA4030 = 4.0 x 4.0 x 3.0
    "JST_PH_S6B-PH-SM4-TB_1x06-1MP_P2.00mm_Horizontal": 5.5,   # cadkit PH_SIDE_H
    # ⚠ THE FOOT STRIP'S CONNECTOR, AND THIS NUMBER IS THE REASON IT IS AN SH. Read off
    # JST's own SH catalogue drawing (side entry type, side view: 6.25 long x 2.95 tall),
    # not a catalogue attribute -- the whole board hangs into a 3.40 mm trough and the
    # 5.5 PH above does not fit. See src/foot_light.py.
    "JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal": 2.95,
    # the fret boards' seam pogo, C5203987: the BARREL, 3.80 tall on its pad (maker's
    # drawing, front view 3.00 x 3.80). The plunger is not in F.Fab -- src/fret_light.py
    # models it, because it leaves the board and crosses a comb wall.
    "Xinyangze_YZF0002-38080-02": 3.80,
}
# a top-entry XH with its XHP plug seated: 9.8 over the board (JST's "assembled board
# height"), which is what a housing has to leave room for -- see solid(mated=True)
_XH_MATED_H = 9.8
# ⚠ ESTIMATE, NOT READ: a top-entry PH with its PHR plug seated. 6.0 body + the PHR's
# reach above it; confirm off JST's ePH drawing (the same pages cadkit's PH_SIDE_* were
# rendered from) before a housing is cut to it.
_PH_MATED_H = 8.0
# ⚠ A THROUGH-HOLE PAD HAS A TAIL, and until now the CAD modelled none of them: solid()
# extrudes every part UPWARD from the board's top face, so a THT connector's posts simply
# did not exist. Every overlap check therefore passed on boards whose posts run into
# whatever they are mounted against -- for the LED strip, the rail wall its back sits ON.
# 3.4 is cadkit.pcb.XH_POST_TAIL, the protrusion below the board on an untrimmed XH post,
# and it is the right order for any 2.00/2.54 header. Trimming is an assembly step nobody
# has specified, so model the untrimmed case: it is the one that has to fit.
_THT_TAIL = 3.4
# ⚠ ...AND ONE SLAB UNDER EVERY PAD IS WRONG FOR A PART WHOSE LEGS ARE FAR APART. solid()
# draws the tail as a box under the bounding box of all the through-hole pads, which is
# right for a pin row and wrong for the 24 V inlet: its eleven lands span 13 x 18.6 mm,
# and the slab's empty corner reached the endplate's board ledge (3.8 mm3 of a leg that
# is not there). A footprint listed here gets one box per leg instead:
#   (x, y, size_x, size_y) in the FOOTPRINT's own frame -- KiCad's, as the .kicad_mod
#   has it -- about its origin, each the HOLE the leg passes through.
THT_LEGS = {
    "Kycon_KPJX-4S-S": [
        (-2.9, -14.65, 0.6, 2.7), (2.9, -14.65, 0.6, 2.7),      # pins 1, 2
        (-2.5, -11.0, 0.6, 2.7), (2.5, -11.0, 0.6, 2.7),        # pins 3, 4
        (-7.8, -16.0, 0.6, 2.7), (7.8, -16.0, 0.6, 2.7),        # rear shell legs
        (-7.8, -7.5, 2.2, 2.2), (7.8, -7.5, 2.2, 2.2),          # front shell legs
        (0.0, -5.5, 2.2, 1.0),                                  # shell tab
        (-2.5, -7.5, 1.7, 1.7), (2.5, -7.5, 1.7, 1.7),          # the two plastic pegs
    ],
}

# ⚠ A SIDE-ENTRY CONNECTOR'S PLUG LEAVES THROUGH THE BOARD EDGE, and until now solid()
# modelled none of it: the mated branch below tested for "Vertical" only, so every
# HORIZONTAL part came out as its bare socket body. On the motor controller that is the
# whole point of the part -- J2/J6 face the chassis floor and the plug is what a hand
# pulls from underneath -- so the CAD showed a 5.5 mm socket where the real envelope
# reaches 3.6 mm further out, and any hole sized off that solid would be sized to the
# socket. It affects the horizontal XH on the optical board and pi_cap the same way.
# The numbers are cadkit's, read off JST's drawings there rather than re-derived: the
# mated pair is 9.6 long against a 6.0 body (PH, p.2/p.4) and 13.6 against 6.1 (XH).
_SIDE_PLUG_RUN = {"JST_PH_": _CK.PH_PLUG_RUN, "JST_XH_": 7.5}

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
    # The TRS sibling, and every number above is UNCHANGED: Neutrik's D-series housing is
    # common to both, so the panel work -- the 3.0 mm clamp, the nose nut, the 15.6
    # counterbore, the 11.8 opening -- is the same part of the endplate either way. What
    # differs is two more contacts inside the shell, which the panel never sees.
    "Jack_6.35mm_Neutrik_NMJ6HCD2_Horizontal": dict(
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
    # Kycon KPJX-4S-S, drawing rev A17 (08/15/22): body 16.0 wide x 13.4 long x 14.4 tall
    # (15.0 over the top boss), axis 7.1 above the PCB, and a O12.9 x 4.0 NOSE in front
    # of the body -- the shield barrel a KPPX plug's sliding shell latches into. F.Fab is
    # the body alone (elec/footprints/Steel.pretty), so `front` is the body's shoulder and
    # the nose is what passes through the panel to the face: a round hole, 0.3 a side.
    # Mouth is the footprint's +Y.
    "Kycon_KPJX-4S-S": dict(
        mouth=(0.0, 1.0), axis_h=7.1, nose=("round", 12.9, 4.0),
        opening=("round", 13.5), mount="through"),
}


# ── TAIL LENGTH BELOW THE BOARD, per footprint ──────────────────────────────────────
# The other side of HEIGHT, and needed for the same reason: KiCad does not carry it, and
# a part that has it will go straight through anything mounted against the board's
# underside. 0.0 means SURFACE MOUNT -- nothing to clear.
#
# EVERY FOOTPRINT ON A CHECKED BOARD MUST APPEAR, like HEIGHT, so a new part forces the
# decision instead of defaulting to "no tail" and being wrong silently. The UI's clamp
# plate lies against the board and takes a relief under exactly the entries above zero;
# when that rule relieved EVERY footprint instead, the 0402 reliefs left a 1.38 mm web
# between two of them.
TAIL = {
    "Alps_RKJXT1F42001": 3.5,                    # ten terminals + the position lug
    "PinHeader_1x20_P2.54mm_Vertical": 3.0,      # Kinghelm's "end connection pin"
    "IDC-Header_2x07_P2.54mm_Horizontal": 3.0,
    "R_0402_1005Metric": 0.0, "C_0402_1005Metric": 0.0, "C_0805_2012Metric": 0.0,
    # the fret LED boards are SURFACE MOUNT THROUGHOUT, and that is a requirement
    # rather than a preference: the board's underside sits 1.00 mm over the CAN
    # harness (src/fret_light.py), so a 3 mm through-hole tail would be in the cable.
    "XINGLIGHT_XL-5050RGBW": 0.0,
    "HTSSOP-20-1EP_4.4x6.5mm_P0.65mm_EP3.4x6.5mm_Mask2.75x3.43mm": 0.0,
    "Texas_RNX0012_VQFN-HR-12_2x3mm_P0.5mm": 0.0, "L_Sunlord_SWPA4030S": 0.0,
    "JST_PH_S6B-PH-SM4-TB_1x06-1MP_P2.00mm_Horizontal": 0.0,
    "C_1206_3216Metric": 0.0, "Fuse_1206_3216Metric": 0.0,
    "Xinyangze_YZF0002-38080-02": 0.0,
    "JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal": 0.0,   # SMT, like everything on
                                                               # the foot strip: it has
                                                               # 1.90 mm under it
}


def tails(board: str):
    """[(ref, fab, tail)] for every footprint, tail 0.0 for surface mount."""
    out = []
    for f in load(board)["footprints"]:
        if not f["fab"]:
            continue
        name = fp_name(f["fpid"])
        if name not in TAIL:
            raise KeyError("%s: no TAIL for %s -- say whether it has through-hole legs, "
                           "because anything against the board's underside has to clear "
                           "them" % (board, name))
        out.append((f["ref"], f["fab"], TAIL[name]))
    return out


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


def lead_exit(board: str, ref: str):
    """Where a LEAD LEAVES connector `ref`, in the board's own frame (centred in XY,
    underside at z = 0) -- the point a cable should be drawn from.

    ⚠ A SIDE-ENTRY CONNECTOR DOES NOT LET GO UPWARD, and asking for its mated HEIGHT is
    asking the wrong question: it returns how far the body reaches, which for J2/J6 on
    the motor controller is a point inside the socket rather than a seated plug. Those
    two are the whole bus-B input, and their plugs leave through the board EDGE. So this
    reuses the mouth geometry solid() already derives for _SIDE_PLUG_RUN rather than
    carrying a second copy of it: the mouth is the end of the F.Fab body farther from
    the origin, pushed out by the mated plug's run, at the contact axis -- mid-body, not
    over the top.

    For a top-entry part the answer is the old one: straight up off the mated plug.
    """
    f = footprint(board, ref)
    t = load(board)["thickness_mm"]
    name = fp_name(f["fpid"])
    h = HEIGHT[name]
    x0, x1, y0, y1 = f["fab"]
    # ⚠ THE BODY'S CENTRE, NOT THE FOOTPRINT ORIGIN. "each lead leaves its body's centre"
    # is the convention every existing cable is drawn to; the origin sits at the pad row,
    # which for a side-entry part is at the BACK. Using it here would have moved four
    # cables that had nothing wrong with them.
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    if "Horizontal" not in f["fpid"]:
        if name.startswith("JST_XH_"):
            h = _XH_MATED_H
        elif name.startswith("JST_PH_"):
            h = _PH_MATED_H
        return (cx, cy, t + h)
    run = _SIDE_PLUG_RUN.get(name[:7])
    if run is None:
        return (cx, cy, t + h)
    ax = "x" if abs(round(f["rot"]) % 180 - 90) < 1e-6 else "y"
    lo, hi = (x0, x1) if ax == "x" else (y0, y1)
    o = f["x"] if ax == "x" else f["y"]
    if abs((hi - o) - (o - lo)) < 1.0:
        raise ValueError("%s %s: the footprint origin sits mid-body, so which end is "
                         "the mouth cannot be read from the geometry" % (board, ref))
    out = (hi + run) if (hi - o > o - lo) else (lo - run)
    # mid-body in z: the contacts run along the connector's axis, and the lead leaves
    # in line with them rather than off the top of a shell that has no top here.
    z = t + h / 2.0
    return (out, cy, z) if ax == "x" else (cx, out, z)


def bodies(board: str, refs) -> cq.Workplane:
    """Just the named parts' bodies, in the board's own frame.

    For a board the CAD wants to draw in more than one colour. The fret LED boards are
    the case: their 92 LEDs are the point of the part and want to read as LIT, so they
    come out of solid(skip=...) and back in through here. Two parts, no shared volume,
    which is what the overlap gate requires of anything drawn twice."""
    g = load(board)
    t, want = g["thickness_mm"], set(refs)
    out = None
    for f in g["footprints"]:
        if f["ref"] not in want or not f["fab"]:
            continue
        h = HEIGHT[fp_name(f["fpid"])]
        x0, x1, y0, y1 = f["fab"]
        z0 = -h if f["side"] == "B" else t
        b = box_at(x1 - x0, y1 - y0, h, x=(x0 + x1) / 2.0, y=(y0 + y1) / 2.0,
                   z=z0 + h / 2.0)
        out = b if out is None else out.union(b)
    if out is None:
        raise KeyError("%s has none of %s" % (board, sorted(want)[:6]))
    return out


def solid(board: str, mated: bool = False, omit: tuple = (), skip=()) -> cq.Workplane:
    """The board in its OWN frame: centred on the origin in XY, underside at z = 0, parts
    rising +Z. Every part is its routed F.Fab body extruded to its HEIGHT, and a panel
    connector with a nose gets that too. `mated=True` stands every top-entry XH at its
    plugged height -- the envelope a housing has to clear, not the bare header.
    `skip` names refs to leave out, for a caller drawing them separately (see bodies).
    ⚠ `omit` AND `skip` ARE NOT THE SAME EXCLUSION, and they arrived from two branches
    within a day of each other, which is exactly how they would have been collapsed into
    one by mistake. `omit` means THIS INSTANCE DOES NOT FIT THAT PART -- the strip's last
    section has no outgoing header -- so nothing draws it and nothing should. `skip` means
    the part IS fitted and SOMEONE ELSE DRAWS IT, so that it can be a different colour.
    Merge them and either a DNP part reappears or a lit LED is drawn twice."""
    g = load(board)
    t = g["thickness_mm"]
    skip = set(skip)
    out = _plate(board)
    missing = sorted({fp_name(f["fpid"]) for f in g["footprints"]
                      if f["fab"] and fp_name(f["fpid"]) not in HEIGHT})
    if missing:
        raise KeyError("%s: no HEIGHT for %s -- a part with no height is a part the CAD "
                       "would silently leave out" % (board, ", ".join(missing)))
    for f in g["footprints"]:
        if f["ref"] in omit:
            # ⚠ A REF THE BOARD CARRIES BUT THIS INSTANCE DOES NOT FIT. The LED strip's
            # last section has no next section, so its outgoing header is DNP -- and left
            # modelled it projects past the seat and into the chassis (16.4 mm3), which
            # reads as a board that is too long rather than a part that is not there.
            continue
        if not f["fab"] or f["ref"] in skip:
            continue                               # solder jumpers: flat copper
        h = HEIGHT[fp_name(f["fpid"])]
        if mated and fp_name(f["fpid"]).startswith("JST_XH_") and "Vertical" in f["fpid"]:
            h = _XH_MATED_H
        elif mated and fp_name(f["fpid"]).startswith("JST_PH_") and "Vertical" in f["fpid"]:
            h = _PH_MATED_H
        if h <= 0.0:
            continue
        legs = THT_LEGS.get(fp_name(f["fpid"]))
        if legs:
            # each leg where it is, not one slab under all of them (see THT_LEGS)
            for fx, fy, sx, sy in legs:
                ox, oy = _rot((fx, fy), f["rot"])
                wx, wy = (abs(v) for v in _rot((sx, sy), f["rot"]))
                out = out.union(box_at(wx, wy, _THT_TAIL, x=f["x"] + ox, y=f["y"] + oy,
                                       z=-_THT_TAIL / 2.0))
        elif f.get("tht"):
            tx0, tx1, ty0, ty1 = f["tht"]
            out = out.union(box_at(tx1 - tx0, ty1 - ty0, _THT_TAIL,
                                   x=(tx0 + tx1) / 2.0, y=(ty0 + ty1) / 2.0,
                                   z=-_THT_TAIL / 2.0))
        x0, x1, y0, y1 = f["fab"]
        # A SIDE-ENTRY PART GROWS ALONG THE BOARD, NOT UPWARD (see _SIDE_PLUG_RUN). The
        # mating axis is whichever of X/Y the footprint is turned onto, and the mouth is
        # the end of the body FARTHER FROM THE ORIGIN -- the pad row sits behind the
        # mouth, so the origin is at the back. Read off the geometry rather than off
        # `rot`, because that only has to be right about which end is which and cannot
        # be got wrong by a rotation-sign convention.
        _run = _SIDE_PLUG_RUN.get(fp_name(f["fpid"])[:7]) if (
            mated and "Horizontal" in f["fpid"]) else None
        if _run:
            _ax = "x" if abs(round(f["rot"]) % 180 - 90) < 1e-6 else "y"
            _lo, _hi = (x0, x1) if _ax == "x" else (y0, y1)
            _o = f["x"] if _ax == "x" else f["y"]
            if abs((_hi - _o) - (_o - _lo)) < 1.0:
                raise ValueError(
                    "%s %s: the footprint origin sits mid-body, so which end is the "
                    "mouth cannot be read from the geometry" % (board, f["ref"]))
            if _hi - _o > _o - _lo:
                if _ax == "x":
                    x1 += _run
                else:
                    y1 += _run
            else:
                if _ax == "x":
                    x0 -= _run
                else:
                    y0 -= _run
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
