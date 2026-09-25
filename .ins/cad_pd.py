p = 'src/optical_pickup.py'
s = open(p, encoding='utf-8').read()


def rep(o, n, cnt=1):
    global s
    assert s.count(o) == cnt, (o[:90], s.count(o))
    s = s.replace(o, n)


# 1. packages
rep('''    "0805OPT":  (2.00, 1.25, 0.85),   # optoelectronic 0805
''', '''    "0805OPT":  (2.00, 1.25, 0.85),   # optoelectronic 0805 -- the IR17-21C emitters
    "PD15":     (3.30, 2.80, 1.10),   # Everlight PD15-22B/TR8 photodiode (DTD-152-002 p.2)
    "WQFN-24":  (4.00, 4.00, 0.80),   # TI RTW, TLV320ADC3140 (SBAS993B mechanical)
''')
rep('''    "0805OPT":  (3.45, 1.99),
''', '''    "0805OPT":  (3.45, 1.99),
    "PD15":     (5.00, 3.30),   # elec/footprints/Steel.pretty/Everlight_PD15-22B
    "WQFN-24":  (5.26, 5.26),   # KiCad Texas_RTW_WQFN-24-1EP_4x4mm_P0.5mm_EP2.7x2.7mm
''')
rep('''PD_PKG  = PKG["0805OPT"]''', '''PD_PKG  = PKG["PD15"]''')

# 2. PD_DY / PD_X / slots
rep('''PD_DY = 1.6                                      # detector offset either side of the
                                                 # string; scaled to the SHORT standoff''',
    '''# ⚠ 2026-09-21: THE DETECTOR IS NOW THE EVERLIGHT PD15-22B, AND PD_DY FOLLOWS FROM ITS BODY.
# The VEMD4110X01 had 95 in stock against 20 per instrument; the PD15-22B has 11k, peaks at
# 940 nm (the emitter's own wavelength), gives ~3x the photocurrent, and costs a tenth. It
# is 3.3 x 2.8 rather than an 0805, so the triplet cannot stay at 1.6: the same 0.35 body gap
# to the emitter puts the detectors at 2.375. What the note above says 2.0 would have cost
# is paid by widening the aperture instead (SLOT_DY), and it buys something: a longer DIFF
# baseline. Optically the move costs ~25% of the light (line-integrated over the lit
# string, not the point estimate), more than repaid by the part's photocurrent.
PD_GAP = 0.35                                    # emitter body -> detector body, in Y
PD_DY = LED_PKG[1] / 2 + PD_GAP + PD_PKG[1] / 2  # 2.375
# AND IN X THE DETECTORS SIT JUST -X OF THE ROOF'S +X STRIP, not on the emitter's centre
# line. Their 4.5 mm land would otherwise reach the board's +X edge keep-out, and set here
# every detector body lies wholly inside its aperture notch (x1 < APER_X1): the part is
# 1.1 tall against the emitter's 0.85, so it stands 0.25 above the emitter face and only
# 0.05 under the roof's underside -- it must never pass UNDER roof material, including
# while the board slides +X into place along the notches. 0.36 mm off the emitter's line
# is nothing optically.
PD_X = (BAND_X0 - D.MIN_WALL_2P) - 0.05 - PD_PKG[0] / 2      # -28.36''')
rep('''SLOT_DY   = 5.0                                  # ...and in Y (triplet spans +-2.225)''',
    '''SLOT_DY   = 7.6                                  # ...and in Y: the PD15 triplet spans
                                                 # +-3.775; the teeth left between
                                                 # apertures are PITCH - 7.6 = 1.76 (>=1.6)''')

# 3. the sensing row
rep('''        add("PD%dA" % n, "PIN photodiode, Vishay VEMD4110X01 (daylight filter), +Y", "0805OPT", SENSE_X, sy + PD_DY)
        add("PD%dB" % n, "PIN photodiode, Vishay VEMD4110X01 (daylight filter), -Y", "0805OPT", SENSE_X, sy - PD_DY)''',
    '''        add("PD%dA" % n, "PIN photodiode, Everlight PD15-22B (daylight filter), +Y", "PD15", PD_X, sy + PD_DY)
        add("PD%dB" % n, "PIN photodiode, Everlight PD15-22B (daylight filter), -Y", "PD15", PD_X, sy - PD_DY)''')
