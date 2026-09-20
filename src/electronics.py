"""Electronics bay: compute hardware mounts + purchased-part dummies.

The PRO compute stack (per the compute plan) lives on one printed TRAY in the
keyhead bay (x -608..-530 - between the keyhead bulkhead and motor 9, under
the strings, above the open floor):

  - Raspberry Pi 5            (pro: 10ch audio->MIDI + Dexed + USB audio)
  - Teensy 4.1 + audio shield (basic+pro: sensors, CAN servo loop, UI, USB)
  - multichannel TDM ADC stack (pro: 10ch analog in; modeled stacked)
  - buck converter            (24V -> 5V for Pi + Teensy)
  - CAN transceiver breakout  (SN65HVD230: Teensy logic <-> CAN-H/L bus)

A BASIC build prints the SAME tray and just leaves the Pi/ADC/buck mounts
empty - the sockets are the upgrade path.

Mounting is tool-free and zero-hardware: each board sits on corner posts
between low locator strips and is retained by two 45-degree snap fingers
(all clearance-fit in the model - posts stop 0.2 under the board, finger
nubs hover 0.15 over it, so the gate sees no contact). The tray itself
drops in from above: a 40-wide tab on each side edge rides a vertical
channel cut in the rail web (open at the top, floor at the tab's z) -
gravity plus the wire loom holds it; lift straight out for service.

Panel I/O (TS line out, DC power in, USB-C) mounts through a 4 mm recessed
wall in the bridge endplate's lower -Y corner - the endplate prints flat so
the holes are print-trivial, and the inside there is empty floor band.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
# Everything chassis reaches BACK for lives above the chassis import -- see the note
# below. (The AFE board's footprint used to live here; it is deleted.)
# The jack row below is DERIVED from the bridge axle, not hardcoded. The endplate's inboard wall follows
# BRIDGE_AXLE_X (= BRIDGE_X - OD/2, because the string rides the OD and has to leave
# at x = 0), so when the bearing grew Ø8 -> Ø13 the axle stepped 2.5 -X and the wall
# came with it — straight through this board's +X edge, which sat at a constant.
# NOTE: this block sits ABOVE the chassis import ON PURPOSE. chassis builds at
# import time and used to reach BACK here for the AFE_* constants to cut its
# matching boss; the AFE is gone but the ordering still matters for the rest.
# boss (it once also read the tray tab/channel constants, now gone). With the constants below the import, that reach-back hit a
# half-initialised module and `import src.electronics` failed outright with a
# circular-import ImportError -- only working at all because everything else
# happened to import chassis first. These are plain literals, so hoisting them is
# free and makes the module importable on its own.
# ---- bay geometry (the tray's FLAT frame; see STANDING TRAY below) ----
TRAY_X0, TRAY_X1 = -607.0, -547.0
TRAY_Y0, TRAY_Y1 = -127.5, 53.5        # 1.25 off each rail inner face
TRAY_Z0, TRAY_Z1 = -64.0, -61.0        # plate band (3 thick) - 1.15 ABOVE the
                                       # x -575 rib top so the bay rib passes
                                       # under the tray


from . import chassis as CH          # only early constants (X_*, Z_*) used here
from .helpers import box_at, cyl, cyl_x
from cadkit.pcb import (PCB_T as _PCB_T, jst_xh_header, jst_xh_side_header,
                        xh_length, xh_side_length)

# ---- board footprints (x0, x1, y0, y1); board bottom z = TRAY_Z1 + post ----
POST_H = 4 * D.BEAD                    # 3.2 printed standoff posts under each board
BD_T = 1.6
PI_FP     = (-603.0, -547.0, -50.0, 35.0)     # Pi 5: 56 x 85 (long side on Y);
                                       # slid 19 SOUTH (FLUSH round): the wired
                                       # leg's jack chimney + cable drop own the
                                       # tray's west-north corner (x > -603 must
                                       # stay clear of y > 35 there; east is
                                       # walled by motor 0)
# THE SOUTH HALF WAS RE-LAID-OUT around the motor controller (2026-09-14). The
# Teensy stack and the teensy_ifc carrier are both gone -- one board does their job.
# (⚠ THE SIZES IN THIS PARAGRAPH WERE 40 x 35 AND A 90 DEG ROTATION, both true of the
# board as it stood on 09-14 and neither true since: it is 46 x 58 and UNROTATED, which
# is what MCTRL_BOARD_X/Y and MCTRL_ROT below already say. The constants moved and the
# prose above them did not.) The board sits in the -X -Y
# corner and the buck turns with it into the strip east of it. The ADC shifted
# 3 south to clear it; 0.5 of gap is all that is left between them, which is the
# honest state of a 60 x 181 tray holding four boards.
MCTRL_FP  = (-600.0, -554.0, -127.5, -69.5)   # motor controller + power, 46 x 58

BOARD_Z = TRAY_Z1 + POST_H             # every bottom board sits at -67

# ── STANDING TRAY (user, 2026-09-11) ─────────────────────────────────────────
# Everything above is the tray's FLAT layout -- plate, posts, boards -- and it is still
# the frame the tray PRINTS in. In the instrument the whole thing stands on its end with
# the plate's underside against the keyhead endplate's inboard face, so it takes only
# its stack depth in X instead of its 60 mm length, and the motor bank packs up to it
# (dimensions.MOTOR_X0). ONE rigid transform poses every part, so nothing inside the tray
# moves relative to anything else: rotate +90 deg about Y through the flat tray's -X
# bottom edge (up -> +X, the old +X end -> down), plate underside onto the keyhead face,
# bottom edge STAND_Z0.
# NO MOUNT YET (user): bronner is reworking the keyhead endplate, so retention is left
# for that round. The old drop-in side tabs and their rail channels are gone -- they
# do not line up with a standing tray.
STAND_Z0 = -62.0                       # bottom edge: 1.1 above the wired leg's TRRS pigtail
                                       # (top -63.1) where it runs east under this corner
STAND_DX = D.KEYHEAD_INBOARD_X - TRAY_X0
STAND_DZ = (STAND_Z0 + (TRAY_X1 - TRAY_X0)) - TRAY_Z0


def stand(wp: cq.Workplane) -> cq.Workplane:
    """Pose a part authored in the flat tray frame into the standing position."""
    return (wp.translate((-TRAY_X0, 0.0, -TRAY_Z0))
              .rotate((0, 0, 0), (0, 1, 0), 90.0)
              .translate((TRAY_X0 + STAND_DX, 0.0, TRAY_Z0 + STAND_DZ)))


def stand_pt(x: float, y: float, z: float):
    """The same transform for a single point (wiring endpoints on the boards)."""
    dx, dz = x - TRAY_X0, z - TRAY_Z0
    return (TRAY_X0 + STAND_DX + dz, y, TRAY_Z0 + STAND_DZ - dx)


# the dimensions datum the motor bank is packed against has to hold the real boards:
# tallest part above the plate's underside in the flat frame = depth in X once standing
_PI_TOP = BOARD_Z + BD_T + 14.0                # Pi 5 USB/ethernet block top (see pi5)
_MCTRL_TOP = BOARD_Z + BD_T + 9.8              # a MATED XH on the motor controller
_STACK = max(_PI_TOP, _MCTRL_TOP, BOARD_Z + BD_T + 9.0) - TRAY_Z0   # (+ buck caps)
assert _STACK <= D.ELEC_STACK_D + 1e-6, (
    f"the electronics stack is {_STACK:.2f} deep standing, over dimensions.ELEC_STACK_D "
    f"{D.ELEC_STACK_D} -- the motor bank is packed against that number")

# ---- panel jacks (through the endplate recess wall, kept 4 mm thick) ----
# The real connectors are deep (TS ~22 mm, DC ~15.5 mm). Behind the endplate
# the corner is open in X for ~100 mm (out to motor 0 at x -89) EXCEPT the low
# bridge cross-rib (tops at z -65). So the jacks ride HIGH (z -41), clear above
# the rib (and above where the AFE board used to sit) - their bodies then reach
# freely into the open bay.
# The +X face is now the centred 25 mm bridge's tip (BRIDGE_AXLE_X + 25/2 = 8.5), NOT
# X_BRIDGE+WALL -- the block is centred on the axle, not pinned to the rail end. Keep a
# 4 mm panel at that tip and slide the connectors (authored with their panel face at
# x~14) by JACK_FACE_DX so they ride the tip wherever it lands.
JACK_TIP = D.BRIDGE_AXLE_X + D.ENDPLATE_W / 2        # bridge +X face = centred block (8.5).
                                                     # Reads the BRIDGE's width, not the keyhead's:
                                                     # it used KH_EP_THK back when they were one
                                                     # number, which is now simply the wrong end
JACK_WALL_X = JACK_TIP - 4.0                          # inner face of the 4 mm panel (4.5)
JACK_FACE_DX = JACK_TIP - 14.0                        # authored face sits at x~14; ride the +X tip
JACK_Z = -51 * D.BEAD                  # -40.8 jack row centre height
# THE PANEL ROW IS NO LONGER EVENLY PITCHED, and it is not meant to be. TS and USB
# are now BOARD parts on output_panel and their spacing (31.27) is set by that board;
# only the DC inlet is still a free-standing panel jack, and it MOVED OUT of the
# board's span. It had been at -86, between the other two -- which put the 24 V pair
# for ten stepper drivers straight through the board that carries the output buffer,
# and the overlap gate found the wires passing through the PCB. At -118 it is 10 mm
# clear of the board, 10.75 from the -Y rail's inner face, and 50 mm from the audio
# jack, which is the separation that matters.
TS_Y = -68.0                           # THE ONE PANEL INPUT. Every other panel hole
                                       # is now an OUTPUT of the output+panel board
                                       # (DC_Y, USB_Y, defined after it) -- put all
                                       # three jacks on one PCB and the board, not
                                       # this file, decides where the holes go.

# ---- UI: OLED + joystick on the top deck (mounted to the top plate) ----
# Centred along X. NOTE: the strings cover the deck within +-42.75 with only
# ~2 mm clearance, and the +Y/string-10 edge is just ~12 mm wide before the
# rail - too narrow for the 38 mm screen. So the UI sits on the WIDE -Y deck
# band (86 mm, over the motor PCBs, clear of the strings). The joystick (Alps
# RKJXT1F42001: 2-way rotary + 4-way + push) is the sole control.
UI_X      = (CH.X_BRIDGE + CH.X_NUT) / 2     # instrument X centre
DECK_TOP  = D.DECK_TOP_Z                      # 6.4 — THE deck datum (was a stale
                                              # STRING_Z - 10 = 6.0, which sank the UI
                                              # dummies 0.4 into the deck plate); 9.6
                                              # under the strings, bar still can't bottom
OLED_Y    = -100.0                            # wide -Y deck band (clear of strings)
OLED_W, OLED_L, OLED_T = 38.0, 72.0, 1.6      # 2.42" module PCB (Y x X)
JOY_X     = UI_X + 70 * D.BEAD                # -252.17: just +X of the screen
JOY_Y     = -102 * D.BEAD                     # -81.6


def oled() -> cq.Workplane:
    """2.42" 128x64 OLED module dummy: PCB + glass + header, face up."""
    b = box_at(OLED_L, OLED_W, OLED_T, x=UI_X, y=OLED_Y, z=DECK_TOP + OLED_T / 2)
    b = b.union(box_at(62.0, 33.0, 2.0, x=UI_X, y=OLED_Y,
                       z=DECK_TOP + OLED_T + 1.0))          # glass active area
    b = b.union(box_at(20.0, 2.5, 5.0, x=UI_X, y=OLED_Y - OLED_W / 2 + 2.0,
                       z=DECK_TOP + OLED_T + 2.5))          # pin header (-Y edge)
    return b


