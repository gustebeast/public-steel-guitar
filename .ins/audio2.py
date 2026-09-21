p = 'elec/output_panel.py'
s = open(p, encoding='utf-8').read()


def rep(o, n, cnt=1):
    global s
    assert s.count(o) == cnt, (o[:80], s.count(o))
    s = s.replace(o, n)


# -- U7 / U8: AC-coupled, biased at mid-rail
rep('''    buf += u7[1], u7[4]       # unity-gain follower
    agnd += u7[2]
    sel += u7[3]
    v5 += u7[5]''', '''    buf += u7[1], u7[4]       # unity-gain follower
    agnd += u7[2]
    u7_in += u7[3]            # AC-coupled from the relay's common, biased at VMID
    v5 += u7[5]''')
rep('''    sel, buf = Net("AUDIO_SEL"), Net("BUF_OUT")''', '''    # ⚠ BOTH BUFFERS RUN AT MID-RAIL NOW (2026-09-21). They sit on 0..5 V, and neither
    # signal they carry is: the pickup is AC about 0 V and the DAC's OUTL is GROUND-CENTRED
    # (its charge pump makes the negative rail). Each op-amp input is AC-coupled and biased
    # at VMID = 2.5 V, so the whole waveform fits the rail instead of the bottom half
    # clipping at ground.
    sel, buf = Net("AUDIO_SEL"), Net("BUF_OUT")
    u7_in, pk_in, vmid = Net("OUT_BUF_IN"), Net("PICKUP_IN"), Net("VMID")''')
rep('''    pk_buf += u8[1], u8[4]
    agnd += u8[2]
    pk_hot += u8[3]
    v5 += u8[5]''', '''    pk_buf += u8[1], u8[4]
    agnd += u8[2]
    pk_in += u8[3]            # the coil through C37, biased at VMID through R8 (1M)
    v5 += u8[5]''')

# -- K1: Omron G6K-2F-Y
rep('''    # 1/10 coil, 2 common, 3 NC (direct), 4 NO (processed) on the pole in use.
    coil = Net("RELAY_COIL")
    k1 = Part(name="RELAY_DPDT", ref_prefix="K", tag="K1", dest="NETLIST", tool="skidl",
              value="FRT5-class 5V", description="true-bypass select; DE-ENERGISED = DIRECT",
              footprint=RELAY_FP, pins=[Pin(num=i, func=P) for i in range(1, 11)])
    v5 += k1[1]
    coil += k1[10]
    sel += k1[2]
    pk_buf += k1[3]
    proc += k1[4]
    for i in (5, 6, 7, 8, 9):
        Net("K1_NC_%d" % i).connect(k1[i])''', '''    # OMRON G6K-2F-Y-DC5 (LCSC C326376), off Omron's own terminal arrangement (TOP VIEW,
    # datasheet p.6): coil 1 (+) / 8 (-); pole A COM 3, NC 2, NO 4; pole B COM 6, NC 7, NO 5.
    # It replaces an "FRT5-class" part numbered 1..10 with no datasheet behind it -- the
    # FRT5's own maker publishes no pin diagram that could be found, and its SMD variant is
    # not stocked where this board is built. Pole B is spare.
    # BOTH THROWS ARE AC-COUPLED (C38 on the direct side, the DAC is ground-centred already),
    # and the common is held at 0 V by R15 -- so switching between them moves no DC and
    # makes no click.
    coil, direct, dac_att = Net("RELAY_COIL"), Net("DIRECT_AC"), Net("DAC_ATT")
    k1 = Part(name="G6K-2F-Y", ref_prefix="K", tag="K1", dest="NETLIST", tool="skidl",
              value="G6K-2F-Y-DC5", description="true-bypass select; DE-ENERGISED = DIRECT "
              "(LCSC C326376)", footprint=RELAY_FP, pins=[Pin(num=i, func=P) for i in range(1, 9)])
    v5 += k1[1]
    coil += k1[8]
    sel += k1[3]
    direct += k1[2]
    dac_att += k1[4]
    for i in (5, 6, 7):
        Net("K1_NC_%d" % i).connect(k1[i])''')

# -- D5: a real part
rep('''    d5 = _d("D5", "bidir clamp", "catches the insertion edge C1 passes through")''',
    '''    d5 = _d("D5", "ESD5B5.0ST1G", "bidirectional 5 V TVS (LCSC C93623): catches the "
            "insertion edge C1 passes through. The node it sits on idles at VMID and swings "
            "0..5 V, inside its 5.0 V working voltage")''')

# -- R8 and the new passives
rep('''    r8 = _r("R8", "1M", "pickup input bias to ground -- the coil is FLOATING until "
            "someone screws a pickup on, and an unbiased op-amp input rails")
    pk_hot += r8[1]
    agnd += r8[2]''', '''    r8 = _r("R8", "1M", "pickup input bias to VMID -- and the LOAD the pickup sees, which "
            "sets its tone: 1M is a typical amplifier input")
    pk_in += r8[1]
    vmid += r8[2]''')
