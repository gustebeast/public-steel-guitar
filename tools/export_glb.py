"""Export a SIMPLIFIED, colored GLB of the instrument for web sharing.

Writes docs/assembly.glb (served by GitHub Pages via docs/index.html, Google's
<model-viewer>). The full assembly.step is ~145 MB — far too big for in-browser
viewers — and a GLB is web-native, keeps the per-part colors, and is ~10x smaller.

This SIMPLIFIED view keeps only the instrument body, the strings, the nut block,
and the motor/changer drivetrain. It drops the legs, the deck cover plates, the
electronics + wiring, the output jacks, and the pickup, so the mechanism reads
clearly. Re-run after a design change:  py -3.12 -m tools.export_glb
"""

from __future__ import annotations

import os
import re

import cadquery as cq

from src.build import collect_components, _color_for

# base names to KEEP (everything else — legs, top_plate, electronics, wires,
# jacks, pickup/clamp/height screws — is dropped)
INCLUDE = {
    # instrument body (no legs); the nut block is fused into keyhead_endplate now
    "chassis", "bridge_endplate", "keyhead_endplate",
    # strings
    "string", "string_nut",
    # nut-block hardware (gauged break pins + clamp set screws)
    "break_dowel", "set_screw",
    # motor / changer drivetrain
    "motor", "leadscrew", "carriage", "nut", "guide_rod",
    "screw_pulley", "motor_pulley", "belt", "belt_clamp",
    "screw_bearing", "bridge_bearings", "locknut",
}


def base(name: str) -> str:
    return re.sub(r"_\d+$", "", name)


def main() -> None:
    # cadquery's GLTF exporter already converts CAD Z-up to glTF Y-up at the scene
    # root, so we add NO rotation here (an explicit one double-rotates -> upside down)
    asm = cq.Assembly(name="servo_pedal_steel")
    n = 0
    for name, wp in collect_components():
        if base(name) in INCLUDE:
            asm.add(wp, name=name, color=_color_for(name))
            n += 1
    os.makedirs("docs", exist_ok=True)
    asm.save("docs/assembly.glb", exportType="GLTF")
    mb = os.path.getsize("docs/assembly.glb") / 1e6
    print(f"wrote docs/assembly.glb  ({n} parts, {mb:.1f} MB)")


if __name__ == "__main__":
    main()
