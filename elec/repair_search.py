"""Find a legal via + two-track path to close one stubborn net, on a ROUTED board.

    py -3.12 elec/repair_search.py elec/out/optical +3V3A U2 4

⚠ WHY THIS IS A FILE AND NOT A SCRIPT IN A COMMENT. The same search was written inline
four times in one session and got a different answer each time, because each version
quietly checked a different set of obstacles:

  1st  tracks + vias, 0.20 mm margin, run against a STALE board  -> "no legal site"
  2nd  tracks + vias, 0.15 mm margin                             -> 2638 sites, shortest
       one chosen; it closed +3V3A and cost FIVE analog nets, because it was laid as a
       PRE-LAY and the other 76 nets had to plan around it
  3rd  same, after the netlist changed underneath it              -> the chosen spur
       CROSSED TIA_OUT_2A: a short between two nets
  4th  same, longer path to a different rail                      -> SEVEN violations:
       two solder_mask_bridge against the target part's OWN PAD, three
       copper_edge_clearance, a copper_sliver

Every one of those is the same mistake in a different coat: the search knew about less
of the board than DRC does. Tracks and vias are not the obstacles -- PADS and the BOARD
OUTLINE are obstacles too, and a 4 mm path can miss them by luck while a 14 mm path
cannot. Writing it down once, with every obstacle class in it, is the only way the
answer stops depending on which day it was typed.

⚠ AND THE RESULT IS PINNED TO ONE ROUTING. These coordinates are searched against a
specific routed board. Change the netlist -- even a connector going from four ways to
two -- and the router re-plans, the obstacles move, and the answer is silently wrong.
That happened once already. RE-RUN THIS after any netlist change.

The output is meant to be pasted into a board's BOARD_NOTES as repair_vias /
repair_tracks, which route.py applies AFTER routing (see its repair block). Laid before
routing the same geometry is a constraint that costs more than it buys.
"""
from __future__ import annotations

import json
import math
import os
import re
import sys

MARGIN = 0.15          # on top of each obstacle's own half-width, over the netclass rule
VIA_D, VIA_DRILL = 0.6, 0.3
TRACK_W = 0.25
GRID = 0.1
REACH = 9.0            # how far from the pad to look, mm


def _segments(board_txt):
    out = []
    for b in re.findall(r"\(segment\b(.*?)\n\t\)", board_txt, re.S):
        st = re.search(r"\(start ([-\d.]+) ([-\d.]+)\)", b)
        en = re.search(r"\(end ([-\d.]+) ([-\d.]+)\)", b)
        ly = re.search(r'\(layer "([^"]+)"', b)
        nt = re.search(r'\(net "([^"]*)"', b)
        w = re.search(r"\(width ([-\d.]+)\)", b)
        if st and en and ly:
            out.append(dict(x1=float(st.group(1)), y1=float(st.group(2)),
                            x2=float(en.group(1)), y2=float(en.group(2)),
                            layer=ly.group(1), net=nt.group(1) if nt else "",
                            half=(float(w.group(1)) if w else TRACK_W) / 2.0))
    return out


def _vias(board_txt):
    out = []
    for b in re.findall(r"\(via\b(.*?)\n\t\)", board_txt, re.S):
        at = re.search(r"\(at ([-\d.]+) ([-\d.]+)\)", b)
        sz = re.search(r"\(size ([-\d.]+)\)", b)
        nt = re.search(r'\(net "?([^")\s]*)', b)
        if at:
            out.append(dict(x=float(at.group(1)), y=float(at.group(2)),
                            r=(float(sz.group(1)) if sz else VIA_D) / 2.0,
                            net=nt.group(1) if nt else ""))
    return out


