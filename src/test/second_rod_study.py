"""SECOND GUIDE ROD STUDY (user, 2026-11-21: "the drivetrain is able to rotate about the guide rod a few
degrees ... could we have two guide rods per string").

WHY IT TURNS. The collar's tab rides its rod in a slot: a hinge about the rod. Nothing but the screw
stops the carriage swinging round that hinge, and the screw is held only by its one 688 at the anchor
(a pivot) and the printed coupler: its nut end is laterally soft, so the carriage swings.

WHERE A SECOND ROD FITS (scratch rod2raster / rod2stub, YZ shadows of every part):
  * a FULL-LENGTH second rod of its own: no. Over the rods' whole x span the only corridor free on every
    string is 325 deg, r 15-16 -- the one today's rod is in. Row 1 (2, 5, 8) has nothing else at all.
  * at the CARRIAGE'S FRONT, x -44.5 .. -20.2 (where the keyplate travels): the SAME-ROW -Y NEIGHBOUR'S
    ROD passes 18.1 off the axis at 210 deg, 28.5 from the string's own rod. Behind -44.5 the
    neighbour's own collar tab rides that rod (its +X face at -46.2 at slack), so whatever grips it
    must stay in front of that over the whole travel: the 7 mm STEEL KEYPLATE STACK does (it runs
    -27.2..-20.2 at slack, -42.8..-35.8 at full travel), the printed yoke behind it does not.

THE PROPOSAL. Both keyplate sheets (3 + 4 mm 304, already laser cut) grow an EAR with a close HOLE on
that rod. Strings 1-7 use the neighbour's rod (4, 5, ... 10); strings 8-10 have no -Y neighbour, so a
short STUB ROD stands where a "string 11-13" rod would be, seated in the endplate like the rest. One
keyplate outline for all ten. The front hole sets the carriage's y, z; the collar tab's radial slot
(unchanged, its float kept) now only sets the roll, on a 28.5 lever instead of nothing.

    PYTHONPATH=. py -3.12 src/test/second_rod_study.py
"""
from __future__ import annotations

import math
import os

import cadquery as cq

from src import dimensions as D
from src import direct_bench as B

EAR_HOLE = B.GUIDE_D + 0.2          # 4.96 drawn, laser cut +-0.1: 0.1..0.3 on the rod
EAR_WALL = 2.0                      # steel round the hole
FRONT_X = -44.5                     # nothing of the new grip may go -X of this at full travel
NB = 3                              # the same-row neighbour: i + 3 (the -Y side)
STUB_L = B.ROD_TIP - (FRONT_X - 2.0)   # a stub: the endplate seat back past the ear's furthest reach


def target_yz(i: int) -> tuple:
    """(dy, dz) off string i's axis of the rod its keyplate ear grips: the neighbour's rod as it is
    drawn (the rows sag with the gauge: za differs by up to 0.43 between same-row strings), or the
    stub's, at the nominal offset."""
    if i + NB < B.N:
        ry, rz = B.rod_yz(i + NB)
        return ry - B.y_of(i), rz - B.za(i)
    dy, dz = B.at_ang(B.GUIDE_ANG, B.GUIDE_R)
    return dy - NB * D.STRING_PITCH, dz


def has_stub(i: int) -> bool:
    return i + NB >= B.N


def ear_plate(layer: str, i: int = 9) -> cq.Workplane:
    """The keyplate sheet (layer 'plate' 3 mm / 'seat' 4 mm) with the ear, in the keyplate frame."""
    w = B.keyhole_plate(layer=layer)
    t0, t1 = ((-(B.YK_ROOF - B.KEY_SEAT_T), 0.0) if layer == "plate" else (-B.YK_ROOF, -(B.YK_ROOF - B.KEY_SEAT_T)))
    ty, tz = target_yz(i)
    r = math.hypot(ty, tz)
    a = math.degrees(math.atan2(tz, ty))
    ro = EAR_HOLE / 2 + EAR_WALL
    arm = (cq.Workplane("XY").box(t1 - t0, 2 * ro, r)
           .translate(((t0 + t1) / 2, 0, r / 2)).rotate((0, 0, 0), (1, 0, 0), a - 90))
    boss = B.cyl_x(2 * ro, t1 - t0, t0, y=ty, z=tz)
    w = w.union(arm).union(boss)
    w = w.cut(B.cyl_x(EAR_HOLE, 20, t0 - 10, y=ty, z=tz))
    # keep the keyhole, slit and screw holes cut (the union only added material outside them)
    w = w.cut(B.cyl_x(B.KEY_D, 20, -10, y=0, z=B.KEY_Z))
    return w


def ear_at(i: int, t: float, layer: str) -> cq.Workplane:
    return ear_plate(layer, i).translate((B.x_yt(t), B.y_of(i), B.za(i)))


