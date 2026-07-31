"""OPTICAL per-string pickup -- a reflective IR strip that reads all 10 strings
individually, for pitch detection (calibration + audio->MIDI) and for per-string AUDIO.

WHY optical, not a second magnetic hex pickup: a Cycfi Nu Multi is ~$33/string and a
per-string magnetic coil bleeds into its neighbours at this pitch. Reflective IR has
ZERO magnetic crosstalk -- which matters more here than on a normal instrument,
because ten SERVO42D steppers with PWM current control live directly under the deck
and would inject straight into ten passive coils.

MOUNTING -- DOWN-FIRING, FROM THE BRIDGE ENDPLATE'S TIE BAR:
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
SENSE_X, and the tie bar is EXTENDED -X to reach it rather than crowding the bridge.

SENSING LAYOUT -- per string, THREE parts in a row across Y:
      [PD] --PD_DY-- [IR LED] --PD_DY-- [PD]
  The string sits under the emitter. Light goes down, reflects off the string, and
  returns to both photodiodes.
    * SUM of the pair tracks the string's Z (vertical) motion. This is the AUDIO
      signal -- a linear displacement signal; it is what goes out over USB.
    * DIFFERENCE tracks its Y (lateral) motion.
  BOTH are needed, and the reason is sharper than "more signal". With the detectors
  symmetric about the emitter, SUM is an EVEN function of lateral displacement and
  DIFF is ODD. So a purely vertical vibration puts a clean f0 in SUM; as the
  vibration plane PRECESSES toward horizontal -- which it does over the long sustain
  this instrument is built for -- SUM's f0 collapses and its 2f0 term takes over. A
  single-axis pickup there does not merely go quiet, it hands the detector a strong,
  coherent, WRONG answer an octave up, which no plausibility gate can coast through.
  DIFF is what keeps f0 observable through that rotation.
  The pair straddles Y, not X, because transverse string motion is in the Y-Z plane.

  NOT by magnitude. sqrt(SUM^2 + DIFF^2) is full-wave rectification for a flat orbit
  (2f0 again) and DC for a circular one -- wrong at both extremes. The pitch path
  takes the 2x2 covariance of (SUM, DIFF) over a short window and PROJECTS onto the
  dominant eigenvector: a clean single-axis f0 that follows the precession.

SIGNAL CHAIN. Each photodiode gets its OWN transimpedance amp and its OWN ADC input
-- 20 of each. SUM and DIFF are then one add and one subtract in firmware, which is
cheaper in parts than building analog sum AND difference stages, and it keeps the
high-impedance node to a single R/C at the op-amp.
  * AUDIO path: SUM at 48 kHz, 10 channels, straight out over USB. 960 kB/s.
  * PITCH path: decimated to ~6-8 kHz, then detection on-chip, MIDI out over the same
    cable. Pitch detection at 48 kHz would be wasted work -- the detector needs 2-3
    PERIODS, not samples -- so decimating is not a compromise, it is the right rate.
  The split is why both fit: the expensive stage is the only one not running at 48k.

SPECTRUM (worth knowing before judging the audio): near the termination the mode-shape
factor sin(n*pi*d/L) grows with n and cancels most of the displacement rolloff, so the
sensed spectrum of a plucked string is ~1/n -- sawtooth-like, NOT a near-sine. Darker
than a magnetic pickup at the same spot by ~6 dB/octave, but harmonically rich. Good
raw material for the per-string overdrive the user wants (per-string clipping never
intermodulates, and heavy clipping compresses away the precession warble).

BOARD ORGANISATION -- two blocks, and the split is electrical, not just packing:
  * ANALOG FIELD, the X band immediately +X of the sensor row: the 20 TIAs (5 quad
    op-amps, one per string PAIR, sat at that pair's centroid) and their feedback
    R/C. The TIA summing node is the noise-critical point on a board reading tens of
    nanoamps, so the amp belongs within a few mm of its photodiode.
  * DIGITAL BLOCK, in the -Y room past the last string: MCU, USB HS PHY, crystals,
    regulators, connector. Nothing switching sits beside the detector row.

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
# millimetre of bar cantilevered over the player.
# The cost is real and linear: 0.60x the signal of a 20 mm station. Revisit with the
# prototype's measured SNR margin, not by argument -- SENSE_D is the only edit needed,
# PCB_X1 and the endplate's TIE_X0 both derive from it.
# STEPPED, not uniform -- the row is two rows. Optical signal scales with the string's
# DIAMETER (the string IS the target: a wide beam is mostly missing it, and how much comes
# back is set by how much of the beam the string intercepts). Across this set that is
# .014 against .070 = 5.1x = 14.0 dB, and the thin strings are also up to 0.71 further from
# the sensor plane, since the plane references the THICKEST string's top -- call it 16 dB.
# Signal is also linear in distance from the termination, so distance can buy some of that
# back: +20*log10(d/12) dB. It is the WORST lever we have -- logarithmic gain against a
# linear cost in playing space -- and it cannot come close to closing 16 dB on its own
# (equalising .014 would need d = 60, putting the board edge at -66.5). But the user's call
# is to spend every lever rather than hedge, so the five PLAIN strings get the step.
#
# A STEP, not a taper, and that is the better shape here: a taper interpolates, so it would
# hand string 5 almost nothing, while a step gives all five plain strings the full +5.3 dB.
# It also keeps the board a two-rectangle outline instead of a trapezoid.
# The wound strings stay at 12 -- they do not need it, and every millimetre out there is
# playing space spent for nothing.
SENSE_D_WOUND = 12.0                             # strings 6-10, .030-.070 (wound)
SENSE_D_PLAIN = 22.0                             # strings 1-5,  .014-.024 (plain)
N_PLAIN       = 5                                # count of plain strings, from string 1
SENSE_D       = SENSE_D_WOUND                    # the +X-most row; sets the tie-bar minimum
SENSE_X       = TERMINATION_X - SENSE_D_WOUND    # -16.0
SENSE_X_PLAIN = TERMINATION_X - SENSE_D_PLAIN    # -26.0
# Y where the outline steps: between string 5 and string 6, both of which sit ~4.7 off
# centre with their detectors 1.6 further, so the centre line is clear of every package.
Y_STEP = 0.0


def sense_d(i: int) -> float:
    """Sensing distance from the termination for string i (0-based)."""
    return SENSE_D_PLAIN if i < N_PLAIN else SENSE_D_WOUND


def sense_x(i: int) -> float:
    return TERMINATION_X - sense_d(i)
# Floor, from the string's bending-stiffness length sqrt(EI/T): ~1.2 mm for the plain
# .015 core at ~120 N, ~1.7 mm for the wound .070 (core ~.018) at ~150 N. The boundary
# layer where the string stops following the ideal mode shape -- and the effective
# termination point turns frequency-dependent, which would put inharmonicity straight
# into a PITCH measurement -- runs a few multiples of that, so 5-10 mm. 10 is the
# pessimistic end of that estimate; SENSE_D keeps ~20% over it.
STIFF_FLOOR   = 10.0

OPT_GAP = 3.0                                    # sensor face -> string TOP (down-firing)
PCB_T   = 1.6                                    # FR4
PCB_W   = 20.0                                   # X -- sensor row + the analog field
# The sensor row sits near the board's -X EDGE, not on its centre line: the row's X is
# fixed by the physics (SENSE_X) and everything else is free to sit +X of it, toward the
# endplate that already exists. Centring the board on the sensors instead pushed its -X
# edge -- and therefore the tie-bar extension carrying it -- 8 mm further over the player
# for no reason.
# 2.5, sized from the WIDEST part in the row now that packages run long-axis-along-X: the
# 0805 emitter's 1.0 half-width + JLCPCB's 1.0 component-to-edge rule + their 0.2 outline
# tolerance = 2.2, rounded up.
SENSE_EDGE = 2.5                                 # sensor row inset from the board's -X edge

# ── PACKAGE LIBRARY -- real outlines, (X, Y, Z) AS PLACED ────────────────────
# Body + leads where leads protrude, at JEDEC/IPC MAX, so the model is the worst case an
# assembler can hand us rather than a nominal that a real part exceeds.
# (An earlier revision carried invented envelopes; among other things it modelled the
# emitter and its detectors FLUSH against each other at 0.00 mm, which is unbuildable.)
PKG = {
    "0402":     (1.00, 0.50, 0.55),   # 1005 metric; 0.55 is MLCC max, resistors are lower
    "0603":     (1.60, 0.80, 0.95),   # 1608 metric
    "0805C":    (2.00, 1.25, 1.45),   # 2012 metric MLCC (taller than the optoelectronic 0805)
    "0805OPT":  (2.00, 1.25, 0.85),   # optoelectronic 0805, e.g. Vishay VSMB1940X01
    "SOT-23":   (2.90, 2.40, 1.30),   # 3-lead, across the leads
    "SOT-23-5": (2.90, 2.80, 1.45),
    "SOT-563":  (1.60, 1.60, 0.60),
    "SOIC-14":  (6.00, 8.65, 1.75),   # LONG AXIS ALONG Y: 8.65 body, 6.00 across the leads
    "QFN-24":   (4.00, 4.00, 0.90),   # 4x4 mm, e.g. USB3343-class ULPI PHY
    "LQFP100":  (16.00, 16.00, 1.60), # JEDEC MS-026 BED: 14x14 body, 16x16 over the leads
    "3225":     (3.20, 2.50, 0.90),   # 3.2 x 2.5 crystal
    "USB-C":    (8.94, 7.35, 3.16),   # TYPE-C-31-M-12 (LCSC C165948)
    # JST XH 2-pin, SMT SIDE-ENTRY (S2B-XH-SM4-TB class), long axis along Y so the mouth
    # faces -X. Length scaled from the S4B-XH-SM4-TB figures already in BOM.md (15.0 long
    # over 4 ways at 2.5 pitch -> 7.5 of overhead + 2.5 per way) -- CONFIRM against JST's
    # drawing before layout, like the S4B was.
    "XH-SM-2":  (6.10, 10.00, 7.00),
}
LED_PKG = PKG["0805OPT"]
PD_PKG  = PKG["0805OPT"]
PKG_CLR = 0.25                                   # least placement gap between packages
EDGE_KEEP = 1.2                                  # part -> board edge: JLCPCB's 1.0 rule
                                                 # + their 0.2 routed-outline tolerance
PART_KEEP = 2.0                                  # sensor row -> anything else, in X
ROW_GAP   = 1.0                                  # between placement rows/columns
# Any package sitting over the sensing field hangs BELOW the emitter plane if it is
# taller than the emitter, and the strings run under the whole board -- not just under
# the sensor row. The quad op-amps (1.75) are the deep ones out there. This is the floor
# on what is left between such a package and the top of the thickest string; it is not
# an optical number (the optical standoff is OPT_GAP, at the sensors) but a mechanical
# one, for string installation and for the string's own excursion.
PART_STRING_CLR = 1.5

# SINGLE-SIDED (user): every part on the BOTTOM face. One populated side = one stencil,
# one reflow, no back-side placement. It costs length -- the digital block has to queue
# up in -Y rather than tuck under the analog field -- and that is the trade taken.
#
# Z stack, built DOWNWARD from the strings. The LED sets the board height (its face must
# land on SENSE_FACE_Z); taller packages therefore hang LOWER than the sensors. That is
# fine because every one of them lives past the last string in Y -- asserted below.
# The standoff datum is the TOP OF THE THICKEST STRING, not D.STRING_Z.
# D.STRING_Z is the string CENTRE line -- the model holds centres coplanar (verified: the
# .070 low C tops out at 16.89, the .054 at 16.69, both centred on 16.00), so string TOPS
# rise with gauge. Referencing D.STRING_Z directly, as this did, silently gave the
# THICKEST string -- the one nearest the sensors -- only 2.11 of the intended 3.0, and put
# the USB shell 0.2 INTO the low C. Reference the worst case and every other string simply
# gets more gap.
STRING_TOP_MAX = D.STRING_Z + max(D.STRING_GAUGE) / 2     # 16.889
SENSE_FACE_Z   = STRING_TOP_MAX + OPT_GAP                 # sensor faces look down
PCB_BOT        = SENSE_FACE_Z + LED_PKG[2]                # board underside
PCB_TOP        = PCB_BOT + PCB_T                          # board top; nothing above it
STACK_BOT_Z    = PCB_BOT - max(p[2] for p in PKG.values())  # lowest package (the USB shell)

# ── per-string sensor triplet ────────────────────────────────────────────────
PD_DY   = 1.6                                    # detector offset either side of the string.
                                                 # Scaled to the SHORT standoff -- at 3 mm a
                                                 # wider straddle would view the string at too
                                                 # oblique an angle to return signal.
END_KEEP = 2.0                                   # outer detector -> the digital block


def string_y_at(i: int, x: float) -> float:
    """String i's Y at X, on the linear nut->changer fan (0 at the nut block, 1 at the
    changer). The sensors sit on THESE, not on a uniform pitch -- which is the whole
    argument for a custom PCB over a fixed-pitch array."""
    t = (x - D.NUT_BLOCK_X) / (D.BRIDGE_X - D.NUT_BLOCK_X)
    return D.nut_y(i) + (D.string_y(i) - D.nut_y(i)) * t


# X extent. The +X edge is common; the -X edge STEPS with the sensor row, so only the
# +Y half -- where the plain strings are, at y > 0 -- reaches deep into the playing area.
# That matters more than it looks: the tie bar's underside is only 3.0 above the strings,
# so nothing can be picked UNDER it, and the bar's -X face is the boundary of the picking
# zone. Stepping keeps that boundary at 14.5 mm from the termination over the wound
# strings and moves it to 24.5 only over the plain ones.
PCB_X0  = SENSE_X - SENSE_EDGE + PCB_W           # 1.5  -- +X edge, common to both sections
PCB_X1  = SENSE_X - SENSE_EDGE                   # -18.5 -- -X edge, WOUND (-Y) section
PCB_X1W = SENSE_X_PLAIN - SENSE_EDGE             # -28.5 -- -X edge, PLAIN (+Y) section
PCB_CX  = (PCB_X0 + PCB_X1) / 2
MID_X   = PCB_CX                                 # centre line, for the wide digital parts


def board_x1(y: float) -> float:
    """The board's -X edge at Y -- the step."""
    return PCB_X1W if y > Y_STEP else PCB_X1

