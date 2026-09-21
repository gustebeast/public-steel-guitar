def edit(path, pairs):
    s=open(path,encoding='utf-8').read()
    for o,n in pairs:
        assert s.count(o)==1,(path,o[:70]); s=s.replace(o,n)
    open(path,'w',encoding='utf-8').write(s)
edit('src/wiring.py',[
('''RAIL_INNER_Y = _Y_LO + _RAIL_T / 2                       # -128.75: -Y rail inner face
RAIL_Y = RAIL_INNER_Y + 4.5                              # the old floor-level corridor, which
                                                         # only bus B still uses at the keyhead''',
'''RAIL_INNER_Y = _Y_LO + _RAIL_T / 2                       # -131.55: -Y rail inner face
# the old floor-level corridor, which only bus B still uses at the keyhead. Held where it was
# (-124.25) when the body widened for string 10's pigtail (chassis.RAIL_GAP): nothing on it
# wanted to move, and following the wall out put bus B across the Pi link's riser.
from .chassis import RAIL_GAP as _RAIL_GAP
RAIL_Y = RAIL_INNER_Y + 4.5 + (_RAIL_GAP - 2.0)'''),
('''            out.append((f"motor_pigtail_{i}", _wire([
                (mx, back, mz), (mx, back - stand, mz), (mx, back - stand, dz),
                (dx, back - stand, dz), (dx, dy, dz)],
                WIRE_OD["motor_pigtail"])))
            continue''',
'''            _yc = back - stand
            if _yc - _od / 2.0 < CHAN_Y + 2.5:
                # ...and it climbs RIGHT UNDER THE TROUGH'S LANES, which carry on over this
                # motor at CHAN_Y where the trough is left out. Its tee's mouth is at feed 2's
                # height, so rising to it and turning east ran 21 mm along inside that cable.
                # So it crosses onto the motor at the motor's own top, UNDER the lanes, and
                # only rises to the mouth once it is +Y of them.
                _zc = D.MOTOR_BELT_Z + D.MOTOR_SQ / 2 + _od / 2.0 + 0.35
                assert _zc + _od / 2.0 < LANE_PWR2 - PWR_OFF - 0.9 - 0.3, (
                    "motor %d's pigtail cannot pass under the trough lanes" % i)
                _yi = CHAN_Y + 2.5 + _od / 2.0 + 1.0
                out.append((f"motor_pigtail_{i}", _wire([
                    (mx, back, mz), (mx, _yc, mz), (mx, _yc, _zc), (mx, _yi, _zc),
                    (mx, _yi, dz), (dx, _yi, dz), (dx, dy, dz)], _od)))
                continue
            out.append((f"motor_pigtail_{i}", _wire([
                (mx, back, mz), (mx, back - stand, mz), (mx, back - stand, dz),
                (dx, back - stand, dz), (dx, dy, dz)],
                WIRE_OD["motor_pigtail"])))
            continue'''),
])
print('ok')
