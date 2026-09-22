def edit(p, pairs):
    s = open(p, encoding='utf-8').read()
    for o, n in pairs:
        assert s.count(o) == 1, (p, o[:80], s.count(o))
        s = s.replace(o, n)
    open(p, 'w', encoding='utf-8').write(s)


edit('src/optical_pickup.py', [
    ('''    _cw = (2.12 + _c[1] / 2) + (_rx + _c[0] / 2)''',
     '''    _cw = (2.70 + _c[1] / 2) + (_rx + _c[0] / 2)'''),
    ('''        return (_cx0 + col * (_cw + _cgap) + 2.12 + _c[1] / 2,''',
     '''        return (_cx0 + col * (_cw + _cgap) + 2.70 + _c[1] / 2,'''),
    ('''        for ref, dx, dy, rot in (("Cm%d4" % t, -2.12, _near, 90.0),
                                 ("Ci%d4" % t, -0.94, _near, 270.0),
                                 ("Ci%d3" % t, 0.24, _near, 270.0),
                                 ("Ci%d2" % t, 1.43, _near, 270.0),
                                 ("Ci%d1" % t, 2.60, _near, 270.0),
                                 ("Cm%d3" % t, -0.35, _far, 90.0),
                                 ("Cm%d2" % t, 0.83, _far, 90.0),
                                 ("Cm%d1" % t, 2.00, _far, 90.0),''',
     '''        # ⚠ THE INPUT FAN IS A GEOMETRY, NOT A SEARCH (2026-09-21). The top pins run
        # 13 (left side) 12 11 10 9 8 7 6 (right side) at 0.5 pitch, alternating INxP/INxM,
        # and the caps for 12/10/8/6 sit in the near row with 11/9/7 threading up between
        # them to the far row. Near caps at 1.2 pitch put every cap within 0.25 of its own
        # pin's x, so the fan only ever WIDENS -- no two traces converge -- and each thread
        # clears the near pads either side by 0.215. With the caps at their earlier,
        # wider-flung positions the paths crossed and the router left 12 of these open.
        # elec/optical.py lays the fan itself ("tracks"), from these same offsets.
        for ref, dx, dy, rot in (("Cm%d4" % t, CELL_FAN["IN4M"], _near, 90.0),
                                 ("Ci%d4" % t, CELL_FAN["IN4P"], _near, 270.0),
                                 ("Ci%d3" % t, CELL_FAN["IN3P"], _near, 270.0),
                                 ("Ci%d2" % t, CELL_FAN["IN2P"], _near, 270.0),
                                 ("Ci%d1" % t, CELL_FAN["IN1P"], _near, 270.0),
                                 ("Cm%d3" % t, CELL_FAN["IN3M"], _far, 90.0),
                                 ("Cm%d2" % t, CELL_FAN["IN2M"], _far, 90.0),
                                 ("Cm%d1" % t, CELL_FAN["IN1M"], _far, 90.0),'''),
    ('''    _near = 3.75                                           # near input row / bottom row, |y|''',
     '''    _near = CELL_NEAR                                      # near input row / bottom row, |y|'''),
    ('''def _members(it):''',
     '''# The converter cells' input fan (see 3e in _parts): cap x per input, relative to the
# converter's centre with the part turned 180. Module-level so elec/optical.py lays the
# fan's copper from the same numbers the caps are placed by.
CELL_FAN = {"IN4M": -2.70, "IN4P": -1.50, "IN3M": -0.90, "IN3P": -0.30,
            "IN2M": 0.30, "IN2P": 0.90, "IN1M": 1.50, "IN1P": 2.10}
CELL_NEAR = 3.75                                 # near-row cap centre above the part's centre
CELL_FAR = CELL_NEAR + 1.95 + 0.15               # far row (0402 on end + CRTYD_GAP)


def _members(it):'''),
])

edit('elec/optical.py', [
    ('''    # AVSS -> EP, one per converter.''',
     '''    # THE CONVERTERS' INPUT FAN, laid rather than routed: from each top pin straight up to
    # its coupling cap's pin-side pad, widening by at most 0.25 -- see CELL_FAN in
    # src/optical_pickup.py for why the router could not find these (12 of 28 open).
    # Pin x (part turned 180): 12 -1.25, 11 -0.75, 10 -0.25, 9 +0.25, 8 +0.75, 7 +1.25 at
    # y +1.96; pin 6 (IN1P) at (+1.96, +1.25), pin 13 (IN4M) at (-1.96, +1.25). A near cap's
    # pin-side pad centres 0.48 below its centre, a far cap's likewise.
    # AVSS -> EP, one per converter.'''),
    ('''               for k in range(5)],''',
     '''               for k in range(5)] + _fan_tracks(),'''),
    ('''def _outline_poly(cx, cy):''',
     '''def _fan_tracks():
    out = []
    near, far = OP.CELL_NEAR - 0.48, OP.CELL_FAR - 0.48
    for k in range(5):
        ux, uy = _placements(CX, CY)["U%d" % (14 + k)][:2]
        for name, pin_x, row in (("IN4P", -1.25, near), ("IN3M", -0.75, far),
                                 ("IN3P", -0.25, near), ("IN2M", 0.25, far),
                                 ("IN2P", 0.75, near), ("IN1M", 1.25, far)):
            cx = OP.CELL_FAN[name]
            d = cx - pin_x
            pts = [(pin_x, 1.96), (pin_x, 2.60), (cx, 2.60 + abs(d)), (cx, row)]
            out.append(("ADC%d_%s" % (k + 1, name), "F.Cu", 0.15,
                        [(ux + x, uy + y) for x, y in pts]))
        for name, (px, py) in (("IN1P", (1.96, 1.25)), ("IN4M", (-1.96, 1.25))):
            cx = OP.CELL_FAN[name]
            out.append(("ADC%d_%s" % (k + 1, name), "F.Cu", 0.15,
                        [(ux + px, uy + py), (ux + cx, uy + py), (ux + cx, uy + near)]))
    return out


def _outline_poly(cx, cy):'''),
])
print('ok')