_OUTER_Y = max(abs(string_y_at(i, sense_x(i))) for i in range(D.N_STRINGS))
SENSE_HL = _OUTER_Y + PD_DY                      # last sensor Y; NOTHING else inside this

# ── ANALOG FIELD -- X columns, running +X from the sensor row's keep-out ─────
# Ordered by how much each part hates a long trace: the LED ballast hugs the emitters
# (short, high-di/dt loop), the TIAs come next (the summing node is the noise-critical
# point on the board), the feedback R/C and decoupling fill the remaining +X strip.
AF_X0 = SENSE_X + LED_PKG[0] / 2 + PART_KEEP                       # -13.0
AF_X1 = PCB_X0 - EDGE_KEEP                                         # 0.3
# LED ballast rides just +X of ITS OWN emitter, per string, so the step carries it along:
# it is the high-di/dt half of the emitter loop and wants to stay next to the part it
# feeds. -12.20 over the wound row, -22.20 over the plain one.
LEDR_DX  = LED_PKG[0] / 2 + PART_KEEP + PKG["0603"][0] / 2         # +3.80 off the emitter
COL_LEDR = SENSE_X + LEDR_DX                                       # -12.20 (wound row)
COL_OPA  = COL_LEDR + PKG["0603"][0] / 2 + ROW_GAP + PKG["SOIC-14"][0] / 2   # -7.40
COL_FB   = COL_OPA + PKG["SOIC-14"][0] / 2 + ROW_GAP               # -3.40, first 0402 column
FB_PITCH = 1.6                                                     # 0402 column pitch
FB_COLS  = 3
FB_ROWS  = (-1.8, -0.6, 0.6, 1.8)                                  # 12 slots per quad

