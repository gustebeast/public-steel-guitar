"""OPTICAL per-string pickup — a reflective IR strip that reads all 10 strings
individually, for pitch detection (calibration + audio->MIDI) and, optionally, for
per-string AUDIO.

WHY optical, not a second magnetic hex pickup: a Cycfi Nu Multi is ~$33/string and a
per-string magnetic coil bleeds into its neighbours at this pitch. Reflective IR has
ZERO magnetic crosstalk -- which matters more here than on a normal instrument,
because ten SERVO42D steppers with PWM current control live directly under the deck
and would inject straight into ten passive coils.

MOUNTING -- DOWN-FIRING, FROM THE BRIDGE ENDPLATE'S TIE BAR (user, this round):
The strip does NOT take a deck slot. It hangs from the tie bar that already spans the
strings at the bridge end (bridge_endplate.py), looking DOWN. Three things fall out:

  * The deck's whole slot grid stays with the MAGNETIC pickup, which needs every
    millimetre of approach to the changer (user's own steel measures 35 mm from the
    string termination; a deck-mounted optical band left it stuck at 39).
  * AMBIENT LIGHT: a down-firing sensor is shaded by its own mounting structure. Sun
    and stage lights hit the tie bar, not the detector face. That is the mechanical
    shade we would otherwise have had to add, for free, with no plate over the strings
    and no string-changing penalty. The residual path is light bouncing UP off the
    deck -- keep the deck colour layer dark under the sensing station.
  * WIDTH IS NO LONGER SCARCE. The deck band had to be 12 mm, which capped the MCU at
    a 5x5 QFN and therefore at USB full-speed. The tie bar is 25 mm deep and extends,
    so a USB HIGH-SPEED part fits -- which is what keeps the per-string AUDIO option
    open (10ch x 48kHz x 16bit ~= 960 kB/s does not fit in full-speed).

X POSITION -- FARTHER from the termination is BETTER, which is the opposite of the
intuition. String displacement at distance d from a rigid termination goes as
sin(pi*d/L) ~= pi*d/L, i.e. SIGNAL IS LINEAR IN d. Halving the distance halves the
fundamental. There is also a floor: bending stiffness gives a boundary layer of order
sqrt(EI/T) (a few mm on a wound string) where the string does not follow the ideal
mode shape and the effective termination point becomes frequency-dependent -- sensing
inside it would inject inharmonicity error into a PITCH measurement. So we sit at
SENSE_X, ~20 mm out, and the tie bar is EXTENDED -X to reach it rather than crowding
the bridge. That is more signal than the old deck position had, not less.

SENSING LAYOUT -- per string, THREE parts in a row across Y:
      [PD] --PD_DY-- [IR LED] --PD_DY-- [PD]
  The string sits under the emitter. Light goes down, reflects off the string, and
  returns to both photodiodes. SUM of the pair tracks the string's Z motion;
  DIFFERENCE tracks its Y motion.
    * PITCH path uses the MAGNITUDE of that 2-D vector -- immune to the vibration-plane
      precession that makes single-axis optical pickups drop notes mid-sustain.
    * AUDIO path (if it earns its place) uses the SUM alone -- a linear displacement
      signal. Magnitude would be rectification and would sound like it.
  The pair straddles Y, not X, because transverse string motion is in the Y-Z plane.

SPECTRUM (worth knowing before judging the audio): near the termination the mode-shape
factor sin(n*pi*d/L) grows with n and cancels most of the displacement rolloff, so the
sensed spectrum of a plucked string is ~1/n -- sawtooth-like, NOT a near-sine. Darker
than a magnetic pickup at the same spot by ~6 dB/octave, but harmonically rich. Good
raw material for the per-string overdrive the user wants (per-string clipping never
intermodulates, and heavy clipping compresses away the precession warble).

Frames: absolute X/Y/Z. Components face -Z (DOWN, at the strings).
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from .helpers import box_at
from cadkit.fasteners import M2

# ── where it sits ────────────────────────────────────────────────────────────
# The speaking length ends at the BEARING TANGENT (directly over the axle), NOT at
# BRIDGE_X (which is the ball-end anchor, past the bearing). Distances that matter to
# the physics are measured from here.
TERMINATION_X = D.BRIDGE_AXLE_X                  # -4.0
# Pushed as far +X (toward the termination) as the physics tolerates, on purpose: this is
# the ONE variable that buys back tie-bar overhang, and every millimetre of SENSE_D is a
# millimetre of bar cantilevered over the player. At 12 the bar reaches -20, only 3.4 past
# the endplate block's own -16.6 face -- versus 11.4 at the earlier, arbitrary 20.
# The cost is real and linear: 0.60x the signal of a 20 mm station. Revisit with the
# prototype's measured SNR margin, not by argument -- SENSE_D is the only edit needed,
# PCB_X1 and the endplate's TIE_X0 both derive from it.
SENSE_D       = 12.0                             # sensing station, out from the termination
SENSE_X       = TERMINATION_X - SENSE_D          # -16.0
# Floor, from the string's bending-stiffness length sqrt(EI/T): ~1.2 mm for the plain
# .015 core at ~120 N, ~1.7 mm for the wound .070 (core ~.018) at ~150 N. The boundary
# layer where the string stops following the ideal mode shape -- and the effective
# termination point turns frequency-dependent, which would put inharmonicity straight
# into a PITCH measurement -- runs a few multiples of that, so 5-10 mm. 10 is the
# pessimistic end of that estimate; SENSE_D keeps ~20% over it.
STIFF_FLOOR   = 10.0

OPT_GAP = 3.0                                    # sensor face -> string TOP (down-firing)
PCB_T   = 1.6                                    # FR4
# X width. The sensor row hugs the -X edge (SENSE_EDGE), so the rest of the board is a
# clear +X field -- wide enough to carry the PROCESSOR AND THE CONNECTOR BESIDE the row
# rather than beyond it in Y. That is what collapses the tail: the board is ~20 mm shorter
# than when those two packages had to queue up past the last string. Width is cheap here
# (the tie bar is 26.6 deep in X); Y length is not, because it is all cantilever.
PCB_W   = 20.0                                   # X -- row + a full-length +X parts field
LED_H   = 1.1                                    # 0805 emitter height (sets the board underside)
MCU_H   = 1.7                                    # LQFP64 height
USB_H   = 2.6                                    # micro-B receptacle shell height
# The sensor row sits near the board's -X EDGE, not on its centre line (user). The row's
# X is fixed by the physics (SENSE_X); everything else about the board is free to sit +X
# of it, toward the endplate that already exists. Centring the board on the sensors
# instead pushed its -X edge -- and therefore the tie-bar extension carrying it -- 8 mm
# further over the player for no reason.
# 2.0 puts the widest package (the 1.25 emitter) 1.375 from the routed edge -- clear of
# JLCPCB's 1.0 component-to-edge rule even after their +/-0.2 outline tolerance (1.175).
# Not tighter: the MT6701 board's note in BOM.md is the precedent -- routed-outline-to-
# copper tolerance eats most of a tight budget, and the last millimetre here buys only
# a millimetre of tie-bar reach.
SENSE_EDGE = 2.0                                 # sensor row inset from the board's -X edge

# SINGLE-SIDED (user): every part on the BOTTOM face. The MCU went on the back for one
# round to keep the board short, but there is plenty of room in -Y -- the -Y rail is out
# at ~-128, so past the string field it is open deck -- so the processor moves THERE
# instead. One populated side = one stencil, one reflow, no back-side placement.
#
# Z stack, built DOWNWARD from the strings. The LED sets the board height (its face must
# land on SENSE_FACE_Z); taller packages therefore hang LOWER than the sensors. That is
# fine because they all live at Y < -44, past string 10 -- checked in _assert_field_clear.
SENSE_FACE_Z = D.STRING_Z + OPT_GAP              # 19.0 -- sensor faces look down
PCB_BOT      = SENSE_FACE_Z + LED_H              # 20.1 -- board underside
PCB_TOP      = PCB_BOT + PCB_T                   # 21.7 -- board top; nothing above it now
STACK_BOT_Z  = PCB_BOT - max(MCU_H, USB_H)       # 17.5 -- lowest package (the USB shell)

# ── per-string sensor triplet ────────────────────────────────────────────────
PD_DY   = 1.6                                    # detector offset either side of the string.
                                                 # Scaled to the SHORT standoff -- at 3 mm a
                                                 # wider straddle would view the string at too
                                                 # oblique an angle to return signal.
LED_PKG = (1.25, 2.0, 1.1)                       # 0805 IR emitter: X, Y, Z
PD_PKG  = (0.8, 1.2, 0.8)                        # 0603 photodiode

# ── processor + IO, in the Y end room BEYOND the outer strings ───────────────
# Placed by measuring OUTWARD from the outer string's detector, never IN from the PCB
# end -- measuring from the end is what put a package exactly on string 10 in an
# earlier cut of this part. _assert_field_clear() below makes that unrepeatable.
#
# ONE cable: USB to the Pi. No CAN transceiver -- calibration f0 reaches the Teensy
# (which owns the position->pitch map) via the existing Teensy<->Pi link. The Pi is
# also the DFU host, so it can reflash this board over the same cable.
MCU_PKG = (12.0, 12.0, MCU_H)                    # LQFP64, USB HIGH-SPEED capable -- TOP side
USB_PKG = (7.5, 5.5, 2.6)                        # micro-B SMT receptacle -- BOTTOM side, -Y tail
END_KEEP = 3.0                                   # clear space between outer detector and any part


def string_y_at(i: int, x: float) -> float:
    """String i's Y at X, on the linear nut->changer fan (0 at the nut block, 1 at the
    changer). The sensors sit on THESE, not on a uniform pitch -- which is the whole
    argument for a custom PCB over a fixed-pitch array."""
    t = (x - D.NUT_BLOCK_X) / (D.BRIDGE_X - D.NUT_BLOCK_X)
    return D.nut_y(i) + (D.string_y(i) - D.nut_y(i)) * t


# X extent: the row sits SENSE_EDGE in from the -X edge, board runs +X from there.
PCB_X1 = SENSE_X - SENSE_EDGE                    # -27.0 -- board's -X edge (sets the tie-bar reach)
PCB_X0 = PCB_X1 + PCB_W                          # -11.0 -- +X edge, tucked under the endplate block
PCB_CX = (PCB_X0 + PCB_X1) / 2

# Y extent. ASYMMETRIC on purpose:
#   +Y stops just past the outer string's detector -- nothing lives out there.
#   -Y runs a TAIL carrying the processor and the USB receptacle, which faces -Y so a
#     cable plugs in horizontally and routes to the bay (user). This is the "lots of room
#     in -Y" the single-sided board spends instead of using its back face.
_OUTER_Y = max(abs(string_y_at(i, SENSE_X)) for i in range(D.N_STRINGS))
SENSE_HL = _OUTER_Y + PD_DY                      # last sensor Y; NOTHING else inside this

# OPTICAL RELIEF -- delete the pocket's -X side wall over the sensing field.
# That wall runs parallel to the entire sensor row, and PETG-GF is reflective in IR, so
# it closes a stray path: emitter -> -X -> wall -> back -> photodiode, never touching a
# string. At this spacing the bounce path is a few mm against a ~6 mm signal path (3 down
# to the string and back), so it is a real fraction of what the detectors see -- and
# because it is modulated by the emitter exactly like the signal, AMBIENT SUBTRACTION
# DOES NOT REMOVE IT. It lands as a DC pedestal that eats headroom and contributes shot
# noise carrying no information. Cheaper to delete the wall than to buy distance from it.
RELIEF_HY = SENSE_HL + 1.0                       # relieve over the sensing field only
RELIEF_X1 = PCB_X1 - 8.0                         # overshoot, to break out past the tie bar

# ── RETENTION ────────────────────────────────────────────────────────────────
# Constraint (user): NO endplate material may sit -X of the PCB -- the board itself is
# the furthest anything reaches into the playing area.
#
# So the board is a SLIDE-IN: it enters along -X->+X through the one open face, into a
# slot whose FLOOR (see opt_pcb_pocket) carries it in -Z and sets the sensor standoff,
# whose CEILING caps it in +Z, and whose end/+X walls locate it in Y and +X. Every
# degree of freedom is then closed except sliding back out -X -- so retention is ONE
# screw, not four. Earlier revisions used four only because the pocket had no floor and
# the screws were holding the board UP; giving it a floor is strictly better, because a
# printed ledge sets the standoff far more repeatably than screw clamping does.
MOUNT_X = SENSE_X + 10.0                         # -6.0: +X of the row, off the optical path


def mount_points():
    """The single retention screw: mid-span, in the string 5/6 gap. (x, y, z) is the
    anchor mouth on the board's TOP face -- the screw travels +Z from below, and the
    insert pocket, if those self-tapped threads ever strip, opens downward into the board
    slot where an iron can reach it with the board out.

    Mid-span rather than at an end so it also damps the board against the strings'
    vibration; the ends are already held in Y and -Z by the slot itself. Landing it in
    the string gap is belt-and-braces -- the boss is above the bar and the head below the
    board, both clear of the strings in Z regardless -- but it keeps a future gauge or
    pitch change from quietly putting a screw over a string."""
    mid = (string_y_at(4, MOUNT_X) + string_y_at(5, MOUNT_X)) / 2
    return [(MOUNT_X, mid, PCB_TOP)]
TIE_HY   = D.BRIDGE_AXLE_Y + D.BRIDGE_ARM_W / 2  # tie-bar half-span at the arms (54.25)
# Processor and connector sit BESIDE the sensor row, in the +X parts field -- not beyond
# it in Y. PART_X is that field's centre line, clear of the row by PART_KEEP.
PART_KEEP = 2.0
PART_X    = SENSE_X + PART_KEEP + max(MCU_PKG[0], USB_PKG[0]) / 2
# The MCU sits over the field (harmless: it is +X of the row, so nothing optical, and it
# hangs no lower than the sensors' own standoff allows) and near the connector, which is
# what routing wants. The USB stays at the -Y EDGE -- it has to face out to be pluggable
# -- but now it is the ONLY thing setting the tail length.
MCU_Y    = -35.0
USB_Y    = -(SENSE_HL + END_KEEP + USB_PKG[1] / 2)
# FLOOR LEDGES (user): the slot's floor exists ONLY at the two Y ends -- just enough to
# carry the board and set its standoff -- so the entire underside between them stays free
# for sensors, processor, connector and routing. The board is sized to overhang each
# ledge by FLOOR_L.
FLOOR_L    = 5.0
LEDGE_KEEP = 1.6                                          # ledge inner edge -> nearest package
# Ledge THICKNESS. The tie bar's underside sits at SENSE_FACE_Z, which leaves only
# PCB_BOT - SENSE_FACE_Z = LED_H (1.1) of material under the board -- below the 1.6 floor
# the user set for added material. The ledges are free to hang LOWER than the bar,
# though, because both sit outside the string field (+Y past string 1, -Y past string
# 10), so nothing here has to respect OPT_GAP. So they get their own thickness.
LEDGE_T    = 1.6                                          # two full beads
PCB_YP     = SENSE_HL + END_KEEP + FLOOR_L                # +Y end, incl. its ledge
PCB_YM     = USB_Y - USB_PKG[1] / 2 - LEDGE_KEEP - FLOOR_L  # -Y end, incl. its ledge
PCB_L    = PCB_YP - PCB_YM
PCB_CY   = (PCB_YP + PCB_YM) / 2


def _part(pkg, x, y, z_top):
    """Package hanging DOWN from the board (bottom side): z_top is its board-side face."""
    dx, dy, dz = pkg
    return box_at(dx, dy, dz, x=x, y=y, z=z_top - dz / 2)


# (no _part_up: the board is single-sided -- everything hangs DOWN from PCB_BOT)


def opt_pcb() -> cq.Workplane:
    """The assembled optical strip: FR4 + every placed component, at its true Z, all
    facing DOWN. Fab/purchased -> NO standalone STEP (cadkit convention); it exists in
    the assembly as the fit-check that it clears the strings and fits the tie bar."""
    pcb = box_at(PCB_W, PCB_L, PCB_T, x=PCB_CX, y=PCB_CY, z=PCB_BOT + PCB_T / 2)

    for i in range(D.N_STRINGS):                          # 10 triplets, on the FAN
        sy = string_y_at(i, SENSE_X)
        pcb = pcb.union(_part(LED_PKG, SENSE_X, sy, PCB_BOT))
        for s in (1, -1):
            pcb = pcb.union(_part(PD_PKG, SENSE_X, sy + s * PD_DY, PCB_BOT))

    pcb = pcb.union(_part(MCU_PKG, PART_X, MCU_Y, PCB_BOT))   # +X field, beside the row
    pcb = pcb.union(_part(USB_PKG, PART_X, USB_Y, PCB_BOT))   # +X field, at the -Y edge

    for mx, my, _ in mount_points():                          # M2 clearance holes
        pcb = pcb.cut(box_at(M2.shaft_clr_d, M2.shaft_clr_d, PCB_T + 2,
                             x=mx, y=my, z=PCB_BOT + PCB_T / 2))
    return pcb


def opt_pcb_pocket() -> cq.Workplane:
    """Cutter for the tie-bar pocket, opening DOWNWARD: the board plus everything hanging
    beneath it, with a slip fit. Cut from the same numbers as the board, so the pocket is
    always exactly the board. It runs down to STACK_BOT_Z, below the bar's underside, so
    the deeper tail packages simply break through into open air at Y < -44 -- which is
    what leaves the USB receptacle reachable by a cable."""
    clr, zclr = 0.3, 0.2
    # (a) THE SLOT -- board thickness, with the Z clearance ABOVE so the FLOOR stays the
    # datum: the board rests on the ledges, which makes the sensor standoff a printed
    # dimension rather than something a screw has to hold. The board SLIDES IN along
    # -X -> +X through the one open face.
    pocket = box_at(PCB_W + 2 * clr, PCB_L + 2 * clr, (PCB_TOP + zclr) - PCB_BOT,
                    x=PCB_CX, y=PCB_CY, z=(PCB_BOT + PCB_TOP + zclr) / 2)

    # (b) EVERYTHING UNDER THE BOARD EXCEPT THE TWO END LEDGES -- cut full depth, so the
    # whole middle of the underside is free for sensors, processor, connector and
    # routing. Carried out past the tie bar's -X face as well, so no plastic faces the
    # emitters (the stray emitter->wall->detector path; see RELIEF_* above).
    dy1, dy0 = PCB_YP - FLOOR_L, PCB_YM + FLOOR_L
    x0 = PCB_X0 + clr
    pocket = pocket.union(box_at(x0 - RELIEF_X1, dy1 - dy0, PCB_BOT - STACK_BOT_Z,
                                 x=(x0 + RELIEF_X1) / 2, y=(dy0 + dy1) / 2,
                                 z=(STACK_BOT_Z + PCB_BOT) / 2))
    return pocket


def _ledge_ys():
    """(y0, y1) of each end floor ledge."""
    return [(PCB_YP - FLOOR_L, PCB_YP), (PCB_YM, PCB_YM + FLOOR_L)]


def opt_floor_ledges() -> cq.Workplane:
    """The two end ledges the board rests on, as a solid for the endplate to UNION after
    it has cut the pocket. They hang LEDGE_T below the board rather than relying on the
    1.1 the tie bar happens to leave there -- see LEDGE_T. Both sit outside the string
    field, so hanging below the bar's underside fouls nothing."""
    clr = 0.3
    out = None
    for y0, y1 in _ledge_ys():
        blk = box_at(PCB_W + 2 * clr, y1 - y0, LEDGE_T,
                     x=PCB_CX, y=(y0 + y1) / 2, z=PCB_BOT - LEDGE_T / 2)
        out = blk if out is None else out.union(blk)
    return out


