"""Keyhead (-X) endplate + NUT BLOCK — PETG-GF, ONE merged piece, CH.KH_EP_THK thick in X.

The nut block (string termination, nut_block.py) is fused into a simple FULL-WIDTH solid
prism (rail outer to rail outer) that TAKES OVER the rail -X ends, so its edge shows from
the front like the bridge endplate. It SLIDES ON ALONG +X (user, 2026-11-06), over the steel wall
bars' -X ends and onto an X dovetail in each kept leg shell (chassis' X-SLIDE ENDPLATE JOINT). It:
  - closes the -X end of the box (its solid +X face stops the deck panels sliding -X);
  - terminates the strings: a steel nut plate per string (nut_block.py) whose crown is the
    break and whose shelf pinches the one wrap against the rod, pushed up by its own M4 height
    screw, with an M4 side screw in the bed face pinning the tail to the plate;
  - holds each wall bar's end in a pocket (the bars bear on its floors), seats on the rail ends
    by its bearing pads, and is held on by the legs' lock screws (legs.lock_pin_joint), which
    pass through its end face.

Service: strings off at the nut, remove the leg lock screws and slide the legs out, slide this
piece off -X (it travels chassis.KH_BAR_D + the pad before it clears the bars), then the deck
panels off -X.
"""

from __future__ import annotations

from . import dimensions as D
from . import chassis as CH
from . import nut_block as NB
from .endplate_base import endplate_base
from .helpers import box_at, heal
from cadkit.holes import teardrop_hole
from cadkit.kept import kept


# ONE part (PETG-GF), FULL-WIDTH (rail outer to rail outer) so it TAKES OVER the whole −X
# end and its edge shows from the front, mirroring the bridge endplate. Per the endplate
# methodology it's AS SOLID AS POSSIBLE: a solid block from the deck level (z6) down to the
# bed -- so the block itself is the −X cross-tie (no separate crossbar) -- with the nut
# block the only thing reaching above the deck and foot clearance hollowed only over the
# −X legs (XBAR above the tenon). Installs LAST, dropping straight DOWN (+Z→−Z): it
# sockets a dovetail tongue on each rail end (X+Y lock + grip vs the +X string tension).
# Build direction (user): the keyhead prints on its -X (outer) face, building -X -> +X.
# Hole cutters that take it (cadkit.fasteners) shape any sideways hole by themselves.
PRINT_UP = (1.0, 0.0, 0.0)
T_EP = CH.KH_EP_THK                        # FULL thickness (X), derived in nut_block (the leg
                                           # shell's -X edge is pinned to this so the -X wall = T)
XHI  = CH.KH_X                             # +X (inboard) face (-611); the rail end stops
                                           # EP_TOP_CLR short of it (CH.KH_RAIL_X)
XLO  = XHI - T_EP                          # -X outer (bed) face
KX   = (XLO + XHI) / 2
YFL  = CH.Y_LO - CH.T / 2                   # full width: -Y rail outer face
YFH  = CH.Y_HI + CH.T / 2                   # and the +Y rail's
# The wrap rod slides in from -Y along the whole of NB.rod_bore, so that run has to come out
# through this part's -Y face -- anything short of it is material the rod cannot be pushed past.
assert NB.ROD_Y0 - NB.ROD_L < YFL, (
    f"the rod's insertion run ends at y {NB.ROD_Y0 - NB.ROD_L:.2f}, inside the keyhead's -Y face "
    f"({YFL:.2f}) -- the {NB.ROD_L:g} mm rod could not be slid into position")
# The stowed key pushes it back out from the +Y face, far enough to grip at the -Y one.
# THE ROD'S FACES STAY WHERE THEY WERE (2026-11-06). The side walls grew 9.6 outward around the
# steel bars, which took 19.2 off what the key leaves standing; each face gets a SLOT at the rod,
# back to the 10.4 wall's old face and open to the top: the key's short arm stands up out of the
# +Y one, and fingers or pliers reach into the -Y one to draw the rod.
ROD_FACE_YL = CH.RAIL_INNER_Y - D.WALL_THICKNESS          # -Y: the old outer face
ROD_FACE_YH = D.RAIL_HI_INNER_Y + D.WALL_THICKNESS        # +Y
ROD_SLOT_W = {1: 10 * D.BEAD, -1: 20 * D.BEAD}           # 8.0 for the key, 16.0 to grip the rod
KEY_LONG_ARM = 88.0                         # Bondhus 10954
ROD_GRIP = KEY_LONG_ARM - (ROD_FACE_YH - NB.ROD_Y1) - (NB.ROD_Y0 - ROD_FACE_YL)
assert ROD_GRIP >= 5.0, f"the key leaves only {ROD_GRIP:.2f} of rod standing out of the -Y face to grip"
FOOT_Z = CH.KH_DT_Z0                       # foot line (-23.15): fill band bottom / wall-box top
# FOOT POCKET: the chassis now KEEPS a ~10 mm rail shell hugging each -X leg socket
# (CH._leg_shell over CH.LEG_SHELL_NX), capped at the foot line (z -23.15); the keyhead
# is solid AROUND that shell and nests over it as it drops -Z. The pocket only clears
# z = Z_BOT .. FOOT_Z (over the shell), NOT full-Z -- so the solid fill band (z -23.15..6)
# stays intact over the legs. leg -> 10 mm rail wall -> keyhead, touching.
LEG_CLR = CH.EP_LEG_CLR                    # assembly clearance around the kept chassis shell (shared)
LEG_SHELL_X0 = CH.LEG_SHELL_NX[0]                # -X end of the kept leg shell (rail-takeover region)



