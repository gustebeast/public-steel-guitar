"""FIT FINDERS, ROUND 3: the smallest joint that prints AS DRAWN, per print-orientation pair.

    py -3.12 -m src.test.fit_round3            # the table, and every corner's radius
    py -3.12 -m src.test.fit_round3 --export   # ...and write src/test/test_fit3_plate_petg_gf.step

WHY (src/test/corner_radius.py, the user's calipers, 2026-10-14, PETG-GF at a 0.8 nozzle).
A corner the NOZZLE makes -- the profile lying in the layer plane -- does not print as
drawn: a CONVEX one comes out about 1.9-2.0 round whatever is drawn under that, and
from 2.0 drawn it tracks the drawing about 0.4 rounder; a CONCAVE one comes out about
1.05 until 0.5 is drawn, then follows it. A corner made by LAYER STACKING -- the profile
standing across the layers -- is assumed to print as drawn. Today's joints have no room
for that: the seam's head is 2.66 deep and the endplate tenon's 1.6, where two 2 mm
corners need 4, so their printed heads are beads, not the T's on the drawing.

THE END STATE every pair here is drawn to (the user, 2026-10-14): BOTH halves print as
modelled, AND the two are the same shape a clearance apart -- even clearance all round.
  printable  a NOZZLE-MADE half's convex corners at least CONVEX_R (2.0), its concave at
             least CONCAVE_R (0.5); a LAYER-MADE half prints as drawn, so anything goes.
  matched    a tenon corner of radius r faces a socket corner of r + c (tenon convex,
             socket concave) or r - c (tenon concave, socket convex): the offset curve.
Both hold when each tenon radius is the LARGER of its own minimum and what its mate's
minimum asks of it -- matched() -- and one pass settles it, since a rounder corner never
prints worse. What it can cost is ROOM (a face carrying two convex corners is their two
radii plus a bead of flat -- with no flat the arcs meet tangent and the second will not
build), so the shapes below are sized from matched() at the loosest step. _gaps() then
MEASURES the result on the solids: no interference, and no air past the clearance.
And no wall under TWO BEADS. This is PLATE 1 of a cadkit joinery system (the user,
2026-10-14): the smallest such joint for every print-orientation pair, PETG-GF to PETG-GF;
plate 2 carries the pairs not here, drawn from what this one measures.

  NOZZLE / NOZZLE  (drop-in: chassis seam, pedal-bar splice, bar-latch rail)
    ROUND  neck NECK_W into a circle of BULB_R = CONVEX_R, its socket lip ROUND_LIP:
           the lip's two end arcs (r * tan(turn / 2) apiece) plus flat, up to the next
           whole bead. (tee() draws the smallest T by the same rules -- 11.2 wide, so it
           is off the plate: the round head is this pair's smallest joint.)
  NOZZLE / LAYER   (chassis -> endplate mushroom): cadkit's mushroom, its waist grown only
           until the head's corners hold 2.0; the socket cut as the tenon's TRUE OFFSET.
  LAYER / LAYER    (octagon: knee lever, leg section, cover rail): OCT_W wide (a two-bead
           stem), two-bead walls, socket likewise a true offset.
  + the STANDING corner rings (corner_radius set 3): does a layer-made corner print as
           drawn, as every layer-made half here assumes?

Clearance steps start from round 2's sharp results, the nearest thing to these shapes
(a sharp nozzle corner already printed ~2 mm round): seam 0.25 tight / 0.35 loose,
endplate 0.20 at 0.50 depth good. Same layout as before: token N beside cell N.
"""
from __future__ import annotations

import argparse
import math
import pathlib
import sys

import cadquery as cq

from src import dimensions as D
from . import fit_finder as F
from . import fit_round2 as R2

HERE = pathlib.Path(__file__).resolve().parent
CONVEX_R = 2.0               # a nozzle-made convex corner: prints ~2.4
CONCAVE_R = 0.5              # a nozzle-made concave corner: prints ~1.1
NOZZLE_MIN = (CONVEX_R, CONCAVE_R)   # (convex, concave) a nozzle-made half can print
LAYER_MIN = (0.0, 0.0)               # a layer-made half prints what is drawn
WALL = 2 * D.BEAD            # 1.6, every socket wall
BACK = 4 * D.BEAD            # 3.2 behind a drop-in socket's head: its number is cut there,
                             # 1.6 deep, and leaves a full wall



