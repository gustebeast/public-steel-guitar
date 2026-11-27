"""layout._path_clear refuses a stub across another net's frozen band, allows a clear run
(output_board rPS_e2: a +24V stub laid across VIN_SW's band).

    "C:/Program Files/KiCad/10.0/bin/python.exe" test_path_clear_frozen.py [<rPS_e2's output_board.unrouted.kicad_pcb>]

On the committed fixture (testdata/frozen_bands, make.py): a SIG stub on F.Cu from (10, 13.5)
to (10, 18.5) crosses NEAR's and FAR's frozen bands -- refused; one from (10, 3) to (10, 8) on
F.Cu crosses nothing -- allowed. With e2's board: its +24V stub (136.38, 131.15) ->
(132.35, 120.06) across VIN_SW's band is refused.
Exit 0 = PASS.
"""
import os
import sys

import wx  # noqa: F401  (KiCad's python ships it)
wx.DisableAsserts()
import pcbnew  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout  # noqa: E402

v = lambda x, y: pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))
bad = []


def run(tag, path, net, a, z, w_mm, want):
    b = pcbnew.LoadBoard(path)
    got = bool(layout._path_clear(b, v(*a), v(*z), net, b.GetLayerID("F.Cu"), pcbnew.FromMM(w_mm)))
    print("%s: %s %s -> %s %s (want %s)" % (tag, net, a, z, "allowed" if got else "refused",
                                            "allowed" if want else "refused"))
    if got != want:
        bad.append("%s: %s" % (tag, "allowed" if got else "refused"))


fx = os.path.join(HERE, "testdata", "frozen_bands", "b.kicad_pcb")
run("fixture across the bands", fx, "SIG", (10.0, 13.5), (10.0, 18.5), 0.2, False)
run("fixture clear run", fx, "SIG", (10.0, 3.0), (10.0, 8.0), 0.2, True)
if len(sys.argv) > 1:
    run("e2 +24V across VIN_SW", sys.argv[1], "+24V", (136.38, 131.15), (132.35, 120.06), 0.9, False)
for b_ in bad:
    print("  FAIL:", b_)
print("PASS" if not bad else "FAIL")
sys.stdout.flush()
os._exit(1 if bad else 0)
