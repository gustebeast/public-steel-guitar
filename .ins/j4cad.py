def edit(path, pairs):
    s=open(path,encoding='utf-8').read()
    for o,n in pairs:
        assert s.count(o)==1,(path,o[:70]); s=s.replace(o,n)
    open(path,'w',encoding='utf-8').write(s)
edit('src/electronics.py',[
('''           for r in ("J1", "J2", "J3", "J5")}          # J1 bus A, J2 bus B, J3 24 V, J5 5 V
_u = _mctrl_fab("J4")                                   # USB-C to the Pi, on the -Y edge
MCTRL_USB = (_u[1] - _u[0], _u[3] - _u[2],
             BG.HEIGHT["USB_C_Receptacle_HRO_TYPE-C-31-M-12"],
             (_u[0] + _u[1]) / 2, (_u[2] + _u[3]) / 2)
''','''           for r in ("J1", "J2", "J3", "J4", "J5")}
# J1 bus A, J2 bus B, J3 24 V, J4 the USB link to the Pi (a top-entry XH now -- the USB-C it
# replaced faced the -Y rail 5.5 mm away and could not be plugged in), J5 5 V to the Pi
'''),
('''    connector `ref` -- so wiring.py asks the board where its connectors are
    instead of carrying a copy of the layout. The three XH leads exit +Z off
    the top of a mated plug; the USB-C lead exits the mouth horizontally, which
    the board's 90 deg turn in the tray points at +X.''','''    connector `ref` -- so wiring.py asks the board where its connectors are
    instead of carrying a copy of the layout. Every lead, the USB link's included,
    leaves +Z off the top of a mated XH plug.'''),
('''    if ref == "J4":
        _w, l, h, ox, oy = MCTRL_USB
        x, y = to_tray(ox, oy - l / 2.0)
        return (x, y, BOARD_Z + BD_T + h / 2.0)
    bx, by, _rot = MCTRL_J[ref]''','''    bx, by, _rot = MCTRL_J[ref]'''),
])
s=open('src/electronics.py',encoding='utf-8').read()
a=s.index('''    # the USB-C (J4) sits ON the -Y edge; its shell's THT legs come through beside it, so''')
b=s.index('''    cr = _cut_anchor(_M4, cr, (hx, hy, POST_H), (0, 0, -1), _M4.anchor_min_wall)''',a)
s=s[:a]+s[b:]
open('src/electronics.py','w',encoding='utf-8').write(s)
