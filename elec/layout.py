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


_LAYERS = {"F.Cu": pcbnew.F_Cu, "B.Cu": pcbnew.B_Cu}


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

    _edge_rect(board, *notes["outline_mm"])

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
