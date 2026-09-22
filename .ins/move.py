def edit(p, pairs):
    s = open(p, encoding='utf-8').read()
    for o, n in pairs:
        assert s.count(o) == 1, (p, o[:70], s.count(o))
        s = s.replace(o, n)
    open(p, 'w', encoding='utf-8').write(s)


edit('src/optical_pickup.py', [
    ('''    for k in range(5):
        qx, qy = _cell(k % 3, k // 3)
        t = k + 1
        add("U%d" % (14 + k), "audio ADC -- TLV320ADC3140, 4 ch, quad U%d's outputs" % t,
            "WQFN-24", qx, qy, 180.0)''',
     '''    # ⚠ QUADS 1 AND 2'S CONVERTERS LIVE AT THE +Y END, NOT BESIDE THE MCU (2026-09-22). With
    # all five in the annulus the board plateaued at 14-17 unconnected over six routings:
    # five cells and their caps in 25 x 27 mm, fed by twenty outputs funnelled down a
    # 13.6 mm strip. The +Y wrap is 14.4 x 62 mm of board holding nothing but one grip.
    # Moved there, U14/U15 take the eight LONGEST analog runs off the strip entirely (quads
    # 1-2 sit at its +Y end), and the annulus keeps three cells in one row. What crosses
    # the strip instead is digital -- two SAI lanes, BCLK, FSYNC, I2C and +3V3D -- which
    # needs no pads on the way and can run under the In1 ground plane, away from the
    # summing nodes on F.Cu. These two cells are turned the other way up (inputs -Y, toward
    # their quads): every offset below is mirrored through the part's centre by `_s`.
    _top_y = PCB_YP - EDGE_KEEP - (_near + _c[0] / 2)          # SAI side toward the +Y edge
    _TOP = {0: (PCB_X1S + EDGE_KEEP + _rx + _c[1] / 2, _top_y),   # over the strip's -X corner
            1: (MOUNT_X_HEAD + TP.JACK_HEAD_D / 2 + PKG_CLR + _rx + _c[1] / 2 + 0.6, _top_y)}
    for k in range(5):
        qx, qy = _TOP[k] if k in _TOP else _cell(k - 2, 0)
        _s = -1.0 if k in _TOP else 1.0
        t = k + 1
        add("U%d" % (14 + k), "audio ADC -- TLV320ADC3140, 4 ch, quad U%d's outputs" % t,
            "WQFN-24", qx, qy, 180.0 if _s > 0 else 0.0)'''),
    ('''            add(ref, "ADC input AC coupling" if ref[1] in "im" else "ADC supply bypass",
                "0402", qx + dx, qy + dy, rot)
    qx, qy = _cell(2, 1)''',
     '''            add(ref, "ADC input AC coupling" if ref[1] in "im" else "ADC supply bypass",
                "0402", qx + _s * dx, qy + _s * dy, rot if _s > 0 else (rot + 180.0) % 360.0)
    qx, qy = _cell(2, 1)'''),
])
print('ok')