def joystick() -> cq.Workplane:
    """Alps RKJXT1F42001 multi-control dummy: ~13 mm body + actuator cap."""
    b = box_at(13.0, 13.0, 9.0, x=JOY_X, y=JOY_Y, z=DECK_TOP + 4.5)
    b = b.union(cyl(7.0, 6.0, z=DECK_TOP + 9.0).translate((JOY_X, JOY_Y, 0)))
    return b

# ---- analog front end (bridge-end -Y corner, near the pickup + jacks) ----
# JFET buffer + SPDT signal relay (true-bypass: de-energized = raw straight to
# the jack; energize = the Q-processed DAC output) + relay driver/flyback +
# a local low-noise LDO fed from the nearby 24 V inlet. Clustering all the
# noise-sensitive analog here (away from the motor drivers) is the whole point;
# only buffered/line-level/logic runs make the long trip to the keyhead bay.


def _support_posts(fp, bz):
    """Four plain corner posts for one board footprint (tops flush with the board bottom --
    the board RESTS on them). Support only: NO retention for now (user, 2026-09-10). The M2
    corner anchor, its fat boss and the two locator strips that used to live here are gone;
    these boards are revisited later under the one-M4-beside-the-board rule
    (cadkit.pcb.pcb_cradle hold_edge), so nothing here should grow an M2 back."""
    x0, x1, y0, y1 = fp
    out = cq.Workplane("XY")
    for px in (x0 + 5, x1 - 5):
        for py in (y0 + 5, y1 - 5):
            out = out.add(cyl(5.0, bz - TRAY_Z1, z=TRAY_Z1).translate((px, py, 0)))
    return out


