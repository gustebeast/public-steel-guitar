"""layout._declared_copper_clear meets declared copper against declared copper (2026-11-22).

    "C:/Program Files/KiCad/10.0/bin/python.exe" test_declared_clear.py [<run dir holding
        output_board.unrouted.kicad_pcb, e.g. rPS_11k1>]

1. SYNTHETIC: two nets' declared tracks laid in ONE batch, 0.10 mm apart edge to edge (U205's
   BOOT5 escape against SW5's 1.3 mm end cap), must stop the board; at 0.20 mm they pass; a
   same-net pair never stops it. The old check compared a batch only with pads and earlier
   tracks, so the 0.10 mm pair passed.
2. ON A BOARD (optional): esc11 seed 1's unrouted board carries the BOOT5_1/SW5_1,
   BOOT5_2/SW5_2 and PB_ISENP_K/PB_VCC_K crowding route.py took up as router shorts; checking
   all its pre-route copper as one batch must name all three.
Exit 0 = PASS. Nothing is saved.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    import wx as _wx
    _wx.DisableAsserts()
except Exception:
    pass
import pcbnew
import layout

F = pcbnew.FromMM


def _net(b, name):
    n = pcbnew.NETINFO_ITEM(b, name)
    b.Add(n)
    return n


def _trk(b, net, a, e, w):
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(pcbnew.VECTOR2I(F(a[0]), F(a[1])))
    t.SetEnd(pcbnew.VECTOR2I(F(e[0]), F(e[1])))
    t.SetWidth(F(w))
    t.SetLayer(pcbnew.F_Cu)
    t.SetNet(net)
    b.Add(t)
    return t


def stops(b, items):
    try:
        layout._declared_copper_clear(b, items)
    except SystemExit as e:
        return str(e)
    return None


def synthetic():
    bad = []
    for gap, want in ((0.10, True), (0.20, False)):
        b = pcbnew.BOARD()
        sw, boot = _net(b, "SW"), _net(b, "BOOT")
        # a 1.3 mm track ending at (10, 10), a 0.2 mm one whose edge is `gap` off its cap
        cap = _trk(b, sw, (10, 10), (10, 6), 1.3)
        y = 10 + 0.65 + gap + 0.1
        esc = _trk(b, boot, (9, y), (11, y), 0.2)
        got = stops(b, [cap, esc])
        if bool(got) != want:
            bad.append("gap %.2f mm: %s" % (gap, "stopped" if got else "passed"))
        elif got and not ("BOOT" in got and "SW" in got):
            bad.append("gap %.2f mm stopped without naming both nets: %s" % (gap, got))
    b = pcbnew.BOARD()
    one = _net(b, "SW")
    a, c = _trk(b, one, (0, 0), (5, 0), 0.5), _trk(b, one, (0, 0.3), (5, 0.3), 0.5)
    if stops(b, [a, c]):
        bad.append("two tracks of ONE net stopped the board")
    return bad


def on_board(d):
    b = pcbnew.LoadBoard(os.path.join(d, "output_board.unrouted.kicad_pcb"))
    got = stops(b, list(b.GetTracks())) or ""
    print(got)
    return ["%s/%s not named" % pr for pr in (("BOOT5_1", "SW5_1"), ("BOOT5_2", "SW5_2"),
                                                 ("PB_ISENP_K", "PB_VCC_K"))
            if not all(any(n in ln and "[%s]" % n in ln for ln in got.splitlines()) for n in pr)]


if __name__ == "__main__":
    bad = synthetic()
    if len(sys.argv) > 1:
        bad += on_board(os.path.abspath(sys.argv[1]))
    for x in bad:
        print("  FAIL:", x)
    print("PASS" if not bad else "FAIL")
    sys.stdout.flush()
    os._exit(1 if bad else 0)
