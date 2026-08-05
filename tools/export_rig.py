"""Emit docs/rig.json — the animation manifest the web viewer plays.

The GLB carries baked geometry (every part node has an identity transform under a
single root that rotates CAD Z-up -> glTF Y-up). So to spin a pulley about its own
axis, the viewer needs the pivot CENTRE and AXIS in CAD coordinates (the frame the
part nodes live in) — which only the CAD model knows. This script reads those
straight from dimensions.py / components.py so the viewer never re-derives geometry
and can't drift. It also carries the C6 copedent (which control moves which strings,
signed semitones) and the visual gains. Regenerated with the GLB on every publish.

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

# ── THE C6 COPEDENT (user's own, from their chart) ───────────────────────────
# As STRING NUMBERS (accepted standard: string 1 = highest pitch, furthest from the
# player). This model indexes strings 0..9 from that same far edge, so string number
# N = index + 1 (string 1 = index 0).
#
# Open tuning, strings 1..10:  D4 E4 C4 A3 G3 E3 C3 A2 F2 C2
#
# WAS the Emmons E9 A/B/C — three pedals, all raises. That was wrong twice over: the
# instrument's design bounds are C6, not E9, and the hardware has FIVE pedals and
# FIVE levers, so the viewer was claiming three-sevenths of the controls.
#
# PEDAL NUMBERING: the user's chart is a DOUBLE-NECK layout whose pedal columns are
# shared with an E9 top neck, so its C6 moves sit on columns 3..7. Ours are P1..P5;
# the chart's number is 3 higher throughout (user).
#
# SEMITONES ARE SIGNED. The E9 set happened to be all raises, and this is not: P1
# lowers strings 2 and 6, P5 drops string 10 a minor third. That is fine mechanically
# — the carriage travels either way, tension up or down — and the viewer only sums
# them, so a negative simply runs the carriage the other way.
#
# SPLITS COST NOTHING HERE. The chart marks two (P3 on string 3, P5 on string 4).
# On a mechanical steel a split is a compromise stop where two pull-rods fight over
# one string; with an independent motor per string the controller just commands the
# pitch, so no split hardware exists to model.
_COPEDENT = {
    # pedals — keys 1..5, left to right as they sit on the bar
    "P1": {"key": "1", "moves": {2: -1, 6: -1, 10: +2}},   # chart P3
    "P2": {"key": "2", "moves": {2: +1, 6: +1, 10: +2}},   # chart P4
    "P3": {"key": "3", "moves": {3: +2, 5: -1, 9: +1}},    # chart P5  (3 is a split)
    "P4": {"key": "4", "moves": {7: +1}},                  # chart P6
    "P5": {"key": "5", "moves": {3: -1, 4: +2, 9: -1, 10: -3}},   # chart P7 (4 split)
    # knee levers — left knee on a/s/d, right knee on k/l, mirroring the knees
    "LKL": {"key": "a", "moves": {4: +1}},
    "VKL": {"key": "s", "moves": {1: +1}},
    "LKR": {"key": "d", "moves": {4: -1, 8: -1}},
    "RKL": {"key": "k", "moves": {7: +1}},
    "RKR": {"key": "l", "moves": {3: +1}},
}
OPEN_TUNING = ("D4", "E4", "C4", "A3", "G3", "E3", "C3", "A2", "F2", "C2")


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
            # JSON key stays "raises" (the viewer's contract); values are SIGNED
            "raises": [{"i": _idx(n), "semitones": st}
                       for n, st in spec["moves"].items()],
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
        "open_tuning": list(OPEN_TUNING),
        "strings": strings,
        "copedent": copedent,
    }
    RIG.parent.mkdir(parents=True, exist_ok=True)
    RIG.write_text(json.dumps(rig, indent=1))
    print(f"wrote {RIG.relative_to(REPO).as_posix()}  "
          f"({len(strings)} strings, {len(copedent)} controls "
          f"({sum(1 for k in _COPEDENT if k.startswith('P'))} pedals + "
          f"{sum(1 for k in _COPEDENT if not k.startswith('P'))} levers), "
          f"build #{build_n})")
    return RIG


def main() -> None:
    build_rig()


if __name__ == "__main__":
    main()
