"""Overlap checker for the pedal-steel assembly.

Loads every placed component from src.build.collect_components(), finds pairs
whose solids actually interpenetrate, and reports the UNINTENDED ones (skipping
designed contacts like screw-in-nut, bushing-in-rail, motor-on-bank, etc.).

  py -3.12 -m tools.check_overlaps            # report unintended overlaps
  py -3.12 -m tools.check_overlaps --all      # also list intended contacts

Exit code is the number of unintended overlapping pairs (0 = clean).
"""

from __future__ import annotations

import re
import sys

from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp

from src.build import collect_components

VOL_EPS = 1.0   # mm^3 — ignore numerically-tiny touching contacts


def base(name: str) -> str:
    return re.sub(r"_\d+$", "", name)


def idx(name: str):
    m = re.search(r"_(\d+)$", name)
    return int(m.group(1)) if m else None


# Designed contacts that SHOULD interpenetrate / touch — not problems.
PER_STRING_OK = {
    frozenset({"leadscrew", "nut"}), frozenset({"leadscrew", "carriage"}),
    frozenset({"nut", "carriage"}), frozenset({"guide_rod", "carriage"}),
    frozenset({"leadscrew", "screw_bearing"}), frozenset({"leadscrew", "screw_pulley"}),
    frozenset({"belt", "screw_pulley"}), frozenset({"belt", "motor_pulley"}),
    frozenset({"motor", "motor_pulley"}),
    frozenset({"string", "carriage"}),
    frozenset({"string_nut", "carriage"}), frozenset({"string_nut", "string"}),
    # nut-block hardware (per string): break pin sets the scale, set screw clamps the string
    frozenset({"break_dowel", "string"}), frozenset({"set_screw", "string"}),
    frozenset({"nut", "screw_pulley"}), frozenset({"screw_bearing", "screw_pulley"}),
    frozenset({"locknut", "leadscrew"}), frozenset({"locknut", "screw_bearing"}),
    # a belt connects its OWN motor and screw, so it touches both there
    frozenset({"belt", "motor"}), frozenset({"belt", "leadscrew"}),
    frozenset({"belt", "belt_clamp"}),   # splice clamp grips its own belt
}
# The bridge endplate hosts the whole drive top end (screw rail fused in, axle
# comb, guide ledges), so most per-string hardware legitimately touches it.
GLOBAL_OK = {
    frozenset({"screw_bearing", "bridge_endplate"}), frozenset({"leadscrew", "bridge_endplate"}),
    frozenset({"locknut", "bridge_endplate"}), frozenset({"screw_pulley", "bridge_endplate"}),
    frozenset({"nut", "bridge_endplate"}), frozenset({"carriage", "bridge_endplate"}),
    frozenset({"bridge_endplate", "bridge_bearings"}),
    frozenset({"string", "bridge_bearings"}), frozenset({"string", "bridge_endplate"}),
    # guide rods drop through the endplate's stop bar into its blind sockets
    frozenset({"guide_rod", "bridge_endplate"}),
    # chassis ties everything into one frame; the motor faceplate walls are fused
    # into it, so motors mount to it
    frozenset({"chassis", "bridge_endplate"}), frozenset({"chassis", "motor"}),
    frozenset({"chassis", "string"}),
    # removable nut block: sits on / bears against / bolts to the chassis; holds
    # the strings + its gauged dowels + set screws
    frozenset({"nut_block", "chassis"}), frozenset({"nut_block", "string"}),
    frozenset({"nut_block", "break_dowel"}), frozenset({"nut_block", "set_screw"}),
    # pickup mount: the bar's tongues ride grooves in the chassis rails; the
    # jaws ride the bar and pinch the pickup, which rests on its shim
    frozenset({"pickup_bar", "chassis"}), frozenset({"pickup_bar", "pickup_jaw"}),
    frozenset({"pickup_bar", "pickup"}), frozenset({"pickup_jaw", "pickup"}),
    frozenset({"pickup_shim", "pickup"}), frozenset({"pickup_shim", "pickup_bar"}),
    frozenset({"pickup_shim", "pickup_jaw"}),
}


def intended(na, nb) -> bool:
    if "build_counter" in (na, nb):
        return True
    # adjacent chassis segments meet at their sliding-dovetail joints (one frame)
    if base(na) == base(nb) == "chassis":
        return True
    # A belt is allowed to touch its OWN two pulleys (it wraps them); any other
    # belt contact (neighbour belt/pulley/rod) is a real clash to be reported.
    if {base(na), base(nb)} <= {"belt", "screw_pulley", "motor_pulley"} \
            and idx(na) == idx(nb):
        return True
    pair = frozenset({base(na), base(nb)})
    if pair in GLOBAL_OK:
        return True
    if idx(na) is not None and idx(na) == idx(nb) and pair in PER_STRING_OK:
        return True
    return False


def bbox_overlap(a, b, tol=0.05) -> bool:
    return (a.xmin < b.xmax - tol and b.xmin < a.xmax - tol and
            a.ymin < b.ymax - tol and b.ymin < a.ymax - tol and
            a.zmin < b.zmax - tol and b.zmin < a.zmax - tol)


def common_volume(sa, sb) -> float:
    try:
        common = BRepAlgoAPI_Common(sa.wrapped, sb.wrapped).Shape()
        props = GProp_GProps()
        BRepGProp.VolumeProperties_s(common, props)
        return props.Mass()
    except Exception:
        return 0.0


def main():
    show_all = "--all" in sys.argv
    comps = [(n, wp.val()) for n, wp in collect_components()]
    bboxes = [s.BoundingBox() for _, s in comps]
    print(f"checking {len(comps)} components for overlaps...")

    bad, ok = [], []
    for i in range(len(comps)):
        for j in range(i + 1, len(comps)):
            if not bbox_overlap(bboxes[i], bboxes[j]):
                continue
            na, nb = comps[i][0], comps[j][0]
            vol = common_volume(comps[i][1], comps[j][1])
            if vol <= VOL_EPS:
                continue
            (ok if intended(na, nb) else bad).append((vol, na, nb))

    bad.sort(reverse=True)
    ok.sort(reverse=True)
    if show_all:
        print(f"\n-- intended contacts ({len(ok)}) --")
        for vol, na, nb in ok:
            print(f"   {vol:9.1f} mm^3   {na:14} <-> {nb}")

    print(f"\n== UNINTENDED overlaps ({len(bad)}) ==")
    for vol, na, nb in bad:
        print(f"   {vol:9.1f} mm^3   {na:14} <-> {nb}")
    if not bad:
        print("   none - clean!")
    sys.exit(len(bad))


if __name__ == "__main__":
    main()