def electronics_tray(standing: bool = True) -> cq.Workplane:
    """The printed tray: plate + board support posts. Prints flat (plate on the bed,
    posts up); stands against the keyhead endplate in the instrument (see STANDING TRAY).
    Pass standing=False for the print pose."""
    body = box_at(TRAY_X1 - TRAY_X0, TRAY_Y1 - TRAY_Y0, TRAY_Z1 - TRAY_Z0,
                  x=(TRAY_X0 + TRAY_X1) / 2, y=(TRAY_Y0 + TRAY_Y1) / 2,
                  z=(TRAY_Z0 + TRAY_Z1) / 2)
    # each board rests on four plain posts -- no retention yet (see _support_posts)
    for fp, bz in ((PI_FP, BOARD_Z), (MCTRL_FP, BOARD_Z)):
        body = body.union(_support_posts(fp, bz))
    # (the NORTH-SHELF lane channel for the TRRS pigtail is gone: standing, the tray's
    #  bottom edge rides above that pigtail instead of lying over it)
    return stand(body) if standing else body


def _board(fp, bz, t=BD_T):
    x0, x1, y0, y1 = fp
    return box_at(x1 - x0, y1 - y0, t, x=(x0 + x1) / 2, y=(y0 + y1) / 2,
                  z=bz + t / 2)


def _ctr(fp):
    return (fp[0] + fp[1]) / 2, (fp[2] + fp[3]) / 2


def pi5() -> cq.Workplane:
    """Raspberry Pi 5 dummy: board + USB/eth block + SoC."""
    cx, cy = _ctr(PI_FP)
    b = _board(PI_FP, BOARD_Z)
    b = b.union(box_at(50.0, 18.0, 14.0, x=cx, y=PI_FP[3] - 9.0,
                       z=BOARD_Z + BD_T + 7.0))
    b = b.union(box_at(15.0, 15.0, 2.5, x=cx, y=cy, z=BOARD_Z + BD_T + 1.25))
    return stand(b)


# (adc_stack is DELETED, 2026-09-14. It modelled a three-PCM1864 carrier that
# digitised ten string signals for the Pi -- a path BOM.md struck out when the
# optical pickup board took on its own 20-channel conversion and sent audio over
# USB. The board had been struck in the BOM and left standing in the CAD, which
# is the wrong way round: the model is what other agents measure against.)


# (THE POWER BOARD IS DELETED, 2026-09-15, merged into the motor controller. It was
#  its own PCB here; folding it in removed a board, a connector and a cable -- and,
#  more usefully, a JUNCTION. The 24 V trunk had to feed both boards at the keyhead
#  and the power board had only a 4-way INLET, so that branch was the one splice in
#  an instrument where every other branch is a board. See elec/motor_ctrl.py U5/F1/F2.)


# ── OUTPUT + PANEL BOARD ─────────────────────────────────────────────────────
# EVERY FRONT-PANEL CONNECTION ON ONE PCB (user, 2026-09-15). It merges the USB
# break-out that stops a laptop back-feeding the Pi with the analog OUTPUT STAGE
# that would not fit on the optical pickup board -- and the merge pays for itself
# twice, because putting the output stage at the panel is what lets the TS JACK
# BE A BOARD PART.
#
# ⚠ THE TS JACK ON THE BOARD FIXES A RULE VIOLATION rather than adding a part.
# BOM.md already specifies a Neutrik NMJ4HCD2 and that jack is PCB-MOUNT with a
# panel bushing -- KiCad ships its footprint. Panel-mounted as this file had it,
# its lugs would have been HAND-SOLDERED, which the project forbids outside a
# factory-assembled board. Same part, same price, and the last hand-soldered
# joint in the instrument goes away. Its nut clamps the endplate, so the PANEL
# takes the cable-yank load and the PCB does not.
#
# ⚠ TWO THINGS THE ENDPLATE HAS TO ABSORB (branner):
#   1. THE PANEL HOLES ARE NO LONGER ONE ROW AT ONE HEIGHT. A 1/4 in jack's axis
#      and a USB-C's axis sit at different heights above the board they share, so
#      the two holes differ in Z by that much (see OP_TS_AXIS_H). Their Y spacing
#      is now 31.27, set by this board rather than by the old 18 mm pitch.
#   2. THERE ARE NOW THREE CONNECTORS ON THE -X EDGE, facing INTO the instrument
#      rather than out the panel: two USB-A shells (J2 to the Pi's gadget port, J4
#      to the optical board) and a USB-C (J3, the hub's upstream to a Pi host port).
#      They want cable room behind them, and a right-angle A shell stands 6.6 off
#      the board.
#   3. THE DC BARREL JACK IS ON THIS BOARD TOO (user, 2026-09-15), and my earlier
#      objection to it was weaker than I made it sound. Two facts settled it: the
#      PJ-005A it replaces is a SOLDER-LUG jack, so it carried the same hand-soldering
#      violation the TS jack did, and BOM.md sizes the 24 V bus UNDER 5 A because the
#      fleet slew is staggered -- which is routine to carry across a board corner. The
#      noise argument survives only as a LAYOUT OBLIGATION, and it is met by keeping
#      PWR_GND a separate net that never joins AGND on this board (see J5/J6).
OP_BOARD_X, OP_BOARD_Y = 74.0, 66.0
# ⚠ IT GREW IN X, 52 -> 74, AND ONLY IN X. The 2026-09-15 respin put the magnetic
# pickup's whole conversion chain on this board -- an MCU, a 24-bit ADC, a DAC, a
# USB hub and a local 24->5 V buck -- because the pickup now LANDS here on screw
# terminals and no analog signal crosses the instrument any more. The board's -Y
# edge sits 3.67 off the chassis rail, so Y had nothing to give; the endplate
# corner is open about 100 in X, and the growth goes BACKWARDS into the bay behind
# the panel face. The panel connectors did not move relative to each other.
#
# Connector anchors, board-local, straight out of elec/output_panel.py.
# ⚠ J2/J3/J4 ARE AT 270, NOT 180, and that is load-bearing: this USB-A footprint's
# courtyard runs -12.68..+3.90 in Y about the pad centroid, so its MOUTH is the -Y
# face. At 180 the shell measures flush against the -X edge while pointing +Y --
# along the board, opening onto the pickup terminals. 270 turns the mouth out
# through the -X edge, which is what these three are for.
OP_J = {"J1": (29.44, 4.00, 90.0),        # panel USB-C, mouth +X
        "J2": (-24.32, 24.00, 270.0),     # USB-A -> the Pi's gadget port, mouth -X
        "J3": (-29.44, 8.00, 270.0),      # USB-C, hub upstream -> a Pi host port
        "J4": (-24.32, -8.00, 270.0),     # USB-A, hub downstream -> optical board
        "J6": (32.02, -20.50, 0.0),       # 24 V inlet, barrel, bushing out +X
        "J7": (0.00, -28.00, 0.0),        # 24 V trunk out, 2 contacts per rail
        # ⚠ J9 WAS ON THE BOARD AND NOT IN THIS TABLE. It is the second 24 V outlet, the
        # optical pickup's feed, added to elec/output_panel.py without ever being added
        # here -- so the CAD has been modelling a board with one power outlet where the
        # netlist has two, and nothing compares the two files. A missing connector is
        # invisible in exactly the way that matters: the solid looks right, and the
        # clearance it does not take is the clearance nobody checks.
        # x is 16.00 rather than 14.00 because at 14.00 its courtyard sat 0.50 mm from
        # J7's and cut the 24 V bus in half -- see the note at the part in
        # elec/output_panel.py.
        "J9": (16.00, -28.00, 0.0),       # 24 V out to the optical pickup board
        # J10, the trunk's SECOND 24 V outlet -- the west-end feed that makes the motor
        # bus dual-fed. On the +X edge, not the -Y row with J7 and J9, because that row
        # is full (measured off the real courtyards: widest gap 5.25 mm against a
        # 13.40 mm connector).
        "J10": (29.70, -8.70, 0.0),
        "J8": (-13.50, 28.00, 0.0)}       # magnetic pickup in, SCREW TERMINALS
