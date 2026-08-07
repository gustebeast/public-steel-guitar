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
    WIRE_D="Ø2 shielded-pair cable (harness dummy)",
    JACK_FACE_DX="connector dummies authored with panel face at x=14; DX slides them to the tip",
    TEE_BOARD_X="custom tee PCB outline 22 x 24 (fabbed board, not printed)",
    TEE_CONN_DX="tee PCB connector-row pitch (on the fabbed board)",
    TEE_CONN_CY="tee PCB connector-row centre (board-local)",
    HDR_Z="lifted XH header wire-entry top (connector body stack, purchased)",
    NUT_INSERT_L="M4 heat-set insert length 5.0",
    NUT_SCREW_L="M4 screw stock length",
    NUT_PIN_D="Ø2 dowel pin nominal",
    NUT_PIN_L="Ø2x4 dowel pin length",
    GUIDE_ROD_D="Ø2.5 precision rod",
    _GROOVE_R="GT2 groove profile radius (belt tooth form)",
    _FLAT_LEN="belt dummy: flat splice-zone length of the purchased belt's centreline model",
    _AUX_OFF="belt dummy: sweep-spine offset (centreline model, nothing printed)",
    # latch return spring -- a purchased coil (BOM SKU); OD/wire/free length and
    # rate are the spring's, and the bore/ID/post derive from them
    SPR_OD="latch spring Ø5.0 OD (BOM SKU)",
    SPR_WIRE="latch spring 0.6 music wire",
    SPR_FREE="latch spring 12.0 free length",
    SPR_SOLID="= (N+2)*wire, the spring's solid height",
    SPR_RATE="N/mm, not a length at all",
    SPR_ID="= SPR_OD - 2*wire, the coil bore",
    POST_D="= SPR_ID - clearance; guides the purchased coil",
    latch__TRRS_WAY_Z0="TRRS D11 jack handle way (legs.leg_head owns it)",
    latch__FACE_Y="= legs.BLK_W/2 = SQ_W/2 - COVER_T - SH_CLR: grid minus a CLEARANCE",
    latch__LG_BLK_HALF="= legs.BLK_W/2 = SQ_W/2 - COVER_T - SH_CLR: grid minus a CLEARANCE",
    latch__OCT_TOP="measured octagon apex within the band",
    PK_MAG_L="Lace Alumitone magnetic (sensing) range 88.9",
    PK_FLG_T="Alumitone mounting-flange thickness 3.3 (datasheet)",
    PK_COIL_W="Alumitone coil-core width 31.0 (datasheet)",
    PK_H_MIN="shortest supported pickup DEPTH (the 15..22 window edge); caps carrier walls",
    EAR_HOLE_X="Alumitone ear-hole pattern 30.6 x 84.0",
    PK_MAX_L="pickup-length WINDOW top = 101.6 Alumitone + 0.4 headroom (decision 94c0a711)",
    GRUB_SWEEP="M4x10 cup-tip usable travel = screw_l - min_bite - ~1 tip",
    JACK_HEAD_D="ISO 7380 M4 button head Ø7.6",
    JACK_HEAD_H="ISO 7380 M4 button head height 2.2",
    SPLICE_LAP="open-belt lap allowance in the splice clamp (cut-length spec, soft)",
    ANCHOR_POST_H="tower top = bearing underside - 1.0 asserted (_BRG_GAP); pinned by "
                  "the CARRIAGE_NOM_Z travel chain against the 695ZZ OD",
    UNDER_Z="comb-finger underside plane (must stay flush with _fpro's 6.5 flat); "
            "LEAD PASS FLAGGED: deck rose to 6.4 so only 0.1 clears the deck panel",
    SENSE_D="sensing station: as close to the termination as the stiffness boundary "
            "layer allows; sets the fabbed board's sensor row",
    END_KEEP="PCB layout rule (strip-end keep-out on the fabbed board)",
    PART_KEEP="PCB layout rule (sensor row to anything else, on the fabbed board)",
    EDGE_KEEP="JLCPCB 1.0 edge rule + 0.2 routed-outline tolerance",
    ROW_GAP="PCB layout rule (component row gap on the fabbed board)",
    PKG_CLR="PCB layout rule (least placement gap between packages)",
    ROUT_R="PCB routed-outline internal-corner radius (~2 mm router bit)",
    SLOT_DX="optical aperture over the 0805 triplet (sized by optics, not material)",
    SLOT_DY="optical aperture over the 0805 triplet (spans +-2.225; optics)",
    WRAP_F_B="dimensionless wrap-pitch factor (x gauge per turn), not a length",
    PCB_T_TOL="+-10% FR4 fab tolerance FACTOR (dimensionless x PCB_T)",
    )

