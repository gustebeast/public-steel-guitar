p = 'elec/optical.py'
s = open(p, encoding='utf-8').read()


def rep(o, n, cnt=1):
    global s
    assert s.count(o) == cnt, (o[:90], s.count(o))
    s = s.replace(o, n)


def cut(a_marker, b_marker, new, keep_b=True):
    global s
    a = s.index(a_marker)
    b = s.index(b_marker, a)
    s = s[:a] + new + (s[b:] if keep_b else s[b + len(b_marker):])


# ── docstring
rep('''transimpedance amps turn tens of nanoamps into volts; twenty ADC channels on one
STM32H743 digitise them; firmware forms SUM (the audio) and DIFF (the lateral''',
    '''transimpedance amps turn tens of nanoamps into volts; five four-channel audio
converters (TLV320ADC3140) digitise them and hand the STM32H743 five TDM lanes;
firmware demodulates the 48 kHz emitter carrier, forms SUM (the audio) and DIFF (the lateral''')

# ── pins the converters' buses use
rep('''    "PH0": 29, "PH1": 30,''', '''    "PH0": 29, "PH1": 30,
    # the audio converters' buses -- see THE CONVERTERS below
    "PE3": 2, "PE4": 3, "PE5": 4, "PE6": 5, "PI6": 175, "PD1": 143,
    "PF0": 16, "PF1": 17, "PF2": 18, "PF15": 65,''')