def _pads(board_txt):
    """⚠ THE CLASS EVERY EARLIER VERSION OF THIS SEARCH MISSED. A pad is copper and it
    is also solder mask -- running a track past one at a legal copper distance can still
    bridge the mask, which is what produced two solder_mask_bridge violations against
    the target part's own pad.

    ⚠ AND A PAD IS A CAPSULE, NOT A CIRCLE. The first version took a circle of half the
    pad's LARGER dimension, which for a SOIC pad (~1.5 x 0.6) is a 0.75 mm radius in
    every direction. Adjacent pads are 1.27 mm apart, so those circles overlapped each
    other and sealed the package off: the search reported ZERO reachable sites around
    U2's pad 3 even at zero margin, for a pad the router had reached to within 2.54 mm.
    An obstacle model that is too FAT fails as silently as one that is too thin -- it
    just reports "impossible" instead of "clear".

    Each pad is now its centreline segment along the long axis plus a half-width of the
    short one, rotated by the footprint's angle and its own."""
    out = []
    for f in re.findall(r"\(footprint\b(.*?)\n\t\)", board_txt, re.S):
        at = re.search(r"\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)", f)
        if not at:
            continue
        fx, fy = float(at.group(1)), float(at.group(2))
        # ⚠ THE SIGN OF THIS ROTATION WAS WRONG, AND IT MOVED 456 OF 982 PADS -- by up to
        # 10.65 mm. KiCad's angles are counter-clockwise on screen while its y axis points
        # DOWN, so a footprint's local (px, py) lands at
        #     gx = fx + px cos - (-py) sin ... = fx + px cos(a) + py sin(a)
        #     gy = fy - px sin(a) + py cos(a)
        # i.e. the transform of -a, not of +a. With +a every rotated part's pads came out
        # MIRRORED THROUGH ITS CENTRE: on a symmetric two-pad passive that silently swaps
        # which end carries which net (found on a SHDNZ pull-up, where audit_board then
        # reported fifteen problems that were each a track ending on its OWN pad), and on
        # an asymmetric part it is simply wrong. Checked now against pcbnew, part by part,
        # in scratchpad/padtest.py: 0 pads more than 0.02 mm out.
        rot = -math.radians(float(at.group(3)) if at.group(3) else 0.0)
        # ⚠ MATCH THE WHOLE PAD BLOCK, not just up to (size ...). A pad's net sits on a
        # LATER line, so a pattern that ended at the size never saw it and every pad read
        # as net "" -- which kills the same-net exemption silently: the search would
        # refuse to route past the very pad it is trying to reach, and report no legal
        # path when there are hundreds.
        for p in re.finditer(r'\(pad "([^"]*)"(.*?)\n\t\t\)', f, re.S):
            body = p.group(2)
            at = re.search(r"\(at ([-\d.]+) ([-\d.]+)", body)
            size = re.search(r"\(size ([-\d.]+) ([-\d.]+)\)", body)
            if not (at and size):
                continue
            px, py = float(at.group(1)), float(at.group(2))
            prot = re.search(r"\(at [-\d.]+ [-\d.]+ ([-\d.]+)\)", body)
            gx = fx + px * math.cos(rot) - py * math.sin(rot)
            gy = fy + px * math.sin(rot) + py * math.cos(rot)
            sw, sh = float(size.group(1)), float(size.group(2))
            # ⚠⚠ A PAD'S STORED ANGLE IS ABSOLUTE, NOT RELATIVE TO ITS FOOTPRINT, and
            # combining the two turned every rotated pad's CAPSULE 90 DEGREES OFF. Positions
            # were right -- an earlier fix checked those against pcbnew part by part -- so the
            # error hid in the pad's SHAPE, where nothing was comparing anything.
            # U7 on optical is the proof: footprint at -90, pads at 270, size 0.25 x 0.875, and
            # pcbnew reports each pad's world bbox as 0.875 x 0.250 -- long axis along X. The
            # combined angle (90 - 270 = -180) put the long axis along Y instead, which laid
            # three 0.625-long capsules END TO END on one line at 0.5 mm pitch, so adjacent QFN
            # lands OVERLAPPED each other by 0.125 mm. Pads that cannot physically coexist.
            # What that cost: U7 pad 9 is VDDIO, the ULPI PHY's I/O supply, and it read as
            # having NO legal escape in any direction at any radius -- a constant -0.0010 mm
            # against pad [ULPI_D4] whose uniformity was the clue, since a real obstacle field
            # does not give the same answer for every heading. 667 legal via sites, zero
            # reachable, because the phantom capsules sealed the pin off. "An obstacle model
            # that is too FAT fails as silently as one that is too thin" -- this docstring said
            # so about pad SHAPE two paragraphs up, and was wrong about shape anyway.
            ang = -math.radians(float(prot.group(1))) if prot else rot
            if sw >= sh:                       # long axis along the pad's local x
                half_len, half_w = (sw - sh) / 2.0, sh / 2.0
                ux, uy = math.cos(ang), math.sin(ang)
            else:                              # ...or along its local y
                half_len, half_w = (sh - sw) / 2.0, sw / 2.0
                ux, uy = -math.sin(ang), math.cos(ang)
            nt = re.search(r'\(net "([^"]*)"\)', body)
            # ⚠ AND WHICH COPPER LAYERS IT IS ON, which this parser did not record and
            # every caller therefore treated as "all of them". An SMD pad on F.Cu does
            # not block a track on B.Cu, and a QFP's unused pins are dozens of such pads
            # in a row: measured on optical, U6's no-net pins rejected a legal B.Cu
            # repair at -0.275 mm against copper that is two layers away from it.
            # A model that is too FAT fails as silently as one that is too thin -- the
            # note above says exactly that about pad SHAPE, and the same was true of pad
            # LAYERS one line further down.
            # "*.Cu" is a through-hole pad and really is on every layer; vias are checked
            # against ALL pads regardless (via_ok), because a via does pierce them all.
            lay = re.search(r"\(layers([^)]*)\)", body)
            names = re.findall(r'"?([\w.*]+)"?', lay.group(1)) if lay else []
            cu = {n for n in names if n.endswith(".Cu")}
            out.append(dict(x1=gx - ux * half_len, y1=gy - uy * half_len,
                            x2=gx + ux * half_len, y2=gy + uy * half_len,
                            r=half_w, net=nt.group(1) if nt else "",
                            cu=None if (not cu or "*.Cu" in cu) else cu))
    return out


