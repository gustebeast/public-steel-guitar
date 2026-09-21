b=''
def edit(path, pairs):
    s=open(path,encoding='utf-8').read()
    for o,n in pairs:
        assert s.count(o)==1,(path,o[:60]); s=s.replace(o,n)
    open(path,'w',encoding='utf-8').write(s)
edit('src/electronics.py',[('''def electronics_tray(standing: bool = True) -> cq.Workplane:''','''def board_screws():
    """The M4 through each of OUR boards' mounting ears: [(name, solid)] -- an M4x10 button
    head seated on the board's top face and its heat-set insert in the boss below, placed
    from the same hole the cradles are bored from. The motor controller's is authored in
    the flat tray frame and stood up with the board; the output board's is world-vertical."""
    from cadkit.fasteners import M4 as _M4, M4_BUTTON_HEAD_H, m4_button_screw, seated_insert
    L = 10.0                                   # M4x10: 1.6 of board, 8.4 into the 8.5 anchor
    assert L - _PCB_T <= _M4.anchor_min_wall + 1e-9
    out = []
    cx, cy = _ctr(MCTRL_FP)
    tx, ty = cx + MCTRL_HOLE[0], cy + MCTRL_HOLE[1]
    out.append(("board_insert_0", stand(seated_insert(_M4, (tx, ty, BOARD_Z), (0, 0, -1)))))
    out.append(("board_screw_0", stand(m4_button_screw(L).translate(
        (tx, ty, BOARD_Z + BD_T + M4_BUTTON_HEAD_H)))))
    ox, oy, oz = op_origin()
    (hx, hy, _hd), = BG.holes("output_panel")
    out.append(("board_insert_1", seated_insert(_M4, (ox + hx, oy + hy, oz), (0, 0, -1))))
    out.append(("board_screw_1", m4_button_screw(L).translate(
        (ox + hx, oy + hy, oz + _PCB_T + M4_BUTTON_HEAD_H))))
    return out


def electronics_tray(standing: bool = True) -> cq.Workplane:''')])
edit('src/build.py',[('''           ("output_panel", EL.output_panel()),
''','''           ("output_panel", EL.output_panel()),
''' ),('''    "tee_insert":      (0.72, 0.60, 0.30),''','''    "tee_insert":      (0.72, 0.60, 0.30),
    "board_screw":     (0.72, 0.74, 0.78),   # M4x10 button THROUGH our boards' mounting ears
    "board_insert":    (0.72, 0.60, 0.30),   # its heat-set brass, in the cradle boss''')])
s=open('src/build.py',encoding='utf-8').read()
o='''           ("oled", EL.oled()), ("joystick", EL.joystick())]
'''
assert s.count(o)==1
s=s.replace(o,o+'''    out += EL.board_screws()
''')
open('src/build.py','w',encoding='utf-8').write(s)
