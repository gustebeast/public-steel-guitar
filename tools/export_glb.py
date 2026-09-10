"""Export a colored GLB of the FULL instrument for web sharing.

Writes docs/assembly.glb (served by GitHub Pages via docs/index.html, Google's
<model-viewer>). The full assembly.step is ~145 MB — far too big for in-browser
viewers — and a GLB is web-native, keeps the per-part colors, and is far smaller.

The GLB carries the ENTIRE assembly (every part collect_components() builds —
body, legs, deck, electronics, wiring, pickup, the lot) so the web preview
matches the build 1:1. Re-run after a design change:  py -3.12 -m tools.export_glb
(a full `py -3.12 -m src.build` refreshes AND publishes it automatically).
"""

from __future__ import annotations

import os
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
# cadquery meshes the whole GLB at ONE tolerance, and its defaults (0.1 mm, 0.1 rad) are
# what pushed build #620's preview to 101.4 MiB: past GitHub's 100 MiB per-file limit, so
# the viewer silently stopped publishing. Almost all of it was the strings' wound capstan
# coils -- a thin tube swept along a multi-turn helix, where the ANGULAR tolerance sets
# the triangle count (string_1 alone meshed to 482,525 triangles). Measured on the whole
# assembly, clearing cached meshes between runs:
#     tolerance / angular     GLB
#       0.1 / 0.1           101.2 MiB   (the old default)
#       0.1 / 0.3            25.5 MiB   <- this
#       0.2 / 0.5            16.8 MiB
#       0.5 / 1.0            12.1 MiB
# 0.3 rad leaves linear deviation at the old 0.1 mm, so round parts are as accurate as
# before and only the angle loosens; the coarser rows save ~9 MiB more at a visible
# faceting cost. Export time fell 62 s -> 8 s as a side effect.
GLB_TOLERANCE = 0.1
GLB_ANGULAR_TOLERANCE = 0.3

def build_glb(components=None, out: pathlib.Path = GLB, build_n=None) -> pathlib.Path:
    """Write `out` (a web GLB) from `components` — the (name, workplane) list from
    collect_components(). Pass the list the caller already built to avoid rebuilding
    all the geometry a second time; omit it to collect fresh. `build_n` stamps the
    floating build-number label into the scene (same as assembly.step); omit it to
    read the current counter without bumping. Returns the path.

    cadquery's GLTF exporter already converts CAD Z-up to glTF Y-up at the scene
    root, so we add NO rotation here (an explicit one double-rotates -> upside down)."""
    if components is None:
        components = collect_components()
    if build_n is None:
        build_n = _current_build_n()
    asm = cq.Assembly(name="public_steel_guitar")
    n = 0
    for name, wp in components:
        asm.add(wp, name=name, color=_color_for(name))
        n += 1
    if build_n is not None:
        counter = _build_counter_model(build_n)
        if counter is not None:
            asm.add(counter, name="build_counter", color=_color_for("build_counter"))
            n += 1
    out.parent.mkdir(parents=True, exist_ok=True)
    asm.save(str(out), exportType="GLTF", tolerance=GLB_TOLERANCE,
             angularTolerance=GLB_ANGULAR_TOLERANCE)
    mb = out.stat().st_size / 1e6
    print(f"wrote {out.relative_to(REPO).as_posix()}  ({n} parts, {mb:.1f} MB, build #{build_n})")
    return out


def main() -> None:
    build_glb()


if __name__ == "__main__":
    main()
