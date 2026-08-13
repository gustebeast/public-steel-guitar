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

(plus "layout" for where purchased parts sit, rib-comb stations and tuned
knobs pinned by model asserts.)

Anything else off-grid is a finding. Exit code = number of findings.
This file is the project DRIVER; the walker itself is cadkit.bead_check
(literal-vs-derived logic, count/angle skipping, per-part NOZZLE_D grids).
"""

from __future__ import annotations

import pathlib

from cadkit import bead_check

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
    PULLEY_BORE_SCREW="= SCREW_OD + 0.2 slip fit over the Tr5x1 crests",
    BELT_PITCH="GT2 tooth pitch 2.0",
    BELT_W="5 mm GT2 open belt (narrowest standard stock)",
    PULLEY_GAP="= the 5 mm GT2 belt + 0.4 running clearance, so it is belt stock + a gap",
    BELT_TOOTH_H="GT2 tooth profile 0.75",
    BELT_T="GT2 belt back thickness 1.4",
    SUPPORT_BRG_OD="MR85 bearing OD 8.0",
    SUPPORT_BRG_W="= 2 x MR85 width: the TANDEM stack, purchased geometry",
    MR85_W="MR85 bearing width 2.5",
    SCREW_PULLEY_Z="frozen root datum (the motor bank derives from it) -- a POSITION, not a printed length",
    BRIDGE_BEARING_OD="693 bearing OD 8.0",
    BRIDGE_BEARING_W="693 bearing width 4.0",
    BRIDGE_AXLE_D="Ø3 precision shaft",
    SCREW_OD="Tr5x1 lead screw OD",
    SCREW_LEN="lead screw cut length (stock, not printed)",
    MOTOR_SHAFT_D="NEMA17 shaft Ø5",
    # H-type brass leadscrew nut -- purchased, and every one of these is a GUESS
    # until the part arrives (see dimensions.NUT_AF). Do NOT snap them to the grid:
    # snapping would hide the measurement when it lands.
    NUT_AF="H-nut across flats (purchased, GUESSED)",
    NUT_FLANGE_L="H-nut flange long axis (purchased, GUESSED)",
    NUT_FLANGE_T="H-nut flange thickness (purchased, GUESSED)",
    NUT_BOSS_L="H-nut boss length (purchased, GUESSED)",
    NUT_HOLE_D="H-nut ear through-hole (purchased, GUESSED)",
    NUT_HOLE_DX="H-nut ear hole pitch (purchased, GUESSED)",
    NUT_TOP_Z="frozen datum: the H-nut flange top at the top of travel, asserted against PULLEY_TOP_MAX -- a POSITION, not a printed length",
    SCREW_PITCH="Tr5x1 thread pitch — the PURCHASED rod's, nothing to do with the nozzle",
    FORM_MINOR="pilot-thread ridge: sized 0.1 radially clear of the Tr5x1 rod's root",
    FORM_MAJOR="pilot-thread groove: sized 0.1 radially under the Tr5x1 rod's crest",
    _CUT_OVERSHOOT="cadkit.threads valley overshoot — a cutter-validity term, not material",
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
    GUIDE_ROD_D="Ø3 g6 precision shaft — the SAME part as the bridge axle",
    GUIDE_ROD_FIT="snug press for the Ø3 rod in its socket — a FIT, i.e. a gap, not material",
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
    AXLE_D="Ø5 journal = the 695ZZ bearing bore",
    AIR_GAP="MT6701 air-gap window (datasheet 0.5..2.0): 1.5 nominal, 1.1 at full float",
    CHIP_DISP_MAX="MT6701 datasheet max sensing-centre misalignment",
    HS_SPR_OD="feel coil Ø6 OD (arm-width-limited)",
    HS_SPR_WIRE="feel coil 1.4 music wire (fatigue-sized)",
    HS_SPR_FREE="feel coil free length = solid + throw + preload margin",
    HS_SPR_INST="feel coil drawn at bay length (lightest preload)",
    M4_SELFTAP="M4 thread-forming pilot Ø (minor-diameter bite)",
    SOCK_D="3/8-inch socket driver clearance bore (12.5-13.5 OD + room)",
    CAP_HEX_AF="hex for a 3/8-inch (9.525 AF) socket; printed-oversize allowance",
    AXLE_FLAT_DEPTH="D-flat depth: magnet-tilt margin vs key-face width (0.5 not 0.7)",
    knee_lever__PCB_X0="sensor PCB outline -X edge (fabbed board; circuit-limited)",
    knee_lever__PCB_X1="sensor PCB outline +X edge (fabbed board; edge keepout)",
    CONN_EDGE="JLCPCB component-to-edge rule on the sensor board",
    CONN_RISE="connector row placement on the fabbed board (flush-top chain)",
    CHIP_DROP="chip below the board top edge (fabbed-board layout)",
    CONN_PLUG_RUN="mated XH plug reach past the housing mouth (purchased plug)",
    CAP_SWEEP_R="= hex across-corners circumradius (AF/sqrt3 = 5.312) + slip + print allowance",
    CR_ENG="groove engagement inside the board's edge-keepout band",
    CR_EDGE_KEEP="groove takes this much X edge (JLCPCB +-0.2 + slip budget)",
    HS_BSTOP_BORE="hollow bore clears the M4 tension-screw hex driver",
    HS_BSTOP_OD="thread crest squeezed between the Ø5 driver bore and the cartridge pitch",
    HS_BSTOP_ENGAGE="= 2 turns of the pitch-3 printed thread; capped by the leg clearance",
    HS_TH_PITCH="printed 45-deg thread form (cadkit.threads): helical form, not wall",
    HS_TH_DEPTH="printed thread flank depth (form, not wall)",
    HS_TH_CLR="printed thread male-side diametral fit",
    MAG_TH_PITCH="printed cap-thread form (cadkit.threads)",
    MAG_TH_DEPTH="printed cap-thread flank depth (valley-overlap-limited)",
    MAG_TH_CLR="printed cap-thread male-side fit",
    BED="printer bed limit (256 bed minus margin)",
    CHJ_MOUTH_Z="10-03404 chassis-jack mouth plane (molded-body insertion chain)",
    belt_tensioner__HEAD_D="ISO 7380 M4 button head Ø7.6",
    belt_tensioner__HEAD_H="ISO 7380 M4 button head height 2.2",
    belt_tensioner__SCREW_L="M4x45 stock screw (spans head -> insert; BOM length)",
    CVR_RAIL_W="octagon rail at cadkit's family floor (h_min 4.95 at 0.8) + margin; "
               "4.8 is below the floor",
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
    latch__LG_HEAD_FACE_Y="= legs.SQ_W/2; SQ_W is 55 beads and half an ODD count "
                          "is never on the grid -- a centre-line, not a thickness",
    )

# Gaps, not material. Always sub-bead; the grid does not apply.
_ex("clearance",
    FIT_CLR="slip fit",
    NUT_PIN_CLR="dowel drop-in fit",
    BOOL_OVERSHOOT="boolean cutter overshoot, not a feature",
    M3_CLR_D="M3 clearance hole",
    NUT_SCREW_D="M4 shaft clearance",
    latch__CLR="latch sliding fit",
    latch__OCT_CLR="standoff that ABSORBS the octagon apex's off-grid remainder, "
                   "so the wall behind the pocket lands on a whole bead",
    latch__OCT_CLR_MIN="least standoff of the channel floor from the octagon",
    latch__TIP_GAP="hook tip -> pocket back, so the hook never bottoms",
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
    SEAT_CLR="slop under the bearing stack (it seats UP on the ledge, so this is a gap)",
    _GUIDE_WEB="a MEASURED distance between two bores (0.2 seat clearance, 1.414 = the teardrop apex's sqrt(2)) — an assert term, not material",
    NUT_RECESS_D="= NUT_BOSS_D + 0.4 running clearance round the H-nut's boss",
    NUT_RECESS_H="= NUT_BOSS_L + 0.4 running clearance over the H-nut's boss",
    DRIVE_X1="drive-relief face = swept radius + 0.4 running gap (a clearance, not material)",
    DRIVE_Z0="drive-relief floor = collar bottom - 0.4 running gap",
    DRIVE_Z1="drive-relief ceiling = raised-plane pulley top + 0.4 running gap",
    RAIL_PULLEY_CLR="running gap, screw-rail top to the pulley flange",
    CHASSIS_END_TOP="MEASURED off chassis_0: the +Z face of the chassis end block at the screw line",
    _SOCKET_X0="= GUIDE_ROD_D + 0.05 snug socket fit, halved to an edge",
    CAGE_W="= STRING_NUT_L + 0.6: the ball-end nut slides in freely",
    SCREW_CLR_D="= SCREW_OD + 0.5: non-contact bore trimmed so the teardrop apex keeps a 2-bead web",
    STRING_EXIT_D="string threading bore = .070 C6 string + clearance; kept under the Ø4 nut",
    AXLE_BORE="= axle Ø5 + 0.4 slide-through fit (10 bearings + 9 fingers)",
    AXLE_GRUB_L="M2 self-tap reach = bore crown to arm top + 0.2 bite-through",
    CARRIER_X1="= OP.PCB_X1S - 0.1: a hair inside the band",
    CARRIER_BOT="optical-carrier plinth floor = deck top + 1.0 running clearance (a gap over the deck panel, not material)",
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
    PIVOT_CLR="hub-face to thrust-boss running clearance",
    HS_CLR="piston/coil to channel slide fit, per side",
    HS_PILOT_D="= coil ID - 0.4 nose fit",
    HS_TRAVEL="= follower travel + 0.5 margin (sweep room, not material)",
    HS_SPR_BORE="= coil OD + 0.6 drop-in bore",
    HS_WIN_WY="= tongue + 0.4: passes the tongue, catches the body",
    CEIL_CLR="board top to chassis underside slide gap (the lid IS the retainer)",
    CR_CLR="board slip fit per groove face",
    MAG_POCKET_D="= magnet Ø + 0.2 slip",
    MAG_COLLAR_H="collar stops 0.1 short so the cap lands on the MAGNET",
    CAP_BASE_CLR="cap rim stops short of the flange (same anti-rattle trap)",
    AXLE_FLAT_Y="flat runs 0.1 past the hub half-width",
    AXLE_SET_L="set-screw way: through the wall + 0.2 past the flat",
    AXLE_BORE_D="= axle Ø + 0.2 slip (the set screw holds it)",
    CAP_CLR_H="board-to-cap gap rule: taller parts must clear the sweep",
    CONN_POCKET="connector pocket relief",
    HS_BACK_X="back wall = guide-post back + insert + 0.5 assembly slack (leg-capped)",
    knee_lever__MORT_CLR="octagon mount-joint slide fit (tenon shrunk by this)",
    BAY_CLR="printed clearance around the pedal's board bay",
    TROUGH_X0="trough stops 0.6 off the -X tower face",
    TROUGH_X1="trough stops 0.6 off the +X tower face",
    SEC_MOR_L="= spigot + 0.4 tip gap (slack at the tip, never the shoulder stop)",
    SEC_CABLE_D="axial cable way through the spigot + socket roof (wires, not material)",
    belt_tensioner__CEIL_UZ="0.15 running clearance over the belt back",
    belt_tensioner__LIFT_LEN="= N_TEETH*pitch + 0.2 ridge-fit slack",
    belt_tensioner__GRIP="= bar + 0.4 slide clearance (well length)",
    belt_tensioner__TUN_W="= belt + 0.4 tunnel clearance",
    belt_tensioner__WELL_W="= belt + 0.6 bar-slide clearance",
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
    LOBE_RC="tuned feel knob: 100/9 ratio, coil fatigue headroom, 2.6 web (measured)",
    LOBE_WY="divider/contact-stress trade knob: the asserted pocket divider moves "
            "~4 mm per mm of lobe (a 4.8 snap left 1.0 < the 1.6 tier), while a "
            "narrower lobe raises line-contact stress ~10%/0.5",
    LOBE_RC_V="RC*sin(20 deg) == the horizontal lever's 4.5 stroke (feel-transfer solve)",
    LOBE_RC_P="RC*sin(20 deg) == the horizontal lever's 4.5 stroke (feel-transfer solve)",
    HS_SETBACK="solid-contact solve: first lobe contact at HS_ENGAGE_DEG = 15 deg",
    FOLL_DZ="flushness solve: window bottom lands on the -Z open face",
    MID_Y="spelled chassis Y midpoint (legacy mortise stop; import direction forbids chassis)",
    knee_lever_vert__MOUNT_X="-455 is a rib-comb X; stations land on ribs -478/-455",
    knee_lever_vert__MOUNT_Y="knee-depth slide default pose (continuous adjustment)",
    TROUGH_HZ="print-proven trough section, squeezed between splice mortises and the detent/rail floor",
    LOCK_D="detent pocket sized to the groove-floor band above the trough (asserted at limit)",
    TROUGH_Z0="band bias within the groove floor (see TROUGH_HZ)",
    SEG_BODY_L="the 142 leg-section pitch (H = 590 + 142k - E; clocking phase carries over)",
    TENON_L="the fine-stage law: travel 142 + overlap 50 + 5 dead",
    SH_CLR="shaft-sleeve octagon SLIDE fit per side (the fine stage strokes)",
    SH_H="slider roof pinned at the section joints' -14 roof plane (shared profile)",
    STUB_RIDGE_EP="end-wall tongue at the endplate end wall's centreline (tip - 5)",
    TRRS_DX="TRRS blind-mate axis in the octagon flare band (clearances quoted in situ)",
    TRRS_DY="TRRS axes ride the profile's deep waist (= groove inscribed-circle centre)",
    LATCH_FOOT="FEET index (which foot carries the latch; None = no latch) -- not a length",
    )

# The instrument, not the printer.
_ex("musical",
    STRING_PITCH="changer string spacing",
    CARRIAGE_TRAVEL="the 6 in 2**(n/6) is MUSICAL — stretch is proportional to f^2 and f = 2^(n/12) — not a length",
    NUT_PITCH="nut string spacing",
    STRING_FIELD_W="derived from STRING_PITCH",
    MOUNTING_SPAN="scale length",
    NUT_BLOCK_X="-MOUNTING_SPAN",
    STRING_Z="string plane height (set by the bearing stack)",
    DL_OPEN="string stretch at pitch (physics)",
    LEG_HEIGHT="floor -> body bottom playing height (user ergonomic reference)",
    )



def main() -> int:
    # all machinery lives in the shared engine (cadkit.bead_check) -- this file
    # is the project driver: the WHY up top, and the exemption table with a
    # written reason per entry. NON_LENGTH, N_* counts, angle names and n*BEAD
    # coefficients are the engine's business.
    return bead_check.cli(src=SRC, package="src", exempt=EXEMPT,
                          default_nozzle=float(D.NOZZLE_D))


if __name__ == "__main__":
    raise SystemExit(main())
