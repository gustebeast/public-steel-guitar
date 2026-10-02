"""Silkscreen a FINISHED board: its name and revision, what each test pad is, what each
connector pin carries. Run after routing, on the board already on disk.

    "C:/Program Files/KiCad/10.0/bin/python.exe" elec/silk.py elec/out/motor_ctrl [...]

WHY THIS EXISTS (user, 2026-10-02: a friend's board had "silkscreen labels for all of the
components, not sure if that's valuable for us"). Surveyed that day, not one board in this
project carried a single character of board-level text. The designators had been moved to
F.Fab on the dense boards for a good reason -- 0402s at courtyard pitch leave no room, and
JLCPCB places from the CPL, not from ink -- but three things went with them that are NOT
about placement:

  * WHICH BOARD IT IS. The four leg pogo boards are two mirror pairs; unlabelled, a top
    and a bottom are told apart by holding them up to each other.
  * WHICH BARE PAD IS WHICH. The SWD and bring-up pads are bare copper with a net name
    that exists only in the generator. docs/board-bringup-diagnostics.md says "probe TP3";
    the board did not say which pad TP3 was.
  * WHAT A CONNECTOR PIN CARRIES. The harness is crimped by hand against these pins, and a
    meter on a mislabelled pin is how a 24 V rail finds a 5 V one.

WHAT IT DOES NOT DO: put a designator beside every passive. On these boards that is ink
on pads, which the fab clips and DRC reports -- the reason refs_on_fab exists.

EVERY LABEL IS SEARCHED FOR A FREE SITE AND DROPPED IF THERE IS NONE. A label is placed
only where its whole box clears every pad, hole, part and other label on that side, and
the board edge; one that cannot be placed is REPORTED, never squeezed in. So this step
cannot add a DRC finding -- and it cannot move copper, so it needs no re-route.

IDEMPOTENT: it deletes the board-level silkscreen text it finds first (there is no other
source of such text in this pipeline) and lays the set again.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pcbnew  # noqa: E402
import wx  # noqa: E402

wx.DisableAsserts()

REV = "r1"                 # bumped by hand when a board is RE-ORDERED with changed copper
MM = pcbnew.FromMM
PAD_CLR = 0.20             # label box <-> any pad's mask opening
EDGE_CLR = 0.40            # label box <-> board edge or cutout
STROKE = 0.15              # JLCPCB's minimum silkscreen line
SIZES_ID = (1.5, 1.2, 1.0, 0.8)
SIZE_TP = 0.8
SIZE_J = 0.8
LEGEND_MAX_PINS = 8        # a 2x20 gets its name only
OPTICS_CLR = 12.0          # no label this close to a part whose own silk was stripped
OPTICS_NAME_CLR = 30.0     # ...and the board's name, which can go anywhere, further still


def _box(item):
    b = item.GetBoundingBox()
    return [b.GetLeft(), b.GetTop(), b.GetRight(), b.GetBottom()]


def _grow(r, d):
    return [r[0] - d, r[1] - d, r[2] + d, r[3] + d]


def _hit(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


class Side:
    """Everything a label on one side of the board has to stay off."""

    def __init__(self, board, back, dark=()):
        self.board, self.back = board, back
        self.layer = pcbnew.B_SilkS if back else pcbnew.F_SilkS
        cu = pcbnew.B_Cu if back else pcbnew.F_Cu
        self.rects, self.dark = [], []
        for fp in board.GetFootprints():
            same = fp.IsFlipped() == back
            # NO INK NEAR THE OPTICS. A board that strips its sensors' own outlines
            # (strip_silk) and is ordered in black mask to keep stray light down does not
            # then get white lettering beside the same sensors.
            if same and any(fp.GetReference().startswith(q) for q in dark):
                self.dark += [_box(pad) for pad in fp.Pads()]
            for pad in fp.Pads():
                if pad.IsOnLayer(cu) or pad.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH,
                                                               pcbnew.PAD_ATTRIB_NPTH):
                    self.rects.append(_grow(_box(pad), MM(PAD_CLR)))
            if same:
                # the part's own body: ink under a fitted part is ink nobody reads
                cy = fp.GetCourtyard(pcbnew.B_CrtYd if back else pcbnew.F_CrtYd)
                if cy.OutlineCount():
                    b = cy.BBox()
                    self.rects.append([b.GetLeft(), b.GetTop(), b.GetRight(), b.GetBottom()])
                for g in fp.GraphicalItems():
                    if g.GetLayer() == self.layer:
                        self.rects.append(_box(g))
                if fp.Reference().IsVisible() and fp.Reference().GetLayer() == self.layer:
                    self.rects.append(_box(fp.Reference()))
        for t in board.GetTracks():
            if t.GetClass() == "PCB_VIA":
                p, r = t.GetPosition(), t.GetDrillValue() // 2 + MM(0.1)
                self.rects.append([p.x - r, p.y - r, p.x + r, p.y + r])
        self.outline = pcbnew.SHAPE_POLY_SET()
        board.GetBoardPolygonOutlines(self.outline, False)
        # A HOLE WHOLLY INSIDE A LABEL'S BOX is invisible to inside(), which walks the
        # box's perimeter: the first run printed "LEG POGO MALE TOP" straight across the
        # leg board's M4 hole. Every cutout is an obstacle in its own right.
        for o in range(self.outline.OutlineCount()):
            for h in range(self.outline.HoleCount(o)):
                hb = self.outline.Hole(o, h).BBox()
                self.rects.append(_grow([hb.GetLeft(), hb.GetTop(), hb.GetRight(),
                                         hb.GetBottom()], MM(EDGE_CLR)))
        e = board.GetBoardEdgesBoundingBox()
        self.bbox = [e.GetLeft(), e.GetTop(), e.GetRight(), e.GetBottom()]

    def inside(self, r):
        """The whole box is board, EDGE_CLR from any edge or cutout. Sampled round the
        grown box's perimeter, because a slot can cross a box whose corners are all on
        laminate."""
        g = _grow(r, MM(EDGE_CLR))
        n = max(2, int((g[2] - g[0] + g[3] - g[1]) / MM(0.4)))
        for k in range(n + 1):
            x = g[0] + (g[2] - g[0]) * k // n
            y = g[1] + (g[3] - g[1]) * k // n
            for px, py in ((x, g[1]), (x, g[3]), (g[0], y), (g[2], y)):
                if not self.outline.Contains(pcbnew.VECTOR2I(int(px), int(py))):
                    return False
        cx, cy = (g[0] + g[2]) // 2, (g[1] + g[3]) // 2
        return self.outline.Contains(pcbnew.VECTOR2I(int(cx), int(cy)))

    def free(self, r, optics=None):
        g = _grow(r, MM(OPTICS_CLR if optics is None else optics))
        return (not any(_hit(g, o) for o in self.dark)
                and not any(_hit(r, o) for o in self.rects) and self.inside(r))

    def text(self, s, size, angle=0.0):
        t = pcbnew.PCB_TEXT(self.board)
        t.SetText(s)
        t.SetLayer(self.layer)
        t.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size)))
        t.SetTextThickness(MM(STROKE))
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
        t.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
        t.SetMirrored(self.back)
        t.SetTextAngleDegrees(angle)
        t.SetPosition(pcbnew.VECTOR2I(0, 0))
        return t

    def place(self, s, size, near, reach, angles=(0.0, 90.0), step=0.25, optics=None):
        """Lay `s` at the free site nearest `near` (a VECTOR2I), no further than `reach`
        mm. Returns True if it went down."""
        best = None
        for ang in angles:
            t = self.text(s, size, ang)
            b = _box(t)                                   # about the origin
            n = int(reach / step)
            for i in range(-n, n + 1):
                for j in range(-n, n + 1):
                    d2 = i * i + j * j
                    if d2 > n * n or (best is not None and d2 >= best[0]):
                        continue
                    x, y = near.x + MM(i * step), near.y + MM(j * step)
                    r = [b[0] + x, b[1] + y, b[2] + x, b[3] + y]
                    if self.free(r, optics):
                        best = (d2, ang, x, y, r)
        if best is None:
            return False
        t = self.text(s, size, best[1])
        t.SetPosition(pcbnew.VECTOR2I(int(best[2]), int(best[3])))
        self.board.Add(t)
        self.rects.append(_grow(best[4], MM(0.15)))
        return True


def _net(pad):
    n = pad.GetNetname().lstrip("/")
    return n if n and not n.startswith("unconnected") else ""


def silk(stem):
    board = pcbnew.LoadBoard(stem + ".kicad_pcb")
    name = os.path.basename(stem)
    old = [d for d in board.GetDrawings()
           if d.GetClass() == "PCB_TEXT" and d.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS)]
    try:
        notes = json.load(open(stem + ".board.json", encoding="utf-8"))
    except OSError:
        notes = {}
    dark = tuple(notes.get("strip_silk", ()))
    sides = {False: Side(board, False, dark), True: Side(board, True, dark)}
    fps = sorted(board.GetFootprints(), key=lambda f: f.GetReference())
    done, missed = [], []

    # 1. test pads FIRST: they have the least freedom, a pad's label is no use far away
    for fp in fps:
        ref = fp.GetReference()
        if not ref.startswith("TP"):
            continue
        pads = list(fp.Pads())
        net = _net(pads[0]) if pads else ""
        label = net if net and len(net) <= 10 else ref
        s = sides[fp.IsFlipped()]
        if s.place(label, SIZE_TP, fp.GetPosition(), 5.0):
            done.append("%s=%s" % (ref, label))
        elif label != ref and s.place(ref, SIZE_TP, fp.GetPosition(), 5.0):
            done.append("%s=%s" % (ref, ref))
        else:
            missed.append(ref)

    # 2. the board's own name, as large as will fit, front for choice. BEFORE the
    #    pinouts: on a 10 x 17 mm leg board there is room for one or the other, and which
    #    of two mirror-image boards this is matters more. One line, else two.
    centre = pcbnew.VECTOR2I((sides[False].bbox[0] + sides[False].bbox[2]) // 2,
                             (sides[False].bbox[1] + sides[False].bbox[3]) // 2)
    reach = max(sides[False].bbox[2] - sides[False].bbox[0],
                sides[False].bbox[3] - sides[False].bbox[1]) / 1e6
    words = name.upper().split("_") + [REV]
    forms = [" ".join(words)]
    if len(words) > 2:
        h = len(words) // 2
        forms.append(" ".join(words[:h]) + chr(10) + " ".join(words[h:]))
    for size, ident, back in [(z, f, b) for z in SIZES_ID for f in forms for b in (False, True)]:
        if sides[back].place(ident, size, centre, reach, step=0.5, optics=OPTICS_NAME_CLR):
            done.append("name %.1f mm (%s)" % (size, "back" if back else "front"))
            break
    else:
        missed.append("BOARD NAME")

    # 3. connectors: the name on the part's own side, the pinout on the back where the
    #    through-hole tails are and nothing else is
    for fp in fps:
        ref = fp.GetReference()
        if not (ref.startswith("J") and ref[1:].isdigit()):
            continue
        s = sides[fp.IsFlipped()]
        shown = fp.Reference().IsVisible() and fp.Reference().GetLayer() == s.layer
        if not shown and not s.place(ref, SIZE_J, fp.GetPosition(), 12.0):
            missed.append(ref)
        pins = {}
        for pad in fp.Pads():
            if pad.GetNumber().isdigit() and _net(pad):
                pins[int(pad.GetNumber())] = _net(pad)
        if not pins or len(pins) > LEGEND_MAX_PINS:
            continue
        legend = ref + "\n" + "\n".join("%d %s" % kv for kv in sorted(pins.items()))
        for back in (True, False):
            if sides[back].place(legend, SIZE_J, fp.GetPosition(), 14.0, step=0.5):
                done.append("%s pinout (%s)" % (ref, "back" if back else "front"))
                break
        else:
            missed.append(ref + " pinout")

    for d in old:                           # after every read; the save is next
        board.Remove(d)
    board.Save(stem + ".kicad_pcb")
    print("%s: %d label(s) -- %s" % (name, len(done), ", ".join(done)))
    if missed:
        print("  no free site for: %s" % ", ".join(missed))
    return missed


if __name__ == "__main__":
    # ⚠ ONE BOARD PER PROCESS. board.Remove() on the old labels leaves pcbnew's SWIG layer
    # in the state layout.py records for footprint graphics: the NEXT LoadBoard hands back
    # a bare SwigPyObject. Seen here on the ninth of ten boards in one run.
    _stems = [a[:-10] if a.endswith(".kicad_pcb") else a for a in sys.argv[1:]]
    if len(_stems) == 1:
        silk(_stems[0])
    else:
        import subprocess
        for _stem in _stems:
            _p = subprocess.run([sys.executable, os.path.abspath(__file__), _stem],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            sys.stdout.write("".join(ln + chr(10) for ln in _p.stdout.splitlines()
                                     if "image handler" not in ln and "memory leak" not in ln))
            if _p.returncode:
                raise SystemExit("silk.py failed on %s" % _stem)
