"""Bead-grid checker: every PRINTED length must be a whole multiple of the nozzle.

  py -3.12 -m tools.check_beads             # report off-grid constants
  py -3.12 -m tools.check_beads --all       # also list what is exempt, and why
  py -3.12 -m tools.check_beads --only direct_bench,keyhead_v2
  py -3.12 tools/check_beads.py            # the same, run as a script

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

(plus "layout" for where purchased parts sit, rib-comb stations and tuned
knobs pinned by model asserts.)

Anything else off-grid is a finding. Exit code = number of findings.
This file is the project DRIVER; the walker itself is cadkit.bead_check
(literal-vs-derived logic, count/angle skipping, per-part NOZZLE_D grids).
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))   # run as a script too

from cadkit import bead_check

import src.dimensions as D

SRC = pathlib.Path(__file__).resolve().parent.parent / "src"
OWN_PROCESS = ("flash_bench",)     # sets board_geom's R1 switch before importing it

# ── exemptions ──────────────────────────────────────────────────────────────
# name -> (category, reason). A bare name matches in EVERY module; "mod.NAME"
# pins it to one. Keep the reason specific -- "it's hardware" is not a reason,
# "MR85 bearing OD" is.
EXEMPT: dict[str, tuple[str, str]] = {}


def _ex(cat: str, **kv) -> None:
    for k, v in kv.items():
        EXEMPT[k.replace("__", ".")] = (cat, v)


# Screw-drive endcap + two-row endplate (branner). Each is off the 0.8 grid FOR A REASON.
_ex("hardware",
    PULLEY_SOCKET_FLOOR_CLR="2 traces of the 0.2 nozzle the screw pulley prints at, not 0.8 beads",
    SCREW_SOCKET_GAP="steel rod end to socket floor: an assembly clearance, not a printed length",
    _BRG_TEARDROP="teardrop apex = r*sqrt(2) with a 0.2 bore clearance: geometry, not a wall",
    _ROD_TEARDROP="teardrop apex = r*sqrt(2) with the rod's press fit: geometry, not a wall",
    _BELT_HALF_DIAG="half-diagonal of the 5 x 1.4 GT2 belt section: geometry, not a wall",
    _ACCESS_PASS_R="Ø4 swaged string end + 0.6 passage, radius: clearance geometry, not a wall",
)


# Real objects. These are measurements, not choices.
_ex("hardware",
    # BOUGHT PARTS and the fits on them: snapping them to the bead grid would be snapping
    # someone else's part.
    saw_jig__SLOT_W="a FIT on a bought blade's tooth set (McMaster 6927A16) -- a clearance, not a wall",
    saw_jig__FILE_ALLOW="material filed off each piece's cut end -- a machining allowance, not a wall",
    saw_jig__CAP_CLR="the cap's sliding clearance in its channel, each side -- not a wall",
    saw_jig__ROOF_CLR="air between the rod's crest and the tunnel's 45 deg roof -- a clearance",
    saw_jig__CAP_LIFT="air under the cap so it seats on the rod, never the channel floor -- a clearance",
    saw_jig__DROP_HW="the fork's drop gap: the rod's crest radius plus clearance for the piece to fall -- not a wall",
    saw_jig__ROOT_R="a BOUGHT rod's thread root (Tr8x2) -- a vendor dimension",
    pi4b__CORNER_R="a BOUGHT board (Raspberry Pi 4), read off its maker's drawing -- a vendor dimension",
    pi4b__HDR_BASE_H="a BOUGHT board (Raspberry Pi 4), read off its maker's drawing -- a vendor dimension",
    pi4b__HDR_H="a BOUGHT board (Raspberry Pi 4), read off its maker's drawing -- a vendor dimension",
    pi4b__HOLE_D="a BOUGHT board (Raspberry Pi 4), read off its maker's drawing -- a vendor dimension",
    pi4b__PIN="a BOUGHT board (Raspberry Pi 4), read off its maker's drawing -- a vendor dimension",
    pi4b__PITCH="a BOUGHT board (Raspberry Pi 4), read off its maker's drawing -- a vendor dimension",
    flash_bench__PITCH="a BOUGHT probe header's pin pitch -- a vendor dimension",
)
_ex("hardware",
    MOTOR_SQ="NEMA17 body 42.3 sq (SERVO42D)",
    MOTOR_SQ_MEASURED="SERVO42D can across the flats, MEASURED (user, 2026-10-20)",
    MOTOR_DRIVER_SQ_MEASURED="SERVO42D driver cover across the flats, MEASURED (user, 2026-10-20)",
    MOTOR_HEIGHT_MEASURED="SERVO42D height with its coil lead, MEASURED (user, 2026-10-20)",
    PI_PLUG_Y0="a POSITION: the Pi's USB-C plug's -Y extent (bronner's pose sets it)",
    PI_PLUG_CLR="plug -> -Y rail clearance (lead, 2026-10-29)",
    OP_PANEL_CLR="brain board -> its registering plastic (fit clearance)",
    OP_PULLEY_CLR="brain board +Y edge -> string 10's screw pulley (air margin, lead 2026-10-29)",
    NEMA17_BOLT_SQ="NEMA17 bolt circle 31.0",
    NEMA17_PILOT_D="NEMA17 pilot boss 22.0",
    PULLEY_OD="GT2 14T over-teeth 8.4",
    PULLEY_FLANGE_OD="GT2 14T flange OD (pulley OD + stock flange)",
    PULLEY_FLANGE_T="GT2 pulley flange stock",
    PULLEY_BORE_MOTOR="= MOTOR_SHAFT_D, the NEMA17 shaft Ø5",
    PULLEY_BORE_SCREW="= FORM_MAJOR, the Tr8x2 pilot-thread groove",
    BELT_PITCH="GT2 tooth pitch 2.0",
    BELT_W="5 mm GT2 open belt (narrowest standard stock)",
    PULLEY_GAP="= the 5 mm GT2 belt + 0.4 running clearance, so it is belt stock + a gap",
    BELT_TOOTH_H="GT2 tooth profile 0.75",
    BELT_T="GT2 belt back thickness 1.4",
    SUPPORT_BRG_OD="688ZZ bearing OD 16.0",
    SUPPORT_BRG_W="= 1 x 688ZZ width 5.0, purchased geometry",
    MR85_W="MR85 bearing width 2.5",
    SCREW_PULLEY_Z="the frozen band plane (the motor bank derives from it) -- a POSITION, not a printed length",
    BRIDGE_BEARING_OD="688ZZ bearing OD 16",
    BRIDGE_BEARING_W="688ZZ bearing width 5.0",
    BRIDGE_AXLE_D="Ø8 precision shaft (the 688ZZ bore)",
    GAUGE_MAX_IN="heaviest published pedal steel string gauge (.080) -- a purchased wire, not a printed length",
    STRING_GAUGE_MAX="GAUGE_MAX_IN in mm -- a wire diameter, not a printed length",
    NUT_BOSS_CLR="radial air round the nut boss: clearance, not a wall",
    SCREW_OD="Tr8x2 lead screw OD",
    SCREW_LEN="lead screw cut length (stock, not printed)",
    MOTOR_SHAFT_D="NEMA17 shaft Ø5",
    # H-type brass leadscrew nut -- purchased, and every one of these is a GUESS
    # until the part arrives (see dimensions.NUT_AF). Do NOT snap them to the grid:
    # snapping would hide the measurement when it lands.
    NUT_AF="Tr8x2 H-flange nut across flats (purchased, off the seller drawing)",
    NUT_FLANGE_L="Tr8x2 H-flange nut flange long axis (purchased, off the seller drawing)",
    NUT_FLANGE_T="Tr8x2 H-flange nut flange thickness (purchased, MEASURED 3.5 2026-11-08)",
    NUT_BOSS_L="Tr8x2 H-flange nut boss length (purchased, MEASURED 10 2026-11-08)",
    NUT_LIP_L="Tr8x2 H-flange nut lip on the flange's top face (purchased, MEASURED 1.5 2026-11-08)",
    NUT_BOSS_D="Tr8x2 H-flange nut boss OD 10.2 (purchased, off the seller drawing)",
    NUT_HOLE_D="H-nut ear through-hole (purchased, MEASURED 3.5 2026-10-16)",
    NUT_HOLE_DX="H-nut ear hole pitch (purchased, GUESSED)",
    CLAMP_END_CLR="belt left between the clamp and each pulley at the ends of travel (air)",
    BELT_CLAMP_L="the belt clamp's measured length along the belt (build.py asserts it)",
    SCREW_PITCH="Tr5x1 thread pitch — the PURCHASED rod's, nothing to do with the nozzle",
    FORM_MINOR="pilot-thread ridge: depth set by the 45-vs-30 deg flank overfill on the Tr8x2 rod",
    FORM_MAJOR="pilot-thread groove: on the Tr8x2 rod's Ø8 crest",
    STRING_NUT_D="Ø4 swaged ball-end nut (measured)",
    STRING_NUT_L="Ø4x3 ball-end nut length (measured)",
    NUT_INSERT_D="M4 heat-set insert install Ø6.0",
    WIRE_D="Ø2 shielded-pair cable (harness dummy)",
    TEE_BOARD_X="custom tee PCB outline 22 x 24 (fabbed board, not printed)",
    TEE_CONN_CY="tee PCB connector-row centre (board-local)",
    NUT_INSERT_L="M4 heat-set insert length 5.0",
    NUT_SCREW_L="M4 screw stock length",
    NUT_PIN_D="Ø4 dowel pin nominal (purchased)",
    NUT_PIN_L="Ø4x4 dowel pin length (purchased)",
    GUIDE_ROD_D="= NUT_HOLE_D, a stock Ø3.5 needle roller (INA NRB 3.5x29.8-G2)",
    GUIDE_ROD_L="stock needle roller length (purchased)",
    GUIDE_EAR_D="the nut ear reamed 9/64in for the guide rod (a stock reamer)",
    GUIDE_RUN_CLR="the guide rod's running clearance in the ear -- a FIT, not material",
    GUIDE_ROD_FIT="snug press for the rod in its socket — a FIT, i.e. a gap, not material",
    NUT_PIN_CLR="slip fit for the Ø2 dowel in its seat — a gap, not material",
    _GROOVE_R="GT2 groove profile radius (belt tooth form)",
    GROOVE_CLR="GT2 groove print allowance (a clearance)",
    MOTOR_SHAFT_FLAT="PURCHASED SERVO42D shaft: 4.5 across its D flat (measured)",
    MOTOR_SHAFT_FLAT_L="PURCHASED SERVO42D shaft: the D flat's length (measured 18)",
    MOTOR_SHAFT_PROUD="PURCHASED SERVO42D shaft: 19.5 proud of the pilot boss (measured)",
    GROOVE_DEPTH="GT2 groove depth (belt tooth form)",
    GROOVE_MOUTH="GT2 groove width at the OD (belt tooth form)",
    _TR_AC="PURCHASED Tr8x2 rod: ISO 2904 crest clearance for pitch 2..5 (leadscrew dummy)",
    # latch return spring -- a purchased coil (BOM SKU); OD/wire/free length and
    # rate are the spring's, and the bore/ID/post derive from them
    SPR_OD="latch spring Ø5.0 OD (BOM SKU)",
    SPR_WIRE="latch spring 0.6 music wire",
    PK_MAG_L="Lace Alumitone magnetic (sensing) range 88.9",
    PK_FLG_T="Alumitone mounting-flange thickness 3.3 (datasheet)",
    PK_COIL_W="Alumitone coil-core width 31.0 (datasheet)",
    PK_H_MIN="shortest supported pickup DEPTH (the 15..22 window edge); caps carrier walls",
    EAR_HOLE_X="Alumitone ear-hole pattern 30.6 x 84.0",
    PK_MAX_L="pickup-length WINDOW top = 101.6 Alumitone + 0.4 headroom (decision 94c0a711)",
    GRUB_SWEEP="M4x10 cup-tip usable travel = screw_l - min_bite - ~1 tip",
    JACK_HEAD_D="ISO 7380 M4 button head Ø7.6",
    JACK_HEAD_H="ISO 7380 M4 button head height 2.2",
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
    PCB_T_TOL="+-10% FR4 fab tolerance FACTOR (dimensionless x PCB_T)",
)

_ex("clearance",
    FIT_CLR="slip fit",
    NUT_PIN_CLR="dowel drop-in fit",
    BOOL_OVERSHOOT="boolean cutter overshoot, not a feature",
    M3_CLR_D="M3 clearance hole",
    NUT_SCREW_D="M4 shaft clearance",
    electronics__OP_TAIL_CLR="the least air under the brain board's cut pins; OP_STANDOFF rounds the sum up to beads",
    screw_rail__SEAT_LEDGE_D="= BRG_OD - 2.5: ledge bore = Ø5 screw + washer pass room",
    HEAD_POCKET_D="= JACK_HEAD_D + 0.4 drop-in fit",
    CAVITY_X="deck cavity = plate + 1.5 fit clearance",
    CAVITY_Y="deck cavity = plate + 1.5 fit clearance",
    SEAT_CLR="slop under the bearing stack (it seats UP on the ledge, so this is a gap)",
    SCREW_CLR_D="= SCREW_OD + 0.5: non-contact bore trimmed so the teardrop apex keeps a 2-bead web",
    AXLE_BORE="= axle Ø5 + 0.4 slide-through fit (10 bearings + 9 fingers)",
    BAND_CLR="carrier keep-off from both deck-band edges",
    OPT_GAP="sensor-face to string optical air gap (signal-critical standoff)",
    PART_STRING_CLR="tallest component to string air floor",
    COVER_GAP="sensor face to cover underside slide gap",
    COVER_X0="lid -X edge = op-amp column edge + 0.5 (lid stops short of the quads)",
    WRAP_CLR="wrap turn past the arm outer face (mirrored both Y)",
    CONDUIT_CLR="hand-fed plug pass-through allowance",
    belt_tensioner__SLOT_CLR="belt-to-slot clearance (a gap, not material)",
    belt_tensioner__SLOT_H="= belt + 2 x clearance",
    belt_tensioner__EDGE_CLR="belt edge to the slot's closed end (a gap)",
    belt_tensioner__GAP="tension travel between the halves = 2 belt teeth",
    belt_tensioner__HEAD_CLR="head to the window's rails (a gap)",
    belt_tensioner__KEY_DEG="ball-end key angle (degrees, not a length)",
    belt_tensioner__SOCKET_IN="ball centre below the head top (purchased screw)",
    belt_tensioner__INS_FIT="insert pocket slack along the screw (a gap)",
    belt_tensioner__RAIL_CLR="rail to its flat (a gap)",
)

_ex("layout",
    KEYHEAD_INBOARD_X="keyhead endplate inboard face X -- a POSITION (asserted in build.py)",
    MCTRL_FIT="board to printed pocket, a fit", MCTRL_Y1="PCB position: off string 1's motor back",
    MCTRL_Y0="PCB position: Y1 less the routed length", MCTRL_L="routed PCB outline",
    MCTRL_PORT_CLR="a clearance round a PCB", MCTRL_DIP="PCB position below the floor (asserted in build.py)",
    MOTOR_BODY_L="PURCHASED SERVO42D depth, MEASURED 53.4 (asserted against components.motor)",
    MOTOR_CLR="slip fit round a purchased motor body in its pocket",
    BOSS_CLR="slip fit round the purchased O22 pilot boss in its drop-in slot",
    SCREW_L="stock M4 button length (6 mm)",
    TEE_MOUTH_DY="PURCHASED side-entry XH: pad row to mouth face (JST drawing)",
    TEE_BOARD_T="PCB thickness (2-layer FR4)",
    TEE_EAR_X="PCB outline: the bare mounting ear off the +X end",
    TEE_EAR_Y="PCB outline: how deep that ear is (fits the bank stagger)",
    TEE_OUTLINE_X="PCB outline: layout region + ear (fabbed board)",
    TEE_TAIL_CY="PCB fact: the THT tail line, board-local",
    TEE_TAIL_DROP="PCB fact: how far those tails hang below the board",
    TEE_FIT="board fit in its seat",
    TEE_WALL_OVER="seat walls over the board top -- a reach, not a wall",
    STAND_Z0="standing electronics bottom-edge POSITION (over the TRRS pigtail)",
    MOTOR_X_STEP="motor pitch = 42.3 body + MOTOR_GAP; drives the rib comb",
    MOTOR_PULLEY_STANDOFF="pulley clamp position on the motor shaft (purchased-part pose)",
    # harness ROUTING: positions of WIRES, which are purchased and never printed.
    # No bead is laid along a cable run, so the grid has nothing to say about
    # where one sits -- these stay where clearance to tees/motors/rails put them.
    TEE_YSHIFT="tee board centre shift; -Y edge pinned at station y-7",
    X_SLIDE="+-6 fine-X pickup slide travel (user spec; a range, not material)",
)

# The instrument, not the printer.
_ex("musical",
    STRING_PITCH="changer string spacing",
    CARRIAGE_TRAVEL="what the shortest belt can carry: a travel, not a printed length",
    TRAVEL_WANT="the 6 in 2**(n/6) is MUSICAL — stretch is proportional to f^2 and f = 2^(n/12) — not a length",
    NUT_BOT_MIN="the nut's floor: the ceiling less the travel less the nut (a position)",
    NUT_PITCH="nut string spacing",
    STRING_FIELD_W="derived from STRING_PITCH",
    MOUNTING_SPAN="scale length",
    NUT_BLOCK_X="-MOUNTING_SPAN",
    STRING_Z="string plane height (set by the bearing stack)",
    DL_OPEN="string stretch at pitch (physics)",
)


def main() -> int:
    # all machinery lives in the shared engine (cadkit.bead_check) -- this file
    # is the project driver: the WHY up top, and the exemption table with a
    # written reason per entry. NON_LENGTH, N_* counts, angle names and n*BEAD
    # coefficients are the engine's business.
    argv = sys.argv[1:]
    if "--only" not in argv:
        # every module but the ones that must run in a process of their own: importing
        # flash_bench after board_geom has loaded at R2 is an error by design
        argv += ["--only", ",".join(p.stem for p in sorted(SRC.glob("*.py"))
                                    if p.stem not in ("__init__",) + OWN_PROCESS)]
    return bead_check.cli(src=SRC, package="src", exempt=EXEMPT,
                          default_nozzle=float(D.NOZZLE_D), argv=argv)


if __name__ == "__main__":
    raise SystemExit(main())