# (courtyard L, W, height, courtyard-centre offset from the anchor)
OP_BOX = {"J1": (9.51, 10.73, 3.26, (2.81, 0.00)),
          "J2": (16.57, 15.59, 6.60, (-4.39, 0.00)),
          "J3": (9.51, 10.73, 3.26, (-2.81, 0.00)),
          "J4": (16.57, 15.59, 6.60, (-4.39, 0.00)),
          "J6": (11.59, 16.09, 11.00, (-0.82, -3.20)),
          "J7": (13.49, 6.84, 7.00, (0.00, -0.53)),
          # J9 is a B2B-XH-A now, 2-way -- see elec/output_panel.py. Five millimetres
          # shorter than J7, which is the point: it was emptying the pad row, not
          # saving a part.
          "J9": (8.49, 6.84, 7.00, (0.00, -0.53)),
          "J10": (13.49, 6.84, 7.00, (0.00, -0.53)),   # same B4B-XH-A as J7
          "J8": (11.59, 8.90, 10.50, (-0.25, 0.10))}
OP_TS_XY = (23.11, 21.50)                 # the 1/4 in jack's pad anchor
OP_TS_L, OP_TS_W = 27.62, 20.32           # its courtyard
OP_TS_OFF = (0.09, 0.00)                  # courtyard centre from the anchor
OP_TS_BODY_D = 15.0                       # Ø behind the panel (as ts_jack had it)
OP_TS_AXIS_H = 9.5                        # ⚠ THE ONE FIGURE NOT OFF A FOOTPRINT:
                                          # how high the bore sits above the board.
                                          # It sets the panel hole's Z and nothing
                                          # else checks it. Confirm against
                                          # Neutrik's drawing before cutting metal.
# The small parts, generated from the routed board (scratch gen_bom.py) rather
# than typed -- XY is the KiCad courtyard about the pad centroid, which is the
# conservative envelope, and only the HEIGHT column is hand-entered.
OP_BOM = (
    ("C1",  "2.2uF/100V",    4.69,  3.29, 1.80,   13.00,   8.00),
    ("C10", "100nF",         1.91,  1.01, 0.55,   14.50,  -8.00),
    ("C11", "100nF",         1.91,  1.01, 0.55,    6.00, -12.00),
    ("C12", "100nF",         1.91,  1.01, 0.55,  -17.00,  -4.00),
    ("C13", "100nF",         1.91,  1.01, 0.55,   -4.00,  22.50),
    ("C14", "100nF",         1.91,  1.01, 0.55,   -3.50,  21.00),
    ("C15", "12pF",          1.91,  1.01, 0.55,  -11.00, -15.00),
    ("C16", "12pF",          1.91,  1.01, 0.55,   -1.00, -15.00),
    ("C17", "12pF",          1.91,  1.01, 0.55,  -21.50, -17.50),
    ("C18", "12pF",          1.91,  1.01, 0.55,  -12.50, -17.50),
    ("C2",  "10uF/50V",      4.69,  2.39, 1.60,  -20.00, -28.00),
    ("C3",  "100nF",         1.91,  1.01, 0.55,  -25.00, -28.00),
    ("C4",  "10nF",          1.91,  1.01, 0.55,  -19.00, -23.50),
    ("C5",  "22uF/16V",      3.49,  2.05, 1.45,    9.00, -23.50),
    ("C6",  "22uF/16V",      3.49,  2.05, 1.45,   13.00, -23.50),
    ("C7",  "10uF",          3.49,  2.05, 1.45,    4.00,   4.00),
    ("C8",  "100nF",         1.91,  1.01, 0.55,    7.50,   4.00),
    ("C9",  "10uF",          3.49,  2.05, 1.45,   11.00,  -8.00),
    ("D1",  "B5819W",        4.79,  2.39, 1.10,  -24.00, -23.50),
    ("D2",  "ESD",           2.59,  1.49, 0.75,   24.00,  -2.50),
    ("D3",  "ESD",           2.59,  1.49, 0.75,   24.00,  -4.50),
    ("D4",  "flyback",       2.59,  1.49, 0.75,    0.00,  15.00),
    ("D5",  "bidir clamp",   2.59,  1.49, 0.75,   17.50,   8.00),
    ("D6",  "SMAJ30A",       7.09,  3.59, 2.20,  -12.00, -28.00),
    ("FB1", "600R@100MHz",   3.05,  1.55, 0.95,   17.00, -23.50),
    ("K1",  "FRT5 5V",      13.15, 14.81, 5.10,  -13.00,  15.00),
    ("L1",  "47uH",          3.69,  3.69, 1.50,  -30.00, -23.50),
    ("Q1",  "AO3400A",       3.95,  3.49, 1.30,   -3.69,  15.00),
    ("R1",  "5k1",           1.95,  1.03, 0.50,   24.00,   2.00),
    ("R10", "100k",          1.95,  1.03, 0.50,   21.00,   8.00),
    ("R11", "preset",        1.95,  1.03, 0.50,  -16.00, -23.50),
    ("R12", "preset",        1.95,  1.03, 0.50,  -16.00, -25.50),
    ("R2",  "5k1",           1.95,  1.03, 0.50,   24.00,   0.00),
    ("R3",  "5k1",           1.95,  1.03, 0.50,  -25.50, -18.00),
    ("R4",  "5k1",           1.95,  1.03, 0.50,  -25.50, -20.00),
    ("R5",  "100R",          1.95,  1.03, 0.50,   -4.00,  12.00),
    ("R6",  "10k",           1.95,  1.03, 0.50,   11.00, -12.00),
    ("R7",  "10k",           1.95,  1.03, 0.50,   14.00, -12.00),
    ("R8",  "1M",            1.95,  1.03, 0.50,   -4.50,  25.00),
    ("R9",  "220R",          1.95,  1.03, 0.50,    8.00,   8.00),
    ("U1",  "CH32V307WCU6",  9.29,  9.29, 0.90,   -6.00,  -8.00),
    ("U2",  "PCM1808PWR",    7.79,  5.59, 1.20,    2.50,  29.00),
    ("U3",  "PCM5102A",      7.79,  7.09, 1.20,    2.50,  21.00),
    ("U4",  "HS USB hub",    5.35,  5.35, 0.80,  -17.00,  -8.00),
    ("U5",  "LMR16006",      4.19,  3.49, 1.10,  -30.00, -28.00),
    ("U6",  "3V3 LDO",       4.19,  3.49, 1.45,    6.23,  -8.00),
    ("U7",  "RRO op-amp",    4.19,  3.49, 1.45,    4.23,   8.00),
    ("U8",  "RRO op-amp",    4.19,  3.49, 1.45,   -3.77,  29.00),
    ("Y1",  "8MHz",          4.29,  3.59, 0.90,   -6.00, -15.00),
    ("Y2",  "12MHz",         4.29,  3.59, 0.90,  -17.00, -17.50),
)


