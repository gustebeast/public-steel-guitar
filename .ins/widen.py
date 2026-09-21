def edit(path, pairs):
    s=open(path,encoding='utf-8').read()
    for o,n in pairs:
        assert s.count(o)==1,(path,o[:70]); s=s.replace(o,n)
    open(path,'w',encoding='utf-8').write(s)
edit('src/chassis.py',[
('''Y_LO     = (D.string_y(D.N_STRINGS - 1) - MOTOR_PULLEY_STANDOFF - D.MOTOR_BODY_LEN
            - D.MOTOR_PCB_LEN - 2.0) - T / 2      # −Y rail off the −Y-most string (last index)''',
'''# THE GAP BEHIND STRING 10's MOTOR is its pigtail's (user, 2026-09-21: "extend the instrument
# body -y until there is enough room to fit that wiring, ensuring we don't need to cut away the
# chassis wall"). It was 2.0 -- motor PCB to rail -- and the pigtail had nowhere to go but a
# 4 mm notch cut INTO the side wall. At 4.8 the Ø3.4 cable climbs straight up behind its own
# motor like the other nine (wiring: 0.9 off the motor's back, 0.5 off the rail), and the wall
# stays whole. The body is 2.8 wider for it.
RAIL_GAP = 6 * D.BEAD
Y_LO     = (D.string_y(D.N_STRINGS - 1) - MOTOR_PULLEY_STANDOFF - D.MOTOR_BODY_LEN
            - D.MOTOR_PCB_LEN - RAIL_GAP) - T / 2   # −Y rail off the −Y-most string (last index)'''),
('''# ── motor-9 cable cutout ──────────────────────────────────────────────────
# The +X-most motor's body reaches the -Y rail, so the harness trunk corridor is blocked
# there; the trunk dips OUTBOARD into the rail behind it (wiring._rail_pts / CUTOUT_Y). We
# notch the -Y rail's inner face for those cables over that span and DROP the diamond
# lightening there (keep the rail SOLID around the notch, per the user). +X-most motor.
_M9X_CH = D.motor_pos(D.N_STRINGS - 1)[0]                 # -110
M9_CUT_X0, M9_CUT_X1 = _M9X_CH - 25.0, _M9X_CH + 35.0     # cutout X-span (covers the m9 trunk dip)
M9_CUT_YBACK = Y_LO + T / 2 - 4.0                         # notch back: inner face -> 4mm into the rail
M9_CUT_Z0, M9_CUT_Z1 = -64.0, -40.0                      # trunk Z-band (above the rib tops, over the top lane)
''','''# (the motor-9 cable NOTCH in the -Y rail is gone: RAIL_GAP makes room for that cable inside
#  the wall instead of in it)
'''),
('''    body = _rail(Y_HI).union(_rail(Y_LO))
    # motor-9 cable cutout: notch the -Y rail inner face for the trunk that dips behind the
    # +X-most motor (diamonds already dropped over this span in _rail).
    body = body.cut(box_at(M9_CUT_X1 - M9_CUT_X0, -116.0 - M9_CUT_YBACK, M9_CUT_Z1 - M9_CUT_Z0,
                           x=(M9_CUT_X0 + M9_CUT_X1) / 2, y=(M9_CUT_YBACK + -116.0) / 2,
                           z=(M9_CUT_Z0 + M9_CUT_Z1) / 2))
''','''    body = _rail(Y_HI).union(_rail(Y_LO))
'''),
('''        # at MB.HARNESS_Y1 and DIPS OUTBOARD into the rail notch behind the +X-most motor, so
        # there is nowhere down here a bay may reach the rail.''','''        # at MB.HARNESS_Y1, so there is nowhere down here a bay may reach the rail.'''),
('''        # INBOARD of the rail; the rail is the wall that closes it, and the only thing allowed
        # to reach into it is the m9 notch, which is bounded on its own.''','''        # INBOARD of the rail; the rail is the wall that closes it, and nothing reaches into it.'''),
('''        # ...and ACROSS THE M9 NOTCH it reaches back to the notch's own face. The notch takes
        # 4 mm off the rail's inner face for the trunk's outboard dip, and string 10's bay back
        # wall reaches 1.2 past that face -- so with the rail gone there, that 1.2 stood alone
        # between the notch void and the corridor void. One sliver per probe line, six of them.
        _nx0, _nx1 = max(M9_CUT_X0, b - 20.0), min(M9_CUT_X1, a + 20.0)
        if _nx1 - _nx0 > 0.1:
            seg = seg.cut(box_at(_nx1 - _nx0, _cy0 - M9_CUT_YBACK,
                                 MB.HARNESS_Z1 - MB.FLOOR_TOP,
                                 x=(_nx0 + _nx1) / 2, y=(M9_CUT_YBACK + _cy0) / 2,
                                 z=(MB.FLOOR_TOP + MB.HARNESS_Z1) / 2))
''',''),
('''        # void's own -Y face -- the rail inside, the notch's back face across the notch.''','''        # void's own -Y face -- the rail's inner face.'''),
('''        seg = seg.cut(_relief(_cy0, b - 20.0, a + 20.0))
        if _nx1 - _nx0 > 0.1:
            seg = seg.cut(_relief(M9_CUT_YBACK, _nx0, _nx1))
''','''        seg = seg.cut(_relief(_cy0, b - 20.0, a + 20.0))
'''),
])
edit('src/wiring.py',[
('''_M9X = D.motor_pos(9)[0]
M9_X0, M9_X1 = _M9X - D.MOTOR_SQ / 2 - 2.0, _M9X + D.MOTOR_SQ / 2 + 2.0
CHAN_Y = CH_WT_LANE_Y                    # -126.35: inside the trough
CUTOUT_Y = RAIL_INNER_Y - 1.25           # motor 9's pigtail lies in the rail notch itself
''','''CHAN_Y = CH_WT_LANE_Y                    # inside the trough
'''),
('''            room = back - RAIL_INNER_Y                 # from the motor's back face to the rail
            if room < WIRE_OD["motor_pigtail"] + 2.0:
                # STRING 10's back is 2.0 off the rail -- no room to climb there. Its cable lies
                # in the rail NOTCH (which exists for exactly this), runs east until it is past
                # the motor, and only then climbs to the tee's mouth height and comes back over
                # the motor's top. Under the magnetic pickup the whole way.
                _ex = mx + D.MOTOR_SQ / 2 + 4.0
                _ly = dy - (MB.STAGGER + 4.0)      # clear of this motor's own +X post band
                out.append((f"motor_pigtail_{i}", _wire([
                    (mx, back, mz), (mx, back - 1.5, mz), (_ex, back - 1.5, mz),
                    (_ex, _ly, mz), (_ex, _ly, dz), (dx, _ly, dz), (dx, dy, dz)],
                    WIRE_OD["motor_pigtail"])))
                continue
            stand = MB.BACK_T + MB.MOTOR_CLR + 2.0     # clear of the bay's back wall''','''            room = back - RAIL_INNER_Y                 # from the motor's back face to the rail
            stand = MB.BACK_T + MB.MOTOR_CLR + 2.0     # clear of the bay's back wall
            # STRING 10's bay has no back wall -- the harness corridor takes it, and the rail
            # is right there -- so its pigtail climbs hugging the motor's back instead, in the
            # chassis.RAIL_GAP left for exactly this: 0.5 off the rail. (It used to lie in a
            # notch cut into the rail and run east round the motor; the user had the body
            # widened so the wall could stay whole.)
            _od = WIRE_OD["motor_pigtail"]
            stand = min(stand, room - _od / 2.0 - 0.5)
            assert stand >= MB.MOTOR_CLR + _od / 2.0, (
                "motor %d: %.2f between its back and the -Y rail -- no room for its Ø%.1f "
                "pigtail to climb (chassis.RAIL_GAP)" % (i, room, _od))'''),
])
edit('tools/check_beads.py',[('''    CUTOUT_Y="trunk dip into the m9 rail notch; keeps the Ø2.6 USB inside the cut",
''','')])
print('ok')
