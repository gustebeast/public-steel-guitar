def edit(path, pairs):
    s=open(path,encoding='utf-8').read()
    for o,n in pairs:
        assert s.count(o)==1,(path,o[:70]); s=s.replace(o,n)
    open(path,'w',encoding='utf-8').write(s)
edit('src/wiring.py',[
('''TRUNK_OFF = {"hot": -2.7, "canh": -0.9, "canl": 0.9, "gnd": 2.7}''',
'''# ...IN THE CONNECTOR'S OWN PIN ORDER (GND, 24 V, CAN-H, CAN-L on 1-4 / 5-8 -- can_tee J1),
# so each conductor runs from its own pin to its own lane without crossing a neighbour.
TRUNK_OFF = {"gnd": -2.7, "hot": -0.9, "canh": 0.9, "canl": 2.7}
# ...and each LANDS on its own pin. All of them used to end on the 8-way's centre, so the
# cables arriving at a tee and leaving it ran through each other for 10-20 mm (nine pairs in
# check_cable_pairs, the worst 9.5 mm3). In on 1-4 from the WEST, out on 5-8 to the EAST.
TRUNK_PIN = {"gnd": 1, "hot": 2, "canh": 3, "canl": 4}
_XH_PITCH = 2.5'''),
('''def tee_point(i, x, y, which="trunk"):''','''def tee_pin(i, x, y, cond, out):
    """Tee i's trunk 8-way, the pin carrying `cond` (TRUNK_PIN key) on its IN (1-4) or OUT
    (5-8) half -- pin 1 at the connector's -X end."""
    px, py, pz = tee_point(i, x, y)
    pin = TRUNK_PIN[cond] + (4 if out else 0)
    return (px + (pin - (EL.TEE_TRUNK_N + 1) / 2.0) * _XH_PITCH, py, pz)


def tee_point(i, x, y, which="trunk"):'''),
('''def _seg(a, b, lane_z, d=WIRE_D, off=0.0):''','''def _seg(a, b, lane_z, d=WIRE_D, off=0.0, a_pin=None, b_pin=None):'''),
('''    return _wire([(px + off, py + off, pz) for px, py, pz in pts], d)


''','''    pts = [(px + off, py + off, pz) for px, py, pz in pts]
    if a_pin is not None:
        pts[0] = a_pin
    if b_pin is not None:
        pts[-1] = b_pin
    return _wire(pts, d)


'''),
# CAN hops + head
('''    _canA_head = [_ia, (BAY_X - 5.0, _ia[1], _ia[2]), (BAY_X - 5.0, _ia[1], _w0[2]),
                  (_w0[0], _ia[1], _w0[2]), _w0]
    for _sfx, _co in (("h", -CAN_OFF), ("l", CAN_OFF)):
        _od = WIRE_OD[f"wire_can{_sfx}"]
        out.append((f"wire_can{_sfx}_0", _wire(
            [(px + _co, py + _co, pz) for px, py, pz in _canA_head], _od)))
        for k in range(9):
            out.append((f"wire_can{_sfx}_{k + 1}",
                        _seg(hdrA[west[k]], hdrA[west[k + 1]], LANE_CAN, _od,
                             off=TRUNK_OFF["can" + _sfx])))''',
'''    def _pin(i, cond, out):
        return tee_pin(i, tees[i][0], tees[i][1], cond, out)

    for _sfx, _co in (("h", -CAN_OFF), ("l", CAN_OFF)):
        _od = WIRE_OD[f"wire_can{_sfx}"]
        _p = _pin(west[0], "can" + _sfx, False)          # the first tee's IN pin
        out.append((f"wire_can{_sfx}_0", _wire(
            [(px + _co, py + _co, pz) for px, py, pz in
             [_ia, (BAY_X - 5.0, _ia[1], _ia[2]), (BAY_X - 5.0, _ia[1], _w0[2])]]
            + [(_p[0], _ia[1] + _co, _w0[2]), _p], _od)))
        for k in range(9):
            out.append((f"wire_can{_sfx}_{k + 1}",
                        _seg(hdrA[west[k]], hdrA[west[k + 1]], LANE_CAN, _od,
                             off=TRUNK_OFF["can" + _sfx],
                             a_pin=_pin(west[k], "can" + _sfx, True),
                             b_pin=_pin(west[k + 1], "can" + _sfx, False))))'''),
# pwr head ends at the east tee's OUT pins
('''    def _head(dz):
        """J7 -> the east-most tee's trunk connector (on string 10's motor)."""
        zr, zl = _REC_Z7 + dz, LANE_PWR + dz
        loop = _loop(zr)
        return _pair([_j7, (_j7[0], _j7[1], zr), (_j7[0], _REC_Y, zr), (_BAY_X7, _REC_Y, zr),
                      (_BAY_X7, CHAN_Y, zr)] + loop
                     + [(_RISE7, CHAN_Y, loop[-1][2]), (_RISE7, CHAN_Y, zl),
                        (_EXIT7, CHAN_Y, zl), (_EXIT7, y10, zl), (x10, y10, zl),
                        hdrA[_WEST0]], dz)''',
'''    def _head(dz, cond):
        """J7 -> the east-most tee's trunk connector (on string 10's motor), onto its OUT
        pin for `cond` -- dropping straight down onto it from the lane."""
        zr, zl = _REC_Z7 + dz, LANE_PWR + dz
        loop = _loop(zr)
        _p = _pin(_WEST0, cond, True)
        return _pair([_j7, (_j7[0], _j7[1], zr), (_j7[0], _REC_Y, zr), (_BAY_X7, _REC_Y, zr),
                      (_BAY_X7, CHAN_Y, zr)] + loop
                     + [(_RISE7, CHAN_Y, loop[-1][2]), (_RISE7, CHAN_Y, zl),
                        (_EXIT7, CHAN_Y, zl), (_EXIT7, y10, zl)], dz) + [
                        (_p[0], y10, zl), (_p[0], _p[1], zl), _p]'''),
('''    _mc24 = SP(*EL.mctrl_pt("J3"))
    tail = [_w0, (BAY_X, _w0[1], _w0[2]), (BAY_X, _mc24[1], _w0[2]),
            (BAY_X, _mc24[1], _mc24[2]), _mc24]''',
'''    _mc24 = SP(*EL.mctrl_pt("J3"))
    # the tail leaves the first tee's IN pins and runs west ABOVE the CAN head, which comes
    # in along the same stretch at the tee's own height (the two crossed at x -582)
    _TAIL_DZ = 3.5

    def _tail(cond, do):
        _p = _pin(west[0], cond, False)
        zt = _w0[2] + _TAIL_DZ + do
        return [_p, (_p[0], _p[1], zt), (BAY_X + do, _p[1], zt), (BAY_X + do, _mc24[1], zt),
                (BAY_X + do, _mc24[1], _mc24[2] + do), (_mc24[0], _mc24[1], _mc24[2] + do)]'''),
('''    _FEED2_X = BAY_X + 3.0''','''    _FEED2_X = BAY_X + 4.5            # 3.0 put it 1.0 off the tail's column (1.6 mm3)'''),
('''        out.append((f"{_nm}_0", _wire(_head(_do), WIRE_OD[_nm])))
        for k in range(9):
            out.append((f"{_nm}_{k + 2}",
                        _seg(hdrA[west[k + 1]], hdrA[west[k]], LANE_PWR, WIRE_OD[_nm],
                             off=TRUNK_OFF[_nm[9:]])))''',
'''        _cond = _nm[9:]
        out.append((f"{_nm}_0", _wire(_head(_do, _cond), WIRE_OD[_nm])))
        for k in range(9):
            out.append((f"{_nm}_{k + 2}",
                        _seg(hdrA[west[k + 1]], hdrA[west[k]], LANE_PWR, WIRE_OD[_nm],
                             off=TRUNK_OFF[_cond],
                             a_pin=_pin(west[k + 1], _cond, False),
                             b_pin=_pin(west[k], _cond, True))))'''),
('''        out.append((f"{_nm}_11", _wire([(x + _do, y, z + _do) for x, y, z in tail],
                                       WIRE_OD[_nm])))''','''        out.append((f"{_nm}_11", _wire(_tail(_cond, _do), WIRE_OD[_nm])))'''),
])
print('ok')
