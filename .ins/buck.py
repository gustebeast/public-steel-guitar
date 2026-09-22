def edit(p, pairs):
    s = open(p, encoding='utf-8').read()
    for o, n in pairs:
        assert s.count(o) == 1, (p, o[:70], s.count(o))
        s = s.replace(o, n)
    open(p, 'w', encoding='utf-8').write(s)


edit('elec/optical.py', [
    ('''    # Pinout, datasheet section 6: 1 CB, 2 GND, 3 FB, 4 EN, 5 VIN, 6 SW.
    u13 = Part(name="TPS560430XF", ref_prefix="U", ref="U13", dest="NETLIST",
               tool="skidl", value="TPS560430XFDBVR",
               description="24V -> 5V synchronous buck, 1.1 MHz FPWM, 600 mA "
               "(LCSC C523980)",
               footprint="Package_TO_SOT_SMD:SOT-23-6",
               pins=[Pin(num=n, func=P) for n in range(1, 7)])
    v24 = Net("+24V")
    v24.drive = Pin.drives.POWER
    boot = Net("BOOT")
    boot += u13[1]
    pgnd += u13[2]
    fb += u13[3]
    # EN WAS LEFT FLOATING, and the datasheet says in as many words "Do not float".
    # Tied to VIN, which it explicitly allows; its precision threshold is 1.23 V, so
    # 24 V is solidly on.
    v24 += u13[4]
    v24 += u13[5]
    sw += u13[6]''',
     '''    # ⚠ NOW THE LMR33630CRNXR (user, 2026-09-22) -- the TPS560430's 600 mA was 105 % used in
    # the worst case once the five converters landed on this board. 3 A, 36 V abs max, the
    # motor controller's family. THE VARIANT IS THE POINT:
    #   * "C" = 2.1 MHz. No forced-PWM LMR33630 is stocked, and a pulse-skipping buck at
    #     light load puts its switching energy at variable, low -- sometimes audio --
    #     frequencies beside twenty TIAs; that is why the TPS560430 was the FPWM part. At
    #     2.1 MHz with 4.7 uH the ripple is 0.40 A pk-pk, so the part stays in continuous
    #     conduction (fixed frequency) above ~0.2 A, and this board never draws less than
    #     the MCU's ~0.3 A. (TI's 5 V / 2.1 MHz example uses 1.5 uH -- sized for 3 A; at
    #     this board's load its 1.25 A ripple would drop the part into PFM.)
    #   * "RNX" = VQFN-HR 2 x 3 mm, NOT the motor controller's HSOIC-8: the buck row sits
    #     against the tail's 0.11 mm length margin and the SOIC grows it 0.86 mm.
    # Pinout, SNVSB08 Table 6-1 (VQFN column): 1 PGND, 2 VIN, 3 NC, 4 BOOT, 5 VCC, 6 AGND,
    # 7 FB, 8 PG, 9 EN, 10 VIN, 11 PGND, 12 SW. TI: "connect the SW pin to NC on the PCB"
    # (it simplifies the CBOOT loop), so pin 3 joins SW. PG is unused and left open.
    # Footprint: elec/footprints/Steel.pretty, drawn from TI's RNX0012B/C land (identical).
    # 793 in stock 2026-09-22 (C2071783).
    u13 = Part(name="LMR33630CRNX", ref_prefix="U", ref="U13", dest="NETLIST",
               tool="skidl", value="LMR33630CRNXR",
               description="24V -> 5V synchronous buck, 2.1 MHz, 3 A (LCSC C2071783)",
               footprint="Steel:Texas_RNX0012_VQFN-HR-12_2x3mm_P0.5mm",
               pins=[Pin(num=n, func=P) for n in range(1, 13)])
    v24 = Net("+24V")
    v24.drive = Pin.drives.POWER
    boot, vcc_buck = Net("BOOT"), Net("BUCK_VCC")
    pgnd += u13[1], u13[11], u13[6]
    v24 += u13[2], u13[10]
    sw += u13[3], u13[12]
    boot += u13[4]
    vcc_buck += u13[5]
    fb += u13[7]
    Net("BUCK_PG_NC").connect(u13[8])
    # EN tied to VIN, which the datasheet allows ("Can be connected directly to VIN; Do
    # not float") -- the same choice the TPS560430 had.
    v24 += u13[9]'''),
    ('''    l1 = Part(name="L", ref_prefix="L", ref="L1", dest="NETLIST", tool="skidl",
              value="SWPA4020S150MT",
              description="buck output inductor, 15 uH shielded, Isat 1.35 A, "
              "DCR 0.299 ohm max, 4.0 x 4.0 x 2.0 (LCSC C36407)",
              footprint="Inductor_SMD:L_Sunlord_SWPA4020S",''',
     '''    # (The TPS560430-era sizing above is history.) With the LMR33630C at 2.1 MHz the pick
    # is 4.7 uH -- see U13 -- in the same Sunlord 4x4 family, the 3.0-tall 4030 for its
    # 3.2 A saturation: the IC's own current limit is ~4 A, so a hard short saturates it
    # briefly either way; in service the peak is ~0.9 A.
    l1 = Part(name="L", ref_prefix="L", ref="L1", dest="NETLIST", tool="skidl",
              value="SWPA4030S4R7MT",
              description="buck output inductor, 4.7 uH shielded, Isat 3.2 A, "
              "DCR 78 mohm, 4.0 x 4.0 x 3.0 (LCSC C57269)",
              footprint="Inductor_SMD:L_Sunlord_SWPA4030S",'''),
    ('''    r40 = _r("R40", "40k2 1%", "buck feedback divider, top -- 5.02 V with R41")
    r41 = _r("R41", "10k 1%", "buck feedback divider, bottom")''',
     '''    # LMR33630: VREF is also 1.0 V; TI's own 5 V example uses 100k / 24.9k (5.02 V).
    r40 = _r("R40", "100k 1%", "buck feedback divider, top -- 5.02 V with R41")
    r41 = _r("R41", "24k9 1%", "buck feedback divider, bottom")'''),
    ('''    c163 = _c("C163", "100nF", "buck bootstrap, CB to SW -- 100 nF per datasheet")
    boot += c163[1]
    sw += c163[2]''',
     '''    c163 = _c("C163", "100nF", "buck bootstrap, BOOT to SW -- 100 nF per datasheet")
    boot += c163[1]
    sw += c163[2]
    # LMR33630 extras (SNVSB08 Table 6-1 / 9.2.2): VCC needs its own 1 uF; the two VIN
    # pins sit on OPPOSITE sides of the RNX package, so each gets its own 100 nF (TI's
    # layout puts one beside each VIN/PGND pair); and a second 22 uF at the output.
    c165 = _c("C165", "100nF", "24 V HF bypass -- the second VIN/PGND pair (pins 10/11)")
    v24 += c165[1]
    pgnd += c165[2]
    c166 = _c("C166", "1uF", "buck VCC bypass (internal 5 V LDO)")
    vcc_buck += c166[1]
    pgnd += c166[2]
    c167 = _c("C167", "22uF/16V", "buck 5 V output bulk, second",
              "Capacitor_SMD:C_0805_2012Metric")
    v5_pre += c167[1]
    pgnd += c167[2]'''),
    ('''    #   +5V / V5_PRE  (U13, TPS560430, 600 mA)''', '''    #   +5V / V5_PRE  (U13, LMR33630C since 2026-09-22 -- 3 A; this budget was the TPS560430's 600 mA)'''),
])
print('net ok')
