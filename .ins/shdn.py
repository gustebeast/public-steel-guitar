def edit(p, pairs):
    s = open(p, encoding='utf-8').read()
    for o, n in pairs:
        assert s.count(o) == 1, (p, o[:60], s.count(o))
        s = s.replace(o, n)
    open(p, 'w', encoding='utf-8').write(s)


edit('elec/optical.py', [
    ('''# I2C2: PF0 SDA (16), PF1 SCL (17). SHDNZ for all five on PF2, pulled LOW, so
# the converters sit in hardware shutdown until firmware has the supplies settled
# (SBAS993B 9.2.1.2 step 1).''',
     '''# I2C2: PF0 SDA (16), PF1 SCL (17).
# ⚠ SHDNZ IS TIED TO EACH PART'S OWN IOVDD, NOT DRIVEN BY THE MCU (2026-09-22). As one
# six-terminal net across the cells it failed in every routing -- three layouts, escape vias
# and all. Tied locally it is five private hops: pin 14 -> via -> In2 down the channel ->
# via -> the IOVDD cap's rail pad, all laid (see "tracks"/"vias"). What it costs: TI's
# power-up sequence holds SHDNZ low until AVDD and IOVDD settle (SBAS993B 9.2.1.2 step 1);
# tied high, the parts leave shutdown as IOVDD rises. FIRMWARE MUST THEREFORE ISSUE THE
# SOFTWARE RESET (P0_R1, SW_RESET) over the I2C broadcast once both rails are up, before
# configuring -- that is the documented recovery, and the only one this board keeps.
# Hardware shutdown (the < 1 uA state) is lost; nothing here needs it.'''),
    ('''ADC_SHDN = "PF2"
''', ''''''),
    ('''    adc_shdn = Net("ADC_SHDNZ")
''', ''''''),
    ('''        adc_shdn += u[14]''', '''        v3d += u[14]              # SHDNZ tied high locally -- see THE CONVERTERS'''),
    ('''                                 ("R51", i2c[0][0], v3d, "I2C2 SDA"),
                                 ("R54", adc_shdn, gnd, "SHDNZ pull-down")):''',
     '''                                 ("R51", i2c[0][0], v3d, "I2C2 SDA")):'''),
    ('''    adc_shdn += u6[PIN[ADC_SHDN]]
''', ''''''),
    ('''                         "VCAP1", "VCAP2", ADC_SHDN) + tuple(SAI_CLK.values()) + SAI_SD''',
     '''                         "VCAP1", "VCAP2") + tuple(SAI_CLK.values()) + SAI_SD'''),
    ('''              + [("ADC_SHDNZ", "F.Cu", 0.15,
                  [(_placements(CX, CY)["U%d" % (14 + k)][0] - 1.96,
                    _placements(CX, CY)["U%d" % (14 + k)][1] + 0.75),
                   (_placements(CX, CY)["U%d" % (14 + k)][0] - 2.85,
                    _placements(CX, CY)["U%d" % (14 + k)][1] + 0.75)]) for k in range(5)],
    "vias": [("ADC_SHDNZ", _placements(CX, CY)["U%d" % (14 + k)][0] - 2.85,
              _placements(CX, CY)["U%d" % (14 + k)][1] + 0.75) for k in range(5)],''',
     '''              + _shdn_tracks(),
    "vias": [("+3V3D", _placements(CX, CY)["U%d" % (14 + k)][0] - 2.85,
              _placements(CX, CY)["U%d" % (14 + k)][1] + y) for k in range(5)
             for y in (0.75, -3.27)],'''),
    ('''def _outline_poly(cx, cy):''',
     '''def _shdn_tracks():
    """Each converter's SHDNZ to its own IOVDD: pin 14 (-1.96, +0.75) -> via at (-2.85, +0.75)
    -> In2 down the channel -> via at (-2.85, -3.27) -> the IOVDD cap Cs<k>8's rail pad at
    (-1.25, -3.27). Offsets from the part's centre, part turned 180."""
    out = []
    for k in range(5):
        ux, uy = _placements(CX, CY)["U%d" % (14 + k)][:2]
        out += [("+3V3D", "F.Cu", 0.15, [(ux - 1.96, uy + 0.75), (ux - 2.85, uy + 0.75)]),
                ("+3V3D", "In2.Cu", 0.15, [(ux - 2.85, uy + 0.75), (ux - 2.85, uy - 3.27)]),
                ("+3V3D", "F.Cu", 0.15, [(ux - 2.85, uy - 3.27), (ux - 1.25, uy - 3.27)])]
    return out


def _outline_poly(cx, cy):'''),
])
edit('src/optical_pickup.py', [
    ('''    for m, (ref, desc) in enumerate((("R50", "I2C2 SCL pull-up"), ("R51", "I2C2 SDA pull-up"),
                                     ("R54", "ADC SHDNZ pull-down -- converters off in reset"))):''',
     '''    for m, (ref, desc) in enumerate((("R50", "I2C2 SCL pull-up"), ("R51", "I2C2 SDA pull-up"))):'''),
    ('''                        "R50", "R51", "R54")}''', '''                        "R50", "R51")}'''),
])
edit('BOM.md', [
    ('''| 3 | R50, R51, R54 | I2C2 pull-ups 4k7 ×2 (all five converters share one bus and one address, written together), converter SHDNZ pull-down 100k |''',
     '''| 2 | R50, R51 | I2C2 pull-ups 4k7 ×2 (all five converters share one bus and one address, written together; SHDNZ is tied high at each part and firmware issues the software reset) |'''),
])
edit('.ins/opt_audit.py', [
    ('''    chk(net_of(adc, 14) == "ADC_SHDNZ", "%s SHDNZ" % adc)''',
     '''    chk(net_of(adc, 14) == "+3V3D", "%s SHDNZ not tied to IOVDD" % adc)'''),
    ('''          "I2C2_SCL", "I2C2_SDA", "ADC_SHDNZ", "LED_GATE"):''',
     '''          "I2C2_SCL", "I2C2_SDA", "LED_GATE"):'''),
])
print('ok')