def matched(c, tenon_min, socket_min):
    """((convex, concave) of the tenon, (convex, concave) of the socket) at clearance `c`:
    each tenon radius the larger of its own printable minimum and what the mating socket
    corner's minimum needs (its convex r - c, its concave r + c), the socket the tenon's
    offset curve."""
    tc = max(tenon_min[0], socket_min[1] - c)
    tv = max(tenon_min[1], socket_min[0] + c)
    return (tc, tv), (max(tv - c, 0.0), tc + c)


TEE = [(0.20, 0.30), (0.25, 0.30), (0.30, 0.30), (0.35, 0.30), (0.40, 0.30)]
ROUND = [0.20, 0.25, 0.30, 0.35, 0.40]
ROOT_R = matched(max(c for c, _b in TEE), NOZZLE_MIN, NOZZLE_MIN)[0][1]   # 2.4: the tee
                                                    # tenon's root, matched to the lip's 2.0

NECK_W = 2 * D.BEAD                                 # 1.6, the quality tier
HEAD_W = NECK_W + 2 * (ROOT_R + CONVEX_R + D.BEAD / 2)   # 11.2: each overhang a root, a
                                                    # corner and a half bead of flat between
HEAD_D = 2 * CONVEX_R + D.BEAD                      # 4.8: two convex corners and a bead of flat
BULB_R = 5 * D.BEAD / 2.0                           # 2.0: the round head, CONVEX_R (5 beads across)


def _lip(*turns):
    """THE LIP -- the socket wall beside the neck, mouth to head -- as short as its two
    ends allow: each end is a nozzle-made convex corner, so it prints CONVEX_R round
    whatever is drawn, and an arc of radius r turning through `t` degrees takes
    r * tan(t / 2) of the lip. Their sum, then up to the next whole bead (some flat
    between, or the second arc will not build)."""
    need = sum(CONVEX_R * math.tan(math.radians(t) / 2.0) for t in turns)
    return (math.floor(need / D.BEAD + 1e-9) + 1) * D.BEAD


def _junction_turn(c):
    """The turn, degrees, where the round head's slot meets its circle."""
    return math.degrees(math.acos((NECK_W / 2.0 + c) / (BULB_R + c)))


LIP_T = _lip(90.0, 90.0)                            # 4.8: the tee's lip, square at both ends
ROUND_LIP = _lip(90.0, max(_junction_turn(c) for c in ROUND))   # 4.0: the round head's,
                                                    # whose inner end turns only ~67 degrees
WAIST = 3 * D.BEAD                                  # 2.4: the mushroom waist, the least that
                                                    # leaves its head's corners 2.0 (1.6 holds 1.8;
                                                    # its socket lip is 1.97 either way)
MUSH_CELL_T = 14 * D.BEAD                           # 11.2: the grown cavity plus four beads
                                                    # behind it: its number (1.4 deep) and two beads

MUSHROOM = [(0.15, 0.50), (0.20, 0.50), (0.25, 0.50), (0.30, 0.50), (0.20, 0.70)]
OCTAGON = [(0.15, 0.60, 0.0), (0.20, 0.60, 0.0), (0.25, 0.60, 0.0), (0.30, 0.60, 0.0)]
TAG = "fit3"
OCT_W = 2 * WALL             # 3.2: the octagon's width, its stem (width / 2) two beads; cadkit
                             # would go to 2.26 on its own, with a 1.13 stem


def _round_u0(c):
    """Where the round head's centre stands: its socket lip, mouth to where the slot
    meets the circle, is ROUND_LIP long."""
    return ROUND_LIP + math.sqrt((BULB_R + c) ** 2 - (NECK_W / 2.0 + c) ** 2)


