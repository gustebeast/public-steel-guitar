"""Can the string array still do its job? The LAYOUT's side of the signal chain.

    "C:/Program Files/KiCad/10.0/bin/python.exe" elec/check_north_si.py elec/out/optical

⚠ THIS IS THE OTHER HALF OF .ins/opt_audit.py. That one reads the NETLIST and asks whether
the right pins are joined; this one reads the BOARD and asks whether the copper that joins
them can carry a picoamp signal. Nothing checked the second question, and the north half
was just rebuilt from scratch -- spines, vias and all -- on the strength of "0 ratlines",
which says every net is connected and says nothing about whether the amplifier still works.

Four measurements, and the thresholds are the design's own numbers (elec/optical.py's TIA
notes), not invented here:

  SUMMING NODE CLEARANCE. TIA_IN is 250 k at the photodiode's ~143 nA (thin string), and
  the LED's carrier current is switched at 48 kHz -- the SAME frequency the firmware's
  lock-in uses as its reference. Coupling from LED copper into the summing node is
  therefore NOT rejected by the demodulator the way ambient light and mains hum are: it
  arrives in phase and reads as signal. 0.5 mm floor, which is 3.3x the fab clearance and
  about where the estimate below stops being small.

  FEEDBACK LOOP AREA. The op-amp's in and out pins with Rf and Cf between them. Any dB/dt
  through that loop is an induced EMF in series with the feedback network. 5 mm2 ceiling:
  the rule for a TIA is "as small as the parts allow", and 0402s around a 0.65 mm pitch
  package allow about 4.

  In1.Cu PLANE CONTINUITY. In1 is a SOLID ground plane and it is the return path for every
  one of these channels. A foreign via punches a O0.90 antipad through it. Where two
  antipads overlap the plane is cut, and a chain of cuts is a plane split in two -- at
  which point the return current goes the long way round and the loop area of twenty
  channels is set by the shape of the hole rather than by the layout.

  MID's SERIES RESISTANCE. The bias reference is shared by all twenty channels, so its own
  impedance is a coupling path between them: current from one channel develops a voltage
  every other channel sees as its reference. The currents are nanoamps, so this is
  expected to be irrelevant and is measured to confirm that, not to police it.

The coupling estimate is REPORTED, NOT ENFORCED, and the reason is honesty: it rests on a
few fF/mm of edge coupling over a plane 0.2 mm down, which is right to a factor of two at
best. A threshold on it would be a threshold on the guess. The geometry it comes from is
what carries the limit.
"""
from __future__ import annotations

import collections
import math
import sys

import wx

wx.DisableAsserts()
import pcbnew  # noqa: E402

BORDER = -19.0
CLR = 0.15              # plane-to-via clearance -> antipad radius = via/2 + CLR
MIN_LED_GAP = 0.50      # summing node to LED copper
MAX_LOOP_MM2 = 5.0      # op-amp + Rf + Cf bounding box
MIN_PLANE_WEB = 0.15    # between two antipads, = the fab clearance itself
MAX_MID_OHM = 5.0       # the reference's end-to-end series resistance

# For the reported estimate only. A 0402-scale pair over a plane 0.2 mm down couples a few
# fF per mm at these spacings.
F_CARRIER = 48e3
V_LED = 1.5             # fundamental at the switched anode
C_PER_MM = 3e-15
I_SIGNAL = 143e-9       # the thin string's photocurrent, optical.py's own figure


def _load(path):
    if not path.endswith(".kicad_pcb"):
        path += ".kicad_pcb"
    b = pcbnew.LoadBoard(path)
    lx = lambda p: p.x / 1e6 - 100.0
    ly = lambda p: 100.0 - p.y / 1e6
    trk = collections.defaultdict(list)
    via = collections.defaultdict(list)
    pad = collections.defaultdict(dict)
    for t in b.GetTracks():
        n = t.GetNetname()
        if not n:
            continue
        s, e = t.GetStart(), t.GetEnd()
        if t.Type() == pcbnew.PCB_VIA_T:
            via[n].append((lx(s), ly(s), t.GetWidth() / 1e6))
        else:
            trk[n].append((t.GetLayer(), lx(s), ly(s), lx(e), ly(e), t.GetWidth() / 1e6))
    for fp in b.GetFootprints():
        for q in fp.Pads():
            n = q.GetNetname()
            if n:
                p = q.GetPosition()
                pad[n]["%s.%s" % (fp.GetReference(), q.GetNumber())] = (lx(p), ly(p))
    return trk, via, pad


def _pt_seg(px, py, x0, y0, x1, y1):
    dx, dy = x1 - x0, y1 - y0
    l2 = dx * dx + dy * dy
    t = 0.0 if l2 == 0 else max(0.0, min(1.0, ((px - x0) * dx + (py - y0) * dy) / l2))
    return math.hypot(px - (x0 + t * dx), py - (y0 + t * dy))