def _zone_clearance(stem):
    """The ZONE clearance rule, read from the project file rather than assumed.

    ⚠ IT IS NOT THE TRACK RULE, AND ON THIS BOARD IT IS FOUR TIMES LARGER. optical's
    board.design_settings.defaults.zones.min_clearance is 0.5000 mm against a 0.127 mm
    netclass clearance, and DRC reports it in those words ("zone clearance 0.5000 mm").
    Assuming the track rule for pours is what let a dog-leg with 0.1557 mm of MEASURED
    headroom land 0.0225 mm from the ground pour. Read it, so it cannot drift from the board.
    """
    try:
        d = json.load(open(stem + ".kicad_pro", encoding="utf-8"))
        return float(d["board"]["design_settings"]["defaults"]["zones"]["min_clearance"])
    except Exception:
        return 0.5              # optical's value: a miss here is conservative, not silent


def _zones(board_txt):
    """The FILLED copper pours: [{layer, net, pts, bbox}], one entry per filled_polygon.

    ⚠ THE FILLED POLYGON IS THE COPPER, NOT THE ZONE OUTLINE. A zone's outline can cover the
    whole board; what is actually plated is the filled_polygon list, poured around every
    existing track and pad. It is the only shape clearance can honestly be measured against.

    ⚠ AND THIS FUNCTION WAS MISSING, WHICH MADE EVERY NUMBER THIS MODULE PRODUCED AN
    UNDERSTATEMENT. Board parsed segments, vias, pads and edges; the pours were invisible, so
    "0.1557 mm of headroom" meant headroom against everything except the largest copper feature
    on the board. optical carries 35 filled polygons on F.Cu alone, 10 on B.Cu and 1 on In1.Cu.
    """
    out = []
    for z in re.findall(r"\(zone\b(.*?)\n\t\)", board_txt, re.S):
        # ⚠ IT IS (net "GND"), NOT (net_name ...). KiCad 10 writes a zone's net the same way
        # it writes a segment's, and this file contains ZERO occurrences of net_name -- so the
        # first version silently gave every pour an empty net. That reads as "foreign" against
        # every net, which happens to be right for +3V3D (the pours are GND) and would block a
        # repair on GND against ITS OWN copper. A parser that is accidentally right on the case
        # in front of it is the kind that gets trusted and then surprises somebody.
        nt = re.search(r'\(net "([^"]*)"', z)
        net = nt.group(1) if nt else ""
        # a zone may also carry its own clearance; keep the STRICTER of it and the project rule
        zc = re.search(r"\(clearance ([-\d.]+)\)", z)
        z_clear = float(zc.group(1)) if zc else 0.0
        for fp in re.findall(r"\(filled_polygon\b(.*?)\n\t\t\)", z, re.S):
            ly = re.search(r'\(layer "([^"]+)"', fp)
            if not ly:
                continue
            pts = [(float(a), float(b))
                   for a, b in re.findall(r"\(xy ([-\d.]+) ([-\d.]+)\)", fp)]
            if len(pts) < 3:
                continue
            xs = [q[0] for q in pts]
            ys = [q[1] for q in pts]
            out.append(dict(layer=ly.group(1), net=net, pts=pts, clear=z_clear,
                            bbox=(min(xs), max(xs), min(ys), max(ys))))
    return out


