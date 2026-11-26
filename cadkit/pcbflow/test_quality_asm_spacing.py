"""quality A34: assembly spacing, extent to extent.  KiCad python: test_quality_asm_spacing.py

An 0402 beside a QFN (KiCad library footprints) at three gaps, set from the parts' own polygons:
0.30 is under IPC-7351B medium density (0.15 + 0.25 = 0.40) -- HARD, no waiver honoured; 0.60 is
under JLC's recommended 1.0 -- soft, waivable; 1.20 is clear. Then a 10 x 10 can with an 0603 in
the corner its BOX covers: polygons, not boxes (brain_board C314 / R308 read 0.00 by boxes)."""
import os
import tempfile
import wx
wx.DisableAsserts()
import pcbnew
import quality

LIB = os.path.join(os.environ.get("KICAD10_FOOTPRINT_DIR", r"C:\Program Files\KiCad\10.0\share\kicad\footprints"))


def fp(lib, name, ref, x, y, rot=0.0):
    f = pcbnew.FootprintLoad(os.path.join(LIB, lib + ".pretty"), name)
    f.SetReference(ref)
    f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
    f.SetOrientationDegrees(rot)
    return f


def judge(parts):
    d = tempfile.mkdtemp(prefix="a34_")
    stem = os.path.join(d, "t")
    b = pcbnew.BOARD()
    for f in parts:
        b.Add(f)
    pcbnew.SaveBoard(stem + ".kicad_pcb", b)
    ctx = quality.Ctx(stem)
    return [(t, quality.is_hard("A34", t)) for _s, ok, t in quality.assembly_spacing(ctx) if not ok]


bad = 0
q = fp("Package_DFN_QFN", "QFN-24-1EP_4x4mm_P0.5mm_EP2.6x2.6mm", "U1", 50.0, 50.0)
c0 = fp("Capacitor_SMD", "C_0402_1005Metric", "C1", 60.0, 50.0)
e = quality._asm_gap(quality._asm_extent(q), quality._asm_extent(c0))      # gap at x = 60
for gap, want in ((0.30, "hard"), (0.60, "soft"), (1.20, "clear")):
    q = fp("Package_DFN_QFN", "QFN-24-1EP_4x4mm_P0.5mm_EP2.6x2.6mm", "U1", 50.0, 50.0)
    c = fp("Capacitor_SMD", "C_0402_1005Metric", "C1", 60.0 - (e - gap), 50.0)
    f = judge([q, c])
    got = "clear" if not f else ("hard" if f[0][1] else "soft")
    ok = got == want
    print("ok " if ok else "BAD", "0402 %.2f from a QFN: %s (want %s)" % (gap, got, want), f[:1])
    bad += not ok
# the can's corner: an 0603 inside the can's bounding box but well clear of its chamfered body / pads
can = fp("Capacitor_SMD", "CP_Elec_10x10.5", "C2", 100.0, 100.0)
r = fp("Resistor_SMD", "R_0603_1608Metric", "R1", 94.4, 94.25)
g = quality._asm_gap(quality._asm_extent(can), quality._asm_extent(r))
bx = quality._box_gap(quality._asm_extent(can)[0], quality._asm_extent(r)[0])
ok = g > bx + 0.1
print("ok " if ok else "BAD", "0603 in a 10 x 10 can's corner: polygon gap %.2f, box gap %.2f" % (g, bx))
bad += not ok
raise SystemExit(bad)
