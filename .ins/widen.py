def edit(p, pairs):
    s = open(p, encoding='utf-8').read()
    for o, n in pairs:
        assert s.count(o) == 1, (p, o[:70], s.count(o))
        s = s.replace(o, n)
    open(p, 'w', encoding='utf-8').write(s)


edit('src/optical_pickup.py', [
    ('''PCB_X0  = BAND_X0 - BAND_CLR                                  # -25.26, strip +X edge
PCB_X1S = BAND_X1 + BAND_CLR                                  # -38.88, strip -X edge''',
     '''# ⚠ THE STRIP IS WIDER THAN THE DECK BAND NOW (user, 2026-09-22): "We have space to add
# some PCB 3.15 +X and as much as we want -X of the optical sensors." The band was the
# binding constraint this whole file was written around, and after the PD15-22B / five-
# converter redesign it was also what stopped the board routing: the triplet's land grew
# 3.45 -> 5.0 across a 13.6 mm strip carrying twenty outputs, MID and the rails.
#   +X: the full 3.15 -- a lane between the detectors' outer pads and the edge.
#   -X: STRIP_GROW_MX. The op-amp columns stay where they are (moving them would lengthen
#       every summing node); the growth is a free lane beyond them for the long TIA
#       outputs and the digital lines to the +Y converters.
# ONLY THE STRIP SECTION GROWS. PCB_X1S stays the wraps' and the tail's -X edge (and the
# endplate pad's), so the strip steps out -X past them; STRIP_X1 is its own -X edge.
STRIP_GROW_PX = 3.15
STRIP_GROW_MX = 6.0
PCB_X0  = BAND_X0 - BAND_CLR + STRIP_GROW_PX                  # -22.11, strip +X edge
PCB_X1S = BAND_X1 + BAND_CLR                                  # -38.88, wraps' / tail's -X edge
STRIP_X1 = PCB_X1S - STRIP_GROW_MX                            # -44.88, the strip's own -X edge'''),
    ('''             (Y_TAIL, HEAD_Y0, PCB_X1S, PCB_X0),       # sensing strip, in the deck band''',
     '''             (Y_TAIL, HEAD_Y0, STRIP_X1, PCB_X0),      # sensing strip (wider than the band)'''),
    ('''    corners = [(PCB_X0, HEAD_Y0),              # head -> strip, +X side
               (PCB_X0, Y_TAIL)]               # strip -> -Y wrap, +X side''',
     '''    corners = [(PCB_X0, HEAD_Y0),              # head -> strip, +X side
               (PCB_X0, Y_TAIL)]               # strip -> -Y wrap, +X side
    if STRIP_X1 < PCB_X1S - 1e-9:              # the strip steps out -X past both wraps
        corners += [(PCB_X1S, HEAD_Y0), (PCB_X1S, Y_TAIL)]'''),
    ('''    if PCB_X1S < BAND_X1 or PCB_X0 > BAND_X0:
        raise AssertionError(''',
     '''    if STRIP_X1 < BAND_X1 - STRIP_GROW_MX - 1e-9 or PCB_X0 > BAND_X0 + STRIP_GROW_PX + 1e-9:
        raise AssertionError('''),
])

edit('elec/optical.py', [
    ('''    # Walk the +X side from -Y to +Y, then the -X side back down. The -X edge is one
    # straight line end to end (see COMPUTE_X0 in the CAD), so it contributes just its
    # two extreme corners -- emitting a point per band there would put collinear
    # duplicates on Edge.Cuts, which KiCad reports as a self-intersecting outline.
    pts = []
    for y0, y1, _x1, x0 in bands:
        if not pts or pts[-1] != (x0, y0):
            pts.append((x0, y0))
        pts.append((x0, y1))
    x_left = min(b[2] for b in bands)
    pts += [(x_left, bands[-1][1]), (x_left, bands[0][0])]
    return [(x - cx, y - cy) for x, y in pts]''',
     '''    # Walk the +X side from -Y to +Y, then the -X side back down, one corner pair per band
    # on each side. Since the strip widened -X (2026-09-22) the -X edge is no longer one
    # straight line. Collinear points (a band whose edge continues its neighbour's) are
    # dropped: KiCad reads collinear duplicates on Edge.Cuts as a self-intersection.
    pts = []
    for y0, y1, _x1, x0 in bands:
        pts += [(x0, y0), (x0, y1)]
    for y0, y1, x1, _x0 in reversed(bands):
        pts += [(x1, y1), (x1, y0)]
    out = []
    for p in pts:
        if not out or out[-1] != p:
            out.append(p)
    if out[0] == out[-1]:
        out.pop()
    changed = True
    while changed:                              # drop points in the middle of a straight run
        changed = False
        for i in range(len(out)):
            a, b, c = out[i - 1], out[i], out[(i + 1) % len(out)]
            if (abs(a[0] - b[0]) < 1e-9 and abs(b[0] - c[0]) < 1e-9) or \\
               (abs(a[1] - b[1]) < 1e-9 and abs(b[1] - c[1]) < 1e-9):
                out.pop(i)
                changed = True
                break
    return [(x - cx, y - cy) for x, y in out]'''),
])
print('ok')
