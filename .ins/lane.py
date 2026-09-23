"""Is there a clear vertical lane at x, over a y range, for one net? Pads AND OUTLINE.

⚠ THIS EXISTS BECAUSE THE SAME MISTAKE WAS MADE TWICE, four days apart, by the same
reasoning both times. Scan the pads along a candidate lane, find none, conclude the lane
is free -- when what the empty scan actually meant was that the lane is off the board.
It cost U15's haul (11 unconnected, 3 violations against a baseline of 9 and 0) and then
the first I2C spine, which sat 0.22 mm from a board edge at 64.5817 against a 0.30 rule.

A scan that asks only the pads cannot tell "nothing is here" from "nothing CAN be here",
and those are opposite answers. So this asks both, always, and reports the binding
constraint by name rather than a verdict:

    py -3.12 .ins/lane.py 69.832 34.9 109.9 SAI_SCK
    py -3.12 .ins/lane.py 69.832,70.332 34.9 109.9 SAI_SCK,SAI_FS   -- several at once

Clearance is the fab rule (0.127) plus the track's half width; the board-edge rule is
0.300. Pads ON the named net are skipped -- they are where the lane is going.
"""
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PCB = os.path.join(ROOT, "elec", "out", "optical.kicad_pcb")
KI = r"C:\Program Files\KiCad\10.0\bin\python.exe"
CLR, EDGE = 0.127, 0.300

# ⚠ RUN THE PAD SCAN IN KiCad's PYTHON, ONCE, AND GET OUT. pcbnew is the only thing that
# knows a footprint's placed pad geometry, so it cannot be dropped -- but every call into
# it is a chance to hang the session, and the reason is not the one it looks like.
#
# ⚠ A pcbnew ASSERT IS A MODAL DIALOG, NOT AN EXCEPTION. PCB_VIA::GetWidth() called
# without a layer argument asserts, and KiCad's Python answers by popping a wxWidgets
# "Do you want to stop the program?" box ON THE USER'S SCREEN and BLOCKING until someone
# clicks it. Two probes were diagnosed as a file-locking deadlock and cost ten minutes
# each; they were not locked, they were waiting for a click nobody knew to make, because
# the commands captured stderr and the warning went with it.
# So: no assert-prone accessor in a probe (via geometry comes from GetDrillValue), and if
# a pcbnew call "hangs", look at the screen before theorising about locks.
# (freerouting has the same failure mode and route.py already fixes it there, with
# -Djava.awt.headless=true. The lesson did not generalise until it cost a second hour.)
_PROBE = r"""
import json, pcbnew
b = pcbnew.LoadBoard(%r)
pads = []
for fp in b.Footprints():
    for p in fp.Pads():
        pads.append([fp.GetReference(), p.GetNumber(), p.GetNetname(),
                     p.GetPosition().x / 1e6, p.GetPosition().y / 1e6,
                     p.GetSize().x / 2e6, p.GetSize().y / 2e6])
edge = [[d.GetStart().x / 1e6, d.GetStart().y / 1e6,
         d.GetEnd().x / 1e6, d.GetEnd().y / 1e6]
        for d in b.GetDrawings() if d.GetLayerName() == "Edge.Cuts"]
print("@@" + json.dumps({"pads": pads, "edge": edge}))
"""


def probe(pcb=PCB):
    cache = os.path.join(HERE, "lane_cache.json")
    if os.path.isfile(cache) and os.path.getmtime(cache) > os.path.getmtime(pcb):
        return json.load(io.open(cache, encoding="utf-8"))
    r = subprocess.run([KI, "-c", _PROBE % pcb], capture_output=True, text=True)
    m = re.search(r"@@(\{.*\})", r.stdout, re.S)
    if not m:
        raise SystemExit("pad probe failed:\n" + (r.stdout + r.stderr)[-800:])
    d = json.loads(m.group(1))
    io.open(cache, "w", encoding="utf-8").write(json.dumps(d))
    return d


