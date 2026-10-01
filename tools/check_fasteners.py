"""Fastener-feature checker: every screw hole should come from cadkit, not by hand.

  py -3.12 -m tools.check_fasteners
  py -3.12 -m tools.check_fasteners --only knee_lever

WHY THIS EXISTS. cadkit owns what a screw hole IS in this project: an ANCHOR is a
Ø6 × 5 melt-fit pocket with a self-tapping bore below it, so the first build needs
no insert and a stripped thread later needs no reprint — you melt an insert into
the pocket that was always there. A hole cut by hand gets none of that. It also
gets none of the print-direction handling (`print_up` decides teardrop vs plain
bore), none of the wall and bite asserts, and none of the head clearance.

None of that is visible in a render, in the overlap gate, or in a bead check. It
shows up on the bench, once, when a thread strips and there is nowhere for an
insert to go. This session wrote exactly that hole — a bare `printable_bore` at
`M4.selftap_d` for the knee lever's travel stop — and it took a human reading the
code to catch it (user, 2026-09-24: "your screw isn't using the cadkit screw hole
cutter. Seems like we should have validation in place to enforce that screws are
always implemented via the cadkit version since we always want a fitted insert").

WHAT IT FLAGS. A call to a raw bore/cylinder primitive whose DIAMETER argument is
a fastener dimension — either a literal equal to one, or a name like
`M4.selftap_d` / `M4_SHAFT_CLR_D`. That is the signature of a hand-rolled screw
feature: nothing else has a reason to be exactly 4.2 or 6.0 wide.

WHAT IT CANNOT SEE, said out loud so a clean run is not over-read: a hole whose
diameter is spelled some other way (a local `d = 4.2`, or an arithmetic
expression), and a hole that is genuinely not a fastener but happens to land on a
fastener diameter. It reads source, not solids. It is a smoke alarm, not a proof.
"""

from __future__ import annotations

import argparse
import ast
import pathlib

from cadkit.fasteners import M2, M4

ROOT = pathlib.Path(__file__).resolve().parent.parent

# the primitives that make a hole. A fastener diameter passed to any of these is a
# screw feature somebody drew themselves.
BORE_CALLS = {"cyl", "cyl_y", "cyl_x", "printable_bore", "teardrop_bore", "makeCylinder"}

# ...and the helpers that are the RIGHT answer, named here so the report can say so
CADKIT_OK = ("cut_anchor", "cut_boss_anchor", "cut_insert_bore", "cut_selftap",
             "cut_clearance", "cut_head_bore", "cut_m4_pocket", "cut_m4_boss",
             "cut_insert_pocket", "anchor_cutter", "insert_bore_cutter")


def _fastener_dims():
    """{value: [names]} — every diameter cadkit would have used for a screw."""
    out = {}
    for spec in (M2, M4):
        for f in ("screw_d", "selftap_d", "shaft_clr_d", "insert_pilot_d", "insert_bore_d"):
            v = getattr(spec, f, None)
            if v:
                out.setdefault(round(float(v), 3), []).append(f"{spec.name}.{f}")
    return out


DIMS = _fastener_dims()
# the module-level aliases for the same numbers (src imports these by name)
ALIASES = {"M4_SHAFT_CLR_D", "M4_INSERT_D", "M2_SHAFT_CLR_D", "M2_INSERT_D",
           "SCREW_CLR", "M4_SELFTAP_D"}


def _call_name(node):
    f = node.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return None


def _dim_of(node):
    """The fastener dimension this expression names, or None."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        hit = DIMS.get(round(float(node.value), 3))
        return ("%.2f" % node.value) + " = " + "/".join(hit) if hit else None
    if isinstance(node, ast.Attribute) and node.attr in (
            "screw_d", "selftap_d", "shaft_clr_d", "insert_pilot_d", "insert_bore_d"):
        base = node.value.id if isinstance(node.value, ast.Name) else "?"
        return f"{base}.{node.attr}"
    if isinstance(node, ast.Name) and node.id in ALIASES:
        return node.id
    return None


def scan(path):
    """[(line, call, dimension)] — the hand-rolled fastener features in one file.

    ONLY WHAT IS BEING CUT. A cylinder at a fastener diameter is only a screw hole if
    something subtracts it; drawn as material it is a screw DUMMY or, in one case, a Ø4
    TPU nub. Scanning every cylinder found five, three of which were solids -- a checker
    that cries wolf three times in five gets ignored, which is worse than not having it.
    So the search starts at each `.cut(...)` and looks inside its argument."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and _call_name(node) == "cut" and node.args):
            continue
        for sub in ast.walk(node.args[0]):
            if not isinstance(sub, ast.Call) or not sub.args:
                continue
            if _call_name(sub) not in BORE_CALLS:
                continue
            dim = _dim_of(sub.args[0])
            if dim:
                out.append((sub.lineno, _call_name(sub), dim))
    return sorted(set(out))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma-separated module stems")
    a = ap.parse_args()
    want = {s.strip() for s in a.only.split(",")} if a.only else None

    files = sorted(p for p in (ROOT / "src").glob("*.py"))
    total = 0
    for f in files:
        if want and f.stem not in want:
            continue
        hits = scan(f)
        if not hits:
            continue
        print(f"  -- src/{f.name} --")
        for line, call, dim in hits:
            # a CLEARANCE hole wants no insert -- it wants cadkit's print_up handling.
            # Saying so is the difference between a checker and a nag: "use cut_anchor"
            # on a Ø4.4 access way is advice nobody can follow.
            # NOT `want`: that is the --only filter, and shadowing it here made the
            # checker report the FIRST file with a hit and then silently skip every file
            # after it -- `f.stem not in want` still ran, as a substring test against an
            # advice string. It looked like a clean codebase.
            fix = ("cut_clearance/cut_insert_bore"
                   if "clr" in dim.lower() or "insert_bore" in dim.lower() else "cut_anchor")
            print("    :%-5d %-16s at %-22s -> %s" % (line, call, dim, fix))
        total += len(hits)
    if not total:
        print("no hand-rolled fastener features.")
    else:
        print("\n%d hand-rolled fastener feature(s). Each one is a screw hole with no "
              "insert pocket behind it:" % total)
        print("   cut_anchor leaves an insert pocket behind the thread, so a stripped")
        print("   plastic thread never needs a reprint; the clearance cutters carry the")
        print("   print direction, so a horizontal bore comes back a teardrop.")
    return 0        # advisory: some of these are deliberate, so it reports, it does not gate


if __name__ == "__main__":
    raise SystemExit(main())
