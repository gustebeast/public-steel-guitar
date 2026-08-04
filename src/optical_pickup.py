"""OPTICAL per-string pickup -- a reflective IR strip that reads all 10 strings
individually, for pitch detection (calibration + audio->MIDI) and for per-string AUDIO.

WHY optical, not a second magnetic hex pickup. Re-examined properly 2026-08-02 (full
working in BOM.md) because the original one-liner was thinner than the decision
deserved. What the check changed:

  * The old reason "a Cycfi Nu Multi is ~$33/string" is NOT the reason. A per-string
    magnetic board is CHEAPER than this one in parts -- PCB planar spiral coils are
    etched copper, i.e. free, and positioned to layout tolerance, which is BETTER than
    optical's placed parts. Manufacturability was never the obstacle.
  * The turns deficit is survivable: ~44-50 dB below a real single-coil, so ~0.5-1 mV,
    with ~84 dB of thermal SNR at the coil's ~6 ohms. Amplifiable, not marginal.
  * THE REASON THAT SURVIVES is interference. A spiral is a ~17.7 cm^2 loop antenna
    over ten SERVO42D steppers running PWM current control directly under the deck.
    Reflective IR couples to that ZERO, not weakly.
  * Two things that would NOT improve by switching, contrary to instinct: channel count
    (hex pickups need TWO coils per string for the same even-function reason SUM/DIFF
    exists here, so 21 channels against 20 -- the LQFP144 stays), and the thin-string
    deficit (frequency helps, ferromagnetic mass hurts, they mostly cancel).
  * One strike specific to THIS instrument: magnets LOAD THE STRING. Damping and
    pitch-pulling are tolerated on a guitar; here they fight motorised tuning to a few
    cents and the long sustain the whole design is built around. Optical exerts no
    force on the string at all.

MOUNTING -- UNDER THE STRINGS, UP-FIRING, ON A CARRIER THAT IS PART OF THE ENDPLATE
AND RIDES ON TOP OF THE DECK (user, this round). The strip spent a while hanging
DOWN from the bridge endplate's tie bar. That is optically better -- a down-firing
sensor is shaded by its own mount, for free -- but it put structure 3.0 mm above the
strings starting 14.5 mm out from the termination, straight through the PALM BLOCKING
zone. Blocking is core right-hand technique on this instrument, not a flourish, so the
overhead mount was a design that fights the player. It went.

What under-string costs, and what pays it back:
  * AMBIENT LIGHT is now the real problem: an up-firing detector looks at the sky, and
    ambient subtraction fixes flicker and offset but NOT saturation. Answered by the
    COVER (see opt_cover): a slotted lid whose -X wall closes the shallow-angle path,
    which also keeps skin and string shed off the optics. An up-firing sensor collects
    debris where a down-firing one sheds it, so the lid is not optional.
  * NO DECK SLOT IS SPENT. The carrier is part of the endplate and simply sits on the
    deck surface, so the magnetic pickup keeps the whole slot grid. There is a 14.0 mm
    clear band between the pickup cavity's +X edge and the deck's end at the endplate,
    and the entire sensing section lives in it.
  * THE BAND IS 14 mm, and that is the binding constraint on this design. It holds ONE
    sensor row plus the transimpedance amps -- not two rows plus the amps. The stepped
    row that gave the plain strings +5.3 dB was dropped for that reason (user's call):
    keeping every TIA within a few mm of its photodiode beats 5.3 dB, because the
    summing node is the noise-critical point on a board reading tens of nanoamps and
    the alternative was a ~90 mm trace sharing a board with a 96 kHz LED driver whose
    switching noise is SYNCHRONOUS with sampling, so subtraction would not cancel it.
    The single row sits further out than the old wound row did, so every string gains
    ~+1.9 dB and the thin ones give up 3.4 relative to the stepped plan.

X POSITION -- FARTHER from the termination is BETTER, which is the opposite of the
intuition. String displacement at distance d from a rigid termination goes as
sin(pi*d/L) ~= pi*d/L, i.e. SIGNAL IS LINEAR IN d. There is also a floor: bending
stiffness gives a boundary layer of order sqrt(EI/T) (a few mm on a wound string)
where the string does not follow the ideal mode shape and the effective termination
point becomes frequency-dependent -- sensing inside it would inject inharmonicity
error into a PITCH measurement.

SENSING LAYOUT -- per string, THREE parts in a row across Y:
      [PD] --PD_DY-- [IR LED] --PD_DY-- [PD]
  ACROSS Y, NOT ALONG X, AND THAT IS FORCED. Y is the axis DIFF has to resolve. Lay the
  same three parts along X (down the string) and both detectors sit under the SAME point
  of the string's lateral motion: they see the same signal, DIFF collapses to ~zero, and
  the octave-error defence below goes with it. The only difference left would be the
  slight amplitude change from sensing at two distances from the termination, which is
  common mode, not lateral information. (It is NOT a humbucking argument -- there is no
  magnetic circuit here. The humbucking-LIKE benefit, that both detectors see the same
  ambient so DIFF rejects it, works at any orientation and so does not set this one.)
  An X-wise row would genuinely beat this on ONE axis -- it would keep both detectors on
  their own string's centre line instead of 1.6 nearer the neighbour -- so we accept a few
  dB more crosstalk to keep DIFF. A wrong octave beats a little pedestal.
  The string sits over the emitter. Light goes up, reflects off the string, and
  returns to both photodiodes.
    * SUM of the pair tracks the string's Z motion. This is the AUDIO signal.
    * DIFFERENCE tracks its Y motion.
  BOTH are needed, and the reason is sharper than "more signal". With the detectors
  symmetric about the emitter, SUM is an EVEN function of lateral displacement and
  DIFF is ODD. So a purely vertical vibration puts a clean f0 in SUM; as the vibration
  plane PRECESSES toward horizontal -- which it does over the long sustain this
  instrument is built for -- SUM's f0 collapses and its 2f0 term takes over. A
  single-axis pickup there does not merely go quiet, it hands the detector a strong,
  coherent, WRONG answer an octave up, which no plausibility gate can coast through.

  NOT combined by magnitude. sqrt(SUM^2 + DIFF^2) is full-wave rectification for a flat
  orbit (2f0 again) and DC for a circular one -- wrong at both extremes. The pitch path
  takes the 2x2 covariance of (SUM, DIFF) over a short window and PROJECTS onto the
  dominant eigenvector: a clean single-axis f0 that follows the precession.

SIGNAL CHAIN. Each photodiode gets its OWN transimpedance amp and its OWN ADC input --
20 of each. SUM and DIFF are then one add and one subtract in firmware, cheaper in
parts than analog sum AND difference stages.
  * AUDIO path: SUM at 48 kHz, 10 channels, out over USB. 960 kB/s -> needs USB HS.
  * PITCH path: decimated to ~6-8 kHz, detected on-chip, MIDI out over the same cable.
    Pitch detection at 48 kHz would be wasted work -- the detector needs 2-3 PERIODS,
    not samples -- so decimating is the right rate, not a compromise.

THE THIN-STRING PROBLEM. Optical signal scales with the string's DIAMETER (the string
IS the target). .014 against .070 is 5.1x = 14.0 dB, and thin strings sit further from
the sensor plane, which references the string nearest it. Levers, in order of value:

  1. EMITTER BEAM ANGLE -- +9.5 dB at +-30 deg, +13.6 at +-20, and free. *** THIS LEVER
     IS UNAVAILABLE (2026-08-01). *** Narrow-beam is not made in 0805: every candidate in
     the LCSC/JLC library is ~120 deg full angle, and the one 940 nm part that looked
     narrower (IR19-21C) is 150 deg AND 0603. D1-D10 are IR17-21C/TR8 at ~120 deg.
     NOTE the cover CANNOT recover this. An aperture DISCARDS off-axis flux, it does not
     redirect it, so on-axis intensity at the string -- and therefore the returned signal
     -- is unchanged. The dB in the budget come from a LENSED emitter putting the SAME
     total flux into a narrower cone. Apertures buy crosstalk and ambient rejection,
     which is worth having and is not this.
  2. PER-STRING LED CURRENT (R1-R10 are per-string VALUES) -- now the FIRST lever, not
     the second, and correspondingly more important. Drive current is why J2 exists.
  3. PER-STRING TIA GAIN (Rf likewise), bounded by the op-amp's GBW, not the resistor.
  4. DISTANCE from the termination -- the worst lever: signal is linear in d.

See BOM.md.

Frames: absolute X/Y/Z. Components face +Z (UP, at the strings).
"""