def _pt_in_poly(px, py, pts):
    inside = False
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        if (y1 > py) != (y2 > py):
            if px < x1 + (py - y1) * (x2 - x1) / (y2 - y1):
                inside = not inside
    return inside


def _d_seg_poly(ax, ay, bx, by, z, reach):
    """Edge-to-edge distance from segment AB to a filled polygon; 0.0 if AB touches or enters.

    `reach` bounds the bbox reject, so a pour whose nearest edge cannot matter is skipped
    before its (often thousands of) points are walked."""
    x0, x1, y0, y1 = z["bbox"]
    if (min(ax, bx) > x1 + reach or max(ax, bx) < x0 - reach
            or min(ay, by) > y1 + reach or max(ay, by) < y0 - reach):
        return 1e9
    pts = z["pts"]
    if _pt_in_poly(ax, ay, pts) or _pt_in_poly(bx, by, pts):
        return 0.0
    best = 1e9
    n = len(pts)
    for i in range(n):
        cx, cy = pts[i]
        dx, dy = pts[(i + 1) % n]
        d = _d_seg_seg(ax, ay, bx, by, cx, cy, dx, dy)
        if d < best:
            best = d
            if best <= 0.0:
                return 0.0
    return best


def _edges(board_txt):
    """The board outline. Copper too close to it is copper_edge_clearance, three of
    which the fourth inline version of this search produced."""
    out = []
    # ⚠ THE LAYER COMES AFTER THE STROKE BLOCK, so a pattern that stops at the first
    # ")" never sees it and silently returns ZERO edges -- which is exactly how three
    # copper_edge_clearance violations got through. Match the whole item.
    for b in re.findall(r"\(gr_line\b(.*?)\n\t\)", board_txt, re.S):
        if "Edge.Cuts" not in b:
            continue
        st = re.search(r"\(start ([-\d.]+) ([-\d.]+)\)", b)
        en = re.search(r"\(end ([-\d.]+) ([-\d.]+)\)", b)
        if st and en:
            out.append((float(st.group(1)), float(st.group(2)),
                        float(en.group(1)), float(en.group(2))))
    return out


def _d_pt_seg(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / L))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def _seg_hit(ax, ay, bx, by, cx, cy, dx_, dy_):
    """True when the two segments properly cross."""
    def side(ox, oy, px, py, qx, qy):
        return (px - ox) * (qy - oy) - (py - oy) * (qx - ox)
    d1 = side(ax, ay, bx, by, cx, cy)
    d2 = side(ax, ay, bx, by, dx_, dy_)
    d3 = side(cx, cy, dx_, dy_, ax, ay)
    d4 = side(cx, cy, dx_, dy_, bx, by)
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))


