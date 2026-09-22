def edit(path, pairs):
    s=open(path,encoding='utf-8').read()
    for o,n in pairs:
        assert s.count(o)==1,(path,o[:70]); s=s.replace(o,n)
    open(path,'w',encoding='utf-8').write(s)
edit('src/wiring.py',[
('''TRUNK_PIN = {"gnd": 1, "hot": 2, "canh": 3, "canl": 4}''','''TRUNK_PIN = {"gnd": 1, "hot": 2, "canh": 3, "canl": 4}
# ...and at its own HEIGHT between tees. With the same pin order at both ends, the four
# conductors have to cross over one another near one connector or the other -- a crimped
# harness of discrete wires does exactly that, one lying over the next -- and a model can only
# show that as a height difference. 2.0 steps clear the fattest pair (O1.8 + O1.8).
TRUNK_DZ = {"gnd": -3.0, "hot": -1.0, "canh": 1.0, "canl": 3.0}'''),
('''def _seg(a, b, lane_z, d=WIRE_D, off=0.0, a_pin=None, b_pin=None):''','''def _seg(a, b, lane_z, d=WIRE_D, off=0.0, a_pin=None, b_pin=None, dz=0.0):'''),
('''        _lean = 2.0 if b[0] >= a[0] else -2.0
        pts = [a, (a[0] + _lean, lane, a[2]), (b[0] - _lean, lane, b[2]), b]''','''        _lean = 2.0 if b[0] >= a[0] else -2.0
        if a_pin is not None and b_pin is not None:
            # PIN TO PIN: straight out of each pin's own contact, then along its own lane at
            # its own height (TRUNK_DZ) -- see TRUNK_PIN for why
            z = a[2] + dz
            ly = lane + off
            return _wire([a_pin, (a_pin[0], a_pin[1] - 1.5, z), (a_pin[0], ly, z),
                          (b_pin[0], ly, z), (b_pin[0], b_pin[1] - 1.5, z), b_pin], d)
        pts = [a, (a[0] + _lean, lane, a[2]), (b[0] - _lean, lane, b[2]), b]'''),
('''                             off=TRUNK_OFF["can" + _sfx],
                             a_pin=_pin(west[k], "can" + _sfx, True),
                             b_pin=_pin(west[k + 1], "can" + _sfx, False))))''','''                             off=TRUNK_OFF["can" + _sfx],
                             a_pin=_pin(west[k], "can" + _sfx, True),
                             b_pin=_pin(west[k + 1], "can" + _sfx, False),
                             dz=TRUNK_DZ["can" + _sfx])))'''),
('''                             a_pin=_pin(west[k + 1], _cond, False),
                             b_pin=_pin(west[k], _cond, True))))''','''                             a_pin=_pin(west[k + 1], _cond, False),
                             b_pin=_pin(west[k], _cond, True), dz=TRUNK_DZ[_cond])))'''),
])
print('ok')
