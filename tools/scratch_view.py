"""Scratch view for THIS project -- YOUR portion, fresh, in the web viewer.

    py -3.12 cadkit/tools/agent_sync.py view            # the normal way to run this
    py -3.12 -m tools.scratch_view                      # your part fresh, the rest as built
    py -3.12 -m tools.scratch_view --cache-only         # the page alone, in seconds
    py -3.12 -m tools.scratch_view --gate               # fast gate on the same model
    py -3.12 -m tools.scratch_view --own                # build EVERYTHING here (minutes)
    py -3.12 -m tools.scratch_view --lead               # forget what you built: back to the lead's

WHY: a full `src.build` is minutes, and nearly all of it is geometry you are not
touching. The lead's build leaves every component in a cache all worktrees share, so
this rebuilds only the part under work and takes the rest from there. A part you built
earlier in the sitting stays as YOU built it. READ cadkit/scratch.py for what each of
those is trusted for: the caches are for the VIEW and the scoped gate only --
`src.build` and its gates never read them.

WHICH PART IS YOURS COMES FROM THE SCOPE REGISTRY, NOT FROM THIS FILE. Claim it once:

    py -3.12 cadkit/tools/agent_sync.py scope --set src.<your_module> [--attr assembly]
    py -3.12 cadkit/tools/agent_sync.py scope --set part:bridge_endplate,src.nut_block

(several, comma-separated, are all rebuilt every run). That deliberately does NOT live
here. This file is TRACKED, so a per-agent config block would put every agent's "which
part am I on" edit on the same three lines -- a guaranteed conflict on every merge
request, between two agents who are both right. The registry is per-worktree state
under .git instead (cadkit/agents.py).

The only thing you may need to add here is a POSE helper, and only if your part is not
authored in global coordinates -- see POSES below. Those are additive, so two agents
adding one do not collide.
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

# What is rebuilt every run: one entry, or several separated by commas.
LIVE = [m.strip() for m in SCOPE["module"].split(",") if m.strip()]
REPLACED = tuple(SCOPE.get("replaced", ()))


# ── optional per-part helpers ────────────────────────────────────────────────
# Only needed when a part is NOT authored in global coordinates. Add yours; a scope
# opts in with
#   scope --set ... --pose <key>
# and anything unregistered simply gets no pose.
def _tensioner_string():
    """The string the belt-tensioner work sits on: the LAST one -- the short belt run,
    where clamp-vs-pulley clearance is decided."""
    from src import dimensions as D
    return D.N_STRINGS - 1


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


POSES = {"belt_tensioner": _pose_belt_tensioner}


def _live_one(entry):
    """The parts one scope entry names. An entry is a module (its attribute given by
    the scope's --attr, else the module's OWN TAIL NAME, which is how nearly every part
    module here is written: src/bridge_endplate.py ends in `bridge_endplate =
    _build()`), or a BUILD PART, `part:bridge_endplate`: some parts are only ever
    assembled in src/build.py, so "point it at the right module attribute" has no
    correct answer for them (brenner, 2026-09-07). PARTS[name][0] is a zero-arg builder
    returning one Workplane -- exactly a live set of one."""
    if entry.startswith("part:"):
        key = entry[len("part:"):]
        parts = importlib.import_module("src.build").PARTS
        if key not in parts:
            raise SystemExit(f"scratch_view: no build part {key!r}. "
                             "List them with:  py -3.12 -m src.build --list")
        return [(key, parts[key][0]())]
    try:
        mod = importlib.import_module(entry)
    except ModuleNotFoundError:
        raise SystemExit(
            f"scratch_view: your scope names {entry!r}, which does not exist.\n"
            "Re-point it with:  agent_sync.py scope --set src.<your_module>")
    # YOUR MODULE'S CHECKS ALL RUN. Some modules build their parts on first use
    # (cadkit.lazy), so that others can read their dimensions without waiting; the
    # asserts inside those builders must still fire for whoever is working on the module.
    from cadkit.lazy import build_all
    build_all(mod)
    # --attr belongs to a scope of ONE module; with several, each uses its tail name
    attr = (SCOPE.get("attr") if len(LIVE) == 1 else None) or entry.rpartition(".")[2]
    obj = getattr(mod, attr, None)
    if obj is None:
        cands = [n for n in vars(mod)
                 if not n.startswith("_") and hasattr(getattr(mod, n), "val")]
        raise SystemExit(
            f"scratch_view: {entry} has no {attr!r}.\n"
            + (f"  solids it exports: {', '.join(cands)}\n" if cands else "")
            + "  agent_sync.py scope --set " + entry + " --attr <name>")
    # THREE SHAPES, because the part modules here follow no single convention:
    #   a bare solid         bridge_endplate = _build()        <- the common case
    #   a callable -> solid  belt_tensioner.tensioner_coupon()
    #   a callable -> list   build.py's _*_components()
    if callable(obj):
        obj = obj()
    parts = [(attr, obj)] if hasattr(obj, "val") else list(obj)
    return [(n, w) for n, w in parts if not n.endswith("_CONTEXT")]


def _live():
    return [p for entry in LIVE for p in _live_one(entry)]


def _lookup(table, key, what):
    """Resolve a POSES key, LOUDLY. `dict.get` returned None for an unknown key, so a
    typo rendered the part unposed with no warning at all -- the silent-wrong-answer
    failure this project keeps paying for."""
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
    pose=_lookup(POSES, SCOPE.get("pose"), "pose"),
    # Every part wears the colour the full build gives it, resolved through
    # src.build._color_for -- the very function the real build uses -- so this view
    # cannot drift from the finished assembly.
    colors=lambda n: importlib.import_module("src.build")._color_for(n),
    # What the page shows beyond the parts: the mechanism's rig, real part models on the
    # boards, the filament each part is printed in, and what the model is called.
    web=dict(
        rig=lambda path: importlib.import_module("tools.export_rig").build_rig(out=path),
        boards=lambda: importlib.import_module("src.board_geom").BOARDS,
        materials=lambda n: importlib.import_module("tools.web_materials").material_of(n),
        extras={"title": "Public Steel Guitar", "subtitle": "full assembly · C6 copedent"},
    ),
    # INNER-LOOP gates (`--gate`): the project's real gate functions, handed the
    # scratch model instead of a fresh 5.5-min rebuild. Scoping a gate by NAME
    # never helped -- the build is ~95% of its cost, not the checking -- so this
    # scopes what gets BUILT, exactly as the view does. This is the contributor's gate;
    # the FULL gate runs in the lead's build on merge, and `--gate` says so every run.
    gates=(("overlaps", lambda comps:
            importlib.import_module("tools.check_overlaps").gate(comps)),
           ("sweep", lambda comps:
            importlib.import_module("tools.check_sweep").gate(comps))),
)

if __name__ == "__main__":
    raise SystemExit(main(VIEW))
