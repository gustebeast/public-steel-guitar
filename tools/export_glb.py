"""Export a colored GLB of the FULL instrument for web sharing.

Writes docs/assembly.glb and docs/assembly.geo.json, and docs/index.html: the viewer
page (cadkit.web), which GitHub Pages serves with them.

The GLB carries the ENTIRE assembly (every part collect_components() builds —
body, legs, deck, electronics, wiring, pickup, the lot) so the web preview
matches the build 1:1. Re-run after a design change:  py -3.12 -m tools.export_glb
(a full `py -3.12 -m src.build` refreshes AND publishes it automatically).
"""

from __future__ import annotations

import pathlib

import cadquery as cq

from src.build import (collect_components, _color_for, _build_counter_model,
                       _BUILD_COUNTER_FILE)

REPO = pathlib.Path(__file__).resolve().parents[1]
GLB = REPO / "docs" / "assembly.glb"


def _current_build_n():
    """The current build number WITHOUT bumping it (a preview export is not a
    build). None if the counter file is missing/unreadable."""
    try:
        return int(_BUILD_COUNTER_FILE.read_text().strip())
    except (OSError, ValueError):
        return None


# MESH SETTINGS FOR THE WEB PREVIEW ONLY -- the STEP files and the CAD are untouched.
# The defaults cadquery meshes at (0.1 mm, 0.1 rad) are what pushed build #620's preview
# to 101.4 MiB: past GitHub's 100 MiB per-file limit, so the viewer silently stopped
# publishing. Almost all of it was the strings' wound capstan coils -- a thin tube swept
# along a multi-turn helix, where the ANGULAR tolerance sets the triangle count (string_1
# alone meshed to 482,525 triangles). Measured on the whole assembly through cadquery's
# exporter:
#     tolerance / angular     GLB
#       0.1 / 0.1           101.2 MiB   (the old default)
#       0.1 / 0.3            25.5 MiB   <- this
#       0.2 / 0.5            16.8 MiB
#       0.5 / 1.0            12.1 MiB
# 0.3 rad leaves linear deviation at the old 0.1 mm, so round parts are as accurate as
# before and only the angle loosens. The numbers live in cadkit.web now (TOLERANCE,
# ANGULAR), which meshes the parts itself (one mesh per part, no normals: about half the
# bytes again) and writes the geometry record the viewer measures against beside the GLB.

# what the page calls the model (tools/scratch_view.py says the same)
ABOUT = {"title": "Public Steel Guitar", "subtitle": "full assembly · C6 copedent"}


def build_glb(components=None, out: pathlib.Path = GLB, build_n=None) -> pathlib.Path:
    """Write `out` (the web GLB) and, beside it, <stem>.geo.json (what every triangle
    was: the faces and edges as the CAD kernel describes them, for the viewer's measure
    tool) from `components` -- the (name, workplane) list from collect_components().
    Pass the list the caller already built to avoid rebuilding all the geometry a second
    time; omit it to collect fresh. `build_n` stamps the floating build-number label into
    the scene; omit it to read the current counter without
    bumping. Returns the GLB's path.

    The GLB's root node turns CAD Z-up to glTF Y-up; the part nodes under it are in CAD
    coordinates, which is the frame the rig's pivots are given in."""
    from cadkit.web import export
    from src.board_geom import BOARDS
    from tools.web_materials import material_of, unit_of
    if components is None:
        components = collect_components()
    if build_n is None:
        build_n = _current_build_n()
    parts = [(name, wp, _color_for(name)) for name, wp in components]
    if build_n is not None:
        counter = _build_counter_model(build_n)
        if counter is not None:
            parts.append(("build_counter", counter, _color_for("build_counter")))
    export(parts, out.parent, stem=out.stem, extras=dict(ABOUT, build=build_n), page=True,
           boards=BOARDS, cache_dir=REPO / ".webview" / "boards", materials=material_of,
           units=unit_of)
    print(f"  ({out.relative_to(REPO).as_posix()}, build #{build_n})")
    return out


def main() -> None:
    build_glb()


if __name__ == "__main__":
    main()