# ── THE HEIGHT-ADJUST PRISM (user) ────────────────────────────────────────────────
# New solid under the insert pockets for their extensions and height screws (nut_block's HEIGHT
# ADJUST block). Y: the pockets plus a two-bead wall each side. X: from this part's -X face to the
# extension pockets' roofs plus a two-bead wall -- which runs past XHI, so it is added AFTER the
# thickness trim. Z: a bead over the chassis's wide corner rib (nut_block.HS_PRISM_BOT) up to 0.8 under the top
# plate.
# ...BUT NO FURTHER THAN THIS PART'S OWN +X FACE (user, 2026-11-06: "the -x endplate needs to be able
# to slide up with the top panel in position"). Run on to dimensions.KEYHEAD_INBOARD_X it stood 3.4
# past XHI, under the keyhead deck panel, and the keyhead could not lift out. Trimmed, the wall in
# front of the plate pockets is XHI - the pockets' +X end, 0.8 -- kept so the string termination
# stays at the zero fret (user: "leave it at 0.8 for now and see if it holds").
HS_X1 = min(D.NUT_BLOCK_X + NB.HS_POCKET_X1 + D.MIN_WALL_2P, XHI)
HS_Y0, HS_Y1 = NB._INS_LO - D.MIN_WALL_2P, NB._INS_HI + D.MIN_WALL_2P
HS_Z0 = D.STRING_Z + NB.HS_PRISM_BOT
HS_Z1 = CH.TP_GZ0 - D.MIN_WALL
# THE +Y LEG SLIDES CLEAR OF THE HEIGHT SCREWS' KEY PATHS (legs.KEYHEAD_SLIDE, sized from them). It
# spells the leg's -Y face out from dimensions; hold it to the chassis's own number.
from . import legs as _LG
assert abs(_LG.LEG_NY_FACE - (CH.LEG_Y[0] - CH.LEG_W / 2.0)) < 1e-6, (
    f"legs.LEG_NY_FACE {_LG.LEG_NY_FACE:.3f} no longer matches the chassis's +Y leg face "
    f"{CH.LEG_Y[0] - CH.LEG_W / 2.0:.3f} -- KEYHEAD_SLIDE would be sized from the wrong place")


def _height_prism():
    return box_at(HS_X1 - XLO, HS_Y1 - HS_Y0, HS_Z1 - HS_Z0,
                  x=(XLO + HS_X1) / 2, y=(HS_Y0 + HS_Y1) / 2, z=(HS_Z0 + HS_Z1) / 2)


def _height_negatives():
    """Everything the prism needs cut, fused and subtracted once, in the nut block's local frame:
    the pockets again (they run down through it to the screws' floor) and every height screw's
    heat-set pocket and bore."""
    out = NB.all_pockets()
    for i in range(D.N_STRINGS):
        for k in NB.height_screw_negatives(i):
            out = out.union(k)
    return out.translate((D.NUT_BLOCK_X, 0.0, D.STRING_Z))



