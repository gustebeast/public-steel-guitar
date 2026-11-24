"""SHARED GUIDE RODS (user, 2026-11-22: "instead of gripping one guide rod completely we had each collar grip
two slightly less than halfway around. This way two collars could share a single rod and slide past each
other without contact").

THE RODS stay where they are (string k's at GUIDE_ANG 325, GUIDE_R off its axis). Rod k is shared by
collar k (its OWN, as today) and collar k-3 (the same-row +Y neighbour, 28.5 over). Strings 8-10 have no -Y
neighbour, so three NEW rods stand where strings "11-13"'s would (nominal offset, same row).
Rods: 10 + 3, not 20.

THE SPLIT. Seen from rod k, collar k's axis is at 145 deg and collar k-3's at ~30: only 115 apart, so two
U's facing their own collars would overlap. Instead each rod is split by the line through its centre
TANGENT to its own collar (perpendicular to the own collar's radius, s = 0 below):
  OWN JAW (collar k, s >= +GAP): today's tab and radial slot, less its round end past the rod. Its two
          walls still bear on the rod's sides (GAP short of the equator), so it locks the turn as today,
          GUIDE_FLOAT along the radius kept.
  HOOK    (collar k-3, s <= -GAP): a half-ring round the rod's far side (GUIDE_WALL thick, GUIDE_SLOT
          bore), and a tab from it back to collar k-3, trimmed to the same side of the split line.
  The two never meet: 2 x GAP between them, at every pair of travel positions (both move only in x).

WHAT IT LOCKS. Each collar now bears, both ways, along the split line's direction (55 deg, mostly Z) at
TWO rods 28.5 apart: the own jaw on rod k and the hook on rod k+3. Two parallel two-sided contacts that far
apart stop the collar turning about its axis AND swinging about either rod, the swing the user sees today.
Along the radius (145/325) the own slot floats GUIDE_FLOAT and the hook bears one way; the screw holds
that as today. A rod-to-rod position error only turns the collar a hair and shifts the nut sideways
(the screw's nut end is soft): nothing binds.

    PYTHONPATH=. py -3.12 src/test/shared_rod_study.py
"""
from __future__ import annotations

import math
import os

import cadquery as cq

from src import dimensions as D
from src import direct_bench as B

GAP = 0.4                                   # each jaw stops this far short of the split line
NB = 3                                      # the same-row -Y neighbour
R_I = B.GUIDE_SLOT / 2                      # the hook's bore (as the slot across)
R_O = R_I + B.GUIDE_WALL
TAB_X = lambda t: (B.x_collar(t)[0] - B.TAB_L, B.x_collar(t)[0])     # the tabs' x span


def _rod_dir(k: int):
    """Unit (y, z) from rod k toward collar k's axis (the own side), and the tangent (55 deg)."""
    ry, rz = rod_yz(k)
    ay, az = own_axis(k)
    dy, dz = ay - ry, az - rz
    L = math.hypot(dy, dz)
    return (dy / L, dz / L)


def own_axis(k: int):
    """The axis of the collar that OWNS rod k (k < N: string k; new rods: their virtual string)."""
    if k < B.N:
        return B.y_of(k), B.za(k)
    i = k - NB
    return B.y_of(i) - NB * D.STRING_PITCH, B.za(i)


def rod_yz(k: int):
    if k < B.N:
        return B.rod_yz(k)
    oy, oz = own_axis(k)
    dy, dz = B.at_ang(B.GUIDE_ANG, B.GUIDE_R)
    return oy + dy, oz + dz


def new_rod(k: int) -> cq.Workplane:
    """Rods 11-13 (k = 10..12): the endplate's seat back past the collars' furthest tab."""
    x0 = TAB_X(1.0)[0] - 3.0
    ry, rz = rod_yz(k)
    return B.cyl_x(B.GUIDE_D, B.ROD_TIP - x0, x0, y=ry, z=rz)


def _halfspace(k: int, x0: float, x1: float, keep_own: bool, reach: float) -> cq.Workplane:
    """The side of rod k's split line: own (s >= GAP) or hook (s <= -GAP), a box `reach` each way."""
    ry, rz = rod_yz(k)
    uy, uz = _rod_dir(k)
    ang = math.degrees(math.atan2(uz, uy))
    # a box in the rod frame: s along u from GAP to reach (own) or -reach to -GAP (hook), wide 2 reach
    s0, s1 = (GAP, reach) if keep_own else (-reach, -GAP)
    b = (cq.Workplane("XY").box(x1 - x0, s1 - s0, 2 * reach)
         .translate(((x0 + x1) / 2, (s0 + s1) / 2, 0)))
    return b.rotate((0, 0, 0), (1, 0, 0), ang).translate((0, ry, rz))


def hook(i: int, t: float) -> cq.Workplane:
    """Collar i's hook on rod i+3 (or the new rod), in world coordinates, at travel t."""
    k = i + NB
    x0, x1 = TAB_X(t)
    ry, rz = rod_yz(k)
    oy, oz = B.y_of(i), B.za(i)
    L = math.hypot(oy - ry, oz - rz)
    ang = math.degrees(math.atan2(oz - rz, oy - ry))
    ring = B.cyl_x(2 * R_O, x1 - x0, x0, y=ry, z=rz)
    reach_in = L - (B.STOP_D / 2 - 1.0)                     # into the collar's body
    arm = (cq.Workplane("XY").box(x1 - x0, reach_in, 2 * R_O)
           .translate(((x0 + x1) / 2, reach_in / 2, 0))
           .rotate((0, 0, 0), (1, 0, 0), ang).translate((0, ry, rz)))
    w = ring.union(arm).intersect(_halfspace(k, x0 - 1, x1 + 1, False, L + 5))
    return w.cut(B.cyl_x(2 * R_I, x1 - x0 + 2, x0 - 1, y=ry, z=rz))


