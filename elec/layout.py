"""Netlist + placement -> a .kicad_pcb with every part already where it belongs.

    "C:/Program Files/KiCad/10.0/bin/python.exe" elec/layout.py elec/out/can_tee

RUNS UNDER KICAD'S OWN PYTHON, not the project's 3.12: it needs `pcbnew`, which
ships only inside the KiCad install. That is also why it talks to the rest of
the project through a JSON file rather than importing anything -- KiCad's Python
has no cadquery, so it can never import src/. The board module (e.g.
elec/can_tee.py) runs under 3.12, reads the mechanical model, and writes both
the netlist and `<board>.board.json`; this reads the pair and writes the board.

WHY NOT kinet2pcb, the obvious existing tool: it hardcodes a list of KiCad
install paths that stops at 9.0, so it cannot find a KiCad 10 installation at
all, and it places parts by a generic auto-arranger. We need the opposite of an
auto-arranger -- the whole point is that these positions come from the
instrument's geometry.

⚠ EXPIRY: `pcbnew` is the SWIG binding, deprecated since KiCad 9 and slated for
removal in KiCad 11. When that lands, this one file is what has to move to the
IPC API (`kicad-python`); nothing else in elec/ imports pcbnew.
"""
from __future__ import annotations

import json
import os
import sys

import pcbnew

FP_DIRS = [
    os.environ.get("KICAD10_FOOTPRINT_DIR")
    or r"C:\Program Files\KiCad\10.0\share\kicad\footprints",
]


# ── a very small S-expression reader (the netlist is all we parse) ───────────
def _sexp(text: str):
    tok, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c in "()":
            tok.append(c); i += 1
        elif c == '"':
            j = i + 1
            while text[j] != '"' or text[j - 1] == "\\":
                j += 1
            tok.append(text[i + 1:j]); i = j + 1
        elif c.isspace():
            i += 1
        else:
            j = i
            while j < n and not text[j].isspace() and text[j] not in '()"':
                j += 1
            tok.append(text[i:j]); i = j

    def build(k):
        out = []
        while tok[k] != ")":
            if tok[k] == "(":
                sub, k = build(k + 1)
                out.append(sub)
            else:
                out.append(tok[k]); k += 1
        return out, k + 1

    assert tok[0] == "("
    return build(1)[0]


def _find(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


def _val(node, key, default=None):
    hit = _find(node, key)
    return hit[0][1] if hit and len(hit[0]) > 1 else default


def read_netlist(path):
    """-> ({ref: (footprint, value)}, {net_name: [(ref, pad), ...]})"""
    root = _sexp(open(path, encoding="utf-8").read())
    comps = {}
    for block in _find(root, "components"):
        for c in _find(block, "comp"):
            comps[_val(c, "ref")] = (_val(c, "footprint"), _val(c, "value", ""))
    nets = {}
    for block in _find(root, "nets"):
        for nt in _find(block, "net"):
            nets[_val(nt, "name")] = [(_val(nd, "ref"), _val(nd, "pin"))
                                      for nd in _find(nt, "node")]
    return comps, nets


# ── board frame ──────────────────────────────────────────────────────────────
# Board-local millimetres have the ORIGIN AT THE BOARD CENTRE with +Y up, which
# is how src/ describes everything. KiCad's page has +Y DOWN and wants the board
# somewhere sensible on the sheet, so every placement goes through here and the
# sign flip lives in exactly one place.
SHEET_ORIGIN = (100.0, 100.0)


def _to_board(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(SHEET_ORIGIN[0] + x),
                           pcbnew.FromMM(SHEET_ORIGIN[1] - y))


def _load_footprint(spec):
    lib, name = spec.split(":", 1)
    for d in FP_DIRS:
        path = os.path.join(d, lib + ".pretty")
        if os.path.isdir(path):
            fp = pcbnew.FootprintLoad(path, name)
            if fp:
                return fp
    raise SystemExit("footprint not found: %s (looked in %s)" % (spec, FP_DIRS))


def _place_ref(fp, target):
    """Put the reference designator at an absolute board position, upright and
    small. Left where the footprint puts it, a designator sits over the part --
    fine on a roomy board, but here the connector bodies fill most of the copper
    and the text lands on a neighbour's silk or off the edge. The free strips
    between the parts are the only place it can be READ once the board is
    populated, so the board module names them."""
    ref = fp.Reference()
    ref.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(0.8), pcbnew.FromMM(0.8)))
    ref.SetTextThickness(pcbnew.FromMM(0.15))
    ref.SetPosition(target)
    ref.SetTextAngleDegrees(0.0)      # upright regardless of how the part turned
    ref.SetKeepUpright(True)


def _anchor_on_courtyard(fp, target):
    """Move `fp` so the CENTRE OF ITS COURTYARD sits on `target`.

    ⚠ THE OPTICAL BOARD PLACES BY COURTYARD, NOT BY PAD CENTROID, and it is the only
    one that does. Its placements come from src/optical_pickup.py, where a part's
    coordinate is the centre of the box that has to clear its neighbours, the cover and
    the strings -- a mechanical model reasons about envelopes, not about where the
    solder lands average out. For a two-pad passive the two agree; for a USB-C, a JST
    side-entry header, a SOT-223 or a SOT-23-5 they do not, because the pads sit
    asymmetrically in the body.

    Handing those coordinates to the pad-centroid anchor put four parts into their
    neighbours and hung J1's land off the board's -Y edge -- a shift of a couple of
    millimetres that is invisible in the model and fatal on the board. Rather than
    correcting the CAD (whose convention is right for what the CAD is for) or carrying
    a per-footprint offset table (which would be a second copy of the footprint library
    to keep true), the board says which convention it means and this runs here, where
    pcbnew can measure the footprint directly."""
    bb = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
    c = bb.GetCenter()
    pos = fp.GetPosition()
    fp.SetPosition(pcbnew.VECTOR2I(pos.x + (target.x - c.x), pos.y + (target.y - c.y)))


def _anchor_on_pads(fp, target):
    """Move `fp` so the CENTROID OF ITS PADS sits on `target`.

    A KiCad footprint's origin is wherever its author put it, and for connectors
    that is almost always PAD 1 -- the JST B4B-XH-A's courtyard runs x -3.00 to
    +10.49 about its origin. src/ places these parts by their PIN ROW instead
    (cadkit's jst_xh_header is centred on the row, which is what a mechanical
    drawing and a mating plug both care about), so handing the model's
    coordinate straight to SetPosition puts the connector 3.75 mm off and the
    error is invisible until something collides.

    Anchoring on the pad centroid makes the two agree for every part we place,
    without a per-footprint offset table to get wrong: it is the origin for
    two-pad passives, and the row centre for a symmetric header. Rotation is
    already applied when this runs, so the correction needs no trig."""
    pads = list(fp.Pads())
    cx = sum(p.GetPosition().x for p in pads) // len(pads)
    cy = sum(p.GetPosition().y for p in pads) // len(pads)
    pos = fp.GetPosition()
    fp.SetPosition(pcbnew.VECTOR2I(pos.x + (target.x - cx), pos.y + (target.y - cy)))


# counters for why a differential-pair hop could not be laid -- the failure message
# quotes them, because "no clear path" on its own sends you looking in the wrong place:
# 'escape' is a placement problem, 'run' an obstacle problem, 'edge' a board-outline one.
_DBG = {}