# EVERY CELL OF A STRIP IS AS DEEP AS ITS LOOSEST: the number is cut in the back face, one
# plane for the whole strip, so that face must not move with the step
D_TEE = LIP_T + max(c for c, _b in TEE) + HEAD_D + max(b for _c, b in TEE) + BACK
D_ROUND = max(_round_u0(c) + BULB_R + c for c in ROUND) + BACK
LOG = {}                     # finder name -> [(corner log, radii asked, gaps)], per step


def _poly(pts, z0, z1):
    return cq.Workplane("XY").polyline(pts).close().extrude(z1 - z0).translate((0, 0, z0))


def _gaps(token, cell, axis, beyond):
    """The clearance as built: points round the tenon's profile (a section at mid-length),
    each one's distance to the socket. Only points past the token's own face count
    (`beyond(u, v)`): the host faces are coupon, not joint. Returns the sorted gaps."""
    import OCP.BRepBuilderAPI as BB
    import OCP.gp as gp
    pln = (gp.gp_Pln(gp.gp_Pnt(0, 0, F.L / 2.0), gp.gp_Dir(0, 0, 1)) if axis == "z" else
           gp.gp_Pln(gp.gp_Pnt(F.L / 2.0, 0, 0), gp.gp_Dir(1, 0, 0)))
    plane = cq.Face(BB.BRepBuilderAPI_MakeFace(pln, -200, 200, -200, 200).Face())
    sec = token.val().intersect(plane)
    cs = cell.val()
    out = []
    for e in sec.Edges():
        for k in range(41):
            q = e.positionAt(k / 40.0)
            u, v = (q.x, q.y) if axis == "z" else (q.y, q.z)
            if beyond(u, v):
                out.append(cs.distance(cq.Vertex.makeVertex(q.x, q.y, q.z)))
    return sorted(out)


def _record(name, token, cell, axis, beyond, radii):
    F.ROUND_LOG.clear()
    token, cell = F._round_pair(token, cell, axis, dict(radii, hosts=False))
    LOG.setdefault(name, []).append((F.ROUND_LOG[0], radii, _gaps(token, cell, axis, beyond)))
    return token, cell


def _drop_pair(tenon_pts, cavity, host_w, host_d, name, c):
    """A drop-in pair in fit_finder's _drop frame (X depth past the seam, Y width, Z the
    drop; both halves print +Z, both nozzle-made): `tenon_pts` the tenon's plan (from
    x = -1, inside its host), `cavity` the socket cutter; rounded to matched()."""
    hw = host_w / 2.0
    token = F._box(-host_d, 0, -hw, hw, 0, F.L).union(_poly(tenon_pts, 0, F.L))
    cell = F._box(0, host_d, -hw, hw, 0, F.L).cut(cavity)
    rt, rs = matched(c, NOZZLE_MIN, NOZZLE_MIN)
    return _record(name, token, cell, "z", lambda u, v: u > 1e-3, {"tenon": rt, "socket": rs})


def tee(c, bc):
    """The smallest rule-fitting T: neck NECK_W through a LIP_T lip into a HEAD_W x HEAD_D
    head. `c` round the sides and under the head, `bc` past its tip."""
    n2, h2, lip = NECK_W / 2.0, HEAD_W / 2.0, LIP_T + c
    pts = [(-1.0, -n2), (lip, -n2), (lip, -h2), (lip + HEAD_D, -h2),
           (lip + HEAD_D, h2), (lip, h2), (lip, n2), (-1.0, n2)]
    cav = (_poly([(-1.0, -n2 - c), (lip - c + 0.01, -n2 - c), (lip - c + 0.01, n2 + c),
                  (-1.0, n2 + c)], -1.0, F.L + 1.0)
           .union(_poly([(lip - c, -h2 - c), (lip + HEAD_D + bc, -h2 - c),
                         (lip + HEAD_D + bc, h2 + c), (lip - c, h2 + c)], -1.0, F.L + 1.0)))
    host_w = HEAD_W + 2 * c + 2 * WALL
    return _drop_pair(pts, cav, host_w, D_TEE, "tee", c)


