p = 'elec/output_panel.py'
s = open(p, encoding='utf-8').read()


def rep(o, n, cnt=1):
    global s
    assert s.count(o) == cnt, (o[:80], s.count(o))
    s = s.replace(o, n)


def cut(a_marker, b_marker, new):
    global s
    a = s.index(a_marker)
    b = s.index(b_marker, a)
    s = s[:a] + new + s[b:]


rep('ADC_FP = "Package_SO:TSSOP-16_4.4x5mm_P0.65mm"',
    'ADC_FP = "Package_SO:TSSOP-14_4.4x5mm_P0.65mm"     # PCM1808PWR is a 14-pin TSSOP')
rep('RELAY_FP = "Relay_SMD:Relay_DPDT_FRT5_SMD"',
    'RELAY_FP = "Relay_SMD:Relay_DPDT_Omron_G6K-2F-Y"')

# -- U1: MCLK + VBAT, and the relay pin's real name
rep('''    #   25 PB0 relay, 48 PA13 SWDIO, 52 PA14 SWCLK, 63 BOOT0''',
    '''    #   25 PC5 relay (the comment said PB0 until 2026-09-21; PB0 is pin 26 -- the WIRING was
    #            always pin 25, so firmware drives PC5), 48 PA13 SWDIO, 52 PA14 SWCLK, 63 BOOT0
    #   39 PC6  = I2S2_MCK -> the ADC's SCKI and the DAC's SCK (256 fS)
    #    1 VBAT -> 3V3 (it was floating: see motor_ctrl.py's note -- the same check that
    #            passed every WIRED pin never asked which pins were not wired)
    # Re-read 2026-09-21 off datasheet V3.8 Table 3-1 (the 303/305/307 table; pages 41-48
    # are the CH32V317's and number these pins differently).''')
rep('''                 61, 62, 35, 36, 37, 38, 25, 48, 52, 63)]''',
    '''                 61, 62, 35, 36, 37, 38, 25, 48, 52, 63, 39, 1)]''')
rep('''    relay += u1[25]
''', '''    relay += u1[25]
    mclk = Net("I2S_MCK")
    mclk += u1[39]
    v3v3 += u1[1]             # VBAT: no backup battery, so it is the main supply
''')

# -- U2 / U3: real pinouts, real supplies
cut('''    # ══ ⚠ AUDIT, 2026-09-17: THE ANALOG HALF OF THIS BOARD IS NOT BUILDABLE AS WIRED''',
    '''    # ── U4: the hub.''', '''    # ══ THE ANALOG HALF, REWIRED FROM TI'S DATASHEETS (2026-09-21) ══════════════════════
    # The 2026-09-17 audit found it unbuildable: both converters' pinouts invented, the DAC on
    # 5 V (abs max 3.9), the ADC's SCKI tied to BCK, and both buffers unable to go below
    # ground. Every pin below is off the part's own Pin Functions table (PCM1808 SLES177B,
    # PCM5102A SLAS859C, both read 2026-09-21), every support part off its typical-application
    # figure (PCM5102A Figure 33; PCM1808 sections 8.2 and 10.1.4). fab.py still holds the
    # board OPEN until someone checks this against the datasheets independently.

    # ── U2: PCM1808PWR, TSSOP-14 -- the magnetic channel's ADC ──────────────
    #   1 VREF 2 AGND 3 VCC(5 V) 4 VDD(3V3) 5 DGND 6 SCKI 7 LRCK 8 BCK 9 DOUT
    #   10 MD0 11 MD1 12 FMT 13 VINL 14 VINR
    # MD1 = MD0 = low: SLAVE mode, SCKI auto-detected at 256/384/512 fS, so the MCU owns BCK
    # and LRCK and the ADC and DAC share one clock. FMT low = I2S.
    # SCKI is the MCU's I2S2_MCK (PC6) -- a real 256 fS master clock. It was tied to BCK
    # (64 fS), which the part cannot run from.
    pk_buf, adc_in, vref = Net("PICKUP_BUF"), Net("ADC_IN"), Net("ADC_VREF")
    u2 = Part(name="PCM1808PWR", ref_prefix="U", ref="U2", tag="U2", dest="NETLIST", tool="skidl",
              value="PCM1808PWR", description="24-bit 99 dB 96 kHz stereo ADC",
              footprint=ADC_FP,
              pins=[Pin(num=i + 1, name=n, func=P) for i, n in enumerate(
                  ("VREF", "AGND", "VCC", "VDD", "DGND", "SCKI", "LRCK", "BCK", "DOUT",
                   "MD0", "MD1", "FMT", "VINL", "VINR"))])
    vref += u2["VREF"]
    agnd += u2["AGND"]
    v5 += u2["VCC"]
    v3v3 += u2["VDD"]
    gnd += u2["DGND"], u2["MD0"], u2["MD1"], u2["FMT"]
    mclk += u2["SCKI"]
    i2s_ws += u2["LRCK"]
    i2s_ck += u2["BCK"]
    i2s_sdi += u2["DOUT"]
    # BOTH inputs take the one buffered pickup (one coil), through ONE coupling cap: the ADC
    # biases its own inputs at VREF (0.5 VCC), 60k each, so the cap is the input HPF --
    # TI's 1 uF gives 2.7 Hz into one input; into the two in parallel, 5.3 Hz.
    adc_in += u2["VINL"], u2["VINR"]

    # ── U3: PCM5102APWR, TSSOP-20 -- the Pi's processed audio, made analog again ──
    #   1 CPVDD 2 CAPP 3 CPGND 4 CAPM 5 VNEG 6 OUTL 7 OUTR 8 AVDD 9 AGND 10 DEMP
    #   11 FLT 12 SCK 13 BCK 14 DIN 15 LRCK 16 FMT 17 XSMT 18 LDOO 19 DGND 20 DVDD
    # EVERY SUPPLY IS 3.3 V (AVDD/CPVDD/DVDD abs max 3.9 V). FLT, DEMP, FMT low: normal
    # latency, no de-emphasis, I2S. SCK takes the same 256 fS MCLK as the ADC (4-wire), so
    # the DAC's clock does not depend on its PLL locking to BCK. XSMT high = un-muted.
    proc = Net("AUDIO_PROC")
    capp, capm = Net("DAC_CAPP"), Net("DAC_CAPM")
    vneg, ldoo = Net("DAC_VNEG"), Net("DAC_LDOO")
    u3 = Part(name="PCM5102APWR", ref_prefix="U", ref="U3", tag="U3", dest="NETLIST", tool="skidl",
              value="PCM5102APWR", description="112 dB stereo DAC, 2.1 Vrms ground-centred out",
              footprint=DAC_FP,
              pins=[Pin(num=i + 1, name=n, func=P) for i, n in enumerate(
                  ("CPVDD", "CAPP", "CPGND", "CAPM", "VNEG", "OUTL", "OUTR", "AVDD", "AGND",
                   "DEMP", "FLT", "SCK", "BCK", "DIN", "LRCK", "FMT", "XSMT", "LDOO", "DGND",
                   "DVDD"))])
    v3v3 += u3["CPVDD"], u3["AVDD"], u3["DVDD"], u3["XSMT"]
    gnd += u3["CPGND"], u3["AGND"], u3["DGND"], u3["DEMP"], u3["FLT"], u3["FMT"]
    capp += u3["CAPP"]
    capm += u3["CAPM"]
    vneg += u3["VNEG"]
    ldoo += u3["LDOO"]
    mclk += u3["SCK"]
    i2s_ck += u3["BCK"]
    i2s_sdo += u3["DIN"]
    i2s_ws += u3["LRCK"]
    proc += u3["OUTL"]
    # ⚠ OUTR IS UNCONNECTED ON PURPOSE AND THAT IS NOW A DECISION, NOT AN OMISSION.
    # The user's call: the PI DOES THE STEREO->MONO SUM IN SOFTWARE. It already
    # chooses what to send here, so it can fold down for the jack while the
    # computer gets full stereo over the gadget port -- two different mixes from
    # one stream.
    Net("DAC_OUT_R_NC").connect(u3["OUTR"])

''')

