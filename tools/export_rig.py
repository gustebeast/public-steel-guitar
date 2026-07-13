"""Emit docs/rig.json — the animation manifest the web viewer plays.

The GLB carries baked geometry (every part node has an identity transform under a
single root that rotates CAD Z-up -> glTF Y-up). So to spin a pulley about its own
axis, the viewer needs the pivot CENTRE and AXIS in CAD coordinates (the frame the
part nodes live in) — which only the CAD model knows. This script reads those
straight from dimensions.py / components.py so the viewer never re-derives geometry
and can't drift. It also carries the Emmons E9 copedent (which pedal raises which
strings) and the visual gains. Regenerated with the GLB on every publish.

  py -3.12 -m tools.export_rig

Kinematics: motor pulley (axis Y) -> twisted GT2 belt -> screw pulley (axis Z) ->
leadscrew -> carriage travels in Z. Pulleys are 14T:14T (1:1). The leadscrew and
belt loop are perfectly cylindrical / a closed sweep, so a rigid transform can't
make them look different — they are intentionally NOT animated (see NOTE below).
The gains (mm per semitone, pulley turns per mm, belt-clamp travel) are VISUAL
approximations: the real screw lead and string tension->pitch curve aren't modelled.
"""

from __future__ import annotations

import json
import pathlib

from src import dimensions as D
from src import components as C

REPO = pathlib.Path(__file__).resolve().parents[1]
RIG = REPO / "docs" / "rig.json"

# ── Emmons E9 copedent, as STRING NUMBERS (accepted standard: string 1 = highest
# pitch, furthest from the player). This model indexes strings 0..9 from that same
# far edge, so string number N = index + 1 (string 1 = index 0). Raises are in
# semitones; every classic A/B/C move is a raise (carriage travels to tension).
_COPEDENT = {
    "A": {"key": "1", "raise": {5: 2, 10: 2}},   # B->C# on 5 & 10
    "B": {"key": "2", "raise": {3: 1, 6: 1}},    # G#->A on 3 & 6
    "C": {"key": "3", "raise": {4: 2, 5: 2}},    # E->F# / B->C# on 4 & 5
}


def _idx(string_no: int) -> int:
    return string_no - 1                           # N = index + 1  <=>  index = N - 1


def build_rig(build_n=None) -> pathlib.Path:
    if build_n is None:
        from tools.export_glb import _current_build_n
        build_n = _current_build_n()
    # The GLB bakes a static demo pose (some carriages parked at full travel to show
    # the extremes). The viewer cancels it so the animation starts from a clean
    # neutral rest — read the exact per-string offset that was baked in.
    from src.build import DEMO_POSE_DZ

    strings = []
    for i in range(D.N_STRINGS):
        sy = D.string_y(i)
        scz = D.screw_pulley_z(i)
        mpos = D.motor_pos(i)                        # (mx, my, mz)
        _, tan, _ = C.splice_frame(mpos, (D.SCREW_X, sy, scz))   # belt-clamp travel dir
        strings.append({
            "i": i,
            "string": i + 1,                          # string number (1 = highest, far edge)
            "rest_dz": DEMO_POSE_DZ.get(i, 0.0),      # baked demo offset (viewer cancels it)
            # carriage assembly: pure Z translation (raise = -Z, toward more tension)
            "carriage_nodes": [f"carriage_{i}", f"nut_{i}", f"string_nut_{i}"],
            # pulleys: spin about their own axis, centre in CAD space
            "screw_pulley": {"node": f"screw_pulley_{i}",
                             "center": [D.SCREW_X, sy, scz], "axis": [0, 0, 1]},
            "motor_pulley": {"node": f"motor_pulley_{i}",
                             "center": list(mpos), "axis": [0, 1, 0]},
            # belt clamp: rides the belt -> slides along the belt tangent
            "belt_clamp": {"node": f"belt_clamp_{i}", "dir": list(tan)},
        })

    copedent = []
    for name, spec in _COPEDENT.items():
        copedent.append({
            "name": name, "key": spec["key"],
            "raises": [{"i": _idx(n), "semitones": st}
                       for n, st in spec["raise"].items()],
        })

    rig = {
        "build": build_n,
        "n_strings": D.N_STRINGS,
        "carriage_travel": D.CARRIAGE_TRAVEL,        # hard clamp on net displacement
        # VISUAL gains (not physical — see module docstring):
        "gains": {
            "mm_per_semitone": 2.0,                  # carriage Z per semitone raised
            "pulley_turns_per_mm": 0.12,             # screw/motor pulley spin per mm
            "belt_mm_per_mm": 1.5,                    # belt-clamp slide per mm
        },
        "strings": strings,
        "copedent": copedent,
    }
    RIG.parent.mkdir(parents=True, exist_ok=True)
    RIG.write_text(json.dumps(rig, indent=1))
    print(f"wrote {RIG.relative_to(REPO).as_posix()}  "
          f"({len(strings)} strings, {len(copedent)} pedals, build #{build_n})")
    return RIG


def main() -> None:
    build_rig()


if __name__ == "__main__":
    main()