def output_panel_pcb() -> cq.Workplane:
    """The output + panel board in its OWN frame: board centred on the origin in
    XY, underside at z=0, parts rising +Z, the panel connectors facing +X."""
    b = box_at(OP_BOARD_X, OP_BOARD_Y, _PCB_T, x=0.0, y=0.0, z=_PCB_T / 2)
    for ref, (jx, jy, _rot) in OP_J.items():
        l, w, h, (ox, oy) = OP_BOX[ref]
        b = b.union(box_at(l, w, h, x=jx + ox, y=jy + oy, z=_PCB_T + h / 2))
    # the 1/4 in jack: a real cylinder, because its BORE is what the endplate hole
    # has to line up with and a box would hide that
    jx, jy = OP_TS_XY
    zc = _PCB_T + OP_TS_AXIS_H
    b = b.union(box_at(OP_TS_L, OP_TS_W, OP_TS_AXIS_H, x=jx + OP_TS_OFF[0],
                       y=jy + OP_TS_OFF[1], z=_PCB_T + OP_TS_AXIS_H / 2))
    b = b.union(cyl_x(OP_TS_BODY_D, OP_TS_L, jx + OP_TS_OFF[0] - OP_TS_L / 2, jy, zc))
    for _n, _v, _w, _l, _h, _x, _y in OP_BOM:
        b = b.union(box_at(_w, _l, _h, x=_x, y=_y, z=_PCB_T + _h / 2))
    return b


# The panel holes bridge_endplate cuts. DERIVED, not typed: they follow the board.
DC_Y = TS_Y - OP_TS_XY[1] + OP_J["J6"][1]        # the barrel inlet is J6 now
USB_Y = TS_Y - OP_TS_XY[1] + OP_J["J1"][1]


def output_panel() -> cq.Workplane:
    """The output + panel board posed at the bridge endplate: flat, panel
    connectors out through the wall at +X.

    Z is set from the TS JACK'S BORE, not from the board: the jack is the part
    whose hole a player has to hit with a plug, so it owns the panel row's height
    and the board hangs wherever that puts it. Y is set so the jack lands on the
    existing TS_Y; the USB-C then falls 31.27 further -Y, which is where the panel
    hole has to move to."""
    # X: the jack's courtyard reaches 25.91 of a 26 half-board, so the BOARD EDGE is
    # the panel face to within 0.09 and is the honest thing to register against.
    b = output_panel_pcb().translate(
        (JACK_TIP - OP_BOARD_X / 2, TS_Y - OP_TS_XY[1],
         JACK_Z - _PCB_T - OP_TS_AXIS_H))
    return b.translate((JACK_FACE_DX, 0, 0))     # ride the panel's +X face


def op_pt(ref: str):
    """World (x, y, z) where a lead leaves the output+panel board's connector `ref`
    -- so wiring.py asks the board rather than carrying a copy of its layout, the
    same contract mctrl_pt provides for the motor controller.

    J2, J3 and J4 all exit along the board's -X, out of the mouths that face the
    instrument; J7 and J8 exit +Y and -Y respectively. J1 and J6 are panel parts
    and have no internal lead at all -- a player's cable is what plugs into them.

    ⚠ IT RETURNS THE COURTYARD'S FAR FACE ALONG +Y FOR EVERY REF, which was right
    while every connector exited +Y and is now right for J7/J8 only. The -X three
    need their own exit vector before wiring.py routes a lead to one; until then
    this is honest for the connectors the harness actually uses.
    """
    cx = JACK_TIP - OP_BOARD_X / 2 + JACK_FACE_DX
    cy = TS_Y - OP_TS_XY[1]
    jx, jy, _rot = OP_J[ref]
    l, w, h, (ox, oy) = OP_BOX[ref]
    return (cx + jx, cy + jy + oy + w / 2, JACK_Z - OP_TS_AXIS_H + h / 2)


def usb_panel_y() -> float:
    """Where the panel's USB-C hole now sits, for whoever cuts the endplate."""
    return TS_Y - OP_TS_XY[1] + OP_J["J1"][1]