def _build():
    # THE SHARED TWO-PRISM BASE (endplate_base — same code as the bridge):
    # 1) the FILL SLAB (z -23.15..6, full footprint) = the -X cross-tie;
    # 2) the FOOT BOX below, hollowed to CH.T exterior walls (the -X end
    # face + both +-Y side faces stay solid; +X opens to the chassis box —
    # the rail-end shells + tongues come from the chassis side).
    w = endplate_base(XLO, XHI, "lo")
    # nut block (the only thing reaching above the deck): its fingers and end blocks, stood on
    # this piece's floor at the deck plane, up to the lid over the wrap rod. Fused on
    w = w.union(NB.nut_block.translate((D.NUT_BLOCK_X, 0, D.STRING_Z)))
    # THE INSERT SLOTS RUN PAST THE NUT BLOCK'S BASE, so they have to be cut HERE too --
    # nut_block can only cut its own prism, and an insert at its lowest travel hangs well
    # below that, into this piece's fill slab.
    w = w.cut(NB.all_pockets().translate((D.NUT_BLOCK_X, 0, D.STRING_Z)))
    w = w.intersect(box_at(T_EP, 4000.0, 4000.0, x=KX, y=0, z=0))
    # the height-adjust prism, AFTER the trim (its +X wall runs past XHI), and everything it needs cut
    w = w.union(_height_prism())
    w = w.cut(_height_negatives())
    # FOOT POCKET: pocket exactly the kept chassis rail shell (+ clearance) out of each
    # -X leg station so the keyhead nests over it as it drops -Z. It ONLY clears z =
    # Z_BOT .. FOOT_Z (over the shell, capped at -23.15) -- NOT full-Z -- so the solid
    # fill band above stays intact over the legs.
    for yr, s in ((CH.Y_HI, 1), (CH.Y_LO, -1)):
        yf = yr + s * CH.T / 2 + s * LEG_CLR        # shell outer face + clearance
        yi = yr - s * CH.T / 2 - s * LEG_CLR        # shell inner face + clearance
        top = CH.leg_shell_top(CH.LEG_STATIONS_X[1], yr)   # the shelf, as the bridge end
        w = w.cut(box_at((XHI + 1.0) - (LEG_SHELL_X0 - LEG_CLR), abs(yf - yi),
                         top - (CH.Z_BOT - 1.0),          # stop AT the shell top (= band floor):
                         x=((LEG_SHELL_X0 - LEG_CLR) + (XHI + 1.0)) / 2,   # no +0.1 step into the band
                         y=(yf + yi) / 2, z=((CH.Z_BOT - 1.0) + top) / 2))
    # THE X-SLIDE JOINT (user, 2026-11-06), per rail -- see chassis' X-SLIDE ENDPLATE JOINT block:
    # the steel bar's pocket, the bearing pad on the rail's end, and the X dovetail's tenon hanging
    # from the shelf into the kept shell. The keyhead slides on +X, onto the bars' ends first.
    for ycc in (CH.Y_HI, CH.Y_LO):
        w = w.union(CH.ep_pad("kh", ycc))
        w = w.union(CH.ep_dovetail("kh", ycc))
        w = w.cut(CH.bar_pocket("kh", ycc))
    # LEG-STUB grooves (Y-INSTALL round — user: the stubs print on their
    # side and SLIDE IN ALONG Y): cut this end's corner negatives from the
    # SAME shared source the chassis uses (legs.corner_groove_negatives).
    # For the keyhead that hosts: the 44-long END-WALL rebate (against
    # the wall's inner face — its blind inboard end is the stub's flush hard
    # stop), the crossing grooves' reach through the
    # endplate's own side-wall band / tab, and nothing of the fin passage
    # (that crossing is all kept-shell). Groove roofs at bed + 7.34, far
    # below the dovetail sockets (-23.15..-6).
    # relief=False: the 45° overhang wedge relieves the CHASSIS tongue
    # only — cut here it eats the end-wall groove roof (user-caught).
    # + the leg's ONE screw (legs.lock_pin_joint): an M4 button head recessed in the end
    # face and clearance on through, shaped from PRINT_UP; its insert is in the chassis.
    from .legs import (corner_groove_negatives as _cgn,
                       endwall_screw_negatives as _esn)
    for _ly, _s in ((CH.LEG_Y[0], 1.0), (CH.LEG_Y[1], -1.0)):
        for _n in _cgn(CH.LEG_STATIONS_X[1], _ly, _s, -1.0, CH.Z_BOT,
                       relief=False):
            w = w.cut(_n)
        for _n in _esn(CH.LEG_STATIONS_X[1], _ly, -1.0, CH.Z_BOT, PRINT_UP, _s):
            w = w.cut(_n)
    # THE SIDE SCREWS (one per string): heat-set in the bed face, clearance on into the tail channel,
    # where the tip pins the tail to its plate (nut_block.side_screw_negatives).
    w = w.cut(NB.all_side_screw_negatives().translate((D.NUT_BLOCK_X, 0.0, D.STRING_Z)))
    w = w.cut(NB.lanes().translate((D.NUT_BLOCK_X, 0.0, D.STRING_Z)))
    w = w.cut(NB.plier_window().translate((D.NUT_BLOCK_X, 0.0, D.STRING_Z)))
    w = w.cut(NB.rod_bore().translate((D.NUT_BLOCK_X, 0.0, D.STRING_Z)))
    # THE KEY'S WAY OUT TO THE +Y FACE: the rod's in the plate now, so its push hole runs on to the skin.
    w = w.cut(teardrop_hole(NB.ROD_PUSH_D, YFH - NB.ROD_Y1 + 1.0,
                            axis_point=(D.NUT_BLOCK_X + NB.ROD_X, NB.ROD_Y1, D.STRING_Z + NB.ROD_Z),
                            axis_dir=(0.0, 1.0, 0.0), print_up=PRINT_UP))
    # THE ROD SLOTS (ROD_FACE_*): from a bead under the push hole up through the top.
    _rx, _rz = D.NUT_BLOCK_X + NB.ROD_X, D.STRING_Z + NB.ROD_Z
    _sz0 = _rz - NB.ROD_PUSH_D / 2.0 - D.BEAD
    for _s, _yo, _yn in ((1, ROD_FACE_YH, YFH), (-1, ROD_FACE_YL, YFL)):
        _y0, _y1 = sorted((_yo, _yn + _s * 1.0))
        w = w.cut(box_at(ROD_SLOT_W[_s], _y1 - _y0, 60.0, x=_rx, y=(_y0 + _y1) / 2,
                         z=_sz0 + 30.0))
    # ONE SOLID, CHECKED. The overlap gate reports interpenetration, not disconnection: a
    # fused feature that never touches the plate would leave the part quietly in TWO pieces.
    _n = len(w.val().Solids())
    assert _n == 1, (
        "keyhead_endplate came out as %d disconnected solids -- a fused feature is not "
        "touching the plate." % _n)
    # THE ROD BORE'S WALL, on the finished solid: every top face, finger and end block alike, off the
    # bore's own cutter, teardrop included. The string load pulls the rod toward this wall.
    _bore = NB.rod_bore().translate((D.NUT_BLOCK_X, 0.0, D.STRING_Z)).val()
    _top = [f for f in w.val().Faces()
            if f.geomType() == "PLANE" and f.Center().z > D.STRING_Z + NB.ROD_Z
            and NB.Y_LO < f.Center().y < NB.HW
            and abs(f.normalAt().y) < 1e-6 and f.normalAt().z > 1e-6 and f.normalAt().x > -1e-6]
    _wall = min(f.distance(_bore) for f in _top)
    assert _wall >= D.MIN_WALL_2P, f"{_wall:.2f} of wall from the rod's bore to the top"
    # THE END BLOCKS MATCH on the +X face, on the finished solid: the outermost webs either side of the
    # pockets, just under the block's top.
    _x = D.NUT_BLOCK_X + NB.X_FRONT - 0.05
    _z = D.STRING_Z + NB.NUT_TOP - 0.5
    _ys = sorted((b.ymin, b.ymax) for b in (s.BoundingBox() for s in w.val().intersect(
        box_at(0.02, 300.0, 0.02, x=_x, y=0.0, z=_z).val()).Solids()))
    _a, _b = _ys[0][1] - _ys[0][0], _ys[-1][1] - _ys[-1][0]
    assert abs(_a - _b) < 0.01, f"the end blocks are {_a:.2f} (-Y) and {_b:.2f} (+Y) wide"
    return heal(w)


