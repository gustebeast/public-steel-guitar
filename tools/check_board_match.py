"""Board match: the CAD's model of the sensor board vs the board elec actually lays out.

  py -3.12 -m tools.check_board_match

WHY THIS EXISTS. The lever sensor board is described TWICE and neither copy is derived
from the other, because the dependency genuinely runs both ways:

  * the OUTLINE is a mechanical spec. The board is retained by sliding down a groove in
    the housing, so how much bare edge it needs is the housing's business
    (docs/lever-sensor-respin.md, and elec/lever_sensor.py says so itself).
  * the PLACEMENTS are an electrical output. src.knee_lever.SENSOR_BOM is generated from
    the laid-out board, and the housing's plinth relief is cut to clear those parts.

So each side owns half of it and each side has to believe the other half. Nothing checked
that they still agreed, and a change to one is invisible in the other: the CAD builds and
renders perfectly with a stale BOM, and the netlist is valid with a stale outline.

It has already gone wrong both ways. The +X edge was widened here on 2026-09-29 -- the
groove grips 1.85 mm of it and the sensor's courtyard was 0.87 inside that -- and only
the CAD copy moved (user: "did you add the extra PCB to both?"). And the CAD's BOM still
carries the buck converter and its inductor that the 2026-09-21 re-spin deleted.

WHAT IT COMPARES: the outline, the chip's position in the board-centred frame, the board
thickness, which refs exist, and where each one sits once both are put in the CHIP's
frame -- which is the frame the housing cares about, since the chip is the axle axis.

NOT IN THE BOM BY DESIGN: J1 (cadkit models the real connector, see sensor_connector)
and the SWD test pads, which are copper with no body to clear.

(Importing the elec side pulls in skidl, which complains on stderr about KiCad library
paths it does not need here. The report is on stdout; redirect stderr if it is in the
way. Exit is 1 while the two disagree, so this can gate.)
"""

from __future__ import annotations

import argparse
import os
import sys

TOL = 0.005                     # mm: below this the two are the same number
NO_BODY = ("J1", "TP1", "TP2", "TP3", "TP4")


def _elec():
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "elec"))
    import lever_sensor                                  # noqa: E402
    return lever_sensor


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tol", type=float, default=TOL)
    a = ap.parse_args()

    from src import knee_lever as KL
    EL = _elec()
    bad = []

    def cmp(what, cad, elec):
        ok = abs(cad - elec) <= a.tol
        print("  %-28s CAD %10.4f   elec %10.4f   %s"
              % (what, cad, elec, "ok" if ok else "DIFFER by %.4f" % (cad - elec)))
        if not ok:
            bad.append(what)

    print("OUTLINE and datum")
    cmp("width (X)", KL.PCB_X1 - KL.PCB_X0, EL.BOARD_W)
    cmp("length (Z)", KL.PCB_Z1 - KL.PCB_Z0, EL.BOARD_L)
    cmp("thickness", KL.PCB_T, float(EL.BOARD_NOTES["thickness_mm"]))
    # the chip is the axle axis, so where it sits in the board-centred frame is fixed by
    # the outline: half the board, less the distance from the chip to each far edge
    # ...from the CAD's OWN width, not elec's. Mixing the two made this line report a
    # third number that was neither side's, which is worse than not checking it.
    cmp("chip x in board frame", (KL.PCB_X1 - KL.PCB_X0) / 2 - KL.PCB_X1, EL.CHIP_XY[0])
    cmp("chip z in board frame", (KL.PCB_Z1 - KL.PCB_Z0) / 2 - KL.PCB_Z1, EL.CHIP_XY[1])

    pl = EL.BOARD_NOTES["placements"]
    bom = {r[0]: (r[5], r[6], r[2], r[3]) for r in KL.SENSOR_BOM}
    print("\nPARTS (%d in the CAD BOM, %d placed by elec)" % (len(bom), len(pl)))
    only_cad = sorted(set(bom) - set(pl))
    only_elec = sorted(set(pl) - set(bom) - set(NO_BODY))
    for r in only_cad:
        print("  %-6s in the CAD BOM, NOT placed by elec -- the housing clears a part "
              "that is not on the board" % r)
    for r in only_elec:
        print("  %-6s placed by elec, NOT in the CAD BOM -- the housing does not know "
              "it is there" % r)
    bad += ["ref %s" % r for r in only_cad + only_elec]

    moved = []
    for ref in sorted(set(bom) & set(pl)):
        bx, bz = bom[ref][0], bom[ref][1]
        ex, ez = pl[ref][0] - EL.CHIP_XY[0], pl[ref][1] - EL.CHIP_XY[1]
        d = ((bx - ex) ** 2 + (bz - ez) ** 2) ** 0.5
        if d > a.tol:
            moved.append((d, ref, bx, bz, ex, ez))
    for d, ref, bx, bz, ex, ez in sorted(moved, reverse=True):
        print("  %-6s CAD (%7.3f,%7.3f)  elec (%7.3f,%7.3f)  %.3f mm apart"
              % (ref, bx, bz, ex, ez, d))
    bad += ["position %s" % m[1] for m in moved]

    # ...and the one thing neither copy states: does anything stand in a groove? The CAD
    # asserts this against its own BOM, which is only as good as the BOM.
    print("\nGROOVE KEEP-OUT, against the ELEC placements")
    grooved = []
    for ref in sorted(set(bom) & set(pl)):
        hw = bom[ref][2] / 2.0            # the courtyard's half-width in X
        ex = pl[ref][0] - EL.CHIP_XY[0]   # the part's centre, in the chip's frame
        if ex + hw > KL.PCB_X1 - KL.CR_ENG + 1e-9:
            grooved.append((ref, ex + hw, "+X", KL.PCB_X1 - KL.CR_ENG))
        if ex - hw < KL.PCB_X0 + KL.CR_ENG - 1e-9:
            grooved.append((ref, ex - hw, "-X", KL.PCB_X0 + KL.CR_ENG))
    for ref, reach, w, lim in grooved:
        print("  %-6s reaches %+.3f past the %s groove's inner face at %+.3f"
              % (ref, reach, w, lim))
    bad += ["groove %s" % g[0] for g in grooved]
    if not grooved:
        print("  nothing stands in either groove band")

    print("\n%s" % ("the two copies of the board agree." if not bad else
                    "%d disagreement(s): the CAD and elec boards are NOT the same board."
                    % len(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
