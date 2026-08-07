"""Bead-grid checker: every PRINTED length must be a whole multiple of the nozzle.

  py -3.12 -m tools.check_beads             # report off-grid constants
  py -3.12 -m tools.check_beads --all       # also list what is exempt, and why
  py -3.12 -m tools.check_beads --only legs,latch

WHY: this build runs a 0.8 mm nozzle. A wall of 1.75 mm is 2.19 beads -- the
slicer (Arachne) cannot lay 2.19 beads, so it either widens two beads to 0.88 or
squeezes in a starved third. Both are fine on a cosmetic face and NOT fine on a
load-bearing ledge, where the improvised bead is exactly where a part
delaminates. Sizing on the grid means what you drew is what gets extruded.

THE RULE (user): every length is either N * BEAD, or another feature +/- N * BEAD.

Those are two different tests, and conflating them is why a naive checker is
useless here:

  BARE LITERAL   (WALL_T = 2.0)              -> the VALUE must be on the grid.
  DERIVED        (Y_HI = AXLE_Y + 3.0)       -> the OFFSETS must be on the grid.
                                                The RESULT usually is not, and
                                                must not be forced to be.

The second case is not a loophole, it is most of the instrument. Y coordinates
descend from a 9.5 mm string pitch and X from a 615 mm scale; neither is ever a
whole number of 0.8 beads, and "fixing" one detunes the guitar. What the printer
cares about is the material you added -- the +3.0 -- and that is what gets
checked. So a derived constant passes iff every numeric literal in its
expression is on-grid (or exempt), whatever the result evaluates to.

Corollary worth knowing: this makes a derived value that is off-grid FOR A
LITERAL REASON visible while leaving the datum chain alone.

THREE THINGS ARE LEGITIMATELY OFF-GRID, and each needs a reason in EXEMPT below:

  hardware  -- a dummy modelling a REAL object. A NEMA17 is 42.3 mm whether or
               not that suits our nozzle. Rounding these lies about fit.
  clearance -- a slip fit is 0.25 mm BY NECESSITY; it is smaller than a bead and
               always will be. Clearances are gaps, not material: no bead is laid
               across a clearance, so the grid has nothing to say about them.
  musical   -- scale length, string pitch, gauges. Set by the instrument.

Anything else off-grid is a finding. Exit code = number of findings.
"""

from __future__ import annotations

import argparse
import ast
import importlib
import os
import pathlib

from cadkit.printing import on_grid

import src.dimensions as D

SRC = pathlib.Path(__file__).resolve().parent.parent / "src"

# ── exemptions ──────────────────────────────────────────────────────────────
# name -> (category, reason). A bare name matches in EVERY module; "mod.NAME"
# pins it to one. Keep the reason specific -- "it's hardware" is not a reason,
# "MR85 bearing OD" is.
EXEMPT: dict[str, tuple[str, str]] = {}


def _ex(cat: str, **kv) -> None:
    for k, v in kv.items():
        EXEMPT[k.replace("__", ".")] = (cat, v)


