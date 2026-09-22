import re


def edit(p, pairs):
    s = open(p, encoding='utf-8').read()
    for o, n in pairs:
        assert s.count(o) == 1, (p, o[:80], s.count(o))
        s = s.replace(o, n)
    open(p, 'w', encoding='utf-8').write(s)


edit('elec/optical.py', [
    ("    # emitter return -- 211 mA pulsed at 96 kHz, the board's worst aggressor -- is",
     "    # emitter return -- 211 mA square-waved at 48 kHz, the board's worst aggressor -- is"),
    ("    # TIAs (a quarter of a quad each) with Rf/Cf, and two ADC pins.",
     "    # TIAs (a quarter of a quad each) with Rf/Cf, and two converter channels."),
    ("    # Every TIA output goes straight to an ADC pin, and ST's Table 21 (DS12110,",
     "    # (Written when every TIA output went straight to an MCU ADC pin; the converters'\n"
     "    # inputs are AC-coupled now, but their abs max is AVDD + 0.3 all the same.)\n"
     "    # Every TIA output went straight to an ADC pin, and ST's Table 21 (DS12110,"),
    ("    #       a measurement: the emitters run at 96 kHz against a 48 kHz sample rate with\n"
     "    #       an LEDs-off ambient sample between, so equal on and off periods give 50%.",
     "    #       a measurement: the emitters square-wave at 48 kHz, a quarter of the\n"
     "    #       converters' 192 kHz, for the lock-in -- a square wave is 50% by nature."),
    ("               # 96 kHz, synchronously with sampling, the one noise source ambient",
     "               # 48 kHz, synchronously with sampling, the one noise source ambient"),
    ("    # it, and the emitters pulsing at 96 kHz share the same rail. 10 uF beside U8 costs",
     "    # it, and the emitters pulsing at 48 kHz share the same rail. 10 uF beside U8 costs"),
    ("    # Only the LOCAL cluster is laid; the long run to the MCU's ADC pin stays the",
     "    # Only the LOCAL cluster is laid; the long run to the converter's coupling cap stays the"),
])
edit('src/optical_pickup.py', [
    ("    the alternative was a ~90 mm trace sharing a board with a 96 kHz LED driver whose",
     "    the alternative was a ~90 mm trace sharing a board with a pulsed LED driver whose"),
    ("    # board's LED driver switches at 96 kHz SYNCHRONOUSLY WITH SAMPLING, so that return",
     "    # board's LED driver switches at 48 kHz SYNCHRONOUSLY WITH SAMPLING, so that return"),
    ("    # assuming. LCSC's whole catalogue was swept for a DAYLIGHT-FILTERED PIN photodiode",
     "    # ⚠ SUPERSEDED 2026-09-21 -- the detector is the Everlight PD15-22B now (see PD_DY).\n"
     "    # The sweep below looked only at 0805 lands; the full catalogue (802 photodiodes)\n"
     "    # has filtered parts in bigger packages, and redesigning the triplet around one\n"
     "    # was cheaper than the stock problem. Kept for the history.\n"
     "    # assuming. LCSC's whole catalogue was swept for a DAYLIGHT-FILTERED PIN photodiode"),
])
print('ok')