# ── MOTOR CONTROLLER PCB ─────────────────────────────────────────────────────
# ONE per instrument, and it REPLACES THREE THINGS: the Teensy 4.1, its SGTL5000
# audio shield and the teensy_ifc carrier. The Teensy's value was the Audio
# Library, USB high-speed and the codec, all irrelevant once no audio touches
# this board (user: audio goes to the Pi; this board reads angles off bus B,
# applies the saved travel offsets and commands the SERVO42Ds on bus A). What
# could NOT be deleted is the pair of CAN TRANSCEIVERS -- no general-purpose MCU
# integrates one -- so the board was always going to exist; the only question was
# whether an MCU sat on it too. It now does, which is what deletes the jumper
# harness that used to run from the Teensy stack to the carrier.
#
# ⚠ THE OUTLINE IS AN OUTPUT, like the TRRS adapter and unlike every purchased
# board here: 46 x 58 is what elec/motor_ctrl.py's own contents came to, and the
# TRAY was re-laid-out around it (see MCTRL_FP). It is UNROTATED -- see MCTRL_ROT.
# (Said "40 x 35 ... stands 90 deg to the tray's X" until 2026-09-19, directly above
# a constant reading 46.0, 58.0. A number in prose beside the number it describes is
# the one place nothing checks; BOM.md carried the same stale 40 x 35 for this board
# and sized an enclosure row from it.)
MCTRL_BOARD_X, MCTRL_BOARD_Y = 46.0, 58.0
MCTRL_ROT = 0.0                  # UNROTATED now: at 46 x 58 the board fits
                                 # the tray straight, and the ADC slot it grows
                                 # into is free (that board is deleted).
# Pad-row centres, board-local, straight out of elec/motor_ctrl.py's placements.
MCTRL_J = {"J1": (-10.0, 2.5, 0.0),      # bus A out -- the ten motor tees
           "J2": (4.0, 2.5, 0.0),        # bus B out -- the eight lever boards
           "J3": (15.5, -8.5, 90.0),     # 24 V in, +X edge
           "J4": (0.0, -20.5, 0.0),      # USB-C to the Pi, -Y edge
           "J5": (0.0, 26.0, 0.0)}       # 5 V to the Pi's GPIO (was the power board)
MCTRL_USB = (10.73, 9.51, 3.26, 0.0, -23.31)   # HRO TYPE-C-31-M-12: courtyard + height
# Every populated part except the four connectors, which are modelled properly
# (cadkit XH / the USB block above). (name, value, X, Y, height, x, y), board-local
# and GENERATED from the laid-out board -- XY is the KiCad COURTYARD about the pad
# centroid, so the envelope is the assembly clearance rather than the bare body,
# which is the right error for a clearance model. HEIGHT is the one hand-entered
# column: it is package-family typical (the same figures knee_lever.SENSOR_BOM
# carries), not a footprint output, and it is the number to distrust.
MCTRL_BOM = (
    ("C1",   "4.7uF/50V",         4.69,  2.39, 1.60,  -16.50, -15.00),
    ("C2",   "10uF/16V",          3.49,  2.05, 1.45,  -16.00, -18.00),
    ("C3",   "100nF",             1.91,  1.01, 0.55,  -12.50, -15.00),
    ("C4",   "12pF",              1.91,  1.01, 0.55,   -8.00, -16.50),
    ("C5",   "12pF",              1.91,  1.01, 0.55,    0.00, -16.50),
    ("C6",   "100nF",             1.91,  1.01, 0.55,  -11.00,  -9.50),
    ("C7",   "100nF",             1.91,  1.01, 0.55,  -11.00,  -6.50),
    ("C8",   "100nF",             1.91,  1.01, 0.55,  -11.00,  -5.00),
    ("C9",   "100nF",             1.91,  1.01, 0.55,   -8.60,  -3.00),
    ("C10",  "100nF",             1.91,  1.01, 0.55,   -6.60,  -3.00),
    ("C11",  "100nF",             1.91,  1.01, 0.55,   -4.60,  -3.00),
    ("C12",  "100nF",             1.91,  1.01, 0.55,   -2.60,  -3.00),
    ("C13",  "100nF",             1.91,  1.01, 0.55,   -0.60,  -3.00),
    ("C14",  "100nF",             1.91,  1.01, 0.55,    1.40,  -3.00),
    ("C15",  "10uF",              3.49,  2.05, 1.45,   -8.00, -19.00),
    ("C16",  "10uF/50V",          4.69,  2.39, 1.60,  -12.00,  13.00),
    ("C17",  "10uF/50V",          4.69,  2.39, 1.60,   -6.00,  13.00),
    ("C18",  "100nF",             1.91,  1.01, 0.55,   -1.50,  13.00),
    ("C19",  "1uF",               1.91,  1.01, 0.55,  -17.00,   9.00),
    ("C20",  "100nF",             1.91,  1.01, 0.55,  -13.00,   9.00),
    ("C21",  "22uF/16V",          3.49,  2.05, 1.45,    9.00,  18.50),
    ("C22",  "22uF/16V",          3.49,  2.05, 1.45,   13.50,  18.50),
    ("D1",   "B5819W",            4.79,  2.39, 1.10,  -16.00, -11.50),
    ("D2",   "SMF24CA",           2.59,  1.49, 0.75,   12.30,   1.00),
    ("D3",   "SMF24CA",           2.59,  1.49, 0.75,   15.30,   1.00),
    ("D4",   "SMF24CA",           2.59,  1.49, 0.75,   10.00, -17.00),
    ("D5",   "SMF24CA",           2.59,  1.49, 0.75,   13.00, -17.00),
    ("D6",   "ESD",               2.59,  1.49, 0.75,    7.00, -24.00),
    ("D7",   "ESD",               2.59,  1.49, 0.75,   10.00, -24.00),
    ("D8",   "SMAJ30A",           7.09,  3.59, 2.20,    5.00,  13.00),
    ("D9",   "SMBJ5.0A",          7.39,  4.59, 2.30,    2.00,  18.50),
    ("F1",   "1A",                4.65,  2.35, 1.10,  -18.00,  13.00),
    ("F2",   "4A",                4.65,  2.35, 1.10,   13.00,  13.00),
    ("JP1",  "TERM",              3.39,  2.59, 0.05,   16.50, -17.50),
    ("JP2",  "TERM",              3.39,  2.59, 0.05,   16.50, -24.50),
    ("L1",   "47uH",              3.69,  3.69, 1.50,  -16.00,  -8.00),
    ("L2",   "6.8uH",             6.69,  6.29, 2.80,   -7.00,  18.50),
    ("R1",   "100k",              1.95,  1.03, 0.50,  -12.50, -17.50),
    ("R2",   "30k1",              1.95,  1.03, 0.50,  -12.50, -19.00),
    ("R3",   "10k",               1.95,  1.03, 0.50,   11.20,  -5.00),
    ("R4",   "10k",               1.95,  1.03, 0.50,   11.20, -11.50),
    ("R5",   "120R",              3.05,  1.55, 0.55,   16.50,   3.50),
    ("R6",   "120R",              3.05,  1.55, 0.55,   16.50, -21.00),
    ("R7",   "10k",               1.95,  1.03, 0.50,  -11.00, -11.00),
    ("R8",   "5k1",               1.95,  1.03, 0.50,   -7.00, -24.00),
    ("R9",   "5k1",               1.95,  1.03, 0.50,  -10.00, -24.00),
    ("R10",  "100k",              1.95,  1.03, 0.50,   -9.00,   9.00),
    ("R11",  "preset",            1.95,  1.03, 0.50,   -5.00,   9.00),
    ("R12",  "preset",            1.95,  1.03, 0.50,   -1.00,   9.00),
    ("R13",  "preset",            1.95,  1.03, 0.50,    3.00,   9.00),
    ("U1",   "LMR16006XDDCR",     4.19,  3.49, 1.10,  -16.00,  -3.50),
    ("U2",   "SN65HVD230DR",      7.49,  5.49, 1.75,    6.30,  -5.00),
    ("U3",   "SN65HVD230DR",      7.49,  5.49, 1.75,    6.30, -11.50),
    ("U4",   "CH32V307WCU6",      9.29,  9.29, 0.90,   -4.00,  -9.50),
    ("U5",   "LMR33630ADDAR",     7.49,  5.49, 1.75,  -16.00,  18.50),
    ("Y1",   "8MHz",              4.29,  3.59, 0.90,   -4.00, -16.50),
)


