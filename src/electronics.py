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
# below. AFE board footprint (the analog front end on the bridge rib):
# DERIVED from the bridge axle, not hardcoded. The endplate's inboard wall follows
# BRIDGE_AXLE_X (= BRIDGE_X - OD/2, because the string rides the OD and has to leave
# at x = 0), so when the bearing grew Ø8 -> Ø13 the axle stepped 2.5 -X and the wall
# came with it — straight through this board's +X edge, which sat at a constant.
AFE_X1 = D.BRIDGE_AXLE_X + 2.0         # tuck 2.0 clear of the axle line
AFE_X0 = AFE_X1 - 20.0                 # 20 long
AFE_Y0, AFE_Y1 = -108.0, -78.0         # inboard of the pickup groove + leg barrel
AFE_Z = -59.0                          # board bottom (on the bridge-rib boss)
AFE_PED_TOP = -61.0                    # boss top (posts rise to the board)

# NOTE: this block sits ABOVE the chassis import ON PURPOSE. chassis builds at
# import time and reaches BACK here for TAB_X0/TAB_X1/CH_W/CH_D/TRAY_Z0 to cut its
# matching channels. With the constants below the import, that reach-back hit a
# half-initialised module and `import src.electronics` failed outright with a
# circular-import ImportError -- only working at all because everything else
# happened to import chassis first. These are plain literals, so hoisting them is
# free and makes the module importable on its own.
# ---- bay geometry (chassis.py cuts the matching channels from these) ----
TRAY_X0, TRAY_X1 = -607.0, -547.0
TRAY_Y0, TRAY_Y1 = -127.5, 53.5        # 1.25 off each rail inner face
TRAY_Z0, TRAY_Z1 = -64.0, -61.0        # plate band (3 thick) - 1.15 ABOVE the
                                       # x -575 rib top so the bay rib passes
                                       # under the tray
TAB_X0, TAB_X1 = -572.0, -552.0        # one tab per side, in the only solid
                                       # web window between the leg dovetail
                                       # slot (ends -582) and the rail web
                                       # diamonds (start -560)
TAB_T = 2.7                            # into a 3-deep channel (0.3 floor gap)
CH_W, CH_D = 20.6, 3.0                 # channel cut: width / depth into web


from . import chassis as CH          # only early constants (X_*, Z_*) used here
from .helpers import box_at, cyl
from cadkit.fasteners import M2, cut_anchor
from cadkit.pcb import jst_xh_header

# ---- board footprints (x0, x1, y0, y1); board bottom z = TRAY_Z1 + post ----
POST_H = 3.0
BD_T = 1.6
PI_FP     = (-603.0, -547.0, -50.0, 35.0)     # Pi 5: 56 x 85 (long side on Y);
                                       # slid 19 SOUTH (FLUSH round): the wired
                                       # leg's jack chimney + cable drop own the
                                       # tray's west-north corner (x > -603 must
                                       # stay clear of y > 35 there; east is
                                       # walled by motor 0)
TEENSY_FP = (-607.0, -589.0, -118.0, -57.0)    # Teensy 4.1 + shield stack
ADC_FP     = (-585.0, -547.0, -90.0, -55.0)   # multichannel TDM ADC, stacked
BUCK_FP   = (-585.0, -549.0, -118.0, -95.0)   # buck module, 20 x 40
XCVR_FP   = (-570.0, -552.0, 39.0, 52.0)      # teensy_ifc (CAN transceivers):
                                       # moved to the tray's NORTH strip east of
                                       # the wired leg's jack chimney (FLUSH
                                       # round) - pi5 slid south into its old
                                       # -X-corner spot

BOARD_Z = TRAY_Z1 + POST_H             # every bottom board sits at -67

# ---- panel jacks (through the endplate recess wall, kept 4 mm thick) ----
# The real connectors are deep (TS ~22 mm, DC ~15.5 mm). Behind the endplate
# the corner is open in X for ~100 mm (out to motor 0 at x -89) EXCEPT the low
# bridge cross-rib (tops at z -65). So the jacks ride HIGH (z -41), clear above
# the rib and above the bottom-mounted AFE board - their bodies then reach
# freely into the open bay.
# The +X face is now the centred 25 mm bridge's tip (BRIDGE_AXLE_X + 25/2 = 8.5), NOT
# X_BRIDGE+WALL -- the block is centred on the axle, not pinned to the rail end. Keep a
# 4 mm panel at that tip and slide the connectors (authored with their panel face at
# x~14) by JACK_FACE_DX so they ride the tip wherever it lands.
JACK_TIP = D.BRIDGE_AXLE_X + CH.KH_EP_THK / 2        # bridge +X face = centred 25 mm block (8.5)
JACK_WALL_X = JACK_TIP - 4.0                          # inner face of the 4 mm panel (4.5)
JACK_FACE_DX = JACK_TIP - 14.0                        # authored face sits at x~14; ride the +X tip
JACK_Z = -41.0
TS_Y, DC_Y, USB_Y = -68.0, -86.0, -104.0