from __future__ import annotations

import cadquery as cq
from cadquery.selectors import NearestToPointSelector

from . import dimensions as D
from . import chassis as CH
from . import top_plate as TP
from .helpers import box_at
from cadkit.fasteners import M4

# ── where it sits ────────────────────────────────────────────────────────────
# The speaking length ends at the BEARING TANGENT (directly over the axle), NOT at
# BRIDGE_X (which is the ball-end anchor, past the bearing).
TERMINATION_X = D.BRIDGE_AXLE_X                  # -4.0
SENSE_D       = 15.5                             # sensing station, out from the termination
SENSE_X       = TERMINATION_X - SENSE_D          # -19.5
# Floor, from the string's bending-stiffness length sqrt(EI/T): ~1.2 mm for the plain
# .015 core at ~120 N, ~1.7 mm for the wound .070 at ~150 N. The boundary layer where
# the string stops following the ideal mode shape -- and the effective termination point
# turns frequency-dependent, which would put inharmonicity straight into a PITCH
# measurement -- runs a few multiples of that, so 5-10 mm. SENSE_D keeps well over it.
STIFF_FLOOR   = 10.0

# ── THE DECK BAND -- the constraint this whole layout is shaped by ───────────
# The carrier rides on the deck between the magnetic pickup's cavity and the deck's +X
# end at the endplate. Both edges are READ from top_plate so they cannot drift: if the
# pickup's travel or plate size changes, this band changes with it and the assertions
# below fail rather than the parts quietly overlapping.
DECK_TOP   = TP.TZ                                            # 6.00, deck surface
BAND_X0    = TP.PX0                                           # -16.60, deck's +X end
BAND_X1    = TP.PICKUP_X_NOM + TP.CAVITY_X / 2                # -30.62, cavity's +X edge
BAND_CLR   = 0.2                                              # keep off both band edges

OPT_GAP = 3.0                                    # sensor face -> string UNDERSIDE
PCB_T   = 1.6                                    # FR4, NOMINAL. Correct for 4 layer: 1.6 is
                                                 # JLCPCB's standard 4-layer thickness and
                                                 # also their standard at 6, so the "how many
                                                 # layers" question does not move this number.
# ...but 1.6 is a NOMINAL with a +-10% fab tolerance, and that tolerance lands on a
# CLEARANCE. The board's TOP is the design datum (derived down from the string), while the
# thing that physically exists is the printed PLINTH under it -- so a thicker board pushes
# its own components UP, straight into the 0.30 roof gap it has to slide through.
PCB_T_TOL = 0.10 * PCB_T                         # +-0.16; JLCPCB is +-10% over 1.0 mm
PCB_T_MAX = PCB_T + PCB_T_TOL                    # 1.76, the worst case for clearance

# ── PACKAGE LIBRARY -- real outlines, (X, Y, Z) AS PLACED ────────────────────
# Body + leads where leads protrude, at JEDEC/IPC MAX, so the model is the worst case an
# assembler can hand us rather than a nominal that a real part exceeds.
PKG = {
    "0402":     (1.00, 0.50, 0.55),   # 1005 metric; 0.55 is MLCC max
    "0603":     (1.60, 0.80, 0.95),   # 1608 metric
    "0805C":    (2.00, 1.25, 1.45),   # 2012 metric MLCC
    "0805OPT":  (2.00, 1.25, 0.85),   # optoelectronic 0805
    "SOT-23":   (2.90, 2.40, 1.30),
    "SOT-23-5": (2.90, 2.80, 1.45),
    "SOT-563":  (1.60, 1.60, 0.60),
    # U8's digital rail is ~300 mA, so 5V->3V3 burns 0.51 W. That is past a SOT-23-5
    # (>100 degC rise), which is why U8 is NOT the same part as U9. A BUCK was the obvious
    # answer and is the wrong one here: this board reads tens of nanoamps on 20 TIAs, and
    # putting a ~1 MHz switcher next to them trades a thermal problem for a noise problem
    # on the axis the design is most sensitive to. A tab package sheds the heat instead --
    # SOT-223 is ~50 degC/W with a copper pour, i.e. ~25 degC rise, and the board stays
    # switcher-free. 1.7 V of headroom against AMS1117's 1.3 V max dropout.
    "SOT-223":  (6.50, 3.50, 1.80),   # tab package, JEDEC TO-261AA
    "SOIC-14":  (6.00, 8.65, 1.75),   # LONG AXIS ALONG Y: 8.65 body, 6.00 across leads.
                                      # Chosen over TSSOP-14 purely for X: 6.00 across
                                      # the leads against TSSOP's 6.40, and X is the
                                      # scarce direction in a 14 mm band.
    "QFN-24":   (4.00, 4.00, 0.90),
    "TSSOP-16": (6.40, 5.00, 1.20),   # 4.40 body + leads; PCM1808 audio ADC
    # LQFP144, not 100: the LQFP100 STM32H743VIT6 exposes only 16 ADC channels and this
    # board needs 20. The 144 (STM32H743ZIT6) has exactly 20, and at ~$7.63 on LCSC it is
    # CHEAPER than the 100-pin part. 22x22 over leads fits the 30 mm tail with 2.8 spare.
    "LQFP144":  (22.00, 22.00, 1.60), # JEDEC MS-026: 20x20 body, 22x22 over leads
    "3225":     (3.20, 2.50, 0.90),
    "USB-C":    (8.94, 7.35, 3.16),   # TYPE-C-31-M-12 (LCSC C165948)
    # J2 is a SIX-way on the -Y EDGE, mouth facing -Y alongside the USB-C, so every cable
    # leaves the board at one end (user: a -X exit is unmanageable). Six ways because the
    # magnetic pickup's buffered audio tap arrives here too and MUST bring its own return:
    # 2x 5V, 2x PWR_GND, AUDIO, AUDIO_GND.
    #
    # Note there is no S2B -- JST's SMT side-entry XH line starts at 4 way -- and the 6 way
    # costs nothing on the harness side, because XHP-6 housings are ALREADY bought to mate
    # the ten SERVO42D pigtails and SXH-001T contacts are common to every XH size. The only
    # new line is the board-side part itself.
    #
    # ORIENTED FOR A -Y MOUNT: 20.0 runs along X (the edge), 6.10 is the body's reach into
    # the board in Y. The 4-way entry it replaces was (6.10, 15.00, 7.00) for a -X mount.
    # 20.0 is DERIVED from XH's 2.5 pitch (4 way B = 15.0, +2 ways) -- CONFIRM against JST's
    # drawing before layout, exactly as the S4B figures were.
    "XH-SM-6Y": (20.00, 6.10, 7.00),  # JST S6B-XH-SM4-TB (C191914), SMT side entry, -Y
}
LED_PKG = PKG["0805OPT"]
PD_PKG  = PKG["0805OPT"]
PKG_CLR = 0.25                                   # least placement gap between packages
EDGE_KEEP = 1.2                                  # part -> board edge: JLCPCB's 1.0 rule
                                                 # + their 0.2 routed-outline tolerance
ROW_GAP   = 1.0

# ── Z STACK, built UPWARD from the deck ─────────────────────────────────────
# Datum is the LOWEST string underside. Centres are coplanar (verified), so the THICKEST
# string hangs lowest and is the one that sets the standoff; every thinner string simply
# gets more gap. (The overhead version had the mirror-image of this bug: it referenced
# D.STRING_Z, the centre line, and silently gave the thickest string 2.11 of the intended
# 3.0.)
STRING_BOT_MIN = D.STRING_Z - max(D.STRING_GAUGE) / 2         # 15.111
SENSE_FACE_Z   = STRING_BOT_MIN - OPT_GAP                     # 12.111, emitter faces UP
PCB_TOP        = SENSE_FACE_Z - LED_PKG[2]                    # 11.261
PCB_BOT        = PCB_TOP - PCB_T                              # 9.661, NOMINAL board underside
# THE PLINTH IS DATUMED OFF THE WORST-CASE BOARD, NOT THE NOMINAL ONE. The printed plinth
# is a fixed surface; the board thickness is not. Referencing the plinth to PCB_BOT (the
# nominal) means a board at the +10% limit carries its components 0.16 HIGHER than modelled
# and the 0.30 roof gap it must slide through drops to 0.14 -- a clearance the model would
# have declared fine while the real assembly bound. Referencing PCB_T_MAX instead makes the
# tolerance one-sided in the direction that is harmless: a thin board simply sits low and
# OPENS the optical gap (signal is linear in standoff, and per-string gain trims it), while
# clearance can only ever be at least what was designed. Trading a benign ~0.45 dB against a
# mechanical interference is the right way round.
PLINTH_TOP     = PCB_TOP - PCB_T_MAX                          # 9.501, what the endplate builds to
STANDOFF       = PLINTH_TOP - DECK_TOP                        # 3.501 under the board
# Anything over the sensing field must still clear the strings. The quad op-amps (1.75)
# are the deep ones out there; this is the floor on what is left above them.
PART_STRING_CLR = 1.5