def _offset_poly(pts, ds, math):
    """`pts` offset by the signed per-vertex distances `ds`, corners mitred.

    This is the whole trick. Offsetting a polyline preserves parallelism through the
    bends, so two rails taken as +d and -d of one line keep their gap and cannot cross,
    however the line turns -- the pair property becomes a consequence of the
    construction instead of something checked for afterwards.

    ⚠ THE OFFSET VARIES PER VERTEX, which is not decoration. At a package the two rails
    have to start ON their own pads, and those are as far apart as the part's pitch
    makes them -- 1.9 mm across a SOT-563, 0.5 mm across a USB-C. Run out at the pair's
    own pitch instead and the rails leave the pads diagonally, straight into the lane
    of the pad BETWEEN them; on this board that missed the ESD array's ground pin by
    0.012 mm and failed every hop. Starting at the pad separation and tapering to the
    pair pitch over the escape is what a person draws, and it is the same polyline
    trick with one number per vertex rather than one for the line.
    """
    if not isinstance(ds, (list, tuple)):
        ds = [ds] * len(pts)
    segs = []
    for i, (p, q) in enumerate(zip(pts, pts[1:])):
        ux, uy = q[0] - p[0], q[1] - p[1]
        L = math.hypot(ux, uy)
        if L == 0:
            continue
        ux, uy = ux / L, uy / L
        nx, ny = -uy, ux
        segs.append(((p[0] + ds[i] * nx, p[1] + ds[i] * ny),
                     (q[0] + ds[i + 1] * nx, q[1] + ds[i + 1] * ny)))
    if not segs:
        return list(pts)
    out = [segs[0][0]]
    for s1, s2 in zip(segs, segs[1:]):
        (x1, y1), (x2, y2) = s1
        (x3, y3), (x4, y4) = s2
        den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(den) < 1e-9:
            out.append(s1[1])
            continue
        e = x1 * y2 - y1 * x2
        f = x3 * y4 - y3 * x4
        out.append(((e * (x3 - x4) - (x1 - x2) * f) / den,
                    (e * (y3 - y4) - (y1 - y2) * f) / den))
    out.append(segs[-1][1])
    return out


