"""THE LEG'S BLIND-MATE BOARDS -- four small passive PCBs, two joints.

    py -3.12 elec/leg_pogo.py            # -> elec/out/leg_pogo_{male,female}_{top,bottom}.*

src/leg_pogo.py is the mechanical truth (the pockets, the screws, the dimension chain from
the mating plane) and says of itself "this is CAD for bronner to route from, not a routed
board". This is the routed board. Every dimension below is READ from that module; nothing
is retyped, and _check_against_cad() fails the generator if the two drift.

WHAT EACH BOARD IS. Four conductors of bus B (GND, +5V, CAN_H, CAN_L -- harness.PH_PINOUT)
straight through, and nothing else:
  * MALE, on the leg, standing on edge in the tenon's end: a right-angle 1 x 4 spring-pin
    header on the lower edge (LCSC C54799748) and a side-entry JST PH on the upper edge
    (S4B-PH-SM4-TB, C265102), one M4 through the board.
  * FEMALE, on the fixed part, flat in a pocket: a vertical gold target (C54930022) and a
    side-entry JST ZR (S4B-ZR-SM4A-TF, C485354), one M4 through the board.
Every placed part is on ONE face (the panel's shared assembly setting) and the finish
stays HASL: the contact surfaces are the two parts' own gold.

FOUR DESIGNS, NOT TWO, AND THE REASON IS CHIRALITY. The CAD draws both joints from one set
of (t, s, d) numbers with d reversed -- into the tenon is +Z at the bottom joint and -Z at
the top. Reversing one axis of a single-faced board is a MIRROR, not a rotation: the M4
hole sits 3.0 off the pin row toward one side (it is on the leg's axis; the row is not),
so the top board is the bottom board's mirror image and no turning of one makes the other.
Two holes on one board would make the male symmetric, but 4.5 mm holes at +-3.0 leave a
1.5 mm web between them and 1.25 outside -- nowhere for four tracks to pass. So each joint
has its own pair, generated from the same code with x negated.

⚠ WHICH CONTACT CARRIES WHICH NET IS DECIDED BY POSITION, NOT BY PAD NUMBER. The header
and the target are symmetric parts; what must agree across a joint is the net at each
position ALONG THE ROW (the CAD's s). The rule, at both joints and on both boards: the
contact at the k-th s position, counting up, carries harness.PH_PINOUT[k]. The pad number
that lands there differs between the mirrored variants, so the netlist is built by
computing where each pad ends up -- and check_pogo_nets() re-reads the ROUTED board and
proves it, because a hand-derived frame mapping returns believable wrong numbers and this
one would put 5 V on CAN_L.

DEBUG. Each board carries four bare test pads, one per conductor, in the harness order
(TP1-TP4 = GND, +5V, CAN_H, CAN_L); only the ground pad's letter fits on the silk. With
the leg off, the pins are spring-loaded gold you do not want to slip a probe on, and the
target's faces are 0.44 mm apart; the pads are where a meter, a scope ground or a CAN
analyser clips on. Bring-up use: continuity pad-to-pad through a mated joint is the test
that the mirrored pair is the right pair.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT_DIR, exist_ok=True)
os.chdir(OUT_DIR)

import json  # noqa: E402
import math  # noqa: E402

import harness  # noqa: E402

PINOUT = harness.PH_PINOUT                      # GND, V5, CAN_H, CAN_L
NET_NAME = {"GND": "GND", "V5": "+5V", "CAN_H": "CAN_H", "CAN_L": "CAN_L"}

HDR_FP = "Steel:Xinyangze_YZ165615055F-04025"
TGT_FP = "Steel:Xinyangze_YZ185115035T-04025"
# ⚠ BOTH JSTs ARE LOCAL COPIES OF KiCad's FOOTPRINTS, ONE NUMBER CHANGED IN EACH, because the
# CAD's dimension chain puts each connector where the library part cannot go:
#   * PH: the mouth is ON the board's top edge, and the library's reinforcement lands run
#     to the mouth. They are trimmed 0.4 at that end (3.4 -> 3.0) for the 0.3 edge rule.
#   * ZR: its tails end 0.5 from the target's housing, and the library courtyard runs 0.5
#     past the tail pads. It stops at the pad tips here; the copper gap (0.2) is DRC's.
PH_FP = "Steel:JST_PH_S4B-PH-SM4-TB_MouthOnEdge"
ZR_FP = "Steel:JST_ZH_S4B-ZR-SM4A-TF_TightCourtyard"
TP_FP = "TestPoint:TestPoint_Pad_D1.0mm"

# ── the footprints' own geometry, in KiCad's frame (y DOWN), as (pad, x, y) ──────────────
# layout.py anchors a part on the centroid of ALL its pads, mounting pads and peg holes
# included, so the centroid is computed from the same list rather than assumed.
_HDR = [("1", -3.75, 0.0), ("2", -1.25, 0.0), ("3", 1.25, 0.0), ("4", 3.75, 0.0),
        ("", -5.25, -0.45), ("", 5.25, -0.45)]
_HDR_REAR = 1.05            # the housing's rear, +y of the pad row
_TGT = [("1", -3.81, 0.0), ("2", -1.27, 0.0), ("3", 1.27, 0.0), ("4", 3.81, 0.0)]
_PH = [("1", -3.0, -2.85), ("2", -1.0, -2.85), ("3", 1.0, -2.85), ("4", 3.0, -2.85),
       ("MP", -5.35, 2.7), ("MP", 5.35, 2.7)]
_PH_MOUTH = 4.6             # courtyard 5.1 less its 0.5 margin: tails 2.6 + body 6.0 = 8.6
_ZR = [("1", -2.25, -1.65), ("2", -0.75, -1.65), ("3", 0.75, -1.65), ("4", 2.25, -1.65),
       ("MP", -4.2, 2.05), ("MP", 4.2, 2.05)]
_ZR_MOUTH = 4.0             # courtyard 4.5 less 0.5: tails 1.5 + body 5.0 = 6.5


def _centroid(pads):
    return (sum(p[1] for p in pads) / len(pads), sum(p[2] for p in pads) / len(pads))


def _pad_xy(pads, at, rot):
    """Where each pad lands on the board (authored frame, y UP), for a part whose pad
    centroid is placed at `at` and turned `rot` degrees counter-clockwise."""
    cx, cy = _centroid(pads)
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    out = []
    for num, x, y in pads:
        u, v = x - cx, -(y - cy)                 # KiCad y down -> authored y up
        out.append((num, at[0] + c * u - s * v, at[1] + s * u + c * v))
    return out


def _anchor(pads, rot, want_xy, of_xy):
    """The placement that puts the footprint-frame point `of_xy` at board `want_xy`."""
    cx, cy = _centroid(pads)
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    u, v = of_xy[0] - cx, -(of_xy[1] - cy)
    return (want_xy[0] - (c * u - s * v), want_xy[1] - (s * u + c * v))


def _cad():
    from src import leg_pogo as P
    return P


def design(kind, joint):
    """One of the four boards. Returns (stem, parts, BOARD_NOTES).

    `parts` is [(ref, value, footprint, description, {pad: net})]. The frame: MALE x = the
    CAD's s (negated at the top joint), y = d from the board's middle; FEMALE x = t
    (negated at the top joint), y = s, both from the board's middle."""
    P = _cad()
    m = 1.0 if joint == "bottom" else -1.0       # the mirror; see the docstring
    stem = "leg_pogo_%s_%s" % (kind, joint)
    hole_d = P.HOLE_D
    parts, notes = [], {}

    def nets_by_s(pads, at, rot, s_of):
        """{pad: net} for a contact row: sort the numbered pads by s, k-th gets PINOUT[k]."""
        row = sorted(((s_of(x, y), num) for num, x, y in _pad_xy(pads, at, rot)
                      if num.isdigit()))
        return {num: NET_NAME[PINOUT[k]] for k, (_s, num) in enumerate(row)}

    conn_nets = {str(i + 1): NET_NAME[n] for i, n in enumerate(PINOUT)}

    if kind == "male":
        W, L = P.MB_S, P.MB_TOP - P.EDGE_D
        dc = (P.MB_TOP + P.EDGE_D) / 2.0
        Y = lambda d: d - dc                                     # noqa: E731
        # header: rear at d = REAR, plungers toward -d, so the footprint is turned 180
        hdr_at = _anchor(_HDR, 180.0, (0.0, Y(P.REAR)), (0.0, _HDR_REAR))
        # PH: mouth ON the top edge, facing +d
        ph_at = _anchor(_PH, 180.0, (0.0, Y(P.MB_TOP)), (0.0, _PH_MOUTH))
        hole = (m * P.M_HOLE_S, Y(P.M_HOLE_D))
        # test pads: beside the hole, between the header's rear and the PH's tails
        tp = [(-(m * P.M_HOLE_S / abs(P.M_HOLE_S)) * x, Y(d)) for x, d in ((1.6, 9.9), (4.4, 9.9), (1.6, 12.6), (4.4, 12.6))]
        parts.append(("J1", "YZ165615055F-04025-02", HDR_FP,
                      "right-angle 1x4 spring-pin header, LCSC C54799748 (or -01, C5296819)",
                      nets_by_s(_HDR, hdr_at, 180.0, lambda x, y: m * x)))
        parts.append(("J2", "S4B-PH-SM4-TB", PH_FP,
                      "leg harness, side entry, mouth up the leg (LCSC C265102)", conn_nets))
        place = {"J1": hdr_at + (180.0,), "J2": ph_at + (180.0,)}
        s_axis = "x"
    else:
        W, L = P.FB_T1 - P.FB_T0, P.FB_S1 - P.FB_S0
        tc, sc = (P.FB_T1 + P.FB_T0) / 2.0, (P.FB_S1 + P.FB_S0) / 2.0
        X = lambda t: m * (t - tc)                               # noqa: E731
        Y = lambda s: s - sc                                     # noqa: E731
        tgt_at = (X(P.PIN_T), Y(0.0))
        # ZR: mouth ON the -t edge, facing -t (so -x at the bottom joint, +x at the top)
        zr_rot = 270.0 if m > 0 else 90.0
        zr_at = _anchor(_ZR, zr_rot, (X(P.FB_T0), Y(0.0)), (0.0, _ZR_MOUTH))
        hole = (X(P.F_HOLE_T), Y(P.F_HOLE_S))
        # test pads: the corner the screw's head and the ZR leave free
        tp = [(X(t), Y(s)) for t, s in ((-2.4, -8.5), (-4.4, -8.5), (-2.4, -10.7), (-4.4, -10.7))]
        parts.append(("J1", "YZ185115035T-04025-01", TGT_FP,
                      "vertical 1x4 gold contact target, LCSC C54930022",
                      nets_by_s(_TGT, tgt_at, 90.0, lambda x, y: y)))
        parts.append(("J2", "S4B-ZR-SM4A-TF", ZR_FP,
                      "harness stub, side entry (takes the ZHR-4 crimp housing; LCSC C485354)",
                      conn_nets))
        place = {"J1": tgt_at + (90.0,), "J2": zr_at + (zr_rot,)}
        s_axis = "y"

    for i, n in enumerate(PINOUT):
        ref = "TP%d" % (i + 1)
        parts.append((ref, n, TP_FP, "probe pad -- %s; bare copper, no component"
                      % NET_NAME[n], {"1": NET_NAME[n]}))
        place[ref] = tp[i] + (0.0,)

    notes.update({k: v for k, v in notes.items()})
    notes.update({
        "outline_mm": (W, L),
        # The FEMALE's screw head bears on the board (the male's is recessed in the tenon's
        # flat and never touches it), so its head -- 7.6 -- keeps copper out from under it.
        # The quality pass found tracks and a via 0.6-0.8 mm inside that circle.
        "cutouts": [dict({"xy": hole, "d": hole_d},
                         **({} if kind == "male" else {"head_d": P.HEAD_D}))],
        "hole": {"xy": hole, "d": hole_d},
        "layers": 2,
        "thickness_mm": 1.6,
        "placements": {k: (round(v[0], 4), round(v[1], 4), v[2]) for k, v in place.items()},
        # 1 A a pin is the header's rating and bus B is current-limited well under it;
        # 0.5 mm is what a 0.7 mm ZR tail pad will take without necking.
        # The female is 10 mm wide with a connector, a target and four pads on it; at 0.5 the
        # router stranded a test pad on one mirror or the other. 0.3 mm is 1.0 A.
        # 0.35, not 0.3: the quality pass measured 0.30 as a hair under what 1 A needs at a
        # 10 C rise (IPC-2221, 1 oz outer), and 1 A is what the contacts may be asked for.
        "net_widths": {"+5V": 0.5, "GND": 0.5} if kind == "male" else {"+5V": 0.35, "GND": 0.35},
        "mounting_hole_xy": hole,
        "single_sided": True,
        "qty_per_instrument": 1,
        # for check_pogo_nets(): which board axis is the CAD's s, and its sign
        "pogo": {"kind": kind, "joint": joint, "s_axis": s_axis, "s_sign": m if kind == "male" else 1.0,
                 "pinout": [NET_NAME[n] for n in PINOUT]},
    })
    # ONE LETTER PER TEST PAD, because that is what fits: the pads are 2.7 mm apart on a
    # board 10 mm wide, and "CAN_H" at the legible 1.0 mm is 4.4 mm long. G, 5V, H, L in
    # the harness order; kicad_silk places each beside its pad or reports that it could not.
    notes["silk_labels"] = {"TP1": "G", "TP2": "5V", "TP3": "H", "TP4": "L"}
    # The stem is 22 characters and the back is 10-13 mm wide with vias across it.
    notes["silk_name"] = "POGO %s %s" % ("MALE" if kind == "male" else "FEM",
                                         "BOT" if joint == "bottom" else "TOP")
    notes["quality"] = _quality(kind, parts)
    return stem, parts, notes


