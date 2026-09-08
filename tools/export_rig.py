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
    "ILKL": {"key": "q", "moves": {1: +2}},            # D->E  (whole step)
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


def _levers() -> dict:
    """The six KNEE LEVERS' kinematics, keyed by control name, so the viewer can
    show them swing on q/w/e/r/t/y.

    Same shape as _pedals(), read from build.LEVER_STATIONS rather than restated:

      * centre — the station pose. Both designs build in a local frame whose ORIGIN
                 is the axle, so the pose IS the pivot.
      * axis   — a KL station's axle is local +Y and the station applies no rotation,
                 so it stays guitar +Y. A KV station is posed with -90° about Z,
                 which carries +Y to +X.
      * throw  — KL +30°, KV **-20°**, both PROBED (see _verify_levers), because the
                 designs disagree about which way positive goes: +30 swings a KL
                 paddle -X, which is what an "…L" lever does, but +20 drives the KV
                 arm DOWN and the knee LIFTS that one. Shipping +20 swung the
                 vertical lever backwards. A MIRRORED station ("…R") is the design
                 reflected in X, and reflecting a rotation about Y negates it, so
                 the sign flips again with the mirror.
      * lobe_rc — piston stroke = rc*sin(theta), exact, as on the pedals.

    Only the arm and the parts ON the axle swing. Housing, bearings, board and
    sensor stack are stationary, as they are on the pedal.
    """
    from src import build as B
    from src import knee_lever as KL
    from src import knee_lever_vert as KV

    # The piston retracts INTO its cartridge, so the direction is piston -> base.
    # Measured off the placed solids rather than copied from cart_dummies' own
    # `translate((-s, 0, 0))`: that line is written in the KNEE lever's frame and is
    # applied AFTER the pose, so it is only correct for the design it was authored
    # for. Deriving it here makes the mirror and the KV rotation come out right for
    # free, and never silently disagrees with the geometry.
    placed = dict(B._lever_stations_components())

    def _piston_dir(piston, basen):
        if piston not in placed or basen not in placed:
            return None
        pc = placed[piston].val().Center()
        bc = placed[basen].val().Center()
        v = (bc.x - pc.x, bc.y - pc.y, bc.z - pc.z)
        n = sum(c * c for c in v) ** 0.5
        return [round(c / n, 6) for c in v] if n > 1e-9 else None

    out = {}
    for name, kind, sx, sy, mirrored in B.LEVER_STATIONS:
        if sy is None:
            sy = B._vkl_mount_y()
        pre = "" if name == "lkl" else f"{name}_"
        if kind == "kl":
            mz, axis, throw, rc = KL.MOUNT_Z, [0, 1, 0], KL.THROW, KL.LOBE_RC
            swing_nodes = [f"{pre}knee_lever", f"{pre}kl_axle",
                           f"{pre}kl_magnet_cap", f"{pre}kl_magnet"]
            pistons = [f"{pre}main_cart_piston", f"{pre}half_stop_cart_piston"]
        else:
            # NEGATIVE: the knee lifts this arm, and +THROW_V drives it down
            mz, axis, throw, rc = KV.MOUNT_Z, [1, 0, 0], -KV.THROW_V, KV.LOBE_RC_V
            swing_nodes = [f"{pre}kv_lever", f"{pre}kv_magnet"]
            pistons = [f"{pre}kv_main_cart_piston", f"{pre}kv_half_stop_cart_piston"]
        out[name.upper()] = {
            "center": [sx, sy, mz],
            "axis": axis,
            "throw_deg": -throw if mirrored else throw,
            "lobe_rc": rc,
            "swing_nodes": swing_nodes,
            "piston_nodes": pistons,
            "piston_dir": _piston_dir(pistons[0], pistons[0].replace("_piston", "_base")),
            "mirrored": mirrored,
        }
    return out


