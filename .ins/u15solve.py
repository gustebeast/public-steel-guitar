"""Find a clear pre-laid haul for U15's four inputs, and print it as optical.py tracks.

Only the LONG HAUL is laid. The last few millimetres into Ci2x are left to the router,
because that is the one part it already does successfully -- U16/17/18's identical cells
route their coupling caps every time. What it cannot do is discover a 40 mm journey across
the board for four nets at once, which is the same thing +3V3D needed a trunk for."""
import json
import itertools

d = json.load(open('.ins/board_dump.json'))
PADS = [(p[0][0], p[0][1], p[1], p[2], p[3], p[4]) for p in d['pads']]
CLR = 0.40


def hit(seg, net):
    (x0, y0), (x1, y1) = seg
    for px, py, w, h, pnet, ref in PADS:
        if pnet == net:
            continue
        hw, hh = w / 2 + CLR, h / 2 + CLR
        if abs(x0 - x1) < 1e-9:
            if abs(px - x0) <= hw and min(y0, y1) - hh <= py <= max(y0, y1) + hh:
                return ref
        else:
            if abs(py - y0) <= hh and min(x0, x1) - hw <= px <= max(x0, x1) + hw:
                return ref
    return None


def clear(pts, net):
    return all(hit(s, net) is None for s in zip(pts, pts[1:]))


NETS = (("TIA_OUT_3A", "Rf21", "Ci21"), ("TIA_OUT_3B", "Rf22", "Ci22"),
        ("TIA_OUT_4A", "Rf23", "Ci23"), ("TIA_OUT_4B", "Rf24", "Ci24"))
ESC_X = [round(-16.2 + 0.4 * i, 2) for i in range(26)]     # lanes in the clear corridor
BAND_Y = [round(74.8 + 0.4 * i, 2) for i in range(16)]     # lanes in the clear band
ESC_Y = [round(30.0 + 0.4 * i, 2) for i in range(40)]      # where to leave the column

used_x, used_y, out = set(), set(), []
for net, sref, dref in NETS:
    s = [p for p in PADS if p[5] == sref and p[4] == net][0]
    t = [p for p in PADS if p[5] == dref and p[4] == net][0]
    best = None
    for ey, ex, by in itertools.product(ESC_Y, ESC_X, BAND_Y):
        if ex in used_x or by in used_y:
            continue
        pts = [(s[0], s[1]), (s[0], ey), (ex, ey), (ex, by), (t[0], by)]
        if clear(pts, net):
            best = (pts, ex, by)
            break
    if best is None:
        print("%-12s NO CLEAR HAUL" % net)
        continue
    pts, ex, by = best
    used_x.add(ex)
    used_y.add(by)
    out.append((net, pts))
    print('%-12s ok  esc_y %.1f  lane_x %.1f  band_y %.1f' % (net, pts[1][1], ex, by))

print()
for net, pts in out:
    print('        ("%s", "F.Cu", 0.15,' % net)
    print('         [%s]),' % ', '.join('(%.2f, %.2f)' % p for p in pts))