# ── DIGITAL BLOCK -- the -Y room past the last string ───────────────────────
DIG_Y0 = -(SENSE_HL + END_KEEP)                  # -46.0, where the digital block may start


def _spread(out, y, items, x0=None, x1=None):
    """Lay a row of parts evenly across an X span at row-centre y. Even spacing is a
    REPRESENTATIVE placement, not a layout: what it has to be right about is the area
    budget and the Z envelope. A negative slack shows up as a package overlap in
    _assert_parts_clear rather than passing quietly."""
    x0 = PCB_X1 + EDGE_KEEP if x0 is None else x0
    x1 = PCB_X0 - EDGE_KEEP if x1 is None else x1
    widths = [PKG[p][0] for _, _, p in items]
    gap = ((x1 - x0) - sum(widths)) / max(len(items) - 1, 1)
    cx = x0
    for (ref, desc, pkg), w in zip(items, widths):
        out.append({"ref": ref, "desc": desc, "pkg": pkg, "x": cx + w / 2, "y": y})
        cx += w + gap


def _block(out, y, items, x0=None, x1=None):
    """Pack parts into as many rows as they NEED, marching -Y from y (the block's +Y
    edge); returns the block's -Y edge.

    Rows are packed, not hand-assigned, on purpose: hand-tuned rows silently went under
    the placement clearance every time a part was added, and the board length has to be
    an OUTPUT of the part list rather than a number that parts get squeezed into."""
    x0 = PCB_X1 + EDGE_KEEP if x0 is None else x0
    x1 = PCB_X0 - EDGE_KEEP if x1 is None else x1
    span, row, used = x1 - x0, [], 0.0

    def flush(row, y):
        if not row:
            return y
        h = max(PKG[p][1] for _, _, p in row)
        _spread(out, y - h / 2, row, x0, x1)
        return y - h - ROW_GAP

    for it in items:
        w = PKG[it[2]][0]
        need = used + w + (PKG_CLR + 0.15 if row else 0.0)
        if row and need > span:
            y = flush(row, y)
            row, used, need = [], 0.0, w
        row.append(it)
        used = need
    return flush(row, y)