# ---- UI: OLED + joystick on the top deck (mounted to the top plate) ----
# Centred along X. NOTE: the strings cover the deck within +-42.75 with only
# ~2 mm clearance, and the +Y/string-10 edge is just ~12 mm wide before the
# rail - too narrow for the 38 mm screen. So the UI sits on the WIDE -Y deck
# band (86 mm, over the motor PCBs, clear of the strings). The joystick (Alps
# RKJXT1F42001: 2-way rotary + 4-way + push) is the sole control.
UI_X      = (CH.X_BRIDGE + CH.X_NUT) / 2     # instrument X centre
DECK_TOP  = D.STRING_Z - 10.0                 # deck surface 10 mm under the
                                              # strings (bar can press strings
                                              # down without bottoming out) = +6
OLED_Y    = -100.0                            # wide -Y deck band (clear of strings)
OLED_W, OLED_L, OLED_T = 38.0, 72.0, 1.6      # 2.42" module PCB (Y x X)
JOY_X     = UI_X + 56.0                       # just +X of the screen
JOY_Y     = -82.0


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


def analog_frontend() -> cq.Workplane:
    """Bridge-end analog board dummy: relay (chunkiest), buffer/LDO/driver
    bumps. Mounted on the chassis -Y-corner pedestal."""
    bz = AFE_Z
    b = box_at(AFE_X1 - AFE_X0, AFE_Y1 - AFE_Y0, BD_T,
               x=(AFE_X0 + AFE_X1) / 2, y=(AFE_Y0 + AFE_Y1) / 2, z=bz + BD_T / 2)
    # relay (chunkiest, toward the east edge near the jacks)
    b = b.union(box_at(10.0, 7.5, 6.0, x=AFE_X1 - 7, y=AFE_Y1 - 8, z=bz + BD_T + 3.0))
    for px, py in ((AFE_X0 + 6, AFE_Y0 + 6), (AFE_X0 + 6, AFE_Y1 - 6),
                   (AFE_X1 - 6, AFE_Y0 + 6)):
        b = b.union(box_at(4.0, 4.0, 2.5, x=px, y=py, z=bz + BD_T + 1.25))
    return b


def _screw_xy(fp, corner):
    """One board corner (5 mm inset, at a real corner mounting-hole position)."""
    x0, x1, y0, y1 = fp
    return (x0 + 5 if corner[0] < 0 else x1 - 5,
            y0 + 5 if corner[1] < 0 else y1 - 5)


def _posts_strips_screw(fp, bz, corner):
    """Drop-in, SCREW-RETAINED mount for one board footprint (no snap/flexure --
    a deliberate rule; plastic snaps aren't trusted). 4 corner support posts
    (tops flush with the board bottom -- the board RESTS on them), 2 locator
    strips along the x edges (0.3 plan fit) that locate the board in the pocket,
    and ONE fat boss at `corner` carrying an M2 anchor: the board drops into the
    strip-located pocket and a single screw through its corner mounting hole
    stops lift-out. The anchor itself is cut in electronics_tray() (after the
    boss fuses into the tray plate, so the self-tap runs full depth)."""
    x0, x1, y0, y1 = fp
    sx, sy = _screw_xy(fp, corner)
    out = cq.Workplane("XY")
    for px in (x0 + 5, x1 - 5):
        for py in (y0 + 5, y1 - 5):
            is_screw = abs(px - sx) < 1e-6 and abs(py - sy) < 1e-6
            out = out.add(cyl(7.0 if is_screw else 5.0, bz - TRAY_Z1, z=TRAY_Z1)
                          .translate((px, py, 0)))
    for sy2 in (y0 - 1.0, y1 + 1.0):    # strips: 0.3 plan gap to the board
        out = out.add(box_at(x1 - x0 - 16.0, 1.4, bz + 1.0 - TRAY_Z1,
                             x=(x0 + x1) / 2, y=sy2,
                             z=(TRAY_Z1 + bz + 1.0) / 2))
    return out