def _d_seg_seg(ax, ay, bx, by, cx, cy, dx_, dy_):
    """⚠ THE MINIMUM OF THE FOUR ENDPOINT DISTANCES IS ONLY THE SEGMENT-TO-SEGMENT
    DISTANCE WHEN THE SEGMENTS DO NOT CROSS. Two segments that properly intersect are
    at distance ZERO, but every endpoint can still be far from the other segment -- so
    the endpoint minimum comes back POSITIVE and a crossing reads as clearance.

    Measured on this board: the MID repair line and a +3V3A diagonal intersect at
    x 72.128, and the endpoint minimum reported +0.758 mm of room. The search passed the
    path, the repair was laid, and DRC returned it as a tracks_crossing -- a short
    between two nets. An earlier tracks_crossing in this session was blamed on stale
    coordinates; this is at least as likely to have been the real cause both times.

    A clearance test that cannot see an intersection is not a clearance test."""
    if _seg_hit(ax, ay, bx, by, cx, cy, dx_, dy_):
        return 0.0
    return min(_d_pt_seg(ax, ay, cx, cy, dx_, dy_), _d_pt_seg(bx, by, cx, cy, dx_, dy_),
               _d_pt_seg(cx, cy, ax, ay, bx, by), _d_pt_seg(dx_, dy_, ax, ay, bx, by))


class Board:
    def __init__(self, stem, net):
        txt = open(stem + ".kicad_pcb", encoding="utf-8").read()
        self.net = net
        self.segs = _segments(txt)
        self.vias = _vias(txt)
        self.pads = _pads(txt)
        self.edges = _edges(txt)
        # ⚠ AND THE POURS, which this class did not model at all until 2026-09-30.
        self.zones = _zones(txt)
        self.zone_clear = _zone_clearance(stem)

    def via_ok(self, x, y, r=VIA_D / 2.0):
        for s in self.segs:
            if s["net"] == self.net:
                continue
            if _d_pt_seg(x, y, s["x1"], s["y1"], s["x2"], s["y2"]) < r + s["half"] + MARGIN:
                return False
        for v in self.vias:
            if v["net"] == self.net:
                continue
            if math.hypot(x - v["x"], y - v["y"]) < r + v["r"] + MARGIN:
                return False
        for p in self.pads:                       # pads: capsules, not circles
            if p["net"] == self.net:
                continue
            if _d_pt_seg(x, y, p["x1"], p["y1"], p["x2"], p["y2"]) < r + p["r"] + MARGIN:
                return False
        for e in self.edges:                      # and the outline
            if _d_pt_seg(x, y, *e) < r + MARGIN:
                return False
        return True

    def track_gap(self, p, q, layer, half=TRACK_W / 2.0):
        """Smallest EDGE-TO-EDGE gap this track leaves, and what it is against.

        ⚠ track_ok() answers a SEARCH question -- "is there comfortable room here" -- by
        demanding MARGIN (0.15) on top of every obstacle, which is deliberately more than
        the netclass rule (0.127). That is right when CHOOSING a path and wrong as the
        only verdict on one that has already been measured and DRC-checked: it cannot
        tell "breaks the rule" from "legal but tighter than we like to search for", and
        those deserve different words. This returns the number so the caller can say
        which it is.
        """
        worst, who = 1e9, None
        for s in self.segs:
            if s["layer"] != layer or s["net"] == self.net:
                continue
            d = _d_seg_seg(*p, *q, s["x1"], s["y1"], s["x2"], s["y2"]) - half - s["half"]
            if d < worst:
                worst, who = d, "track [%s]" % s["net"]
        for v in self.vias:
            if v["net"] == self.net:
                continue
            d = _d_pt_seg(v["x"], v["y"], *p, *q) - half - v["r"]
            if d < worst:
                worst, who = d, "via [%s]" % v["net"]
        for pd in self.pads:
            if pd["net"] == self.net:
                continue
            if pd.get("cu") is not None and layer not in pd["cu"]:
                continue                      # see _pads: an F.Cu pad is not a B.Cu obstacle
            d = _d_seg_seg(*p, *q, pd["x1"], pd["y1"], pd["x2"], pd["y2"]) - half - pd["r"]
            if d < worst:
                worst, who = d, "pad [%s]" % (pd["net"] or "no net")
        for e in self.edges:
            d = _d_seg_seg(*p, *q, *e) - half
            if d < worst:
                worst, who = d, "board edge"
        return worst, who

    def zone_gap(self, p, q, layer, half=TRACK_W / 2.0):
        """Edge-to-edge gap from this track to the nearest FOREIGN copper pour, and its net.

        ⚠ KEPT SEPARATE FROM track_gap ON PURPOSE. The two answer to DIFFERENT RULES -- the
        netclass clearance (0.127 on optical) for tracks, pads, vias and the outline, and the
        zone clearance (0.5000) for pours. Folding pours into track_gap would return one "worst
        gap" that the caller then compares against one rule, which is exactly the mistake that
        approved a dog-leg sitting 0.0225 mm from the ground pour: the number was true and the
        rule it was judged against was the wrong one.
        """
        worst, who = 1e9, None
        reach = half + self.zone_clear + 1.0
        for z in self.zones:
            if z["layer"] != layer or z["net"] == self.net:
                continue
            d = _d_seg_poly(p[0], p[1], q[0], q[1], z, reach) - half
            if d < worst:
                worst, who = d, "zone [%s] on %s" % (z["net"] or "?", z["layer"])
        return worst, who

    def zone_ok(self, p, q, layer, half=TRACK_W / 2.0):
        g, _ = self.zone_gap(p, q, layer, half)
        return g >= self.zone_clear

    def track_ok(self, p, q, layer, half=TRACK_W / 2.0, pours=False):
        """Is there comfortable room for this track? `pours` decides whether the EXISTING
        copper pours count as obstacles, and the default is NO. That is not laziness:

        ⚠ A POST-ROUTE REPAIR IS FOLLOWED BY A ZONE REFILL, so the pour that is on the board
        while we search is NOT the pour the repair will live in -- repair_planes.py refills,
        and the fill retreats around whatever copper it finds. Treating the old pour as an
        obstacle rejects paths that work: it declared optical's +3V3D dog-leg at U6.36
        impossible ("0 legal dog-legs") when laying that exact path and refilling gives DRC
        violations IDENTICAL to the baseline and zero clearance. I had this switched on by
        default for one tick and it hid a repair that was already proven good.

        Pass pours=True to ask the other question -- "is this legal against the board AS IT
        STANDS" -- which is what an auditor wants, and what audit_board asks through zone_gap.
        """
        if pours and not self.zone_ok(p, q, layer, half):
            return False
        for s in self.segs:
            if s["layer"] != layer or s["net"] == self.net:
                continue
            if _d_seg_seg(*p, *q, s["x1"], s["y1"], s["x2"], s["y2"]) < half + s["half"] + MARGIN:
                return False
        for v in self.vias:
            if v["net"] == self.net:
                continue
            if _d_pt_seg(v["x"], v["y"], *p, *q) < half + v["r"] + MARGIN:
                return False
        for pd in self.pads:
            if pd["net"] == self.net:
                continue
            if pd.get("cu") is not None and layer not in pd["cu"]:
                continue                      # an F.Cu pad does not block a B.Cu track
            if _d_seg_seg(*p, *q, pd["x1"], pd["y1"], pd["x2"], pd["y2"]) < half + pd["r"] + MARGIN:
                return False
        for e in self.edges:
            if _d_seg_seg(*p, *q, *e) < half + MARGIN:
                return False
        return True


