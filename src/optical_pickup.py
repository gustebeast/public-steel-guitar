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

# ── where it sits ────────────────────────────────────────────────────────────
# The speaking length ends at the BEARING TANGENT (directly over the axle), NOT at
# BRIDGE_X (which is the ball-end anchor, past the bearing). Distances that matter to
# the physics are measured from here.
TERMINATION_X = D.BRIDGE_AXLE_X                  # -4.0
SENSE_D       = 20.0                             # sensing station, out from the termination
SENSE_X       = TERMINATION_X - SENSE_D          # -24.0
STIFF_FLOOR   = 12.0                             # do not sense closer than this (see docstring)

OPT_GAP = 3.0                                    # sensor face -> string TOP (down-firing)
PCB_T   = 1.6                                    # FR4
PCB_W   = 16.0                                   # X -- fits an LQFP64-class USB-HS MCU
LED_H   = 1.1                                    # 0805 emitter height (sets the board underside)
MCU_H   = 1.7                                    # LQFP64 height (sets the top of the stack)

# Z stack, built DOWNWARD from the strings. The board is DOUBLE-SIDED, and which side
# a part lives on is a real decision:
#   BOTTOM (facing the strings) = the sensor triplets ONLY. Keeping it otherwise bare
#     leaves the optical path clean -- no package near a detector to bounce stray IR.
#   TOP (facing into the tie bar) = the MCU. A 12x12 LQFP in the Y end room made the
#     board 123.6 long, 7.6 past each end of the tie bar; on the top face it costs no
#     length at all. This is what lets a USB-HIGH-SPEED part fit, and therefore what
#     keeps the per-string audio option open.
SENSE_FACE_Z = D.STRING_Z + OPT_GAP              # 19.0 -- sensor faces look down
PCB_BOT      = SENSE_FACE_Z + LED_H              # 20.1 -- board underside
PCB_TOP      = PCB_BOT + PCB_T                   # 21.7 -- board top
STACK_TOP_Z  = PCB_TOP + MCU_H                   # 23.4 -- top of the tallest top-side part

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


# Y extent. ASYMMETRIC on purpose:
#   +Y ends just past the outer string's detector -- nothing lives out there any more.
#   -Y runs a TAIL past the tie bar's edge so the USB receptacle sits in OPEN AIR and a
#     cable can actually be plugged in; buried under the bar it would be unreachable.
#     -Y is also where the user wants the cable routed to the bay.
_OUTER_Y = max(abs(string_y_at(i, SENSE_X)) for i in range(D.N_STRINGS))
SENSE_HL = _OUTER_Y + PD_DY                      # last sensor Y; NOTHING else inside this
TIE_HY   = D.BRIDGE_AXLE_Y + D.BRIDGE_ARM_W / 2  # tie-bar half-span (54.25)
PCB_YP   = SENSE_HL + END_KEEP                   # +Y end
PCB_YM   = -(TIE_HY + 4.0)                       # -Y end: clear of the bar, connector reachable
PCB_L    = PCB_YP - PCB_YM
PCB_CY   = (PCB_YP + PCB_YM) / 2
USB_Y    = -(TIE_HY + 1.0)                       # receptacle centre, just outside the bar

# board envelope, for the tie-bar pocket (shared solid -> pocket and board can't drift)
PCB_X0, PCB_X1 = SENSE_X + PCB_W / 2, SENSE_X - PCB_W / 2


def _part(pkg, x, y, z_top):
    """Package hanging DOWN from the board (bottom side): z_top is its board-side face."""
    dx, dy, dz = pkg
    return box_at(dx, dy, dz, x=x, y=y, z=z_top - dz / 2)


def _part_up(pkg, x, y, z_bot):
    """Package standing UP from the board (top side): z_bot is its board-side face."""
    dx, dy, dz = pkg
    return box_at(dx, dy, dz, x=x, y=y, z=z_bot + dz / 2)


def opt_pcb() -> cq.Workplane:
    """The assembled optical strip: FR4 + every placed component, at its true Z, all
    facing DOWN. Fab/purchased -> NO standalone STEP (cadkit convention); it exists in
    the assembly as the fit-check that it clears the strings and fits the tie bar."""
    pcb = box_at(PCB_W, PCB_L, PCB_T, x=SENSE_X, y=PCB_CY, z=PCB_BOT + PCB_T / 2)

    for i in range(D.N_STRINGS):                          # 10 triplets, on the FAN
        sy = string_y_at(i, SENSE_X)
        pcb = pcb.union(_part(LED_PKG, SENSE_X, sy, PCB_BOT))
        for s in (1, -1):
            pcb = pcb.union(_part(PD_PKG, SENSE_X, sy + s * PD_DY, PCB_BOT))

    pcb = pcb.union(_part_up(MCU_PKG, SENSE_X, 0.0, PCB_TOP))     # TOP side, over the field
    pcb = pcb.union(_part(USB_PKG, SENSE_X, USB_Y, PCB_BOT))      # BOTTOM, -Y tail, open air
    return pcb


def opt_pcb_pocket() -> cq.Workplane:
    """Cutter for the tie-bar pocket, opening DOWNWARD: from the sensor faces up over
    the top-side MCU, with a slip fit in X/Y. Cut from the same numbers as the board,
    so the pocket is always exactly the board. The -Y tail runs out past the bar, so
    the pocket breaks out there and the USB receptacle ends up in open air."""
    clr = 0.3
    return box_at(PCB_W + 2 * clr, PCB_L + 2 * clr, STACK_TOP_Z - SENSE_FACE_Z,
                  x=SENSE_X, y=PCB_CY, z=(SENSE_FACE_Z + STACK_TOP_Z) / 2)


def _assert_field_clear():
    """Guard two bugs this part can silently ship, neither of which the assembly
    overlap gate can catch (board + components are ONE unioned solid, and a pairwise
    checker never tests a solid against itself):
      1. a processor/IO package placed by measuring in from the PCB end landing on a
         string's sensor triplet -- this actually happened, on string 10;
      2. the sensing station creeping inside the string's stiffness boundary layer,
         where pitch would pick up inharmonicity error."""
    near = USB_Y + USB_PKG[1] / 2                    # USB is BOTTOM-side, so it can collide
    if near > -SENSE_HL:
        raise AssertionError(
            f"optical strip: USB reaches Y={near:.2f}, inside the sensing field edge "
            f"{-SENSE_HL:.2f} -- it would sit on a string's sensors")
    if PCB_YP < SENSE_HL:
        raise AssertionError(
            f"optical strip: board +Y end {PCB_YP:.2f} is inside the last detector at "
            f"{SENSE_HL:.2f} -- string 1's sensors would hang off the board")
    if SENSE_D < STIFF_FLOOR:
        raise AssertionError(
            f"optical strip: sensing at {SENSE_D:.1f} mm from the termination is inside "
            f"the {STIFF_FLOOR:.1f} mm stiffness floor -- pitch would be inharmonic")


_assert_field_clear()
