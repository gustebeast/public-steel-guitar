def edit(p, pairs):
    s = open(p, encoding='utf-8').read()
    for o, n in pairs:
        assert s.count(o) == 1, (p, o[:80], s.count(o))
        s = s.replace(o, n)
    open(p, 'w', encoding='utf-8').write(s)


edit('src/optical_pickup.py', [
    ('''    _rx = _q / 2 + CRTYD_GAP + _c[0] / 2 + 0.35          # right column, 0.35 clear of the corners
    _cw = _q / 2 + 2.12 + _c[1] / 2 + _rx + _c[0] / 2 - _q / 2 + _q / 2   # -2.12-0.52 .. _rx+0.98
    _cw = (2.12 + _c[1] / 2) + (_rx + _c[0] / 2)''',
     '''    _rx = _q / 2 + CRTYD_GAP + _c[0] / 2                  # the +X column
    _cw = (2.12 + _c[1] / 2) + (_rx + _c[0] / 2)'''),
    ('''        for ref, dx, dy in (("Cm%d4" % t, -2.12, _near), ("Ci%d4" % t, -0.94, _near),
                            ("Ci%d3" % t, 0.24, _near), ("Ci%d2" % t, 1.43, _near),
                            ("Ci%d1" % t, 2.60, _near),
                            ("Cm%d3" % t, -0.35, _far), ("Cm%d2" % t, 0.83, _far),
                            ("Cm%d1" % t, 2.00, _far),
                            # bottom: IOVDD under pin 19, DREG under pin 24, corridor between
                            ("Cs%d8" % t, -2.12, -_near), ("Cs%d9" % t, -0.94, -_near),
                            ("Cs%d7" % t, 1.30, -_near), ("Cs%d6" % t, 2.48, -_near)):
            add(ref, "ADC input AC coupling" if ref[1] in "im" else "ADC supply bypass",
                "0402", qx + dx, qy + dy, 90.0)
        # +X column, top to bottom: AVDD 1u, VREF, AREG 100n, AREG 10u, AVDD 100n
        for ref, dy in (("Cs%d1" % t, 2.12), ("Cs%d5" % t, 0.94), ("Cs%d4" % t, -0.24),
                        ("Cs%d3" % t, -1.43), ("Cs%d2" % t, -2.60)):
            add(ref, "ADC supply / reference bypass", "0402", qx + _rx, qy + dy)''',
     '''        # ⚠ ROTATION IS WHICH PAD FACES THE PIN. An 0402 at 90 has pad 1 at the BOTTOM, at
        # 270 on top. Every cap here is wired pad 1 = the net nearer the part's pins' far
        # side, so: above the part the input caps (pad 2 = the ADC pin for Ci, pad 1 for Cm)
        # and below it the rail caps (pad 1 = the rail pin) are turned to face the pins.
        for ref, dx, dy, rot in (("Cm%d4" % t, -2.12, _near, 90.0),
                                 ("Ci%d4" % t, -0.94, _near, 270.0),
                                 ("Ci%d3" % t, 0.24, _near, 270.0),
                                 ("Ci%d2" % t, 1.43, _near, 270.0),
                                 ("Ci%d1" % t, 2.60, _near, 270.0),
                                 ("Cm%d3" % t, -0.35, _far, 90.0),
                                 ("Cm%d2" % t, 0.83, _far, 90.0),
                                 ("Cm%d1" % t, 2.00, _far, 90.0),
                                 # bottom: IOVDD under pin 19, DREG beside pin 24, and a 2.5 mm
                                 # corridor between them for SDOUT/BCLK/FSYNC
                                 ("Cs%d8" % t, -1.25, -_near, 270.0),
                                 ("Cs%d6" % t, 1.90, -_near, 270.0)):
            add(ref, "ADC input AC coupling" if ref[1] in "im" else "ADC supply bypass",
                "0402", qx + dx, qy + dy, rot)
        # +X column at the pins' own heights: AVDD (pin 1, y -1.25), AREG (-0.75), VREF (-0.25)
        for ref, dy in (("Cs%d1" % t, -1.90), ("Cs%d3" % t, -0.72), ("Cs%d5" % t, 0.46)):
            add(ref, "ADC supply / reference bypass", "0402", qx + _rx, qy + dy)'''),
])

edit('elec/optical.py', [
    ('''    SEC = {0: (1, 2, 3), 1: (7, 6, 5), 2: (8, 9, 10), 3: (14, 13, 12)}''',
     '''    # ⚠ SECTIONS BY HEIGHT, NOT IN ORDER (2026-09-21). A quad serves two strings, and its
    # four detectors run top to bottom 1A, 1B, 2A, 2B; the SOIC's sections sit A top-left,
    # D top-right, C bottom-right, B bottom-left. Mapped in plain order, 2B -- the lowest
    # detector -- went to D at the TOP, and its summing node and output crossed section
    # C's pins: the pre-laid local nets shorted there. Mapped by height, every detector
    # meets the pins level with it.
    SEC = {0: (1, 2, 3), 1: (14, 13, 12), 2: (8, 9, 10), 3: (7, 6, 5)}'''),
    ('''        for j, (val, net, rtn, fp) in enumerate((
                ("1uF", v3a, gnd, None), ("100nF", v3a, gnd, None),      # AVDD
                ("10uF", areg, gnd, None), ("100nF", areg, gnd, None),    # AREG
                ("1uF", vref, gnd, None),                                  # VREF
                ("10uF", dreg, gnd, None), ("100nF", dreg, gnd, None),    # DREG
                ("10uF", v3d, gnd, None), ("100nF", v3d, gnd, None)),     # IOVDD
                start=1):
            c = _c("Cs%d%d" % (tag, j), val, "U%d supply/reference bypass (SBAS993B Fig 165)"
                   % (14 + k))
            net += c[1]
            rtn += c[2]''',
     '''        # SBAS993B Fig 165 less its four 100 nF: TI parallels 0.1 uF with each bulk part,
        # and here the bulk parts are 0402s already (10 uF 6.3 V X5R, 1 uF) -- the low-ESL
        # package the 100 nF is there to supply. Four fewer parts in each of five cells
        # that could not route with them. Refs keep TI's numbering (Cs2/4/7/9 are the gaps).
        for j, val, net in ((1, "1uF", v3a),            # AVDD
                            (3, "10uF", areg),          # AREG
                            (5, "1uF", vref),           # VREF
                            (6, "10uF", dreg),          # DREG
                            (8, "10uF", v3d)):          # IOVDD
            c = _c("Cs%d%d" % (tag, j), val, "U%d supply/reference bypass (SBAS993B Fig 165)"
                   % (14 + k))
            net += c[1]
            gnd += c[2]'''),
])

edit('.ins/opt_audit.py', [
    ('''SEC = {0: (1, 2, 3), 1: (7, 6, 5), 2: (8, 9, 10), 3: (14, 13, 12)}''',
     '''SEC = {0: (1, 2, 3), 1: (14, 13, 12), 2: (8, 9, 10), 3: (7, 6, 5)}'''),
])
print('ok')