# -- U4: CH334F
cut('''    # ── U4: the hub. HIGH SPEED -- a FS hub would reintroduce the TT''',
    '''    # ── U5: 24 -> 5 V.''', '''    # ── U4: the hub. HIGH SPEED -- a FS hub would reintroduce the TT ─────────
    # WCH CH334F, QFN-24 4x4 (LCSC C5187527). Pins off WCH's datasheet V2.5 Table 1-3, the
    # "4F" column (the pin-arrangement FIGURE's package labels are offset by one block --
    # read the table): 1 OVCUR# 2 NC 3 XO 4 XI 5 DM4 6 DP4 7 DM3 8 DP3 9 DM2 10 DP2
    # 11 DM1 12 DP1 13 LED3/SCL 14 DMU 15 DPU 16 RESET# 17 NC 18 NC 19 V5 20 VDD33
    # 21 LED4/SDA 22 LED1/PSELF 23 LED2/PGANG 24 PWREN#, EP = GND.
    # Powered at 3.3 V on BOTH V5 ("5V or 3.3V power input") and VDD33 ("LDO output and
    # 3.3V input"). RESET# has its own pull-up and WCH says leave it open; PSELF and PGANG
    # default high (self-powered, ganged) through their own pull-ups -- both what this board
    # is. OVCUR# is pulled high: nothing here measures port current. Ports 3/4 unused.
    # (The old generic "1 UDP 2 UDM 3 VDD..." pinout matched no real hub.)
    hub_xi, hub_xo, ovcur = Net("HUB_XI"), Net("HUB_XO"), Net("HUB_OVCUR_N")
    u4 = Part(name="CH334F", ref_prefix="U", ref="U4", tag="U4", dest="NETLIST", tool="skidl",
              value="CH334F", description="4-port USB 2.0 HIGH-SPEED hub (2 used): "
              "the MCU and the optical board reach the Pi on ONE cable",
              footprint=HUB_FP, pins=[Pin(num=i, func=P) for i in range(1, 26)])
    ovcur += u4[1]
    hub_xo += u4[3]
    hub_xi += u4[4]
    hub_dn2_dm += u4[9]
    hub_dn2_dp += u4[10]
    hub_dn1_dm += u4[11]
    hub_dn1_dp += u4[12]
    hub_up_dm += u4[14]
    hub_up_dp += u4[15]
    v3v3 += u4[19], u4[20]
    gnd += u4[25]
    for n in (2, 5, 6, 7, 8, 13, 16, 17, 18, 21, 22, 23, 24):
        Net("U4_NC_%d" % n).connect(u4[n])

''')
open(p, 'w', encoding='utf-8').write(s)
print('stage1 ok')