rep('''        add("R%d" % n, "LED current-set (per-string value)", "0603", SENSE_X, sy - PITCH / 2)''',
    '''        # 0402 since the PD15 triplet: an 0603's courtyard reaches the detector's
        add("R%d" % n, "LED current-set (per-string value)", "0402", SENSE_X, sy - PITCH / 2)''')

# 4. MCU description
rep('''    add("U6", "MCU -- STM32H743IIT6, 20x 16-bit ADC ch, USB OTG_HS via ULPI", _MCU_PKG,''',
    '''    add("U6", "MCU -- STM32H743IIT6, 5 SAI TDM lanes from the audio ADCs, USB OTG_HS via ULPI", _MCU_PKG,''')

# 5. the converters, in the annulus -X of the MCU
rep('''    # ---- 3b/3b-i/3d ARE GONE: THE MAGNETIC PATH LEFT THIS BOARD (user, 2026-09-15) ----''',
    '''    # ---- 3e. THE AUDIO CONVERTERS, in the escape annulus -X of the MCU (2026-09-21) ----
    # Five TLV320ADC3140s, one per quad (see elec/optical.py for why the MCU's own ADCs
    # went). They go in the 25 x 27 mm of empty board -X of U6 -- the annulus the twenty
    # analog nets used to cross to reach the LQFP's pins. Now those nets END here, a
    # converter sits where they arrive, and only seven SAI lines and two I2C pairs continue
    # to the MCU. Each converter travels with its seventeen capacitors (nine supply/reference,
    # SBAS993B Figure 165, and eight AC couplings), laid as one cell: the part on top, the
    # capacitors in rows of four under it. Three cells across, two down; the sixth cell
    # holds the I2C pulls and the SHDNZ pull-down.
    _cx0 = COMPUTE_X0 + EDGE_KEEP
    _cx1 = _part_x("U6") - CRTYD[_MCU_PKG][0] / 2 - CRTYD_GAP
    _cw = 4 * CRTYD["0402"][0] + 3 * CRTYD_GAP
    _cgap = ((_cx1 - _cx0) - 3 * _cw) / 2
    assert _cgap >= CRTYD_GAP - 1e-9, (
        "the converter cells need %.2f mm across and the annulus -X of U6 is %.2f"
        % (3 * _cw + 2 * CRTYD_GAP, _cx1 - _cx0))
    _ch = CRTYD["WQFN-24"][1] + CRTYD_GAP + 5 * (CRTYD["0402"][1] + CRTYD_GAP)
    _cy_top = _part_y("U6") + CRTYD[_MCU_PKG][1] / 2
    _cy_gap = CRTYD[_MCU_PKG][1] - 2 * _ch
    assert _cy_gap >= 0, "two converter cells do not fit beside U6 (%.2f short)" % -_cy_gap

    def _cell(col, row):
        return _cx0 + col * (_cw + _cgap), _cy_top - row * (_ch + _cy_gap)

    for k in range(5):
        cx, cy = _cell(k % 3, k // 3)
        add("U%d" % (14 + k), "audio ADC -- TLV320ADC3140, 4 ch, quad U%d's outputs" % (k + 1),
            "WQFN-24", cx + _cw / 2, cy - CRTYD["WQFN-24"][1] / 2)
        caps = (["Cs%d%d" % (k + 1, j) for j in range(1, 10)]
                + ["Ci%d%d" % (k + 1, c) for c in range(1, 5)]
                + ["Cm%d%d" % (k + 1, c) for c in range(1, 5)])
        y = cy - CRTYD["WQFN-24"][1] - CRTYD_GAP - CRTYD["0402"][1] / 2
        for m, ref in enumerate(caps):
            col, row = m % 4, m // 4
            desc = ("ADC supply / reference bypass" if ref.startswith("Cs")
                    else "ADC input AC coupling, C0G")
            add(ref, desc, "0402",
                cx + CRTYD["0402"][0] / 2 + col * (CRTYD["0402"][0] + CRTYD_GAP),
                y - row * (CRTYD["0402"][1] + CRTYD_GAP))
    cx, cy = _cell(2, 1)
    for m, (ref, desc) in enumerate((("R50", "I2C2 SCL pull-up"), ("R51", "I2C2 SDA pull-up"),
                                     ("R52", "I2C4 SCL pull-up"), ("R53", "I2C4 SDA pull-up"),
                                     ("R54", "ADC SHDNZ pull-down -- converters off in reset"))):
        add(ref, desc, "0402",
            cx + CRTYD["0402"][0] / 2 + (m % 4) * (CRTYD["0402"][0] + CRTYD_GAP),
            cy - CRTYD["0402"][1] / 2 - (m // 4) * (CRTYD["0402"][1] + CRTYD_GAP))

    # ---- 3b/3b-i/3d ARE GONE: THE MAGNETIC PATH LEFT THIS BOARD (user, 2026-09-15) ----''')