def motor_ctrl_pcb(mating: bool = False) -> cq.Workplane:
    """The motor controller, in its OWN frame: board centred on the origin in XY
    with its underside at z=0 and every part rising +Z (single-sided, one
    assembly setup). `mating=True` swaps the bare XH headers for their mated
    envelope, which is the volume a housing has to leave alone.

    The three XH headers take cadkit's dummy with `flip=True`: the B4B-XH-A
    footprint puts the body on the -Y side of its pin row, and the connector is
    not symmetric about its pins, so which side the body falls on is a real
    choice at layout rather than a cosmetic one."""
    b = box_at(MCTRL_BOARD_X, MCTRL_BOARD_Y, _PCB_T, x=0.0, y=0.0, z=_PCB_T / 2)
    for ref, (jx, jy, rot) in MCTRL_J.items():
        if ref == "J4":
            w, l, h, ox, oy = MCTRL_USB
            b = b.union(box_at(w, l, h, x=ox, y=oy, z=_PCB_T + h / 2))
            continue
        p = jst_xh_header(4, mated=mating, flip=True)
        if rot:
            p = p.rotate((0, 0, 0), (0, 0, 1), rot)
        b = b.union(p.translate((jx, jy, _PCB_T)))
    for _n, _v, _w, _l, _h, _x, _y in MCTRL_BOM:
        b = b.union(box_at(_w, _l, _h, x=_x, y=_y, z=_PCB_T + _h / 2))
    return b


def mctrl_pt(ref: str):
    """Tray FLAT-frame (x, y, z) where a lead leaves the motor controller's
    connector `ref` -- so wiring.py asks the board where its connectors are
    instead of carrying a copy of the layout. The three XH leads exit +Z off
    the top of a mated plug; the USB-C lead exits the mouth horizontally, which
    the board's 90 deg turn in the tray points at +X.

    The board-local -> tray mapping IS the MCTRL_ROT turn: board +X -> tray +Y,
    board +Y -> tray -X."""
    cx, cy = _ctr(MCTRL_FP)

    def to_tray(bx, by):
        """board-local -> tray, HONOURING MCTRL_ROT. This used to hardcode the 90 deg
        turn; the board is unrotated at 46 x 58, and a hardcoded mapping would have put
        every connector on the wrong edge with nothing to catch it."""
        if abs(MCTRL_ROT - 90.0) < 1e-6:
            return (cx - by, cy + bx)
        return (cx + bx, cy + by)

    if ref == "J4":
        _w, l, h, ox, oy = MCTRL_USB
        x, y = to_tray(ox, oy - l / 2.0)
        return (x, y, BOARD_Z + BD_T + h / 2.0)
    bx, by, _rot = MCTRL_J[ref]
    x, y = to_tray(bx, by)
    return (x, y, BOARD_Z + BD_T + 9.8)


def motor_ctrl() -> cq.Workplane:
    """The motor controller posed in the standing tray (see MCTRL_FP)."""
    cx, cy = _ctr(MCTRL_FP)
    b = (motor_ctrl_pcb(mating=True)
         .rotate((0, 0, 0), (0, 0, 1), MCTRL_ROT)
         .translate((cx, cy, BOARD_Z)))
    return stand(b)


# floor plane (bed top) — tee PCBs and the trunk-and-drop harness live here.
# = the LIVE chassis print-bed datum. Was a spelled-out -75.15, which had gone
# STALE: SCREW_TOP_Z, SCREW_PULLEY_Z and XBAR each moved onto the bead grid and
# the copy silently ended 0.2 below the real bed (-74.95). The off-grid audit is
# what caught it — a derived value that can't land on the grid means a parent
# moved without it.
FLOOR_Z = CH.Z_BOT