def electronics_tray() -> cq.Workplane:
    """The printed tray: plate + drop-in side tabs + all snap-mount sets.
    Prints flat (plate on the bed, posts/fingers up, no overhangs beyond
    the 45-degree nubs)."""
    body = box_at(TRAY_X1 - TRAY_X0, TRAY_Y1 - TRAY_Y0, TRAY_Z1 - TRAY_Z0,
                  x=(TRAY_X0 + TRAY_X1) / 2, y=(TRAY_Y0 + TRAY_Y1) / 2,
                  z=(TRAY_Z0 + TRAY_Z1) / 2)
    for ye, s in ((TRAY_Y0, -1), (TRAY_Y1, 1)):      # side tabs into channels
        body = body.union(box_at(TAB_X1 - TAB_X0, TAB_T + 1.25, 6.0,
                                 x=(TAB_X0 + TAB_X1) / 2,
                                 y=ye + s * (TAB_T + 1.25) / 2 - s * 0.001,
                                 z=TRAY_Z0 + 3.0))
    # each board: strip-located drop-in pocket + ONE M2 screw at a chosen corner
    # (a corner clear of the board's top-side components / neighbours).
    for fp, bz, corner in ((PI_FP, BOARD_Z, (-1, -1)),
                           (TEENSY_FP, BOARD_Z + 1.0, (-1, -1)),
                           (ADC_FP, BOARD_Z, (+1, -1)),
                           (BUCK_FP, BOARD_Z, (+1, +1)),
                           (XCVR_FP, BOARD_Z, (-1, -1))):
        body = body.union(_posts_strips_screw(fp, bz, corner))
        sx, sy = _screw_xy(fp, corner)
        body = cut_anchor(M2, body, (sx, sy, bz), (0, 0, -1), M2.anchor_min_wall)
    # NORTH-SHELF LANE CHANNEL (Y-INSTALL round; supersedes the old
    # west-north chimney bite - the jack chimney/fin is gone): the wired
    # leg's Ø3.8 factory pigtail rides the chassis' over-rib raceway east
    # at y 50.5 / z -65.0, passing under the tray's north rim shelf
    # (y 46.5..53.5, bottom -64.0) - channel its underside 1.7 deep so
    # the cable (top -63.1) clears by 0.7; the shelf keeps 1.4 above.
    body = body.cut(box_at(25.2, 9.9, 1.7, x=-595.6, y=48.45, z=-63.25))
    return body


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
    return b


def teensy_stack() -> cq.Workplane:
    """Teensy 4.1 + audio shield (stacked on headers), long axis on Y."""
    cx, cy = _ctr(TEENSY_FP)
    bz = BOARD_Z + 1.0
    b = _board(TEENSY_FP, bz)
    b = b.union(_board(TEENSY_FP, bz + 11.0))
    b = b.union(box_at(8.0, 8.0, 3.5, x=cx, y=TEENSY_FP[2] + 5.0,
                       z=bz + BD_T + 1.75))
    for hx in (TEENSY_FP[0] + 2.6, TEENSY_FP[1] - 2.6):
        b = b.union(box_at(2.4, TEENSY_FP[3] - TEENSY_FP[2] - 6, 11.0,
                           x=hx, y=cy, z=bz + BD_T + 5.5))
    return b


def adc_stack() -> cq.Workplane:
    """Multichannel TDM ADC carrier stack (the pro 10-ch analog front end) + header."""
    cx, cy = _ctr(ADC_FP)
    b = _board(ADC_FP, BOARD_Z)
    for px in range(3):
        b = b.union(box_at(9.0, 9.0, 1.3, x=ADC_FP[0] + 8 + px * 13,
                           y=cy, z=BOARD_Z + BD_T + 0.65))
    b = b.union(box_at(ADC_FP[1] - ADC_FP[0] - 8, 4.0, 7.0, x=cx, y=ADC_FP[2] + 3.0,
                       z=BOARD_Z + BD_T + 3.5))
    return b


def buck() -> cq.Workplane:
    """24V -> 5V buck module dummy (caps + inductor)."""
    cx, cy = _ctr(BUCK_FP)
    b = _board(BUCK_FP, BOARD_Z)
    for px in (BUCK_FP[0] + 8, BUCK_FP[1] - 8):
        b = b.union(cyl(7.0, 9.0, z=BOARD_Z + BD_T).translate((px, cy, 0)))
    b = b.union(box_at(12.0, 12.0, 7.0, x=cx, y=cy, z=BOARD_Z + BD_T + 3.5))
    return b


