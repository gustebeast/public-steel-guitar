"""Self-check of Steel:Texas_RPW0010A_VQFN-HR-10_2x2mm_P0.45mm (U21 / U221, the TPS259470A eFuse).

    "C:/Program Files/KiCad/10.0/bin/python.exe" elec/check_fp_rpw0010a.py

The land is hand-written from TI SLVSFC9C (Rev C, May 2026) p.73, "RPW0010A example board
layout" (4225183/A), read off the drawing at 200 px/mm, with p.72's outline for the pitches.
This checks the FILE against that table, not against itself:

1. every pad number 1..10 is present; corner pins 1/4/7/10 are two overlapping pads (the
   L shape), every other pin one pad;
2. each pad's centre and size match the table within 0.01 mm (the drawing's dimensions are
   "for reference only": 0.475 pitch puts the corner pads at 0.700, the drawn pads and the
   0.65 leg at 0.705 -- the drawing is taken);
3. pin 1 is top-left in the top view and the numbering runs 1-4 down the left, 5 / 6 the
   bars, 7-10 up the right (p.5 Fig 5-1);
4. copper of different pins never comes closer than 0.19 mm (the drawing's gaps are 0.2);
5. the courtyard encloses every pad by >= 0.25 mm and the fab outline is the 2.0 mm body.
Exit 0 = PASS. Nothing is written.
"""
import os
import sys

try:
    import wx as _wx
    _wx.DisableAsserts()
except Exception:
    pass
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, "footprints", "Steel.pretty")
NAME = "Texas_RPW0010A_VQFN-HR-10_2x2mm_P0.45mm"
TOL = 0.01

# pin -> [(x, y, w, h)] in mm, top view, KiCad y down (SLVSFC9C p.73)
TABLE = {
    "1": [(-0.900, -0.705, 0.600, 0.300), (-0.725, -0.880, 0.250, 0.650)],
    "2": [(-0.900, -0.225, 0.600, 0.250)],
    "3": [(-0.900, 0.225, 0.600, 0.250)],
    "4": [(-0.900, 0.705, 0.600, 0.300), (-0.725, 0.880, 0.250, 0.650)],
    "5": [(-0.250, 0.000, 0.300, 2.400)],
    "6": [(0.250, 0.000, 0.300, 2.400)],
    "7": [(0.900, 0.705, 0.600, 0.300), (0.725, 0.880, 0.250, 0.650)],
    "8": [(0.900, 0.225, 0.600, 0.250)],
    "9": [(0.900, -0.225, 0.600, 0.250)],
    "10": [(0.900, -0.705, 0.600, 0.300), (0.725, -0.880, 0.250, 0.650)],
}
MIN_GAP = 0.19
CRT_MARGIN = 0.25


def mm(v):
    return pcbnew.ToMM(v)


def rect(p):
    c, s = p.GetPosition(), p.GetSize()
    x, y, w, h = mm(c.x), mm(c.y), mm(s.x), mm(s.y)
    return (x - w / 2, y - h / 2, x + w / 2, y + h / 2)


def gap(a, b):
    dx = max(a[0] - b[2], b[0] - a[2], 0.0)
    dy = max(a[1] - b[3], b[1] - a[3], 0.0)
    return (dx * dx + dy * dy) ** 0.5