# Real objects. These are measurements, not choices.
_ex("hardware",
    MOTOR_SQ="NEMA17 body 42.3 sq (SERVO42D)",
    MOTOR_PCB_LEN="SERVO42D driver PCB stack",
    NEMA17_BOLT_SQ="NEMA17 bolt circle 31.0",
    NEMA17_PILOT_D="NEMA17 pilot boss 22.0",
    PULLEY_OD="GT2 14T over-teeth 8.4",
    PULLEY_FLANGE_OD="GT2 14T flange OD (pulley OD + stock flange)",
    PULLEY_FLANGE_T="GT2 pulley flange stock",
    PULLEY_BORE_MOTOR="= MOTOR_SHAFT_D, the NEMA17 shaft Ø5",
    PULLEY_BORE_SCREW="= SCREW_OD, the Tr5x1 screw",
    BELT_PITCH="GT2 tooth pitch 2.0",
    BELT_W="5 mm GT2 open belt (narrowest standard stock)",
    BELT_TOOTH_H="GT2 tooth profile 0.75",
    BELT_T="GT2 belt back thickness 1.4",
    SUPPORT_BRG_OD="MR85 bearing OD 8.0",
    SUPPORT_BRG_W="MR85 bearing width 5.0",
    BRIDGE_BEARING_OD="693 bearing OD 8.0",
    BRIDGE_BEARING_W="693 bearing width 4.0",
    BRIDGE_AXLE_D="Ø3 precision shaft",
    SCREW_OD="Tr5x1 lead screw OD",
    SCREW_LEN="lead screw cut length (stock, not printed)",
    MOTOR_SHAFT_D="NEMA17 shaft Ø5",
    NUT_OD="brass leadscrew nut OD",
    NUT_FLANGE_OD="brass leadscrew nut flange OD",
    NUT_FLANGE_T="brass leadscrew nut flange thickness",
    NUT_BODY_LEN="brass leadscrew nut body length",
    LOCKNUT_OD="M5 locknut across flats",
    LOCKNUT_W="M5 locknut height",
    STRING_NUT_D="Ø4 swaged ball-end nut (measured)",
    STRING_NUT_L="Ø4x3 ball-end nut length (measured)",
    NUT_INSERT_D="M4 heat-set insert install Ø6.0",
    NUT_INSERT_L="M4 heat-set insert length 5.0",
    NUT_SCREW_L="M4 screw stock length",
    NUT_PIN_D="Ø2 dowel pin nominal",
    NUT_PIN_L="Ø2x4 dowel pin length",
    GUIDE_ROD_D="Ø2.5 precision rod",
    )

# Gaps, not material. Always sub-bead; the grid does not apply.
_ex("clearance",
    FIT_CLR="slip fit",
    NUT_PIN_CLR="dowel drop-in fit",
    BOOL_OVERSHOOT="boolean cutter overshoot, not a feature",
    M3_CLR_D="M3 clearance hole",
    NUT_SCREW_D="M4 shaft clearance",
    )

# Where PURCHASED parts sit relative to each other. No bead is laid to define a
# motor pitch, so the grid buys nothing -- and these are load-bearing for the
# LAYOUT: the rib comb is generated from the motor pitch, and the knee-lever
# mount hardcodes a rib X, so a 0.4 mm snap here walked the comb out from under
# the lever and buried its tenons in solid rib (3021 mm^3). Snapped and reverted
# 2026-08-06; chassis now asserts MOUNT_X lands on a rib.
_ex("layout",
    MOTOR_X0="first motor offset -- sized for a >=100 mm free belt span",
    MOTOR_X_STEP="motor pitch = 42.3 body + tension slot; drives the rib comb",
    )

# The instrument, not the printer.
_ex("musical",
    STRING_PITCH="changer string spacing",
    NUT_PITCH="nut string spacing",
    STRING_FIELD_W="derived from STRING_PITCH",
    MOUNTING_SPAN="scale length",
    NUT_BLOCK_X="-MOUNTING_SPAN",
    STRING_Z="string plane height (set by the bearing stack)",
    DL_OPEN="string stretch at pitch (physics)",
    )


def classify(name: str, mod: str) -> tuple[str, str] | None:
    return EXEMPT.get("%s.%s" % (mod, name)) or EXEMPT.get(name)


# Literals that are never a length, so the grid does not apply: array indices,
# the /2 of a centre-line, 360 degrees of a circle, unit scale factors.
STRUCTURAL = {0.0, 1.0, 2.0, 90.0, 180.0, 270.0, 360.0}

# Names that ARE the bead. `13 * BEAD` states a length in the grid's own unit, so
# the 13 is a COUNT -- checking it as a length would reject the very idiom this
# refactor exists to introduce.
BEAD_NAMES = {"BEAD", "NOZZLE_D", "MIN_WALL"}

# Constants that are not lengths at all, by name. Counts and angles.
NON_LENGTH = ("N_STRINGS", "N_TEETH", "SEGMENTS", "COUNT", "_N", "TURNS",
              "_DEG", "ANGLE", "TEETH")


def _is_bead_unit(node: ast.AST) -> bool:
    return (isinstance(node, ast.Name) and node.id in BEAD_NAMES) or (
        isinstance(node, ast.Attribute) and node.attr in BEAD_NAMES)