def check(x, y0, y1, net, width=0.25, d=None):
    """Nearest obstruction to a vertical lane, as (margin_mm, what)."""
    d = d or probe()
    need = CLR + width / 2.0
    worst = (1e9, "clear")
    for ref, num, pnet, px, py, hx, hy in d["pads"]:
        if pnet == net or py + hy < min(y0, y1) or py - hy > max(y0, y1):
            continue
        gap = abs(px - x) - hx - width / 2.0
        if gap - CLR < worst[0]:
            worst = (gap - CLR, "%s pad %s [%s] at x %.3f, gap %.3f (need %.3f)"
                     % (ref, num, pnet or "-", px, gap, CLR))
    # ⚠ AND THE OUTLINE. An empty pad scan is not an answer until this has run.
    for x1, ey1, x2, ey2 in d["edge"]:
        for yy in (y0, y1, (y0 + y1) / 2.0):
            if abs(ey2 - ey1) > 1e-9 and min(ey1, ey2) - 1e-9 <= yy <= max(ey1, ey2) + 1e-9:
                ex = x1 + (x2 - x1) * (yy - ey1) / (ey2 - ey1)
                gap = abs(ex - x) - width / 2.0
                if gap - EDGE < worst[0]:
                    worst = (gap - EDGE, "BOARD EDGE at x %.4f (y %.1f), gap %.3f "
                             "(need %.3f)" % (ex, yy, gap, EDGE))
    return worst


def seg(p0, p1, net, width=0.2, d=None):
    """Same question for an ARBITRARY segment, not just a vertical one.

    The vertical form above answers "can a spine run the length of the column". This one
    answers "can this ONE hop be laid straight", which is what a repeated per-quad failure
    asks: four of the five TIA_OUT_*B runs failed at an identical 10.48 mm, so the hop is
    the unit, not the net."""
    d = d or probe()
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    L2 = dx * dx + dy * dy
    worst = (1e9, "clear")
    for ref, num, pnet, px, py, hx, hy in d["pads"]:
        if pnet == net:
            continue
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - x0) * dx + (py - y0) * dy) / L2))
        cx, cy = x0 + t * dx, y0 + t * dy
        # rectangular pad, so the clearance is measured per axis and the worse one wins
        gap = max(abs(cx - px) - hx, abs(cy - py) - hy) - width / 2.0
        if gap - CLR < worst[0]:
            worst = (gap - CLR, "%s pad %s [%s] gap %.3f" % (ref, num, pnet or "-", gap))
    for ex1, ey1, ex2, ey2 in d["edge"]:
        for s in range(21):                       # sample the hop against every edge
            t = s / 20.0
            cx, cy = x0 + t * dx, y0 + t * dy
            ux, uy = ex2 - ex1, ey2 - ey1
            el2 = ux * ux + uy * uy
            u = 0.0 if el2 == 0 else max(0.0, min(1.0, ((cx - ex1) * ux + (cy - ey1) * uy) / el2))
            gap = ((cx - ex1 - u * ux) ** 2 + (cy - ey1 - u * uy) ** 2) ** 0.5 - width / 2.0
            if gap - EDGE < worst[0]:
                worst = (gap - EDGE, "BOARD EDGE gap %.3f (need %.3f)" % (gap, EDGE))
    return worst


def pad(ref, num, d=None):
    d = d or probe()
    for r, n, net, px, py, hx, hy in d["pads"]:
        if r == ref and n == str(num):
            return (px, py, net)
    raise SystemExit("no pad %s.%s" % (ref, num))


if __name__ == "__main__":
    xs = [float(v) for v in sys.argv[1].split(",")]
    y0, y1 = float(sys.argv[2]), float(sys.argv[3])
    nets = sys.argv[4].split(",")
    w = float(sys.argv[5]) if len(sys.argv) > 5 else 0.25
    d = probe()
    for x, net in zip(xs, nets * len(xs)):
        margin, what = check(x, y0, y1, net, w, d)
        print("x %-9.3f %-10s %-5s margin %+.3f mm   %s"
              % (x, net, "OK" if margin >= 0 else "FAIL", margin, what))
