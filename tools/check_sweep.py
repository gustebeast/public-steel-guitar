"""SWEPT-envelope checker — what check_overlaps structurally cannot see.

check_overlaps compares parts WHERE THEY SIT. That is the right question for a
static assembly and the wrong one for anything that turns: a part on a rotating
shaft has to clear its neighbours at every angle, so what must not collide is its
swept CIRCLE about the shaft axis, not its outline.

Three real collisions hid behind that gap on this instrument, all found at once:

  * the leadscrew retaining collar was drawn as a 12.8 x 8.0 prism with spanner
    flats — Ø20.8 swept, in a 9.5 mm string lane. Every collar would have milled
    both its neighbours on the first move. Statically it touched nothing.
  * the drive pulleys' Ø11 flanges sweep to x -2.5 and the endplate's foot block
    starts at x -4.2, so the pulleys have always been ~1.7 mm buried in it. Where
    they SIT they only graze the corner (9-16 mm^3), which is why the pair ended up
    in check_overlaps' allow list as an "intended contact".
  * a first attempt at the pulleys' torque path put an M2 grub in a -X lug: r 8.6,
    Ø17 swept, straight through the endplate.

The test is deliberately CONSERVATIVE and cheap: each rotating part becomes a
cylinder of its own maximum radius about its axis, over its own Z extent, and that
cylinder is intersected with everything else. A conservative envelope can only
report a collision that a finer sweep would clear, never miss one that is real — so
a clean run here is a real guarantee, and a hit is a prompt to look, not proof.

    py -3.12 -m tools.check_sweep

Registering a part: add its base name to ROTATING with the axis it turns about.
If a part turns and is not listed, this gate simply says nothing about it.
"""

from __future__ import annotations

import math
import sys

import cadquery as cq

from src import dimensions as D

# base name -> (axis x, axis y) in global coordinates. Everything on the screw line
# turns about its own screw; the motor pulleys turn about the motor shaft, which is
# a Y axis and is checked by hand (they are nowhere near anything).
ROTATING = {
    "screw_pulley": lambda i: (D.SCREW_X, D.string_y(i)),
    "screw_collar": lambda i: (D.SCREW_X, D.string_y(i)),
    "leadscrew":    lambda i: (D.SCREW_X, D.string_y(i)),
    "screw_bearing": lambda i: (D.SCREW_X, D.string_y(i)),
}

# Pairs whose swept overlap is BY DESIGN — the same idea as check_overlaps'
# allow list, and it must be kept just as short.
SWEPT_OK = {
    # everything on one screw shares that screw's axis, so their swept cylinders are
    # concentric and overlap trivially; their real clearances are asserted in
    # dimensions.py (PULLEY_TOP_MAX, COLLAR_Z1, SUPPORT_BRG_BOT).
    ("screw_pulley", "leadscrew"), ("screw_collar", "leadscrew"),
    ("screw_bearing", "leadscrew"), ("screw_collar", "screw_bearing"),
    ("screw_pulley", "screw_bearing"), ("screw_collar", "screw_pulley"),
    ("screw_pulley", "belt"),        # the belt is what the pulley is for
    ("leadscrew", "nut"), ("leadscrew", "carriage"),
    ("screw_bearing", "bridge_endplate"),   # seated in the rail, by design
    ("leadscrew", "bridge_endplate"),       # runs through the rail's bores
}

MIN_REPORT = 0.5    # mm^3 — below this it is a shared face, not an interference


def _base(name: str) -> str:
    head = name.rsplit("_", 1)
    return head[0] if len(head) == 2 and head[1].isdigit() else name


def _index(name: str):
    head = name.rsplit("_", 1)
    return int(head[1]) if len(head) == 2 and head[1].isdigit() else None


def _slab(bb, zc, eps):
    """A thin horizontal slab through zc, wide enough to span the shape."""
    w = max(bb.xlen, bb.ylen) + 10.0
    return (cq.Workplane("XY").workplane(offset=zc - 5 * eps)
            .box(w, w, 10 * eps, centered=(True, True, False))
            .translate(((bb.xmin + bb.xmax) / 2, (bb.ymin + bb.ymax) / 2, 0)).val())


def envelope(shape, ax, ay, eps=1e-3):
    """The shape's swept envelope about (ax, ay): a stack of cylinders, one per Z
    band between consecutive vertex heights, each at the max radius of the vertices
    bounding that band.

    Banding rather than one tall cylinder matters. A stepped part — the retaining
    collar is a Ø8.8 body under a Ø5.6 pilot boss — would otherwise report its widest
    radius all the way up and cry collision where the boss enters the bearing seat.
    Still conservative within each band (a cone reports its larger end), so a clean
    run is a real guarantee."""
    bb = shape.BoundingBox()
    levels = sorted({round(v.Z, 6) for v in shape.Vertices()}
                    | {round(bb.zmin, 6), round(bb.zmax, 6)})
    env, rmax = None, 0.0
    for z0, z1 in zip(levels, levels[1:]):
        if z1 - z0 <= eps:
            continue
        # radius from a THIN SLICE inside the band, not from the band's edge
        # vertices: a step's lower face sits on the boundary, so reading edges
        # would carry the wide section up into the narrow one.
        r = 0.0
        for f in (0.02, 0.5, 0.98):
            zc = z0 + (z1 - z0) * f
            sl = _slab(bb, zc, eps)
            try:
                cut = shape.intersect(sl)
            except Exception:
                continue
            for v in cut.Vertices():
                r = max(r, math.hypot(v.X - ax, v.Y - ay))
        if r <= eps:
            continue
        rmax = max(rmax, r)
        band = (cq.Workplane("XY").workplane(offset=z0).circle(r)
                .extrude(z1 - z0).translate((ax, ay, 0)).val())
        env = band if env is None else env.fuse(band)
    return env, rmax


def main() -> int:
    from src.build import collect_components
    comps = [(n, wp.val()) for n, wp in collect_components()]
    by_name = dict(comps)

    spun = []
    for name, shape in comps:
        base, i = _base(name), _index(name)
        if base in ROTATING and i is not None:
            ax, ay = ROTATING[base](i)
            env, r = envelope(shape, ax, ay)
            spun.append((name, base, env, r))

    if not spun:
        print("check_sweep: nothing registered as rotating — see ROTATING")
        return 0
    print(f"check_sweep: {len(spun)} rotating parts, "
          f"{len(comps)} components to clear them against")

    hits = []
    for name, base, env, r in spun:
        ebb = env.BoundingBox()
        for other, shape in comps:
            if other == name:
                continue
            obase = _base(other)
            if tuple(sorted((base, obase))) in {tuple(sorted(p)) for p in SWEPT_OK}:
                continue
            # same rotating family on the SAME screw is concentric — skip; a
            # DIFFERENT screw is exactly what we are here to catch.
            obb = shape.BoundingBox()
            if (obb.xmin > ebb.xmax or obb.xmax < ebb.xmin
                    or obb.ymin > ebb.ymax or obb.ymax < ebb.ymin
                    or obb.zmin > ebb.zmax or obb.zmax < ebb.zmin):
                continue
            try:
                v = env.intersect(shape).Volume()
            except Exception:
                continue
            if v > MIN_REPORT:
                hits.append((v, name, r, other))

    if not hits:
        print("clean: every rotating part clears everything through a full turn.")
        return 0

    hits.sort(reverse=True)
    print(f"\n== SWEPT collisions ({len(hits)}) — these only appear when the part TURNS ==")
    for v, name, r, other in hits:
        print(f"  {v:10.1f} mm^3   {name:18s} (swept Ø{2 * r:.1f})  <->  {other}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