# 6. MPN table
rep('''    ("U6",   ("STM32H743IIT6",   "C89597",   10.005, "LQFP176; same die as the ZIT6 (20 ADC ch, "
                                                    "OTG_HS, 2 MB). @10 price. 548 in stock "
                                                    "2026-09-17; the LQFP144 ZIT6 showed 0.")),''',
    '''    ("U6",   ("STM32H743IIT6",   "C89597",   10.005, "LQFP176; same die as the ZIT6 (OTG_HS, "
                                                    "2 MB). @10 price. 335 in stock 2026-09-21. "
                                                    "Its own ADCs are no longer used -- the "
                                                    "five TLV320ADC3140s convert")),''')
rep('''    ("R",    ("0603 thick-film R", "BASIC",  0.003, "per-string LED ballast")),''',
    '''    ("R",    ("0402 thick-film R", "BASIC",  0.002, "per-string LED ballast")),
    ("Cs",   ("0402 X5R MLCC",   "BASIC",    0.004, "audio ADC supply / reference bypass "
                                                    "(1 uF, 10 uF 6.3 V and 100 nF per SBAS993B "
                                                    "Figure 165)")),
    ("Ci",   ("0402 C0G MLCC",   "BASIC",    0.004, "audio ADC input coupling, 10 nF C0G -- "
                                                    "the channel's signal rides a 48 kHz "
                                                    "carrier, so 10 nF into 20 k is ample")),
    ("Cm",   ("0402 C0G MLCC",   "BASIC",    0.004, "audio ADC INxM coupling to MID, 10 nF C0G")),''')
rep('''    ("PD",   ("VEMD4110X01",     "C3211080", 0.58,  "filtered Si PIN, 0.42 mm2, +-55 deg, "
                                                    "740-1040 nm. ZERO BIAS here, so the "
                                                    "numbers that apply are Ik 2.2 uA/(mW/cm2) "
                                                    "and CD 7 pF, not the front page's 2.4 and "
                                                    "2.5 at VR = 5 V. @100+ price; 10 boards = "
                                                    "200 pcs. STOCK 95 on 2026-09-17 -- the ONLY "
                                                    "filtered 0805 PIN at LCSC, so this is a "
                                                    "timing problem with no substitute")),''',
    '''    ("PD",   ("PD15-22B/TR8",    "C161211",  0.067, "Everlight filtered Si PIN, black epoxy "
                                                    "(730-1100 nm), PEAK 940 nm = the emitter's. "
                                                    "Isc 6.5 uA/(mW/cm2) typ, 4.0 min (@875 nm); "
                                                    "6 pF at VR 5 V, zero-bias C not published. "
                                                    "3.3 x 2.8 x 1.1. 11,271 in stock "
                                                    "2026-09-21 (the VEMD4110X01 it replaces had "
                                                    "95, at $0.58)")),''')
rep('''_MPN_EXACT = {r: ("0402 thick-film R", "BASIC", 0.002, "pulls / divider / gate")
              for r in ("R30", "R31", "R32", "R33", "R34", "R35", "R36", "R37", "R38", "R39")}''',
    '''_MPN_EXACT = {r: ("0402 thick-film R", "BASIC", 0.002, "pulls / divider / gate")
              for r in ("R30", "R31", "R32", "R33", "R34", "R35", "R36", "R37", "R38", "R39",
                        "R50", "R51", "R52", "R53", "R54")}
# The five audio converters: exact, because the bare "U" rule is the TIA quad's.
_MPN_EXACT.update({r: ("TLV320ADC3140IRTWT", "C1852021", 3.6456,
                       "TI 4-ch 768 kHz audio ADC, WQFN-24 (RTW). 106 dB SNR (2 Vrms diff). "
                       "306 in stock 2026-09-21; the IRTWR reel (C882863) had 67")
                   for r in ("U14", "U15", "U16", "U17", "U18")})''')
open(p, 'w', encoding='utf-8').write(s)
print('cad ok')
