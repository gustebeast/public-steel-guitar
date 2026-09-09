"""Scratch view for THIS project -- renders YOUR portion into YOUR OWN FreeCAD tab.

    py -3.12 cadkit/tools/agent_sync.py view            # the normal way to run this
    py -3.12 -m tools.scratch_view --start              # BEGIN a flow: re-cache, render
    py -3.12 -m tools.scratch_view                      # iterate: your part fresh
    py -3.12 -m tools.scratch_view --merge              # END a flow: DELETE the cache

WHY: a full `src.build` is minutes, and nearly all of it is geometry you are not
touching. This caches the surroundings and rebuilds only the part under work --
measured here at ~14 s per iteration against a ~4 min build.

WHICH PART IS YOURS COMES FROM THE SCOPE REGISTRY, NOT FROM THIS FILE. Claim it once:

    py -3.12 cadkit/tools/agent_sync.py scope --set src.<your_module> [--attr assembly]

That deliberately does NOT live here. This file is TRACKED, so a per-agent config
block would put every agent's "which part am I on" edit on the same three lines --
a guaranteed conflict on every merge request, between two agents who are both
right. The registry is per-worktree state under .git instead (cadkit/agents.py).

The only thing you may need to add here is a POSE or CROP helper, and only if your
part is not authored in global coordinates -- see POSES / CROPS below. Those are
additive, so two agents adding one do not collide.

READ cadkit/scratch.py before trusting the cache. Short version: the LIFECYCLE is
the invalidation strategy (re-cache on --start, delete on --merge, so a cache never
outlives one sitting), and the cache is for the VIEW ONLY -- `src.build` and
tools.check_overlaps never read it, so a drift costs a surprise at merge rather
than a wrong part. Do not "improve" it into something the gate reads.
"""

from __future__ import annotations

import importlib
import pathlib

from cadkit.agents import current_agent, get_scope
from cadkit.scratch import ScratchView, main

ROOT = pathlib.Path(__file__).resolve().parent.parent

SCOPE = get_scope()
if SCOPE is None:
    raise SystemExit(
        f"scratch_view: {current_agent()} has not claimed a portion yet.\n"
        "  py -3.12 cadkit/tools/agent_sync.py scope --set src.<your_module>\n"
        "Then see who owns what with:  agent_sync.py scope")

LIVE_MODULE = SCOPE["module"]
# Default to the module's OWN TAIL NAME, which is how nearly every part module in
# this project is written: src/bridge_endplate.py ends in `bridge_endplate = _build()`.
# Defaulting to "assembly" named a callable that exists nowhere here, so a bare
# `scope --set src.<module>` could never work and every agent had to guess an --attr.
LIVE_ATTR = SCOPE.get("attr") or LIVE_MODULE.rpartition(".")[2]
REPLACED = tuple(SCOPE.get("replaced", ()))

# A scope may name a BUILD PART instead of a module attribute:
#     scope --set part:bridge_endplate
# Some parts are only ever assembled in src/build.py, so "point it at the right
# module attribute" has no correct answer for them (brenner, 2026-09-07).
# PARTS[name][0] is a zero-arg builder returning one Workplane -- exactly a live set
# of one.
PART_KEY = LIVE_MODULE[len("part:"):] if LIVE_MODULE.startswith("part:") else None


# ── optional per-part helpers ────────────────────────────────────────────────
# Only needed when a part is NOT authored in global coordinates, or when you want
# the context cropped to a region. Add yours; a scope opts in with
#   scope --set ... --pose <key> --crop <key>
# and anything unregistered simply gets no pose and the whole instrument.
def _leg_station():
    """The -X/+Y (TRRS) leg station."""
    from src import chassis as CH
    return CH.LEG_STATIONS_X[1], CH.LEG_Y[0], CH.Z_BOT


def _pose_leg_stack(name, wp):
    """leg_stack is authored +Z up from its own base; on the instrument it hangs
    off the chassis bottom, flipped."""
    lx, ly, zt = _leg_station()
    return wp.rotate((0, 0, 0), (1, 0, 0), 180).translate((lx, ly, zt))


def _tensioner_string():
    """The string the belt-tensioner work sits on: the LAST one -- the short belt run,
    where clamp-vs-pulley clearance is decided. Shared by the pose and the crop so the
    two cannot drift onto different strings."""
    from src import dimensions as D
    return D.N_STRINGS - 1