# ── COVER -- the lid that makes up-firing viable ────────────────────────────
# Sits in the optical gap over the sensor row only. Three jobs: an APERTURE (each string
# gets its own slot, so the shallow-angle ambient path is cut), a DEBRIS LID (up-firing
# optics collect what down-firing ones shed), and physical protection during stringing.
# It is honest about its limits: at this standoff a slot cannot collimate much -- the
# geometric rejection is a few dB, and the heavy lifting against sun is an IR-pass
# window (see BOM.md). What it definitely buys is the -X wall and the debris seal.
COVER_GAP = 0.3                                  # sensor face -> cover underside
COVER_T   = 1.6                                  # two-bead floor for added material
COVER_Z0  = SENSE_FACE_Z + COVER_GAP             # 12.411
COVER_Z1  = COVER_Z0 + COVER_T                   # 14.011
SLOT_DX   = 3.0                                  # aperture over the triplet, in X
SLOT_DY   = 5.0                                  # ...and in Y (triplet spans +-2.225)
# The lid covers the OPTICS ONLY -- the sensor row's X band and the sensing field's Y
# span. It deliberately stops short of the quad op-amps, which stand 1.75 above the board
# (higher than the roof) and need no protection. COVER_X0/COVER_HY are module-level so
# the clearance assertions test the same volume the solid occupies.


def string_y_at(i: int, x: float) -> float:
    """String i's Y at X, on the linear nut->changer fan. The sensors sit on THESE, not
    on a uniform pitch -- which is the whole argument for a custom PCB over an array."""
    t = (x - D.NUT_BLOCK_X) / (D.BRIDGE_X - D.NUT_BLOCK_X)
    return D.nut_y(i) + (D.string_y(i) - D.nut_y(i)) * t


PITCH = abs(string_y_at(1, SENSE_X) - string_y_at(0, SENSE_X))
PD_DY = 1.6                                      # detector offset either side of the
                                                 # string; scaled to the SHORT standoff
END_KEEP = 2.0

_OUTER_Y = max(abs(string_y_at(i, SENSE_X)) for i in range(D.N_STRINGS))
SENSE_HL = _OUTER_Y + PD_DY                      # last sensor Y

# ── BOARD OUTLINE -- narrow sensing strip + a wide tail past the cavity ─────
# The strip is capped by the 14 mm band. The digital block cannot live in 14 mm (the MCU
# alone is 16 over its leads), so the board widens in the -Y room PAST the pickup
# cavity's -Y edge, where the deck is solid again and nothing is overhead.
PCB_X0  = BAND_X0 - BAND_CLR                                  # -16.80, strip +X edge
PCB_X1S = BAND_X1 + BAND_CLR                                  # -30.42, strip -X edge
# Both wraps turn +X at the SAME distance past the bearing arms. Y_TAIL used to be derived
# from the magnetic pickup's CAVITY, which was correct while the tail widened -X over the
# deck and had to clear it -- but the tail widens +X over the ENDPLATE now, so the cavity
# stopped governing this and the leftover left -Y 1.05 slacker than +Y (user spotted the
# asymmetry in the render). One constant, mirrored.
WRAP_CLR = 0.75                                               # past the arm outer face
Y_TAIL   = -(D.BRIDGE_AXLE_Y + D.BRIDGE_ARM_W / 2 + WRAP_CLR)  # -55.00
# TAIL WIDENS +X, OVER THE ENDPLATE -- not -X over the deck (user). Two things fall out
# and both were open problems:
#   SUPPORT. Past |y| 54 the endplate has no material above z6 for a plinth to start on,
#     which is why the tail had nothing under it. But out here it has the FILL SLAB, whose
#     top IS z6 -- so a plinth over the endplate merges straight into solid material and
#     needs no deck standoffs, i.e. no top_plate change at all.
#   THE DECK STAYS CLEAR. The tail no longer lies across the deck panel.
# +X edge stops MIN_WALL_2P short of the endplate's outer face so the board is not flush
# with the instrument's exterior.
TAIL_X1 = D.BRIDGE_BASE_X1 - D.MIN_WALL_2P                    # 7.00
# -X edge runs out to the STRIP's own -X edge. Sized off the LQFP144 instead (-18.40) the
# two sections overlapped by just 1.60 in X, so the whole board hung on a 1.6 mm waist:
# brittle, and hopeless for routing -- 20 analog channels + 10 LED drives + power all have
# to cross it to reach the MCU. Full width makes it a smooth transition rather than a neck.
# The -X part of the tail overhangs the plinth (which stops at the endplate face) by 13.8,
# but that is 1.6 FR4 over open air 3.7 above the deck, not a load path.
PCB_X1T = PCB_X1S                                             # -30.42
# +Y HEAD -- the tail's mirror image (user). The board turns +X over the endplate at BOTH
# Y ends, so it grips the instrument at two widely spaced points and its position becomes
# a fixed, screwed thing rather than something that has to be eyeballed. That matters more
# than it used to: the light cover is now part of the endplate, so the board's Y position
# is what lines its apertures up with the sensor triplets.
# HEAD_Y0 clears the bearing arms (outer face +-54.25) before turning +X -- inboard of that
# the comb brace occupies the same X band and the same Z.
HEAD_Y0 = -Y_TAIL                                             # 55.00, mirrored
# -X edge of the endplate's wrap plinths. The board overhangs it, so this -- not the board
# outline -- is what limits how far -X the M4 grips can go.
PLINTH_X0 = BAND_X0                                           # -16.60
# The -Y side MIRRORS the head (user): the same Y length of full-width board, wrapping +X
# over the endplate, and THAT band is the strip's structural and routing connection to the
# compute block. Symmetric spans in X at both ends.
# Below it the compute section pulls its -X edge back in -- everything -X of the MCU down
# there was board doing no work, hanging over the deck.
# +Y end sits FLUSH with the endplate's existing +Y extent (user): the head no longer sets
# how far the endplate reaches. Affordable because the M4 grip moved inboard -- it needs
# MIN_WALL_2P + pilot/2 = 4.60 to this edge and has 5.15.
PCB_YP     = CH.Y_HI + CH.T / 2                               # 64.75, the rail outer face
HEAD_LEN   = PCB_YP - HEAD_Y0                                 # 9.75, mirrored at -Y
WRAP_Y     = Y_TAIL - HEAD_LEN                                # -65.80, compute starts here
# COMPUTE SECTION WIDTH is set by the -Y EDGE, not by the MCU any more. Every cable now
# leaves at -Y (user: a -X exit cannot be routed cleanly), so that edge has to carry the
# USB-C AND the 6-way XH side by side, and THAT is the binding dimension -- the LQFP144
# only needs 24.4 of the 32.34 this produces. Derived, not typed, so it tracks either
# connector's envelope; the assertion below re-checks the MCU still fits.
#
# The widening is FREE in billed area: the SENSING STRIP already sets the bounding box's
# -X extreme at PCB_X1S (-30.42), and this lands at -25.34, inside it. There is 5.08 mm of
# further headroom before the bbox -- and therefore the fab charge -- would move at all.
COMPUTE_W  = (2 * EDGE_KEEP + PKG["USB-C"][0] + ROW_GAP + PKG["XH-SM-6Y"][0])
COMPUTE_X0 = TAIL_X1 - COMPUTE_W                              # -25.34
# PCB_YP is an OUTPUT, set after the parts exist: the +Y-most quad's feedback grid sits
# in the Y gap above it and reaches past the last detector, so sizing this end from the
# sensing field alone ran parts off the board.


