p='src/electronics.py'; s=open(p,encoding='utf-8').read()
a=s.index("    from cadkit.fasteners import cut_anchor as _cut_anchor\n    for fp in (PI_FP, MCTRL_FP):")
end_marker="        body = cr if body is None else body.union(cr)\n"
b=s.index(end_marker, a)+len(end_marker)
new='''    from cadkit.fasteners import cut_anchor as _cut_anchor
    from cadkit.pcb import pcb_hold_xy
    zb = RIB_LZ - TRAY_Z1          # cradle frame: the endplate's wall, -26.5 below the mount face

    def _cyl_col(x, y, d, z0, z1):
        return cq.Workplane("XY").add(cq.Solid.makeCylinder(d / 2.0, z1 - z0, cq.Vector(x, y, z0)))

    # ── THE MOTOR CONTROLLER: A HOLLOW FRAME, NO PLATE (user, 2026-09-21) ──────────────────
    # It used to be pcb_cradle's plate standing on ribs 27 mm off the endplate wall, and the
    # user read it right: the ribs cut the plate's bridge to 10 mm, but a bridge is still an
    # overhang, and the plate was 5.3 mm thick everywhere only because the M4 insert needed
    # 8.5 mm of depth in ONE spot. This endplate prints standing on its -X face, so anything
    # lying across the build axis is a ceiling -- the fix is to have nothing lying across it.
    # Every piece of this cradle is a COLUMN rising from the endplate wall straight to the
    # board: a ring of wall round the board (LIP under its edge to carry it, then on up past
    # its top as the locating wall), and the M4 boss under the ear. Zero ceilings, and the
    # board -- single-sided, nothing on its underside but THT tails -- needs no floor.
    # Nothing is behind it but open air down to the wall, so the columns go all the way.
    x0, x1, y0, y1 = MCTRL_FP
    y1 = y1 + MCTRL_EAR_H
    bw, bl = x1 - x0, y1 - y0
    hx, hy = MCTRL_HOLE[0], MCTRL_HOLE[1] - MCTRL_EAR_H / 2.0
    CLR, WALL, LIP = 0.3, D.MIN_WALL_2P, 1.2
    ox, oy = bw / 2 + CLR + WALL, bl / 2 + CLR + WALL
    top = POST_H + BD_T + 0.8                          # locating wall stands 0.8 over the board
    ring = (box_at(2 * ox, 2 * oy, POST_H - zb, x=0.0, y=0.0, z=(zb + POST_H) / 2)
            .cut(box_at(bw - 2 * LIP, bl - 2 * LIP, 80.0, x=0.0, y=0.0, z=0.0)))
    wall = (box_at(2 * ox, 2 * oy, top - POST_H, x=0.0, y=0.0, z=(POST_H + top) / 2)
            .cut(box_at(bw + 2 * CLR, bl + 2 * CLR, 80.0, x=0.0, y=0.0, z=0.0)))
    # -Y open above the board: the harness side, every lead leaves that way
    wall = wall.cut(box_at(2 * ox + 2, 2 * WALL + 2 * CLR + 2, 80.0,
                           x=0.0, y=-bl / 2, z=0.0))
    cr = ring.union(wall)
    # the USB-C (J4) sits ON the -Y edge; its shell's THT legs come through beside it, so
    # the lip steps back from under it and the board rests on the rest of the ring there
    _uw, _ul, _uh, _ux, _uy = MCTRL_USB
    cr = cr.cut(box_at(_uw + 1.0, 2 * LIP + 2 * CLR + 1.0, 2 * POST_H,
                       x=_ux, y=-bl / 2 + LIP / 2, z=POST_H))
    # the M4: a boss_od column under the ear's hole, the insert in its top
    cr = cr.union(_cyl_col(hx, hy, _M4.boss_od, zb, POST_H))
    cr = _cut_anchor(_M4, cr, (hx, hy, POST_H), (0, 0, -1), _M4.anchor_min_wall)
    body = cr.translate(((x0 + x1) / 2.0, (y0 + y1) / 2.0, TRAY_Z1))

    # ── THE PI: THE SAME PLATE, BUT 1.6 THICK, NOT 5.3 ───────────────────────────────────
    # The Pi cannot have the frame: the string-nut hardware fills x -630.2..-610.1 behind
    # it across y -37.3..+31.5 (slide inserts running the full z -55..0), so no column can
    # reach the wall under most of it and its plate has to span that stretch. What CAN go is
    # the thickness: pcb_cradle sizes its whole plate to the M4 insert's 8.5 mm depth, which
    # only the boss beside the +Y edge needs -- and that boss is past the hardware (y > 33),
    # so it gets a column to the wall and the plate drops to two beads.
    x0, x1, y0, y1 = PI_FP
    pw, pl = x1 - x0, y1 - y0
    cr = pcb_cradle(pw, pl, open_edge="-y", hold_edge="+y", hold_at=0.0, hold_spec=_M4,
                    standoff=POST_H, clr=0.3, base_t=D.MIN_WALL_2P)
    phx, phy = pcb_hold_xy(pw, pl, "+y", hold_at=0.0, clr=0.3, spec=_M4)
    cr = cr.union(_cyl_col(phx, phy, _M4.boss_od, zb, POST_H))
    cr = _cut_anchor(_M4, cr, (phx, phy, POST_H), (0, 0, -1), _M4.anchor_min_wall)
    cr = cr.translate(((x0 + x1) / 2.0, (y0 + y1) / 2.0, TRAY_Z1))
    # hung from the endplate's ledge at its -Y end (y < -39, clear of the nut hardware)...
    wx0, wx1 = max(x0, LEDGE_LX0), min(x1, LEDGE_LX1)
    wy0, wy1 = max(y0, LEDGE_LY0), min(y1, LEDGE_LY1)
    if wx1 > wx0 and wy1 > wy0:
        cr = cr.union(box_at(wx1 - wx0, wy1 - wy0, TRAY_Z1 - LEDGE_LZ,
                             x=(wx0 + wx1) / 2.0, y=(wy0 + wy1) / 2.0,
                             z=(LEDGE_LZ + TRAY_Z1) / 2.0))
    # ...and ribs to the wall wherever the hardware leaves room (both ends of the Pi; the
    # middle stays a bridge -- the one ceiling here that the hardware forces)
    _bb = cr.val().BoundingBox()
    rx0, rx1 = _bb.xmin - 1.0, _bb.xmax + 1.0
    for k in range(int(pl // RIB_PITCH) + 1):
        ry = y0 + RIB_PITCH / 2.0 + k * RIB_PITCH
        if ry > y1 - RIB_T:
            break
        if NUT_KEEPOUT_Y0 - RIB_T < ry < NUT_KEEPOUT_Y1 + RIB_T:
            continue
        cr = cr.union(box_at(rx1 - rx0, RIB_T, TRAY_Z1 - RIB_LZ,
                             x=(rx0 + rx1) / 2.0, y=ry, z=(RIB_LZ + TRAY_Z1) / 2.0))
    body = body.union(cr)
'''
s=s[:a]+new+s[b:]
open(p,'w',encoding='utf-8').write(s)