def _near_len(seg, others, within, step=0.05):
    """(length of `seg` running within `within` of any of `others`, closest approach)."""
    L = math.hypot(seg[3] - seg[1], seg[4] - seg[2])
    k = max(2, int(L / step))
    close, best = 0, float("inf")
    for i in range(k + 1):
        x = seg[1] + (seg[3] - seg[1]) * i / k
        y = seg[2] + (seg[4] - seg[2]) * i / k
        d = min(_pt_seg(x, y, o[1], o[2], o[3], o[4]) - seg[5] / 2 - o[5] / 2
                for o in others)
        best = min(best, d)
        if d < within:
            close += 1
    return close * L / (k + 1), best


def main(argv):
    trk, via, pad = _load(argv[1] if len(argv) > 1 else "elec/out/optical")
    bad = []

    # 1 -- the summing node against the LED's switched current
    led = [s for n, v in trk.items() if n.startswith("LED_") for s in v]
    run, gap = 0.0, float("inf")
    chans = [n for n in trk if n.startswith("TIA_IN_")]
    for n in chans:
        for s in trk[n]:
            r, g = _near_len(s, led, 1.5)
            run += r
            gap = min(gap, g)
    cc = C_PER_MM * run / max(1, len(chans))
    inj = 2 * math.pi * F_CARRIER * cc * V_LED
    print("1. summing node: %.3f mm to LED copper, %.2f mm of it within 1.5 mm (%d ch)"
          % (gap, run, len(chans)))
    print("   estimate ~%.1f fF per channel -> %.2f nA at the carrier, %.1f%% of the thin "
          "string's %.0f nA" % (cc * 1e15, inj * 1e9, 100 * inj / I_SIGNAL, I_SIGNAL * 1e9))
    print("   (IN PHASE with the lock-in reference, so it reads as signal rather than as "
          "noise -- an offset the at-rest calibration removes, not a noise floor)")
    if gap < MIN_LED_GAP:
        bad.append("summing node is %.3f from LED copper, floor %.2f" % (gap, MIN_LED_GAP))

    # 2 -- the feedback loop
    loops = []
    for i in range(1, 11):
        for h in "AB":
            pts = []
            for net in ("TIA_IN_%d%s" % (i, h), "TIA_OUT_%d%s" % (i, h)):
                for k, v in pad.get(net, {}).items():
                    ref, pin = k.split(".")
                    if ref.startswith(("Rf", "Cf")) or \
                       (ref.startswith("U2") and pin in ("1", "2", "6", "7")):
                        pts.append(v)
            if len(pts) < 4:
                continue
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            loops.append(((max(xs) - min(xs)) * (max(ys) - min(ys)), "%d%s" % (i, h)))
    if loops:
        loops.sort()
        print("2. feedback loop: %.2f .. %.2f mm2 over %d channel(s) (worst %s)"
              % (loops[0][0], loops[-1][0], len(loops), loops[-1][1]))
        if loops[-1][0] > MAX_LOOP_MM2:
            bad.append("channel %s's feedback loop is %.2f mm2, ceiling %.1f"
                       % (loops[-1][1], loops[-1][0], MAX_LOOP_MM2))

    # 3 -- the plane
    foreign = [(x, y, w / 2 + CLR, n) for n, v in via.items() if n != "GND"
               for (x, y, w) in v if y > BORDER]
    webs = []
    for i in range(len(foreign)):
        for j in range(i + 1, len(foreign)):
            a, c = foreign[i], foreign[j]
            webs.append((math.hypot(a[0] - c[0], a[1] - c[1]) - a[2] - c[2], a, c))
    webs.sort()
    cut = [w for w in webs if w[0] <= 0]
    print("3. In1.Cu plane: %d foreign via(s) north of the border, thinnest web %.3f mm, "
          "%d cut(s)" % (len(foreign), webs[0][0] if webs else float("nan"), len(cut)))
    if webs and webs[0][0] < MIN_PLANE_WEB:
        bad.append("the plane necks to %.3f mm between %s and %s at %.2f %.2f"
                   % (webs[0][0], webs[0][1][3], webs[0][2][3],
                      webs[0][1][0], webs[0][1][1]))

    # 4 -- MID
    rsq = lambda layer: 0.494 if layer in (0, 31) else 0.988   # 1 oz outer, 0.5 oz inner
    res = sum(math.hypot(s[3] - s[1], s[4] - s[2]) / s[5] * rsq(s[0])
              for s in trk.get("MID", ()))
    print("4. MID: %.1f mm of copper, %d via(s), %.0f mohm end to end"
          % (sum(math.hypot(s[3] - s[1], s[4] - s[2]) for s in trk.get("MID", ())),
             len(via.get("MID", ())), res))
    if res / 1000.0 > MAX_MID_OHM:
        bad.append("MID is %.1f ohm end to end, ceiling %.1f" % (res / 1000.0, MAX_MID_OHM))

    for m in bad:
        print("  FAIL %s" % m)
    print("north half: %s" % ("%d finding(s)" % len(bad) if bad
                              else "the layout does not stand in the signal's way"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