# ── the ADC map essay -> the converter section
cut('# ── THE ADC MAP, and the pair skew it cannot avoid', 'def _r(ref, value, desc, fp=_R_0402):',
    '''# ── THE CONVERTERS: FIVE TLV320ADC3140s, NOT THE MCU'S OWN ADCs (2026-09-21) ──────
# This section used to be ~340 lines on mapping twenty channels onto the H743's three ADCs:
# which pins each unit could reach, the pair skew a sequenced scan could not avoid, which
# strings came out with DIFF sign-inverted, and three routing proxies that each predicted
# wrong. All of it went with the decision below (it is in git history, 2026-09-21).
#
# WHY THE MCU'S ADCs WENT. They were this board's noise floor. DS12110 rev V gives 77 dB SNR
# single-ended -- characterised on BGA, "values for LQFP packages might differ" -- which is
# ~165 uVrms, against the ~35-50 uVrms the front end makes once its own op-amp noise is
# band-limited. Oversampling could not rescue it: ADC3 carried ten conversions, six of
# them on SLOW channels (1 Msps at 16 bit, DS12110 Table 185 notes), so ~4x was the
# ceiling. A delta-sigma audio converter fixes all of it at once:
#   * ~13 uVrms (SBAS993B 7.5: 106 dB SNR A-wt at 2 Vrms differential full scale)
#   * its decimation filter removes everything above the band, so the op-amps' voltage
#     noise out to their GBW no longer folds into the audio
#   * all twenty channels convert on ONE edge (shared BCLK/FSYNC), so a string's A and B
#     are simultaneous by construction -- the old pair-skew budget and the
#     DIFF_SIGN_INVERTED bookkeeping have nothing left to describe
#   * the analog nets end at a converter beside the MCU instead of fanning into a 0.5 mm
#     pitch LQFP edge -- which was this board's routing problem, every time
# ONE CONVERTER PER QUAD: U14..U18 take U1..U5's four outputs, IN1..IN4 in the quad's own
# section order (see SEC below), differential and AC-coupled: INxP from the TIA output,
# INxM from MID, 10 nF C0G each (TI: "for the best dynamic range performance, the
# differential AC-coupled input must be used", SBAS993B 8.3.x). MID is what every TIA
# output sits on, so taking it as the - input cancels its noise instead of adding it.
#
# ⚠ THEY RUN AT fS = 192 kHz AND THE EMITTERS ARE MODULATED AT 48 kHz, LOCKED TO FSYNC.
# The old ambient scheme -- a LEDs-on and a LEDs-off sample inside each 48 kHz frame --
# needs a sampler; a delta-sigma converter's filter averages the two together. So ambient
# rejection becomes a LOCK-IN: the emitters square-wave at fS/4, the string's audio rides
# as sidebands at 28..68 kHz inside the 192 kHz filter's ~86 kHz passband, and firmware
# multiplies by the +-1 reference and decimates to 48 kHz. Ambient light and its flicker
# land at 28..68 kHz after demodulation and are filtered away. (A 10 nF coupling cap into
# the 20 k input setting is an ~800 Hz high-pass, far below the carrier's lowest sideband.)
# The TIAs must pass the carrier, so their pole moved from 15.4 kHz to ~160 kHz -- see Rf.
#
# 20 ch x 16 bit x 192 kHz is 61 Mbit/s, more than one TDM lane carries (BCLK <= 24.576
# MHz), so EACH CONVERTER GETS ITS OWN DATA LANE at BCLK 12.288 MHz (4 slots x 16 bit x
# 192 kHz), all five on one BCLK/FSYNC pair driven by SAI1 block A. Pins, read off KiCad's
# STM32H743IITx symbol alternates (which are generated from ST's database):
#   SAI1_SCK_A PE5 (4), SAI1_FS_A PE4 (3)                      -- the one clock pair
#   lane 1 SAI1_SD_A PE6 (5)   lane 2 SAI1_SD_B PE3 (2)   lane 3 SAI2_SD_B PA0 (40)
#   lane 4 SAI2_SD_A PI6 (175) lane 5 SAI3_SD_A PD1 (143)
# ⚠ SAI2 AND SAI3 RUN AS SYNCHRONOUS SLAVES OF SAI1 (SAI_GCR SYNCIN), taking its clocks
# internally -- which is why lanes 3-5 need no SCK/FS pins of their own. SAI4 would have
# kept lane 5 on the strip-facing edge (PC1, pin 33) but it sits in the D3 domain; confirm
# SAI4<-SAI1 synchronisation in RM0433 before moving it there.
# CONTROL IS TWO I2C BUSES, because the part has two address straps -- four addresses
# (1001100..1001111, SBAS993B Table 48) for five devices. U14..U17 on I2C2 (PF0 SDA, PF1
# SCL), U18 alone on I2C4 (PF15 SDA, PF14 SCL). SHDNZ for all five on PF2, pulled LOW, so
# the converters sit in hardware shutdown until firmware has the supplies settled
# (SBAS993B 9.2.1.2 step 1).
# ⚠ THE EMITTER GATE (PB3) IS TIM2_CH2, and firmware must run it from the same PLL as the
# SAI kernel clock so the carrier is frequency-locked to FSYNC; its phase is fixed at start.
SAI_CLK = {"SAI_SCK": "PE5", "SAI_FS": "PE4"}
SAI_SD = ("PE6", "PE3", "PA0", "PI6", "PD1")     # lane k -> converter U(14 + k)
I2C_BUS = (("PF0", "PF1"), ("PF15", "PF14"))      # (SDA, SCL): I2C2, I2C4
ADC_I2C = (0, 0, 0, 0, 1)                          # converter k -> bus
ADC_ADDR = (0, 1, 2, 3, 0)                         # converter k -> ADDR1:ADDR0 strap
ADC_SHDN = "PF2"


''')