def round_head(c):
    """The same neck into a circle of BULB_R, whose centre stands far enough out that
    the socket's lip (mouth to where the slot meets the circle) is ROUND_LIP long."""
    n2 = NECK_W / 2.0
    u0 = _round_u0(c)
    neck = _poly([(-1.0, -n2), (u0, -n2), (u0, n2), (-1.0, n2)], 0, F.L)
    bulb = cq.Workplane("XY").circle(BULB_R).extrude(F.L).translate((u0, 0, 0))
    hole = (_poly([(-1.0, -n2 - c), (u0, -n2 - c), (u0, n2 + c), (-1.0, n2 + c)], -1.0, F.L + 1.0)
            .union(cq.Workplane("XY").circle(BULB_R + c).extrude(F.L + 2.0)
                   .translate((u0, 0, -1.0))))
    hw = BULB_R + c + WALL
    host_d = D_ROUND
    token = F._box(-host_d, 0, -hw, hw, 0, F.L).union(neck).union(bulb)
    cell = F._box(0, host_d, -hw, hw, 0, F.L).cut(hole)
    rt, rs = matched(c, NOZZLE_MIN, NOZZLE_MIN)
    return _record("round", token, cell, "z", lambda u, v: u > 1e-3, {"tenon": rt, "socket": rs})


def _drop_finder(name, what, make, steps, host_w, host_d):
    f = F.Finder(name, what, make, (steps[0], steps[0]), host_w + F.GAP, F.UP_Z, F.UP_Z,
                 "chassis_0", "chassis_0",
                 cell_mark=((host_d, 0.0, F.L / 2.0), (1, 0, 0), (0, 1, 0)),
                 token_mark=((-host_d / 2.0, 0.0, F.L), (0, 0, 1), (0, 1, 0)))
    f.deltas = tuple(steps)
    return f


def finders():
    """The plate's finders, each re-stepped: ONE joint per orientation pair, its smallest.
    The tee (tee()) is not among them: it is the smallest T, but the round head does the
    same nozzle/nozzle pair in a 4.0 head against its 11.2 (user, 2026-10-14)."""
    out = []
    w_rd = 2 * (BULB_R + max(ROUND) + WALL)
    out.append(_drop_finder("round", "nozzle/nozzle drop-in round head",
                            lambda k, d: round_head(d), ROUND, w_rd, D_ROUND))
    base = {f.name: f for f in F.finders()}
    ep, octa = base["endplate"], base["octagon"]
    ep.deltas = tuple(MUSHROOM)
    ep.name = "mushroom"
    ep.make = _mushroom_make(ep.make)
    at, n, xd, kw = ep.cell_mark[0]
    ep.cell_mark = [((at[0], at[1], MUSH_CELL_T), n, xd, kw)]      # its bed face moved out
    octa.deltas = tuple(OCTAGON)
    octa.make, top, host_w = _octagon_make()
    octa.pitch = host_w + F.GAP
    at, n, xd, kw = octa.cell_mark[0]
    octa.cell_mark = [((at[0], at[1], top), n, xd, kw)]
    return out + [ep, octa]


def _octagon_make():
    """(maker, cell top, host width) for the octagon at its smallest: OCT_W wide, both
    halves layer-made (sharp, printed as drawn), every wall two beads -- the socket's
    sides, and its roof under the number (cut 1.4 deep into a 3.2 roof)."""
    from src import knee_lever as KL
    from cadkit.joinery import joint
    cmax = max(c for c, _b, _r in OCTAGON)
    host_w = OCT_W + 2 * cmax + 2 * WALL
    top = max(joint(OCT_W, F.L, tenon=KL._JUP, mortise=KL._JUP, clearance=c,
                    back_clearance=bc).height + bc for c, bc, _r in OCTAGON) + 2 * WALL

    def make(k, d):
        c, bc, _r = d
        J = joint(OCT_W, F.L, tenon=KL._JUP, mortise=KL._JUP, clearance=c, back_clearance=bc)
        hw = host_w / 2.0
        token = F._box(0, F.L, -hw, hw, -6 * D.BEAD, 0).union(J.tenon(root=1.0, length=F.L))
        # cut as the tenon's true offset, not cadkit's mortise (whose depth relief leaks
        # into the 45 degree faces, as the mushroom's does)
        cell = F._box(0, F.L, -hw, hw, 0, top).cut(_offset_cavity(token, c, bc))
        LOG.setdefault("octagon", []).append(({"tenon": [], "socket": []},
                                              {"tenon": LAYER_MIN, "socket": LAYER_MIN},
                                              _gaps(token, cell, "x", lambda u, v: v > 1e-3)))
        return token, cell
    return make, top, host_w


