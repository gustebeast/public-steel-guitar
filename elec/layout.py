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
        ref_pos = notes.get("ref_pos", {}).get(ref)
        if ref_pos:
            _place_ref(fp, _to_board(*ref_pos))

    by_ref = {fp.GetReference(): fp for fp in board.GetFootprints()}
    for name, nodes in nets.items():
        net = pcbnew.NETINFO_ITEM(board, name)
        board.Add(net)
        for ref, pad_no in nodes:
            pad = by_ref[ref].FindPadByNumber(pad_no)
            if pad is None:
                raise SystemExit("%s has no pad %s" % (ref, pad_no))
            pad.SetNet(net)

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
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())

    out = stem + ".kicad_pcb"
    board.Save(out)
    print("%s: %d parts, %d nets, %.1f x %.1f mm"
          % (os.path.basename(out), len(comps), len(nets), *notes["outline_mm"]))
    return out


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__.strip().splitlines()[2].strip())
    build(os.path.abspath(sys.argv[1]))