# ── photodiode parts
rep('''            pd = Part(name="PHOTODIODE", ref_prefix="PD", ref="PD%d%s" % (i, tag),
                      dest="NETLIST", tool="skidl", value="VEMD4110X01",
                      description="filtered Si PIN photodiode, string %d side %s "
                      "(LCSC C3211080)" % (i, tag),
                      footprint="Diode_SMD:D_0805_2012Metric",
                      pins=[Pin(num=1, name="K", func=P), Pin(num=2, name="A", func=P)])''',
    '''            # Everlight PD15-22B/TR8: pad 1 ANODE, pad 2 CATHODE (DTD-152-002 p.2), two
            # pads each -- elec/layout.py nets every pad that shares a number.
            pd = Part(name="PHOTODIODE", ref_prefix="PD", ref="PD%d%s" % (i, tag),
                      dest="NETLIST", tool="skidl", value="PD15-22B/TR8",
                      description="filtered Si PIN photodiode, string %d side %s "
                      "(LCSC C161211)" % (i, tag),
                      footprint="Steel:Everlight_PD15-22B",
                      pins=[Pin(num=1, name="A", func=P), Pin(num=2, name="K", func=P)])''')

# ── ballast to 0402
rep('''        r = _r("R%d" % i, "180R", "LED ballast, string %d -- 21 mA, tune per string" % i,
               "Resistor_SMD:R_0603_1608Metric")''',
    '''        r = _r("R%d" % i, "180R", "LED ballast, string %d -- 21 mA, tune per string" % i)''')

# ── the summing-node notes + wiring
cut('''        # ZERO BIAS: the photodiode's anode sits on the virtual earth and its cathode''',
    '''        out += q[out_p]''',
    '''        # ZERO BIAS: the photodiode's CATHODE sits on the virtual earth and its ANODE on
        # MID, so there is no reverse bias and next to no dark current.
        #
        # ⚠ IT WAS WIRED THE OTHER WAY ROUND UNTIL 2026-09-21, AND THE OUTPUT WENT THE WRONG
        # WAY. Photocurrent leaves a photodiode by its ANODE (it is the + terminal, which is
        # why Voc is forward polarity), so an anode on the summing node pushes current IN
        # and drives the output DOWN from MID -- and MID is 0.33 V, set there precisely
        # because the output was believed to swing UP (see R34). Every string but the
        # thinnest would have clipped at the rail. With the cathode on the virtual earth
        # the photocurrent is drawn out through Rf and the output rises, which is what the
        # rest of the board assumes.
        #
        # ⚠ THE NOISE FLOOR IS THE LIGHT NOW, NOT THE ELECTRONICS. The budget that used to
        # sit here left out photon shot noise, and every SNR it quoted (67, 75 dB) inherited
        # that. Input-referred, per string, in the demodulated band (28..68 kHz at the
        # converter, 20 kHz after the lock-in), thinnest string, no ambient:
        #   signal shot    sqrt(2q x 143 nA), on half the time      0.15 pA/rtHz
        #   Rf thermal     sqrt(4kT / 1M)                            0.13
        #   en x 2 pi f Cin at 60 kHz (10 nV, ~25 pF)                 0.09
        #   in             TLV9064                                   0.02
        #   converter      ~20 nV/rtHz at +12 dB PGA, / Rf           0.02
        # -> ~67 dB against the thin string's lock-in signal (I/2 at 50% duty). The 143 nA
        # is the old ~60 nA x the PD15's photocurrent (7 vs 2.2 uA per mW/cm2 at 940 nm)
        # x 0.75 for the wider triplet. AMBIENT IR adds its own shot noise on top: 1 uA
        # of it (~0.14 mW/cm2 in the 750-1100 nm band -- a halogen wash can do that) costs
        # ~9 dB. The daylight filter rejects visible light and nothing else: LED and
        # fluorescent stage lighting are gone, sun and incandescent are not. Their FLICKER
        # is removed by the lock-in; their shot noise and headroom are what the cover
        # (field of view) and Rf's headroom are for.
        # The lever left is LIGHT: shot-limited SNR grows as sqrt(emitter current), and the
        # emitters run at 21 mA of a 65 mA rating.
        mid += pd["A"]
        summing += pd["K"], q[inn_p]
        mid += q[inp_p]
''')
cut('''        # ⚠ 4M7 IS A FIRST-ARTICLE VALUE WITH ARITHMETIC BEHIND IT, not a guess, and it''',
    '''        summing += rf[1], cf[1]''',
    '''        # ⚠ 1M / 1 pF SINCE 2026-09-21, FOR BANDWIDTH -- the TIA has to pass the 48 kHz
        # emitter carrier and its +-20 kHz sidebands, where the old 4M7 / 2.2 pF set a
        # 15.4 kHz pole that would have eaten them. The closed-loop limit is
        # sqrt(GBW / (2 pi Rf Cin)) = sqrt(10 MHz / (2 pi x 1M x ~25 pF)) = 250 kHz, and
        # 1 pF puts the feedback pole at 159 kHz; the least Cf that is stable is
        # sqrt(Cin / (2 pi Rf GBW)) = 0.63 pF, so 1 pF is 1.6x that. (Cin: the PD15's
        # zero-bias capacitance is NOT published -- 6 pF is at VR 5 V -- and ~17 pF is
        # assumed from the VEMD's own 0 V / 5 V ratio. Measure it: more makes the loop
        # quicker to ring and the en term larger.)
        # SIGNAL LEVEL: the thin string's ~143 nA gives 0.14 V at MID + ..., a wound
        # string ~0.7 V, leaving ~2 V of the 2.9 V swing for AMBIENT photocurrent (~2 uA)
        # before the output rails. The converter's PGA (0..42 dB) takes the small end up
        # to its full scale, so the gain split is Rf for headroom, PGA for level.
        # Still per string: the plain strings can take 2M if ambient allows.
        rf = _r("Rf%s" % n, "1M", "TIA feedback, string %d%s -- tune per string" % (i, side))
        # ⚠ Cf IS C0G, NOT X7R: it sets the pole, and an X7R part's capacitance moves with
        # bias and temperature, so twenty channels would stop matching -- which is exactly
        # what DIFF cannot tolerate. 1 pF is at the edge of what a part sets rather than
        # the layout (an 0402's own stray is a few tenths): measure the pole at bring-up.
        cf = _c("Cf%s" % n, "1pF", "TIA feedback cap, string %d%s -- C0G, ~160 kHz pole"
                % (i, side))
''')