def _parts():
    """EVERY component on the strip, with its package and placed centre.

    ONE source of truth for the 3D model, the area budget, the clearance assertions and
    the BOM in BOM.md -- so a part cannot exist in one and not the others.

    Packages are real outlines at JEDEC/IPC max (see PKG). Placement is representative:
    the blocks, their order and their X columns are deliberate, but the exact XY of an
    0402 is the layout's business, not the assembly model's."""
    P = []

    def add(ref, desc, pkg, x, y):
        P.append({"ref": ref, "desc": desc, "pkg": pkg, "x": x, "y": y})

    # ---- 1. sensing row: 10 triplets ON THE STRING FAN, + their LED ballast ----
    for i in range(D.N_STRINGS):
        n, sx = i + 1, sense_x(i)
        sy = string_y_at(i, sx)
        kind = "plain" if i < N_PLAIN else "wound"
        add("D%d" % n, "IR emitter, 940 nm, NARROW beam", "0805OPT", sx, sy)
        add("PD%dA" % n, "PIN photodiode, +Y of string", "0805OPT", sx, sy + PD_DY)
        add("PD%dB" % n, "PIN photodiode, -Y of string", "0805OPT", sx, sy - PD_DY)
        add("R%d" % n, "LED current-set resistor (per-string, %s)" % kind,
            "0603", sx + LEDR_DX, sy)

    # ---- 2. the 20 TIAs: one QUAD per string PAIR, at that pair's centroid ----
    for q in range(D.N_STRINGS // 2):
        cy = (string_y_at(2 * q, sense_x(2 * q))
              + string_y_at(2 * q + 1, sense_x(2 * q + 1))) / 2
        add("U%d" % (q + 1), "quad op-amp -- 4x transimpedance amp", "SOIC-14", COL_OPA, cy)
        # Feedback R/C per channel + local decoupling, in the 0402 field beside the quad.
        # The feedback cap doubles as the anti-alias pole, so it is per-channel, not shared.
        items = ([("Rf%d%d" % (q + 1, k + 1), "TIA feedback resistor") for k in range(4)]
                 + [("Cf%d%d" % (q + 1, k + 1), "TIA feedback cap (anti-alias pole)")
                    for k in range(4)]
                 + [("Cd%d%d" % (q + 1, k + 1), "op-amp decoupling") for k in range(2)])
        slots = [(COL_FB + c * FB_PITCH, cy + r) for r in FB_ROWS for c in range(FB_COLS)]
        for (ref, desc), (px, py) in zip(items, slots):
            add(ref, desc, "0402", px, py)

    # ---- 3. digital block, marching -Y from the last string ----
    y = DIG_Y0

    # MCU. LQFP100 is the floor, not a preference: 20 ADC inputs + a 12-signal ULPI bus
    # will not fit a 64-pin part, and every STM32 with an INTERNAL HS PHY is >=144 pins
    # (22x22 over leads -- wider than this board can ever be).
    y -= PKG["LQFP100"][1] / 2
    add("U6", "MCU -- Cortex-M7, 3x 16-bit ADC, USB OTG_HS via ULPI", "LQFP100", MID_X, y)
    y -= PKG["LQFP100"][1] / 2 + ROW_GAP

    # POWER INPUT -- 5V from the instrument rail, NOT from USB VBUS. Sizing: MCU ~200-300,
    # PHY ~50, 21 op-amp channels ~40, and ten emitters at whatever current the thin
    # strings turn out to need. That is already past a USB port's 500 mA before the LEDs
    # are counted, and LED current is the single best SNR lever we have -- capping it at
    # a port's budget would be exactly the hedge the user ruled out.
    # SIDE-ENTRY on the board's -X EDGE, not the -Y end: the -Y edge is spoken for by the
    # USB receptacle and the floor-ledge lane, and -X of the board is open air (the
    # optical relief takes the tie bar's wall away there), so a mouth on that edge is
    # reachable. It plugs in after the board slides home.
    y -= PKG["XH-SM-2"][1] / 2
    add("J2", "power in, 5V from the instrument rail -- side entry, -X edge",
        "XH-SM-2", PCB_X1 + PKG["XH-SM-2"][0] / 2, y)
    _spread(P, y, [("C%d" % (140 + k), "power-input decoupling", "0402") for k in range(4)],
            x0=PCB_X1 + PKG["XH-SM-2"][0] + ROW_GAP, x1=PCB_X0 - EDGE_KEEP)
    y -= PKG["XH-SM-2"][1] / 2 + ROW_GAP

    y = _block(P, y, [("C%d" % (100 + k), "MCU decoupling", "0402") for k in range(12)]
                     + [("R30", "BOOT0 pull-down", "0402"),
                        ("R31", "NRST pull-up", "0402")])

    # USB HS PHY + the two crystals. The PHY sits between the MCU and the connector
    # because it owns both ends: 12 ULPI signals up to the MCU, D+/D- down to the port.
    y = _block(P, y, [("Y1", "25 MHz crystal -- MCU HSE", "3225"),
                      ("U7", "USB 2.0 high-speed ULPI PHY", "QFN-24"),
                      ("Y2", "24 MHz crystal -- PHY reference", "3225")]
                     + [("C%d" % (120 + k), "PHY decoupling", "0402") for k in range(3)]
                     + [("C%d" % (123 + k), "crystal load cap", "0402") for k in range(4)])

    # Power + LED drive. All ten emitters are driven TOGETHER by one FET: ambient
    # subtraction sweeps the whole row "on" then the whole row "off", which gives the
    # analog front end ~10 us to settle instead of ~1 us. One driver, not ten.
    # U11 is the mid-rail reference the 20 TIAs sit on: single-supply transimpedance
    # needs a bias for the non-inverting inputs, and all 20 quad channels are spoken for.
    y = _block(P, y, [("U8", "LDO -- 3V3 digital", "SOT-23-5"),
                      ("U9", "LDO -- 3V3 analog (low noise)", "SOT-23-5"),
                      ("U11", "single op-amp -- TIA mid-rail reference buffer", "SOT-23-5"),
                      ("Q1", "N-ch MOSFET -- LED row driver", "SOT-23"),
                      ("U10", "USB data-line ESD array", "SOT-563"),
                      ("FB1", "ferrite bead -- analog rail isolation", "0603"),
                      ("C130", "bulk cap -- VBUS", "0805C"),
                      ("C131", "bulk cap -- 3V3 digital", "0805C"),
                      ("C132", "bulk cap -- 3V3 analog", "0805C"),
                      ("C133", "reference bypass", "0805C"),
                      ("R32", "USB-C CC1 pull-down 5k1", "0402"),
                      ("R33", "USB-C CC2 pull-down 5k1", "0402"),
                      ("R34", "mid-rail divider", "0402"),
                      ("R35", "mid-rail divider", "0402"),
                      ("R36", "LED driver gate resistor", "0402")])

    # Connector, at the -Y edge with its mouth flush so a cable plugs in horizontally and
    # routes to the bay. It hugs the -X edge ON PURPOSE: the +X lane beside it is the only
    # place the -Y floor ledge can bear on the board (see _ledge_specs), so nothing else
    # may be placed in this Y band.
    usb_x = PCB_X1 + EDGE_KEEP + PKG["USB-C"][0] / 2
    y -= PKG["USB-C"][1] / 2
    add("J1", "USB-C receptacle -- 10ch audio + MIDI + DFU", "USB-C", usb_x, y)
    return P


PARTS = _parts()


def part(ref):
    for p in PARTS:
        if p["ref"] == ref:
            return p
    raise KeyError(ref)


def part_span(p):
    """(x0, x1, y0, y1) footprint of a placed part."""
    dx, dy, _ = PKG[p["pkg"]]
    return (p["x"] - dx / 2, p["x"] + dx / 2, p["y"] - dy / 2, p["y"] + dy / 2)


# ── board extent ────────────────────────────────────────────────────────────
# +Y end is set by the SENSING FIELD (nothing lives out there); -Y by the connector,
# whose mouth must reach the edge to be pluggable. Both then add a floor ledge.
FLOOR_L    = 3.0                                          # ledge depth in Y -- bearing only
LEDGE_KEEP = 1.0                                          # ledge -> nearest package (clearance)
# Slip fit, SHARED by the pocket cutter and the ledges. It has to be shared: the pocket
# is cut to board + PCB_CLR, so a ledge drawn to the BOARD's own edges stops PCB_CLR short
# of the pocket wall and the union leaves it FLOATING IN AIR (user-caught in the viewer:
# the -Y ledge as a detached block). Anything unioned back INTO a pocket must be sized
# from the pocket, not from the part the pocket was cut for.
PCB_CLR    = 0.3
# ...and it has to reach PAST the wall, not just touch it. LEDGE_ROOT is that run into
# solid bar, and it earns its keep twice:
#   FUSE -- the pocket clears everything under the board, so the root is the ledge's only
#     joint to the bar. At the wall plane it is the bar's full depth, not the 0.85 of
#     overlap the ledge's top shares with the bar underside.
#   PRINT -- the endplate builds +X -> -X (it prints flat on its +X face), so a shelf
#     rooted in solid material at +X is supported layer-on-layer along its whole run,
#     while a shelf floating inside the pocket has no first layer at all. This is why
#     BOTH ledges are anchored at +X and grow -X; see _ledge_specs.
LEDGE_ROOT = 2.0
# Ledge THICKNESS. The tie bar's underside sits at SENSE_FACE_Z, which leaves only
# PCB_BOT - SENSE_FACE_Z = 0.85 of material under the board -- below the 1.6 floor the
# user set for added material. The ledges are free to hang LOWER than the bar, though,
# because both sit outside the string field, so nothing here has to respect OPT_GAP.
LEDGE_T    = 1.6                                          # two full beads

PCB_YP = SENSE_HL + END_KEEP + FLOOR_L                    # +Y end, incl. its ledge
PCB_YM = part("J1")["y"] - PKG["USB-C"][1] / 2            # -Y end = the connector mouth
PCB_L  = PCB_YP - PCB_YM
PCB_CY = (PCB_YP + PCB_YM) / 2
# Ledge outer Y -- past the pocket wall, into solid bar (second fuse face; see LEDGE_ROOT).
# The endplate's tie bar has to reach past LEDGE_YM for that to be solid, so it reads this.
LEDGE_YP = PCB_YP + PCB_CLR + LEDGE_ROOT
LEDGE_YM = PCB_YM - PCB_CLR - LEDGE_ROOT

# OPTICAL RELIEF -- delete the pocket's -X side wall over the sensing field.
# That wall runs parallel to the entire sensor row, and PETG-GF is reflective in IR, so
# it closes a stray path: emitter -> -X -> wall -> back -> photodiode, never touching a
# string. At this spacing the bounce path is a few mm against a ~6 mm signal path (3 down
# to the string and back), so it is a real fraction of what the detectors see -- and
# because it is modulated by the emitter exactly like the signal, AMBIENT SUBTRACTION
# DOES NOT REMOVE IT. It lands as a DC pedestal that eats headroom and contributes shot
# noise carrying no information. Cheaper to delete the wall than to buy distance from it.
# Measured from the DEEPEST section (the plain-string one), so the wall is gone at every
# Y -- referenced to PCB_X1 it would have left plastic facing the plain-string emitters,
# which are the very ones short of signal.
RELIEF_X1 = PCB_X1W - 8.0                        # overshoot, to break out past the tie bar

# ── RETENTION ────────────────────────────────────────────────────────────────
# Constraint (user): NO endplate material may sit -X of the PCB -- the board itself is
# the furthest anything reaches into the playing area.
#
# So the board is a SLIDE-IN: it enters along -X->+X through the one open face, into a
# slot whose FLOOR (the two end ledges) carries it in -Z and sets the sensor standoff,
# whose CEILING caps it in +Z, and whose end/+X walls locate it in Y and +X. Every degree
# of freedom is then closed except sliding back out -X -- so retention is ONE screw.
MOUNT_X = COL_OPA                                # in the op-amp column, which has a clear
                                                 # 10 mm Y gap between quads


def mount_points():
    """The single retention screw, in the Y GAP BETWEEN two quad op-amps -- the only
    mid-board spot with real clearance in both axes (the op-amp column's pair-to-pair
    pitch is ~18.8 against an 8.65 package). (x, y, z) is the anchor mouth on the board's
    TOP face: the screw travels +Z from below, and the insert pocket, if those self-tapped
    threads ever strip, opens downward into the board slot where an iron can reach it.

    Mid-span rather than at an end so it also damps the board against the strings'
    vibration; the ends are already held in Y and -Z by the slot itself."""
    cy = [(string_y_at(2 * q, sense_x(2 * q))
           + string_y_at(2 * q + 1, sense_x(2 * q + 1))) / 2
          for q in range(D.N_STRINGS // 2)]
    return [(MOUNT_X, (cy[1] + cy[2]) / 2, PCB_TOP)]


def _part_solid(p):
    """Package hanging DOWN from the board's underside (single-sided)."""
    dx, dy, dz = PKG[p["pkg"]]
    return box_at(dx, dy, dz, x=p["x"], y=p["y"], z=PCB_BOT - dz / 2)


def _outline(grow=0.0, t=None, zc=None):
    """The board's STEPPED footprint as a solid: the wide (plain-string) section from
    Y_STEP to +Y, the narrow (wound) section from Y_STEP to -Y, sharing the +X edge.
    `grow` inflates it in X and Y for the pocket's slip fit."""
    t = PCB_T if t is None else t
    zc = PCB_BOT + PCB_T / 2 if zc is None else zc
    out = None
    for y0, y1, x1 in ((Y_STEP, PCB_YP, PCB_X1W), (PCB_YM, Y_STEP, PCB_X1)):
        # only the OUTER Y face of each section grows -- the shared seam at Y_STEP must
        # not, or the two halves would overlap by 2*grow and the seam would move
        a, b = (y0 - grow, y1) if y0 != Y_STEP else (y0, y1 + grow)
        blk = box_at((PCB_X0 + grow) - (x1 - grow), b - a, t,
                     x=((PCB_X0 + grow) + (x1 - grow)) / 2, y=(a + b) / 2, z=zc)
        out = blk if out is None else out.union(blk)
    return out


def opt_pcb() -> cq.Workplane:
    """The assembled optical strip: FR4 + EVERY placed component, at its true Z, all
    facing DOWN. Fab/purchased -> NO standalone STEP (cadkit convention); it exists in
    the assembly as the fit-check that it clears the strings and fits the tie bar."""
    pcb = _outline()
    for p in PARTS:
        pcb = pcb.union(_part_solid(p))
    for mx, my, _ in mount_points():                          # M2 clearance hole
        pcb = pcb.cut(box_at(M2.shaft_clr_d, M2.shaft_clr_d, PCB_T + 2,
                             x=mx, y=my, z=PCB_BOT + PCB_T / 2))
    return pcb


def opt_pcb_pocket() -> cq.Workplane:
    """Cutter for the tie-bar pocket, opening DOWNWARD: the board plus everything hanging
    beneath it, with a slip fit. Cut from the same numbers as the board, so the pocket is
    always exactly the board."""
    zclr = 0.2
    # (a) THE SLOT -- board thickness, with the Z clearance ABOVE so the FLOOR stays the
    # datum: the board rests on the ledges, which makes the sensor standoff a printed
    # dimension rather than something a screw has to hold. The board SLIDES IN along -X.
    pocket = _outline(grow=PCB_CLR, t=(PCB_TOP + zclr) - PCB_BOT,
                      zc=(PCB_BOT + PCB_TOP + zclr) / 2)
    # (b) EVERYTHING UNDER THE BOARD -- cut full depth over the WHOLE footprint, and
    # carried out past the tie bar's -X face so no plastic faces the emitters (the stray
    # emitter->wall->detector path; see RELIEF_X1). The floor ledges are unioned back
    # afterwards by the endplate, so they define their own shape.
    # This used to spare the two ledge Y-bands instead -- which left material under the
    # USB inside the -Y band and drove it straight into the connector, because that ledge
    # is X-limited and the spared band was not.
    x0 = PCB_X0 + PCB_CLR
    pocket = pocket.union(box_at(x0 - RELIEF_X1, PCB_L + 2 * PCB_CLR, PCB_BOT - STACK_BOT_Z,
                                 x=(x0 + RELIEF_X1) / 2, y=PCB_CY,
                                 z=(STACK_BOT_Z + PCB_BOT) / 2))
    return pocket


def _ledge_specs():
    """(y0, y1, x0, x1) per end ledge.

    Both are ROOTED AT +X, in solid bar past the pocket wall, and grow from there in -X
    -- the build direction (see LEDGE_ROOT). Both also overrun the pocket in Y for a
    second fuse face.

    The -Y one is X-LIMITED, to the lane +X OF THE USB RECEPTACLE. It cannot be full
    width: the connector's mouth has to reach the -Y board edge to be pluggable and its
    shell occupies the ledge's own Z band. It cannot sit -X of the connector either --
    that side faces nothing but open pocket all the way to the board's -X edge, so it
    would have no material at +X to print onto. The connector is deliberately placed
    against the -X edge to open this lane, and nothing else is placed in its Y band.

    The +Y one is full width: nothing is out there."""
    ux0, ux1, _, _ = part_span(part("J1"))
    root_x = PCB_X0 + PCB_CLR + LEDGE_ROOT
    return [
        # +Y ledge is in the WIDE section, so it runs out to that section's edge
        (PCB_YP - FLOOR_L, LEDGE_YP, PCB_X1W - PCB_CLR, root_x),
        (LEDGE_YM, PCB_YM + FLOOR_L, ux1 + LEDGE_KEEP, root_x),
    ]


def opt_floor_ledges() -> cq.Workplane:
    """The two end ledges the board rests on, as a solid for the endplate to UNION after
    it has cut the pocket. They hang LEDGE_T below the board rather than relying on the
    0.85 the tie bar happens to leave there -- see LEDGE_T. Both sit outside the string
    field, so hanging below the bar's underside fouls nothing.

    That overhang is the one print-direction step in the feature: LEDGE_T - LED height =
    0.75 of new material at the ledge's first (+X-most) layer, where it drops below the
    bar's underside. Sub-millimetre, on a face that carries no fit."""
    out = None
    for y0, y1, x0, x1 in _ledge_specs():
        blk = box_at(x1 - x0, y1 - y0, LEDGE_T,
                     x=(x0 + x1) / 2, y=(y0 + y1) / 2, z=PCB_BOT - LEDGE_T / 2)
        out = blk if out is None else out.union(blk)
    return out


def bom_rows():
    """The strip's BOM, grouped -- (qty, description, package, refs). Same PARTS table the
    3D model is built from, so BOM.md and the assembly cannot disagree about what is on
    this board."""
    groups = {}
    for p in PARTS:
        groups.setdefault((p["desc"], p["pkg"]), []).append(p["ref"])
    rows = [(len(r), desc, pkg, r) for (desc, pkg), r in groups.items()]
    rows.sort(key=lambda r: (-PKG[r[2]][0] * PKG[r[2]][1], r[1]))
    return rows


def _assert_field_clear():
    """Guard the bugs this part can silently ship, NONE of which the assembly overlap
    gate can catch -- the board and its components are ONE unioned solid, and a pairwise
    checker never tests a solid against itself."""
    # 1. emitter <-> detector placement gap. This was 0.00 (packages flush) before the row
    # was laid long-axis-along-X; a real assembler cannot place that.
    gap = (PD_DY - PD_PKG[1] / 2) - LED_PKG[1] / 2
    if gap < PKG_CLR:
        raise AssertionError(
            f"optical strip: emitter-to-detector gap {gap:.2f} < PKG_CLR {PKG_CLR}")
    # 2. sensing station inside the string's stiffness boundary layer, where pitch would
    # pick up inharmonicity error.
    if SENSE_D < STIFF_FLOOR:
        raise AssertionError(
            f"optical strip: sensing at {SENSE_D:.1f} mm from the termination is inside "
            f"the {STIFF_FLOOR:.1f} mm stiffness floor -- pitch would be inharmonic")
    # 3. EVERY part inside the board, clear of the routed edge, and clear of every other
    # part. A package placed by measuring in from the PCB end once landed exactly on
    # string 10's triplet; even spacing in _spread can silently go negative.
    for p in PARTS:
        x0, x1, y0, y1 = part_span(p)
        # -X limit is the STEPPED edge: a part straddling Y_STEP has to satisfy the
        # NARROW section, since that is where the board actually ends under it.
        lim = board_x1(y0) if board_x1(y0) == board_x1(y1) else PCB_X1
        keep_x0 = 0.0 if p["ref"] == "J2" else EDGE_KEEP   # J2's mouth IS the -X edge
        keep_ym = 0.0 if p["ref"] == "J1" else EDGE_KEEP   # J1's mouth IS the -Y edge
        if (x0 < lim + keep_x0 - 1e-9 or x1 > PCB_X0 - EDGE_KEEP + 1e-9
                or y0 < PCB_YM + keep_ym - 1e-9 or y1 > PCB_YP - EDGE_KEEP + 1e-9):
            raise AssertionError(
                f"optical strip: {p['ref']} ({p['desc']}) at "
                f"X {x0:.2f}..{x1:.2f} Y {y0:.2f}..{y1:.2f} breaks the {EDGE_KEEP} "
                f"edge keep-out of board X {lim:.2f}..{PCB_X0:.2f} "
                f"Y {PCB_YM:.2f}..{PCB_YP:.2f}")
    for i, a in enumerate(PARTS):
        ax0, ax1, ay0, ay1 = part_span(a)
        for b in PARTS[i + 1:]:
            bx0, bx1, by0, by1 = part_span(b)
            # L-infinity separation: negative means the footprints interpenetrate
            sep = max(max(ax0, bx0) - min(ax1, bx1), max(ay0, by0) - min(ay1, by1))
            if sep < PKG_CLR - 1e-9:
                raise AssertionError(
                    f"optical strip: {a['ref']} ({a['desc']}) and {b['ref']} "
                    f"({b['desc']}) are {sep:.2f} apart, inside the {PKG_CLR} "
                    f"placement clearance")
    # 4. NOTHING may sit -X OF A SENSOR at an overlapping Y. That is the open side the
    # optical relief exists to clear: a package out there is a reflector on the stray
    # emitter -> -X -> back -> detector path, which ambient subtraction cannot remove
    # because it is modulated by the emitter exactly like the signal. With the row now
    # stepped this has to be per-sensor rather than one X band.
    sensors = [p for p in PARTS if p["pkg"] == "0805OPT"]
    for p in PARTS:
        if p["pkg"] == "0805OPT":
            continue
        px0, _, py0, py1 = part_span(p)
        for s in sensors:
            sx0, _, sy0, sy1 = part_span(s)
            if px0 < sx0 and py1 > sy0 and py0 < sy1:
                raise AssertionError(
                    f"optical strip: {p['ref']} ({p['desc']}) reaches X={px0:.2f}, "
                    f"-X of sensor {s['ref']} at {sx0:.2f} and overlapping it in Y -- "
                    f"it would sit in that emitter's stray-reflection path")
    # 5. anything over the sensing field must clear the STRINGS in Z. The strings run
    # under the whole board, not just under the sensor row, so a tall package in the
    # analog field is over a string even though it is nowhere near the optics.
    for p in PARTS:
        dz = PKG[p["pkg"]][2]
        _, _, y0, y1 = part_span(p)
        if y1 <= -SENSE_HL or y0 >= SENSE_HL:
            continue
        clr = (PCB_BOT - dz) - STRING_TOP_MAX
        if clr < PART_STRING_CLR - 1e-9:
            raise AssertionError(
                f"optical strip: {p['ref']} ({p['desc']}, {p['pkg']}) hangs to "
                f"Z={PCB_BOT - dz:.2f} over the sensing field, leaving {clr:.2f} to the "
                f"thickest string at {STRING_TOP_MAX:.2f} -- under PART_STRING_CLR "
                f"{PART_STRING_CLR}")
    # 6. the retention screw must clear every package.
    for mx, my, _ in mount_points():
        r = 2.5                                   # screw head / boss radius, generous
        for p in PARTS:
            x0, x1, y0, y1 = part_span(p)
            if x0 - r < mx < x1 + r and y0 - r < my < y1 + r:
                raise AssertionError(
                    f"optical strip: retention screw at ({mx:.2f}, {my:.2f}) lands on "
                    f"{p['ref']} ({p['desc']})")
    # 6. the -Y floor ledge's lane must be free of packages, or the board cannot seat.
    for y0, y1, x0, x1 in _ledge_specs():
        for p in PARTS:
            px0, px1, py0, py1 = part_span(p)
            if px1 > x0 and px0 < x1 and py1 > y0 and py0 < y1:
                raise AssertionError(
                    f"optical strip: {p['ref']} ({p['desc']}) sits in a floor-ledge lane "
                    f"(X {x0:.2f}..{x1:.2f} Y {y0:.2f}..{y1:.2f})")
    # 7. ledges must reach past the pocket wall -- both a detached-island bug and a
    # print bug (no first layer), and the overlap gate sees neither.
    for y0, y1, x0, x1 in _ledge_specs():
        tag = "+Y" if y1 > 0 else "-Y"
        if x1 < PCB_X0 + PCB_CLR + 1e-9:
            raise AssertionError(
                f"optical strip: {tag} floor ledge ends at X={x1:.2f}, inside the pocket "
                f"wall at {PCB_X0 + PCB_CLR:.2f} -- detached island, and nothing at +X "
                f"to print onto")
        if x1 - x0 <= 0 or y1 - y0 <= 0:
            raise AssertionError(f"optical strip: {tag} floor ledge is degenerate")


_assert_field_clear()