def _offset_cavity(token, c, bc):
    """The socket cutter for an x-running tenon standing on z = 0: the tenon's profile
    (with a neck-wide stub run down through the mouth) offset by `c`, swept up a further
    `bc - c` so the top alone gets `bc`, run the length of the cell and a mm past each end."""
    body = token.val()
    sec = body.intersect(cq.Face.makePlane(400, 400, cq.Vector(F.L / 2.0, 0, 0), cq.Vector(1, 0, 0)))
    n = min(abs(e.startPoint().y) for e in sec.Edges()
            if e.geomType() == "LINE" and max(e.startPoint().z, e.endPoint().z) > 1e-6
            and min(e.startPoint().z, e.endPoint().z) > -1e-6
            and abs(e.startPoint().y - e.endPoint().y) < 1e-6)
    part = (cq.Workplane("XY").add(body).intersect(F._box(-1, F.L + 1, -50, 50, 0, 50))
            .union(F._box(0, F.L, -n, n, -1 - c, 0.1)))
    end = part.faces("<X").val()
    prof = cq.Face.makeFromWires(end.outerWire().offset2D(c, "arc")[0])
    cut = cq.Workplane("XY").add(cq.Solid.extrudeLinear(prof, cq.Vector(F.L + 2.0, 0, 0))
                                 .translate(cq.Vector(-1.0, 0, 0)))
    return cut.union(cut.translate((0, 0, bc - c))) if bc > c else cut


def _mushroom_make(base_make):
    """The endplate finder's maker with the waist grown to WAIST and both halves to
    matched(): the tenon (nozzle-made) rounded, the socket (layer-made) cut as the
    rounded tenon's TRUE OFFSET -- c on every side and on the 45 degree faces under the
    head, `bc` only on top. cadkit's own mortise offsets the profile c sideways and `bc`
    upward, which leaves the faces under the head (the pull-out bearing faces) at
    (c + bc) / sqrt(2) and their arcs off-centre: matched in angle, not in clearance."""
    from src import chassis as CH
    from cadkit.joinery import joint

    def make(k, d):
        c, bc = d
        R1 = F._round1_sites()
        site = dict(width=R1.EP_J_W, tenon=R1._EP_AX, mortise=R1._EP_DN, install="+x",
                    standoff=R1.EP_TOP_CLR)
        h0 = joint(length=F.L, clearance=c, back_clearance=bc, **site).height
        J = joint(length=F.L, clearance=c, back_clearance=bc,
                  depth=h0 - 2 * D.BEAD + WAIST, **site)
        hw = CH.T / 2.0
        root = R1.EP_J_ROOT
        token = F._box(0, F.L, -hw, hw, -10 * D.BEAD, 0).union(J.tenon(root=root, length=F.L))
        so = getattr(J, "standoff", 0.0)
        assert J.height + bc + 4 * D.BEAD <= MUSH_CELL_T + 1e-9, "no room behind the cavity for its number"
        rt, rs = matched(c, NOZZLE_MIN, LAYER_MIN)
        token, lt = F._round(token, "x", rt, False)
        cell = F._box(0, F.L, -hw, hw, so, MUSH_CELL_T).cut(_offset_cavity(token, c, bc))
        cell, ls = F._round(cell, "x", rs, False)
        beyond = lambda u, v: v > so + 1e-3              # noqa: E731
        LOG.setdefault("mushroom", []).append(({"tenon": lt, "socket": ls}, {"tenon": rt, "socket": rs},
                                               _gaps(token, cell, "x", beyond)))
        return token, cell
    return make


