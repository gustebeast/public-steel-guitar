p = 'src/optical_pickup.py'
s = open(p, encoding='utf-8').read()
a = s.index('''    # to the MCU. Each converter travels with its seventeen capacitors (nine supply/reference,''')
b = s.index('''    # ---- 3b/3b-i/3d ARE GONE''')
new = '''    # to the MCU.
    # ⚠ EACH CELL IS LAID PIN-SIDE BY PIN-SIDE, NOT AS A GRID. The first layout put every
    # capacitor in rows of three under the part, which walled the pins off from the caps
    # they serve: 101 unconnected, nearly all of them inside these cells. Now the part is
    # turned 180 so its analog side (pins 6-13, the inputs) faces +Y, where the twenty TIA
    # nets arrive from the strip, and each group of capacitors sits on the side of the
    # package whose pins it serves (SBAS993B Pin Functions; KiCad numbers pin 1 top-left,
    # counter-clockwise, and 180 turns the left side to the right):
    #   +Y  (pins 6-13 )  four INxP couplings + ONE shared INxM coupling, standing on end
    #   +X  (pins 1-6  )  AVDD 1 uF + 100 nF, AREG 10 uF + 100 nF, VREF 1 uF
    #   -Y  (pins 19-24)  DREG 10 uF + 100 nF, IOVDD 10 uF + 100 nF, standing on end
    #   -X  (pins 13-18)  SHDNZ, address straps, I2C -- nothing, it is the routing side
    # Two rows of three cells with the full leftover height BETWEEN the rows, so the lower
    # row's inputs have an 8 mm corridor to arrive through. The sixth cell holds the pulls.
    _cx0 = COMPUTE_X0 + EDGE_KEEP
    _cx1 = _part_x("U6") - CRTYD[_MCU_PKG][0] / 2 - CRTYD_GAP
    _q, _c = CRTYD["WQFN-24"][0], CRTYD["0402"]          # 5.26; (1.95, 1.03)
    _cw = _q + CRTYD_GAP + _c[0]
    _cgap = ((_cx1 - _cx0) - 3 * _cw) / 2
    assert _cgap >= CRTYD_GAP - 1e-9, (
        "the converter cells need %.2f mm across and the annulus -X of U6 is %.2f"
        % (3 * _cw + 2 * CRTYD_GAP, _cx1 - _cx0))
    _ch = _c[0] + CRTYD_GAP + _q + CRTYD_GAP + _c[0]
    _cy_top = _part_y("U6") + CRTYD[_MCU_PKG][1] / 2
    _cy_gap = CRTYD[_MCU_PKG][1] - 2 * _ch
    assert _cy_gap >= 0, "two converter cells do not fit beside U6 (%.2f short)" % -_cy_gap

    def _cell(col, row):
        return _cx0 + col * (_cw + _cgap), _cy_top - row * (_ch + _cy_gap)

    _step = _c[1] + CRTYD_GAP                            # one 0402 on end, side by side
    for k in range(5):
        cx, cy = _cell(k % 3, k // 3)
        t = k + 1
        qx, qy = cx + _q / 2, cy - _c[0] - CRTYD_GAP - _q / 2
        add("U%d" % (14 + k), "audio ADC -- TLV320ADC3140, 4 ch, quad U%d's outputs" % t,
            "WQFN-24", qx, qy, 180.0)
        for m, ref in enumerate(["Ci%d%d" % (t, c) for c in range(1, 5)] + ["Cm%d" % t]):
            add(ref, "ADC input AC coupling", "0402",
                cx + _c[1] / 2 + m * _step, cy - _c[0] / 2, 90.0)
        for m, j in enumerate((1, 2, 3, 4, 5)):          # AVDD x2, AREG x2, VREF
            add("Cs%d%d" % (t, j), "ADC supply / reference bypass", "0402",
                cx + _q + CRTYD_GAP + _c[0] / 2, cy - _c[0] - CRTYD_GAP - _c[1] / 2 - m * _step)
        for m, j in enumerate((6, 7, 8, 9)):             # DREG x2, IOVDD x2
            add("Cs%d%d" % (t, j), "ADC supply / reference bypass", "0402",
                cx + _c[1] / 2 + m * _step, cy - _ch + _c[0] / 2, 90.0)
    cx, cy = _cell(2, 1)
    for m, (ref, desc) in enumerate((("R50", "I2C2 SCL pull-up"), ("R51", "I2C2 SDA pull-up"),
                                     ("R52", "I2C4 SCL pull-up"), ("R53", "I2C4 SDA pull-up"),
                                     ("R54", "ADC SHDNZ pull-down -- converters off in reset"))):
        add(ref, desc, "0402",
            cx + _c[0] / 2 + (m % 3) * (_c[0] + CRTYD_GAP),
            cy - _c[1] / 2 - (m // 3) * (_c[1] + CRTYD_GAP))

'''
s = s[:a] + new + s[b:]
s = s.replace('''    ("Cm",   ("0402 C0G MLCC",   "BASIC",    0.004, "audio ADC INxM coupling to MID, 10 nF C0G")),''',
              '''    ("Cm",   ("0402 X7R MLCC",   "BASIC",    0.002, "audio ADC shared INxM coupling to MID, "
                                                    "100 nF: one per converter, all four INxM")),''')