def _belt_run_box(pad=12.0, back_pad=8.0, top_pad=2.0):
    """Crop for the belt tensioner: ONLY what bears on the clamp -- this string's motor,
    the belt it drives, the leadscrew and pulley at the far end, and whatever chassis runs
    between them. The crop CLIPS rather than filters, so chassis_0 comes back as the local
    slab instead of the whole instrument, and the +Y pad catches the neighbouring string's
    belt, which is the thing the clamp can actually foul.

    Derived from the real parts, not hardcoded, so it follows the layout if that moves."""
    from src import components as C, dimensions as D
    i = _tensioner_string()
    sy, spz = D.string_y(i), D.screw_pulley_z(i)
    m = D.motor_pos(i)
    # Sized from the BELT PLANE only -- motor, belt, screw pulley. The leadscrew is
    # deliberately NOT in this list even though it is wanted in view: it stands 53mm
    # up to the carriage, and sizing to its top raised the ceiling through the deck,
    # dragging in top_plate, pickup, optical and bridge_endplate -- none of which the
    # clamp can reach. It still renders, clipped to its drive end, which is the part
    # the belt wraps and the only part the clamp comes near.
    bbs = [C.belt(m, (D.screw_x(i), sy, spz)).val().BoundingBox(),
           C.motor().translate(m).val().BoundingBox(),
           C.screw_pulley(high=spz > D.SCREW_PULLEY_Z)
            .translate((D.screw_x(i), sy, spz)).val().BoundingBox()]
    lo = [min(b.xmin for b in bbs) - pad, min(b.ymin for b in bbs) - pad,
          min(b.zmin for b in bbs) - pad]
    hi = [max(b.xmax for b in bbs) + pad, max(b.ymax for b in bbs) + pad,
          max(b.zmax for b in bbs) + pad]
    # -Y is cut just behind the motor PULLEY rather than behind the motor. The motor
    # body + driver stack runs 88mm toward the player, and everything living in that
    # band -- the CAN wiring, tee PCBs, knee lever, panel jacks, analog front end --
    # came into the view while being unable to touch the clamp. The drive end is the
    # only part of the motor the belt (and so the clamp) actually relates to.
    lo[1] = C.motor_pulley().translate(m).val().BoundingBox().ymin - back_pad
    # +Z stops at the top of the drive itself. A full pad above it reached into the
    # deck and brought back 0.4-3mm SLIVERS of top_plate, pickup and pickup_zplate --
    # shavings clipped exactly at the ceiling, which read as debris in the view and
    # are the one thing that cannot reach a clamp sitting in the chassis cavity.
    hi[2] = max(b.zmax for b in bbs) + top_pad
    return (hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2],
            (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2)


def _pose_belt_tensioner(name, wp):
    """belt_tensioner authors the clamp in the BELT-LOCAL frame (splice at the origin,
    belt back on z=0), because one clamp SKU is placed ten times. Unposed it would render
    at the world origin with no context near it. Placed here on the LAST string: the short
    belt run, which is where clamp-vs-pulley clearance is actually decided, and the one
    string the full build gives lifter bars to."""
    import cadquery as cq
    from src import components as C, dimensions as D
    i = _tensioner_string()
    so, sxd, sn = C.splice_frame(D.motor_pos(i),
                                 (D.screw_x(i), D.string_y(i), D.screw_pulley_z(i)))
    loc = cq.Location(cq.Plane(origin=so, xDir=sxd, normal=sn))
    return cq.Workplane("XY").add(wp.val().moved(loc))


POSES = {"leg_stack": _pose_leg_stack, "belt_tensioner": _pose_belt_tensioner}


def _crop_leg_station():
    """400 sq x 900 box round the leg station. Spelled out rather than built by
    tuple concatenation -- the one-liner read `(w,d,h) + station[:2] + (z-300.0)`,
    and that last term is a FLOAT, not a 1-tuple, so it raised the moment anyone
    actually used a crop. Nobody had until now."""
    lx, ly, zt = _leg_station()
    return (400.0, 400.0, 900.0, lx, ly, zt - 300.0)


def _crop_keyhead():
    """The whole keyhead endplate and what it mates with, at the -X end.

    Z IS SPANNED FROM THE BED TO OVER THE NUT BLOCK, not centred on the string plane.
    Centring on STRING_Z with 90 of height put the floor at -29 and spent 45 on empty air
    above the instrument -- which clipped chassis_2 to a 29 mm band that the deck panel
    then sat on top of, so the chassis read as MISSING from the render. Everything this
    part actually mates with is BELOW that line: the rail-end dovetail sockets at -23.15,
    the leg shell, the fill band down to the bed."""
    from src import dimensions as D, chassis as CH
    z0, z1 = CH.Z_BOT - 5.0, D.STRING_Z + 10.0
    return (120.0, 140.0, z1 - z0, D.NUT_BLOCK_X, 0.0, (z0 + z1) / 2)


