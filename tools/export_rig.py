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
# SIX levers, so the viewer was claiming three-elevenths of the controls.
#
# PEDAL NUMBERING: the user's chart is a DOUBLE-NECK layout whose pedal columns are
# shared with an E9 top neck, so its C6 moves sit on columns 4..8. Ours are P1..P5;
# the chart's number is 3 higher throughout (user).
#
# SEMITONES ARE SIGNED. The E9 set happened to be all raises, and this is not: P3
# lowers both its strings, P5 drops string 10 a minor third. That is fine
# mechanically — the carriage travels either way, tension up or down — and the
# viewer only sums them, so a negative simply runs the carriage the other way.
#
# SPLITS COST NOTHING HERE. The chart marks two, and BOTH land on P4 (strings 3 and
# 4). On a mechanical steel a split is a compromise stop where two pull-rods fight
# over one string; with an independent motor per string the controller just commands
# the pitch, so no split hardware exists to model.
# RE-READ FROM THE RAW SHEET, cell by cell. The first pass at this table went
# through a SUMMARISED read of the spreadsheet and landed a column out of step,
# with sign errors on top. Round-tripping each move back to a note name did not
# catch it, because that only proved the table was self-consistent — it checked
# arithmetic against my own transcription, never against the source. Every move
# below is now derived from the exported CSV's own cells, and the chart's target
# note is quoted beside each one so the next reader can check it without me.
#
# The chart's C6 pedal columns are 4..8 — contiguous, which is the "3 higher"
# offset the user described (its 1..3 are the E9 top neck's).
_COPEDENT = {
    # pedals — keys 1..5, left to right as they sit on the bar
    "P1": {"key": "1", "moves": {2: +1, 6: +1, 10: +2}},   # chart 4: E->F  E->F  C->D
    "P2": {"key": "2", "moves": {5: -1, 9: +1, 10: +2}},   # chart 5: G->F# F->F# C->D
    "P3": {"key": "3", "moves": {2: -1, 6: -1}},           # chart 6: E->D# E->D#
    "P4": {"key": "4", "moves": {3: +2, 4: +2}},           # chart 7: C->D* A->B*  (both split)
    "P5": {"key": "5", "moves": {7: +1, 9: -1, 10: -3}},   # chart 8: C->C# F->E  C->A
    # KNEE LEVERS — keyed q..y (the QWERTY home row above the pedals' number
    # row, so the two UI rows sit the same way round as the keyboard) strictly LEFT TO RIGHT from the player's seat
    # (user's rule), which is ascending X, the same direction the pedals run.
    # ILKL therefore takes the leftmost key: it sits one slot -X of LKL. The user
    # confirmed strict left-to-right over their earlier "a is LKL" example, which
    # predated their own note that a sixth (inner) lever exists.
    "ILKL": {"key": "q", "moves": {}},   # the chart assigns it on the E9 neck ONLY
    #                                      (G#->A#/B); on C6 the lever is fitted
    #                                      but unassigned. Kept so the hardware,
    #                                      the UI and the chart all show six.
    "LKL": {"key": "w", "moves": {4: +1}},             # A->A#
    "VKL": {"key": "e", "moves": {1: +1}},             # D->D#
    "LKR": {"key": "r", "moves": {4: -1, 8: -1}},      # A->G#  A->G#
    "RKL": {"key": "t", "moves": {3: -1}},             # C->B
    "RKR": {"key": "y", "moves": {3: +1, 7: +1}},      # C->C#  C->C#
}
OPEN_TUNING = ("D4", "E4", "C4", "A3", "G3", "E3", "C3", "A2", "F2", "C2")


def _idx(string_no: int) -> int:
    return string_no - 1                           # N = index + 1  <=>  index = N - 1


def _pedals() -> list[dict]:
    """The foot pedals' own kinematics, so the viewer can show them DEPRESS.

    Everything here is read from the model, not restated:

      * centre  — the axle, at (station x, MOUNT_DY, BAR_TOP_Z + the bar's lift).
      * axis    — foot_pedal._to_guitar maps the lever's local +Y axle to guitar
                  -X, so the pedal swings about -X (along the bar).
      * throw   — foot_pedal.THROW_P, and NEGATIVE is the pressed direction: the
                  cartridges sit above the lobe pushing down, so the foot drives
                  -theta (see _to_guitar's docstring). Probed, not assumed —
                  swing(-20) is the pose whose pad ends up lowest.
      * lobe_rc — the piston stroke is EXACT, not a visual gain: a flat lobe face
                  at radius RC swept through theta retracts the piston by
                  RC*sin(theta). 13.2*sin(20) = 4.514, which is the 4.51 the pedal
                  arm was sized around, and 9*sin(30) = 4.50 on the knee lever.

    The pistons retract along guitar +Z (the cartridge bases sit above them). The
    springs are NOT animated — a compressing helix isn't a rigid transform, same
    reason the belt loop and leadscrew aren't (see the module docstring).
    """
    from src import foot_pedal as FP
    from src.build import PEDAL_LIFT_DZ

    out = []
    for i, x in enumerate(FP.PEDAL_X):
        out.append({
            "i": i,
            "center": [x, FP.MOUNT_DY, FP.BAR_TOP_Z + PEDAL_LIFT_DZ],
            "axis": [-1, 0, 0],
            "throw_deg": -FP.THROW_P,               # signed: pressed = -theta
            "lobe_rc": FP.LOBE_RC_P,                # stroke = rc*sin(theta)
            # on the axle, so they swing with the arm (the bearings, board and
            # sensor stack do not — they stay with the housing)
            "swing_nodes": [f"pedal_lever_{i}", f"pedal{i}_magnet"],
            # pushed back into their cartridges as the lobe comes round
            "piston_nodes": [f"pedal{i}_main_cart_piston",
                             f"pedal{i}_half_stop_cart_piston"],
            "piston_dir": [0, 0, 1],
        })
    return out


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

    # P1..P5 are the bar's stations left to right, and foot_pedal.PEDAL_X is in
    # that same order (index 0 = most -X = flush end, the leg side), so the
    # control's number IS its station index. Levers carry no pedal index — the
    # knee hardware isn't posed by the viewer yet.
    pedals = _pedals()
    copedent = []
    for name, spec in _COPEDENT.items():
        entry = {
            "name": name, "key": spec["key"],
            # JSON key stays "raises" (the viewer's contract); values are SIGNED
            "raises": [{"i": _idx(n), "semitones": st}
                       for n, st in spec["moves"].items()],
        }
        if name.startswith("P"):
            entry["pedal"] = int(name[1:]) - 1
        copedent.append(entry)
    _np = sum(1 for c in copedent if "pedal" in c)
    assert _np == len(pedals), f"{_np} pedal controls vs {len(pedals)} stations"

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
        "pedals": pedals,
        "copedent": copedent,
    }
    RIG.parent.mkdir(parents=True, exist_ok=True)
    RIG.write_text(json.dumps(rig, indent=1))
    print(f"wrote {RIG.relative_to(REPO).as_posix()}  "
          f"({len(strings)} strings, {len(pedals)} posed pedals, "
          f"{len(copedent)} controls "
          f"({sum(1 for k in _COPEDENT if k.startswith('P'))} pedals + "
          f"{sum(1 for k in _COPEDENT if not k.startswith('P'))} levers), "
          f"build #{build_n})")
    return RIG


def main() -> None:
    build_rig()


if __name__ == "__main__":
    main()
