"""drop_redundant_pad_vias never removes a via its net needs, slack or no slack (brain_board vip, 2026-11-24).

    "C:/Program Files/KiCad/10.0/bin/python.exe" test_pad_via_baseline.py <run dir holding
        output_board.kicad_pcb (brain_board vip_s2)>

Both vip seeds lost 72 in-land vias to this pass, and the nets they sat in (AUDIO_SEL, BST_VCC,
HUB_XO, ...) were open on the finished board. The pass took each via off its NET and recounted,
but KiCad joins copper by geometry, so a net-0 via still bridged its land to the inner track and
never read as needed. (It also judged every via against the count before ANY removal, so a
removal that lowered the count left slack a needed via could spend.)
Fails without the fix (cadkit e81df41): cases 1 and 2.

On a scratch copy of vip_s2 stripped to AUDIO_SEL's tracks and vias (zones kept), the
via the pass removed is put back at (64.935, 82.900) in C39.1's land: the In2 track starts there,
so it is the pad's ONLY layer change.
  1  no slack                                    -> the needed in-land via survives
  2  an earlier candidate's removal lowers the   -> it still survives (the baseline moved)
     count by one (modelled: the board's count
     drops by one once that via is off its net)
  3  a second via in R15.1, joined only to F.Cu  -> removed: the pass still tidies
Exit 0 = PASS. The run dir is not written.
"""
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    import wx
    wx.DisableAsserts()
except Exception:
    pass
import pcbnew  # noqa: E402
import layout  # noqa: E402

FM = pcbnew.FromMM
NEED = (64.935, 82.900)     # C39.1's in-land via: the In2 track's start
EXTRA = (66.375, 86.600)    # R15.1's centre: F.Cu copper only, a via there carries nothing


def via(b, xy, net):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pcbnew.VECTOR2I(FM(xy[0]), FM(xy[1])))
    v.SetWidth(FM(0.6))
    v.SetDrill(FM(0.3))
    v.SetNet(net)
    b.Add(v)
    return v


def strip(src, dst, keep):
    """Copy a board file with every top-level segment / arc / via not on `keep` left out. Done as
    text: removing tracks through SWIG broke the board's track list ('SwigPyObject' object is not
    iterable), the trap layout's own passes document."""
    out, skip = [], False
    for line in open(src, encoding="utf-8"):
        if re.match(r"	\((segment|arc|via)\s*$", line):
            skip, block = True, [line]
            continue
        if skip:
            block.append(line)
            if line.startswith("	)"):
                skip = False
                if any('(net "%s")' % keep in x for x in block):
                    out.extend(block)
            continue
        out.append(line)
    open(dst, "w", encoding="utf-8").write("".join(out))


def board(run, slack):
    d = tempfile.mkdtemp(prefix="padvia_")
    p = os.path.join(d, "b.kicad_pcb")
    strip(os.path.join(run, "output_board.kicad_pcb"), p, "AUDIO_SEL")
    b = pcbnew.LoadBoard(p)
    net = b.FindNet("AUDIO_SEL")
    first = None
    if slack:
        # the slack via goes FIRST in track order; it sits in C39.1's land too, so the pass
        # tests it before the needed one
        first = via(b, (64.40, 82.40), net)
    via(b, NEED, net)
    via(b, EXTRA, net)
    if slack:
        real = b.GetConnectivity

        class Conn:
            def __init__(self, c):
                self.c = c

            def GetUnconnectedCount(self, vis):
                n = self.c.GetUnconnectedCount(vis)
                return n - 1 if first.GetNetCode() == 0 or first not in list(b.GetTracks()) else n

        b.GetConnectivity = lambda: Conn(real())
    b.BuildConnectivity()
    return b


def left(b):
    M = pcbnew.ToMM
    return {(round(M(t.GetPosition().x), 3), round(M(t.GetPosition().y), 3))
            for t in b.GetTracks() if isinstance(t, pcbnew.PCB_VIA)}


def main(run):
    bad = []

    def want(ok, msg):
        print("%s %s" % ("PASS" if ok else "FAIL", msg))
        if not ok:
            bad.append(msg)

    b = board(run, slack=False)
    v0 = [t for t in b.GetTracks() if isinstance(t, pcbnew.PCB_VIA)
          and (round(pcbnew.ToMM(t.GetPosition().x), 3), round(pcbnew.ToMM(t.GetPosition().y), 3)) == NEED][0]
    b.BuildConnectivity()
    with_v = b.GetConnectivity().GetUnconnectedCount(False)
    nc, at = v0.GetNetCode(), v0.GetPosition()
    v0.SetNetCode(0)
    b.BuildConnectivity()
    net0 = b.GetConnectivity().GetUnconnectedCount(False)
    v0.SetPosition(pcbnew.VECTOR2I(FM(-1000.0), FM(-1000.0)))
    b.BuildConnectivity()
    without = b.GetConnectivity().GetUnconnectedCount(False)
    v0.SetPosition(at)
    v0.SetNetCode(nc)
    b.BuildConnectivity()
    want(without > with_v, "setup: the C39.1 via carries AUDIO_SEL (%d unconnected off the board, %d with it)"
         % (without, with_v))
    print("     (off its net only: %d -- %s)" % (net0, "the old test could not see it" if net0 == with_v else "seen"))
    layout.drop_redundant_pad_vias(b, {})
    v = left(b)
    want(NEED in v, "1 the needed in-land via survives (no slack)")
    want(EXTRA not in v, "3 the redundant via in R15.1 is removed")

    b = board(run, slack=True)
    layout.drop_redundant_pad_vias(b, {})
    v = left(b)
    want(NEED in v, "2 the needed in-land via survives when an earlier removal lowered the count")
    b.BuildConnectivity()
    return bad


if __name__ == "__main__":
    bad = main(os.path.abspath(sys.argv[1]))
    print("PASS" if not bad else "FAIL: %d" % len(bad))
    os._exit(1 if bad else 0)