# ── CAN bus TEE PCB ──────────────────────────────────────────────────────────
# The SERVO42D has a SINGLE 6-pin XH (power+CAN); a single-port device can't be
# daisy-chained without soldering, so each node needs a 3-way junction -- this tee:
# TRUNK-IN + DROP + TRUNK-OUT + a switchable 120R terminator. Connectors are the
# real cadkit JST-XH: TOP-ENTRY (B4B-XH-A), cables rising +Z into the corridor
# harness, so the board packs compactly (the 15 mm SIDE-entry parts used on the
# knee lever would need a ~45 mm board -- infeasible at the 32 mm tee pitch). All
# three are 4-pin: a single-motor DROP needs only the 4 CAN conductors (gnd/24V/
# H/L), so the SERVO42D's 6-pin pigtail lands its 4 relevant wires here. Single-
# sided placement (all bodies on top); the THT posts drop 3.4 through the board
# and are cleared by a relief WINDOW in the cradle base (see wiring.tee_cradles).
TEE_CONN_N   = 4                                     # CAN = 4 conductors (gnd/24V/H/L)
# RESHAPED for the motor seats (bronner, 2026-09-14). It was 22 x 24 with three 4-way XH
# rotated 90 deg, which put a 16 x 11 band of 3.4-deep THT tails across the board's MIDDLE --
# unusable on a motor, where the only support is the faceplate wall's 6.4 strip and everything
# else overhangs the motor it has to lap. Now: ONE 8-way trunk (in on 1-4, out on 5-8) plus its
# own 4-way motor drop, pin rows COLLINEAR along X in a band at the +Y edge, so the tails land
# on the wall and the rest of the board laps the motor. Pulling the 4-way swaps a motor without
# disturbing the trunk -- which is what the tee is for.
TEE_BOARD_X  = D.TEE_BOARD_X                         # one row of 8-way + 4-way
TEE_BOARD_Y  = D.TEE_BOARD_Y                         # shallow: it sits ON the motor, not on the rail
TEE_YSHIFT   = 5.0                                   # board centre shift +Y so the -Y edge stays at y-7
TEE_TRUNK_N  = 8                                     # trunk in (1-4) / out (5-8) on ONE housing
# SIDE ENTRY (bronner, 2026-09-14): S8B-XH-A / S4B-XH-A, mouth facing -Y so the plugs run out
# OVER the motor instead of up. It stands 7.0 off the board where the top-entry pair stood 9.8
# mated -- and that 2.8 is what lets string 10's tee sit on its motor at all: the magnetic
# pickup's neck-most position dips to z -18.2 right over it. So the bank has no exception left.
TEE_CONN_CY  = 2.0                                   # PAD ROW: 6.0 in from the +Y edge, over the wall
TEE_MOUTH_DY = 3.25                                  # pad row -> mouth face (body 6.1, pads 2.85 off its back)
TEE_RELIEF   = (38.0, 3.0)                           # base tail-relief window (w × l), board-local, at (0, CONN_CY)


def tee_board_cy(y: float) -> float:
    """Board (and cradle) centre Y for a tee at station y: the -Y edge stays at y-7
    (clear of the -Y rail, as before); the board grows +Y into the open corridor."""
    return y + TEE_YSHIFT


def tee_pcb(x: float, y: float, drop: int = 1, accurate: bool = True) -> cq.Workplane:
    """CAN bus TEE PCB dummy, flat on the chassis floor. THREE 4-pin TOP-ENTRY XH
    (B4B-XH-A; cadkit jst_xh_header, drawn MATED) -- trunk-in / drop / trunk-out,
    L-to-R, cables up -- plus the 120 Ω-behind-jumper terminator (closed only on
    each bus's LAST tee). Serves the 10 bus-A motor tees on the open -Y rail. `drop`
    = ±1 marks the device side (cables are top-entry, so it doesn't change the board
    geometry). Mount: ONE M4 THROUGH the bare ear off its +X end (wiring.tee_hold). `accurate=False` -> the compact bus-B
    placeholder (see _tee_pcb_placeholder)."""
    if not accurate:
        return _tee_pcb_placeholder(x, y, drop)
    top = FLOOR_Z + 1.6                              # board top face; connectors rise +Z from here
    cy = tee_board_cy(y)
    # `x` is the OUTLINE centre. Bronner's 40 mm layout region is the -X part of it; off its
    # +X end is a bare EAR, D.TEE_EAR_X by D.TEE_EAR_Y at the +Y corner, with the retaining M4's
    # clearance hole through it. An L, not a rectangle -- see D.TEE_EAR_Y.
    xl = x - D.TEE_EAR_X / 2                         # the layout region's own centre
    ey = cy + (TEE_BOARD_Y - D.TEE_EAR_Y) / 2        # the ear's own centre Y
    b = box_at(TEE_BOARD_X, TEE_BOARD_Y, 1.6, x=xl, y=cy, z=FLOOR_Z + 0.8)
    b = b.union(box_at(D.TEE_EAR_X, D.TEE_EAR_Y, 1.6,
                       x=x + TEE_BOARD_X / 2, y=ey, z=FLOOR_Z + 0.8))
    b = b.cut(cq.Workplane(obj=cq.Solid.makeCylinder(
        2.25, 3.6, cq.Vector(x + TEE_BOARD_X / 2, ey, FLOOR_Z - 1.0))))   # M4 clearance
    # ONE row along X: the 8-way trunk, then the 4-way drop beside it. Pin rows collinear, so
    # the tail band is ~1.5 deep instead of 7.5 and clears the faceplate wall's strip.
    l8, l4 = xh_side_length(TEE_TRUNK_N, smt=False), xh_side_length(TEE_CONN_N, smt=False)
    run = l8 + l4
    for n, dx in ((TEE_TRUNK_N, -run / 2 + l8 / 2), (TEE_CONN_N, run / 2 - l4 / 2)):
        b = b.union(jst_xh_side_header(n, smt=False, mated=True)
                    .translate((xl + dx, cy + TEE_CONN_CY - TEE_MOUTH_DY, top)))
    b = b.union(box_at(3.5, 2.0, 1.8, x=xl - run / 2 - 1.5, y=cy - 4.0, z=top + 0.9))  # 120R + jumper
    return b


# (THE TRRS <-> JST-XH ADAPTER PCB IS DELETED, 2026-09-16, user. It existed to put the
#  leg-link TRRS jack on a board so the joint could be crossed without crimping a
#  factory-cabled part -- and the leg column has since become an off-the-shelf TRRS
#  M->F extension cable with molded ends, which crosses the same joint with ZERO
#  connections on the leg. The board was solving a problem the cable stopped having.
#
#  Nothing referenced trrs_adapter_pcb: it was modelled, dimensioned against the real
#  PJ-320D-4A and B4B-XH-A courtyards, given an M4 through-hole for retention, and never
#  placed in an assembly. Worth noting, because a part with no caller is exactly the kind
#  that survives a design change unnoticed.
#
#  The leg's own TRRS geometry is NOT this and stays: see TRRS_DX/TRRS_DY and
#  leg_shaft_trrs in legs.py, which seat the naked 10-03404 jack and the extension
#  cable's molded barrel. Same four wires, different problem.)


# (ts_jack is DELETED: the 1/4 in jack is a PCB part on the output+panel board
#  now -- see OP_TS_XY. Modelling it as a free-floating panel jack implied
#  hand-soldered lugs, which the project forbids.)


# (dc_jack is DELETED: the 24 V inlet is a PCB part on the output+panel board now
#  -- see OP_J["J6"]; this said J5 until 2026-09-18, and OP_J has no J5 key at
#  all, because the 1/4 in jack is modelled as a cylinder rather than a box.
#  As a free-standing panel jack it was a PJ-005A, whose SOLDER
#  LUGS carried the same hand-soldering violation the TS jack did.)