def teensy_ifc() -> cq.Workplane:
    """Teensy INTERFACE board (custom, rides the sensor-PCB panel): the
    wiring strategy's carrier for everything crimped — 2× MCP2562FD CAN
    transceivers (bus A motors / bus B inputs), one 120 Ω per bus behind
    shunt jumpers (bus A's closed here + at the last motor tee; bus B's
    closed at the last input tee instead), and THREE XH headers: bus A
    trunk, bus B trunk, and the crimped jumper to the Teensy stack. No
    wire ever solders to this board — every field connection is a
    housing."""
    cx, cy = _ctr(XCVR_FP)
    b = _board(XCVR_FP, BOARD_Z)
    for px in (cx - 4.5, cx + 4.5):                     # 2× MCP2562FD
        b = b.union(box_at(5.0, 4.0, 1.6, x=px, y=cy + 1.5,
                           z=BOARD_Z + BD_T + 0.8))
    for i, hy in enumerate((XCVR_FP[2] + 3.0, XCVR_FP[2] + 3.0, XCVR_FP[3] - 3.0)):
        hx = XCVR_FP[0] + 5.0 + (i % 2) * 8.0 if i < 2 else cx
        b = b.union(box_at(7.0, 4.0, 6.5, x=hx, y=hy,
                           z=BOARD_Z + BD_T + 3.25))    # XH headers (inboard
                                                        # of the tray snap nubs)
    return b


# floor plane (bed top) — tee PCBs and the trunk-and-drop harness live here
FLOOR_Z = -75.15


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
TEE_BOARD_X  = 22.0                                  # seats 3 top-entry XH side by side + hardware
TEE_BOARD_Y  = 24.0                                  # grows +Y off the rail into the open corridor
TEE_YSHIFT   = 5.0                                   # board centre shift +Y so the -Y edge stays at y-7
TEE_CONN_DX  = 6.5                                   # trunk-in / drop / trunk-out X spacing
TEE_CONN_CY  = -1.0                                  # connector row centre (board-local Y)
TEE_SCREW_XY = (0.0, 9.0)                            # cradle retention hole (top band, clear of connectors)
TEE_RELIEF   = (16.0, 11.0)                          # base tail-relief window (w × l), board-local, at (0, CONN_CY)


def tee_board_cy(y: float) -> float:
    """Board (and cradle) centre Y for a tee at station y: the -Y edge stays at y-7
    (clear of the -Y rail, as before); the board grows +Y into the open corridor."""
    return y + TEE_YSHIFT


def _tee_pcb_placeholder(x: float, y: float, drop: int = 1) -> cq.Workplane:
    """Compact SCHEMATIC tee (18×14, box connectors) for the two bus-B tees crammed
    into the keyhead bay: the accurate 22×24 board doesn't fit the 23 mm gap between
    the electronics tray and the bus-A tee there. The real fix is to fold the bus-B
    CAN tap onto the knee-lever / leg-carrier PCBs themselves (no separate tee) -- TODO."""
    b = box_at(18.0, 14.0, 1.6, x=x, y=y, z=FLOOR_Z + 0.8)
    for dx in (-5.5, 5.5):
        b = b.union(box_at(6.0, 8.0, 6.5, x=x + dx, y=y - drop * 2.0, z=FLOOR_Z + 1.6 + 3.25))
    b = b.union(box_at(7.0, 4.0, 6.5, x=x, y=y + drop * 4.5, z=FLOOR_Z + 1.6 + 3.25))
    b = b.union(box_at(3.5, 2.0, 1.8, x=x - 6.5, y=y + drop * 4.5, z=FLOOR_Z + 1.6 + 0.9))
    return b