def _assert_field_clear():
    """Guard two bugs this part can silently ship, neither of which the assembly
    overlap gate can catch (board + components are ONE unioned solid, and a pairwise
    checker never tests a solid against itself):
      1. a processor/IO package placed by measuring in from the PCB end landing on a
         string's sensor triplet -- this actually happened, on string 10;
      2. the sensing station creeping inside the string's stiffness boundary layer,
         where pitch would pick up inharmonicity error."""
    # Single-sided AND the parts now sit beside the row rather than beyond it, so the
    # test is in X, not Y: nothing may reach back into the sensor row's X band. (The Y
    # test that used to live here is gone with the tail -- MCU_Y is deliberately over
    # the field now.)
    row_x1 = SENSE_X + max(LED_PKG[0], PD_PKG[0]) / 2
    for name, pkg in (("MCU", MCU_PKG), ("USB", USB_PKG)):
        near = PART_X - pkg[0] / 2
        if near < row_x1:
            raise AssertionError(
                f"optical strip: {name} reaches X={near:.2f}, into the sensor row's band "
                f"(ends {row_x1:.2f}) -- it would sit on the emitters")
    if PART_X + max(MCU_PKG[0], USB_PKG[0]) / 2 > PCB_X0 - 1.6:
        raise AssertionError(
            "optical strip: +X parts field overruns the board edge keepout")
    if PCB_YP < SENSE_HL:
        raise AssertionError(
            f"optical strip: board +Y end {PCB_YP:.2f} is inside the last detector at "
            f"{SENSE_HL:.2f} -- string 1's sensors would hang off the board")
    if SENSE_D < STIFF_FLOOR:
        raise AssertionError(
            f"optical strip: sensing at {SENSE_D:.1f} mm from the termination is inside "
            f"the {STIFF_FLOOR:.1f} mm stiffness floor -- pitch would be inharmonic")


_assert_field_clear()
