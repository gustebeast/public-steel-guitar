p = 'elec/motor_ctrl.py'
s = open(p, encoding='utf-8').read()


def rep(o, n):
    global s
    assert s.count(o) == 1, (o[:80], s.count(o))
    s = s.replace(o, n)


rep('''def _xcvr(tag, desc):''', '''PH_FP = "Connector_JST:JST_PH_B4B-PH-K_1x04_P2.00mm_Vertical"


def _ph(tag, desc):
    """The LEVER bus's connector: JST PH, top entry. Same pin ORDER as the XH buses
    (GND / +V / CAN_H / CAN_L) so one crimp order serves the whole harness, but a
    different FAMILY, so a lever harness cannot mate a 24 V XH header and vice versa."""
    return Part(name="B4B-PH-K-S", ref_prefix="J", tag=tag, dest="NETLIST", tool="skidl",
                value="B4B-PH-K-S", description=desc, footprint=PH_FP,
                pins=[Pin(num=i + 1, name=n, func=P)
                      for i, n in enumerate(("GND", "V5", "CAN_H", "CAN_L"))])


def _xcvr(tag, desc):''')
rep('''    j2 = _xh("J2", "bus B out -- the eight lever/pedal boards")''',
    '''    # ⚠ J2 IS PH AND CARRIES 5 V, NOT 24 V (user, 2026-09-21). The lever boards run off a
    # 5 V bus now (their buck is gone -- elec/lever_sensor.py), and their trunk is PH, a
    # different family from the 24 V XH motor tees so no harness can cross them. J2's +V
    # comes off this board's own +5V (the Pi rail, after F2) -- wired further down, once
    # that net exists.
    j2 = _ph("J2", "bus B out -- the eleven lever/pedal boards, 5 V, JST PH")''')
rep('''    gnd += j1[1], j2[1], j3[1], j3[4]
    v24 += j1[2], j2[2], j3[2], j3[3]''', '''    gnd += j1[1], j2[1], j3[1], j3[4]
    v24 += j1[2], j3[2], j3[3]''')
rep('''    gnd += j5[1], j5[4]
    v5 += j5[2], j5[3]''', '''    gnd += j5[1], j5[4]
    v5 += j5[2], j5[3]
    # THE LEVER BUS'S 5 V. Eleven boards at ~30 mA each (CH32V203 + SN65HVD230 + MT6701,
    # through each board's own AP2112K) is ~0.33 A on U5, which is a 3 A part sized for
    # the Pi. At a typical Pi draw (0.6-1.5 A) that is comfortable; at the full 3 A the
    # BOM budgets for the Pi it is 11 % over U5's rating -- the same "the Pi's USB ports
    # are not a free expansion slot" limit F1's note already names. And a D9 crowbar
    # event now also drops the lever bus, which is the right way round: nothing senses
    # while the Pi is dark anyway.
    v5 += j2[2]''')
open(p, 'w', encoding='utf-8').write(s)
print('ok')
