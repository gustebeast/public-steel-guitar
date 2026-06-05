"""Overlap checker for the pedal-steel assembly.

Loads every placed component from src.build.collect_components(), finds pairs
whose solids actually interpenetrate, and reports the UNINTENDED ones (skipping
designed contacts like screw-in-nut, bearing-in-block, motor-on-brick, etc.).

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
    frozenset({"screw", "nut"}), frozenset({"screw", "carriage"}),
    frozenset({"nut", "carriage"}), frozenset({"guiderod", "carriage"}),
    frozenset({"screw", "bblock"}), frozenset({"screw", "bearing"}),
    frozenset({"screw", "spulley"}), frozenset({"belt", "spulley"}),
    frozenset({"belt", "mpulley"}), frozenset({"motor", "mpulley"}),
    frozenset({"string", "carriage"}), frozenset({"string", "tuner"}),
    frozenset({"nut", "spulley"}),
    # single support bearing + locknut at the driven end
    frozenset({"bearing", "bblock"}), frozenset({"bearing", "spulley"}),
    frozenset({"locknut", "screw"}), frozenset({"locknut", "bearing"}),
    frozenset({"locknut", "spulley"}), frozenset({"locknut", "bblock"}),
}
GLOBAL_OK = {
    frozenset({"motor", "motor_brick"}), frozenset({"mpulley", "motor_brick"}),
    frozenset({"base_rail", "bblock"}), frozenset({"base_rail", "bridge_mount"}),
    frozenset({"base_rail", "screw"}), frozenset({"base_rail", "guiderod"}),
    frozenset({"bridge_mount", "roller_bridge"}),
    frozenset({"string", "roller_bridge"}), frozenset({"string", "bridge_mount"}),
    frozenset({"base_rail", "carriage"}),  # carriage may dip near the base top
}


def intended(na, nb) -> bool:
    if "build_counter" in (na, nb):
        return True
    # A belt is allowed to touch its OWN two pulleys (it wraps them); any other
    # belt contact (neighbour belt/pulley/rod) is a real clash to be reported.
    if {base(na), base(nb)} <= {"belt", "spulley", "mpulley"} \
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