def search(stem, net, pad_xy, top=5):
    """Return (board, direct_paths, via_paths).

    ⚠ TWO SHAPES OF REPAIR, AND AN EARLIER VERSION ONLY KNEW ONE. A break is often a
    gap on the SAME layer the pad is on -- MID's was 2.54 mm straight up F.Cu -- and
    needs no via at all. That version modelled only via-plus-spur and reported "0 legal
    paths" for a net whose repair is one straight track, which reads as impossible when
    it is actually trivial.

    ⚠ AND IT TARGETED B.Cu ONLY. MID carries 132 segments on F.Cu, 52 on In2.Cu and 3
    on B.Cu, so hunting B.Cu alone aimed at the 3 and ignored the 52. In2.Cu is the one
    layer with no ground pour on this board, i.e. the emptiest place to land. Target
    every layer the net actually occupies, and let the distance decide.
    """
    b = Board(stem, net)
    own = [s for s in b.segs if s["net"] == net]
    if not own:
        raise SystemExit("no copper on %s to reach" % net)

    def points_on(layer):
        out = []
        for s in own:
            if s["layer"] != layer:
                continue
            for k in (0.0, 0.25, 0.5, 0.75, 1.0):
                out.append((s["x1"] + (s["x2"] - s["x1"]) * k,
                            s["y1"] + (s["y2"] - s["y1"]) * k))
        return out

    # shape 1: a straight track on the pad's own layer, no via
    direct = []
    for (tx, ty) in points_on("F.Cu"):
        if b.track_ok(pad_xy, (tx, ty), "F.Cu"):
            direct.append((round(math.hypot(tx - pad_xy[0], ty - pad_xy[1]), 3),
                           round(tx, 3), round(ty, 3)))
    direct.sort()

    # shape 2: via to another layer, then a spur to the net's copper there
    layers = [L for L in ("In2.Cu", "B.Cu") if any(s["layer"] == L for s in own)]
    found = []
    n = int(REACH / GRID)
    for i in range(-n, n + 1):
        for j in range(-n, n + 1):
            vx, vy = round(pad_xy[0] + i * GRID, 3), round(pad_xy[1] + j * GRID, 3)
            if not b.via_ok(vx, vy):
                continue
            if not b.track_ok(pad_xy, (vx, vy), "F.Cu"):
                continue
            for L in layers:
                hit = None
                for (tx, ty) in points_on(L):
                    if b.track_ok((vx, vy), (tx, ty), L):
                        hit = (tx, ty)
                        break
                if hit:
                    found.append((round(math.hypot(vx - pad_xy[0], vy - pad_xy[1])
                                        + math.hypot(hit[0] - vx, hit[1] - vy), 3),
                                  vx, vy, round(hit[0], 3), round(hit[1], 3), L))
                    break
    found.sort()
    return b, direct, found


