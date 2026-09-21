b = r'C:/Users/gus/Sync/Documents/Archive/3D/public-steel-guitar-bronner/'


def edit(path, pairs):
    s = open(b + path, encoding='utf-8').read()
    for old, new in pairs:
        assert s.count(old) == 1, (path, old[:60])
        s = s.replace(old, new)
    open(b + path, 'w', encoding='utf-8').write(s)


edit('src/board_geom.py', [
    ('''def _rot(v, deg):''',
     '''def holes(board: str):
    """[(x, y, d)] the board's cut holes (its mounting hole), board frame."""
    out = []
    for h in load(board).get("holes", []):
        cx = sum(p[0] for p in h) / len(h)
        cy = sum(p[1] for p in h) / len(h)
        r = sum(math.hypot(p[0] - cx, p[1] - cy) for p in h) / len(h)
        out.append((cx, cy, 2.0 * r))
    return out


def _plate(board: str) -> cq.Workplane:
    """The laminate itself: the routed OUTLINE (an L where the board has a mounting ear)
    minus its holes -- not the outline's bounding box, which would lay a slab under
    everything beside the ear."""
    g = load(board)
    t = g["thickness_mm"]
    poly = g.get("outline_poly")
    if not poly:
        w, l = g["outline_mm"]
        return box_at(w, l, t, x=0.0, y=0.0, z=t / 2.0)
    plate = cq.Workplane("XY").polyline([tuple(p) for p in poly]).close().extrude(t)
    for h in g.get("holes", []):
        plate = plate.cut(cq.Workplane("XY").polyline([tuple(p) for p in h]).close()
                          .extrude(t + 2.0).translate((0, 0, -1.0)))
    return plate


def _rot(v, deg):'''),
    ('''    g = load(board)
    w, l = g["outline_mm"]
    t = g["thickness_mm"]
    out = box_at(w, l, t, x=0.0, y=0.0, z=t / 2.0)
    missing''', '''    g = load(board)
    t = g["thickness_mm"]
    out = _plate(board)
    missing'''),
])

edit('src/bridge_endplate.py', [
    ('''    # ⚠ BUILT WALLED ALL ROUND, THEN OPENED -- because pcb_cradle's model is DROP-IN. It
    # refuses a hold on the open edge ("the head's notch needs a wall to sit in, and the
    # board a stop that way"), and in its world that is right: the board comes down from
    # +Z, the walls hold X and Y, and the head is all that holds Z. A SLIDE-IN board needs
    # the open side and the lock on the SAME edge, and there the shank is the stop. So ask
    # cadkit for the hold at -X in a closed cradle -- which gives the boss, the M4 insert
    # pocket and the head clearance exactly as the tees get them -- and take away the two
    # walls this install does not want.
    cr = pcb_cradle(OP_BOARD_X, OP_BOARD_Y, open_edge=None,
                    hold_edge="-x", hold_at=-22.5, hold_spec=_M4,
                    standoff=standoff, clr=OP_PANEL_CLR)''',
     '''    # ⚠ THE M4 GOES THROUGH THE BOARD NOW, not beside it (user, 2026-09-21: "the screw
    # adjacent ... doesn't provide as strong of retention"). The board grew a mounting EAR
    # off its -X edge (elec/output_panel.py EAR_*), and the screw goes down through that ear
    # into a boss: a head clamping the laminate round a hole holds the board every way,
    # where the side screw lapped 1 mm of its edge.
    # pcb_cradle's through-board path was written for M2 and sizes its boss "pad + 1.5" --
    # too small for an M4 insert -- so cadkit's own M4 boss (boss_od) is stood under the
    # hole here and the anchor re-cut with cadkit's cut_anchor, which the union refilled.
    # Built walled all round, then opened: the board still SLIDES IN +X (its connectors pass
    # through the panel), so the +X wall (the panel is the stop) and the -X wall above the
    # board's underside (the way in) come away, and the screw is what closes it.
    from cadkit.fasteners import cut_anchor as _cut_anchor
    from . import board_geom as _BG
    (hx, hy, _hd), = _BG.holes("output_panel")
    cr = pcb_cradle(OP_BOARD_X, OP_BOARD_Y, screw_xy=(hx, hy), spec=_M4, open_edge=None,
                    standoff=standoff, clr=OP_PANEL_CLR)
    _base_t = max(1.6, _M4.anchor_min_wall - standoff)
    cr = cr.union(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        _M4.boss_od / 2.0, _base_t + standoff, cq.Vector(hx, hy, -_base_t))))
    cr = _cut_anchor(_M4, cr, (hx, hy, standoff), (0, 0, -1), _M4.anchor_min_wall)'''),
    ('''    # ⚠ THE 24 V TRUNK LANE WINS -- IT WAS HERE FIRST. The bus runs -X along y = TEE_Y
    # (-120.75) at z -52, and the board's -Y edge reaches -122.50, so the cradle's -Y wall
    # and its -Y corner pads stood in the lane. The bus serves ten motors and its y is set
    # by the tee row; a board that arrived later does not get to move it. Everything ABOVE
    # the base is cut back clear of the lane; the base stays, 2.9 mm under the board and
    # under the bundle, so the board keeps a continuous floor and the wires run over it.
    _lane_y = -119.0                                 # clear of the bundle at TEE_Y -120.75
    cr = cr.cut(box_at(2 * (OP_BOARD_X / 2 + 4.0), 40.0, 40.0,
                       x=0.0, y=(_lane_y - cy) - 20.0, z=_base_top + 20.0))
''',
     '''    # (The 24 V lane cut that used to take the -Y wall away is gone with the lane: the 24 V
    #  runs cross ABOVE the board now, in the recess, and nothing rides y -120.75 at z -52.)
'''),
])
print('ok')