def _crop_bridge():
    """The bridge endplate's UPPER BLOCK and what it mates with, at the +X end.

    NARROWER IN Y THAN THE KEYHEAD'S. The part itself runs -139..+66 because the screw
    rail and the foot reach right down the instrument, but the work here is the bearing
    arms and the axle between them -- +-51 -- and the optical board that stops the shaft.
    Cropping to that keeps the strings, the carriages and the arms in frame and leaves the
    drivetrain out of it.

    Z SPANS THE DECK TO OVER THE STRINGS, not the whole part: the arms stand above the
    deck and everything they mate with is up there. The foot and the rail below are
    context this view does not need, and they are most of the solids."""
    from src import dimensions as D, chassis as CH
    z0, z1 = CH.Z_TOP - 10.0, D.STRING_Z + 12.0
    return (90.0, 130.0, z1 - z0, D.BRIDGE_AXLE_X, 0.0, (z0 + z1) / 2)


CROPS = {"leg_station": _crop_leg_station, "belt_run": _belt_run_box,
         "keyhead": _crop_keyhead, "bridge": _crop_bridge}
# ─────────────────────────────────────────────────────────────────────────────


def _live():
    if PART_KEY is not None:
        parts = importlib.import_module("src.build").PARTS
        if PART_KEY not in parts:
            raise SystemExit(f"scratch_view: no build part {PART_KEY!r}. "
                             "List them with:  py -3.12 -m src.build --list")
        return [(PART_KEY, parts[PART_KEY][0]())]
    try:
        mod = importlib.import_module(LIVE_MODULE)
    except ModuleNotFoundError:
        raise SystemExit(
            f"scratch_view: your scope names {LIVE_MODULE!r}, which does not exist.\n"
            "Re-point it with:  agent_sync.py scope --set src.<your_module>")
    obj = getattr(mod, LIVE_ATTR, None)
    if obj is None:
        cands = [n for n in vars(mod)
                 if not n.startswith("_") and hasattr(getattr(mod, n), "val")]
        raise SystemExit(
            f"scratch_view: {LIVE_MODULE} has no {LIVE_ATTR!r}.\n"
            + (f"  solids it exports: {', '.join(cands)}\n" if cands else "")
            + "  agent_sync.py scope --set " + LIVE_MODULE + " --attr <name>")
    # THREE SHAPES, because the part modules here follow no single convention:
    #   a bare solid         bridge_endplate = _build()        <- the common case
    #   a callable -> solid  belt_tensioner.tensioner_coupon()
    #   a callable -> list   build.py's _*_components()
    # Accepting only the third is what made BOTH seeded scopes wrong on their first
    # run, and it would have kept being wrong for every module shaped like the others.
    if callable(obj):
        obj = obj()
    parts = [(LIVE_ATTR, obj)] if hasattr(obj, "val") else list(obj)
    return [(n, w) for n, w in parts if not n.endswith("_CONTEXT")]


def _lookup(table, key, what):
    """Resolve a POSES/CROPS key, LOUDLY. `dict.get` returned None for an unknown key,
    so a typo rendered the part unposed (or uncropped) with no warning at all -- the
    silent-wrong-answer failure this project keeps paying for."""
    if not key:
        return None
    if key not in table:
        raise SystemExit(f"scratch_view: unknown {what} {key!r}. Registered: "
                         f"{sorted(table) or '(none)'}. Add one in tools/scratch_view.py, "
                         "or drop it from your scope.")
    return table[key]


VIEW = ScratchView(
    root=ROOT,
    context=lambda: importlib.import_module("src.build").collect_components(),
    live=_live,
    replaced=REPLACED,
    crop=(lambda f: f() if f else None)(_lookup(CROPS, SCOPE.get("crop"), "crop")),
    pose=_lookup(POSES, SCOPE.get("pose"), "pose"),
    # The LIVE set wears the same colours the full build gives it, so the part under
    # work reads as the material it is instead of one flat highlight. Resolved through
    # src.build._color_for -- the very function the real build uses -- so this view
    # cannot drift from the finished assembly. Cached context stays grey on purpose:
    # that contrast is what tells you which parts are live and which may be stale.
    colors=lambda n: importlib.import_module("src.build")._color_for(n),
)

if __name__ == "__main__":
    raise SystemExit(main(VIEW))