open(p, 'w', encoding='utf-8').write(s)

p = 'elec/optical.py'
s = open(p, encoding='utf-8').read()
o = '''        pos, neg = Net("ADC%d_IN%dP" % (k + 1, s_in)), Net("ADC%d_IN%dM" % (k + 1, s_in))
        ci = _c("Ci%d%d" % (k + 1, s_in), "10nF C0G", "string %d%s -> U%d IN%dP"
                % (i, side, 14 + k, s_in))
        cm = _c("Cm%d%d" % (k + 1, s_in), "10nF C0G", "MID -> U%d IN%dM" % (14 + k, s_in))
        tia_out[(i, side)] += ci[1]
        pos += ci[2], adcs[k][4 + 2 * s_in]
        mid += cm[1]
        neg += cm[2], adcs[k][5 + 2 * s_in]'''
assert s.count(o) == 1
s = s.replace(o, '''        pos = Net("ADC%d_IN%dP" % (k + 1, s_in))
        ci = _c("Ci%d%d" % (k + 1, s_in), "10nF C0G", "string %d%s -> U%d IN%dP"
                % (i, side, 14 + k, s_in))
        tia_out[(i, side)] += ci[1]
        pos += ci[2], adcs[k][4 + 2 * s_in]
        # ⚠ ONE INxM COUPLING PER CONVERTER, NOT FOUR: all four INxM pins share a node,
        # AC-grounded to MID by one 100 nF (33 ohm at the 48 kHz carrier, against the pins'
        # 20 k each). The node carries no signal -- it is the reference -- so sharing it
        # couples nothing between channels, and it took 15 parts out of cells that could
        # not route.
        adc_inm[k] += adcs[k][5 + 2 * s_in]''')
o = '''    # the couplings: quad q's section s -> converter q's input s+1
    for ch in range(20):'''
assert s.count(o) == 1
s = s.replace(o, '''    # the couplings: quad q's section s -> converter q's input s+1
    adc_inm = [Net("ADC%d_INM" % (k + 1)) for k in range(5)]
    for k in range(5):
        cm = _c("Cm%d" % (k + 1), "100nF", "MID -> U%d IN1M..IN4M (shared reference)" % (14 + k))
        mid += cm[1]
        adc_inm[k] += cm[2]
    for ch in range(20):''')
s = s.replace('''# section order (see SEC below), differential and AC-coupled: INxP from the TIA output,
# INxM from MID, 10 nF C0G each''', '''# section order (see SEC below), differential and AC-coupled: INxP from the TIA output
# (10 nF C0G each), all four INxM from MID through one shared 100 nF''')
open(p, 'w', encoding='utf-8').write(s)
print('ok')
