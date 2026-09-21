p='src/electronics.py'; s=open(p,encoding='utf-8').read()
a=s.index('''    from cadkit.pcb import pcb_cradle
    from cadkit.fasteners import M4 as _M4
    from .helpers import box_at
    body = None''')
b=s.index('''    body = body.union(cr)
    return stand(body) if standing else body
''')+len('''    body = body.union(cr)
    return stand(body) if standing else body
''')
new='''    from cadkit.fasteners import M4 as _M4, M4_BUTTON_HEAD_D, cut_anchor as _cut_anchor
    from cadkit.pcb import pcb_hold_xy
    from .helpers import box_at
    zb = RIB_LZ - TRAY_Z1          # cradle frame: the endplate's wall, -26.5 below the mount face
    CLR, WALL, LIP = 0.3, D.MIN_WALL_2P, 1.2

    def _cyl_col(x, y, d, z0, z1):
        return cq.Workplane("XY").add(cq.Solid.makeCylinder(d / 2.0, z1 - z0, cq.Vector(x, y, z0)))

    def _frame(bw, bl, boss_xy):
        """A board cradle made ONLY of columns rising from the endplate wall (local z `zb`)
        to the board: a ring round the board -- a LIP under its edge to carry it, then on up
        0.8 past its top as the locating wall, open above the board on -Y (the harness side)
        -- and an M4 boss column at `boss_xy`, the insert in its top. Centred on the board."""
        ox, oy = bw / 2 + CLR + WALL, bl / 2 + CLR + WALL
        top = POST_H + BD_T + 0.8
        ring = (box_at(2 * ox, 2 * oy, POST_H - zb, x=0.0, y=0.0, z=(zb + POST_H) / 2)
                .cut(box_at(bw - 2 * LIP, bl - 2 * LIP, 80.0, x=0.0, y=0.0, z=0.0)))
        wall = (box_at(2 * ox, 2 * oy, top - POST_H, x=0.0, y=0.0, z=(POST_H + top) / 2)
                .cut(box_at(bw + 2 * CLR, bl + 2 * CLR, 80.0, x=0.0, y=0.0, z=0.0))
                .cut(box_at(2 * ox + 2, 2 * WALL + 2 * CLR + 2, 80.0, x=0.0, y=-bl / 2, z=0.0)))
        cr = ring.union(wall).union(_cyl_col(boss_xy[0], boss_xy[1], _M4.boss_od, zb, POST_H))
        return cr

    # ── BOTH BOARDS: HOLLOW FRAMES OF COLUMNS, NO PLATE (user, 2026-09-21) ────────────────
    # They used to be pcb_cradle plates standing on ribs 27 mm off the endplate wall, and the
    # user read it right: the ribs cut the plates' bridges to 10 mm, but a bridge is still an
    # overhang, and each plate was 5.3 mm thick everywhere only because the M4 insert needed
    # 8.5 mm of depth in ONE spot. This endplate prints standing on its -X face, so anything
    # lying across the build axis is a ceiling -- the fix is to have nothing lying across it.
    # Every piece of these cradles is a COLUMN rising from the endplate wall straight to the
    # board. The boards need no floor: the motor controller is single-sided, and the Pi's
    # underside has only the GPIO header's tails, 1 mm inboard of the lip.

    # THE MOTOR CONTROLLER: the M4 goes THROUGH its mounting ear (elec/motor_ctrl.py EAR_*).
    x0, x1, y0, y1 = MCTRL_FP
    y1 = y1 + MCTRL_EAR_H
    bw, bl = x1 - x0, y1 - y0
    hx, hy = MCTRL_HOLE[0], MCTRL_HOLE[1] - MCTRL_EAR_H / 2.0
    cr = _frame(bw, bl, (hx, hy))
    # the USB-C (J4) sits ON the -Y edge; its shell's THT legs come through beside it, so
    # the lip steps back from under it and the board rests on the rest of the ring there
    _uw, _ul, _uh, _ux, _uy = MCTRL_USB
    cr = cr.cut(box_at(_uw + 1.0, 2 * LIP + 2 * CLR + 1.0, 2 * POST_H,
                       x=_ux, y=-bl / 2 + LIP / 2, z=POST_H))
    cr = _cut_anchor(_M4, cr, (hx, hy, POST_H), (0, 0, -1), _M4.anchor_min_wall)
    mc = cr.translate(((x0 + x1) / 2.0, (y0 + y1) / 2.0, TRAY_Z1))

    # THE PI: a purchased board, holes too small for M4, so its M4 stands BESIDE the +Y edge
    # (pcb_hold_xy, the same spot pcb_cradle's hold_edge uses) and the wall is notched for
    # the head. ⚠ AND ITS COLUMNS MOSTLY LAND ON THE NUT HARDWARE'S BLOCK, NOT THE WALL: the
    # height-adjust prism fills x -630..-610.1 behind it, cut through by the insert slots.
    # So the columns are built to the wall and then `pi_cut` (keyhead_endplate: the slots,
    # plus everything straight above them) takes away whatever would land in a slot or hang
    # over one. What is left stands on a fin between slots, on the solid band along the
    # board's -Z edge, or -- past both ends of the block -- on the wall itself.
    x0, x1, y0, y1 = PI_FP
    pw, pl = x1 - x0, y1 - y0
    phx, phy = pcb_hold_xy(pw, pl, "+y", hold_at=0.0, clr=CLR, spec=_M4)
    cr = _frame(pw, pl, (phx, phy))
    cr = cr.cut(_cyl_col(phx, phy, M4_BUTTON_HEAD_D + 2 * CLR, POST_H, POST_H + 20.0))
    cr = _cut_anchor(_M4, cr, (phx, phy, POST_H), (0, 0, -1), _M4.anchor_min_wall)
    pi = cr.translate(((x0 + x1) / 2.0, (y0 + y1) / 2.0, TRAY_Z1))
    if not standing:
        return mc.union(pi)
    pi = stand(pi)
    if pi_cut is not None:
        pi = pi.cut(pi_cut)
    return stand(mc).union(pi)
'''
s=s[:a]+new+s[b:]
s=s.replace('def keyhead_cradles(standing: bool = True) -> cq.Workplane:','def keyhead_cradles(standing: bool = True, pi_cut=None) -> cq.Workplane:')
open(p,'w',encoding='utf-8').write(s)