def _centrelines(p0, p1, detour_mm=6.0, step_mm=0.5):
    """Candidate centrelines from p0 to p1, simplest first.

    Straight, then the two right-angle elbows, then Z routes with the crossbar swept
    across and BEYOND the two endpoints.

    ⚠ THE OVERSHOOT IS THE POINT OF THE Z FAMILY. One corner can only ever route inside
    the rectangle the two endpoints span, and the obstacle that stopped this pair -- a
    USB-C's own shell tab, 1 mm of through-plated copper sitting between the socket and
    the part that feeds it -- is inside that rectangle on every layer. Getting past it
    means going AROUND, which means a crossbar placed outside the span, which no
    one-corner shape can express.
    """
    out = [[p0, p1]]
    if p0[0] != p1[0] and p0[1] != p1[1]:
        out.append([p0, (p1[0], p0[1]), p1])
        out.append([p0, (p0[0], p1[1]), p1])
    step = pcbnew.FromMM(step_mm)
    reach = pcbnew.FromMM(detour_mm)
    for axis in (0, 1):
        lo, hi = sorted((p0[axis], p1[axis]))
        cs = [lo + k * step for k in range(int((hi - lo) // step) + 1)]
        # inside the span first, then working outwards on both sides
        for k in range(1, int(reach // step) + 1):
            cs += [lo - k * step, hi + k * step]
        for c in cs:
            if axis == 0:
                out.append([p0, (c, p0[1]), (c, p1[1]), p1])
            else:
                out.append([p0, (p0[0], c), (p1[0], c), p1])
    return out


def _diff_pairs(board, specs, outline=None, inner=None, clr=0.14):
    """Route declared differential pairs AS PAIRS, before the autorouter sees them.

    ⚠ FREEROUTING HAS NO CONCEPT OF A DIFFERENTIAL PAIR. It routes DP and DM as two
    independent nets that happen to share endpoints, and on the optical board that
    produced 39.6 mm of DP against 32.0 mm of DM over a 22 mm path -- two traces
    taking visibly different routes. The timing skew that implies is survivable (46 ps
    against a 2,080 ps bit); what is NOT survivable is that two traces on different
    paths are not COUPLED, so the 90 ohm differential impedance the stack-up was
    designed around stops describing the interconnect at all. No budget number fixes
    that, because the defect is geometric rather than numeric: the pair has to be
    routed as a pair or it is not a pair.

    So it is routed here, deterministically, and excluded from the router's DSN.

    ⚠ EVERYTHING IS BUILT BY OFFSETTING ONE CENTRELINE, and that is the design of this
    routine rather than an implementation detail. It was arrived at the long way round:
    the first version searched a via position for each pad and then joined via to via,
    and every bug it had was one bug in different clothes. Two independently placed
    endpoints share no notion of which rail is on which side, so the rails crossed at a
    package; then crossed in the middle of a run; then -- the one that finally made the
    right shape obvious -- both turned their corner at the same coordinate and ran
    along on top of each other for three millimetres, because an elbow drawn through
    two endpoints is the SAME elbow for both of them.

    A centreline cannot do any of that, and which rail carries D+ reduces to a single
    choice of sign for the whole run, made once by trying both and keeping the shorter
    stubs.

    THE PATH PER HOP: pad-pair midpoint -> escape point -> optional elbow -> escape
    point -> pad-pair midpoint. The escape points stand the vias off far enough to
    clear their neighbours; the run between them drops to `inner` when the component
    layer is blocked, which it nearly always is, because both ends of a hop terminate
    inside a fine-pitch pad field. Short stubs on the component layer join each pad to
    its own rail end.

    If a hop cannot be laid clear, NOTHING is emitted for that pair and it is reported.
    A half-routed pair is worse than an unrouted one: the router would finish it, and
    the finished half would look deliberate.
    """
    import math
    pads = [(pad, fp) for fp in board.GetFootprints() for pad in fp.Pads()]
    boxes = [(q.GetBoundingBox(), q.GetNetname(),
              "%s.%s" % (f.GetReference(), q.GetNumber())) for q, f in pads]
    boxes += [(t.GetBoundingBox(), t.GetNetname(), "track") for t in board.GetTracks()]
    # ⚠ AN INNER-LAYER RUN HAS A DIFFERENT OBSTACLE SET, and using the surface one was
    # why the re-planned board still reported the hop blocked. An SMD pad lives on F.Cu
    # and is no obstacle at all to a trace on In2.Cu; what pierces every layer is
    # THROUGH-HOLE copper -- vias, and the occasional THT pad. Checking a 7 mm inner run
    # against 566 surface pads finds a collision every time, and the message reads as
    # "the board is too dense" when the board is nothing of the kind.
    thru = [(t.GetBoundingBox(), t.GetNetname(), "via") for t in board.GetTracks()
            if t.GetClass() == "PCB_VIA"]
    thru += [(q.GetBoundingBox(), q.GetNetname(),
              "%s.%s" % (f.GetReference(), q.GetNumber())) for q, f in pads
             if q.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)]
    by_ref = {}
    for pad, fp in pads:
        by_ref.setdefault(fp.GetReference(), []).append(pad)

    # ⚠ THE OBSTACLES ARE BUCKETED INTO A GRID, and that is not premature optimisation.
    # A clearance test that walks all 600 pads costs nothing once and everything when
    # the search has to try thousands of candidate paths -- and it does have to, because
    # getting a pair around a connector's shell tabs means considering routes with two
    # corners, not just the three one-corner shapes a cheap test can afford. The honest
    # version of "the board is too dense to route this" is usually "the search gave up
    # early", and a fast test is what lets it not.
    CELL = pcbnew.FromMM(2.0)

    def _grid(items):
        g = {}
        for bb, onet, _lbl in items:
            for cx in range(bb.GetLeft() // CELL, bb.GetRight() // CELL + 1):
                for cy in range(bb.GetTop() // CELL, bb.GetBottom() // CELL + 1):
                    g.setdefault((cx, cy), []).append((bb, onet, _lbl))
        return g

    def clear(x, y, nets, margin, grid):
        x, y = int(x), int(y)
        seen = set()
        for cx in range((x - margin) // CELL, (x + margin) // CELL + 1):
            for cy in range((y - margin) // CELL, (y + margin) // CELL + 1):
                for item in grid.get((cx, cy), ()):
                    if id(item) in seen:
                        continue
                    seen.add(id(item))
                    bb, onet, lbl = item
                    if onet in nets:
                        continue
                    dx = max(bb.GetLeft() - x, 0, x - bb.GetRight())
                    dy = max(bb.GetTop() - y, 0, y - bb.GetBottom())
                    if math.hypot(dx, dy) < margin:
                        return False
        return True

    def seg_clear(p0, p1, nets, margin, grid):
        L = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        if L == 0:
            return True
        n = max(4, int(pcbnew.ToMM(L) / 0.15) + 1)
        return all(clear(p0[0] + (p1[0] - p0[0]) * t / n,
                         p0[1] + (p1[1] - p0[1]) * t / n, nets, margin, grid)
                   for t in range(n + 1))

    def on_board(x, y, reach_mm):
        """Is copper of half-width `reach_mm` at (x, y) actually ON the board?

        ⚠ THE ESCAPE SEARCH USED TO ASSUME ANY DIRECTION AWAY FROM THE PACKAGE WAS
        BOARD, and at an EDGE CONNECTOR that is false in the one direction it most
        wants to go: the socket sits against the edge because the plug has to reach the
        outside world, so there is half a millimetre of board past its pad row and
        nothing else. The reach has to include the copper's own half-width -- a via
        CENTRE 0.5 mm from the edge has copper 0.2 mm from it, which the fab cares
        about and a bare point-in-polygon test waves through.
        """
        if outline is None:
            return True
        return _inside(outline, int(x), int(y), pcbnew.FromMM(reach_mm + 0.5))

    def rails_for(centre, ds, vi, a0, b0, a1, b1, na, nb, margin, width,
                  surf_layer, run_layer, via_margin, grid):
        """Offset `centre` into two rails and return the copper to emit, or None.

        `centre` runs pad-midpoint -> neck -> escape -> ... -> escape -> neck ->
        pad-midpoint, and `ds` carries one half-pitch per vertex, so the ESCAPE IS PART
        OF THE LINE rather than a stub bolted on afterwards. That is what rotates the
        pair correctly: coming off a connector the two rails are separated ALONG the pad
        row, and heading away down the board they have to be separated ACROSS the run.
        Offsetting a polyline does that turn for free at the corner.

        ⚠ THE NECK IS WHY `ds` VARIES. The pair runs at a via pitch wide enough for
        0.6 mm vias -- 0.74 mm centre to centre -- and a USB-C's pads are on 0.5 mm
        pitch. Arriving at that row still fanned out leaves each rail 0.23 mm from the
        NEIGHBOURING pad, and that was the last thing standing between this board and a
        routed pair. The line therefore necks back to the part's own pad separation
        before it reaches the part and opens out again once clear: a taper, which is
        what a person draws and what a polyline offset expresses in one number per
        vertex.

        ⚠ THE SIGN IS CHOSEN ONCE FOR THE WHOLE RUN. Both options are built and the
        one with the shorter ends wins -- the same thing as "D+ leaves on the side its
        pad is already on". Because both rails are offsets of one line, that single
        decision holds for every segment and every corner of the hop.
        """
        opts = []
        for sa in (+1, -1):
            r = {na: _offset_poly(centre, [sa * d for d in ds], math),
                 nb: _offset_poly(centre, [-sa * d for d in ds], math)}
            pd = {na: (a0, a1), nb: (b0, b1)}
            cost = sum(math.hypot(pd[n][i].GetPosition().x - r[n][j][0],
                                  pd[n][i].GetPosition().y - r[n][j][1])
                       for n in (na, nb) for i, j in ((0, 0), (1, -1)))
            opts.append((cost, r, pd))
        # ⚠ REJECT A CENTRELINE THAT DOUBLES BACK ON ITSELF. Mitring a corner means
        # intersecting the two offset lines, and when the two segments are nearly
        # anti-parallel that intersection runs away to infinity -- the rails fly apart
        # in opposite directions and what lands on the board is not a pair but two long
        # traces to nowhere. It reached DRC looking like a pair whose halves were 10 mm
        # apart. A corner is only a corner if it turns.
        limit = 3.0 * max(ds)
        opts = [o for o in opts
                if all(math.hypot(v[0] - c[0], v[1] - c[1]) < limit
                       for rr in (o[1][na], o[1][nb])
                       for v, c in zip(rr, centre))]
        if not opts:
            return None
        opts.sort(key=lambda o: o[0])
        nets = {na, nb}
        for _, r, pd in opts:
            out, ok = [], True
            for n in (na, nb):
                p_start, p_end = pd[n]
                own = {n}
                # the rail ENDS on its own pad; the neck brings it within microns and
                # this closes the gap exactly.
                rail = list(r[n])
                rail[0] = (p_start.GetPosition().x, p_start.GetPosition().y)
                rail[-1] = (p_end.GetPosition().x, p_end.GetPosition().y)
                if vi is None:
                    for q0, q1 in zip(rail, rail[1:]):
                        if q0 != q1 and not seg_clear(q0, q1, nets, margin, grid):
                            ok = False
                            break
                    if not ok:
                        break
                    for q0, q1 in zip(rail, rail[1:]):
                        if q0 != q1:
                            out.append(("TRK", p_start, q0, q1, surf_layer))
                    continue
                i0, i1 = vi
                # ⚠ THE SURFACE ENDS ARE CHECKED AGAINST THE PARTNER'S PADS, not
                # against "the pair". Excluding both nets is right for the coupled RUN --
                # the rails sit a fixed gap apart on purpose and would otherwise reject
                # each other -- and wrong at a fan-out: D+'s escape ran straight over
                # D-'s pad at the connector, and DRC called it the short it was.
                surf = (list(zip(rail[:i0], rail[1:i0 + 1]))
                        + list(zip(rail[i1:-1], rail[i1 + 1:])))
                run = list(zip(rail[i0:i1], rail[i0 + 1:i1 + 1]))
                for q0, q1 in surf:
                    if q0 != q1 and not seg_clear(q0, q1, own, margin, g_all):
                        ok = False
                        _DBG['escape'] = _DBG.get('escape', 0) + 1
                        break
                if not ok:
                    break
                for v in (rail[i0], rail[i1]):
                    if not clear(v[0], v[1], own, via_margin, g_all):
                        ok = False
                        _DBG['via'] = _DBG.get('via', 0) + 1
                    elif not on_board(v[0], v[1], 0.3):
                        ok = False
                        _DBG['edge'] = _DBG.get('edge', 0) + 1
                    if not ok:
                        break
                if not ok:
                    break
                for q0, q1 in run:
                    if q0 != q1 and not seg_clear(q0, q1, nets, margin, grid):
                        ok = False
                        _DBG['run'] = _DBG.get('run', 0) + 1
                        break
                if not ok:
                    break
                for q0, q1 in surf:
                    if q0 != q1:
                        out.append(("TRK", p_start, q0, q1, surf_layer))
                for q0, q1 in run:
                    if q0 != q1:
                        out.append(("TRK", p_start, q0, q1, run_layer))
                out.append(("VIA", p_start, rail[i0], None, None))
                out.append(("VIA", p_end, rail[i1], None, None))
            if ok:
                return out
        return None

    g_all, g_thru = _grid(boxes), _grid(thru)

    done = []
    for spec in specs:
        na, nb = spec["nets"]
        chain = spec["chain"]
        gap = spec.get("gap", 0.2)
        width = spec.get("width", 0.2)
        off = pcbnew.FromMM((gap + width) / 2.0)
        # ⚠ THE VIA PITCH IS WIDER THAN THE TRACK PITCH. 0.2 mm traces on a 0.2 mm gap
        # sit 0.4 apart centre to centre, which 0.6 mm vias cannot use -- at the track
        # pitch they overlap outright. The inner run is therefore laid at the WIDER
        # pitch throughout, which keeps the geometry a pair (both rails identical,
        # mirror imaged, constant gap) at the cost of weaker coupling than the surface
        # stubs. A constant impedance you have not calculated beats a varying one you
        # have -- and it is not calculated: the actual differential impedance needs the
        # stack-up's dielectric heights, which JLCPCB fixes and nothing here reads.
        voff = max(off, pcbnew.FromMM((0.6 + clr) / 2.0))
        margin = pcbnew.FromMM(width / 2.0 + clr)
        via_margin = pcbnew.FromMM(0.3 + clr)

        # ── the pads to visit: an IN pair and an OUT pair for every part ──
        # ⚠ A PART IN THE MIDDLE OF THE CHAIN NEEDS DIFFERENT PADS ON ITS TWO SIDES, and
        # getting that wrong is what kept the last hop unroutable through three rewrites
        # of the escape search. The ESD array is a SERIES part: the PHY feeds one face
        # and the connector is fed from the other, and the USBLC6 exposes each net on
        # both (D+ on pins 1 and 6, D- on 3 and 4) precisely so that it can be dropped
        # into the run that way. Using one pad pair for both hops means the outgoing hop
        # has to escape backwards across the package it just arrived at -- which is not
        # a hard routing problem, it is an impossible one, and it reported as "no clear
        # path" rather than as the placement mistake it was.
        #
        # So each part gets an IN pair, chosen nearest where the run came from, and an
        # OUT pair, chosen nearest where it is going, and they are only the same pads
        # when the part has nothing else to offer.
        fps = []
        for ref in chain:
            fpo = next((f for f in board.GetFootprints()
                        if f.GetReference() == ref), None)
            cand = {n: [q for q in by_ref.get(ref, []) if q.GetNetname() == n]
                    for n in (na, nb)}
            if fpo is None or not cand[na] or not cand[nb]:
                fps = None
                break
            fps.append((fpo, cand))
        if fps is None:
            done.append((na, "could not find both nets on every part of the chain"))
            continue

        def best_pair(cand, targets, avoid=()):
            """The (D+, D-) pad pair closest to `targets`, preferring pads not in
            `avoid` -- minimising the TOTAL of the two distances, which picks the
            uncrossed combination for free: crossing is always longer than not."""
            best = None
            for qa in cand[na]:
                for qb in cand[nb]:
                    if qa.GetPosition() == qb.GetPosition():
                        continue
                    cost = sum((q.GetPosition() - t).EuclideanNorm()
                               for q, t in zip((qa, qb), targets))
                    cost += sum(pcbnew.FromMM(25.0) for q in (qa, qb) if q in avoid)
                    if best is None or cost < best[0]:
                        best = (cost, qa, qb)
            return best[1], best[2]

        stops = []
        for k, (fpo, cand) in enumerate(fps):
            if k == 0:
                nxt = fps[1][0].GetCourtyard(pcbnew.F_CrtYd).BBox().GetCenter()
                a, b_ = best_pair(cand, (nxt, nxt))
                stops.append({"fp": fpo, "in": (a, b_), "out": (a, b_)})
                continue
            pa0, pb0 = (q.GetPosition() for q in stops[-1]["out"])
            a, b_ = best_pair(cand, (pa0, pb0))
            if k == len(fps) - 1:
                stops.append({"fp": fpo, "in": (a, b_), "out": (a, b_)})
                continue
            nxt = fps[k + 1][0].GetCourtyard(pcbnew.F_CrtYd).BBox().GetCenter()
            oa, ob = best_pair(cand, (nxt, nxt), avoid=(a, b_))
            stops.append({"fp": fpo, "in": (a, b_), "out": (oa, ob)})

        pending, laid, why = [], 0, None
        for s0, s1 in zip(stops, stops[1:]):
            (a0, b0), fp0 = s0["out"], s0["fp"]
            (a1, b1), fp1 = s1["in"], s1["fp"]
            m0 = ((a0.GetPosition().x + b0.GetPosition().x) / 2.0,
                  (a0.GetPosition().y + b0.GetPosition().y) / 2.0)
            m1 = ((a1.GetPosition().x + b1.GetPosition().x) / 2.0,
                  (a1.GetPosition().y + b1.GetPosition().y) / 2.0)

            hs0 = math.hypot(a0.GetPosition().x - b0.GetPosition().x,
                             a0.GetPosition().y - b0.GetPosition().y) / 2.0
            hs1 = math.hypot(a1.GetPosition().x - b1.GetPosition().x,
                             a1.GetPosition().y - b1.GetPosition().y) / 2.0
            hop = None
            # 1. the surface try: no vias at all, if the component layer is open
            for sh in _centrelines(m0, m1):
                ds = [max(off, hs0)] + [off] * (len(sh) - 2) + [max(off, hs1)]
                hop = rails_for(sh, ds, None, a0, b0, a1, b1, na, nb, margin, width,
                                a0.GetLayer(), None, via_margin, g_all)
                if hop:
                    break

            # 2. otherwise take the WHOLE PAIR down to an inner layer together.
            # ⚠ BOTH NETS GO DOWN AT ONCE. On this board the PHY sits behind two rows of
            # parts, so there is no component-layer path to the connector, and weaving
            # between the rows is precisely the wandering that made the router's own
            # attempt unusable. Taking the pair down keeps it coupled the whole way,
            # runs it on copper that has no pads on it at all, and costs exactly the two
            # vias per net the budget already allows.
            if hop is None and inner is not None:
                for e0 in _escape_plan(fp0, m0, a0, b0, hs0, voff, margin, via_margin,
                                       na, nb, clear, seg_clear, on_board, g_all, math):
                    for e1 in _escape_plan(fp1, m1, a1, b1, hs1, voff, margin,
                                           via_margin, na, nb, clear, seg_clear,
                                           on_board, g_all, math):
                        for sh in _centrelines(e0["e"], e1["e"]):
                            centre = [m0, e0["n"]] + sh + [e1["n"], m1]
                            ds = ([hs0 or voff] * 2 + [voff] * len(sh)
                                  + [hs1 or voff] * 2)
                            hop = rails_for(centre, ds, (2, len(centre) - 3),
                                            a0, b0, a1, b1, na, nb, margin, width,
                                            a0.GetLayer(), _LAYERS[inner],
                                            via_margin, g_thru)
                            if hop:
                                break
                        if hop:
                            break
                    if hop:
                        break
            if hop is None:
                why = "no clear path %s->%s %s" % (fp0.GetReference(), fp1.GetReference(), sorted((k, v) for k, v in _DBG.items() if v))
                break
            pending += hop
        if why:
            done.append((na, why))
            continue

        for kind, pad, q0, q1, layer in pending:
            if kind == "VIA":
                v = pcbnew.PCB_VIA(board)
                v.SetPosition(pcbnew.VECTOR2I(int(q0[0]), int(q0[1])))
                v.SetWidth(pcbnew.FromMM(0.6))
                v.SetDrill(pcbnew.FromMM(0.3))
                v.SetNet(pad.GetNet())
                v.SetViaType(pcbnew.VIATYPE_THROUGH)
                board.Add(v)
                continue
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(pcbnew.VECTOR2I(int(q0[0]), int(q0[1])))
            t.SetEnd(pcbnew.VECTOR2I(int(q1[0]), int(q1[1])))
            t.SetWidth(pcbnew.FromMM(width))
            t.SetLayer(layer)
            t.SetNet(pad.GetNet())
            board.Add(t)
            laid += 1
        done.append((na, "laid %d segment(s) as a coupled pair over %d hop(s)"
                     % (laid, len(stops) - 1)))
    return done


def _escape_plan(fpo, m, pa, pb, hs, voff, margin, via_margin, na, nb,
                 clear, seg_clear, on_board, grid, math, limit=16):
    """Workable ways for a pair to leave one package, best first.

    Each entry is a NECK point -- a short run straight out of the pads at the part's own
    pitch -- and an ESCAPE point where the pair has opened out to the via pitch and can
    drop to an inner layer.

    ⚠ THIS EXISTS TO PRUNE, and the pruning is what makes the search honest. The path
    search downstream has to consider two-corner routes to get around a connector's
    shell tabs, and the product of (directions x distances x shapes) is tens of
    thousands of candidates. Checking the escape here -- once per direction and
    distance, before any shape is considered -- removes the combinations that could
    never work whatever the run does, and the ones that survive are few. Everything is
    re-checked exactly downstream; this is a filter, not an authority.

    ⚠ AND THE DIRECTIONS FAN OUT, rather than being just "away from the part". The
    PHY's D+/D- pins face its own 24 MHz crystal, 2 mm away: straight out is into the
    crystal, and the pair has to leave at an angle. Outward is tried first and inward
    last -- inward, under the body, is the only direction open at a connector that sits
    on the board edge, which is where a USB-C always sits.
    """
    c = fpo.GetCourtyard(pcbnew.F_CrtYd).BBox().GetCenter()
    base = math.atan2(m[1] - c.y, m[0] - c.x)
    neck = pcbnew.FromMM(0.6)
    nets = {na, nb}
    pads = ((pa.GetPosition().x, pa.GetPosition().y),
            (pb.GetPosition().x, pb.GetPosition().y))
    out = []
    for turn in (0.0, math.pi):
        for dth in (0.0, 0.4, -0.4, 0.8, -0.8, 1.2, -1.2):
            ang = base + turn + dth
            ux, uy = math.cos(ang), math.sin(ang)
            nx, ny = -uy, ux
            n = (m[0] + ux * neck, m[1] + uy * neck)
            # either pairing of pad to side will do -- which rail is D+ is decided
            # downstream, and pinning it here rejected every escape at the ESD array,
            # where the arbitrary choice happened to send each rail diagonally across
            # the package to the other one's pad.
            if not any(all(seg_clear(pad, (n[0] + sgn * hs * nx, n[1] + sgn * hs * ny),
                                     nets, margin, grid)
                           for pad, sgn in zip(pads, sides))
                       for sides in ((+1, -1), (-1, +1))):
                continue
            for k in range(11):
                r = pcbnew.FromMM(1.0 + 0.25 * k)
                e = (m[0] + ux * r, m[1] + uy * r)
                vs = [(e[0] + sgn * voff * nx, e[1] + sgn * voff * ny)
                      for sgn in (+1, -1)]
                if not all(clear(v[0], v[1], nets, via_margin, grid)
                           and on_board(v[0], v[1], 0.3) for v in vs):
                    continue
                if not all(seg_clear((n[0] + sgn * hs * nx, n[1] + sgn * hs * ny), v,
                                     nets, margin, grid)
                           for v, sgn in zip(vs, (+1, -1))):
                    continue
                out.append({"n": n, "e": e})
                if len(out) >= limit:
                    return out
    return out


def _outline_pts(notes):
    """The board edge as board-local mm points, whichever way the board declared it."""
    if notes.get("outline_poly"):
        return [tuple(pt) for pt in notes["outline_poly"]]
    w, h = notes["outline_mm"]
    return [(-w / 2.0, -h / 2.0), (w / 2.0, -h / 2.0), (w / 2.0, h / 2.0), (-w / 2.0, h / 2.0)]


def _inside(outline, x, y, margin):
    """Is board-coordinate (x, y) inside `outline` by at least `margin` (all internal
    units)? Ray cast for the inside test, then point-to-segment for the margin -- a
    point can be well inside a polygon and still be 0.05 mm from one of its edges,
    which is what a via on a board edge looks like to the fab."""
    import math as _m
    pts = [(_to_board(px, py)) for px, py in outline]
    n = len(pts)
    inside = False
    for i in range(n):
        ax, ay = pts[i].x, pts[i].y
        bx, by = pts[(i + 1) % n].x, pts[(i + 1) % n].y
        if (ay > y) != (by > y) and x < (bx - ax) * (y - ay) / float(by - ay) + ax:
            inside = not inside
    if not inside:
        return False
    for i in range(n):
        ax, ay = pts[i].x, pts[i].y
        bx, by = pts[(i + 1) % n].x, pts[(i + 1) % n].y
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / L2))
        if _m.hypot(x - (ax + t * dx), y - (ay + t * dy)) < margin:
            return False
    return True


def _stitch_plane_pads(board, nets_wanted, outline, via_d=0.6, via_drill=0.3,
                       clr=0.2, max_reach=3.0, allow=(), keepouts=()):
    """Give every pad on a plane net its own via down to the plane layers.

    ⚠ WITHOUT THIS, A GROUND PAD'S CONNECTION DEPENDS ON THE POUR'S ISLAND TOPOLOGY,
    which the router decides after the fact. The F.Cu ground pour connects every
    ground pad when the board is placed -- and then routing lays 2400 track segments
    across it, chopping it into islands, and every island that does not happen to
    reach a via is unconnected copper and gets removed. 86 ground endpoints went that
    way on the optical board. The pour is still worth having (it is what stops the
    router having to find 75 separate paths), but it cannot be the ONLY thing holding
    a pad to the plane.

    A via per pad makes each connection independent of everything that happens later:
    the pad reaches In1.Cu directly, and the pour becomes a bonus rather than the
    mechanism.

    PLACEMENT IS SEARCHED, NOT ASSUMED. The via goes beside the pad, in the first of
    eight directions at increasing radius that clears every other pad on the board by
    `clr`. Same-net pads do not block it -- a ground via touching ground copper is the
    point -- and a direction that fails simply is not used. Pads with nowhere to put a
    via are REPORTED rather than skipped silently, because that is a real placement
    problem and the board should not quietly ship with one pad floating.
    """
    import math
    pads = [(pad, fp) for fp in board.GetFootprints() for pad in fp.Pads()]
    # ⚠ PADS ARE RECTANGLES AND MODELLING THEM AS CIRCLES DOES NOT WORK HERE. The
    # first version took each pad's radius as half its LARGEST dimension, which for an
    # LQFP144 pin -- 1.48 long by 0.30 wide -- inflates its width by five times. Every
    # point near the pad row then reads as occupied, and the search failed on all nine
    # of the MCU's VSS pins with "no room" when there was plenty. Bounding boxes are
    # what pcbnew already computes, they follow the pad's rotation, and point-to-box is
    # not meaningfully more code than point-to-circle.
    others = [(p.GetBoundingBox(), p.GetNetname()) for p, _ in pads]
    # ⚠ AND THE COPPER THAT IS ALREADY THERE. This used to look at pads only, which was
    # true when stitching was the first thing to lay anything. It is not any more: the
    # differential pairs are routed before this, and their tracks and transition vias
    # are obstacles like any other. Ignoring them put stitch vias on top of diff-pair
    # vias and stitch tracks across diff-pair traces -- five shorts and a pair of
    # co-located drills, none of which either routine could see on its own.
    others += [(t.GetBoundingBox(), t.GetNetname()) for t in board.GetTracks()]

    def _clear_of(x, y, netname, margin):
        """True if (x, y) keeps `margin` from every pad or track NOT on `netname`."""
        for bb, onet in others:
            if onet == netname:
                continue
            dx = max(bb.GetLeft() - x, 0, x - bb.GetRight())
            dy = max(bb.GetTop() - y, 0, y - bb.GetBottom())
            if math.hypot(dx, dy) < margin:
                return False
        return True
    made, failed, done_vias = 0, [], []
    for pad, fp in pads:
        if pad.GetNetname() not in nets_wanted:
            continue
        net = pad.GetNet()
        pc = pad.GetPosition()
        half = max(pad.GetSize().x, pad.GetSize().y) / 2.0
        need = pcbnew.FromMM(via_d / 2.0 + clr)
        # ⚠ A BIG PAD TAKES THE VIA INSIDE ITSELF, and that is the right answer rather
        # than a concession. An exposed thermal pad -- a QFN's belly, a SOT-223's tab --
        # is enclosed by its own part's pins, so there is no "beside" to search; the
        # first version of this raised on U7.25 for exactly that reason. Vias straight
        # through a thermal pad are how those parts are meant to be grounded anyway, and
        # inside the pad there is nothing to collide with by definition.
        # The threshold keeps ordinary SMD lands out of it: an 0805's 1.0 mm land is too
        # narrow to swallow a 0.6 via and still hold solder, and via-in-pad there wicks
        # paste down the hole.
        if min(pad.GetSize().x, pad.GetSize().y) >= pcbnew.FromMM(via_d + 0.6):
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(pc)
            v.SetWidth(pcbnew.FromMM(via_d))
            v.SetDrill(pcbnew.FromMM(via_drill))
            v.SetNet(net)
            v.SetViaType(pcbnew.VIATYPE_THROUGH)
            board.Add(v)
            done_vias.append((pc.x, pc.y))
            made += 1
            continue
        # ⚠ FINE-PITCH PINS NEED A FANOUT, NOT A NUDGE. A via cannot fit beside an
        # LQFP144 pin on a 0.5 mm pitch -- its neighbours are 0.5 mm away and a 0.6 mm
        # via with clearance needs about 1.0. The escape is to go OUTWARD, past the pad
        # row entirely, which is how every fine-pitch package is fanned out; the first
        # version searched only 0.5 mm and gave up on all 9 of the MCU's VSS pins.
        # So: search out to several millimetres, and try the direction pointing AWAY
        # from the part first, because that is where the open board is. Inward from a
        # QFP pin is the package's own belly and there is never room there.
        # THE COURTYARD CENTRE, not fp.GetPosition() -- a footprint's origin is
        # wherever its author put it, which for most packages is PIN 1, i.e. a corner.
        # Pointing "outward" away from a corner sends half the pins sideways along their
        # own pad row instead of off the package, and the search then fails on exactly
        # the fine-pitch pins it was added for.
        fc = fp.GetCourtyard(pcbnew.F_CrtYd).BBox().GetCenter()
        out_a = math.atan2(pc.y - fc.y, pc.x - fc.x) if (pc.x, pc.y) != (fc.x, fc.y) else 0.0
        dirs = sorted((math.pi * k / 4.0 for k in range(8)),
                      key=lambda a: abs(((a - out_a + math.pi) % (2 * math.pi)) - math.pi))
        placed = False
        for step in range(28):
            r = half + need + pcbnew.FromMM(0.15 * step)
            # A stitch is a SHORT hop to the plane. Past a couple of millimetres it has
            # stopped being that and become a wire with an impedance and a loop area,
            # and the honest thing is to fail and say the pad has no room rather than
            # quietly run one across the board.
            if r - half > pcbnew.FromMM(max_reach):
                break
            for a in dirs:
                x = int(pc.x + r * math.cos(a))
                y = int(pc.y + r * math.sin(a))
                # ⚠ CHECK THE WHOLE SEGMENT, NOT JUST THE VIA. The first version tested
                # only the via's centre and let the short track from the pad run wherever
                # it liked -- straight across U10's USB_DM pad, in one case, which DRC
                # correctly called a short between GND and a USB data line. The track is
                # copper too; sample along it and hold it to the same clearance.
                # ⚠ SAMPLE BY LENGTH, NOT BY A FIXED COUNT. Five samples over a
                # 5 mm track is one every 1.25 mm, and a 0.5 mm pad fits between two
                # of them -- which is exactly how a GND stitch ended up laid straight
                # across U10's USB_DM pad while every sample said it was clear.
                seg = math.hypot(x - pc.x, y - pc.y)
                nsamp = max(4, int(pcbnew.ToMM(seg) / 0.15) + 1)
                pts = [(pc.x + (x - pc.x) * t / nsamp, pc.y + (y - pc.y) * t / nsamp)
                       for t in range(nsamp + 1)]
                # ⚠ TWO DIFFERENT MARGINS, because two different things are being
                # placed. The VIA is 0.6 across and needs via/2 + clearance; the TRACK
                # reaching it is 0.25 and needs only track/2 + clearance, about half as
                # much. Holding the track to the via's margin is what made the search
                # fail on every fine-pitch VSS pin: the first sample sits at the pad's
                # own centre, 0.35 mm from the neighbouring pin's land, which clears a
                # 0.25 track easily and never clears a 0.6 via. The pad's own footprint
                # is skipped for the same reason -- a track leaving a pad starts inside
                # it by definition.
                if not _inside(outline, x, y, pcbnew.FromMM(via_d / 2.0 + 0.3)):
                    continue          # a via hanging off the board edge is not a via
                # ⚠ STAY OUT OF THE RESERVED CHANNELS. A through via pierces every
                # layer, so 75 ground stitches turn the inner layers into a sieve --
                # and an inner layer is exactly where a differential pair needs a clear
                # run under the component rows. Without a reserved corridor the two
                # features simply cannot both succeed: whichever goes first wins, and
                # the other reports failure. The board names the corridor, this avoids
                # it, and the pair gets somewhere to go.
                if any(kx0 <= pcbnew.ToMM(x - _to_board(0, 0).x) <= kx1
                       and ky0 <= -pcbnew.ToMM(y - _to_board(0, 0).y) <= ky1
                       for kx0, ky0, kx1, ky1 in keepouts):
                    continue
                via_lim = pcbnew.FromMM(via_d / 2.0 + clr)
                trk_lim = pcbnew.FromMM(0.25 / 2.0 + 0.127)
                ok = (_clear_of(x, y, pad.GetNetname(), via_lim)
                      and all(_clear_of(px, py, pad.GetNetname(), trk_lim)
                              for px, py in pts[1:]))
                # ...and against the vias already placed, or two neighbouring pads
                # choose the same gap and drill the same hole twice.
                if ok:
                    lim = pcbnew.FromMM(via_d + clr)
                    if any(math.hypot(x - vx, y - vy) < lim for vx, vy in done_vias):
                        ok = False
                if not ok:
                    continue
                v = pcbnew.PCB_VIA(board)
                v.SetPosition(pcbnew.VECTOR2I(x, y))
                v.SetWidth(pcbnew.FromMM(via_d))
                v.SetDrill(pcbnew.FromMM(via_drill))
                v.SetNet(net)
                v.SetViaType(pcbnew.VIATYPE_THROUGH)
                board.Add(v)
                t = pcbnew.PCB_TRACK(board)
                t.SetStart(pc)
                t.SetEnd(pcbnew.VECTOR2I(x, y))
                t.SetWidth(pcbnew.FromMM(0.25))
                t.SetLayer(pad.GetLayer())
                t.SetNet(net)
                board.Add(t)
                done_vias.append((x, y))
                made += 1
                placed = True
                break
            if placed:
                break
        if not placed:
            failed.append("%s.%s" % (fp.GetReference(), pad.GetNumber()))
    failed = [f for f in failed if f not in allow]
    if failed:
        raise SystemExit(
            "no room for a stitching via beside %d pad(s): %s\n"
            "Those pads can only reach the plane through the pour, which routing can "
            "orphan. Move the part, widen its neighbourhood, or -- if the pad really "
            "can live on the pour alone -- name it in stitch_exceptions with a reason."
            % (len(failed), ", ".join(failed[:12])))
    return made


def _edge_poly(board, pts):
    """An arbitrary closed outline on Edge.Cuts, in board-local mm.

    THE BOARD IS NOT ALWAYS A RECTANGLE. The motor tee grew an EAR off its +X end
    to carry a mounting hole -- a positive M4 through the board instead of a screw
    beside it, because a screw beside the board only resists pull-out by friction
    and the tee's connectors face the direction it would be pulled. The layout
    region stays 40 x 16 and every part stays where it was; the outline is what
    changed."""
    for a, b in zip(pts, pts[1:] + pts[:1]):
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(_to_board(*a))
        seg.SetEnd(_to_board(*b))
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetWidth(pcbnew.FromMM(0.1))
        board.Add(seg)


def _cutout(board, cx, cy, d, keepout=0.6):
    """A round hole as an Edge.Cuts circle -- which is how a board CUTOUT is drawn,
    as against a plated pad. These M4 clearance holes are mechanical: nothing
    connects to one, so giving it a pad would invent a net that does not exist.

    ⚠ AND IT GETS A KEEPOUT, WHICH THE TEE'S HOLE DID NOT NEED AND THE TRRS
    ADAPTER'S DOES. KiCad's Specctra exporter does not turn an Edge.Cuts circle
    into a DSN boundary, so FREEROUTING CANNOT SEE THE HOLE -- it happily lays
    track across it. The tee's ear hole sits in a bare tab where nothing wanted to
    route, so the gap never showed; the adapter's sits mid-board between the two
    connectors, where every net has to pass, and the first route put a +V track
    0.166 from the edge of it. A keepout zone DOES export, so the router is told
    about the hole in the only language it reads.

    `keepout` is the ring added to the hole's RADIUS: 0.6 covers the 0.3 board-edge
    clearance plus half a 0.25 track and a little rounding."""
    c = pcbnew.PCB_SHAPE(board)
    c.SetShape(pcbnew.SHAPE_T_CIRCLE)
    c.SetCenter(_to_board(cx, cy))
    c.SetEnd(_to_board(cx + d / 2.0, cy))
    c.SetLayer(pcbnew.Edge_Cuts)
    c.SetWidth(pcbnew.FromMM(0.1))
    board.Add(c)

    import math
    r = d / 2.0 + keepout
    poly = pcbnew.SHAPE_LINE_CHAIN()
    for i in range(24):
        a = 2.0 * math.pi * i / 24.0
        poly.Append(_to_board(cx + r * math.cos(a), cy + r * math.sin(a)))
    poly.SetClosed(True)
    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    z.SetDoNotAllowTracks(True)
    z.SetDoNotAllowVias(True)
    z.SetDoNotAllowZoneFills(True)
    z.SetLayerSet(pcbnew.LSET.AllCuMask())
    z.AddPolygon(poly)
    board.Add(z)


def _edge_rect(board, w, h):
    """The outline on Edge.Cuts, centred on the board origin."""
    hw, hh = w / 2.0, h / 2.0
    corners = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
    for a, b in zip(corners, corners[1:] + corners[:1]):
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(_to_board(*a))
        seg.SetEnd(_to_board(*b))
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetWidth(pcbnew.FromMM(0.1))
        board.Add(seg)


def _rules(board, notes):
    """Stack-up and clearances. A board left on KiCad's defaults fails DRC on
    fine-pitch parts for a reason that has nothing to do with the design: the
    default 0.2 mm clearance is wider than the gap between a 0.4 mm-pitch QFN's
    own pads, so every adjacent pin pair is reported. 0.127 mm (5 mil) is
    JLCPCB's standard capability and is what these boards are made to."""
    bds = board.GetDesignSettings()
    bds.SetCopperLayerCount(int(notes.get("layers", 2)))
    bds.m_MinClearance = pcbnew.FromMM(0.127)
    # 0.127 (5 mil) is JLCPCB's standard capability on 2 and 4 layer, and it is
    # what these boards are ordered to. KiCad's 0.200 default is not a fab limit
    # -- leaving it in place reports the router's own legal narrowing (it drops
    # to 0.187 to escape a 0.4 mm-pitch QFN) as 50 violations.
    bds.m_TrackMinWidth = pcbnew.FromMM(0.127)
    bds.m_ViasMinSize = pcbnew.FromMM(0.6)
    bds.m_MinThroughDrill = pcbnew.FromMM(0.3)
    bds.m_CopperEdgeClearance = pcbnew.FromMM(0.3)
    for nc in board.GetAllNetClasses().values():
        nc.SetClearance(pcbnew.FromMM(0.127))
        nc.SetTrackWidth(pcbnew.FromMM(0.25))
        # KiCad's default 0.8/0.4 via cannot escape a 0.4 mm-pitch QFN -- it does
        # not fit between the pads, so the router simply leaves those pins
        # unrouted. 0.6/0.3 is JLCPCB's STANDARD (not advanced) capability and
        # costs nothing extra.
        nc.SetViaDiameter(pcbnew.FromMM(0.6))
        nc.SetViaDrill(pcbnew.FromMM(0.3))


_LAYERS = {"F.Cu": pcbnew.F_Cu, "B.Cu": pcbnew.B_Cu,
           "In1.Cu": pcbnew.In1_Cu, "In2.Cu": pcbnew.In2_Cu}


def _add_track(board, net, layer, width, pts):
    """A polyline of tracks on one layer, all on one net."""
    for a, b in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(_to_board(*a))
        t.SetEnd(_to_board(*b))
        t.SetWidth(pcbnew.FromMM(width))
        t.SetLayer(_LAYERS[layer])
        t.SetNet(net)
        board.Add(t)


def _add_zone(board, net, layer, inset, w, h):
    """A copper pour over the whole board less `inset`. Not decoration: it is
    how the THT pads reach GND at all, since no GND track is drawn."""
    zone = pcbnew.ZONE(board)
    zone.SetLayer(_LAYERS[layer])
    zone.SetNet(net)
    zone.SetIsFilled(True)
    # SOLID pad connection, not thermal relief. Thermals exist to stop a pour
    # stealing heat from a hand-soldering iron; these boards are reflowed by the
    # fab, and on a board this small KiCad reports the two-spoke minimum as
    # "starved" anyway. Solid is also the better electrical answer for a return.
    zone.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    # ⚠ ISLAND HANDLING MUST BE SET EXPLICITLY, and not setting it was a live bug.
    # A bare pcbnew.ZONE() comes up with a min-island-area of 1e13 nm2 -- 10,000 mm2,
    # larger than any board here -- which is uninitialised memory, not a default. With
    # the AREA mode that number would purge every island on the board.
    #
    # It went unnoticed because the pours that existed were each ONE island: a plane on
    # an inner layer with nothing on it to break it up. The moment GND was poured on
    # F.Cu, where 153 parts fragment it into hundreds of islands, the zone filled to
    # exactly ZERO square millimetres -- and a zone that fills to nothing looks, in the
    # board file, exactly like a zone that filled fine.
    #
    # ALWAYS is the right mode and the one KiCad's own UI defaults to: an island of
    # copper not connected to its net is an antenna, so drop it. The islands that
    # matter are the ones touching a pad, and those are connected by definition.
    zone.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    hw, hh = w / 2.0 - inset, h / 2.0 - inset
    outline = zone.Outline()
    outline.NewOutline()
    for x, y in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)):
        pt = _to_board(x, y)
        outline.Append(pt.x, pt.y)
    board.Add(zone)
    return zone


def build(stem):
    """stem = the path prefix shared by <stem>.net and <stem>.board.json."""
    comps, nets = read_netlist(stem + ".net")
    notes = json.load(open(stem + ".board.json", encoding="utf-8"))
    placements = notes["placements"]

    missing = set(comps) - set(placements)
    if missing:
        # A part with no place is a part someone has to find a home for by hand,
        # which is exactly the drift this pipeline exists to prevent.
        raise SystemExit("no placement given for: %s" % ", ".join(sorted(missing)))

    board = pcbnew.CreateEmptyBoard()
    _rules(board, notes)
    for ref, (fp_spec, value) in sorted(comps.items()):
        fp = _load_footprint(fp_spec)
        board.Add(fp)
        fp.SetReference(ref)
        fp.SetValue(value)
        x, y, rot = placements[ref]
        fp.SetPosition(_to_board(x, y))
        fp.SetOrientationDegrees(rot)
        # WHICH POINT OF THE FOOTPRINT THE PLACEMENT NAMES. Everywhere but the optical
        # board it is the pad centroid, which is what elec/ reasons in; the optical
        # board's placements come from the CAD and name the courtyard centre instead.
        # See both anchor functions -- the difference is a couple of millimetres on
        # asymmetric parts and nothing at all on a two-pad passive, which is exactly
        # what makes it worth stating rather than inferring.
        if notes.get("anchor") == "courtyard":
            _anchor_on_courtyard(fp, _to_board(x, y))
        else:
            _anchor_on_pads(fp, _to_board(x, y))
        # The VALUE text is the part number, which is already on the assembly
        # drawing and the BOM; printed on a 22 mm board it only lands on top of
        # a pad or a neighbour's silk. Reference designators stay -- they are
        # what you read when probing the thing.
        fp.Value().SetVisible(False)
        if notes.get("refs_on_fab"):
            # DENSE BOARD: 29 designators will not fit on the silkscreen of a
            # 28 x 25 without landing on pads or each other, and JLCPCB places
            # from the CPL file, not from silk. Put them on F.Fab, which is the
            # assembly drawing, and leave the silkscreen clean. Boards with room
            # (the tee, the adapter) keep theirs on silk where a person can read
            # them while probing.
            fp.Reference().SetLayer(pcbnew.F_Fab)
        # ⚠ SILKSCREEN THAT LANDS ON A PAD IS NOT PRINTED -- the solder mask clips it --
        # so a footprint outline inside a deliberately tight cluster is ink the fab
        # cannot lay down and DRC has to complain about. The optical board's sensor
        # triplets are exactly that: an emitter between two detectors at a 1.6 pitch,
        # ten times over, producing 140 silk warnings on top of the 20 declared
        # courtyard overlaps. All 160 come from the same intended geometry.
        #
        # THE REASON TO STRIP IT IS NOT TIDINESS, IT IS LEGIBILITY. A DRC report with
        # 160 known-noise warnings is a report nobody reads, and that is how the seven
        # REAL violations from the routing pass hide in it. Nothing is lost: these parts
        # are machine-placed from the CPL, their designators are already on F.Fab, and
        # an outline printed under a component nobody can see once it is fitted was
        # never doing any work.
        # ⚠ MOVED TO F.Fab, NOT DELETED, and that is not a stylistic choice. Calling
        # fp.Remove() on a graphical item hands ownership back across the SWIG boundary
        # and pcbnew has no destructor for PCB_SHAPE: it leaks the shape AND leaves the
        # IO plugin in a state where the very next FootprintLoad raises
        # AttributeError on a SwigPyObject. Relocating the layer touches no ownership.
        # It is also the better answer -- the outline is not noise, it is just on the
        # wrong layer. F.Fab is the assembly drawing, which is exactly where a part
        # outline nobody can see once the part is fitted belongs.
        if any(ref.startswith(pre) for pre in notes.get("strip_silk", ())):
            for g in fp.GraphicalItems():
                if g.GetLayer() == pcbnew.F_SilkS:
                    g.SetLayer(pcbnew.F_Fab)
                elif g.GetLayer() == pcbnew.B_SilkS:
                    g.SetLayer(pcbnew.B_Fab)
        ref_pos = notes.get("ref_pos", {}).get(ref)
        if ref_pos:
            _place_ref(fp, _to_board(*ref_pos))

    by_ref = {fp.GetReference(): fp for fp in board.GetFootprints()}
    # ⚠ SINGLE-PAD NETS ARE NOT GIVEN TO THE BOARD AT ALL. The netlist names every
    # deliberately-unconnected pin -- U6_NC_57, K1_UNUSED_7, DAC_OUT_R_NC -- because a
    # NAMED no-connect is a decision on the record and a silently floating pin is not.
    # That is right for the SCHEMATIC and wrong for the BOARD: a net with one pad on it
    # cannot be routed, has nothing to connect to, and its only effect downstream is to
    # occupy the autorouter's search space and the DRC report. On the optical board that
    # is 88 pads of 566 -- 16% of everything the router is asked to think about, all of
    # it work that cannot be done and does not need doing.
    #
    # Counted by PADS rather than matched by NAME on purpose: a naming convention is a
    # habit someone can break, whereas "one pad" is the actual property that makes a net
    # unroutable. It also catches the genuine mistake -- a net that was MEANT to connect
    # to something and does not -- and those show up in ERC, which is where they belong.
    skipped = 0
    for name, nodes in nets.items():
        if len(nodes) < 2:
            skipped += 1
            continue
        net = pcbnew.NETINFO_ITEM(board, name)
        board.Add(net)
        for ref, pad_no in nodes:
            pad = by_ref[ref].FindPadByNumber(pad_no)
            if pad is None:
                raise SystemExit("%s has no pad %s" % (ref, pad_no))
            pad.SetNet(net)

    # ⚠ ORDER MATTERS, AND IT IS PAIRS FIRST. Both routines lay copper and each
    # treats the other's as an obstacle, so whichever runs first gets the free board.
    # I had it the other way round on the argument that ground is 75 pads against the
    # pair's four -- and with 75 stitching vias already down, the pair could not find
    # room for a PAIRED escape anywhere and gave up entirely.
    #
    # The trade is not close once stated. A ground pad that misses its via still
    # reaches the plane through the pour and whatever the router lays; it is a
    # degraded connection, not an absent one. A differential pair that cannot escape
    # as a pair is not a differential pair at all, and nothing downstream recovers it.
    # So the pair goes first and the handful of ground pads it displaces are declared.
    for name, msg in _diff_pairs(board, notes.get("diff_pairs", ()),
                                 outline=_outline_pts(notes),
                                 inner=notes.get("diff_pair_inner")):
        print("  diff pair %s: %s" % (name, msg))

    stitch = set(notes.get("stitch_nets", ()))
    if stitch:
        n = _stitch_plane_pads(board, stitch, _outline_pts(notes),
                               allow=set(notes.get("stitch_exceptions", ())),
                               keepouts=notes.get("via_keepouts", ()))
        print("  stitched %d pad(s) on %s straight to the plane"
              % (n, "/".join(sorted(stitch))))

    # outline_poly wins when present; outline_mm stays the LAYOUT REGION either way
    # (place_check and the zone filler both measure parts against it).
    if notes.get("outline_poly"):
        _edge_poly(board, [tuple(pt) for pt in notes["outline_poly"]])
    else:
        _edge_rect(board, *notes["outline_mm"])
    for h in notes.get("cutouts", ()):
        _cutout(board, h["xy"][0], h["xy"][1], h["d"])

    nets_by_name = {n.GetNetname(): n for n in board.GetNetInfo().NetsByName().values()}
    for net_name, layer, width, pts in notes.get("tracks", []):
        _add_track(board, nets_by_name[net_name], layer, width, pts)
    for net_name, layer, inset in notes.get("zones", []):
        _add_zone(board, nets_by_name[net_name], layer, inset, *notes["outline_mm"])
    if notes.get("zones"):
        # ⚠ BUILD THE CONNECTIVITY GRAPH FIRST. A board assembled by script has none --
        # it is built by the editor as you work, and nothing here was ever "worked on".
        # The zone filler uses it to decide which islands are attached to their net, so
        # without it EVERY island reads as unconnected and island removal discards the
        # lot. On an inner-layer plane that is invisible (one island, kept by luck); on
        # a pour fragmented by 153 parts it fills to exactly ZERO square millimetres,
        # and a zone that filled to nothing looks in the file just like one that
        # filled fine.
        board.BuildConnectivity()
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())

    out = stem + ".kicad_pcb"
    board.Save(out)
    print("%s: %d parts, %d nets%s, %.1f x %.1f mm"
          % (os.path.basename(out), len(comps), len(nets) - skipped,
             (" (+%d single-pad, not placed)" % skipped) if skipped else "",
             *notes["outline_mm"]))
    return out


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__.strip().splitlines()[2].strip())
    build(os.path.abspath(sys.argv[1]))