def main():
    bad = []
    fp = pcbnew.FootprintLoad(LIB, NAME)
    if fp is None:
        return ["cannot load %s from %s" % (NAME, LIB)]
    pads = {}
    for p in fp.Pads():
        pads.setdefault(p.GetNumber(), []).append(p)
    if set(pads) != set(TABLE):
        bad.append("pad numbers %s, want %s" % (sorted(pads, key=int), sorted(TABLE, key=int)))
    for num, want in TABLE.items():
        got = sorted(((mm(p.GetPosition().x), mm(p.GetPosition().y), mm(p.GetSize().x), mm(p.GetSize().y))
                      for p in pads.get(num, [])), key=lambda t: (t[2], t[3]))
        want = sorted(want, key=lambda t: (t[2], t[3]))
        if len(got) != len(want):
            bad.append("pin %s: %d pad(s), want %d" % (num, len(got), len(want)))
            continue
        for g, w in zip(got, want):
            if any(abs(a - b) > TOL for a, b in zip(g, w)):
                bad.append("pin %s: pad at (%.3f, %.3f) %.3f x %.3f, want (%.3f, %.3f) %.3f x %.3f" % ((num,) + g + w))
        if len(got) == 2 and gap(rect(pads[num][0]), rect(pads[num][1])) > 0:
            bad.append("pin %s: the L's two pads do not touch" % num)
        for p in pads.get(num, []):
            if not p.IsOnLayer(pcbnew.F_Cu) or not p.IsOnLayer(pcbnew.F_Paste) or not p.IsOnLayer(pcbnew.F_Mask):
                bad.append("pin %s: a pad is not on F.Cu + F.Paste + F.Mask" % num)
    # 3: orientation -- pin 1 top-left, left column 1-4 top to bottom, right column 10-7
    if pads.get("1") and pads.get("10"):
        p1 = min(pads["1"], key=lambda p: p.GetSize().x * 0 + p.GetPosition().x)
        if not (mm(p1.GetPosition().x) < 0 and mm(p1.GetPosition().y) < 0):
            bad.append("pin 1 is not top-left")
    ys = lambda n: min(mm(p.GetPosition().y) for p in pads.get(n, [])) if pads.get(n) else None
    if not ys("1") < ys("2") < ys("3") < ys("4"):
        bad.append("left column is not 1-4 top to bottom")
    if not ys("10") < ys("9") < ys("8") < ys("7"):
        bad.append("right column is not 10-7 top to bottom")
    # 4: different pins' copper
    allp = [(n, rect(p)) for n, ps in pads.items() for p in ps]
    worst = (9.0, None)
    for i, (na, ra) in enumerate(allp):
        for nb, rb in allp[i + 1:]:
            if na != nb:
                g = gap(ra, rb)
                if g < worst[0]:
                    worst = (g, (na, nb))
    print("closest copper of two pins: %.3f mm (%s / %s)" % ((worst[0],) + worst[1]))
    if worst[0] < MIN_GAP - 1e-6:
        bad.append("pins %s / %s copper %.3f mm apart, under %.2f" % (worst[1] + (worst[0], MIN_GAP)))
    # 5: courtyard and fab
    crt = fp.GetCourtyard(pcbnew.F_CrtYd)
    if crt.OutlineCount() == 0:
        bad.append("no courtyard")
    else:
        bb = crt.BBox()
        c = (mm(bb.GetX()), mm(bb.GetY()), mm(bb.GetRight()), mm(bb.GetBottom()))
        lo = min(r[0] for _, r in allp), min(r[1] for _, r in allp)
        hi = max(r[2] for _, r in allp), max(r[3] for _, r in allp)
        m = min(lo[0] - c[0], lo[1] - c[1], c[2] - hi[0], c[3] - hi[1])
        print("courtyard (%.2f, %.2f)-(%.2f, %.2f); pads (%.2f, %.2f)-(%.2f, %.2f); margin %.3f mm"
              % (c + lo + hi + (m,)))
        if m < CRT_MARGIN - 1e-6:
            bad.append("courtyard encloses the pads by %.3f mm, under %.2f" % (m, CRT_MARGIN))
    fab = [g for g in fp.GraphicalItems() if g.GetLayer() == pcbnew.F_Fab]
    if fab:
        xs = [mm(v) for g in fab for v in (g.GetStart().x, g.GetEnd().x)]
        yv = [mm(v) for g in fab for v in (g.GetStart().y, g.GetEnd().y)]
        if abs(max(xs) - min(xs) - 2.0) > TOL or abs(max(yv) - min(yv) - 2.0) > TOL:
            bad.append("fab outline %.2f x %.2f, want the 2.0 x 2.0 body" % (max(xs) - min(xs), max(yv) - min(yv)))
    else:
        bad.append("no fab outline")
    return bad


if __name__ == "__main__":
    bad = main()
    for x in bad:
        print("  FAIL:", x)
    print("PASS" if not bad else "FAIL")
    sys.stdout.flush()
    os._exit(1 if bad else 0)