def collar(i: int, t: float) -> cq.Workplane:
    """Collar i: today's, its own tab cut back to its side of the split (if rod i is shared), plus
    its hook on rod i+3."""
    w = B._collar(i, t)
    x0, x1 = TAB_X(t)
    if i - NB >= 0:                                          # rod i also carries collar i-3's hook
        ry, rz = rod_yz(i)
        keep = _halfspace(i, x0 - 1, x1 + 1, False, 12.0)    # its far side, near the rod only
        near = B.cyl_x(2 * (R_O + 3.0), x1 - x0 + 2, x0 - 1, y=ry, z=rz)
        w = w.cut(keep.intersect(near))
    return w.union(hook(i, t))


def check(ts=(0.0, 0.5, 1.0)) -> list:
    """Every new collar at each t against: every other new collar at each t, every other part of the
    drive (old collars left out) at t 0/1, the rods (old + new), the endplate and body."""
    others = []
    for t in (0.0, 1.0):
        for nm, w in B._drive(t):
            if nm.startswith("string_") or nm.startswith("collar_"):
                continue
            others.append((nm, t, w))
    others.append(("endplate", 0.0, B.endplate_full()))
    others.append(("body", 0.0, B.kept(B._body)))
    for k in range(B.N, B.N + NB):
        others.append((f"newrod_{k + 1}", 0.0, new_rod(k)))
    mine = {(i, t): collar(i, t) for i in range(B.N) for t in ts}
    bbs = {key: w.val().BoundingBox() for key, w in mine.items()}

    def apart(a, b):
        return (a.xmax < b.xmin or a.xmin > b.xmax or a.ymax < b.ymin or a.ymin > b.ymax
                or a.zmax < b.zmin or a.zmin > b.zmax)

    out = []
    own_names = ("yoke", "keyplate", "keyseat", "ball", "nut", "m3", "col_ins", "hold_wsh", "spring")
    # (its own spring grips its post: build-intended, and only ever at the same t)
    for (i, t), w in mine.items():
        eb = bbs[(i, t)]
        for nm, tt, o in others:
            base, _, idx = nm.rpartition("_")
            if idx.isdigit() and int(idx) == i and any(base == s or base.startswith(s + "_") for s in own_names):
                continue                                     # its own carriage (moves with it)
            if not o.vals():
                continue
            ob = cq.Compound.makeCompound(o.vals()).BoundingBox()
            if apart(ob, eb):
                continue
            v = w.intersect(o).val().Volume()
            if v > 0.01:
                out.append((f"collar {i + 1} t{t}", nm, tt, round(v, 2)))
        for (j, tj), o in mine.items():
            if j <= i:
                continue
            if apart(bbs[(j, tj)], eb):
                continue
            v = w.intersect(o).val().Volume()
            if v > 0.01:
                out.append((f"collar {i + 1} t{t}", f"collar {j + 1}", tj, round(v, 2)))
    return out


def report():
    print(f"split GAP {GAP} each side (jaws {2 * GAP} apart); hook bore {2 * R_I:.2f}, ring {2 * R_O:.2f}")
    for i in range(B.N):
        k = i + NB
        ry, rz = rod_yz(k)
        oy, oz = B.y_of(i), B.za(i)
        u = _rod_dir(k)
        d = math.hypot(oy - ry, oz - rz)
        a_own = math.degrees(math.atan2(*reversed(u))) % 360
        a_hook = math.degrees(math.atan2(oz - rz, oy - ry)) % 360
        print(f"  string {i + 1}: hooks rod {k + 1}{' (NEW)' if k >= B.N else ''} at {d:.2f} off its axis;"
              f" from that rod its owner is at {a_own:.0f} deg, this collar at {a_hook:.0f} ({(a_own - a_hook) % 360:.0f} apart)")
    # the lock: both contacts bear along the split line (tangent to the own collar) at two rods
    i = 4
    t1 = _rod_dir(i)
    p1 = rod_yz(i)
    p2 = rod_yz(i + NB)
    n = (-t1[1], t1[0])                                      # the split line's direction
    sep = abs((p2[0] - p1[0]) * t1[0] + (p2[1] - p1[1]) * t1[1])
    print(f"string 5: both locks bear along {math.degrees(math.atan2(n[1], n[0])) % 360:.0f} deg; "
          f"their lines {sep:.1f} apart (the lever against turning/swinging)")
    c = B.GUIDE_SLOT - B.GUIDE_D
    print(f"  play from the bores alone (+{c / 2:.2f} each side): ±{math.degrees(c / sep):.2f} deg "
          f"(today: free about the rod, the screw alone holds the swing)")


if __name__ == "__main__":
    report()
    hits = check()
    print(f"{len(hits)} overlaps")
    for h in hits:
        print("  ", h)
    os.makedirs("out/shared_rod", exist_ok=True)
    for i in (3, 4, 9):
        cq.exporters.export(collar(i, 0.0), f"out/shared_rod/collar_{i + 1}_shared.step")
    print("wrote out/shared_rod/collar_*_shared.step")
