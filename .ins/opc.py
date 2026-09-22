p='src/bridge_endplate.py'; s=open(p,encoding='utf-8').read()
o='''    (hx, hy, _hd), = _BG.holes("output_panel")
    cr = pcb_cradle(OP_BOARD_X, OP_BOARD_Y, screw_xy=(hx, hy), spec=_M4, open_edge=None,
                    standoff=standoff, clr=OP_PANEL_CLR)'''
n='''    (hx, hy, _hd), = _BG.holes("output_panel")
    # THE CRADLE IS THE BOARD'S RECTANGLE, NOT ITS BOX (user, 2026-09-21: the -X wall made
    # print overhangs and no real retention, and "a little prism ... doesn't seem to do
    # anything"). Sized to the bounding box it carried floor, a curb and a corner pad beside
    # the ear where there is no board. The ear is carried by the M4 boss alone, the -X side
    # is open (the way in, and nothing the screw does not already hold), and the rectangle's
    # own +Y edge -- which only the rectangle spans -- is what finds it in the outline.
    _poly = _BG.load("output_panel")["outline_poly"]
    _ymax = max(p[1] for p in _poly)
    _rx0 = min(p[0] for p in _poly if abs(p[1] - _ymax) < 1e-6)
    _rx1 = max(p[0] for p in _poly)
    rw, rcx = _rx1 - _rx0, (_rx0 + _rx1) / 2.0        # rectangle width and centre (geom frame)
    hx -= rcx                                         # the cradle is built about the rectangle
    cr = pcb_cradle(rw, OP_BOARD_Y, screw_xy=(hx, hy), spec=_M4, open_edge="-x",
                    standoff=standoff, clr=OP_PANEL_CLR)'''
assert s.count(o)==1; s=s.replace(o,n)
o='''    cr = cr.cut(box_at(20.0, OP_BOARD_Y + 40.0, 60.0,
                       x=OP_BOARD_X / 2 + OP_PANEL_CLR + 10.0, y=0.0, z=0.0))
    # -X WALL, above the board's underside only: that is the way in. What stays below is a
    # curb the board slides over, and the screw's boss, which pcb_cradle stood on the
    # mounting surface and topped at the board's underside -- so this cut leaves it whole.
    cr = cr.cut(box_at(20.0, OP_BOARD_Y + 40.0, 60.0,
                       x=-(OP_BOARD_X / 2 + OP_PANEL_CLR + 10.0), y=0.0,
                       z=standoff + 30.0))'''
n='''    cr = cr.cut(box_at(20.0, OP_BOARD_Y + 40.0, 60.0,
                       x=rw / 2 + OP_PANEL_CLR + 10.0, y=0.0, z=0.0))'''
assert s.count(o)==1; s=s.replace(o,n)
o='''    return cr.translate((cx, cy, cz - standoff))'''
n='''    return cr.translate((cx + rcx, cy, cz - standoff))'''
assert s.count(o)==1; s=s.replace(o,n)
open(p,'w',encoding='utf-8').write(s)