# ── THE QUALITY RECORD (cadkit/PCB_QUALITY.md), one text for the four boards ─────────────
# Each line says what it was checked AGAINST. A rule that is not here is OPEN, and why it
# is open is in docs/pcb-quality-status.md.
def _quality(kind, parts):
    j1_5v = [pad for pad, net in parts[0][4].items() if net == "+5V"][0]
    male = kind == "male"
    width = "0.5" if male else "0.35"
    return {
        # 1 A is the spring header's rating (and the ZH contact's): the most this joint
        # may ever be asked to pass. Bus B's real load is a handful of sensor boards.
        "power_paths": [{"net": "+5V", "from": "J2.2", "to": "J1.%s" % j1_5v, "amps": 1.0}],
        "pinouts": {
            "S4B-PH-SM4-TB": "JST ePH.pdf p.4, Header (SMT type) / Side entry: looking INTO "
                             "the mouth with the board below, the No. 1 circuit mark is on "
                             "the left. KiCad JST_PH_S4B-PH-SM4-TB has the mouth toward +Y "
                             "and pad 1 at -X: the same end. The local copy changes only "
                             "the reinforcement lands' length. Read 2026-10-04",
            "S4B-ZR-SM4A-TF": "JST eZH.pdf p.5, Header / SMT type / SM4 type, Side entry: "
                              "looking INTO the mouth with the board below, No. 1 circuit "
                              "is on the left. KiCad JST_ZH_S4B-ZR-SM4A-TF has the mouth "
                              "toward +Y and pad 1 at -X: the same end. The local copy "
                              "changes only the courtyard. Read 2026-10-04",
            "YZ165615055F-04025-02": "a symmetric 1 x 4 row: there is no pin order to get "
                                     "wrong, only POSITION. The k-th contact along the row "
                                     "carries harness.PH_PINOUT[k]; `leg_pogo.py --check` "
                                     "re-reads the ROUTED board and proves it (run "
                                     "2026-10-04: GND, +5V, CAN_H, CAN_L on all four)",
            "YZ185115035T-04025-01": "a symmetric 1 x 4 row of lands: position, not pad "
                                     "number, decides the net. `leg_pogo.py --check` proves "
                                     "the routed order on all four boards (run 2026-10-04)",
        },
        # A12 "Break it when" (b): no site at the legible size, and the text is not
        # needed to assemble or wire the board.
        "waive": {"A12:silk text height":
                  "the front face is all courtyard and the back is 10-13 mm wide with vias "
                  "across it: the ground test pad's letter (and a pin legend, on the one "
                  "board where one fits at all) has no site at 1.0 mm and is printed at "
                  "0.8. Neither is needed to build or wire the board -- the order is "
                  "fixed by the polarised housings and written down (M31) -- and the "
                  "board's name, which is, is at 1.0 mm or larger on all four"},
        "manual": {
            "M1": "across the joint: `leg_pogo.py --check` reads the four ROUTED boards and "
                  "finds GND, +5V, CAN_H, CAN_L along the row on every one, so male and "
                  "female agree contact for contact at both joints. Harness side: J2's ways "
                  "1-4 are harness.PH_PINOUT, the one constant every bus-B connector binds "
                  "to; the leads are crimped 1:1. PH and ZH are both polarised housings, "
                  "and the joint itself cannot mate offset: the leg's joinery is engaged "
                  "before the pins touch",
            "M3": "measured on the routed board: GND and +5V are the same width (%s mm, "
                  "set together in net_widths), both plain tracks, no pour and no slot. "
                  "There is no analog reference on this board" % width,
            "M4": "no capacitor, no regulator and no load: four conductors straight "
                  "through (A2 reports the same)",
            "M5": "bus B is 5 V. Spring header 12 V DC / 1 A (maker's drawing, as recorded "
                  "in src/leg_pogo.py RA_V); JST PH 100 V / 2 A (ePH.pdf p.1); JST ZH "
                  "50 V / 1 A (eZH.pdf p.1). Current is M33",
            "M9": "four bare 1.0 mm test pads, one per conductor, in a 2 x 2 block in the "
                  "harness order TP1-TP4 = GND, +5V, CAN_H, CAN_L. Only TP1's letter (G) "
                  "finds a silk site on every board, so the ORDER is the label: G marks "
                  "the first pad. No MCU on the board",
            "M31": "decision: the board carries a short name and revision (back, e.g. "
                   "'POGO FEM BOT r1') and a G beside the ground test pad, and nothing "
                   "else that is promised. There is no site for "
                   "more: kicad_silk reports no room for the other three pad letters or "
                   "either connector's pin legend on a board 10-13 mm wide whose front is "
                   "all courtyard. Relied on instead: both connectors are polarised and "
                   "carry the one bus-B order (GND, +5V, CAN_H, CAN_L from pin 1), the "
                   "test pads repeat it from the lettered pad, and it is written in "
                   "elec/harness.py and the bring-up notes. JST's own pin-1 marks are "
                   "moulded on the housings",
            "M11": ("finish.py's CAD check: both routed parts present where the CAD draws "
                    "them, the M4 cutout matches (15.9 mm2). "
                    + ("The screw's head is recessed in the tenon's flat and bears on "
                       "plastic, never on the board" if male else
                       "The screw's 7.6 mm head bears on the front face: tracks and vias "
                       "are kept out to 4.0 mm from the hole's centre on that face "
                       "(cutout head_d), measured 4.18 on the routed boards; the test "
                       "pads start at the head's edge by the generator's own assert")
                    + ". Every part is one the fab places; no hand soldering"),
            "M28": ("JST's own parts for J2 (see pinouts). J1: "
                    + ("YZ165615055F-04025-02, LCSC C54799748 -- the land was read today "
                       "from LCSC's footprint for this exact code (EasyEDA CONN-SMD_4P-"
                       "L11.0-W5.5-P2.50): four pads at 2.50 pitch, 1.6 x 2.3, pegs 0.70 "
                       "at +-5.25; ours is the same with the pads trimmed 0.2 at the "
                       "board-edge end (the footprint says why). The maker's spec sheet "
                       "for the code has no dimensioned drawing" if male else
                       "YZ185115035T-04025-01, LCSC C54930022 -- maker's drawing D.0 "
                       "(2025-08-30) read today: 2.54 pitch, housing 10.20 x 2.50, faces "
                       "1.20 dia at 3.50, recommended lands 4 x 2.20 dia; ours are 2.10 "
                       "on the same centres (0.44 between lands instead of 0.34)")),
            "M29": "A12 measures the board against JLCPCB's capability page, read "
                   "2026-10-04 (2-layer, 1 oz, standard service): tracks, holes, rings, "
                   "hole spacing, pad gaps pass, and no via hole is inside a soldered pad. "
                   "There is no two-pad part to tombstone",
            "M32": ("J2 is JST " + ("PH, 2.0 pitch, 2 A / 100 V" if male else
                                    "ZH (ZR header), 1.5 pitch, 1 A / 50 V")
                    + " -- pitch read from the footprint's pads, ratings from the JST "
                    "sheet's first page; it takes the "
                    + ("PHR-4" if male else "ZHR-4") + " housing the leg harness is "
                    "crimped with. The joint's own pair is rated 12 V / 1 A (maker's "
                    "spec sheet for C54799748, read today). Ground is on way 1 of both"),
            "M38": "no ceramic capacitor and no two-pad part on the board. Routed outline, "
                   "no V-score. The harness connector's mouth is on the board's edge, "
                   "facing the way the lead runs; the test pads are bare and in a block "
                   "of their own. The M4 hole is unplated with no copper round it: "
                   "isolated on purpose",
            "M16": "decision: nothing to damp here. The board has no capacitor; what a "
                   "live leg joint rings into is the sensor boards' inputs, signed there",
            "M20": "no terminator and no pull-up on this board, by design: it is a joint "
                   "in the middle of bus B, whose two 120 R are fixed at the far ends. The "
                   "stub it adds is its own ~15 mm of track",
            "M34": "no active part. CAN_H meets CAN_H and CAN_L meets CAN_L across the "
                   "joint and at the harness connector (M1's check reads both)",
            "M40": "no resistor or capacitor value on the board. The spring header and "
                   "the gold target are chosen as a mating PAIR (2.5 against 2.54 pitch, "
                   "lands 2.1 wide): substituting either needs the other's drawing, and "
                   "the generator's header says so",
        },
    }


