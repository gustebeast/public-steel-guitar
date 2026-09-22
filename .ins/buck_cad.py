def edit(p, pairs):
    s = open(p, encoding='utf-8').read()
    for o, n in pairs:
        assert s.count(o) == 1, (p, o[:70], s.count(o))
        s = s.replace(o, n)
    open(p, 'w', encoding='utf-8').write(s)


edit('src/optical_pickup.py', [
    ('''    "IND-4040": (4.10, 4.10, 2.10),   # 4x4 shielded power inductor, buck output''',
     '''    "IND-4040": (4.10, 4.10, 3.10),   # 4x4 shielded power inductor, buck output (SWPA4030,
                                      # 3.0 tall since the LMR33630 swap)
    "RNX12":    (2.00, 3.00, 1.00),   # TI VQFN-HR RNX0012, the LMR33630CRNXR buck'''),
    ('''    "IND-4040": (5.15, 4.59),''',
     '''    "IND-4040": (5.15, 4.59),
    "RNX12":    (2.90, 3.90),   # elec/footprints/Steel.pretty/Texas_RNX0012_...'''),
    ('''    _buck_order = (("C160", "24 V input bulk -- 50 V part, see 1206C", "1206C"),
                   ("C161", "24 V input HF bypass -- CLOSEST to U13 on purpose", "0402"),
                   ("U13", "buck -- 24V -> 5V, the board's only switcher", "SOT-23-6"),
                   ("C163", "bootstrap -- CB to SW, both on U13's left", "0402"),
                   ("L1", "buck output inductor", "IND-4040"),
                   ("C162", "5 V output bulk", "0805C"),''',
     '''    # LMR33630CRNXR since 2026-09-22 (see U13 in elec/optical.py): its two VIN/PGND pairs
    # sit on OPPOSITE sides, so each gets a 100 nF hard against it (C161 -X, C165 +X), and
    # VCC's 1 uF (C166) and a second output 22 uF (C167) join the row.
    _buck_order = (("C160", "24 V input bulk -- 50 V part, see 1206C", "1206C"),
                   ("C161", "24 V input HF bypass -- the VIN/PGND pair on U13's -X side", "0402"),
                   ("U13", "buck -- 24V -> 5V, the board's only switcher", "RNX12"),
                   ("C165", "24 V input HF bypass -- the VIN/PGND pair on U13's +X side", "0402"),
                   ("C163", "bootstrap -- BOOT to SW", "0402"),
                   ("C166", "buck VCC bypass, 1 uF", "0402"),
                   ("L1", "buck output inductor", "IND-4040"),
                   ("C162", "5 V output bulk", "0805C"),
                   ("C167", "5 V output bulk, second", "0805C"),'''),
    ('''    ("U13",  ("TPS560430XFDBVR", "C523980",  0.35,  "24V->5V synchronous buck, SOT-23-6, 600 mA, "
                                                    "1.1 MHz FORCED PWM. Meets the recorded want: "
                                                    "synchronous, 38 V abs max (>=30), fSW far from "
                                                    "the sample rate. 3,494 in stock 2026-09-17. "
                                                    "NOTE the 24 V trunk also feeds the steppers; "
                                                    "38 V is the margin against their regen")),
    ("L1",   ("SWPA4020S150MT",  "C36407",   0.10,  "buck output inductor, 15 uH shielded, 4.0 x 4.0 "
                                                    "x 2.0. Isat 1.35 A worst case -- sized against "
                                                    "the TPS560430's 1.4 A MAXIMUM current limit, "
                                                    "which is what SLVSE22B 9.2.2.4 says to size "
                                                    "against, not the 0.72 A the board draws. 15 uH "
                                                    "rather than 18: KIND 0.42 is inside TI's 20-60% "
                                                    "band and no 4x4 part at 22 uH gets past 1.05 A. "
                                                    "SHIELDED is not optional -- an unshielded "
                                                    "inductor radiates into 20 TIAs. "
                                                    "8,816 in stock 2026-09-17")),''',
     '''    ("U13",  ("LMR33630CRNXR",   "C2071783", 1.82,  "24V->5V synchronous buck, VQFN-HR RNX 2x3, 3 A, "
                                                    "2.1 MHz, 36 V abs max (user, 2026-09-22: the "
                                                    "TPS560430's 600 mA was 105 % used worst case "
                                                    "with the five converters). No FPWM variant is "
                                                    "stocked; at 2.1 MHz / 4.7 uH it stays in CCM "
                                                    "(fixed frequency) above ~0.2 A. 793 in stock")),
    ("L1",   ("SWPA4030S4R7MT",  "C57269",   0.12,  "buck output inductor, 4.7 uH shielded, 4.0 x 4.0 "
                                                    "x 3.0, Isat 3.2 A, DCR 78 mohm. 0.40 A pk-pk "
                                                    "ripple at 2.1 MHz. SHIELDED is not optional -- "
                                                    "an unshielded inductor radiates into 20 TIAs. "
                                                    "42,221 in stock 2026-09-22")),'''),
    ('''                   for r in ("C161", "C163")})''',
     '''                   for r in ("C161", "C163", "C165", "C166")})
_MPN_EXACT["C167"] = ("0805 X7R MLCC", "BASIC", 0.01, "buck 5 V output bulk, second")'''),
])
edit('elec/fab.py', [
    ('''    "TPS560430XFDBVR": "C523980",   # 24->5 V sync buck, 1.1 MHz FPWM''',
     '''    "LMR33630CRNXR": "C2071783",    # 24->5 V sync buck, 2.1 MHz, 3 A, VQFN-HR RNX (optical U13)'''),
    ('''    "SWPA4020S150MT": "C36407",      # 15 uH, 4x4x2.0 shielded, DCR 0.299 ohm max''',
     '''    "SWPA4030S4R7MT": "C57269",      # 4.7 uH, 4x4x3.0 shielded, Isat 3.2 A (optical L1)'''),
])
edit('elec/optical.py', [
    ('''    "WQFN-24":  "Package_DFN_QFN:Texas_RTW_WQFN-24-1EP_4x4mm_P0.5mm_EP2.7x2.7mm",''',
     '''    "WQFN-24":  "Package_DFN_QFN:Texas_RTW_WQFN-24-1EP_4x4mm_P0.5mm_EP2.7x2.7mm",
    "RNX12":    "Steel:Texas_RNX0012_VQFN-HR-12_2x3mm_P0.5mm",'''),
])
print('ok')
