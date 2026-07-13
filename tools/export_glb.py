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

from src.build import collect_components, _color_for

REPO = pathlib.Path(__file__).resolve().parents[1]
GLB = REPO / "docs" / "assembly.glb"


def build_glb(components=None, out: pathlib.Path = GLB) -> pathlib.Path:
    """Write `out` (a web GLB) from `components` — the (name, workplane) list from
    collect_components(). Pass the list the caller already built to avoid rebuilding
    all the geometry a second time; omit it to collect fresh. Returns the path.

    cadquery's GLTF exporter already converts CAD Z-up to glTF Y-up at the scene
    root, so we add NO rotation here (an explicit one double-rotates -> upside down)."""
    if components is None:
        components = collect_components()
    asm = cq.Assembly(name="public_steel_guitar")
    n = 0
    for name, wp in components:
        asm.add(wp, name=name, color=_color_for(name))
        n += 1
    out.parent.mkdir(parents=True, exist_ok=True)
    asm.save(str(out), exportType="GLTF")
    mb = out.stat().st_size / 1e6
    print(f"wrote {out.relative_to(REPO).as_posix()}  ({n} parts, {mb:.1f} MB)")
    return out


def main() -> None:
    build_glb()


if __name__ == "__main__":
    main()