VARIANTS = tuple((k, j) for k in ("male", "female") for j in ("bottom", "top"))


def _check_against_cad():
    """The numbers this board is cut from, against the pockets cut for it."""
    P = _cad()
    assert abs(P.RA_PITCH - 2.5) < 1e-9 and abs(P.TG_PITCH - 2.54) < 1e-9
    assert abs(P.PH_PITCH - 2.0) < 1e-9 and abs(P.ZR_PITCH - 1.5) < 1e-9
    # the header's shoulder is the male board's lower edge
    assert abs((P.REAR - P.EDGE_D) - P.RA_BODY_D) < 1e-9
    # the PH: tails + body, mouth on the top edge
    assert abs((P.MB_TOP - P.SE_TAIL0) - (P.SE_TAIL + P.SE_DEPTH)) < 1e-9
    # the female's two rows must not meet: ZR tail pad tips against the target's lands
    zr_tip_t = P.ZR_MOUTH + _ZR_MOUTH + 3.0          # pad tip, 0.5 past the tail
    gap = (P.PIN_T - 2.1 / 2.0) - zr_tip_t
    assert gap >= 0.19, "the ZR's tail pads reach the target's lands (%.2f mm)" % gap
    for kind, joint in VARIANTS:
        stem, parts, notes = design(kind, joint)
        W, L = notes["outline_mm"]
        hx, hy = notes["hole"]["xy"]
        r = notes["hole"]["d"] / 2.0
        assert abs(hx) + r + P.EDGE <= W / 2.0 + 1e-9, "%s: the M4 hole leaves the board" % stem
        assert abs(hy) + r + P.EDGE <= L / 2.0 + 1e-9, "%s: the M4 hole leaves the board" % stem
        for ref, (x, y, _r) in notes["placements"].items():
            if ref.startswith("TP"):
                assert abs(x) + 0.5 + 0.3 <= W / 2.0 and abs(y) + 0.5 + 0.3 <= L / 2.0, (
                    "%s: %s is off the board" % (stem, ref))
                assert math.hypot(x - hx, y - hy) >= r + 0.5 + 0.3, (
                    "%s: %s is in the M4 hole's margin" % (stem, ref))
                if kind == "female":
                    assert math.hypot(x - hx, y - hy) >= P.HEAD_D / 2.0 + 0.5, (
                        "%s: %s is under the screw's head" % (stem, ref))


