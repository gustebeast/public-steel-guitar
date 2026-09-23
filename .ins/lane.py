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
# ⚠ PRE-LAID COPPER IS AN OBSTACLE TOO, and leaving it out of this probe made the
# tool confidently recommend a via lane straight through the I2C and +3V3D spines --
# 502 candidate spots, the best of them sitting on a B.Cu trunk. A via pierces every
# layer, so it does not care which one the spine is on.
# GetWidth() on a via asserts and pops a MODAL DIALOG (see above): use GetDrillValue.
vias, tracks = [], []
for t in b.GetTracks():
    if t.Type() == pcbnew.PCB_VIA_T:
        vias.append([t.GetNetname(), t.GetStart().x / 1e6, t.GetStart().y / 1e6,
                     t.GetDrillValue() / 2e6 + 0.15])
    else:
        tracks.append([t.GetNetname(), b.GetLayerName(t.GetLayer()),
                       t.GetStart().x / 1e6, t.GetStart().y / 1e6,
                       t.GetEnd().x / 1e6, t.GetEnd().y / 1e6, t.GetWidth() / 2e6])
print("@@" + json.dumps({"pads": pads, "edge": edge, "vias": vias, "tracks": tracks}))
"""


def via_clear(x, y, net, dia=0.6, d=None):
    """Margin for a THROUGH via at (x, y): pads, board edge, other vias, and every
    pre-laid track on any layer -- a via connects them all."""
    d = d or probe()
    r = dia / 2.0
    worst = (1e9, "clear")
    for ref, num, pnet, px, py, hx, hy in d["pads"]:
        if pnet == net:
            continue
        g = max(abs(px - x) - hx, abs(py - y) - hy) - r - CLR
        if g < worst[0]:
            worst = (g, "%s pad %s [%s]" % (ref, num, pnet or "-"))
    for vnet, vx, vy, vr in d.get("vias", ()):
        if vnet == net:
            continue
        g = ((vx - x) ** 2 + (vy - y) ** 2) ** 0.5 - vr - r - CLR
        if g < worst[0]:
            worst = (g, "via [%s] at %.2f,%.2f" % (vnet or "-", vx, vy))
    for tnet, layer, x1, y1, x2, y2, hw in d.get("tracks", ()):
        if tnet == net:
            continue
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / L2))
        g = (((x1 + t * dx - x) ** 2 + (y1 + t * dy - y) ** 2) ** 0.5) - hw - r - CLR
        if g < worst[0]:
            worst = (g, "%s track [%s]" % (layer, tnet or "-"))
    for ex1, ey1, ex2, ey2 in d["edge"]:
        ux, uy = ex2 - ex1, ey2 - ey1
        el2 = ux * ux + uy * uy
        u = 0.0 if el2 == 0 else max(0.0, min(1.0, ((x - ex1) * ux + (y - ey1) * uy) / el2))
        g = (((ex1 + u * ux - x) ** 2 + (ey1 + u * uy - y) ** 2) ** 0.5) - r - EDGE
        if g < worst[0]:
            worst = (g, "BOARD EDGE")
    return worst


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


def inner_seg(p0, p1, net, width=0.2, layer="In2.Cu", d=None):
    """A segment on an INNER layer: pads do not block it, vias and same-layer copper do.

    ⚠ ASKING seg() ABOUT AN INNER LAYER GIVES THE WRONG ANSWER IN BOTH DIRECTIONS. It
    counts every SMD pad as an obstacle -- on In2 they are three layers away and irrelevant,
    so it rejects lanes that are wide open -- while knowing nothing about the vias that DO
    block it. On this board that matters: In2 is the only signal layer left once F.Cu is
    full, and it is where the analog runs that cannot cross the Ci row have to go."""
    d = d or probe()
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    L2 = dx * dx + dy * dy
    worst = (1e9, "clear")

    def near(px, py, r):
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - x0) * dx + (py - y0) * dy) / L2))
        return (((x0 + t * dx - px) ** 2 + (y0 + t * dy - py) ** 2) ** 0.5) - r - width / 2.0

    for vnet, vx, vy, vr in d.get("vias", ()):
        if vnet == net:
            continue
        g = near(vx, vy, vr) - CLR
        if g < worst[0]:
            worst = (g, "via [%s] at %.2f,%.2f" % (vnet or "-", vx, vy))
    for tnet, tlayer, ax, ay, bx, by, hw in d.get("tracks", ()):
        if tnet == net or tlayer != layer:
            continue
        for px, py in ((ax, ay), (bx, by), ((ax + bx) / 2, (ay + by) / 2)):
            g = near(px, py, hw) - CLR
            if g < worst[0]:
                worst = (g, "%s track [%s]" % (tlayer, tnet or "-"))
    for ex1, ey1, ex2, ey2 in d["edge"]:
        for s in range(11):
            t = s / 10.0
            cx, cy = x0 + t * dx, y0 + t * dy
            ux, uy = ex2 - ex1, ey2 - ey1
            el2 = ux * ux + uy * uy
            u = 0.0 if el2 == 0 else max(0.0, min(1.0, ((cx - ex1) * ux + (cy - ey1) * uy) / el2))
            g = (((ex1 + u * ux - cx) ** 2 + (ey1 + u * uy - cy) ** 2) ** 0.5) - width / 2.0 - EDGE
            if g < worst[0]:
                worst = (g, "BOARD EDGE")
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


def overlaps(d=None, clr=CLR):
    """Every pair of pads on DIFFERENT nets that is closer than the fab rule.

    ⚠ THE PIPELINE HAD NO SUCH CHECK AND IT COST AN HOUR. Turning the +X supply column
    flat moved it 0.92 mm east into U1..U5, and layout reported "139 laid, 1 left to the
    router" and looked entirely healthy. The shorts -- Cs<k>3 pad 2 on its op-amp's pad 5,
    in every quad -- surfaced only in the DRC at the END of a 57-minute route, as five
    shorting_items among 35 violations, where they read as routing damage rather than as a
    placement that was never manufacturable.
    A placement error should be caught by looking at the placement. This is O(n^2) on 900
    pads and takes about a second.
    """
    d = d or probe()
    bad = []
    for i, (r1, n1, net1, x1, y1, hx1, hy1) in enumerate(d["pads"]):
        for r2, n2, net2, x2, y2, hx2, hy2 in d["pads"][i + 1:]:
            if r1 == r2 or (net1 and net1 == net2):
                continue
            gap = max(abs(x1 - x2) - hx1 - hx2, abs(y1 - y2) - hy1 - hy2)
            if gap < clr:
                bad.append((round(gap, 4), "%s.%s [%s]" % (r1, n1, net1 or "-"),
                            "%s.%s [%s]" % (r2, n2, net2 or "-")))
    return sorted(bad)


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