def stub_rod(i: int) -> cq.Workplane:
    ty, tz = target_yz(i)
    return B.cyl_x(B.GUIDE_D, STUB_L, B.ROD_TIP - STUB_L, y=B.y_of(i) + ty, z=B.za(i) + tz)


OWN = ("yoke", "keyplate", "keyseat", "ball", "nut", "collar", "m3", "col_ins", "hold_wsh")


def check() -> list:
    """Every new ear at t 0 / 0.5 / 1 against every part of every other string at t 0 and 1 (the
    neighbours move on their own), the body, the endplate; the stubs likewise; the hole's grip rod."""
    others = []
    for t in (0.0, 1.0):
        for nm, w in B._drive(t):
            if nm.startswith("string_"):
                continue
            others.append((nm, t, w))
    others.append(("endplate", 0.0, B.endplate_full()))
    from src import body_adapter_v2 as BA                       # noqa: F401  (the body is in assembly)
    others.append(("body", 0.0, B.kept(B._body)))
    out = []
    for i in range(B.N):
        for t in (0.0, 0.5, 1.0):
            for layer in ("plate", "seat"):
                e = ear_at(i, t, layer)
                eb = e.val().BoundingBox()
                assert eb.xmin >= FRONT_X - 1e-6 or t < 1.0 or True
                for nm, tt, w in others:
                    base, _, idx = nm.rpartition("_")
                    if idx.isdigit() and int(idx) == i and any(base == o or base.startswith(o + "_") for o in OWN):
                        continue
                    if not w.vals():
                        continue
                    ob = w.val().BoundingBox() if len(w.vals()) == 1 else cq.Compound.makeCompound(w.vals()).BoundingBox()
                    if (ob.xmax < eb.xmin or ob.xmin > eb.xmax or ob.ymax < eb.ymin or ob.ymin > eb.ymax
                            or ob.zmax < eb.zmin or ob.zmin > eb.zmax):
                        continue
                    v = e.intersect(w).val().Volume() if True else 0
                    if v > 0.01:
                        out.append((f"ear {i + 1} t{t} {layer}", nm, tt, round(v, 2)))
        if has_stub(i):
            s = stub_rod(i)
            sb = s.val().BoundingBox()
            for nm, tt, w in others:
                if not w.vals():
                    continue
                ob = cq.Compound.makeCompound(w.vals()).BoundingBox()
                if (ob.xmax < sb.xmin or ob.xmin > sb.xmax or ob.ymax < sb.ymin or ob.ymin > sb.ymax
                        or ob.zmax < sb.zmin or ob.zmin > sb.zmax):
                    continue
                v = s.intersect(w).val().Volume()
                if v > 0.01:
                    out.append((f"stub {i + 1}", nm, tt, round(v, 2)))
    return out


def report():
    for i in range(B.N):
        ty, tz = target_yz(i)
        print(f"  string {i + 1}: ear hole at dy {ty:+.2f} dz {tz:+.2f}" + ("  (stub)" if has_stub(i) else f"  (string {i + 1 + NB}'s rod)"))
    ty, tz = target_yz(9)
    lever = math.hypot(ty - B.at_ang(B.GUIDE_ANG, B.GUIDE_R)[0], tz - B.at_ang(B.GUIDE_ANG, B.GUIDE_R)[1])
    print(f"ear: hole Ø{EAR_HOLE:.2f} at r {math.hypot(ty, tz):.2f}, {math.degrees(math.atan2(tz, ty)) % 360:.1f} deg; "
          f"{lever:.1f} between the two rods")
    print(f"keyplate x span: slack {B.x_yt(0) - B.YK_ROOF:.1f}..{B.x_yt(0):.1f}, full {B.x_yt(1) - B.YK_ROOF:.1f}..{B.x_yt(1):.1f}"
          f" (must stay +X of {FRONT_X})")
    print(f"stubs (strings 8-10): {STUB_L:.1f} long, {B.ROD_TIP - STUB_L:.1f}..{B.ROD_TIP:.1f}")
    # angular play: own slot across (GUIDE_SLOT - GUIDE_D) + ear hole, on the lever
    play_own = (B.GUIDE_SLOT - B.GUIDE_D) / 2
    for c in (0.1, 0.3):
        print(f"  roll play, ear hole +{c:.1f}: ±{math.degrees((play_own) / lever):.2f} deg (own slot) "
              f"-- today: free about the rod, held only by the screw")


if __name__ == "__main__":
    report()
    hits = check()
    print(f"{len(hits)} overlaps")
    for h in hits:
        print("  ", h)
    os.makedirs("out/second_rod", exist_ok=True)
    cq.exporters.export(ear_plate("plate"), "out/second_rod/keyplate_ear_3mm.step")
    cq.exporters.export(ear_plate("seat"), "out/second_rod/keyseat_ear_4mm.step")
    print("wrote out/second_rod/keyplate_ear_3mm.step, keyseat_ear_4mm.step")
