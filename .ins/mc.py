b = r'C:/Users/gus/Sync/Documents/Archive/3D/public-steel-guitar-bronner/'
def edit(path, pairs):
    s = open(b + path, encoding='utf-8').read()
    for old, new in pairs:
        assert s.count(old) == 1, (path, old[:70])
        s = s.replace(old, new)
    open(b + path, 'w', encoding='utf-8').write(s)

edit('src/board_geom.py', [('''        cx = sum(p[0] for p in h) / len(h)
        cy = sum(p[1] for p in h) / len(h)
        r = sum(math.hypot(p[0] - cx, p[1] - cy) for p in h) / len(h)
        out.append((cx, cy, 2.0 * r))''', '''        # the BOX centre, not the vertex mean: KiCad spaces an arc's points unevenly, and
        # the mean of the motor controller's came out 0.8 mm off its hole
        xs, ys = [p[0] for p in h], [p[1] for p in h]
        out.append(((min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0,
                    max(max(xs) - min(xs), max(ys) - min(ys))))''')])

edit('src/electronics.py', [
('''    for fp in (PI_FP, MCTRL_FP):
        x0, x1, y0, y1 = fp
        cr = pcb_cradle(x1 - x0, y1 - y0, open_edge="-y",
                        hold_edge="+y", hold_at=0.0, hold_spec=_M4,
                        standoff=POST_H, clr=0.3)
        cr = cr.translate(((x0 + x1) / 2.0, (y0 + y1) / 2.0, TRAY_Z1))''',
'''    from cadkit.fasteners import cut_anchor as _cut_anchor
    for fp in (PI_FP, MCTRL_FP):
        x0, x1, y0, y1 = fp
        if fp is MCTRL_FP:
            # ⚠ THE MOTOR CONTROLLER'S M4 GOES THROUGH THE BOARD (user, 2026-09-21: "the
            # screw adjacent ... doesn't provide as strong of retention"). The board grew a
            # mounting EAR off its +Y edge (elec/motor_ctrl.py EAR_*), so the cradle is sized
            # to the board's box INCLUDING the ear and the screw goes down through the ear's
            # hole into a boss. pcb_cradle's through-board boss is sized for M2 ("pad + 1.5"),
            # so cadkit's M4 boss is stood under the hole and the anchor re-cut after the
            # union, as the output board's is (bridge_endplate.op_cradle).
            # The Pi is a PURCHASED board -- its holes are M2.5 -- so it keeps the M4 beside
            # its +Y edge.
            y1 = y1 + MCTRL_EAR_H
            hx, hy = MCTRL_HOLE[0], MCTRL_HOLE[1] - MCTRL_EAR_H / 2.0
            cr = pcb_cradle(x1 - x0, y1 - y0, screw_xy=(hx, hy), spec=_M4, open_edge="-y",
                            standoff=POST_H, clr=0.3)
            _bt = max(1.6, _M4.anchor_min_wall - POST_H)
            cr = cr.union(cq.Workplane("XY").add(cq.Solid.makeCylinder(
                _M4.boss_od / 2.0, _bt + POST_H, cq.Vector(hx, hy, -_bt))))
            cr = _cut_anchor(_M4, cr, (hx, hy, POST_H), (0, 0, -1), _M4.anchor_min_wall)
        else:
            cr = pcb_cradle(x1 - x0, y1 - y0, open_edge="-y",
                            hold_edge="+y", hold_at=0.0, hold_spec=_M4,
                            standoff=POST_H, clr=0.3)
        cr = cr.translate(((x0 + x1) / 2.0, (y0 + y1) / 2.0, TRAY_Z1))'''),
('''    b = box_at(MCTRL_BOARD_X, MCTRL_BOARD_Y, _PCB_T, x=0.0, y=0.0, z=_PCB_T / 2)
    for ref, (jx, jy, rot) in MCTRL_J.items():''',
'''    # the laminate as ROUTED -- the rectangle plus its +Y mounting ear, minus the M4 hole
    b = (cq.Workplane("XY").polyline(MCTRL_OUTLINE).close().extrude(_PCB_T)
         .cut(cq.Workplane("XY").add(cq.Solid.makeCylinder(
             MCTRL_HOLE[2] / 2.0, _PCB_T + 2.0,
             cq.Vector(MCTRL_HOLE[0], MCTRL_HOLE[1], -1.0)))))
    for ref, (jx, jy, rot) in MCTRL_J.items():'''),
('''MCTRL_USB = (10.73, 9.51, 3.26, 0.0, -23.31)''',
'''# THE MOUNTING EAR, read off the ROUTED board (elec/geom/motor_ctrl.geom.json), moved into
# this file's frame: the rectangle's centre, which is what MCTRL_FP, MCTRL_J and MCTRL_BOM
# are all written about. The geom file centres on the outline's BOX, which the ear pushes
# +Y by half its height.
def _mctrl_ear():
    from . import board_geom as _BG
    poly = _BG.load("motor_ctrl")["outline_poly"]
    ymin = min(p[1] for p in poly)
    dy = -ymin - MCTRL_BOARD_Y / 2.0                  # geom frame -> rectangle frame
    out = [(p[0], p[1] + dy) for p in poly]
    (hx, hy, hd), = _BG.holes("motor_ctrl")
    ear_h = max(p[1] for p in out) - MCTRL_BOARD_Y / 2.0
    return out, (hx, hy + dy, hd), ear_h


MCTRL_OUTLINE, MCTRL_HOLE, MCTRL_EAR_H = _mctrl_ear()
MCTRL_USB = (10.73, 9.51, 3.26, 0.0, -23.31)'''),
])
print('ok')
