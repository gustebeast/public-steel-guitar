"""Check hand-typed numbers in comments against the expressions they annotate.

    py -3.12 tools/check_annotations.py [--fix] [module ...]

⚠ WHY THIS EXISTS. Three separate defects in one day had the same shape: a value that
is DERIVED by an expression, with the number it evaluated to typed into the comment
beside it, and nothing anywhere comparing the two. The code follows when an upstream
datum moves; the comment does not. Found this way, by hand, before this existed:

  * src/optical_pickup.py -- BAND_X1, PCB_X0, PCB_X1S and COMPUTE_X0 all 8.46 mm stale
    after the pickup cavity moved, and the MCU's escape annulus recorded as 6.6 mm
    where it is 26.18. The placement argument that note is making was UNDERSOLD 4x by
    its own figure.
  * elec/can_tee.py -- the THT tail band annotated 4.0 where it computes 6.0, against a
    6.4 mm limit. That one turned 2.4 mm of apparent margin into 0.4.

The first full run found 25 more across src/ and elec/, the largest being SCREW_LEN at
14.6 mm. None had reached a purchase: BOM.md carries its own copy of the cut length and
that copy was right. The danger is not that these numbers are load-bearing today, it is
that a number sitting beside an expression LOOKS derived, so the next person to reason
from one will not re-evaluate it. That is exactly how the escape annulus was misread.

Nothing else can catch this: DRC and the netlist checks read copper, the overlap gate
reads solids, and this is a defect in PROSE. It is invisible to every gate by
construction.

⚠ IT REPORTS, IT DOES NOT ASSERT, AND THAT IS DELIBERATE. These annotations go stale
whenever an upstream datum legitimately moves, which is a normal edit and not a fault.
Wiring it as a build assertion would red-gate somebody else's unrelated change. The
useful behaviour is a list a person reads. Exit is 1 when there are findings, so it can
run in CI as a warning step rather than a gate.

⚠ AND THE CHECKER ITSELF SHIPPED TWO BUGS ON ITS FIRST RUN, both of which inflated the
count. `\\w` matches digits, so `X = 11.0` read as a dotted reference and a bare literal
was reported as drifting from itself; and the comment's number was matched without a
leading boundary, so the "0402" in a package name read as 402 and "disagreed" with a
2.0 pitch by 400. A tool that finds wrong numbers is not exempt from having them.
"""
from __future__ import annotations

import importlib
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "elec"))

DEFAULT = ("src.optical_pickup", "src.dimensions", "src.electronics",
           "elec.can_tee", "elec.optical", "elec.output_panel",
           "elec.motor_ctrl", "elec.lever_sensor")

# NAME = <expression>   # <number> ...
# The number must not be a fragment of a longer token -- see the bug note above.
ASSIGN = re.compile(r"^([A-Za-z_]\w*)\s*=\s*([^#\n]+?)\s*#\s*(-?\d+(?:\.\d+)?)(?![\w.])")
# An operator or a DOTTED NAME. [A-Za-z_] before the dot rather than \w, because \w
# matches digits and the literal 11.0 would read as a reference. A bare literal has
# nothing to drift from and is never a finding.
DERIVED = re.compile(r"[-+*/]|[A-Za-z_]\w*\.[A-Za-z_]")
TOL = 0.005                                      # below a printed 2-decimal rounding


def check(mod_name):
    try:
        mod = importlib.import_module(mod_name)
    except Exception as exc:
        return [(mod_name, 0, "-", "did not import: %s" % exc, None, None)]
    path = getattr(mod, "__file__", None)
    if not path:
        return []
    out = []
    for n, line in enumerate(io.open(path, encoding="utf-8").read().splitlines(), 1):
        m = ASSIGN.match(line)
        if not m:
            continue
        name, expr, claimed = m.group(1), m.group(2), float(m.group(3))
        if not DERIVED.search(expr):
            continue
        actual = getattr(mod, name, None)
        if not isinstance(actual, (int, float)) or isinstance(actual, bool):
            continue
        if abs(float(actual) - claimed) > TOL:
            out.append((mod_name, n, name, expr.strip(), claimed, float(actual)))
    return out


def fix(findings):
    """Rewrite each stale number in place, leaving the rest of the comment alone.

    Only the leading number is touched, and only on a line this module already matched,
    so prose like "-- the CUT length (see BOM)" survives. The replacement keeps the
    stale annotation's decimal places, so a comment that said 6 does not become 6.4000.
    """
    by_file = {}
    for mod, n, _name, _expr, claimed, actual in findings:
        if claimed is None:
            continue
        by_file.setdefault(sys.modules[mod].__file__, []).append((n, actual))
    for path, rows in sorted(by_file.items()):
        raw = io.open(path, "rb").read()
        crlf = b"\r\n" in raw
        lines = raw.decode("utf-8").replace("\r\n", "\n").split("\n")
        for n, actual in rows:
            m = ASSIGN.match(lines[n - 1])
            assert m, "line %d of %s stopped matching" % (n, path)
            stale = m.group(3)
            dp = len(stale.split(".")[1]) if "." in stale else 0
            # Keep the stale annotation's precision, but not when keeping it would write
            # a number this checker would flag again -- "-29.8" is 1 dp and -30.5496 at
            # 1 dp is -30.5, which is still 0.05 out. Widen until it lands inside TOL.
            while dp < 3 and abs(round(actual, dp) - actual) > TOL:
                dp += 1
            new_num = "%.*f" % (dp, actual) if dp else "%g" % round(actual, 2)
            lines[n - 1] = lines[n - 1][:m.start(3)] + new_num + lines[n - 1][m.end(3):]
        out = "\n".join(lines)
        io.open(path, "wb").write(
            (out.replace("\n", "\r\n") if crlf else out).encode("utf-8"))
        print("  rewrote %d annotation(s) in %s"
              % (len(rows), os.path.relpath(path, ROOT)))


def main(argv):
    do_fix = "--fix" in argv
    argv = [a for a in argv if a != "--fix"]
    mods = argv[1:] or list(DEFAULT)
    bad = []
    for m in mods:
        bad += check(m)
    if not bad:
        print("every annotated derived value matches its comment")
        return 0
    print("%d annotation(s) disagree with the value they annotate:\n" % len(bad))
    for mod, n, name, expr, claimed, actual in bad:
        if claimed is None:
            print("  %s:%d  %s" % (mod, n, expr))
            continue
        print("  %s:%d  %s" % (mod, n, name))
        print("      = %s" % expr)
        print("      comment says %-10.4g  actual %-10.4g  drift %+.4g"
              % (claimed, actual, actual - claimed))
    if do_fix:
        print()
        fix(bad)
        print("\nre-run without --fix to confirm")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