def main(argv):
    if len(argv) < 5:
        raise SystemExit(__doc__.strip().splitlines()[2].strip())
    stem, net, ref, pad = argv[1], argv[2], argv[3], argv[4]
    d = json.load(open(stem + ".finish.drc.json", encoding="utf-8"))
    xy = None
    for v in d.get("unconnected_items", []):
        for it in v["items"]:
            if ("Pad %s" % pad) in it["description"] and ("of %s" % ref) in it["description"]:
                xy = (it["pos"]["x"], it["pos"]["y"])
    if xy is None:
        raise SystemExit("pad %s of %s is not reported unconnected -- nothing to repair"
                         % (pad, ref))
    b, direct, found = search(stem, net, xy)
    print("obstacles: %d segments, %d vias, %d pads, %d edge lines"
          % (len(b.segs), len(b.vias), len(b.pads), len(b.edges)))
    print("target pad %s.%s at (%.4f, %.4f)" % (ref, pad, xy[0], xy[1]))
    print("same-layer paths (no via): %d      via paths: %d" % (len(direct), len(found)))
    for t, tx, ty in direct[:3]:
        print("   F.Cu straight to (%.2f, %.2f)   %.2f mm" % (tx, ty, t))
    for t, vx, vy, tx, ty, L in found[:3]:
        print("   via(%.2f, %.2f) -> %s (%.2f, %.2f)   total %.2f mm" % (vx, vy, L, tx, ty, t))
    if direct:
        t, tx, ty = direct[0]
        print()
        print("    # one track, no via -- the break is on the pad's own layer")
        print('    "repair_tracks": [("%s", "F.Cu", %.2f, [(%.3f, %.3f), (%.3f, %.3f)])],'
              % (net, TRACK_W, xy[0] - 100, 100 - xy[1], tx - 100, 100 - ty))
    elif found:
        t, vx, vy, tx, ty, L = found[0]
        print()
        print('    "repair_vias": [("%s", %.3f, %.3f)],' % (net, vx - 100, 100 - vy))
        print('    "repair_tracks": [("%s", "F.Cu", %.2f, [(%.3f, %.3f), (%.3f, %.3f)]),'
              % (net, TRACK_W, xy[0] - 100, 100 - xy[1], vx - 100, 100 - vy))
        print('                      ("%s", "%s", %.2f, [(%.3f, %.3f), (%.3f, %.3f)])],'
              % (net, L, TRACK_W, vx - 100, 100 - vy, tx - 100, 100 - ty))
    return 0 if (direct or found) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
