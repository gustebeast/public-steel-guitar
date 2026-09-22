p = 'src/optical_pickup.py'
s = open(p, encoding='utf-8').read()
a = s.index('''    # ⚠ EACH CELL IS LAID PIN-SIDE BY PIN-SIDE, NOT AS A GRID.''')
b = s.index('''    # ---- 3b/3b-i/3d ARE GONE''')
new = '''    # ⚠ EACH CELL IS LAID PIN BY PIN, OFF THE PLACED PART'S OWN PAD COORDINATES. Two
    # layouts came before this one and both lost the cells: a grid of caps under the part
    # (101 unconnected), then caps on the right SIDES but in the wrong ORDER along each
    # side (59) -- IN1P's cap at the far end from IN1P, DREG's under IOVDD, and a solid
    # row of caps under the three SAI pins with no way out between them. The part is
    # turned 180, which puts (relative to its centre, read back through pcbnew):
    #   +X side  pin 1 AVDD y-1.25, 2 AREG -0.75, 3 VREF -0.25, 4 AVSS, 6 IN1P +1.25
    #   +Y side  pins 7..12 = IN1M +1.25, IN2P +0.75, IN2M +0.25, IN3P -0.25, IN3M -0.75,
    #            IN4P -1.25; pin 13 IN4M on the -X side at y +1.25
    #   -Y side  19 IOVDD x-1.25, 21 SDOUT -0.25, 22 BCLK +0.25, 23 FSYNC +0.75, 24 DREG +1.25
    #   -X side  SHDNZ, address straps, I2C -- nothing, it is the routing side
    # and every capacitor sits at its own pin's coordinate. The eight input couplings
    # (INxP from the TIA, INxM to GND: SBAS993B Fig. 31) take two rows on end above the
    # part -- the INxM caps of pins 7/9/11 in the far row, each in the gap between two
    # near-row caps, directly above its pin -- and the bottom row leaves a 1.8 mm corridor
    # at x -0.6..+1.1 for the three SAI lines.
    _cx0 = COMPUTE_X0 + EDGE_KEEP
    _cx1 = _part_x("U6") - CRTYD[_MCU_PKG][0] / 2 - CRTYD_GAP
    _q, _c = CRTYD["WQFN-24"][0], CRTYD["0402"]          # 5.26; (1.95, 1.03)
    _rx = _q / 2 + CRTYD_GAP + _c[0] / 2 + 0.35          # right column, 0.35 clear of the corners
    _cw = _q / 2 + 2.12 + _c[1] / 2 + _rx + _c[0] / 2 - _q / 2 + _q / 2   # -2.12-0.52 .. _rx+0.98
    _cw = (2.12 + _c[1] / 2) + (_rx + _c[0] / 2)
    _cgap = ((_cx1 - _cx0) - 3 * _cw) / 2
    assert _cgap >= CRTYD_GAP - 1e-9, (
        "the converter cells need %.2f mm across and the annulus -X of U6 is %.2f"
        % (3 * _cw + 2 * CRTYD_GAP, _cx1 - _cx0))
    _near = 3.75                                           # near input row / bottom row, |y|
    _far = _near + _c[0] + CRTYD_GAP                       # far input row
    _ch = (_far + _c[0] / 2) + (_near + _c[0] / 2)
    _cy_top = _part_y("U6") + CRTYD[_MCU_PKG][1] / 2
    _cy_gap = CRTYD[_MCU_PKG][1] - 2 * _ch
    assert _cy_gap >= 0, "two converter cells do not fit beside U6 (%.2f short)" % -_cy_gap

    def _cell(col, row):
        """The part's centre for a cell."""
        return (_cx0 + col * (_cw + _cgap) + 2.12 + _c[1] / 2,
                _cy_top - row * (_ch + _cy_gap) - _far - _c[0] / 2)

    for k in range(5):
        qx, qy = _cell(k % 3, k // 3)
        t = k + 1
        add("U%d" % (14 + k), "audio ADC -- TLV320ADC3140, 4 ch, quad U%d's outputs" % t,
            "WQFN-24", qx, qy, 180.0)
        for ref, dx, dy in (("Cm%d4" % t, -2.12, _near), ("Ci%d4" % t, -0.94, _near),
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
            add(ref, "ADC supply / reference bypass", "0402", qx + _rx, qy + dy)
    qx, qy = _cell(2, 1)
    for m, (ref, desc) in enumerate((("R50", "I2C2 SCL pull-up"), ("R51", "I2C2 SDA pull-up"),
                                     ("R52", "I2C4 SCL pull-up"), ("R53", "I2C4 SDA pull-up"),
                                     ("R54", "ADC SHDNZ pull-down -- converters off in reset"))):
        add(ref, desc, "0402", qx - 1.5 + (m % 3) * (_c[0] + CRTYD_GAP),
            qy + _far - (m // 3) * (_c[1] + CRTYD_GAP))

'''
s = s[:a] + new + s[b:]
s = s.replace('''    ("Cm",   ("0402 X7R MLCC",   "BASIC",    0.002, "audio ADC shared INxM coupling to MID, "
                                                    "100 nF: one per converter, all four INxM")),''',
              '''    ("Cm",   ("0402 C0G MLCC",   "BASIC",    0.004, "audio ADC INxM coupling to GND, 10 nF C0G "
                                                    "(SBAS993B Fig. 31, single-ended AC-coupled)")),''')
open(p, 'w', encoding='utf-8').write(s)

p = 'elec/optical.py'
s = open(p, encoding='utf-8').read()
o = '''    adc_inm = [Net("ADC%d_INM" % (k + 1)) for k in range(5)]
    for k in range(5):
        cm = _c("Cm%d" % (k + 1), "100nF", "MID -> U%d IN1M..IN4M (shared reference)" % (14 + k))
        mid += cm[1]
        adc_inm[k] += cm[2]
'''
assert s.count(o) == 1
s = s.replace(o, '')
o = '''        # ⚠ ONE INxM COUPLING PER CONVERTER, NOT FOUR: all four INxM pins share a node,
        # AC-grounded to MID by one 100 nF (33 ohm at the 48 kHz carrier, against the pins'
        # 20 k each). The node carries no signal -- it is the reference -- so sharing it
        # couples nothing between channels, and it took 15 parts out of cells that could
        # not route.
        adc_inm[k] += adcs[k][5 + 2 * s_in]'''
assert s.count(o) == 1
s = s.replace(o, '''        # INxM: SINGLE-ENDED AC-COUPLED, TI's Figure 31 -- the pin grounded through its
        # own 10 nF. (A shared INxM node to MID was tried, 2026-09-21: the four INxM pins
        # alternate with the INxP pins at 0.5 mm pitch, so joining them needs a via per
        # pin inside a crowded cell, and it was the cells' worst net. MID's own noise is
        # a buffered reference's; rejecting it was never worth an unroutable cell.)
        neg = Net("ADC%d_IN%dM" % (k + 1, s_in))
        cm = _c("Cm%d%d" % (k + 1, s_in), "10nF C0G", "U%d IN%dM -> GND" % (14 + k, s_in))
        neg += cm[1], adcs[k][5 + 2 * s_in]
        gnd += cm[2]''')
s = s.replace('''# section order (see SEC below), differential and AC-coupled: INxP from the TIA output
# (10 nF C0G each), all four INxM from MID through one shared 100 nF''',
              '''# section order (see SEC below), single-ended AC-coupled (SBAS993B Fig. 31): INxP from the
# TIA output through 10 nF C0G, INxM to GND through its own 10 nF C0G''')
open(p, 'w', encoding='utf-8').write(s)
print('ok')
