def edit(p, pairs):
    s = open(p, encoding='utf-8').read()
    for o, n in pairs:
        assert s.count(o) == 1, (p, o[:80], s.count(o))
        s = s.replace(o, n)
    open(p, 'w', encoding='utf-8').write(s)


edit('src/optical_pickup.py', [
    ('''CELL_FAN = {"IN4M": -2.70, "IN4P": -1.50,''', '''CELL_FAN = {"IN4M": -2.30, "IN4P": -1.50,'''),
    ('''    _rx = _q / 2 + CRTYD_GAP + _c[0] / 2                  # the +X column
    _cw = (2.70 + _c[1] / 2) + (_rx + _c[0] / 2)''',
     '''    # ⚠ NARROW CELLS, SO THE ROUTING SIDE HAS A CHANNEL (2026-09-22). Each part's -X side
    # (SHDNZ, the address straps, SCL, SDA) faced the next cell's +X column across ~0.5 mm,
    # and that column's ground vias filled the gap: SHDNZ failed on all five parts. The +X
    # column is now two caps ON END beside their pins (AREG, VREF) with AVDD's cap moved to
    # the bottom row, and IN4M's cap went to the far row -- 1.3 mm off every cell, so the
    # channels between cells open from ~0.5 to ~2.5 mm.
    _rx = _q / 2 + CRTYD_GAP + _c[1] / 2                  # the +X column, caps on end
    _left = -CELL_FAN["IN4M"] + _c[1] / 2                 # IN4M's far cap is the -X extreme
    _cw = _left + (_rx + _c[1] / 2)'''),
    ('''        return (_cx0 + col * (_cw + _cgap) + 2.70 + _c[1] / 2,''',
     '''        return (_cx0 + col * (_cw + _cgap) + _left,'''),
    ('''        for ref, dx, dy, rot in (("Cm%d4" % t, CELL_FAN["IN4M"], _near, 90.0),''',
     '''        for ref, dx, dy, rot in (("Cm%d4" % t, CELL_FAN["IN4M"], _far, 90.0),'''),
    ('''                                 ("Cs%d8" % t, -1.25, -_near, 270.0),
                                 ("Cs%d6" % t, 1.90, -_near, 270.0)):''',
     '''                                 ("Cs%d8" % t, -1.25, -_near, 270.0),
                                 ("Cs%d6" % t, 1.90, -_near, 270.0),
                                 ("Cs%d1" % t, 3.10, -_near, 270.0),   # AVDD, pin 1 at +X low
                                 # +X column on end: AREG (pin 2, y -0.75) rail pad on top,
                                 # VREF (pin 3, y -0.25) rail pad at the bottom
                                 ("Cs%d3" % t, _rx, -1.20, 270.0),
                                 ("Cs%d5" % t, _rx, 0.90, 90.0)):'''),
    ('''        # +X column at the pins' own heights: AVDD (pin 1, y -1.25), AREG (-0.75), VREF (-0.25)
        for ref, dy in (("Cs%d1" % t, -1.90), ("Cs%d3" % t, -0.72), ("Cs%d5" % t, 0.46)):
            add(ref, "ADC supply / reference bypass", "0402", qx + _rx, qy + dy)
''', ''''''),
])

edit('elec/optical.py', [
    ('''        for name, (px, py) in (("IN1P", (1.96, 1.25)), ("IN4M", (-1.96, 1.25))):
            cx = OP.CELL_FAN[name]
            out.append(("ADC%d_%s" % (k + 1, name), "F.Cu", 0.15,
                        [(ux + px, uy + py), (ux + cx, uy + py), (ux + cx, uy + near)]))''',
     '''        for name, (px, py), row in (("IN1P", (1.96, 1.25), near),
                                    ("IN4M", (-1.96, 1.25), far)):   # IN4M's cap: far row
            cx = OP.CELL_FAN[name]
            out.append(("ADC%d_%s" % (k + 1, name), "F.Cu", 0.15,
                        [(ux + px, uy + py), (ux + cx, uy + py), (ux + cx, uy + row)]))'''),
])
print('ok')
