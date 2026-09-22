def edit(p, pairs):
    s = open(p, encoding='utf-8').read()
    for o, n in pairs:
        assert s.count(o) == 1, (p, o[:80], s.count(o))
        s = s.replace(o, n)
    open(p, 'w', encoding='utf-8').write(s)


edit('elec/optical.py', [
    ('''# CONTROL IS TWO I2C BUSES, because the part has two address straps -- four addresses
# (1001100..1001111, SBAS993B Table 48) for five devices. U14..U17 on I2C2 (PF0 SDA, PF1
# SCL), U18 alone on I2C4 (PF15 SDA, PF14 SCL). SHDNZ for all five on PF2, pulled LOW, so''',
     '''# CONTROL IS ONE I2C BUS AT ONE ADDRESS, ALL FIVE PARTS WRITTEN AT ONCE (2026-09-22). The
# five are configured IDENTICALLY -- each already has its own data lane, so each uses slots
# 0-3 on it -- so every register write is the same write to all five, and they share
# address 1001100 (both straps to GND). Open-drain ACKs from five parts simply wire
# together. What it gives up is reading one part back on its own (a read returns the
# wired-AND of five); firmware only writes. What it bought: this used to be two buses
# (I2C2 for four parts at four addresses, I2C4 for the fifth), and the straps that pulled
# ADDR0/ADDR1 up to +3V3D were two of the last 14 nets the router could not close -- the
# address pins sit between the I2C pins on the part's routing side.
# I2C2: PF0 SDA (16), PF1 SCL (17). SHDNZ for all five on PF2, pulled LOW, so'''),
    ('''I2C_BUS = (("PF0", "PF1"), ("PF15", "PF14"))      # (SDA, SCL): I2C2, I2C4
ADC_I2C = (0, 0, 0, 0, 1)                          # converter k -> bus
ADC_ADDR = (0, 1, 2, 3, 0)                         # converter k -> ADDR1:ADDR0 strap''',
     '''I2C_BUS = (("PF0", "PF1"),)                       # (SDA, SCL): I2C2
ADC_I2C = (0, 0, 0, 0, 0)                          # converter k -> bus
ADC_ADDR = (0, 0, 0, 0, 0)                         # converter k -> ADDR1:ADDR0 strap'''),
    ('''    i2c = [(Net("I2C%d_SDA" % b), Net("I2C%d_SCL" % b)) for b in (2, 4)]''',
     '''    i2c = [(Net("I2C%d_SDA" % b), Net("I2C%d_SCL" % b)) for b in (2,)]'''),
    ('''                                 ("R51", i2c[0][0], v3d, "I2C2 SDA"),
                                 ("R52", i2c[1][1], v3d, "I2C4 SCL"),
                                 ("R53", i2c[1][0], v3d, "I2C4 SDA"),''',
     '''                                 ("R51", i2c[0][0], v3d, "I2C2 SDA"),'''),
])
edit('src/optical_pickup.py', [
    ('''    for m, (ref, desc) in enumerate((("R50", "I2C2 SCL pull-up"), ("R51", "I2C2 SDA pull-up"),
                                     ("R52", "I2C4 SCL pull-up"), ("R53", "I2C4 SDA pull-up"),
                                     ("R54", "ADC SHDNZ pull-down -- converters off in reset"))):''',
     '''    for m, (ref, desc) in enumerate((("R50", "I2C2 SCL pull-up"), ("R51", "I2C2 SDA pull-up"),
                                     ("R54", "ADC SHDNZ pull-down -- converters off in reset"))):'''),
    ('''                        "R50", "R51", "R52", "R53", "R54")}''',
     '''                        "R50", "R51", "R54")}'''),
])
edit('.ins/opt_audit.py', [
    ('''    bus = "I2C4" if k == 4 else "I2C2"''', '''    bus = "I2C2"'''),
    ('''    key = ("I2C4" if k == 4 else "I2C2", net_of("U%d" % (14 + k), 15), net_of("U%d" % (14 + k), 16))
    chk(key not in seen, "address collision %s" % (key,))
    seen[key] = k''', '''    chk((net_of("U%d" % (14 + k), 15), net_of("U%d" % (14 + k), 16)) == ("GND", "GND"),
        "U%d address straps not both GND (broadcast scheme)" % (14 + k))'''),
    ('''          "I2C2_SCL", "I2C2_SDA", "I2C4_SCL", "I2C4_SDA", "ADC_SHDNZ", "LED_GATE"):''',
     '''          "I2C2_SCL", "I2C2_SDA", "ADC_SHDNZ", "LED_GATE"):'''),
])
print('ok')