rep('''    for tag, net in (("C15", osc_in), ("C16", osc_out), ("C17", hub_xi), ("C18", hub_xo)):
        c = _c(tag, "12pF", "crystal load")
        net += c[1]
        gnd += c[2]
''', '''    for tag, net in (("C15", osc_in), ("C16", osc_out), ("C17", hub_xi), ("C18", hub_xo)):
        c = _c(tag, "12pF", "crystal load")
        net += c[1]
        gnd += c[2]

    # ── the analog rewrite's parts (2026-09-21) ────────────────────────────────
    C0805 = "Capacitor_SMD:C_0805_2012Metric"
    dac_filt = Net("DAC_FILT")
    for tag, val, a, b, desc, fp in (
            # U2, PCM1808: VREF, VCC and VDD each 0.1 uF + 10 uF (TI 10.1.4 / 8.2 C3-C5);
            # C13 is VCC's 0.1 uF
            ("C19", "100nF", vref, agnd, "ADC VREF", None),
            ("C20", "10uF", vref, agnd, "ADC VREF bulk", C0805),
            ("C21", "10uF", v5, agnd, "ADC VCC bulk", C0805),
            ("C22", "100nF", v3v3, gnd, "ADC VDD", None),
            ("C23", "10uF", v3v3, gnd, "ADC VDD bulk", C0805),
            ("C24", "1uF", pk_buf, adc_in, "ADC input coupling (TI's 1 uF)", C0805),
            # U3, PCM5102A, Figure 33: AVDD / CPVDD / DVDD / LDOO each 0.1 + 10 uF, the charge
            # pump's flying cap and VNEG 2.2 uF each; C14 is AVDD's 0.1 uF
            ("C25", "10uF", v3v3, agnd, "DAC AVDD bulk", C0805),
            ("C26", "100nF", v3v3, gnd, "DAC CPVDD", None),
            ("C27", "10uF", v3v3, gnd, "DAC CPVDD bulk", C0805),
            ("C28", "100nF", v3v3, gnd, "DAC DVDD", None),
            ("C29", "10uF", v3v3, gnd, "DAC DVDD bulk", C0805),
            ("C30", "100nF", ldoo, gnd, "DAC LDOO", None),
            ("C31", "10uF", ldoo, gnd, "DAC LDOO bulk", C0805),
            ("C32", "2.2uF", capp, capm, "DAC charge-pump flying cap", C0805),
            ("C33", "2.2uF", vneg, gnd, "DAC VNEG", C0805),
            ("C34", "2.2nF C0G", dac_filt, agnd, "DAC output filter, with R13 "
             "(TI's recommended 470R + 2.2 nF)", None),
            # U4, CH334F: V5 >= 1 uF, VDD33 0.1 + 10 uF (C12 is the 0.1)
            ("C35", "1uF", v3v3, gnd, "hub V5", None),
            ("C36", "10uF", v3v3, gnd, "hub VDD33 bulk", C0805),
            # the buffers
            ("C37", "100nF C0G", pk_hot, pk_in, "pickup input coupling -- 16 Hz into R8's "
             "1M. C0G: a coupling cap in the coil's own path must not have a voltage "
             "coefficient", "Capacitor_SMD:C_1206_3216Metric"),
            ("C38", "1uF", pk_buf, direct, "direct-path coupling to the relay (1.6 Hz into "
             "R15 + the U7 path)", C0805),
            ("C39", "1uF", sel, u7_in, "output buffer input coupling (1.6 Hz into R16)", C0805),
            ("C40", "10uF", vmid, agnd, "VMID reservoir", C0805)):
        c = _c(tag, val, desc, fp) if fp else _c(tag, val, desc)
        a += c[1]
        b += c[2]
    for tag, val, a, b, desc in (
            ("R13", "470R", proc, dac_filt, "DAC output filter, with C34"),
            ("R14", "10k", dac_filt, dac_att, "DAC -6 dB with R15: 2.1 Vrms (5.9 Vpp) is "
             "more than a 5 V rail carries; ~3 Vpp after this"),
            ("R15", "10k", sel, agnd, "relay common to 0 V -- no DC step when it switches"),
            ("R16", "100k", u7_in, vmid, "output buffer bias to VMID"),
            ("R17", "100k", v5, vmid, "VMID divider, top"),
            ("R18", "100k", vmid, agnd, "VMID divider, bottom"),
            ("R19", "10k", ovcur, v3v3, "hub OVCUR# pulled inactive")):
        r = _r(tag, val, desc)
        a += r[1]
        b += r[2]
''')
rep('''            ("C14", "100nF", v5, agnd, "DAC analog bypass")):''',
    '''            ("C14", "100nF", v3v3, agnd, "DAC AVDD bypass -- 3V3, never 5 V (abs max 3.9)")):''')
open(p, 'w', encoding='utf-8').write(s)
print('stage2 ok')