# ── the MCU: SAI / I2C / SHDNZ instead of the twenty analog pins
rep('''              description="MCU, LQFP176, 20x ADC + OTG_HS ULPI (LCSC C89597)",''',
    '''              description="MCU, LQFP176, SAI TDM from 5 audio ADCs + OTG_HS ULPI (LCSC C89597)",''')
rep('''    # the twenty analog inputs, in the pair order argued above
    for i, (pa, pb) in enumerate(ADC_PAIRS, start=1):
        tia_out[(i, "A")] += u6[PIN[pa]]
        tia_out[(i, "B")] += u6[PIN[pb]]
    Net("ADC_SPARE_NC").connect(u6[PIN[ADC_SPARE]])
''', '''    # the converters' buses -- see THE CONVERTERS
    sai_sck, sai_fs = Net("SAI_SCK"), Net("SAI_FS")
    sai_sck += u6[PIN[SAI_CLK["SAI_SCK"]]]
    sai_fs += u6[PIN[SAI_CLK["SAI_FS"]]]
    sai_sd = [Net("SAI_SD%d" % (k + 1)) for k in range(5)]
    for net, port in zip(sai_sd, SAI_SD):
        net += u6[PIN[port]]
    i2c = [(Net("I2C%d_SDA" % b), Net("I2C%d_SCL" % b)) for b in (2, 4)]
    for (sda, scl), (p_sda, p_scl) in zip(i2c, I2C_BUS):
        sda += u6[PIN[p_sda]]
        scl += u6[PIN[p_scl]]
    adc_shdn = Net("ADC_SHDNZ")
    adc_shdn += u6[PIN[ADC_SHDN]]
''')
rep('''                         "VCAP1", "VCAP2", ADC_SPARE)}
    used |= {PIN[p] for pair in ADC_PAIRS for p in pair}''',
    '''                         "VCAP1", "VCAP2", ADC_SHDN) + tuple(SAI_CLK.values()) + SAI_SD
        + tuple(p for bus in I2C_BUS for p in bus)}''')