def plate():
    """[(name, solid)], bed at z = 0: every finder's strip with its tokens beside it, and
    in a row in front the standing corner rings (corner_radius set 3), which measure the
    layer-made corners every layer-made half here is drawn on."""
    from . import corner_radius as CR
    out, x = [], 0.0
    for f in finders():
        grp, w = R2._group(f, "both", TAG)
        y0 = min(sh.BoundingBox().ymin for _n, sh in grp)
        out += [(n, sh.moved(cq.Location(cq.Vector(x, -y0, 0.0)))) for n, sh in grp]
        x += w + R2.BETWEEN
    for n, sh in CR.standing_pieces():
        bb = sh.BoundingBox()
        out.append((n, sh.moved(cq.Location(cq.Vector(CR.OUT_S / 2.0 + 2.0, -bb.ymax - R2.BETWEEN,
                                                         0.0)))))
    return [(n, sh if sh.isValid() else sh.fix()) for n, sh in out]


def assembly(origin=(-560.0, 330.0, 160.0)):
    """[(name, Workplane)] for the scratch view: the plate as it prints."""
    return [("test_" + n, cq.Workplane("XY").newObject([s]).translate(origin)) for n, s in plate()]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--export", action="store_true", help="write src/test/test_fit3_plate_petg_gf.step")
    a = ap.parse_args(argv)
    LOG.clear()
    pl = plate()
    print("TEE neck %.1f, head %.1f x %.1f, lip %.1f | ROUND head r %.1f, lip %.1f | MUSHROOM waist %.1f"
          % (NECK_W, HEAD_W, HEAD_D, LIP_T, BULB_R, ROUND_LIP, WAIST))
    for name, steps in (("tee", TEE), ("round", ROUND), ("mushroom", MUSHROOM), ("octagon", OCTAGON)):
        print(name)
        for k, d in enumerate(steps):
            dd = d if isinstance(d, tuple) else (d,)
            print("   %d    %s" % (k + 1, " / ".join("%.2f" % v for v in dd[:2])))
    steps = {"tee": TEE, "round": ROUND, "mushroom": MUSHROOM, "octagon": OCTAGON}
    for name, logs in LOG.items():
        print("%s   (radii tenon convex/concave | socket convex/concave, then the gap as built)" % name)
        for k, (log, radii, gaps) in enumerate(logs[:len(steps[name])]):
            d = steps[name][k]
            c, bc = (d, d) if not isinstance(d, tuple) else d[:2]
            off = [(half, kind, used) for half in ("tenon", "socket") for u, v, kind, used in log[half]
                   for want in [radii[half][0 if kind == "convex" else 1]]
                   if kind and want > 1e-9 and (used is None or abs(used - want) > 1e-6)]
            at_c = sum(abs(g - c) < 0.01 for g in gaps) / float(len(gaps))
            print("   %d  c %.2f  %.2f/%.2f | %.2f/%.2f   gap %.3f..%.3f (%.0f%% at c)%s%s" % (
                k + 1, c, radii["tenon"][0], radii["tenon"][1], radii["socket"][0], radii["socket"][1],
                gaps[0], gaps[-1], 100 * at_c,
                "" if gaps[-1] <= max(c, bc) + 0.01 else "   AIR PAST THE CLEARANCE",
                "" if not off else "   CORNERS OFF: %s" % off))
    lo = [min(getattr(s.BoundingBox(), a_) for _n, s in pl) for a_ in ("xmin", "ymin", "zmin")]
    hi = [max(getattr(s.BoundingBox(), a_) for _n, s in pl) for a_ in ("xmax", "ymax", "zmax")]
    print("plate: %d pieces, %.1f cm3, %.1f x %.1f, %.1f tall" % (
        len(pl), sum(s.Volume() for _n, s in pl) / 1000.0, hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]))
    bad = [n for n, s in pl if not s.isValid() or len(s.Solids()) != 1]
    print("every piece one valid solid" if not bad else "NOT ONE VALID SOLID: %s" % ", ".join(bad))
    if a.export:
        from cadkit.step_export import export_step
        path = HERE / "test_fit3_plate_petg_gf.step"
        export_step(cq.Workplane("XY").newObject(
            [cq.Compound.makeCompound([s for _n, s in pl])]), str(path))
        print("wrote", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