def check_pogo_nets(stem):
    """Re-read the ROUTED board and prove the k-th contact along s carries PINOUT[k].
    Run under KiCad's python (finish has to have written the board)."""
    import pcbnew
    notes = json.load(open(os.path.join(OUT_DIR, stem + ".board.json"), encoding="utf-8"))
    pg = notes["pogo"]
    board = pcbnew.LoadBoard(os.path.join(OUT_DIR, stem + ".kicad_pcb"))
    row = []
    for fp in board.GetFootprints():
        if fp.GetReference() != "J1":
            continue
        for p in fp.Pads():
            if p.GetNumber().isdigit():
                x, y = pcbnew.ToMM(p.GetPosition().x), -pcbnew.ToMM(p.GetPosition().y)
                row.append(((x if pg["s_axis"] == "x" else y) * pg["s_sign"], p.GetNetname()))
    got = [n for _s, n in sorted(row)]
    assert got == pg["pinout"], "%s: contacts along s carry %s, want %s" % (stem, got, pg["pinout"])
    print("%s: contacts along s = %s  ok" % (stem, ", ".join(got)))


if "--check" not in sys.argv:          # --check runs under KiCad's python: no cadquery there
    _check_against_cad()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        for kind, joint in VARIANTS:
            check_pogo_nets("leg_pogo_%s_%s" % (kind, joint))
        sys.exit(0)
    from skidl import ERC, Net, Part, Pin, generate_netlist, reset  # noqa: E402
    import netcheck  # noqa: E402
    for kind, joint in VARIANTS:
        reset()
        stem, parts, notes = design(kind, joint)
        nets = {}
        for ref, value, fp, desc, padnets in parts:
            pins = sorted(set(padnets))
            part = Part(name=value, ref_prefix="".join(c for c in ref if c.isalpha()),
                        ref=ref, tag=ref, dest="NETLIST", tool="skidl", value=value,
                        description=desc, footprint=fp,
                        pins=[Pin(num=n, name=padnets[n], func=Pin.types.PASSIVE) for n in pins])
            for n in pins:
                if padnets[n] not in nets:
                    nets[padnets[n]] = Net(padnets[n])
                    nets[padnets[n]].drive = Pin.drives.POWER
                nets[padnets[n]] += part[n]
        ERC()
        generate_netlist(file_=os.path.join(OUT_DIR, stem + ".net"))
        netcheck.no_orphan_pins(os.path.join(OUT_DIR, stem + ".net"))
        with open(os.path.join(OUT_DIR, stem + ".board.json"), "w") as f:
            json.dump(notes, f, indent=2)
        print("%s: board %.2f x %.2f mm, hole at (%.2f, %.2f)"
              % ((stem,) + tuple(notes["outline_mm"]) + tuple(notes["hole"]["xy"])))