def _verify_levers(levers) -> None:
    """Check the levers TWO ways: does the transform match CAD, and does it move the
    lever the way a knee actually drives it.

    The second check exists because the first one alone shipped a bug. Matching the
    CAD swing only proves the viewer agrees with whatever sign I fed it — it takes
    the premise on trust, exactly the way round-tripping the copedent to note names
    validated arithmetic against my own transcription. The vertical lever went out
    swinging DOWN when a knee lifts it, and a same-sign check had nothing to say
    about that.

    So: apply the EXPORTED transform to the rest part and assert the physics.
      * a horizontal lever's paddle travels -X, or +X when mirrored (an "…L" lever
        is one the knee pushes left; "…R" is the reflection)
      * a vertical lever's arm RISES
    """
    import cadquery as cq
    from src import build as B
    from src import knee_lever as KL
    from src import knee_lever_vert as KV

    for name, kind, sx, sy, mirrored in B.LEVER_STATIONS:
        if sy is None:
            sy = B._vkl_mount_y()
        spec = levers[name.upper()]
        # The LOCAL angle that the exported (guitar-frame) one must correspond to.
        # Mirroring in X negates a rotation about Y, so it comes back out here.
        # Deriving it rather than re-stating the throw is what keeps this check
        # about the PIVOT (centre/axis/mirror) and leaves the SIGN to the physics
        # assert below — otherwise the two would just agree with each other.
        th = spec["throw_deg"] * (-1 if mirrored else 1)
        if kind == "kl":
            local, mz = KL.knee_lever, KL.MOUNT_Z
            swung = local.rotate((0, 0, 0), (0, 1, 0), th)
        else:
            local, mz = KV.kv_lever.rotate((0, 0, 0), (0, 0, 1), -90), KV.MOUNT_Z
            swung = (KV.kv_lever.rotate((0, 0, 0), (0, 1, 0), th)
                     .rotate((0, 0, 0), (0, 0, 1), -90))

        def _pose(s):
            return (s.mirror("YZ") if mirrored else s).translate((sx, sy, mz))

        truth, rest = _pose(swung), _pose(local)
        c, ax = spec["center"], spec["axis"]
        viewer = (rest.translate((-c[0], -c[1], -c[2]))
                      .rotate((0, 0, 0), tuple(ax), spec["throw_deg"])
                      .translate((c[0], c[1], c[2])))
        a, b = viewer.val().BoundingBox(), truth.val().BoundingBox()
        err = max(abs(u - v) for u, v in
                  ((a.xmin, b.xmin), (a.xmax, b.xmax), (a.ymin, b.ymin),
                   (a.ymax, b.ymax), (a.zmin, b.zmin), (a.zmax, b.zmax)))
        assert err < 1e-6, (
            f"{name}: the viewer's pivot does not reproduce the CAD swing "
            f"({err:.4f} mm) — check axis/sign against the mirror")

        # ...and does it move the way the knee drives it?
        r = rest.val().BoundingBox()
        if kind == "kv":
            assert a.zmax > r.zmax + 1.0, (
                f"{name}: the vertical lever's arm goes DOWN ({r.zmax:.2f} -> "
                f"{a.zmax:.2f}); a knee LIFTS it — the throw sign is inverted")
        elif mirrored:
            assert a.xmax > r.xmax + 1.0, (
                f"{name}: an '…R' lever's paddle must travel +X "
                f"({r.xmax:.2f} -> {a.xmax:.2f})")
        else:
            assert a.xmin < r.xmin - 1.0, (
                f"{name}: an '…L' lever's paddle must travel -X "
                f"({r.xmin:.2f} -> {a.xmin:.2f})")


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
            # the H-nut IS the carriage now: it, its ball end and nothing else
            "carriage_nodes": [f"nut_{i}", f"string_nut_{i}"],
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
    levers = _levers()
    _verify_levers(levers)
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
        elif name in levers:
            entry["lever"] = levers[name]
        copedent.append(entry)
    _nl = sum(1 for c in copedent if "lever" in c)
    assert _nl == len(levers), f"{_nl} lever controls vs {len(levers)} stations"
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
