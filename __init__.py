"""cadkit — shared, project-agnostic CAD/3D-printing utilities.

A small library reused across the parametric-3D-printing projects. The modules depend
only on CadQuery/OCP: import them directly, e.g.

    from cadkit.fasteners import cut_anchor, M2, M4
    from cadkit.threads import cut_thread, threaded_rod
    from cadkit.step_export import export_step
    from cadkit.overlap_check import run
    from cadkit.joinery import ...
    from cadkit.printing import min_wall        # min-material floor (whole nozzle beads, no buffer)
    from cadkit import cq_colors
    from cadkit.board_geom import Boards        # a ROUTED KiCad board as CAD solids
    from cadkit.board_check import check        # ...and the gate that it is the routed one
                                                # (read PCB_README.md; kicad_geom.py and
                                                # kicad_silk.py run under KiCad's Python)
    from cadkit.pcbflow import gen              # MAKE a board from code (PCB_README.md §0)
    from cadkit.agents import current_agent, get_scope   # multi-agent: who owns what
    from cadkit.scratch import ScratchView               # fast per-part iteration loop
    from cadkit.lazy import lazy                         # a module's solids, built on first use

The assembly viewer is a web page, `cadkit.web`:

    from cadkit.web import show          # never raises; viewer trouble can't break a build

Dev-only tooling (the multi-agent worktree/merge CLI) lives in `cadkit/tools/` and is
run as a script, not imported: `py -3.12 cadkit/tools/agent_sync.py`.

Vendored into each project via `git subtree` at `<project>/cadkit`, so a cloned project
repo is fully self-contained; the canonical upstream is the standalone `cadkit` repo.
"""

__all__ = []


def _record_import_reads():
    """What each module OPENS while it is being imported (a board's JSON...), for
    cadkit.kept: a result keyed on a module's source must also change when a data file that
    module read at import changes. Installed here, the first thing any cadkit import runs,
    so it sees the project's own modules import. Cheap: it looks at read opens only."""
    import sys

    reads = []                                  # (importing module, path), in order

    def hook(event, args):
        if event != "open" or len(reads) > 100000:
            return
        path = args[0]
        mode = args[1] if len(args) > 1 else "r"
        if not isinstance(path, str) or (isinstance(mode, str) and any(c in mode for c in "wax+")):
            return
        if path.endswith((".py", ".pyc", ".pyd", ".dll", ".so")):
            return
        f = sys._getframe(1)
        while f is not None:
            if f.f_code.co_name == "<module>":
                reads.append((f.f_globals.get("__name__", ""), path))
                return
            f = f.f_back

    sys.addaudithook(hook)
    return reads


IMPORT_READS = _record_import_reads()
