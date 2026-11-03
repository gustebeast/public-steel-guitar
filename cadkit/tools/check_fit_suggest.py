"""Gate on cadkit.fitted_joint.suggest(): clearance per joint, from the prints on record.

    py -3.12 cadkit/tools/check_fit_suggest.py      # from a project root; exit 0 = holds

Each case is a joint whose answer a print settled, or a property the rule promises. It
does not build geometry, so it runs in a second.
"""
from __future__ import annotations

import pathlib
import sys

# run as a script: the folder holding the cadkit package goes on the path
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from cadkit import fitted_joint as FJ  # noqa: E402

GF, PCTG = "PETG-GF", "PCTG"

# (what it is, suggest() args, want c, want measured) -- each want is a judged print
CASES = [
    ("lever, 8 tenons at full length", ("up", "up", 34.9, 8, "slide", GF), 0.45, True),
    ("one lever tenon at full length", ("up", "up", 34.9, 1, "slide", GF), 0.35, True),
    ("minimum coupon, snug", ("up", "up", 12.0, 1, "snug", GF), 0.15, True),
    ("seam, full drop", ("N", "N", 64.0, 8, "slide", GF), 0.55, True),
    ("endplate, four tenons", ("N", "down", 58.0, 4, "slide", GF), 0.30, True),
    ("tiramisu wall joint", ("N", "N", 73.6, 2, "slide", PCTG), 0.375, True),
    # PCTG up/up has no print: it borrows PETG-GF and must SAY so
    ("PCTG up/up dock", ("up", "up", 20.0, 4, "slide", PCTG), 0.45, False),
    # past every print of a pair
    ("up/up longer than any print", ("up", "up", 60.0, 8, "slide", GF), 0.45, False),
]


def main():
    bad = 0
    for what, a, want, meas in CASES:
        g = FJ.suggest(*a)
        ok = abs(g.c - want) < 1e-9 and g.measured == meas
        print("  %-32s -> %.3f %-12s %s   %s" % (what, g.c, "measured" if g.measured
                                                 else "NOT measured", g.bracket,
                                                 "ok" if ok else "FAIL (want %.3f, %s)"
                                                 % (want, meas)))
        bad += not ok

    # LONGER AND MULTIPLIED RUN LOOSER: within one pair and material, c never falls as the
    # joint grows -- in length or in tenons -- for either fit.
    mono = []
    for t, s in {(r.tenon, r.socket) for r in FJ.PRINTS}:
        for fit in FJ.FITS:
            for mat in (GF, PCTG):
                last = None
                for L, n in ((5, 1), (12, 1), (20, 1), (34.9, 1), (34.9, 4), (34.9, 8),
                             (58, 8), (80, 8)):
                    c = FJ.suggest(t, s, L, n, fit, mat).c
                    if last is not None and c < last - 1e-9:
                        mono.append("%s/%s %s %s: %.3f at %s x%d after %.3f"
                                    % (t, s, fit, mat, c, L, n, last))
                    last = c
    print("  bigger never tighter             -> %d breach(es)   %s"
          % (len(mono), "ok" if not mono else "FAIL"))
    for m in mono:
        print("        * " + m)
    bad += bool(mono)

    # snug is never looser than slide, and an unmeasured answer always brackets
    loose = [(t, s) for t, s in FJ.CLEARANCE
             if FJ.suggest(t, s, 20, 1, "snug").c > FJ.suggest(t, s, 20, 1, "slide").c]
    nobr = [(t, s) for t, s in FJ.CLEARANCE
            if len(FJ.suggest(t, s, 20, 1, "slide", "PLA").bracket) < 3]
    ok = not loose and not nobr
    print("  snug <= slide; unmeasured brackets -> %s %s   %s"
          % (loose or "", nobr or "", "ok" if ok else "FAIL"))
    bad += not ok

    # the old pair-only shorthand still answers what its callers were given
    ok = (FJ.clearance("N", "N", "short") == 0.30 and FJ.clearance("up", "up") == 0.45
          and FJ.clearance("up", "down") == 0.25)
    print("  clearance() shorthand            -> %s" % ("ok" if ok else "FAIL"))
    bad += not ok

    print("\n%s" % ("suggest() holds" if not bad else "*** %d FAILURE(S) ***" % bad))
    return int(bad)


if __name__ == "__main__":
    sys.exit(main())