def section_at(y: float):
    """(x1, x0) = the board's -X and +X edges at Y. Three sections: the +X HEAD, the narrow
    sensing STRIP that has to stay inside the deck band, and the +X TAIL."""
    for y0, y1, x1, x0 in _SECTIONS:
        if y0 - 1e-9 <= y <= y1 + 1e-9:
            return x1, x0
    return PCB_X1S, PCB_X0


# ── ANALOG FIELD -- everything fits in the band, which is the point ─────────
# Column order is set by what each part loses to distance. The sensor row takes the +X
# end (closest to the termination it is allowed to be); the quad op-amps sit immediately
# -X of it so the summing node is a few mm long; the feedback R/C and the LED ballast
# fill the Y GAPS rather than taking their own columns, because there is no X left.
PART_KEEP = 2.0                                               # sensor row -> anything else
ROW_X0    = SENSE_X - LED_PKG[0] / 2                          # the row's -X edge, -20.50
COL_OPA   = ROW_X0 - PART_KEEP - PKG["SOIC-14"][0] / 2        # -25.50
COVER_X0  = COL_OPA + PKG["SOIC-14"][0] / 2 + 0.5             # lid's -X edge, -22.00
# Lid Y half-span, sized off the OUTERMOST APERTURE rather than the sensing field: the
# slot is wider than the triplet it serves (SLOT_DY 5.0 against 4.45 of packages), so
# referencing SENSE_HL left only 0.1 of material outboard of the last slot -- a knife edge
# (user-caught). Two full beads past the aperture instead.
COVER_HY  = _OUTER_Y + SLOT_DY / 2 + D.MIN_WALL_2P
FB_PITCH, FB_ROWS = 2.0, (5.6, 6.8, 8.0, 9.2)                 # 0402 grid in the Y gaps


def _spread(out, y, items, x0, x1):
    widths = [PKG[p][0] for _, _, p in items]
    gap = ((x1 - x0) - sum(widths)) / max(len(items) - 1, 1)
    cx = x0
    for (ref, desc, pkg), w in zip(items, widths):
        out.append({"ref": ref, "desc": desc, "pkg": pkg, "x": cx + w / 2, "y": y})
        cx += w + gap


