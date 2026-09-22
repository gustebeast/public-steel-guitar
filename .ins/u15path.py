"""Is there a clear all-F.Cu L-path from each of U15's four sources to its coupling cap?

Pre-laid VIAS are never connected by the router on this board, so any deliberate path has
to stay on one layer end to end. This tests an L (up in y at the source's x, across in x,
up to the pad) against every pad on the board, and reports the first obstacle."""
import json
import sys

d = json.load(open('.ins/board_dump.json'))
PADS = [(p[0][0], p[0][1], p[1], p[2], p[3], p[4]) for p in d['pads']]
CLR = 0.35            # track half-width + clearance


def blocked(seg, net):
    (x0, y0), (x1, y1) = seg
    out = []
    for px, py, w, h, pnet, ref in PADS:
        if pnet == net:
            continue
        hw, hh = w / 2 + CLR, h / 2 + CLR
        if x0 == x1:
            if abs(px - x0) <= hw and min(y0, y1) - hh <= py <= max(y0, y1) + hh:
                out.append((ref, round(px, 1), round(py, 1)))
        else:
            if abs(py - y0) <= hh and min(x0, x1) - hw <= px <= max(x0, x1) + hw:
                out.append((ref, round(px, 1), round(py, 1)))
    return out


for net, src_ref, dst_ref in (("TIA_OUT_3A", "Rf21", "Ci21"), ("TIA_OUT_3B", "Rf22", "Ci22"),
                              ("TIA_OUT_4A", "Rf23", "Ci23"), ("TIA_OUT_4B", "Rf24", "Ci24")):
    src = [p for p in PADS if p[5] == src_ref and p[4] == net]
    dst = [p for p in PADS if p[5] == dst_ref and p[4] == net]
    if not src or not dst:
        print("%-12s no pad (%s/%s)" % (net, bool(src), bool(dst)))
        continue
    sx, sy = src[0][0], src[0][1]
    dx, dy = dst[0][0], dst[0][1]
    for lane in [float(v) for v in sys.argv[1:]] or [76.0]:
        segs = [((sx, sy), (sx, lane)), ((sx, lane), (dx, lane)), ((dx, lane), (dx, dy))]
        hits = [h for s in segs for h in blocked(s, net)]
        print("%-12s (%6.2f,%6.2f) -> (%6.2f,%6.2f) via y=%5.1f : %s"
              % (net, sx, sy, dx, dy, lane,
                 "CLEAR" if not hits else "%d hit(s) %s" % (len(hits), hits[:4])))

# ── WHAT THIS FOUND (2026-09-22) ─────────────────────────────────────────────
# U15's four inputs fail every route because nothing lays them; the board is not actually
# short of room for them. Measured on the 9-unconnected board, in BOARD-LOCAL coords:
#   * a VERTICAL corridor at x -16.5 .. -5.5 is completely clear over y 45..83 (11 mm, and
#     four lanes at 0.3 pitch need 1.2)
#   * a HORIZONTAL band at y 74.4 .. 81.2 is clear right across x -28 .. -6 (6.8 mm)
# So the long haul from the strip to the +Y wrap is open. What blocks a naive L is only the
# two ENDS: leaving the source runs into that op-amp column's own Rf/Cf stack and the sensor
# row (D4/PD4B), and arriving at Ci21-24 from below runs over Cm21-24, which sit 1.6 mm
# under them. Both ends need a proper FAN -- four staggered approaches -- not a straight L.
# elec/optical.py already has _fan_tracks() doing exactly that for the converter inputs;
# this is the same job at the other end of the run.