def _offsets(node: ast.AST) -> list[float]:
    """Numeric literals in an expression that act as LENGTHS.

    Two things are skipped. STRUCTURAL literals (a `/ 2` centre-line, a 180 deg
    rotate, an index) are arithmetic, not material. And the coefficient of a
    `n * BEAD` product is a bead COUNT already stated in grid units -- flagging
    it would reject the idiom the grid is written in. Everything else in a
    geometry expression is an offset someone chose, and is fair game."""
    skip = set()
    for n in ast.walk(node):
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mult):
            if _is_bead_unit(n.right):
                skip.add(id(n.left))
            if _is_bead_unit(n.left):
                skip.add(id(n.right))
    out = []
    for n in ast.walk(node):
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) \
           and not isinstance(n.value, bool) and id(n) not in skip:
            if abs(float(n.value)) not in STRUCTURAL:
                out.append(float(n.value))
    return out


def module_constants(mod_name: str):
    """(name, value, line, kind, offsets) per module-level UPPERCASE constant.

    kind is 'literal' (RHS is a bare number -> check the value) or 'derived'
    (RHS references something -> check the offsets it adds to that something)."""
    text = (SRC / (mod_name + ".py")).read_text(encoding="utf-8")
    mod = importlib.import_module("src." + mod_name)
    out = []
    for node in ast.parse(text).body:
        if not isinstance(node, ast.Assign):
            continue
        for t in node.targets:
            if not (isinstance(t, ast.Name) and t.id.isupper()):
                continue
            v = getattr(mod, t.id, None)
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                continue
            if any(k in t.id for k in NON_LENGTH):     # a count or an angle
                continue
            bare = isinstance(node.value, ast.Constant) or (
                isinstance(node.value, ast.UnaryOp)
                and isinstance(node.value.operand, ast.Constant))
            kind = "literal" if bare else "derived"
            out.append((t.id, float(v), node.lineno, kind,
                        [] if bare else _offsets(node.value)))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="list exempt constants too")
    ap.add_argument("--only", help="comma-separated module names")
    a = ap.parse_args()

    mods = sorted(p.stem for p in SRC.glob("*.py") if p.stem != "__init__")
    if a.only:
        want = {s.strip() for s in a.only.split(",")}
        mods = [m for m in mods if m in want]

    findings: list[tuple[str, str, int, str, float]] = []
    exempted: list[tuple[str, str, float, str, str]] = []
    n_on = n_tot = 0

    for m in mods:
        for name, v, line, kind, offs in module_constants(m):
            n_tot += 1
            cat = classify(name, m)
            if kind == "literal":
                bad = [] if on_grid(v, D.NOZZLE_D) else [v]
            else:
                # derived: the RESULT may sit anywhere (it inherits a musical or
                # hardware datum); what must be on grid is what we ADDED to it
                bad = [o for o in offs if not on_grid(o, D.NOZZLE_D)]
            if not bad:
                n_on += 1
                continue
            if cat:
                exempted.append((m, name, v, cat[0], cat[1]))
                continue
            for o in bad:
                findings.append((m, name, line, kind, o))

    print("bead grid = %.2f mm (nozzle)" % D.NOZZLE_D)
    print("%d module constants: %d clean, %d exempt, %d with OFF-GRID lengths"
          % (n_tot, n_on, len(exempted),
             len({(f[0], f[1]) for f in findings})))

    if a.all and exempted:
        print("\nexempt (off-grid on purpose):")
        for m, name, v, cat, why in sorted(exempted):
            print("  %-9s %-22s %9.3f  %-9s %s" % (m, name, v, cat, why))

    if findings:
        print("\nOFF GRID -- snap these, or add an exemption with a reason.")
        print("('derived' shows the OFFSET at fault, not the constant's value.)")
        cur = None
        for m, name, line, kind, o in sorted(findings):
            if m != cur:
                print("\n  -- src/%s.py --" % m)
                cur = m
            b = abs(o) / D.NOZZLE_D
            print("    :%-4d %-24s %-8s %9.3f = %6.2f beads -> %.2f or %.2f"
                  % (line, name, kind, o, b,
                     int(b) * D.NOZZLE_D, (int(b) + 1) * D.NOZZLE_D))
    else:
        print("\nclean: every printed length is a whole number of beads.")
    return len({(f[0], f[1]) for f in findings})


if __name__ == "__main__":
    raise SystemExit(main())