def _block(out, y, items, x0, x1):
    """Pack parts into as many rows as they NEED, marching -Y from y; return the -Y edge.
    Rows are packed, not hand-assigned: hand-tuned rows went under the placement
    clearance every time a part was added, and the board length has to be an OUTPUT of
    the part list rather than a number parts get squeezed into."""
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
    """EVERY component on the strip, with its package and placed centre. ONE source of
    truth for the 3D model, the area budget, the clearance assertions and BOM.md."""
    P = []

    def add(ref, desc, pkg, x, y):
        P.append({"ref": ref, "desc": desc, "pkg": pkg, "x": x, "y": y})

    # ---- 1. sensing row, ON THE STRING FAN, + per-string ballast in the Y gaps ----
    for i in range(D.N_STRINGS):
        n, sy = i + 1, string_y_at(i, SENSE_X)
        add("D%d" % n, "IR emitter, 940 nm, Everlight IR17-21C (~120 deg -- see note)", "0805OPT", SENSE_X, sy)
        add("PD%dA" % n, "PIN photodiode, Vishay VEMD4110X01 (daylight filter), +Y", "0805OPT", SENSE_X, sy + PD_DY)
        add("PD%dB" % n, "PIN photodiode, Vishay VEMD4110X01 (daylight filter), -Y", "0805OPT", SENSE_X, sy - PD_DY)
        # ballast rides in the gap just -Y of its own emitter, same X band: no column to
        # spare, and it keeps the high-di/dt emitter loop a couple of mm long
        add("R%d" % n, "LED current-set (per-string value)", "0603", SENSE_X, sy - PITCH / 2)

    # ---- 2. the 20 TIAs: one QUAD per string PAIR, at that pair's centroid ----
    for q in range(D.N_STRINGS // 2):
        cy = (string_y_at(2 * q, SENSE_X) + string_y_at(2 * q + 1, SENSE_X)) / 2
        add("U%d" % (q + 1), "quad op-amp -- 4x transimpedance amp", "SOIC-14", COL_OPA, cy)
        # feedback R/C + local decoupling go in the Y GAP next to their quad, at the same
        # X -- the band has no room for a column of its own
        items = ([("Rf%d%d" % (q + 1, k + 1), "TIA feedback resistor (per-string value)")
                  for k in range(4)]
                 + [("Cf%d%d" % (q + 1, k + 1), "TIA feedback cap (anti-alias pole)")
                    for k in range(4)]
                 + [("Cd%d%d" % (q + 1, k + 1), "op-amp decoupling") for k in range(2)])
        s = -1 if q == D.N_STRINGS // 2 - 1 else 1        # last quad uses the gap below
        slots = [(COL_OPA + (c - 1) * FB_PITCH, cy + s * r) for r in FB_ROWS
                 for c in range(3)]
        for (ref, desc), (px, py) in zip(items, slots):
            add(ref, desc, "0402", px, py)

    # ---- 3. digital block, in the wide tail past the pickup cavity ----
    x0, x1 = COMPUTE_X0 + EDGE_KEEP, TAIL_X1 - EDGE_KEEP
    # THE MCU CLIMBS INTO THE WRAP BAND (user). It used to start below WRAP_Y, clear of the
    # seam, which cost ~9.75 mm of board on the -Y end for nothing: the wrap band is WIDER
    # in X than the compute section, and the only thing in it is the tail screw. Tucking the
    # LQFP144 hard -X and moving that screw hard +X lets the two share the band, and every
    # row below inherits the saving. The board's -Y end is a cantilever, so length taken off
    # here is worth more than the same length taken off anywhere else.
    y = Y_TAIL - ROW_GAP
    y -= PKG["LQFP144"][1] / 2
    add("U6", "MCU -- STM32H743ZIT6, 20x 16-bit ADC ch, USB OTG_HS via ULPI", "LQFP144",
        x0 + PKG["LQFP144"][0] / 2, y)                 # hard -X, against the edge keep-out
    y -= PKG["LQFP144"][1] / 2 + ROW_GAP

    # POWER + AUDIO INPUT is no longer here -- J2 moved to the -Y EDGE, beside the USB-C,
    # so both cables leave the board at the same end (see the placement after this block).
    # Its decoupling stays in the digital block, near where the rail is consumed.
    _spread(P, y - 0.5, [("C%d" % (140 + k), "power-input decoupling", "0402")
                         for k in range(4)], x0, x1)
    y -= 1.0 + ROW_GAP

    y = _block(P, y, [("C%d" % (100 + k), "MCU decoupling", "0402") for k in range(12)]
                     + [("R30", "BOOT0 pull-down", "0402"),
                        ("R31", "NRST pull-up", "0402")], x0, x1)
    # PHY between the MCU and the connector -- it owns both ends: 12 ULPI signals up to
    # the MCU, D+/D- down to the port.
    y = _block(P, y, [("Y1", "25 MHz crystal -- MCU HSE", "3225"),
                      ("U7", "USB 2.0 high-speed ULPI PHY", "QFN-24"),
                      ("Y2", "24 MHz crystal -- PHY reference", "3225")]
                     + [("C%d" % (120 + k), "PHY decoupling", "0402") for k in range(3)]
                     + [("C%d" % (123 + k), "crystal load cap", "0402") for k in range(4)],
               x0, x1)
    # U11 is the mid-rail reference the 20 TIAs sit on: single-supply transimpedance needs
    # a bias for the non-inverting inputs, and all 20 quad channels are spoken for.
    y = _block(P, y, [("U8", "LDO -- 3V3 digital, TAB package (0.51 W)", "SOT-223"),
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
                      ("R36", "LED driver gate resistor", "0402")], x0, x1)

    # ---- 3b. MAGNETIC PICKUP CHANNEL -- its own ADC, deliberately NOT the MCU's ----
    # The magnetic pickup reaches the Pi by being digitised HERE and sent over the USB link
    # this board already has, instead of running a second analog cable the length of the
    # instrument. Digitising early is the whole point: once it is bits, the Pi's ground
    # noise has no analog path back.
    #
    # It does NOT share the MCU's SAR ADC, for two independent reasons:
    #   CROSSTALK, which is the real one. That ADC is multiplexed across 20 inputs reading
    #     TENS OF NANOAMPS. The magnetic signal is line level -- four to five orders of
    #     magnitude louder. Putting it through the same sample-and-hold mux as the
    #     photodiode channels invites exactly the contamination this board is organised to
    #     prevent, and no layout care downstream can undo it.
    #   PIN COUNT. All 20 of the LQFP144's ADC channels are already spoken for, one per
    #     photodiode. There is no 21st.
    # A dedicated codec sidesteps both and is better on its own merits: 24-bit delta-sigma
    # at ~99 dB SNR against a 16-bit SAR shared twenty ways, on the signal a listener
    # actually hears. It arrives over I2S/SAI -- a peripheral, not an ADC pin.
    #
    # Placed at the -Y end, next to J2 where the audio lands, so the analog input is short
    # and stays away from the emitter driver's 96 kHz switching.
    y = _block(P, y, [("U12", "audio ADC -- PCM1808, magnetic pickup -> I2S", "TSSOP-16"),
                      ("C150", "ADC analog supply bypass", "0805C"),
                      ("C151", "ADC digital supply bypass", "0402"),
                      ("C152", "ADC VREF bypass", "0805C"),
                      ("C153", "audio input DC block", "0805C"),
                      ("R37", "audio input series / anti-alias", "0402"),
                      ("R38", "audio input bias to mid-rail", "0402")], x0, x1)

    # ---- 4. the -Y EDGE: every cable leaves the board here ----
    # Both mouths face -Y and their outer faces are FLUSH, so the two plugs present as one
    # cable exit rather than two at different depths. J1 sets PCB_YM; J2 is referenced to
    # the same face so a deeper or shallower connector cannot silently step one of them.
    y -= PKG["USB-C"][1] / 2
    add("J1", "USB-C receptacle -- 10ch audio + MIDI + DFU", "USB-C",
        COMPUTE_X0 + EDGE_KEEP + PKG["USB-C"][0] / 2, y)
    edge_y = y - PKG["USB-C"][1] / 2                      # the board's -Y face
    # J2 -- POWER *AND* the magnetic pickup's audio tap. 5V from the instrument rail, NOT
    # USB VBUS: MCU ~200-300 mA + PHY ~50 + 21 op-amp channels ~40 is already past a USB
    # port before an emitter is lit, and LED current is now the FIRST SNR lever we have.
    # AUDIO_GND is a dedicated pin, not shared with PWR_GND and emphatically not with USB
    # ground: the LED row driver switches at 96 kHz SYNCHRONOUSLY WITH SAMPLING and that
    # current flows in the power return, so sharing it would inject the one noise source
    # ambient subtraction cannot cancel straight into the audio reference.
    add("J2", "power 5V + magnetic audio tap -- 2x5V, 2x PWR_GND, AUDIO, AUDIO_GND",
        "XH-SM-6Y",
        COMPUTE_X0 + EDGE_KEEP + PKG["USB-C"][0] + ROW_GAP + PKG["XH-SM-6Y"][0] / 2,
        edge_y + PKG["XH-SM-6Y"][1] / 2)
    return P


PARTS = _parts()


# ── ORDERABILITY: every placed part -> a real LCSC/JLCPCB line ──────────────────────
# PARTS above is a MODEL: description + package envelope, which is all the geometry and
# the clearance assertions need. It is NOT orderable -- you cannot put "quad op-amp" on a
# JLCPCB BOM line. This table closes that gap, and `_assert_every_part_orderable()` makes
# the gap impossible to reopen silently: add a part above without a rule here and the
# build fails.
#
# Prices are LCSC qty-1 unless noted, checked 2026-08-01. "BASIC" = JLCPCB Basic part
# (no per-order feeder charge); everything else is Extended, at ~$1.50/unique part/order.
MPN_UNKNOWN = "OPEN"        # deliberately unresolved -- see BOM.md, blocks ordering

# ref-prefix -> (mpn, lcsc, unit_usd, note). Longest prefix wins, so "PD" beats "P".
_MPN_RULES = (
    # --- resolved, verified in LCSC stock 2026-08-01 ---
    ("U6",   ("STM32H743ZIT6",   "C114408",  9.93,  "LQFP144; 20 ADC ch. @10 price. "
                                                    "STOCK 7 -- short for a run of 10")),
    ("U7",   ("USB3343-CP",      "C633347",  1.78,  "ULPI HS PHY, QFN-24. -TR reel = C112967 @2.07")),
    ("U10",  ("USBLC6-2SC6",     "C7519",    0.0983, "USB ESD array. NOTE SOT-23-6, not the "
                                                    "modelled SOT-563 -- envelope grows")),
    ("U11",  ("TLV9061IDCKR",    "C693480",  0.36,  "single of the same family as U1-U5, "
                                                    "so the mid-rail buffer matches the TIAs")),
    ("U12",  ("PCM1808PWR",      "C55513",   0.3419, "24-bit 99 dB 96 kHz stereo audio ADC, "
                                                    "I2S. Keeps the line-level magnetic "
                                                    "signal OFF the MCU's nanoamp SAR mux. "
                                                    "8.2k in LCSC stock")),
    ("U8",   ("AMS1117-3.3",     "C6186",    0.1045, "3V3 DIGITAL, SOT-223 tab -- 0.51 W will "
                                                    "not fit a SOT-23-5. Noisy, but it feeds "
                                                    "the MCU, not the front end")),
    ("U9",   ("SPX3819M5-L-3-3/TR", "C9055", 0.30,  "3V3 ANALOG, 40 uVrms, SOT-23-5. Low load "
                                                    "(~40 mA) so the small package is fine")),
    ("U",    ("TLV9064IDR",      "C388176",  0.2161, "quad op-amp, SOIC-14, 10 MHz GBW, "
                                                    "500 fA Ib -- the TIA part. 10k in stock")),
    ("Y",    ("X322525MSB4SI",   "C13740",   0.0334, "25 MHz 3225 crystal, BASIC. Y2 needs the "
                                                    "PHY's reference freq -- confirm vs USB3343")),
    ("Q1",   ("AO3400A",         "C20917",   0.0487, "N-ch logic-level FET, SOT-23, LED row gate")),
    ("J1",   ("TYPE-C-31-M-12",  "C165948",  0.20,  "USB-C 16P; the modelled envelope IS this part")),
    ("FB1",  ("GZ2012D601TF",    "C1017",    0.02,  "0603 ferrite bead, 600R@100MHz, BASIC class")),
    # --- generic passives: JLCPCB BASIC classes, exact value set at schematic capture ---
    ("Rf",   ("0402 thick-film R", "BASIC",  0.002, "TIA feedback, per-string value")),
    ("Cf",   ("0402 C0G MLCC",   "BASIC",    0.004, "TIA feedback cap -- C0G, not X7R: the "
                                                    "anti-alias pole must not drift with bias")),
    ("Cd",   ("0402 X7R MLCC",   "BASIC",    0.002, "op-amp decoupling")),
    ("C1",   ("0402 X7R MLCC",   "BASIC",    0.002, "decoupling / crystal load (load caps C0G)")),
    ("C13",  ("0805 X7R MLCC",   "BASIC",    0.01,  "bulk")),
    ("C14",  ("0402 X7R MLCC",   "BASIC",    0.002, "power-input decoupling")),
    ("R",    ("0603 thick-film R", "BASIC",  0.003, "per-string LED ballast")),
    # --- OPEN: see BOM.md. These three block ordering. ---
    # RESOLVED. The emitter is 0805 940 nm and WIDE (~120 deg full) because narrow-beam
    # simply is not made in this package -- see the note below and BOM.md. Angle is the one
    # spec to re-confirm on the datasheet at layout; everything else is checked.
    ("D",    ("IR17-21C/TR8",    "C131250",  0.0283, "IR emitter 940 nm, 0805, Everlight. "
                                                    "~120 deg full angle -- lever 1 of the "
                                                    "signal budget is UNAVAILABLE, not merely "
                                                    "unchosen. CONFIRM angle at layout")),
    # RESOLVED, and the no-consignment dilemma was a false alarm: the LCSC-stocked X01
    # CARRIES THE SAME DAYLIGHT FILTER (740-1040 nm, matched to 830-950 nm emitters),
    # same 0.42 mm2 area, same 0805 2.0x1.25x0.7. It is a drop-in for the absent X02.
    ("PD",   ("VEMD4110X01",     "C3211080", 0.58,  "filtered Si PIN, 0.42 mm2, +-55 deg. "
                                                    "@100+ price; 10 boards = 200 pcs. "
                                                    "STOCK 72 -- must recover or be pre-ordered")),
    ("J2",   ("S6B-XH-SM4-TB",   "C191914",  0.4417, "6 way on the -Y edge: 2x5V, 2x PWR_GND, "
                                                    "AUDIO, AUDIO_GND. Only new line here is "
                                                    "the board-side part -- XHP-6 housings are "
                                                    "already bought for the SERVO42D pigtails "
                                                    "and SXH-001T contacts are common to all XH")),
)


# EXACT refs, checked before the prefix rules. These exist because reference designators
# are NOT a clean namespace: the string-3 LED ballast is "R3" and the BOOT0 pull-down is
# "R30", so any prefix rule for the R3x group silently swallows a ballast and quietly
# reassigns it from 0603 to 0402. That is exactly the class of stale-derivation bug this
# file guards against elsewhere -- it evaluates fine and is simply wrong -- so the
# ambiguous group is spelled out instead of pattern-matched.
_MPN_EXACT = {r: ("0402 thick-film R", "BASIC", 0.002, "pulls / divider / gate")
              for r in ("R30", "R31", "R32", "R33", "R34", "R35", "R36", "R37", "R38")}
# The audio-ADC bulk/bypass caps are 0805, but "C150".startswith("C1") would file them
# under the 0402 line -- the same namespace collision as R3 vs R30. Spelled out.
_MPN_EXACT.update({r: ("0805 X7R MLCC", "BASIC", 0.01, "audio ADC bypass / DC block")
                   for r in ("C150", "C152", "C153")})


def mpn(p):
    """The orderable line for a placed part. Exact ref wins; else longest prefix."""
    if p["ref"] in _MPN_EXACT:
        return _MPN_EXACT[p["ref"]]
    best = None
    for pre, rec in _MPN_RULES:
        if p["ref"].startswith(pre) and (best is None or len(pre) > len(best[0])):
            best = (pre, rec)
    if best is None:
        raise KeyError("no MPN rule for %s (%s)" % (p["ref"], p["desc"]))
    return best[1]


def _assert_every_part_orderable():
    """Nothing may be placed on this board without a sourcing decision attached -- even if
    that decision is an explicit OPEN. Silence is the failure mode this prevents.

    AND the decision has to MATCH the part. The first version of this guard only checked
    that a rule existed, which let two real mismatches through unnoticed: R37/R38 are 0402
    in the model but fell to the 0603 ballast rule, and C150/C152/C153 are 0805 but fell to
    the 0402 rule. Both would have shipped a BOM line that disagreed with the footprint --
    the exact "it evaluates fine and is simply wrong" failure this file guards against
    elsewhere. Generic passive lines name their package first in the description, so the
    two can be cross-checked rather than trusted."""
    for p in PARTS:
        rec = mpn(p)                             # raises if unmapped
        if rec[1] == "BASIC":                    # a generic passive class, e.g. "0402 X7R MLCC"
            want = rec[0].split()[0]
            if not p["pkg"].startswith(want):
                raise AssertionError(
                    f"optical strip: {p['ref']} is package {p['pkg']} but its BOM line is "
                    f"'{rec[0]}' -- the sourcing rule does not match the footprint")
    return sorted({mpn(p)[0] for p in PARTS if mpn(p)[0] != MPN_UNKNOWN})


def open_lines():
    """The refs still blocking a preassembled order."""
    return sorted({p["ref"][:2].rstrip("0123456789") or p["ref"]
                   for p in PARTS if mpn(p)[0] == MPN_UNKNOWN})


def parts_cost():
    """Board parts cost from the table -- so BOM.md's figure cannot drift from the model."""
    return sum(mpn(p)[2] for p in PARTS)


_assert_every_part_orderable()


def part(ref):
    for p in PARTS:
        if p["ref"] == ref:
            return p
    raise KeyError(ref)


def part_span(p):
    dx, dy, _ = PKG[p["pkg"]]
    return (p["x"] - dx / 2, p["x"] + dx / 2, p["y"] - dy / 2, p["y"] + dy / 2)


PCB_YM = part("J1")["y"] - PKG["USB-C"][1] / 2   # -Y end = the connector mouth
PCB_L  = PCB_YP - PCB_YM
_SECTIONS = ((HEAD_Y0, PCB_YP, PCB_X1S, TAIL_X1),      # +Y wrap, over the endplate
             (Y_TAIL, HEAD_Y0, PCB_X1S, PCB_X0),       # sensing strip, in the deck band
             (WRAP_Y, Y_TAIL, PCB_X1S, TAIL_X1),       # -Y wrap -- the head's mirror
             (PCB_YM, WRAP_Y, COMPUTE_X0, TAIL_X1))    # compute, no -X overhang


def mount_points():
    """The two M4 grips, one in each +X wrap -- same fastener as the pickup height jacks.
    Widely spaced on purpose: they are the board's Y datum, and the integrated lid's slots
    have to land on the sensor triplets."""
    # Both are pushed as far INBOARD in Y as the material allows (user), to sit as close as
    # possible to the position-critical end of the board. The binding surface is the WRAP
    # PLINTH, not the board: the board is wider than the plinth at both ends, so the insert
    # boss is what runs out of material first. MIN_WALL_2P of plinth all round.
    #
    # THEY ARE NOT AT THE SAME X, and that asymmetry is deliberate (user). The HEAD screw
    # stays hard -X, closest to the sensor row. The TAIL screw is pushed hard +X instead, to
    # get out of the MCU's way: that lets the LQFP144 tuck -X and climb +Y INTO the wrap
    # band rather than starting below it, which takes ~9.75 mm off the board's -Y end -- the
    # end that is already a cantilever. Both still land in the plinth, which is the only
    # hard requirement. The two screws still define the Y datum; a skewed line between them
    # locates the board just as well as a parallel one.
    keep = D.MIN_WALL_2P + M4.insert_pilot_d / 2
    return [(PLINTH_X0 + keep, HEAD_Y0 + keep),        # -12.00, hard -X
            (TAIL_X1 - keep, Y_TAIL - keep)]           # +2.40, hard +X


# ROUTED-OUTLINE FILLETS. A PCB outline is CNC-ROUTED, not cut from plate, so any polygon
# is fine -- but the mill cannot cut a sharp INTERNAL corner. Every concave corner comes
# out with the cutter's radius whether it is drawn or not, so it is drawn: the model was
# optimistic by ROUT_R at three places. External corners stay sharp (the mill goes round
# the outside of those).
ROUT_R = 1.0                                   # ~2 mm router bit


def _concave():
    """The three internal corners, where a section steps NARROWER than its neighbour."""
    return [(PCB_X0, HEAD_Y0),                 # head -> strip, +X side
            (PCB_X0, Y_TAIL),                  # strip -> -Y wrap, +X side
            (COMPUTE_X0, WRAP_Y)]              # -Y wrap -> compute, -X side


def _outline(grow=0.0, t=None, zc=None):
    """The board's footprint as a solid: narrow sensing strip over the strings, wide tail
    past the pickup cavity. `grow` inflates it for a slip fit."""
    t = PCB_T if t is None else t
    zc = PCB_BOT + PCB_T / 2 if zc is None else zc
    out = None
    for y0, y1, x1, x0 in _SECTIONS:
        # only the OUTER Y face of each section grows: the seam at Y_TAIL must not, or
        # the halves overlap by 2*grow and the step moves
        a = y0 - grow if y0 != Y_TAIL else y0
        b = y1 + grow if y1 != Y_TAIL else y1
        blk = box_at((x0 + grow) - (x1 - grow), b - a, t,
                     x=((x0 + grow) + (x1 - grow)) / 2, y=(a + b) / 2, z=zc)
        out = blk if out is None else out.union(blk)
    for fx, fy in _concave():
        out = out.edges(NearestToPointSelector((fx, fy, zc))).fillet(ROUT_R + grow)
    return out


def _part_solid(p):
    """Package standing UP from the board's top face (single-sided, components at the
    strings)."""
    dx, dy, dz = PKG[p["pkg"]]
    return box_at(dx, dy, dz, x=p["x"], y=p["y"], z=PCB_TOP + dz / 2)


def opt_pcb() -> cq.Workplane:
    """The assembled optical strip: FR4 + EVERY placed component at its true Z, all
    facing UP. Fab/purchased -> NO standalone STEP (cadkit convention); it exists in the
    assembly as the fit-check that it clears the strings and fits the carrier."""
    pcb = _outline()
    for p in PARTS:
        pcb = pcb.union(_part_solid(p))
    for mx, my in mount_points():                     # M4 clearance, one per +X wrap
        pcb = pcb.cut(box_at(M4.shaft_clr_d, M4.shaft_clr_d, PCB_T + 2,
                             x=mx, y=my, z=PCB_BOT + PCB_T / 2))
    return pcb


# APERTURE PLAN SHAPE -- an open-ended NOTCH, and the two shapes it is not.
#
# The endplate builds +X -> -X, so each layer is a Y-Z slice and anything it adds must sit
# within 45 deg of the layer at +X of it.
#
#   * A CLOSED rectangular slot fails that at its -X end: the roof resumes across the full
#     SLOT_DY x COVER_T face over void, anchored only at its two Y edges. That is a 5.0 mm
#     bridge directly over the optics, where sag lands in the aperture.
#   * A 45 deg V ("/\") closing the -X end fixes the bridge -- the void must close in Y, not
#     Z, since Z is in-plane for these layers and tapering thickness only thins the bridge --
#     but IT DOES NOT FIT. The apex needs SLOT_DY/2 = 2.50 of X measured from the packages'
#     -X edge at -20.50, landing at -23.00, and the roof stops at COVER_X0 = -22.00 because
#     the quad op-amps stand taller than the roof underside. Truncated there, the flank
#     crosses the roof's -X boundary at 45 deg and leaves an acute WEDGE of roof material
#     tapering 1.50 -> 0.00: a knife edge, measured, and under the 1.6 floor for its whole
#     length. Both failures were caught by the user from renders.
#
# So the aperture simply RUNS OUT of the roof's -X edge with sides parallel to X. Nothing
# ever closes over the void, so there is no bridge; the sides are parallel to the build
# direction, so there is no stepover at all; and the material outboard of every aperture is
# the full 4.40 web rather than a taper. The roof becomes a comb of stubby teeth
# (4.40 x 5.40 x 1.60) joined at +X, which is where it fuses into the endplate's comb brace.
#
# The cost is that the -X end is open rather than partly closed. Cheap: the shallow-angle
# ambient path was already being handled by the 0.30 gap over 5.40 of depth, not by this
# edge, and -X of the cover is instrument interior rather than sky.
#
# To get a true gable the op-amp column would have to move ~1.5 -X so the roof could reach
# -23.50. That trades the TIA's distance from its photodiode -- the noise-critical summing
# node -- for lid cosmetics, which is the wrong way round unless something else wants it.
APER_X1 = BAND_X0 - D.MIN_WALL_2P                # -18.20: leaves a FULL two-bead strip of
                                                 # roof at +X, where the old 3.0-wide slot
                                                 # left only 1.40. Still clears the packages
                                                 # (they end at -18.50) by 0.30.


def _aperture_cutter(sy: float) -> cq.Workplane:
    """One string's aperture: a constant-width notch, open at the roof's -X edge."""
    hy = SLOT_DY / 2
    return box_at(APER_X1 - (COVER_X0 - 1.0), SLOT_DY, COVER_T + 2,
                  x=(APER_X1 + COVER_X0 - 1.0) / 2, y=sy,
                  z=(COVER_Z0 + COVER_Z1) / 2)


def opt_cover() -> cq.Workplane:
    """Lid over the sensor row, UNIONED INTO THE ENDPLATE (user) rather than made as a
    separate printed part: the plinth is only 3.2 thick and cannot host an M2 anchor, so
    a bolt-down lid had nowhere to land. Integral solves retention by deleting it.
    The board therefore installs by SLIDING +X under the roof, and comes out the same way
    -- which needs the magnetic pickup out of the way first.

    Was: a printed lid over the sensor row: a roof with one aperture per string, plus a -X
    wall that closes the shallow-angle ambient path (from +X the endplate already does).
    Drops on after the board and is the last thing installed before stringing.

    It covers the ROW ONLY, not the whole board: the quad op-amps stand 1.75 above the
    board, higher than the roof, and they need no protection -- only the optics do."""
    # +X edge runs to the DECK BAND edge, not the board edge, so the roof fuses into the
    # endplate's comb brace instead of floating 0.2 short of it.
    x0, x1 = COVER_X0, BAND_X0
    roof = box_at(x1 - x0, 2 * COVER_HY, COVER_T,
                  x=(x0 + x1) / 2, y=0, z=(COVER_Z0 + COVER_Z1) / 2)
    # NO -X WALL any more. Integrating the lid means the board SLIDES IN +X beneath it,
    # so nothing may hang below the roof or the sensors cannot pass. Cheap to lose: the
    # roof underside sits COVER_GAP (0.3) over the sensor faces across 5.4 of depth, so a
    # ray from -X has to be within ~3 deg of horizontal to reach a detector -- the gap's
    # own aspect ratio does what the wall did.
    for i in range(D.N_STRINGS):                       # apertures
        roof = roof.cut(_aperture_cutter(string_y_at(i, SENSE_X)))
    return roof


def opt_carrier_pocket() -> cq.Workplane:
    """Cutter the endplate's carrier uses: the board envelope plus its slip fit, opening
    UPWARD. Cut from the board's own numbers so the pocket is always the board."""
    # opens from PLINTH_TOP, not PCB_BOT: the pocket has to admit the thickest board the
    # fab may ship, not the nominal one the model draws.
    return _outline(grow=0.3, t=(COVER_Z1 + 0.3) - PLINTH_TOP,
                    zc=(PLINTH_TOP + COVER_Z1 + 0.3) / 2)


def bom_rows():
    """The strip's BOM, grouped -- (qty, description, package, refs). Same PARTS table the
    3D model is built from, so BOM.md and the assembly cannot disagree."""
    groups = {}
    for p in PARTS:
        groups.setdefault((p["desc"], p["pkg"]), []).append(p["ref"])
    rows = [(len(r), desc, pkg, r) for (desc, pkg), r in groups.items()]
    rows.sort(key=lambda r: (-PKG[r[2]][0] * PKG[r[2]][1], r[1]))
    return rows


def _assert_field_clear():
    """Guard the bugs this part can silently ship, NONE of which the assembly overlap
    gate can catch -- board and components are ONE unioned solid, and a pairwise checker
    never tests a solid against itself.

    A NOTE ON WHAT THESE ARE FOR, because two bugs got through that were nobody's typo.
    COVER_HY was derived from the sensing field when the aperture was what actually
    governed it; Y_TAIL was derived from the magnetic pickup's cavity, correct until the
    tail stopped passing anywhere near that cavity. Both stayed legal, printable and
    gate-clean while being wrong, because a derivation that has gone STALE still
    evaluates. Nothing was violated -- the rule had simply stopped being the rule.

    So these assertions state the INTENT, not the arithmetic. Each one re-checks the
    property the design actually needs, independently of which constant it was computed
    from. When a source stops governing, the value drifts but the assertion still holds
    the design to the real requirement -- which is the only way this class of bug gets
    caught by code rather than by someone noticing it in a render."""
    # 0. SYMMETRY. Anything the design intends to be mirrored is asserted to be, because
    # a stale derivation on ONE side is exactly how the -Y wrap ended up 1.05 slacker
    # than the +Y one. Cheap, and it fails the moment the two ends drift apart.
    if abs(HEAD_Y0 + Y_TAIL) > 1e-9:
        raise AssertionError(
            f"optical strip: wrap bands are not mirrored -- +Y turns at {HEAD_Y0:.2f}, "
            f"-Y at {Y_TAIL:.2f}. They exist to grip the same feature at both ends.")
    if abs((PCB_YP - HEAD_Y0) - (Y_TAIL - WRAP_Y)) > 1e-9:
        raise AssertionError(
            f"optical strip: wrap bands differ in length -- +Y {PCB_YP - HEAD_Y0:.2f}, "
            f"-Y {Y_TAIL - WRAP_Y:.2f}")
    _m = mount_points()
    # Y ONLY. The grips are the board's Y DATUM, so their Y must stay mirrored -- equal
    # leverage about the sensing field, and a stale derivation on one side is exactly how
    # the -Y wrap once ended up 1.05 slacker than the +Y one.
    #
    # Their X deliberately does NOT match (user): the tail screw is hard +X to clear the
    # MCU, the head screw hard -X to stay near the sensor row. X is not part of the datum
    # -- two points at different X locate the board just as well, the line between them is
    # merely skewed -- so asserting it would only forbid a change that is actually wanted.
    # What DOES still matter is that each lands in the plinth, which is checked below.
    if abs(_m[0][1] + _m[1][1]) > 1e-9:
        raise AssertionError(
            f"optical strip: the two M4 grips are not mirrored IN Y -- {_m[0][1]:.2f} and "
            f"{_m[1][1]:.2f}. They are the board's Y datum; asymmetry there means one of "
            f"them moved alone.")
    for _mx, _my in _m:
        if not (PLINTH_X0 + D.MIN_WALL_2P <= _mx <= TAIL_X1 - D.MIN_WALL_2P):
            raise AssertionError(
                f"optical strip: M4 grip at x {_mx:.2f} is outside the wrap plinth "
                f"({PLINTH_X0:.2f}..{TAIL_X1:.2f}) with its {D.MIN_WALL_2P} wall -- it has "
                f"nothing to screw into.")
    # 1. the whole sensing strip must sit inside the deck band, or it fouls the magnetic
    # pickup's cavity (-X) or the endplate (+X). Both edges are read from top_plate, so
    # this fails loudly if the pickup's travel changes rather than overlapping quietly.
    if PCB_X1S < BAND_X1 or PCB_X0 > BAND_X0:
        raise AssertionError(
            f"optical strip: sensing strip X {PCB_X1S:.2f}..{PCB_X0:.2f} is outside the "
            f"deck band {BAND_X1:.2f}..{BAND_X0:.2f} (pickup cavity to deck end)")
    # 2. emitter <-> detector placement gap
    gap = (PD_DY - PD_PKG[1] / 2) - LED_PKG[1] / 2
    if gap < PKG_CLR:
        raise AssertionError(
            f"optical strip: emitter-to-detector gap {gap:.2f} < PKG_CLR {PKG_CLR}")
    if SENSE_D < STIFF_FLOOR:
        raise AssertionError(
            f"optical strip: sensing at {SENSE_D:.1f} mm is inside the "
            f"{STIFF_FLOOR:.1f} mm stiffness floor -- pitch would be inharmonic")
    # 3. every part inside the board, clear of the routed edge, and of every other part
    for p in PARTS:
        x0, x1, y0, y1 = part_span(p)
        # A part straddling a section seam must satisfy BOTH sections, i.e. the
        # intersection of their X spans -- not some arbitrary fallback.
        a, b = section_at(y0), section_at(y1)
        lim, hi = max(a[0], b[0]), min(a[1], b[1])
        # A connector's MOUTH is allowed to sit on the board edge -- that is the point of a
        # side-entry part. J2 used to be the exception on -X; both connectors now exit -Y,
        # so -Y is the only edge with exceptions and -X has none.
        kx = EDGE_KEEP
        ky = 0.0 if p["ref"] in ("J1", "J2") else EDGE_KEEP
        if (x0 < lim + kx - 1e-9 or x1 > hi - EDGE_KEEP + 1e-9
                or y0 < PCB_YM + ky - 1e-9 or y1 > PCB_YP - EDGE_KEEP + 1e-9):
            raise AssertionError(
                f"optical strip: {p['ref']} ({p['desc']}) at X {x0:.2f}..{x1:.2f} "
                f"Y {y0:.2f}..{y1:.2f} breaks the {EDGE_KEEP} edge keep-out of board "
                f"X {lim:.2f}..{hi:.2f} Y {PCB_YM:.2f}..{PCB_YP:.2f}")
    for i, a in enumerate(PARTS):
        ax0, ax1, ay0, ay1 = part_span(a)
        for b in PARTS[i + 1:]:
            bx0, bx1, by0, by1 = part_span(b)
            sep = max(max(ax0, bx0) - min(ax1, bx1), max(ay0, by0) - min(ay1, by1))
            if sep < PKG_CLR - 1e-9:
                raise AssertionError(
                    f"optical strip: {a['ref']} ({a['desc']}) and {b['ref']} "
                    f"({b['desc']}) are {sep:.2f} apart, inside the {PKG_CLR} "
                    f"placement clearance")
    # 4. anything over the sensing field must clear the STRINGS in Z -- they run over the
    # whole board, not just over the sensor row, so a tall package in the analog field is
    # under a string even though it is nowhere near the optics.
    for p in PARTS:
        dz = PKG[p["pkg"]][2]
        _, _, y0, y1 = part_span(p)
        if y1 <= -SENSE_HL or y0 >= SENSE_HL:
            continue
        clr = STRING_BOT_MIN - (PCB_TOP + dz)
        if clr < PART_STRING_CLR - 1e-9:
            raise AssertionError(
                f"optical strip: {p['ref']} ({p['desc']}, {p['pkg']}) stands to "
                f"Z={PCB_TOP + dz:.2f} under the sensing field, leaving {clr:.2f} to the "
                f"lowest string at {STRING_BOT_MIN:.2f} -- under PART_STRING_CLR "
                f"{PART_STRING_CLR}")
    # 5. the COVER must clear the strings above and the parts below it
    if STRING_BOT_MIN - COVER_Z1 < 1.0 - 1e-9:
        raise AssertionError(
            f"optical strip: cover top {COVER_Z1:.2f} leaves "
            f"{STRING_BOT_MIN - COVER_Z1:.2f} to the lowest string -- under 1.0")
    for p in PARTS:
        x0, x1, y0, y1 = part_span(p)
        if x1 <= COVER_X0 or y0 >= COVER_HY or y1 <= -COVER_HY:
            continue                                       # outside the lid's footprint
        # PCB_TOP is the WORST-CASE board top by construction (PLINTH_TOP + PCB_T_MAX), so
        # this tests the thickest board the fab may ship, not the nominal one drawn.
        if PCB_TOP + PKG[p["pkg"]][2] > COVER_Z0 + 1e-9:
            raise AssertionError(
                f"optical strip: {p['ref']} ({p['desc']}) stands to "
                f"{PCB_TOP + PKG[p['pkg']][2]:.2f} on a max-thickness board, into the "
                f"cover underside at {COVER_Z0:.2f}")
    for mx, my in mount_points():
        for q in PARTS:
            x0, x1, y0, y1 = part_span(q)
            r = M4.shaft_clr_d / 2 + 1.0
            if x0 - r < mx < x1 + r and y0 - r < my < y1 + r:
                raise AssertionError(
                    f"optical strip: M4 mount at ({mx:.2f}, {my:.2f}) lands on "
                    f"{q['ref']} ({q['desc']})")
    # 6. the lid must keep real material outboard of its last aperture, at both ends
    edge = COVER_HY - (_OUTER_Y + SLOT_DY / 2)
    if edge < D.MIN_WALL_2P - 1e-9:
        raise AssertionError(
            f"optical strip: cover has only {edge:.2f} outboard of the outermost "
            f"aperture -- under the {D.MIN_WALL_2P} two-bead floor")
    # 7. every sensor must actually see through an aperture
    for i in range(D.N_STRINGS):
        sy = string_y_at(i, SENSE_X)
        for s in (0, PD_DY, -PD_DY):
            if abs(s) + PD_PKG[1] / 2 > SLOT_DY / 2 + 1e-9:
                raise AssertionError(
                    f"optical strip: string {i + 1}'s detector at {s:+.2f} reaches past "
                    f"the {SLOT_DY} aperture -- the cover would blind it")
    # 7. the board must clear the deck it rides over
    if STANDOFF < 1.6:
        raise AssertionError(
            f"optical strip: only {STANDOFF:.2f} between the board and the deck at "
            f"{DECK_TOP:.2f} -- no room for the carrier's ledges")


_assert_field_clear()
