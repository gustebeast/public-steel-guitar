def edit(path, pairs):
    s=open(path,encoding='utf-8').read()
    for o,n in pairs:
        assert s.count(o)==1,(path,o[:70]); s=s.replace(o,n)
    open(path,'w',encoding='utf-8').write(s)
edit('src/board_geom.py',[
('''    "TestPoint_Pad_D1.5mm": 0.0,       # bare copper
}''','''    "TestPoint_Pad_D1.5mm": 0.0,       # bare copper
    # the motor controller's (2026-09-21), package max heights off the JEDEC outlines / the
    # makers' drawings -- the old hand table carried the same 1.75 / 1.10 for these
    "SOIC-8_3.9x4.9mm_P1.27mm": 1.75, "SOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.29x3mm": 1.75,
    "D_SMB": 2.45, "Fuse_1206_3216Metric": 1.10, "R_0603_1608Metric": 0.55,
    "L_Bourns-SRN6028": 2.80,
}
# a top-entry XH with its XHP plug seated: 9.8 over the board (JST's "assembled board
# height"), which is what a housing has to leave room for -- see solid(mated=True)
_XH_MATED_H = 9.8'''),
('''def solid(board: str) -> cq.Workplane:
    """The board in its OWN frame: centred on the origin in XY, underside at z = 0, parts
    rising +Z. Every part is its routed F.Fab body extruded to its HEIGHT, and a panel
    connector with a nose gets that too."""''','''def solid(board: str, mated: bool = False) -> cq.Workplane:
    """The board in its OWN frame: centred on the origin in XY, underside at z = 0, parts
    rising +Z. Every part is its routed F.Fab body extruded to its HEIGHT, and a panel
    connector with a nose gets that too. `mated=True` stands every top-entry XH at its
    plugged height -- the envelope a housing has to clear, not the bare header."""'''),
('''        h = HEIGHT[fp_name(f["fpid"])]
        if h <= 0.0:''','''        h = HEIGHT[fp_name(f["fpid"])]
        if mated and fp_name(f["fpid"]).startswith("JST_XH_") and "Vertical" in f["fpid"]:
            h = _XH_MATED_H
        if h <= 0.0:'''),
])
s=open('src/electronics.py',encoding='utf-8').read()
a=s.index('''# Pad-row centres, board-local, straight out of elec/motor_ctrl.py's placements.''')
b=s.index('''def motor_ctrl_pcb(mating: bool = False) -> cq.Workplane:''')
e=s.index('''def mctrl_pt(ref: str):''')
new_consts='''# THE MOUNTING EAR, read off the ROUTED board (elec/geom/motor_ctrl.geom.json), moved into
# this file's frame: the rectangle's centre, which is what MCTRL_FP is written about. The
# geom file centres on the outline's BOX, which the ear pushes +Y by half its height.
def _mctrl_ear():
    poly = BG.load("motor_ctrl")["outline_poly"]
    ymin = min(p[1] for p in poly)
    dy = -ymin - MCTRL_BOARD_Y / 2.0                  # geom frame -> rectangle frame
    out = [(p[0], p[1] + dy) for p in poly]
    (hx, hy, hd), = BG.holes("motor_ctrl")
    ear_h = max(p[1] for p in out) - MCTRL_BOARD_Y / 2.0
    return out, (hx, hy + dy, hd), ear_h, dy


MCTRL_OUTLINE, MCTRL_HOLE, MCTRL_EAR_H, _MCTRL_DY = _mctrl_ear()


def _mctrl_fab(ref):
    """(x0, x1, y0, y1) of a part's routed F.Fab body, in the rectangle frame."""
    x0, x1, y0, y1 = BG.footprint("motor_ctrl", ref)["fab"]
    return x0, x1, y0 + _MCTRL_DY, y1 + _MCTRL_DY


# ⚠ EVERY PART OF THIS BOARD IS READ OFF THE ROUTED BOARD NOW (2026-09-21). It was a hand
# table -- sixty rows of courtyard boxes and pad-row centres typed from motor_ctrl.py's
# placements -- and cad_geom_check found 8 of its 60 parts not where the router left them.
# A copy of the layout's INPUT cannot know where the layout's OUTPUT put anything; the same
# export the output board's CAD reads (elec/geom/*.geom.json) can.
# The connectors wiring.py asks about: each lead leaves its body's centre.
MCTRL_J = {r: ((_f := _mctrl_fab(r))[0] / 2 + _f[1] / 2, _f[2] / 2 + _f[3] / 2,
               BG.footprint("motor_ctrl", r)["rot"])
           for r in ("J1", "J2", "J3", "J5")}          # J1 bus A, J2 bus B, J3 24 V, J5 5 V
_u = _mctrl_fab("J4")                                   # USB-C to the Pi, on the -Y edge
MCTRL_USB = (_u[1] - _u[0], _u[3] - _u[2],
             BG.HEIGHT["USB_C_Receptacle_HRO_TYPE-C-31-M-12"],
             (_u[0] + _u[1]) / 2, (_u[2] + _u[3]) / 2)


'''
new_pcb='''def motor_ctrl_pcb(mating: bool = False) -> cq.Workplane:
    """The motor controller, in its OWN frame: the rectangle centred on the origin in XY
    (its mounting ear off the +Y edge), underside at z=0, every part rising +Z -- the
    ROUTED board (board_geom.solid), not a table. `mating=True` stands the XH headers at
    their plugged height, which is the volume a housing has to leave alone."""
    return BG.solid("motor_ctrl", mated=mating).translate((0.0, _MCTRL_DY, 0.0))


'''
s=s[:a]+new_consts+new_pcb+s[e:]
# drop the earlier _mctrl_ear definition block (now above) -- it sat before MCTRL_USB originally
open('src/electronics.py','w',encoding='utf-8').write(s)