# ── the converters themselves, after the quads' decoupling
rep('''    # ── U6: the MCU ──────────────────────────────────────────────────────────''',
    '''    # ── U14-U18: the audio converters, one per quad ─────────────────────────
    # TLV320ADC3140IRTWT, WQFN-24 RTW. Pins (SBAS993B Pin Functions): 1 AVDD 2 AREG 3 VREF
    # 4 AVSS 5 MICBIAS 6/7 IN1P/IN1M 8/9 IN2P/M 10/11 IN3P/M 12/13 IN4P/M 14 SHDNZ
    # 15 ADDR1 16 ADDR0 17 SCL 18 SDA 19 IOVDD 20 GPIO1 21 SDOUT 22 BCLK 23 FSYNC 24 DREG,
    # 25 thermal pad (VSS). Support parts are TI's Figure 165, less MICBIAS's 1 uF: there
    # are no microphones and MICBIAS stays powered down, so the pin is left open.
    # AVDD on +3V3A (the quiet LDO -- it now carries these too, see the power budget),
    # IOVDD on +3V3D with the MCU it talks to.
    adcs = {}
    for k in range(5):
        u = Part(name="TLV320ADC3140", ref_prefix="U", ref="U%d" % (14 + k), dest="NETLIST",
                 tool="skidl", value="TLV320ADC3140IRTWT",
                 description="4-ch audio ADC, quad U%d's outputs (LCSC C1852021)" % (k + 1),
                 footprint="Package_DFN_QFN:Texas_RTW_WQFN-24-1EP_4x4mm_P0.5mm_EP2.7x2.7mm",
                 pins=[Pin(num=n, func=P) for n in range(1, 26)])
        adcs[k] = u
        tag = k + 1
        areg, vref, dreg = (Net("ADC%d_AREG" % tag), Net("ADC%d_VREF" % tag),
                            Net("ADC%d_DREG" % tag))
        v3a += u[1]
        areg += u[2]
        vref += u[3]
        gnd += u[4], u[25]
        Net("ADC%d_MICBIAS_NC" % tag).connect(u[5])
        adc_shdn += u[14]
        a1, a0 = divmod(ADC_ADDR[k], 2)
        (v3d if a1 else gnd).__iadd__(u[15])
        (v3d if a0 else gnd).__iadd__(u[16])
        sda, scl = i2c[ADC_I2C[k]]
        scl += u[17]
        sda += u[18]
        v3d += u[19]
        Net("ADC%d_GPIO1_NC" % tag).connect(u[20])
        sai_sd[k] += u[21]
        sai_sck += u[22]
        sai_fs += u[23]
        dreg += u[24]
        for j, (val, net, rtn, fp) in enumerate((
                ("1uF", v3a, gnd, None), ("100nF", v3a, gnd, None),      # AVDD
                ("10uF", areg, gnd, None), ("100nF", areg, gnd, None),    # AREG
                ("1uF", vref, gnd, None),                                  # VREF
                ("10uF", dreg, gnd, None), ("100nF", dreg, gnd, None),    # DREG
                ("10uF", v3d, gnd, None), ("100nF", v3d, gnd, None)),     # IOVDD
                start=1):
            c = _c("Cs%d%d" % (tag, j), val, "U%d supply/reference bypass (SBAS993B Fig 165)"
                   % (14 + k))
            net += c[1]
            rtn += c[2]
    # the couplings: quad q's section s -> converter q's input s+1
    for ch in range(20):
        i, side = ch // 2 + 1, "A" if ch % 2 == 0 else "B"
        k, s_in = ch // 4, ch % 4 + 1
        pos, neg = Net("ADC%d_IN%dP" % (k + 1, s_in)), Net("ADC%d_IN%dM" % (k + 1, s_in))
        ci = _c("Ci%d%d" % (k + 1, s_in), "10nF C0G", "string %d%s -> U%d IN%dP"
                % (i, side, 14 + k, s_in))
        cm = _c("Cm%d%d" % (k + 1, s_in), "10nF C0G", "MID -> U%d IN%dM" % (14 + k, s_in))
        tia_out[(i, side)] += ci[1]
        pos += ci[2], adcs[k][4 + 2 * s_in]
        mid += cm[1]
        neg += cm[2], adcs[k][5 + 2 * s_in]
    for ref, net, rail, what in (("R50", i2c[0][1], v3d, "I2C2 SCL"),
                                 ("R51", i2c[0][0], v3d, "I2C2 SDA"),
                                 ("R52", i2c[1][1], v3d, "I2C4 SCL"),
                                 ("R53", i2c[1][0], v3d, "I2C4 SDA"),
                                 ("R54", adc_shdn, gnd, "SHDNZ pull-down")):
        r = _r(ref, "4k7" if rail is v3d else "100k", what)
        net += r[1]
        rail += r[2]

    # ── U6: the MCU ──────────────────────────────────────────────────────────''')