# Gaps, not material. Always sub-bead; the grid does not apply.
_ex("clearance",
    FIT_CLR="slip fit",
    NUT_PIN_CLR="dowel drop-in fit",
    BOOL_OVERSHOOT="boolean cutter overshoot, not a feature",
    M3_CLR_D="M3 clearance hole",
    NUT_SCREW_D="M4 shaft clearance",
    latch__CLR="latch sliding fit",
    latch__OCT_CLR="channel floor standoff from the octagon",
    SPR_BORE_D="= SPR_OD + drop-in clearance",
    belt_clamp__M2_CLR_D="M2 clearance hole",
    belt_clamp__BELT_SLOT_CLR="belt drop-in clearance in the slot",
    joint_coupon__CLR="octagon slide-joint fit (tenon shrunk by this)",
    tension_fork__BODY_H="= M3_CLR_D - 0.15: slips the M3 slot height",
    tension_fork__BODY_D="= PLATE_T - 0.3: stops shy of the motor face",
    screw_rail__SEAT_LEDGE_D="= BRG_OD - 2.5: ledge bore = Ø5 screw + washer pass room",
    ZHOLE_D="string-stow bore: string coil + pliers grip room",
    electronics__CH_D="tray-tab channel = TAB_T + 0.3 floor gap",
    top_plate__GAP="deck-panel assembly clearance (0.05 between consecutive panels)",
    top_plate__OPEN_YP="piece opening = pickup +Y body edge + 0.6 assembly gap",
    top_plate__JACK_HEAD_Z="head pocket floor = deck top - head height - 0.3 recess",
    HEAD_POCKET_D="= JACK_HEAD_D + 0.4 drop-in fit",
    CAVITY_X="deck cavity = plate + 1.5 fit clearance",
    CAVITY_Y="deck cavity = plate + 1.5 fit clearance",
    pickup_mount__GAP="pickup-top to heaviest-string air gap (demo height setpoint)",
    EP_TOP_CLR="endplate drop-on X clearance to the rail end",
    KH_DT_CLR="endplate dovetail socket Y fit",
    KH_DT_SEAT="lower-dovetail seating gap (tenon seats on the L-foot, not the ceiling)",
    NUT_POCKET_D="= NUT_OD + 0.2 press-in fit for the brass leadscrew nut",
    CAGE_W="= STRING_NUT_L + 0.6: the ball-end nut slides in freely",
    SCREW_CLR_D="= SCREW_OD + 0.5: non-contact bore trimmed so the teardrop apex keeps a 2-bead web",
    STRING_EXIT_D="string threading bore = .070 C6 string + clearance; kept under the Ø4 nut",
    AXLE_BORE="= axle Ø5 + 0.4 slide-through fit (10 bearings + 9 fingers)",
    AXLE_GRUB_L="M2 self-tap reach = bore crown to arm top + 0.2 bite-through",
    CARRIER_X1="= OP.PCB_X1S - 0.1: a hair inside the band",
    POST_SWEEP_X1="carriage tower +X face + 0.4 travel-sweep clearance",
    WIN_Z0="window bottom = cage bottom at full down-travel - 0.5 sweep room",
    CONTACT_CLR="drawing convention: hair of air at working contacts (boolean noise guard)",
    LANE_CLR="air each side of a wrap, before its finger",
    BAY_R="threading annulus around the wrap rod (trimmed to stay inside the 25.4)",
    BAND_CLR="carrier keep-off from both deck-band edges",
    OPT_GAP="sensor-face to string optical air gap (signal-critical standoff)",
    PART_STRING_CLR="tallest component to string air floor",
    COVER_GAP="sensor face to cover underside slide gap",
    COVER_X0="lid -X edge = op-amp column edge + 0.5 (lid stops short of the quads)",
    WRAP_CLR="wrap turn past the arm outer face (mirrored both Y)",
    CONDUIT_CLR="hand-fed plug pass-through allowance",
    CONDUIT_Z0="= RUN_Z - half the Ø9.5 harness bundle",
    GROOVE_W="string lay-in channel = string + 2x0.4 side gaps",
    GROOVE_FLOOR="string channel depth; per-string floor = gauge + break-angle physics",
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
    MOTOR_PULLEY_STANDOFF="pulley clamp position on the motor shaft (purchased-part pose)",
    TENSION_SLOT="+-1.5 belt-tension travel; interlocks with MOTOR_X_STEP (see above)",
    PEDAL_BAR_H="= PEDAL_AXLE_H(48, on grid) - FOOT_H(12) - HOUS_X1(8.1): a derived "
                "value spelled literal to break the legs/foot_pedal import cycle; "
                "foot_pedal asserts the chain",
    # harness ROUTING: positions of WIRES, which are purchased and never printed.
    # No bead is laid along a cable run, so the grid has nothing to say about
    # where one sits -- these stay where clearance to tees/motors/rails put them.
    CAN_OFF="CAN H/L conductor separation inside the old single-jacket envelope",
    PWR_OFF="24V pair separation; lane edges 2.1 < RACE_HW 2.4",
    LANE_CAN="trunk lane Z, 2.0 pitch stack (wires, not printed)",
    LANE_USB="trunk lane Z, 2.0 pitch stack (wires, not printed)",
    LANE_CTRL="trunk lane Z, 2.0 pitch stack (wires, not printed)",
    RAIL_Y="trunk corridor centre hugging the rail (wire run)",
    CUTOUT_Y="trunk dip into the m9 rail notch; keeps the Ø2.6 USB inside the cut",
    TEE_YSHIFT="tee board centre shift; -Y edge pinned at station y-7",
    _M9X="= motor_pos(9)[0]; the 9 is a STRING INDEX, not a length",
    X_SLIDE="+-6 fine-X pickup slide travel (user spec; a range, not material)",
    _ILKL_X="a rib-comb station (_RIB0 + 5*_RIB); the comb inherits MOTOR_X_STEP",
    _RKL_X="a rib-comb station (_RIB0 + 17*_RIB); the comb inherits MOTOR_X_STEP",
    _KNEE_GAP_L="5 rib-comb steps (odd ON PURPOSE so VKL can centre); comb inherits MOTOR_X_STEP",
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
    LEG_HEIGHT="floor -> body bottom playing height (user ergonomic reference)",
    )