def tee_pcb(x: float, y: float, drop: int = 1, accurate: bool = True) -> cq.Workplane:
    """CAN bus TEE PCB dummy, flat on the chassis floor. THREE 4-pin TOP-ENTRY XH
    (B4B-XH-A; cadkit jst_xh_header, drawn MATED) -- trunk-in / drop / trunk-out,
    L-to-R, cables up -- plus the 120 Ω-behind-jumper terminator (closed only on
    each bus's LAST tee). Serves the 10 bus-A motor tees on the open -Y rail. `drop`
    = ±1 marks the device side (cables are top-entry, so it doesn't change the board
    geometry). Mount: drop-in cradle + one M2. `accurate=False` -> the compact bus-B
    placeholder (see _tee_pcb_placeholder)."""
    if not accurate:
        return _tee_pcb_placeholder(x, y, drop)
    top = FLOOR_Z + 1.6                              # board top face; connectors rise +Z from here
    cy = tee_board_cy(y)
    b = box_at(TEE_BOARD_X, TEE_BOARD_Y, 1.6, x=x, y=cy, z=FLOOR_Z + 0.8)
    for dx in (-TEE_CONN_DX, 0.0, TEE_CONN_DX):      # trunk-in / drop / trunk-out (rows along Y)
        b = b.union(jst_xh_header(TEE_CONN_N, mated=True)
                    .rotate((0, 0, 0), (0, 0, 1), 90)
                    .translate((x + dx, cy + TEE_CONN_CY, top)))
    b = b.union(box_at(3.5, 2.0, 1.8, x=x - 8.0, y=cy + 9.0, z=top + 0.9))   # 120R + jumper
    return b


_AX = cq.Vector(1, 0, 0)                # plugs insert from +X (the panel face)


def _cyl_x(d, length, x, y, z) -> cq.Workplane:
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(
        d / 2, length, cq.Vector(x, y, z), _AX))


def ts_jack() -> cq.Workplane:
    """1/4-inch TS panel jack — Neutrik NMJ4HCD2 dims: Ø11.4 panel bushing,
    Ø~15 body ~22 mm deep BEHIND the panel, nut outside. Female socket bore
    Ø6.5 for the 6.35 mm plug."""
    b = _cyl_x(15.0, 22.0, -16.0, TS_Y, JACK_Z)            # deep body, behind cap
    b = b.union(_cyl_x(11.4, 8.05, 6.0, TS_Y, JACK_Z))     # bushing through cap
    b = b.union(_cyl_x(13.0, 2.0, 14.05, TS_Y, JACK_Z))    # nut, outside
    b = b.cut(_cyl_x(6.5, 33.0, -15.0, TS_Y, JACK_Z))      # female plug socket
    return b.translate((JACK_FACE_DX, 0, 0))               # ride the (thicker) +X face


def dc_jack() -> cq.Workplane:
    """DC barrel power inlet — Same Sky PJ-005A dims: Ø10.8 face, Ø5.7 thread,
    ~15.5 mm overall. Female Ø5.5 barrel bore with the Ø2.0 centre pin."""
    b = _cyl_x(10.8, 10.0, -4.0, DC_Y, JACK_Z)             # body behind the cap
    b = b.union(_cyl_x(5.7, 8.05, 6.0, DC_Y, JACK_Z))      # thread through cap
    b = b.union(_cyl_x(10.8, 2.0, 14.05, DC_Y, JACK_Z))    # front face, outside
    b = b.cut(_cyl_x(5.5, 22.0, -3.0, DC_Y, JACK_Z))       # female barrel bore
    b = b.union(_cyl_x(2.0, 17.0, -3.0, DC_Y, JACK_Z))     # centre pin
    return b.translate((JACK_FACE_DX, 0, 0))               # ride the (thicker) +X face


def usbc_jack() -> cq.Workplane:
    """Panel-mount USB-C module: body, flange, and the female receptacle - an
    8.34 x 2.56 mm racetrack opening with the centre tongue."""
    b = box_at(8.0, 22.0, 11.0, x=6.0, y=USB_Y, z=JACK_Z)
    b = b.union(box_at(4.1, 13.0, 6.6, x=12.0, y=USB_Y, z=JACK_Z))
    b = b.union(box_at(1.6, 21.0, 13.0, x=14.85, y=USB_Y, z=JACK_Z))
    # racetrack cavity (8.34 wide x 2.56 tall) + centre PCB tongue
    cav = box_at(7.0, 5.78, 2.56, x=12.5, y=USB_Y, z=JACK_Z)
    for dy in (-2.89, 2.89):
        cav = cav.union(_cyl_x(2.56, 7.0, 9.0, USB_Y + dy, JACK_Z))
    b = b.cut(cav)
    b = b.union(box_at(5.5, 6.7, 0.7, x=11.75, y=USB_Y, z=JACK_Z))
    return b.translate((JACK_FACE_DX, 0, 0))               # ride the (thicker) +X face