# The MCU block needs the bus nets before the converters use them: move the MCU's
# net declarations up by declaring them before the converters.
rep('''    # ── U14-U18: the audio converters, one per quad ─────────────────────────''',
    '''    sai_sck, sai_fs = Net("SAI_SCK"), Net("SAI_FS")
    sai_sd = [Net("SAI_SD%d" % (k + 1)) for k in range(5)]
    i2c = [(Net("I2C%d_SDA" % b), Net("I2C%d_SCL" % b)) for b in (2, 4)]
    adc_shdn = Net("ADC_SHDNZ")

    # ── U14-U18: the audio converters, one per quad ─────────────────────────''')
rep('''    sai_sck, sai_fs = Net("SAI_SCK"), Net("SAI_FS")
    sai_sck += u6[PIN[SAI_CLK["SAI_SCK"]]]''', '''    sai_sck += u6[PIN[SAI_CLK["SAI_SCK"]]]''')
rep('''    sai_sd = [Net("SAI_SD%d" % (k + 1)) for k in range(5)]
    for net, port in zip(sai_sd, SAI_SD):''', '''    for net, port in zip(sai_sd, SAI_SD):''')
rep('''    i2c = [(Net("I2C%d_SDA" % b), Net("I2C%d_SCL" % b)) for b in (2, 4)]
    for (sda, scl), (p_sda, p_scl) in zip(i2c, I2C_BUS):''', '''    for (sda, scl), (p_sda, p_scl) in zip(i2c, I2C_BUS):''')
rep('''    adc_shdn = Net("ADC_SHDNZ")
    adc_shdn += u6[PIN[ADC_SHDN]]''', '''    adc_shdn += u6[PIN[ADC_SHDN]]''')

# ── power budget
rep('''    #     R34/R35 mid-rail divider 3.3 V / 10.09 k          ->   0.33 / 0.33
    #                                                   subtotal  11.7 / 16.1 mA''',
    '''    #     R34/R35 mid-rail divider 3.3 V / 10.09 k          ->   0.33 / 0.33
    #     5x TLV320ADC3140 AVDD (2026-09-21)   ">23 mA" each at 48 kHz, 4 ch (SBAS993B
    #       Table 131) -- NO figure at 192 kHz; ~25 each assumed ->  125 / ~150 ?
    #                                                   subtotal ~137 / ~166 mA
    #     ⚠ THE CONVERTERS MULTIPLY THIS RAIL TENFOLD. U9 (SPX3819, 500 mA) carries it,
    #       but it burns (5 - 3.3) x 0.14 = 0.24 W in a SOT-23-5 -- ~45 C of rise -- and
    #       the buck's worst case below grows by the same ~150 mA. MEASURE AVDD current
    #       at 192 kHz on first boards before trusting either margin.''')

open(p, 'w', encoding='utf-8').write(s)
print('net ok')