def classify(name: str, mod: str) -> tuple[str, str] | None:
    return EXEMPT.get("%s.%s" % (mod, name)) or EXEMPT.get(name)


# Literals that are never a length, so the grid does not apply: array indices,
# the /2 of a centre-line, 360 degrees of a circle, unit scale factors.
STRUCTURAL = {0.0, 1.0, 2.0, 90.0, 180.0, 270.0, 360.0}

# Names that ARE the bead. `13 * BEAD` states a length in the grid's own unit, so
# the 13 is a COUNT -- checking it as a length would reject the very idiom this
# refactor exists to introduce.
BEAD_NAMES = {"BEAD", "B", "NOZZLE_D", "MIN_WALL"}

# Constants that are not lengths at all, by name. Counts and angles. An "N_"
# prefix is the project's count idiom (N_PEDALS, N_SLOTS) -- handled in
# module_constants alongside these substrings.
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

    def _skip_subtree(sub: ast.AST) -> None:
        # the whole operand, not just a bare Constant: `-13 * B` parses as
        # UnaryOp(13) * B, so skipping only the top node still leaves the 13
        for k in ast.walk(sub):
            skip.add(id(k))

    for n in ast.walk(node):
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mult):
            if _is_bead_unit(n.right):
                _skip_subtree(n.left)
            if _is_bead_unit(n.left):
                _skip_subtree(n.right)
    out = []
    for n in ast.walk(node):
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) \
           and not isinstance(n.value, bool) and id(n) not in skip:
            if abs(float(n.value)) not in STRUCTURAL:
                out.append(float(n.value))
    return out


def module_nozzle(mod_name: str) -> float:
    """This module's nozzle. THE GRID IS A PROPERTY OF THE PART (user).

    Most of the instrument is structure and prints 0.8, but a part with detail
    finer than a 0.8 bead can resolve -- the belt clamp's 2.0 mm GT2 tooth pitch
    -- is printed with a finer nozzle and is graded on ITS grid, not the
    project's. A module opts in by declaring its own NOZZLE_D."""
    mod = importlib.import_module("src." + mod_name)
    n = getattr(mod, "NOZZLE_D", None)
    if isinstance(n, (int, float)) and not isinstance(n, bool) and n > 0:
        return float(n)
    return float(D.NOZZLE_D)


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
            if t.id.startswith("N_") or any(k in t.id for k in NON_LENGTH):
                continue                               # a count or an angle
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

    nozzles: dict[str, float] = {}
    for m in mods:
        nz = nozzles[m] = module_nozzle(m)
        for name, v, line, kind, offs in module_constants(m):
            if name == "NOZZLE_D":       # the grid itself, not a length on it
                continue
            n_tot += 1
            cat = classify(name, m)
            if kind == "literal":
                bad = [] if on_grid(v, nz) else [v]
            else:
                # derived: the RESULT may sit anywhere (it inherits a musical or
                # hardware datum); what must be on grid is what we ADDED to it
                bad = [o for o in offs if not on_grid(o, nz)]
            if not bad:
                n_on += 1
                continue
            if cat:
                exempted.append((m, name, v, cat[0], cat[1]))
                continue
            for o in bad:
                findings.append((m, name, line, kind, o))

    print("bead grid = %.2f mm (project default nozzle)" % D.NOZZLE_D)
    fine = {m: n for m, n in nozzles.items() if abs(n - D.NOZZLE_D) > 1e-9}
    if fine:
        print("per-part grids: " + ", ".join(
            "%s %.2f" % (m, n) for m, n in sorted(fine.items())))
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
            nz = nozzles[m]
            b = abs(o) / nz
            print("    :%-4d %-24s %-8s %9.3f = %6.2f beads -> %.2f or %.2f"
                  % (line, name, kind, o, b, int(b) * nz, (int(b) + 1) * nz))
    else:
        print("\nclean: every printed length is a whole number of beads.")
    return len({(f[0], f[1]) for f in findings})


if __name__ == "__main__":
    raise SystemExit(main())