keyhead_endplate = kept(_build)               # cadkit.kept: built once per change, by whoever meets it first


def assembly():
    """The keyhead as the SCRATCH VIEW should draw it: the printed piece plus the
    hardware it is designed around, all rebuilt LIVE.

    The rod, the nut plates, their screws and the strings are every one of them positioned
    from constants in the module under work (nut_block.plate(), .rod(), .wrap_y()). A
    CACHED copy of them would be drawn wherever those constants stood when the cache was
    made -- precisely the lie the cache exists not to tell -- so the scope excludes them
    from the context (see `replaced`) and they are rebuilt here instead.

    Lives here rather than in tools/scratch_view.py because that file is now shared
    machinery keyed off the scope registry; per-part knowledge belongs with the part.
    src.build is imported INSIDE the call to dodge the import cycle (build imports this
    module), which is safe because build is always imported by then."""
    from . import build as B
    out = [("keyhead_endplate", keyhead_endplate),
           ("nut_wrap_rod", NB.rod().translate((D.NUT_BLOCK_X, 0.0, D.STRING_Z)))]
    for i in range(D.N_STRINGS):
        out.append((f"string_{i}", B._string_path(i, D.string_y(i))))
        out += [(n, s) for n, s in B.nut_hardware(i)]
    # THE CHASSIS SEGMENT UNDER THIS END IS LIVE TOO (user). chassis.py cuts a head cavity per
    # height screw, placed from nut_block's own positions, so a CACHED copy of it goes stale the
    # moment those move -- exactly the drift the scratch view exists to prevent. The -X-most
    # segment is the one this endplate sits against; found by extent, not by a pinned index, and
    # named as build.py names it so the scope's `chassis_` supersedes the cached one.
    # (build.py adds its knee-station work to the segments afterwards; that is all far +X of here.)
    ci = min(range(len(CH.segments)), key=lambda k: CH.segments[k].val().BoundingBox().xmin)
    out.append((f"chassis_{ci}", CH.segments[ci]))
    return out
