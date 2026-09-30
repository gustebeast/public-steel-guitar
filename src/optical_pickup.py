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
    the alternative was a ~90 mm trace sharing a board with a pulsed LED driver whose
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

import math

import cadquery as cq
from cadquery.selectors import NearestToPointSelector

from . import dimensions as D
from . import chassis as CH
from . import top_plate as TP
from .helpers import box_at, cyl, cyl_y, oct_cable
from cadkit.fasteners import M4
from cadkit.pcb import PCB_T as _PCB_T

# ── where it sits ────────────────────────────────────────────────────────────
# The speaking length ends at the BEARING TANGENT (directly over the axle), NOT at
# BRIDGE_X (which is the ball-end anchor, past the bearing).
TERMINATION_X = D.BRIDGE_AXLE_X                  # -8.0
# 15.5 -> 20.0 (branner 2026-09-09), forced by the TWO SCREW ROWS at the bridge end.
# The endplate had to widen to host the near row's guide-rod socket, which moved its -X
# face -16.50 -> -23.10; the DECK is flush with that face (top_plate.PX0), so the deck --
# and this strip with it -- lost 6.6 mm off its +X end. At SENSE_D 15.5 the sensing row
# stayed put at X -19.5 while the board's +X edge retreated to -23.30, leaving the
# emitters standing 3.5 mm OFF the board.
# Moving the STATION is the cheap fix, and the only asserted constraint on it is a FLOOR
# (STIFF_FLOOR 10.4, the string's bending-stiffness boundary layer) which 20.0 clears
# with room. The alternative -- running the board on under the endplate -- would have
# needed a relief modelled through it for no gain. Sensing further from the termination
# also reads a LARGER displacement, so the signal improves rather than degrades.
# 21.5 -> 20.0 (branner 2026-09-10): the bridge bearing went Ø13 -> Ø16 (688ZZ), which moved
# the termination (the axle line) 1.5 mm -X. Taking the same 1.5 off SENSE_D keeps the sensing
# row at X -28.0, so the whole board and every part on it stay where they were verified.
SENSE_D       = 20.0                             # sensing station, out from the termination
SENSE_X       = TERMINATION_X - SENSE_D          # -28.0
# Floor, from the string's bending-stiffness length sqrt(EI/T): ~1.2 mm for the plain
# .015 core at ~120 N, ~1.7 mm for the wound .070 at ~150 N. The boundary layer where
# the string stops following the ideal mode shape -- and the effective termination point
# turns frequency-dependent, which would put inharmonicity straight into a PITCH
# measurement -- runs a few multiples of that, so 5-10 mm. SENSE_D keeps well over it.
STIFF_FLOOR   = 13 * D.NOZZLE_D                  # 10.4 (was 10.0 = 12.5 beads)

# ── THE DECK BAND -- the constraint this whole layout is shaped by ───────────
# The carrier rides on the deck between the magnetic pickup's cavity and the deck's +X
# end at the endplate. Both edges are READ from top_plate so they cannot drift: if the
# pickup's travel or plate size changes, this band changes with it and the assertions
# below fail rather than the parts quietly overlapping.
DECK_TOP   = TP.TZ                                            # 6.40, deck surface
BAND_X0    = TP.PX0                                           # -25.06, deck's +X end
BAND_X1    = TP.PICKUP_X_NOM + TP.CAVITY_X / 2                # -39.08, cavity's +X edge
BAND_CLR   = 0.2                                              # keep off both band edges

# ⚠ OPT_GAP IS THE ONE UNDERIVED NUMBER IN THIS Z STACK, AND IT IS A BIG LEVER.
# Everything else here comes from something -- STRING_BOT_MIN from STRING_GAUGE_MAX,
# PCB_TOP from the LED package, COVER_Z0 from COVER_GAP -- and this is a round 3.0 with a
# comment saying what it is and not why. The four levers listed at the top of this file for
# the thin-string problem do not include it.
#
# Costed in .ins/opt_gap.py against elec/optical.py's own noise budget (143 nA on the
# thinnest string, Rf 1M, shot noise included). Signal goes as ~1/h^3 -- a LINE target,
# between a plane's 1/h^2 and a point's 1/h^4 -- which is a model, not a measurement, so
# read these as a ranking:
#
#     clearance 1.10 -> 0.70                    gap 3.44   +2.1 dB
#     cover 1.6 -> 0.8 (1-bead: it will sag)    gap 3.04   +4.4 dB
#     both                                      gap 2.64   +6.8 dB
#     NO COVER, same clearance                  gap 1.94  +11.6 dB
#     NO COVER + Rf 1M -> 250k                  gap 1.94  +10.6 dB, headroom 11.9 uA
#
# ⚠ AND THE STRING THAT SETS SNR IS NOT THE ONE THIS DATUM REFERENCES. STRING_BOT_MIN is
# the THICKEST string, correctly, because it is the clearance case. The thinnest string is
# 0.84 mm FURTHER from the sensor and returns 5.1x less light, so the worst-case gap is
# 3.84 and not 3.00. Every dB above is quoted at 3.84.
#
# ⚠ THE COVER IS PROTECTING TIA HEADROOM, NOT NOISE, which is the thing to understand
# before trading it away. At Rf = 1M and MID = 0.33 V the TIA clips at 2.97 uA of ambient
# photocurrent; elec/optical.py calls 1 uA (a halogen wash) realistic. Widening the
# detector's field of view from ~+-30 to ~+-60 deg is a 3.7x solid angle, so ~3.7 uA --
# over the cliff. Dropping Rf to 250k restores four-fold headroom and costs ~1 dB of the
# 11.6, because only the Rf thermal term moves and the signal moved further.
# Crosstalk, which the aperture also buys, should IMPROVE rather than worsen: at 1.94 mm a
# +-60 deg detector sees +-3.4 mm of string against a 9.5 mm pitch.
# What removing it really costs is MECHANICAL -- it is the debris lid, and it is what
# stands between a dropped bar and twenty photodiodes. That is the trade, and it is the
# user's to make; nothing here is worth 10 dB if the board dies in a year.
# OPT_GAP is now DERIVED at the Z stack (the board rests on the axle) -- see below.
PCB_T   = _PCB_T                                 # FR4 NOMINAL -- cadkit.pcb owns the value
                                                 # (one copy for every board). Correct for 4 layer:
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
    # ⚠ THE EMITTER IS A 0603 AND IT IS TALLER THAN THE 0805 IT REPLACES (2026-09-23).
    # Lite-On LTE-C9901, DS50-2017-0074: 1.60 x 0.80 body, 0.98 to the lens apex (+-0.1 by
    # the drawing's general tolerance note). The instinct is that a smaller package is a
    # shorter one and costs optical gap -- PCB_TOP is axle-set, so a lower emitter face
    # means a LONGER throw to the string. It is the other way round here: 0.98 against
    # 0.85 SHRINKS the gap 1.35 -> 1.22 and is worth +0.9 dB on its own.
    "0603OPT":  (1.60, 0.80, 0.98),   # optoelectronic 0603 -- the LTE-C9901 emitters
    "0805OPT":  (2.00, 1.25, 0.85),   # optoelectronic 0805 -- the old IR17-21C emitters
    "PD15":     (3.30, 2.80, 1.10),   # Everlight PD15-22B/TR8 photodiode (DTD-152-002 p.2)
    "WQFN-24":  (4.00, 4.00, 0.80),   # TI RTW, TLV320ADC3140 (SBAS993B mechanical)
    "SOT-23":   (2.90, 2.40, 1.30),
    "SOT-23-5": (2.90, 2.80, 1.45),
    "SOT-23-6": (2.90, 2.80, 1.45),   # same envelope as the -5; the buck (see U13)
    "IND-4040": (4.10, 4.10, 3.10),   # 4x4 shielded power inductor, buck output (SWPA4030,
                                      # 3.0 tall since the LMR33630 swap)
    "RNX12":    (2.00, 3.00, 1.00),   # TI VQFN-HR RNX0012, the LMR33630CRNXR buck
    "1206C":    (3.40, 1.85, 1.60),   # 50 V X7R -- the 24 V input bulk wants the voltage
                                      # rating AND the derating headroom; an 0805 50 V part
                                      # loses most of its capacitance at 24 V bias
    # ⚠ NOT A SOT-563 BODY. The part ordered is USBLC6-2SC6 in SOT-23-6, and the
    # courtyard below was already corrected to match while the BODY was left at the
    # SOT-563's 1.6 x 1.6. Body is what the pairwise clearance assert measures, so the
    # small one let a neighbour sit closer than the real package allows. The key keeps
    # its name because the footprint library entry the layout uses is the SOT-23-6 one;
    # what was wrong was the envelope, not the choice.
    "SOT-563":  (2.90, 2.80, 1.45),
    "TP":       (1.50, 1.50, 0.00),   # bare 1.5 mm copper pad, nothing on it
    # ⚠ THE SMALL ONE EXISTS BECAUSE OF WHERE THE ROOM IS, not to save area. The I2C2
    # bring-up pads have 26 legal sites on the whole board at D1.5 and hundreds at D1.0.
    "TP_SMALL": (1.00, 1.00, 0.00),   # bare 1.0 mm copper pad, nothing on it
    # U8's digital rail is ~300 mA, so 5V->3V3 burns 0.51 W. That is past a SOT-23-5
    # (>100 degC rise), which is why U8 is NOT the same part as U9. A BUCK is still the
    # wrong answer for THIS rail: it sits among 20 TIAs reading tens of nanoamps, and a
    # ~1 MHz switcher there trades a thermal problem for a noise problem on the axis the
    # design is most sensitive to. A tab package sheds the heat instead -- SOT-223 is
    # ~50 degC/W with a copper pour, i.e. ~25 degC rise. 1.7 V of headroom against
    # AMS1117's 1.3 V max dropout.
    #
    # ⚠ THE BOARD IS NO LONGER SWITCHER-FREE, and that claim used to be here. The rail
    # arriving at J2 is 24 V, not 5 V (user, 2026-09-14), so ONE switcher is unavoidable:
    # 24->3V3 by linear regulation would burn 0.3 A x 20.7 V = 6.2 W, which no package on
    # this board can shed. U13 makes 5 V and the two LDOs still make both 3V3 rails from
    # it, so the switching node is a single point at the board's extreme -Y tail rather
    # than a rail running the length of the sense array. See the U13 block.
    "SOT-223":  (6.50, 3.50, 1.80),   # tab package, JEDEC TO-261AA
    # TLV9062 dual, TI DGK. KiCad-native orientation: pin rows down the X sides, so the
    # 4.90 lead span is the X extent and the 3.00 body length is Y. IT IS PLACED ROTATED
    # (OP_ROT) so the rows face +-Y instead -- see COL_OPA.
    "VSSOP-8":  (4.90, 3.00, 1.10),
    "WQFN-16":  (3.00, 3.00, 0.80),   # TLV9064 RTE/SIRTER quad. 0.80 tall against SOIC-14's
                                      # 1.75, which is what lets a TIA live under a string.
    "SOIC-14":  (6.00, 8.65, 1.75),   # LONG AXIS ALONG Y: 8.65 body, 6.00 across leads.
                                      # Chosen over TSSOP-14 purely for X: 6.00 across
                                      # the leads against TSSOP's 6.40, and X is the
                                      # scarce direction in a 14 mm band.
    "QFN-24":   (4.00, 4.00, 0.90),
    "LQFP144":  (22.00, 22.00, 1.60), # JEDEC MS-026: 20x20 body, 22x22 over leads
    "LQFP176":  (26.00, 26.00, 1.60), # JEDEC MS-026: 24x24 body, 26x26 over leads
    "3225":     (3.20, 2.50, 0.90),
    "USB-C":    (8.94, 7.35, 3.16),   # TYPE-C-31-M-12 (LCSC C165948)
    # J2 is a FOUR-way on the -Y EDGE, mouth facing -Y alongside the USB-C, so every cable
    # leaves the board at one end (user: a -X exit is unmanageable).
    #
    # ⚠ IT WAS A SIX-WAY AND THE FOLLOW-UP RECORDED HERE HAS NOW LANDED. The two extra
    # ways carried the magnetic pickup's buffered audio tap and its own return; the pickup
    # lands on the OUTPUT PANEL board instead (user, 2026-09-15), so the pair is gone and
    # J2 collapses to the instrument's standard 4-way -- the same shell and crimp order as
    # every tee, and one fewer connector SKU in the build.
    #
    # It stays a 4-way rather than shrinking further because JST's SMT side-entry XH line
    # STARTS at 4 way (there is no S2B), and because 24V/PWR_GND on one contact each plus
    # two empty cavities is the pattern every other board here uses. At 24 V the board
    # draws ~85 mA, so one contact per rail is ample -- the doubling other boards use is a
    # current argument that does not apply at this voltage.
    #
    # ORIENTED FOR A -Y MOUNT: 15.0 runs along X (the edge), 6.10 is the body's reach into
    # the board in Y. ⚠ 15.0 is JST's published B for the 4 way -- CONFIRM on the part's
    # drawing before layout, exactly as the 6 way's 20.0 was.
    "XH-SM-4Y": (15.00, 6.10, 7.00),  # JST S2B-XH-SM4-TB, SMT side entry, -Y
                                      # (2-way since 2026-09-18, user -- 5 mm shorter
                                      #  than the 4-way it replaced; see elec/optical.py)
    # (1210C, RELAY-SIG, SOD-523, TSSOP-16 and TSSOP-20 are DELETED: they were the
    #  DC block, the true-bypass relay, the clamps, the magnetic ADC and the DAC, all
    #  of which moved to the output panel with the magnetic path. The CRTYD assertion
    #  below is what found them still sitting here -- a package with no part left.)
}
LED_PKG_NAME = "0603OPT"
LED_PKG = PKG[LED_PKG_NAME]
PD_PKG  = PKG["PD15"]
PKG_CLR = 0.25                                   # least placement gap between packages
EDGE_KEEP = 1.2                                  # part -> board edge: JLCPCB's 1.0 rule
                                                 # + their 0.2 routed-outline tolerance
# ⚠ ROW_GAP AND PKG_CLR APPLY TO BODIES, AND THE PACKING NOW WORKS IN COURTYARDS,
# WHERE THEY WOULD BE DOUBLE-COUNTED. A courtyard already contains the assembly
# clearance -- two courtyards that TOUCH are legal, which is what the boundary means --
# so the packer adds only a hair on top of it to keep an exact touch from reading as an
# overlap on a rounding error. Adding the full PKG_CLR + ROW_GAP on top instead cost
# about 3 mm of board length, and this board has none to spare: it pushed the cable
# conduit straight through the endplate's exterior wall, which is the same wall that
# sent the jack output stage to the output panel.
CRTYD_GAP = 0.15                                 # courtyard-to-courtyard, packing only
ROW_GAP   = 1.0

# ── COURTYARDS -- THE OTHER SIZE, and the one that spaces the layout ────────
# ⚠ PKG ABOVE IS THE BODY. THIS IS THE LAND. They are different measurements and the
# board needs both, which is why there are two tables instead of one corrected one:
#   * PKG (body + leads) is what has to clear the COVER, the deck and the strings.
#     It is a mechanical number and the Z stack and the field assertions use it.
#   * CRTYD is KiCad's COURTYARD -- the pads plus the IPC assembly clearance. It is
#     what has to clear the NEIGHBOURING PART, and it runs 1.0-1.5 mm larger per axis
#     than the body on almost everything, because pads stick out past a body and an
#     assembler needs room to place onto them.
#
# THE LAYOUT USED TO BE SPACED BY PKG, WHICH MEANT IT WAS NOT ASSEMBLABLE. It surfaced
# the moment elec/optical.py fed these placements to a real PCB and the courtyard check
# reported 41 collisions -- every one of them a pair of parts whose BODIES cleared and
# whose LANDS did not. Nothing in the CAD could have caught it: the model was
# self-consistent, it was just measuring the wrong edge for this purpose.
#
# Read out of the KiCad footprints elec/optical.py actually uses, not estimated.
CRTYD = {
    "0402":     (1.95, 1.03),
    "0603":     (3.05, 1.55),
    "0805C":    (3.49, 2.05),
    "0603OPT":  (2.60, 1.50),   # land is 2 x 0.55x0.80 pads on a 2.00 span (DS 7)
    "0805OPT":  (3.45, 1.99),
    "PD15":     (5.00, 3.30),   # elec/footprints/Steel.pretty/Everlight_PD15-22B
    "WQFN-24":  (5.26, 5.26),   # KiCad Texas_RTW_WQFN-24-1EP_4x4mm_P0.5mm_EP2.7x2.7mm
    "1206C":    (4.69, 2.39),
    "SOT-23":   (3.95, 3.49),
    "SOT-23-5": (4.19, 3.49),
    "SOT-23-6": (4.19, 3.49),
    "SOT-563":  (4.19, 3.49),   # the real part is SOT-23-6 -- see the U10 note
    "TP":       (2.50, 2.50),   # KiCad's own courtyard for the D1.5 test pad
    "TP_SMALL": (2.05, 2.05),   # ... and for the D1.0 one (r 1.0 circle + 0.05 stroke)
    "SOT-223":  (8.89, 7.29),   # the biggest gap of the lot: a tab package's land is
                                # nothing like its body
    # ⚠ 6.45, NOT 5.50, measured off the placed footprint rather than the datasheet
    # body. The dual op-amp is the one part in this table whose courtyard something
    # is placed AGAINST -- Cd sits hard against pin 8 -- and 5.50 put all ten of them
    # 0.305 mm inside U2*'s courtyard. DRC caught it only after a full route, because
    # a courtyard overlap is not a clearance error and the layout gate never reads it.
    "VSSOP-8":  (6.45, 3.60),
    "WQFN-16":  (3.60, 3.60),
    "SOIC-14":  (7.49, 9.25),
    "QFN-24":   (5.35, 5.35),
    "LQFP144":  (23.39, 23.39),
    "LQFP176":  (27.36, 27.36),   # KiCad LQFP-176_24x24mm_P0.5mm F.CrtYd
    "3225":     (4.29, 3.59),
    "IND-4040": (5.15, 4.59),
    "RNX12":    (2.90, 3.90),   # elec/footprints/Steel.pretty/Texas_RNX0012_...
    "USB-C":    (10.73, 9.51),
    "XH-SM-4Y": (16.79, 12.09),  # 12.09 in Y against a 6.10 body: a side-entry
                                 # connector's land reaches well back under it
}
assert set(CRTYD) == set(PKG), "every package needs both a body and a courtyard"
for _k, (_cw, _ch) in CRTYD.items():
    assert _cw >= PKG[_k][0] - 1e-9 and _ch >= PKG[_k][1] - 1e-9, (
        "%s: courtyard is smaller than the body, which cannot be right" % _k)


# Anything over the sensing field must still clear the strings. This WAS a round 1.5 with
# no derivation -- "the floor on what is left above" the 1.75 op-amps -- and it was the only
# thing standing between the board and ~11 dB. Budgeted instead, at the sensing station:
#     string vibration  0.306   a hard 3 mm midpoint pluck x sin(pi d/L), 10.2% at d=20
#     bar depression    0.067   1 mm at 300 mm, straight line to the bridge
#     setup variation   0.300   string height trim at bridge/nut
#     part + print tol  0.200   (board thickness is already handled: PLINTH_TOP is
#                                datumed off PCB_T_MAX, not the nominal)
#     ------------------------
#     required          0.873
# 1.10 is 1.3x that. The margin is smaller than it looks on paper because three of the four
# terms are themselves conservative -- a 3 mm pluck is hard playing, and the setup term is a
# full trim range rather than a tolerance.
#
# ⚠ ONLY ONE OF THE FOUR TERMS VARIES WITH X, AND IT IS THE BIGGEST (user, 2026-09-23:
# "this position is very close to the bearings so the string vibration will be minimal").
# The vibration allowance is a midpoint pluck scaled by the MODE SHAPE, sin(pi d/L), so it
# dies to nothing AT the termination -- a string cannot move where it is clamped. The other
# three are geometric offsets that apply everywhere. A single global clearance therefore
# charges every part on the board the amplitude of a string 20 mm away, and that is what
# capped the band between the detectors and the bearings at a 1.10 mm package when the real
# budget there is 1.2-1.4. That band is where the TIAs want to live, so the difference
# decides which op-amp packages are even admissible.
# d is measured from the TERMINATION and clamps at 0 going +X: past the bearing the string
# has turned down toward the changer and is below this board's copper entirely, which is
# what check 4's O_SLOT_X1 bound already encodes.
# ⚠ AND THE FUNCTION RETURNS THE RAW BUDGET, NOT A CLEARANCE. Writing it the other way --
# raw x a 1.26 margin, compared against the gap as if the product were a requirement -- is
# an error that looks right and reads right and flagged two innocent parts before the gate
# caught it. The margin is not a clearance; it is a RATIO, and the thing worth asserting is
# the ratio each part achieves. Comparing a margined requirement against an available gap
# silently demands margin^2 where the requirement is already the conservative number.
PLUCK_A     = 3.0                 # peak midpoint amplitude of a hard pluck
SPEAK_L     = D.MOUNTING_SPAN     # 615.0, the mode shape's half-wavelength
CLR_FIXED   = 0.067 + 0.300 + 0.200   # bar depression + setup trim + part/print tol
CLR_MARGIN  = 1.26                # what the flat 1.10 carried AT THE SENSING STATION
CLR_MARGIN_MIN = 1.15             # ...and the floor every other part has to clear


def string_budget_at(x: float) -> float:
    """RAW least part-to-string gap at X, in mm, before any margin. See the budget above."""
    d = max(TERMINATION_X - x, 0.0)
    vib = PLUCK_A * math.sin(math.pi * min(d, SPEAK_L) / SPEAK_L)
    return vib + CLR_FIXED


# ⚠ THIS IS NOT A FREE PARAMETER -- IT IS PINNED BETWEEN THE STRING AND THE AXLE. It sets
# PCB_TOP, PCB_TOP sets PLINTH_TOP, and bridge_endplate asserts PLINTH_TOP clears the Ø8
# shaft's crown at 12.00. At 1.10 the plinth lands at 12.04: FORTY MICRONS of room. Raising
# this by so much as 0.05 drops the plinth under the crown and the axle rides out over its
# own stop -- which is exactly what happened when a "more conservative" datum was tried here,
# and the ENDPLATE's assert is what caught it, nothing in this file. The string is above
# this number and the axle is below it; it is two-sided and it is not 0.04 of slack.
PART_STRING_CLR = CLR_MARGIN * string_budget_at(SENSE_X)      # 1.100
assert abs(PART_STRING_CLR - 1.10) < 0.005, \
    "the derived clearance no longer reproduces the 1.10 it replaced"


# ── Z STACK, built UPWARD from the deck ─────────────────────────────────────
# Datum is the LOWEST string underside. Centres are coplanar (verified), so the THICKEST
# string hangs lowest and is the one that sets the standoff; every thinner string simply
# gets more gap. (The overhead version had the mirror-image of this bug: it referenced
# D.STRING_Z, the centre line, and silently gave the thickest string 2.11 of the intended
# 3.0.)
# ⚠ THE STRINGS' UNDERSIDES ARE COPLANAR, NOT THEIR CENTRES (user, 2026-09-23: "they all
# rest on bearings at the same height"), and this line had it the other way round for the
# whole life of the board. D.STRING_Z is 16.0 and dimensions.py says what it is on the same
# line -- "speaking-length / bridge-bearing top" -- the surface the string SITS ON. So every
# string's underside is 16.0 whatever its gauge, and subtracting half the heaviest gauge put
# this datum at 14.984: a full 1.016 mm BELOW the bearing top, which is inside the bearing
# and where no string has ever been.
# It cost exactly that 1.016 mm of standoff, on every string, for nothing. Measured on the
# built solids to be sure before changing it: string_0 (.015) tops out at 16.41 and
# string_9 (.070) at 17.81 -- undersides identical, tops differing by the gauge.
# AND IT RETIRES A WORRY RATHER THAN CREATING ONE. With the undersides coplanar, the gap is
# the same for every string, so shrinking it is balance-NEUTRAL; the thin-string deficit is
# purely the 5x diameter, which is what the per-string R1-R10 emitter currents are for.
STRING_BOT_MIN = D.STRING_Z
# ⚠ THE BOARD SITS ON THE AXLE (user, 2026-09-23), so the standoff is not a choice any
# more -- it falls out of the axle. The Ø8 shaft tops at 12.00 and the board's UNDERSIDE
# rests there. The underside is PLINTH_TOP, NOT PCB_BOT: the plinth is datumed off
# PCB_T_MAX so that a max-thickness board's top lands on PCB_TOP. Deriving from PCB_BOT is
# how I first quoted 1.30 mm of part-to-string clearance when the true figure is 1.14.
# ⚠ THE TALLEST PART UNDER THE FIELD SETS THIS, AND IT USED TO BE THE OP-AMP. SOIC-14
# stands 1.75 against the PD15's 1.10, so while the quad TIAs sat beside their detectors
# they -- not the photodiode -- were what ran out of room, and they pinned the board 0.61
# below the axle. Moving them to the +X band (see COL_OPA) hands the title back to the
# detector and is the whole reason the board can rest on the axle and carry a comb.
# _assert_field_clear re-checks this against every placed part, so a part that creeps back
# under the strings fails loudly rather than silently reopening the gap.
FIELD_TALLEST  = PD_PKG[2]                                    # 1.10, the PD15s
PCB_TOP        = STRING_BOT_MIN - PART_STRING_CLR - FIELD_TALLEST
SENSE_FACE_Z   = PCB_TOP + LED_PKG[2]                         # emitter faces UP
# ⚠ 1.22, NOT THE 2.00 THIS COMMENT USED TO CLAIM. The number went stale when PCB_TOP was
# re-datumed onto the axle: it is STRING_BOT_MIN - SENSE_FACE_Z = 16.00 - 14.78, and it has
# been 1.22 ever since. Nothing downstream was wrong -- the value is computed, never the
# typed one -- but the figure was quoted in review as 2.00 more than once, and a `git
# checkout` of an unrelated revert put the stale wording back.
# SHORTER IS BETTER HERE: signal goes as the inverse square of the standoff, so 1.22 buys
# 2.7x the return of 2.00. What bounds it is not optics but collision -- the PD15s stand
# 1.10 and the string's underside is 1.10 above them, of which 0.306 is the vibration
# allowance at this station and the rest is margin.
OPT_GAP        = STRING_BOT_MIN - SENSE_FACE_Z                # 1.22 (emitter face to string)
AXLE_TOP       = D.BRIDGE_BEARING_Z + D.BRIDGE_AXLE_D / 2     # 12.00
# ⚠ AND THIS IS WHAT STANDS BETWEEN THE BOARD AND THE COMB. Resting the board ON the axle
# would let its hole become ten bearing slots with 4 mm strips between them, instead of one
# 30 x 105 opening -- ten extra bridges across the middle of the board. The board's
# underside is PLINTH_TOP, and it lands 0.61 BELOW the axle at the SOIC-14 height. Swapping
# the quad TIAs for a shorter package is the whole difference:
#     SOIC-14  1.75  plinth 11.39  gap 2.00   +7.3 dB   0.61 short of the axle
#     TSSOP-14 1.20  plinth 11.94  gap 1.45  +12.3 dB   0.06 short
#     QFN-16   0.90  plinth 12.24  gap 1.15  +15.5 dB   ON the axle
# TSSOP missing by 0.06 is worth knowing before anyone orders one.
PCB_BOT        = PCB_TOP - PCB_T                              # NOMINAL board underside
# THE PLINTH IS DATUMED OFF THE WORST-CASE BOARD, NOT THE NOMINAL ONE. The printed plinth
# is a fixed surface; the board thickness is not. Referencing the plinth to PCB_BOT (the
# nominal) means a board at the +10% limit carries its components 0.16 HIGHER than modelled
# and the 0.30 roof gap it must slide through drops to 0.14 -- a clearance the model would
# have declared fine while the real assembly bound. Referencing PCB_T_MAX instead makes the
# tolerance one-sided in the direction that is harmless: a thin board simply sits low and
# OPENS the optical gap (signal is linear in standoff, and per-string gain trims it), while
# clearance can only ever be at least what was designed. Trading a benign ~0.45 dB against a
# mechanical interference is the right way round.
PLINTH_TOP     = PCB_TOP - PCB_T_MAX                          # what the endplate builds to
STANDOFF       = PLINTH_TOP - DECK_TOP                        # under the board

# ── COVER -- the lid that makes up-firing viable ────────────────────────────
# Sits in the optical gap over the sensor row only. Three jobs: an APERTURE (each string
# gets its own slot, so the shallow-angle ambient path is cut), a DEBRIS LID (up-firing
# optics collect what down-firing ones shed), and physical protection during stringing.
# It is honest about its limits: at this standoff a slot cannot collimate much -- the
# geometric rejection is a few dB, and the heavy lifting against sun is an IR-pass
# window (see BOM.md). What it definitely buys is the -X wall and the debris seal.
# ⚠ THE COVER IS GONE (user, 2026-09-23: "debris isn't a compelling enough reason"), and
# it was costing 1.90 mm of standoff -- COVER_GAP 0.30 + COVER_T 1.60 -- for an optical
# job it was not doing. What it actually protected was TIA HEADROOM: at Rf 1M and MID 0.33
# the amp clips at 2.97 uA of ambient, and widening the detector's view from ~+-30 to
# ~+-60 deg is 3.7x solid angle. Rf 1M -> 250k buys that back four-fold for ~1 dB of the
# gain. See .ins/opt_gap.py.
# CROSSTALK IMPROVES rather than worsening, which is the part that matters for a pitch
# pickup: the aperture bought isolation, but so does getting closer, and faster. At the
# old 3.00 gap a +-60 deg detector viewed +-5.20 mm against a 4.75 half-pitch -- it was
# looking at its neighbour. At 2.00 it views +-3.46 and is clear.
COVER_GAP = 0.0
COVER_T   = 0.0
COVER_Z0  = SENSE_FACE_Z
COVER_Z1  = SENSE_FACE_Z
SLOT_DX   = 3.0                                  # aperture over the triplet, in X
SLOT_DY   = 7.6                                  # ...and in Y: the PD15 triplet spans
                                                 # +-3.775; the teeth left between
                                                 # apertures are PITCH - 7.6 = 1.76 (>=1.6)
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
# ⚠ THE SENSOR TRIPLET IS DELIBERATELY TIGHTER THAN IPC, AND IT IS THE ONE PLACE ON
# THIS BOARD THAT IS. At 1.6 the three parts' 1.99 COURTYARDS overlap by 0.39, which a
# courtyard check reports and which is correct to report -- so it is declared here
# rather than left to be rediscovered.
#
# WHY IT STAYS 1.6 ANYWAY: the courtyard is IPC's recommended assembly envelope, not a
# manufacturing limit. What has to physically clear is the BODIES, and at 1.6 pitch two
# 1.25-wide 0805s leave 0.35 between them -- placeable, and these three parts are placed
# by the same machine in the same pass.
#
# AND WHAT 2.0 WOULD HAVE COST, which is the reason this is not simply loosened: PD_DY
# is an OPTICAL parameter before it is a placement one. It sets the DIFF baseline, and
# the COVER's aperture is sized around the triplet -- at 2.0 the outer detectors reach
# 2.625 from the string's centre line against a 2.5 aperture half-width, so the lid
# would shade the very detectors it exists to protect. Widening the aperture to suit
# would admit more ambient light, which is the problem the lid was built for. Trading
# a real optical loss for a nominal clearance number is the wrong direction.
# ⚠ 2026-09-21: THE DETECTOR IS NOW THE EVERLIGHT PD15-22B, AND PD_DY FOLLOWS FROM ITS BODY.
# The VEMD4110X01 had 95 in stock against 20 per instrument; the PD15-22B has 11k, peaks at
# 940 nm (the emitter's own wavelength), gives ~3x the photocurrent, and costs a tenth. It
# is 3.3 x 2.8 rather than an 0805, so the triplet cannot stay at 1.6: the same 0.35 body gap
# to the emitter puts the detectors at 2.375. What the note above says 2.0 would have cost
# is paid by widening the aperture instead (SLOT_DY), and it buys something: a longer DIFF
# baseline. Optically the move costs ~25% of the light (line-integrated over the lit
# string, not the point estimate), more than repaid by the part's photocurrent.
PD_GAP = 0.35                                    # emitter body -> detector body, in Y
PD_DY = LED_PKG[1] / 2 + PD_GAP + PD_PKG[1] / 2  # 2.375
# AND IN X THE DETECTORS SIT JUST -X OF THE ROOF'S +X STRIP, not on the emitter's centre
# line. Their 4.5 mm land would otherwise reach the board's +X edge keep-out, and set here
# every detector body lies wholly inside its aperture notch (x1 < APER_X1): the part is
# 1.1 tall against the emitter's 0.98, so it stands 0.12 above the emitter face and only
# 0.05 under the roof's underside -- it must never pass UNDER roof material, including
# while the board slides +X into place along the notches. 0.36 mm off the emitter's line
# is nothing optically.
PD_X = (BAND_X0 - D.MIN_WALL_2P) - 0.05 - PD_PKG[0] / 2      # -28.36
END_KEEP = 2.0

_OUTER_Y = max(abs(string_y_at(i, SENSE_X)) for i in range(D.N_STRINGS))
SENSE_HL = _OUTER_Y + PD_DY                      # last sensor Y

# ── BOARD OUTLINE -- narrow sensing strip + a wide tail past the cavity ─────
# The strip is capped by the 14 mm band. The digital block cannot live in 14 mm (the MCU
# alone is 16 over its leads), so the board widens in the -Y room PAST the pickup
# cavity's -Y edge, where the deck is solid again and nothing is overhead.
# ⚠ THE STRIP IS WIDER THAN THE DECK BAND NOW (user, 2026-09-22): "We have space to add
# some PCB 3.15 +X and as much as we want -X of the optical sensors." The band was the
# binding constraint this whole file was written around, and after the PD15-22B / five-
# converter redesign it was also what stopped the board routing: the triplet's land grew
# 3.45 -> 5.0 across a 13.6 mm strip carrying twenty outputs, MID and the rails.
#   +X: the full 3.15 -- a lane between the detectors' outer pads and the edge.
#   -X: STRIP_GROW_MX. The op-amp columns stay where they are (moving them would lengthen
#       every summing node); the growth is a free lane beyond them for the long TIA
#       outputs and the digital lines to the +Y converters.
# ONLY THE STRIP SECTION GROWS. PCB_X1S stays the wraps' and the tail's -X edge (and the
# endplate pad's), so the strip steps out -X past them; STRIP_X1 is its own -X edge.
STRIP_GROW_PX = 3.15
# ⚠ ZERO AS OF 2026-09-23 -- THE OUTER BORDER IS A RECTANGLE AGAIN (user: "I'd like to see
# if we can get the PCB to be a rectangle on the outer border instead of having an
# outcropping under the strings"). Every millimetre of this 10.0 existed to house the ADC
# cells and the lanes feeding them, and the cells have moved EAST of the comb where they
# belong -- downstream of the TIAs instead of upstream of them. Checked before deleting it:
# no part's span reaches west of PCB_X1S any more. The whole board is now one rectangle,
# -38.88..+25.06 in x. The analysis below is kept because it is the measured record of what
# the corridor width did to routing, and the corridor still exists -- it is just east now.
STRIP_GROW_MX = 0.0   # was 10.0 = 2.5 measured lane + 6.0 ADC column + 1.5 of CORRIDOR
# ⚠ THAT LAST 1.5 IS THE ANALOG NETS' WHOLE PROBLEM, and it took three experiments to
# find because it is not where anyone looks. The corridor between the converter cell's east
# edge and the op-amp column's west edge was 0.68 mm -- ONE track -- and every analog run
# that has to travel in y between them shares it. Measured with .ins/lane.py, not guessed.
#   8.5  -> 0.68 mm,  1 track,  139 local segments laid
#  10.0  -> 2.18 mm,  6 tracks, 139          <- here
#  11.5  -> 3.68 mm, 10 tracks, 134          (the pre-lay starts losing hops)
# This is why widening the wall INSIDE the cell did nothing and measured worse (13 against
# 10): the runs were getting through the doors and arriving in a one-lane corridor. Fixing
# the second-narrowest thing while the narrowest is untouched buys nothing, and the two
# looked alike from the failure list -- both present as analog nets the router drops.
# ⚠ AND THE +X EDGE IS CAPPED BY THE GUIDE-ROD HOLES, NOT BY THE DECK BAND (user,
# 2026-09-22). The near row of rods sits at x -20.0 (the far row is +20.0 and nowhere near
# this board). Each hole needs a COMPLETE RING of endplate around it -- a bearing bore open
# on one side is not supported -- and the board was leaving only 0.36 mm of material on the
# rods' -X flank, so for half the strings that ring never closed. The cutaway may start one
# two-bead wall further west and no sooner. Derived from the rod geometry so it cannot drift
# if a rod moves: whichever of the deck band or the rod support binds first, wins.
ROD_SUPPORT = D.MIN_WALL_2P                                   # 1.6, the ring's own wall
_ROD_CAP = min(D.guide_rod_x(i) for i in range(D.N_STRINGS)
               if D.guide_rod_x(i) < 0) - D.GUIDE_ROD_D / 2 - ROD_SUPPORT
PCB_X0  = min(BAND_X0 - BAND_CLR + STRIP_GROW_PX, _ROD_CAP)   # -23.35, strip +X edge
# ⚠ MEASURED 2026-09-24: 1.20 mm IS FREE, AND THE BLOCKERS ARE NOT WHAT THIS NOTE SAYS.
# Swept PCB_X1S in 0.2 mm steps rather than reasoning about it:
#     +1.20  OK, board 62.74 wide      <- the most that costs nothing
#     +1.40  C160 (the 1206 24 V bulk, x -36.46..-33.0) hits the edge keep-out
#     +4.00  and only THEN the conduit assert below
# So the row-packer/conduit story is the SECOND blocker, not the first: one 1206
# capacitor sitting where _spread happened to leave it is what caps the trim at 1.20.
# NOT TAKEN, deliberately. 1.2 mm off a 63.94 x 188.53 board does not cross a JLCPCB
# price band, so the saving is mechanical only (a little less unsupported overhang past
# the plinth), and applying it perturbs a routed board that is at 10 unconnected / 0
# violations. Worth doing WITH the compute-section rework, not instead of it.
# ⚠ THE -X EDGE CANNOT COME IN YET, AND THE REASON IS THE -Y END (tried 2026-09-23).
# The user asked to reclaim the strip -X of the sensors now that nothing uses it: the
# converter cells moved east, and the floor is the PD15 land plus EDGE_KEEP at -32.06,
# so 6.82 mm looks free. It is not, because of how the compute section is placed.
# _spread and _block lay rows across the FULL width x0..x1. Narrow the board and they do
# not shrink -- they SPILL, taking more rows, and the section grows -Y. The -Y end has
# 0.11 mm before CONDUIT_Y0 passes the endplate's exterior-wall limit, so the board is
# LENGTH-constrained, and the packer silently converts width into length at roughly 1:1.
# Measured: PCB_X1S -32.06 pushed the conduit to -146.26 against a -145.19 limit.
# So this is not a board-outline change, it is a placement change: the compute section
# has to be laid out by FUNCTION (like the MCU ring now is) rather than by rows before
# the width can come in at all. Same root cause as the decoupling row. Deferred, not
# abandoned -- and the assert that would have hidden it is the conduit's, not this file's.
# ⚠ WAS THE BOARD EDGE, IS NOW ONLY THE CAVITY LIMIT. This is how far -X the board MAY
# go before it fouls the magnetic pickup cavity -- a ceiling, not a position. The board
# stopped using all of it on 2026-09-24; the real edge is PCB_X1S below, and the assert
# near the bottom of this file still measures the board against this.
PCB_CAVITY_X1 = BAND_X1 + BAND_CLR                            # -38.88, the -X ceiling
# ⚠ THE STRIP'S -X EDGE BELONGS TO V5_PRE NOW (user, 2026-09-24: "Let's make V5_PRE the
# west most point"). It used to be PCB_X1S, the pickup cavity's edge, which left 6.8 mm of
# board west of the detector column doing nothing but carrying the 5 V emitter rail
# wherever the router felt like putting it. Now the rail has a DECLARED lane and the edge is pinned
# to it, so neither can drift: the lane is the westmost copper on the board by construction.
#
# ⚠ ONLY THE STRIP MOVES. PCB_X1S and COMPUTE_X0 stay where they are, and that separation is
# the whole reason this is safe -- see the long "-X EDGE CANNOT COME IN YET" note above. The
# compute section is laid out by _block/_spread, which pack rows across the FULL width and
# SPILL into extra rows when narrowed, converting width into length at about 1:1; the -Y end
# has 0.11 mm before CONDUIT_Y0 breaks the endplate wall assert. Pulling PCB_X1S in measured
# -146.26 against a -145.19 limit. The strip has no packer, so it carries none of that.
# It also keeps the wraps wide, which the north one needs: its M4 mount hole sits at x -33.98,
# west of this new edge and still inside PCB_X1S.
V5_LANE_W = 0.8          # the emitter rail's own track -- 1068 mA worst case, all ten on
V5_LANE   = 0.2 + V5_LANE_W + 0.3        # PD-land clearance + track + fab edge clearance
# ⚠ ONE WEST EDGE FOR THE WHOLE BOARD (user, 2026-09-24: "I'd like the whole board to be
# a prism for its outer border"). Every section shares it, so the outer border is a single
# straight line from +Y to -Y and the billed bounding box is the board.
PCB_X1S  = PD_X - CRTYD["PD15"][0] / 2 - V5_LANE              # -32.16, the board's -X edge
STRIP_X1 = PCB_X1S                                            # kept: read by the endplate
# ⚠ THESE FOUR X DATUMS ARE DERIVED FROM top_plate AND THEIR COMMENTS WENT STALE BY
# 8.46 mm. BAND_X1, PCB_X0, PCB_X1S and COMPUTE_X0 all track TP.PICKUP_X_NOM and
# TP.CAVITY_X, so when the pickup cavity moved they followed correctly -- the CODE was
# never wrong -- and the hand-typed values beside them did not. Every one was off by the
# same 8.46, which is the signature of a derived chain whose annotations were written
# once. They are corrected 2026-09-18; they are ALSO the numbers a reader reasons from
# when placing a part, so treat the comment as a snapshot and print the attribute if a
# decision depends on it. (One did: the MCU's escape annulus below was recorded as
# 6.6 mm from the -30.42 edge and is 26.18 from the real one.)
# Both wraps turn +X at the SAME distance past the bearing arms. Y_TAIL used to be derived
# from the magnetic pickup's CAVITY, which was correct while the tail widened -X over the
# deck and had to clear it -- but the tail widens +X over the ENDPLATE now, so the cavity
# stopped governing this and the leftover left -Y 1.05 slacker than +Y (user spotted the
# asymmetry in the render). One constant, mirrored.
WRAP_CLR = 0.75                                               # past the arm outer face
# OFF THE ARM'S OUTER FACE, which is BRIDGE_ARM_OUT -- the same arithmetic, but named
# once instead of re-added here. It moved when the axle became a 100 SKU, and this
# board has to move with it: HEAD_Y0 is what stops the shaft sliding +Y.
Y_TAIL   = -(D.BRIDGE_ARM_OUT + WRAP_CLR)
# TAIL WIDENS +X, OVER THE ENDPLATE -- not -X over the deck (user). Two things fall out
# and both were open problems:
#   SUPPORT. Past |y| 54 the endplate has no material above z6 for a plinth to start on,
#     which is why the tail had nothing under it. But out here it has the FILL SLAB, whose
#     top IS z6 -- so a plinth over the endplate merges straight into solid material and
#     needs no deck standoffs, i.e. no top_plate change at all.
#   THE DECK STAYS CLEAR. The tail no longer lies across the deck panel.
# +X edge stops MIN_WALL_2P short of the endplate's outer face so the board is not flush
# with the instrument's exterior.
# ⚠ FLUSH WITH THE ENDPLATE'S +X FACE (user, 2026-09-23), not set back from it. The
# MIN_WALL_2P inset was there to keep a printed wall outboard of the board; there is no
# wall there -- the endplate simply ends -- so the inset bought nothing and cost 1.60 mm
# of the +X band, which is now where the op-amps and their feedback grids live.
TAIL_X1 = D.BRIDGE_BASE_X1                                    # 25.06, flush
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
HEAD_Y0 = -Y_TAIL                                             # 51.55, mirrored
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
PCB_YP     = CH.Y_HI + CH.T / 2                               # 65.95, the rail outer face
HEAD_LEN   = PCB_YP - HEAD_Y0                                 # 14.40, mirrored at -Y
WRAP_Y     = Y_TAIL - HEAD_LEN                                # -65.95, compute starts here
# COMPUTE SECTION WIDTH is set by the -Y EDGE, not by the MCU any more. Every cable now
# leaves at -Y (user: a -X exit cannot be routed cleanly), so that edge has to carry the
# USB-C AND the 6-way XH side by side, and THAT is the binding dimension -- the LQFP144
# only needs 24.4 of the 32.34 this produces. Derived, not typed, so it tracks either
# connector's envelope; the assertion below re-checks the MCU still fits.
#
# The widening is FREE in billed area: the SENSING STRIP already sets the bounding box's
# -X extreme at PCB_X1S (-30.42), and this lands at -25.34, inside it. There is 5.08 mm of
# further headroom before the bbox -- and therefore the fab charge -- would move at all.
COMPUTE_W_MIN = (2 * EDGE_KEEP + CRTYD["USB-C"][0] + CRTYD_GAP + CRTYD["XH-SM-4Y"][0])
# ...but the compute section runs -X to the STRIP'S OWN EDGE, so the board's -X side is ONE
# STRAIGHT LINE end to end (user) rather than stepping in near the -Y end. Two reasons, and
# the second is the one that forced it:
#   * It is free. PCB_X1S already sets the bounding box's -X extreme, so widening to meet it
#     changes no billed area at all -- only the copper inside a rectangle already paid for.
#   * MCU ESCAPE ROUTING. At the stepped-in -25.34 the LQFP144 had 1.20 mm of annulus on its
#     -X side -- 4 top-layer lanes at 0.127/0.127, for a side carrying 36 pins, and not even
#     enough for a staggered via fanout (36 vias at 0.65 pitch want 23.4 mm against a 22.0 mm
#     package side). Two of the MCU's four sides were effectively blocked. Straightening the
#     edge takes that side to 6.6 mm and makes three of four comfortable.
# The -Y edge connectors get the extra width for free as well.
COMPUTE_X0 = PCB_X1S                                          # -38.88, flush with the strip
assert TAIL_X1 - COMPUTE_X0 >= COMPUTE_W_MIN - 1e-9, \
    "compute section too narrow for the -Y edge connectors"

# ── M4 GRIP X, hoisted ───────────────────────────────────────────────────────
# Module level because the MCU is placed AGAINST the tail screw and _parts() runs before
# mount_points() is defined. One source, so the screw and the part that dodges it cannot
# drift apart. MIN_WALL_2P of plinth on the outboard side of each.
MOUNT_KEEP   = D.MIN_WALL_2P + M4.insert_pilot_d / 2          # 4.60
MOUNT_X_HEAD = PLINTH_X0 + MOUNT_KEEP                         # -20.46, hard -X
# ⚠⚠ THE TAIL MOUNT IS ON THE -X PLINTH NOW, NOT +X (user, 2026-09-29: "There seems to be
# more open space over on the -x side, and that's closer to the optical sensors which are the
# main thing we need to lock in position"). Both true, and it is the cheaper answer by a long
# way. The +X strip carries C112, C113, R50, TP7 AND the four east ring caps, and putting a
# 7.6 mm button head in there cost C111 its place -- the fix was moving NINE capacitors, which
# invalidated the SAI_FS post-route repair and the searched bring-up-pad sites and took the
# board from 0/0 to 10 unconnected / 15 violations. On the -X plinth the only thing in the
# head's way is R30, one 0402, which steps 1.0 mm -Y.
# ⚠ AND IT IS NOT AT THE USER'S EXACT SPOT, because the PLINTH runs out before the board does.
# The circled area is around board-local x -20.7; PLINTH_X0 + MOUNT_KEEP puts the westmost
# legal AXIS at -16.906 local. The binding surface is the wrap plinth, not the laminate (see
# mount_points), so this is as far -X as an M4 can go with MIN_WALL_2P of plinth around it.
MOUNT_X_TAIL = MOUNT_X_HEAD                                   # -20.46, the -X plinth too
MOUNT_CLR    = M4.shaft_clr_d / 2 + 1.0                       # keep-out radius, 3.20
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
ROW_X0    = SENSE_X - CRTYD[LED_PKG_NAME][0] / 2              # the row's -X edge, by LAND
# ⚠ THE OP-AMP COLUMN IS DERIVED FROM THE BOARD EDGE NOW, not from a typed gap to the
# sensor row. It used to be `ROW_X0 - 2.0 - half a package`, which worked while the
# spacing was in BODIES and put the quad's land 1.5 mm off the board once the spacing
# became COURTYARDS. The strip is 13.62 wide and the two columns' lands are 3.45 + 7.49
# of that, so there is about 1.2 of slack in the whole band -- not enough to spend on a
# round number. Pinning the quads against the edge keep-out spends the slack where it is
# useful (between the two columns) and makes the remaining gap an OUTPUT that the
# assertion below checks rather than a constant someone has to keep true by hand.
#
# TWO DIFFERENT RULES ON PURPOSE, and mixing them is what produced the 1.5:
#   * PART TO BOARD EDGE is a BODY rule (JLCPCB's ~1.0 mm), so EDGE_KEEP applies to PKG.
#   * PART TO PART is a LAND rule, so it applies to CRTYD -- and two courtyards that
#     TOUCH are already legal, because the clearance is inside the boundary.
# ── the comb's slot extents in X ────────────────────────────────────────────
# Defined HERE rather than beside the slots themselves (which need _BRG_Y, ~1350 lines
# down) because COL_OPA is measured off the +X slot edge and has to know them.
O_SLOT_CLR = 0.25
# ⚠ THE -X END IS THE BEARING'S, DERIVED -- NOT A MEASUREMENT (user: "likely cuts we need
# to cap to the axel size parametrically"). It used to be _FINGER_X0 = -17.20, recorded as
# "what stands above the board, at the arms". That was true while the arms rose to the
# bearing top at 16.0; it died the moment ARM_TOP dropped to the board's seat, and the slot
# went on being cut for a part that is no longer there. Probed to be sure: the endplate
# puts 0.0 mm3 anywhere in this band within the board's Z.
#
# So the only thing that passes through is the BEARING -- and it does not need its full OD
# of slot. It is a Ø16 cylinder whose centre sits 4.20 BELOW the board, so by the time it
# crosses the board it is already narrowing: 6.81 of half-width at PCB_BOT against 8.00 at
# its equator. Size from the widest section the board actually sees, which is at its
# underside, and the slot shortens by 2.39 mm per bearing.
_BRG_HALF = math.sqrt(max((D.BRIDGE_BEARING_OD / 2) ** 2
                          - (PCB_BOT - D.BRIDGE_BEARING_Z) ** 2, 0.0))
_STRING_EXIT_X = 1.10                   # measured: where a .080 string crosses the board's z
O_SLOT_X0 = D.BRIDGE_AXLE_X - _BRG_HALF - O_SLOT_CLR
# ⚠ THE +X END IS THE STRING'S, and it stays a measurement because nothing else predicts
# it. The bearing only reaches -1.19 here, but the string leaves over the bearing's top and
# descends to the changer, crossing this board's Z band at x 0.95 for a .070 and ~1.08 for
# the .080 the instrument is built to take. Ending the slot at the bearing would have the
# board cut the string.
O_SLOT_X1 = _STRING_EXIT_X + O_SLOT_CLR

# ⚠ THE QUAD TIAs LIVE ON THE +X BAND NOW, PAST THE BRIDGE (user, 2026-09-23). They were
# beside the detectors, which is the textbook place for a transimpedance amp -- and it is
# what pinned the whole board 0.61 mm below the axle, because SOIC-14 is 1.75 tall against
# the PD15's 1.10 and BOTH sat under the strings. Past the bridge termination nothing runs
# overhead, so height there is free, and the detector becomes the tallest part under the
# field. That is the entire reason the board can now rest on the axle and carry a comb.
# WHAT IT COSTS, measured rather than assumed: the summing node is the board's one high-Z
# net and it goes from ~8 mm to ~30 mm. Over the In1 plane that is ~3.6 pF on a 25 pF Cin,
# moving the en*2*pi*f*Cin term 0.090 -> 0.103 pA/rtHz: 0.22 dB, against ~4 dB bought by
# the smaller gap. The twenty nets do NOT bundle -- they sit on the detectors' own 4.75 mm
# y pitch and cross the comb's strips four to a strip, of eleven a layer can take.
# ⚠ STILL TO CHECK: the TIA pole. More Cin wants more Cf for the same phase margin, and
# the pole is at ~160 kHz with the carrier's sidebands at 28..68 kHz.
# ⚠ AND IT GOES BACK WEST, INTO THE BAND BETWEEN THE DETECTORS AND THE SLOTS (2026-09-23).
# Moving it +X of the slots fixed the height problem and created a worse one: the ADC cells
# were still -X of the sensor row, so the signal crossed the comb TWICE -- detector -28.4 to
# op-amp +5.6 to converter -44.3, forty crossings -- and the -X leg of that was the board's
# one HIGH-Z net making a 33 mm run past ten carrier-driven emitters. Every station's emitter
# is driven at the SAME 192 kHz, so charge coupled into a summing node lands in the lock-in's
# passband IN PHASE with it and does not integrate away: it reads as a fixed offset that is
# indistinguishable from string displacement. Length is the whole lever on that.
# The band -25.86..-15.06 is 10.80 mm of empty board, and string_clr_at() says it takes a
# 1.19 mm package at its -X edge rising to 1.40 at its +X edge -- which is why this could not
# be done before the clearance became a function of x. SOIC-14 at 1.75 is out for good; every
# live candidate (WQFN-16 quad 0.80, VSSOP-8 dual 1.10, SC-70-5 single 1.10) clears it.
# So: summing nodes ~6 mm instead of 33, and the comb is crossed ONCE, by the op-amp's
# LOW-IMPEDANCE OUTPUT, which is the one signal on the board that does not care.
# ⚠ OP_PKG IS PROVISIONAL -- the channel count is still open (10 duals vs 5 quads vs 21
# singles). The COLUMN is not provisional: it is derived off the detector land, so whichever
# part wins keeps this x and only the Y pitch changes.
# ⚠ ONE DUAL PER STRING, NOT A QUAD PER PAIR (user, 2026-09-23). The quad was never a
# design choice, it was an assumption nobody revisited, and it was the whole sourcing
# crisis: TLV9061/9062/9064 are the SAME DIE on one datasheet, and JLCPCB stocks 107 of
# the quad against 34,405 of the dual at a third the price. But the reason it is also the
# right ELECTRICAL answer is the geometry here. A quad serves four detectors spanning
# 14.25 mm of y, so three of its four summing nodes -- the board's only high-z nets --
# run past neighbouring stations whose emitters all carry the SAME 192 kHz carrier.
# Coupling from those lands in the lock-in passband IN PHASE and reads as displacement.
# A dual serves ONE string's two detectors, 4.75 mm apart, so every summing node is the
# same short length and they are mirror images of each other.
# AND THE MATCHED PAIR ENDS UP ON ONE DIE, which is what DIFF wants: anything that
# perturbs both halves together -- supply, substrate, temperature -- is common mode and
# cancels in A-B. The survey counted the shared die against the dual; for a differenced
# pair that is backwards, and it is the single best argument for this package.
OP_PKG    = "VSSOP-8"
# ROTATED so the pin rows face +-Y: -INA then lands on the +Y side facing PD-A and -INB
# on the -Y side facing PD-B, one short mirror-image run each. Unrotated the two inputs
# are on opposite X flanks and one detector has to reach around the body.
OP_ROT    = 270.0
_OP_W     = CRTYD[OP_PKG][1] if OP_ROT % 180.0 == 90.0 else CRTYD[OP_PKG][0]
_OP_H     = CRTYD[OP_PKG][0] if OP_ROT % 180.0 == 90.0 else CRTYD[OP_PKG][1]
# V+ (pin 8) is the OUTERMOST pin of the -Y row: three half-pitches off the package
# centre on a 0.65 mm VSSOP. Cd is placed against it, so this is a routing fact and
# belongs beside the package, not inside the placement loop.
_OP_VP_DX = 1.5 * 0.65
COL_OPA   = (PD_X + CRTYD["PD15"][0] / 2) + PKG_CLR + _OP_W / 2
# gap from the op-amp land to the SLOTS -- this is the room the feedback network lives in
PART_KEEP = O_SLOT_X0 - (COL_OPA + _OP_W / 2)
assert PART_KEEP >= 0.0, (
    "the sensing strip no longer fits its two columns: the sensor row's land and the "
    "op-amps' land overlap by %.2f mm. The band is %.2f wide and the lands need "
    "%.2f. Either the deck band grew narrower or a package changed."
    % (-PART_KEEP, O_SLOT_X0 - (PD_X + CRTYD["PD15"][0] / 2),
       CRTYD["PD15"][0] + _OP_W + 2 * PKG_CLR))
COVER_X0  = COL_OPA + _OP_W / 2 + 0.5             # lid's -X edge, -22.00
# Lid Y half-span, sized off the OUTERMOST APERTURE rather than the sensing field: the
# slot is wider than the triplet it serves (SLOT_DY 5.0 against 4.45 of packages), so
# referencing SENSE_HL left only 0.1 of material outboard of the last slot -- a knife edge
# (user-caught). Two full beads past the aperture instead.
COVER_HY  = _OUTER_Y + SLOT_DY / 2 + D.MIN_WALL_2P
# ⚠ THE ROW PITCH WAS NEVER THE CONSTRAINT -- THE GAPS WERE SHARED. Each quad's
# feedback cluster sits in a Y gap beside it, and `s` used to alternate, so U1's cluster
# pointed -Y and U2's pointed +Y: BOTH INTO THE SAME GAP, back to back, two four-row
# grids in the 18.73 mm between two quads. That is why the pitch could not be widened --
# every extra 0.1 a row closed 0.6 between Cd12 and Cd22, which is the collision the
# placement assert reported and which my arithmetic (they are 37 mm apart!) could not
# explain: I was reading the two clusters as belonging to different gaps.
#
# EVERY CLUSTER NOW HANGS BELOW ITS OWN QUAD, so each gap holds exactly one. The budget
# stops being "half a gap" and becomes a whole one, and it is not close:
#
#   nearest row  >= SOIC_crtyd_Y/2 + 0402_crtyd_Y/2 + clearance  ->  5.39
#   farthest row <= 2*PITCH - the same                           -> 13.34
#
# 5.6 .. 11.6 at a 2.0 pitch sits inside that with 1.7 mm to spare. The point is not the
# spare: it is that a 2.0 pitch leaves 0.97 mm of clear board between one row's courtyard
# and the next, where 1.15 left 0.12. A 0.25 track plus its clearance is 0.377, so the
# grid now has ROUTING CHANNELS BETWEEN ITS ROWS -- two lanes' worth -- and before it had
# none at all. Thirteen of the router's failures were TIA nets trying to cross this field.
FB_PITCH = 2.0                                # 0402 grid in the Y gaps, column pitch
# ⚠ 2.4, SIZED FOR A VIA AND NOT FOR A TRACK. At 2.0 the channel between two rows is
# 0.97 mm, which takes two 0.25 tracks and NOT a via: a 0.6 via with 0.14 clearance
# needs 0.88 mm of clear board, so at 0.97 it fits only if it is centred to within
# 0.04 mm. That matters because the connection that keeps failing in this field is a
# feedback resistor to its own op-amp OUTPUT, 9.5 mm away past the SOIC -- a trip the
# top layer cannot make at all, so it needs two vias, in these channels.
# 2.4 gives 1.37 mm: a via with room to be placed rather than threaded. The ceiling
# is 2.58 (the next quad's courtyard), so this still leaves margin.
FB_ROW_PITCH = 2.4
FB_ROWS = tuple(5.6 + k * FB_ROW_PITCH for k in range(4))
# No per-quad pull any more. U1 needed one because it was the squeezed half of the shared
# U1/U2 gap; nothing is squeezed now. (U1 still hangs BELOW its quad rather than above --
# the jack's access hole takes the gap above it -- but so does every other cluster.)
FB_ROWS_U1 = FB_ROWS


# The converter cells' input fan (see 3e in _parts): cap x per input, relative to the
# converter's centre with the part turned 180. Module-level so elec/optical.py lays the
# fan's copper from the same numbers the caps are placed by.
CELL_FAN = {"IN4M": -2.30, "IN4P": -1.50, "IN3M": -0.90, "IN3P": -0.30,
            "IN2M": 0.30, "IN2P": 0.90, "IN1M": 1.50, "IN1P": 2.10}
CELL_NEAR = 3.75                                 # near-row cap centre above the part's centre
CELL_FAR = CELL_NEAR + 1.95 + 0.15               # far row (0402 on end + CRTYD_GAP)


def _members(it):
    """One item, or the members of a CLUSTER that must be placed adjacent."""
    return it if isinstance(it[0], tuple) else (it,)


def _item_w(it):
    """⚠ A CLUSTER IS ONE ITEM AS FAR AS THE PACKER IS CONCERNED. Its members are laid
    out touching, at CRTYD_GAP, and the row's leftover space is shared between CLUSTERS
    -- never inside one. That is the whole mechanism: a decoupling capacitor cannot be
    separated from the part it decouples by a packer that has no idea they are related."""
    ms = _members(it)
    return sum(CRTYD[m[2]][0] for m in ms) + CRTYD_GAP * (len(ms) - 1)


def _item_h(it):
    return max(CRTYD[m[2]][1] for m in _members(it))


def _reserve_split(items, left_cap, right_cap):
    """Partition one row's items into the two sub-spans either side of a corridor.

    Returns (left, right, overflow). ONE source of truth for the split: _spread uses it
    to place a row and _block uses it to decide where the row breaks, so the packer
    cannot believe a row fits while the placer finds it does not. Items keep the row's
    own left-to-right order, and the left sub-span fills first.
    """
    left, right, over = [], [], []
    lu = ru = 0.0
    for it in items:
        w = _item_w(it)
        need_l = lu + w + (CRTYD_GAP if left else 0.0)
        need_r = ru + w + (CRTYD_GAP if right else 0.0)
        if need_l <= left_cap:
            left.append(it)
            lu = need_l
        elif need_r <= right_cap:
            right.append(it)
            ru = need_r
        else:
            over.append(it)
    return left, right, over


def _spread(out, y, items, x0, x1, reserve=None):
    """Lay a row out evenly between x0 and x1, optionally leaving a CORRIDOR empty.

    ⚠ THE CORRIDOR IS THE POINT OF `reserve` (user, 2026-09-25: "it would be useful to
    split up the long east west wall so it can have a clear path to the MCU"). A row of
    parts is not a wall because of the parts -- they are SMD and the inner layers pass
    under them -- it is a wall because of their ESCAPE VIAS, which pierce every layer and
    stand where the parts stand. Measured on the power row: 26 vias shadowing 38% of the
    board's width on In2, and where two such rows disagree about where their gaps are,
    only 42% of the width is clear through both.
    Spreading the row more evenly cannot fix that; the vias just spread with it. What
    fixes it is a band with NOTHING in it, wide enough to be worth crossing, put where the
    crossing traffic actually is.
    """
    if reserve:
        lo, hi = reserve
        left, right, over = _reserve_split(items, lo - x0, x1 - hi)
        if over:
            # ⚠ NEVER SILENTLY OVERFLOW. The old split put everything that did not fit
            # on the left into `right` WITHOUT checking the right sub-span held it, and
            # _spread then divided a span smaller than its contents -- a NEGATIVE gap,
            # i.e. parts laid on top of each other. It surfaced as
            # "courtyards_overlap: C133 + FB1" only after a 30 minute route, because
            # nothing between here and DRC looks at spacing. _block packs against the
            # same helper now, so reaching this is a bug rather than a tight board.
            raise ValueError(
                "row at y %.2f overflows the corridor split: %s does not fit in "
                "%.2f + %.2f mm either side of the reserve"
                % (y, ", ".join(_members(it)[0][0] for it in over), lo - x0, x1 - hi))
        if left:
            _spread(out, y, left, x0, lo)
        if right:
            _spread(out, y, right, hi, x1)
        return
    widths = [_item_w(it) for it in items]
    gap = ((x1 - x0) - sum(widths)) / max(len(items) - 1, 1)
    if gap < 0.0:
        raise ValueError("row at y %.2f is %.2f mm wider than the %.2f mm it is given"
                         % (y, sum(widths) - (x1 - x0), x1 - x0))
    cx = x0
    for it, w in zip(items, widths):
        mx = cx
        for ref, desc, pkg in _members(it):
            mw = CRTYD[pkg][0]
            out.append({"ref": ref, "desc": desc, "pkg": pkg, "x": mx + mw / 2, "y": y})
            mx += mw + CRTYD_GAP
        cx += w + gap


def _block(out, y, items, x0, x1, reserve=None, reserve_y=None):
    """Pack parts into as many rows as they NEED, marching -Y from y; return the -Y edge.
    Rows are packed, not hand-assigned: hand-tuned rows went under the placement
    clearance every time a part was added, and the board length has to be an OUTPUT of
    the part list rather than a number parts get squeezed into."""
    span = (x1 - x0) - ((reserve[1] - reserve[0]) if reserve else 0.0)
    ws = [_item_w(it) for it in items]

    def flush(row, y):
        if not row:
            return y
        h = max(_item_h(it) for it in row)
        # ⚠ ONLY THE ROWS THE TRAFFIC CROSSES PAY FOR THE CORRIDOR. `reserve` used to
        # apply to EVERY row in the block, so rows south of the PHY -- which no ULPI net
        # ever crosses -- gave up the same 7-9 mm as the rows between the MCU and the PHY.
        # That is what made a 9 mm corridor cost an extra row and push the board past the
        # endplate's conduit limit. Charge it to the rows in `reserve_y` and let the rest
        # use the full width.
        ry = y - h / 2
        use = reserve if (reserve_y is None or reserve_y[0] <= ry <= reserve_y[1]) else None
        _spread(out, ry, row, x0, x1, use)
        return y - h - CRTYD_GAP

    def pack(limit):
        """Rows, breaking whenever the next part would take the row past `limit`."""
        rows, row, used = [], [], 0.0
        for it, w in zip(items, ws):
            need = used + w + (CRTYD_GAP if row else 0.0)
            if row and need > limit:
                rows.append(row)
                row, used, need = [], 0.0, w
            row.append(it)
            used = need
        if row:
            rows.append(row)
        return rows

    # ⚠ BALANCE THE ROWS, DO NOT JUST FILL THEM. Greedy packing puts every part it can in
    # the first row and leaves the last one short, and _spread then distributes each row
    # over the SAME span -- so a full row lands at CRTYD_GAP, touching, while its
    # neighbour sits at four millimetres. Measured on this board's power block: two rows
    # at 0.15 and 0.15 mm under a row at 4.31, which is the whole clearance budget spent
    # on one row and none of it on the others. It is also the region the user picked out
    # of the routed board by eye as the one with no room in it (2026-09-25).
    #
    # The fewest rows the parts fit in does not change -- that is what `span` decides and
    # the board length depends on it. What changes is how they are shared out: aim for
    # equal used width, and if that needs an extra row, relax the target until it does
    # not. Costs no board area at all.
    # ⚠ A RESERVED ROW HAS TWO CAPACITIES, NOT ONE, and packing against their SUM is
    # what let a row be declared to fit and then overlap when it was placed. `span` says
    # the parts fit in the width outside the corridor; it does not say they fit in the
    # two PIECES that width comes in. Pack against the same split _spread places with.
    if reserve:
        # ⚠ PACK AGAINST THE CAPACITY THE ROW WILL ACTUALLY BE PLACED WITH. A row in the
        # corridor's y-range has TWO capacities (either side of the reserve) and a row
        # outside it has the full width, so the packer has to march y as it goes -- it
        # cannot decide row breaks before it knows where the row lands. Packing against
        # the sum is what let a row be declared to fit and then overlap when placed.
        _lcap, _rcap = reserve[0] - x0, x1 - reserve[1]

        def _reserved_at(row_):
            ry_ = cy - max(_item_h(i) for i in row_) / 2.0
            return reserve_y is None or reserve_y[0] <= ry_ <= reserve_y[1]

        def _fits(row_):
            if _reserved_at(row_):
                return not _reserve_split(row_, _lcap, _rcap)[2]
            return (sum(_item_w(i) for i in row_)
                    + CRTYD_GAP * (len(row_) - 1)) <= (x1 - x0)

        rows, row, cy = [], [], y
        for it in items:
            if not row:
                row = [it]
                if not _fits(row):
                    raise ValueError(
                        "%s does not fit any row here (%.2f / %.2f mm either side of the "
                        "reserve, %.2f mm full width)"
                        % (_members(it)[0][0], _lcap, _rcap, x1 - x0))
                continue
            if _fits(row + [it]):
                row = row + [it]
            else:
                rows.append(row)
                cy -= max(_item_h(i) for i in row) + CRTYD_GAP
                row = [it]
        if row:
            rows.append(row)
        for row in rows:
            y = flush(row, y)
        return y

    n = len(pack(span))
    rows = pack(span)
    if n > 1:
        total = sum(ws) + CRTYD_GAP * (len(items) - 1)
        target = total / n
        while target <= span:
            cand = pack(target)
            if len(cand) <= n:
                rows = cand
                break
            target += 0.25
    for row in rows:
        y = flush(row, y)
    return y


# ── ACCESS HOLE FOR THE PICKUP'S +Y HEIGHT JACK (user) ──────────────────────
# One of the pickup plate's three M4 height jacks lands under this board -- at the +Y
# corner nearest the bridge -- and there is nowhere for it to go: the plate needs it out
# at that corner for leverage. So the board gets out of its way instead.
#
# WHAT IT COST, so the next person does not undo it by tidying: the hole sits ON the
# op-amp column, 0.08 mm from where Cf14 used to be, and U1's whole feedback/decoupling
# cluster had to move. There was no free gap to move it to -- every quad already uses the
# Y gap above itself -- so U1 alone now uses the gap BELOW, and its rows are pulled in
# closer to the quad than the shared FB_ROWS to clear U2's cluster underneath. That is
# electrically fine and arguably better: the feedback loop got shorter, not longer.
#
# Shrinking the hole to driver size does NOT buy that move back -- checked, not assumed:
# the hole is centred in the gap above U1, so a shared-row cluster there still fouls it by
# 2.20 at O4.4. And the pull is not the hole's doing either; it is U2's cluster below that
# sets it. Both survive the diameter change untouched.
JACK_ACCESS_XY = TP.JACK_POS[0]                 # THE JACK'S OWN POSITION, read from
                                                # top_plate -- not a copy of it, so the
                                                # hole cannot drift off the screw
# SIZED FOR THE DRIVER, NOT THE SCREW (user). It was O8.0 -- big enough to pass the M4
# button head, so the jack could be removed through the board. It does not need to be:
# the screw is captured in the deck and stays there; all this hole has to do is let a key
# reach its socket to tighten or slacken it. An ISO 7380 M4 takes a 2.5 hex, 2.887 across
# corners, so M4's own clearance hole passes it with 1.5 of slop for the board's
# positional tolerance -- and it is a number this project already has rather than one
# invented here.
JACK_ACCESS_D  = M4.shaft_clr_d                 # 4.4
# what actually has to fit past the board edge: the KEY, not its clearance hole
_HEX25_R = 2.887 / 2.0
# ⚠ ASKED FOR, MEASURED, AND FOUND UNNECESSARY -- DO NOT RE-CUT IT (2026-09-29). The user
# reported from a render that the pickup height screw looked hard to reach and asked for "a
# little trim". Both a wider endplate relief and a scallop in the board's -X edge were built
# and then REVERTED, because the measurement does not support either.
# tools/_probe_jack_swept.py sweeps the column above each jack head, BEFORE any trim:
#       O2.887 (the 2.5 mm hex key)  jack 0 CLEAR   jacks 1,2 CLEAR
#       O4.000                       jack 0 CLEAR   jacks 1,2 CLEAR
#       O5.000                       jack 0  2.8 mm3 (optical_pcb only)
#       O6.000                       jack 0 16.2 mm3 (bridge_endplate 9.6 + optical_pcb 6.6)
#       O8.000                       jacks 1,2 STILL CLEAR
# ⚠ THE REQUIREMENT IS REACHING THE HEAD, NOT WITHDRAWING THE SCREW (user). A O2.887 key in a
# O4.0 clear column has 0.56 mm all round. Nothing was ever blocked; the O6.0 figure that
# started this came from a probe sized for a driver BODY, which was an assumption about the
# tool, not a requirement. Jack 0 is tighter than jacks 1 and 2 (O4.0 against O8.0) and that
# asymmetry is real and visible -- it is simply not a problem.
# ⚠ AND WIDENING WOULD HAVE TAKEN STRUCTURE OUT FOR NOTHING. jack_access is cut through the
# endplate's PAD, and the comment at that cut says "the pad is structure". This project
# already settled the principle on pi_cap_relief, where a pocket cost wall strength: the
# answer is to not need it, not to make it smaller.
# The scallop in the board's edge would have been 0.725 mm deep at O5.0 and 1.225 at O6.0 --
# genuinely small, and copper-free until O6.4, where a MID track comes within 0.259 mm -- but
# it changes Edge.Cuts, which costs a full re-route on a board at 0 violations, and the user
# confirmed from a top view that the head is reachable as built.




# ⚠ WHERE A GIVEN LQFP PIN IS, DERIVED RATHER THAN MEASURED ONCE AND PASTED. The two
# VCAP capacitors have to sit at their own pins, and the first version of that hard-coded
# the offsets (+7.25 and 12.68/-7.25) with a comment claiming they were read back from the
# placed board. They were not: they were numbers copied out of one measurement, and
# nothing would have caught them going stale when the package, the rotation or the pin
# assignment changed -- which is the exact failure this file keeps finding elsewhere.
#
# KiCad numbers an LQFP from the top of the LEFT edge, down that edge, along the BOTTOM
# left to right, up the RIGHT, then along the TOP right to left. So the along-edge
# coordinate is exact arithmetic from the pitch, and only the pad RING is a property of
# the footprint that this file cannot read.
_LQFP_RING = 12.675      # pad-centre radius of LQFP-176_24x24mm_P0.5mm, read off the
                         # footprint's own pads. The only measured number here.
# ⚠ THE PIN NUMBERS ARE DUPLICATED FROM elec/optical.py's PIN MAP, and the copy is
# CHECKED rather than trusted -- elec/optical.py asserts these two against its own
# map every time it generates a netlist. A silent divergence would put the H7's
# core-regulator capacitors beside the wrong pins, which is not something the
# placement asserts, DRC or the router could ever notice.
VCAP1_PIN, VCAP2_PIN = 81, 125


def _lqfp_pin_offset(pin, n_pins=176, pitch=0.5, ring=_LQFP_RING):
    """(dx, dy) of an LQFP pin from the package centre, IN THE FOOTPRINT'S OWN AXES.

    ⚠ FOOTPRINT AXES, NOT CAD AXES, and the difference is a sign that has already been
    got wrong once. KiCad's y runs the opposite way to this file's, so a caller placing
    a part at a pin uses  +dx  and  -dy.  Returning the footprint's own frame is the
    version that can be checked against the .kicad_mod, which is the whole point.

    ⚠ THE FIRST VERSION OF THIS HAD EDGES 1 AND 3 INVERTED IN Y and nobody would have
    noticed: it was validated on VCAP1 and VCAP2 only, and those two happen not to
    expose the bug -- VCAP1's placement uses the X alone, and VCAP2 is on edge 2, which
    was right. Checking all 176 pads against the footprint is what found it. The two
    asserts below pin the convention so a future edit cannot quietly re-break it.
    """
    per = n_pins // 4
    edge, k = divmod(pin - 1, per)
    along = (k - (per - 1) / 2.0) * pitch
    if edge == 0:                       # left edge, pin 1 at its -Y end, numbering +Y
        return -ring, along
    if edge == 1:                       # bottom edge (+Y in KiCad), left to right
        return along, ring
    if edge == 2:                       # right edge, +Y to -Y
        return ring, -along
    return -along, -ring                # top edge (-Y in KiCad), right to left


# Read straight off LQFP-176_24x24mm_P0.5mm.kicad_mod. Every one of the 176 pads was
# compared against this function once; these two are kept as the standing guard.
assert _lqfp_pin_offset(81) == (7.25, 12.675), _lqfp_pin_offset(81)
assert _lqfp_pin_offset(125) == (12.675, -7.25), _lqfp_pin_offset(125)
assert _lqfp_pin_offset(1) == (-12.675, -10.75), _lqfp_pin_offset(1)
assert _lqfp_pin_offset(176) == (-10.75, -12.675), _lqfp_pin_offset(176)


def _parts():
    """EVERY component on the strip, with its package and placed centre. ONE source of
    truth for the 3D model, the area budget, the clearance assertions and BOM.md."""
    P = []

    def _part_y(ref):
        """The y a part was ACTUALLY placed at -- so nothing re-derives a sibling's."""
        return next(q["y"] for q in P if q["ref"] == ref)

    def _part_x(ref):
        return next(q["x"] for q in P if q["ref"] == ref)

    def add(ref, desc, pkg, x, y, rot=0.0):
        # ROT IS A ROUTING FACT, not a drawing preference: it says which way a part's
        # pins face, and for anything on a high-speed net that is the placement. Only
        # SQUARE or symmetric-envelope packages may use it as written -- the envelope
        # tables here are (w, h) and are NOT swapped for 90/270, so a rotated oblong
        # would be modelled at the wrong size. Assert rather than silently mis-model.
        assert rot in (0.0, 90.0, 180.0, 270.0), (
            "%s: rot %g -- only right angles, so `part_wh` can swap the envelope's axes "
            "instead of rotating a rectangle into something the tables cannot describe."
            % (ref, rot))
        P.append({"ref": ref, "desc": desc, "pkg": pkg, "x": x, "y": y, "rot": rot})

    # ---- 1. sensing row, ON THE STRING FAN, + per-string ballast in the Y gaps ----
    for i in range(D.N_STRINGS):
        n, sy = i + 1, string_y_at(i, SENSE_X)
        add("D%d" % n, "IR emitter, 940 nm, Lite-On LTE-C9901 (65 deg FULL angle)",
            LED_PKG_NAME, SENSE_X, sy)
        # ⚠ NOT TURNED. The cathode (pad 2) is the footprint's +1.65 pair, and +X on this
        # board is TOWARD the op-amps -- so 0 deg already faces the summing node at the
        # column it feeds. This carried a 180 from 2026-09-21 whose note had the
        # direction backwards ("pad 2 ... at 0 deg, i.e. on the far side from the
        # op-amps"); it is the near side. The rotation therefore did the exact thing it
        # was written to prevent, and put the board's most sensitive net on the wrong
        # side of a 3.3 mm part for three days.
        # What it cost, measured on the routed board before the fix: the A summing node
        # climbed 2.0 mm NORTH over the feedback row and came back, 8 segments; the B one
        # took FOUR vias and cut diagonally across the detector lands on In2. 6.56 mm
        # pad-to-pin either way, against 3.29 now, on a 1 MOhm node.
        # MID takes the long way instead, which is the whole point -- it is a buffered
        # reference, the one net up here that does not care about length.
        add("PD%dA" % n, "PIN photodiode, Everlight PD15-22B (daylight filter), +Y", "PD15", PD_X, sy + PD_DY, 0.0)
        add("PD%dB" % n, "PIN photodiode, Everlight PD15-22B (daylight filter), -Y", "PD15", PD_X, sy - PD_DY, 0.0)
        # ballast rides in the gap just -Y of its own emitter, same X band: no column to
        # spare, and it keeps the high-di/dt emitter loop a couple of mm long
        # 0402 since the PD15 triplet: an 0603's courtyard reaches the detector's
        add("R%d" % n, "LED current-set (per-string value)", "0402", SENSE_X, sy - PITCH / 2)

    # ---- 2. the 20 TIAs: one DUAL per STRING, on that string's own y ----
    # Refs start at U21: U6-U18 are taken (MCU, PHY, LDOs, ESD, buffer, buck, converters)
    # and renumbering those would churn the whole netlist for nothing.
    # The feedback network sits +X of its own dual on the SAME y -- the band is 10.80 wide
    # and the dual takes 3.60 of it, so there is a real column there now. That is new: with
    # quads the cluster had to go in the Y GAP between pairs, because a 7.49 mm SOIC-14
    # left no X. Rf and Cf on their channel's own side of the part, so the feedback loop
    # closes beside the pins it belongs to instead of reaching across the package.
    for i in range(D.N_STRINGS):
        n, cy = i + 1, string_y_at(i, SENSE_X)
        add("U%d" % (20 + n), "dual op-amp -- 2x TIA, string %d's A and B detectors" % n,
            OP_PKG, COL_OPA, cy, OP_ROT)
        _fx0 = COL_OPA + _OP_W / 2 + CRTYD_GAP + CRTYD["0402"][1] / 2
        _fx1 = _fx0 + CRTYD["0402"][1] + CRTYD_GAP
        _fdy = CRTYD["0402"][0] + CRTYD_GAP
        for sec, sgn in (("A", 1.0), ("B", -1.0)):
            add("Rf%d%s" % (n, sec), "TIA feedback resistor, string %d%s "
                "(per-string value)" % (n, sec), "0402", _fx0, cy + sgn * _fdy, 90.0)
            add("Cf%d%s" % (n, sec), "TIA feedback cap, string %d%s (anti-alias pole)"
                % (n, sec), "0402", _fx1, cy + sgn * _fdy, 90.0)
        # ⚠ Cd SITS UNDER PIN 8, NOT IN THE FEEDBACK COLUMN, and the move was worth ten
        # unconnected nets. At (_fx1, cy) it was 3.13 mm from V+ with the B channel's
        # FEEDBACK RESISTOR squarely between the two: every straight line from the cap
        # to the pin passes Rf<n>B's output pad 0.33 mm off the centreline against the
        # 0.64 mm that pad and a 0.2 track need, and every elbow either runs down the
        # Cf column through Cf<n>B or comes back along y = pin 8 and clears Rf<n>B's pad
        # by 0.52 mm against 0.51 required. Ten microns, ten times over -- one of the
        # four repeating unconnected nets the user marked up in the render.
        # Directly -Y of the pin the run is 1.28 mm of straight track in an empty band,
        # it is SHORTER than it was (a decoupling loop is the one place length is the
        # whole point), and it is the same on every string.
        # 270, not 90, so pad 1 (+3V3A) faces the pin and pad 2 (GND) faces the plane.
        add("Cd%d" % n, "op-amp decoupling, string %d's dual" % n, "0402",
            COL_OPA + _OP_VP_DX,
            cy - (_OP_H / 2 + CRTYD_GAP + CRTYD["0402"][0] / 2), 270.0)

    # ---- 3. digital block, in the wide tail past the pickup cavity ----
    # ⚠ A RESERVED ROUTING LANE ON THE EAST EDGE (user, 2026-09-25: "if there was a way to
    # move this stuff slightly west we could open up some traces to run along the east edge
    # of the board"). Every row here was packed out to TAIL_X1 - EDGE_KEEP, so Y1, R38,
    # C143 and C133 ended with 1.25 mm between them and Edge.Cuts -- the board's only
    # full-height lane, and too thin to route. Backing the row band off 3.0 opens it to
    # 4.25 without moving any part relative to another.
    # ⚠ THE MCU DOES NOT COME INTO IT, which is worth recording because it looks like it
    # should. The user's reading was that the MCU would have to move west too, and the
    # measurement says otherwise: that column is anchored to the ROW BAND's east limit
    # (x1), not to _part_x("U6"), so the MCU's east face is 10 mm short of it. Backing the
    # MCU off the mount by 3.0 was tried first and moved the lane not at all.
    EAST_LANE = 0.0
    x0, x1 = COMPUTE_X0 + EDGE_KEEP, TAIL_X1 - EDGE_KEEP - EAST_LANE
    # THE MCU CLIMBS INTO THE WRAP BAND (user). It used to start below WRAP_Y, clear of the
    # seam, which cost ~9.75 mm of board on the -Y end for nothing: the wrap band is WIDER
    # in X than the compute section, and the only thing in it is the tail screw. Tucking the
    # LQFP144 hard -X and moving that screw hard +X lets the two share the band, and every
    # row below inherits the saving. The board's -Y end is a cantilever, so length taken off
    # here is worth more than the same length taken off anywhere else.
    # LQFP176, not LQFP144: the ZIT6 went out of stock (see U6 in elec/optical.py).
    # ⚠ THE MCU STAYS AT THIS Y, AND THE ARGUMENT FOR MOVING IT WAS WRONG (2026-09-23).
    # The case made for pushing it -Y was that it sits 0.15 mm off the sensing strip,
    # jammed +Y, which shortens the SAI/TDM lanes (slow) at the expense of ULPI (60 MHz,
    # 12 signals, 19.87 mm) -- i.e. it optimised the wrong bus. That compared two clock
    # rates without checking whether either was stressed, and neither is:
    #   ULPI over 19.87 mm is 0.132 ns, 0.79 % of a 16.67 ns period, against a 2-3 ns
    #     setup/hold budget. Reflection would need ~38 mm at a 1.5 ns edge.
    #   SAI is 8 ch x 32 bit x 48 kHz = 12.29 MHz, not "a few" -- the two buses are far
    #     closer together than the headline numbers suggest.
    #   and the FARTHEST converter is 89 mm away whatever the MCU does, because that run
    #     is set by the sensing strip's length, not by this y.
    # So there is no timing case, and moving a 176-pin part rearranges every row below it.
    # If it moves it will be because the ROUTER says so, not because of a dimension: see
    # .ins/routefan.sh, "reasoning about which single change to spend an hour on has been
    # wrong more often than right, because the surface is not smooth enough to reason
    # about locally". This file has lost that argument before.
    _MCU_PKG = "LQFP176"
    y = Y_TAIL - CRTYD_GAP
    y -= CRTYD[_MCU_PKG][1] / 2
    # X is anchored to the TAIL SCREW, not to the board edge. The screw is the only hard
    # obstacle on this row, so the MCU sits as far +X as it may -- which is what turns the
    # straightened -X edge into ESCAPE ANNULUS (6.6 mm) instead of just sliding the package
    # along with it. Anchoring to x0 would have kept the old 1.20 mm and wasted the change.
    # (The 6.6 was measured to a -30.42 -X edge that has since moved to -38.88 -- see the
    # datum note above. The annulus is now 26.18 mm, so the argument holds harder, not
    # less. The binding number on the other side is unchanged: ROW_GAP, 1.00 mm to the
    # tail screw's clearance, which is what "as far +X as it may" actually means.)
    # ⚠⚠ THIS NO LONGER READS MOUNT_X_TAIL, AND THE MCU DELIBERATELY DOES NOT TAKE THE ROOM
    # THE SCREW LEFT BEHIND (2026-09-29). When the tail mount moved to the -X plinth this line
    # dragged the MCU 41 mm west with it -- straight off the board -- and two asserts caught it
    # in turn: _assert_mount_heads_clear saw C111 land under the head, then _assert_field_clear
    # saw U6 at X -51.34..-25.34 against a board ending at -32.16. A screw position was
    # silently also a PLACEMENT DATUM.
    # The value is unchanged to the micron: TAIL_X1 - MOUNT_KEEP is exactly what MOUNT_X_TAIL
    # used to be, so U6 and every row derived from it stay where they are.
    # ⚠ AND NOT TAKING THE +7.6 mm IS THE POINT, not an oversight. With no screw on this row
    # the package could now reach the board's edge keep-out instead, but this file's own rule
    # governs: "moving a 176-pin part rearranges every row below it. If it moves it will be
    # because the ROUTER says so, not because of a dimension." The board is at a hard-won
    # 0-unconnected baseline and the whole purpose of moving the mount was to STOP perturbing
    # the placement. The freed room is recorded here for whoever does want to spend it.
    _mcu_x1 = TAIL_X1 - MOUNT_KEEP - MOUNT_CLR - ROW_GAP       # 16.256, frozen at its old value
    add("U6", "MCU -- STM32H743IIT6, 5 SAI TDM lanes from the audio ADCs, USB OTG_HS via ULPI", _MCU_PKG,
        _mcu_x1 - CRTYD[_MCU_PKG][0] / 2, y)
    y -= CRTYD[_MCU_PKG][1] / 2 + CRTYD_GAP

    # POWER + AUDIO INPUT is no longer here -- J2 moved to the -Y EDGE, beside the USB-C,
    # so both cables leave the board at the same end (see the placement after this block).
    # Its decoupling stays in the digital block, near where the rail is consumed.
    # C140 now travels with U9 (see the cluster below); C141-C143 stay here as the
    # +5V rail's distributed bypass.
    # ⚠ AND C112/C113 MOVE HERE FROM THE POWER ROW, WHICH IS WHERE THEY SHOULD ALWAYS
    # HAVE BEEN. They are the H7's CORE REGULATOR capacitors on VCAP1/VCAP2 -- MCU pins,
    # decoupling an internal regulator -- and they were sitting 25 mm away in the power
    # block because that is where the "0805 bulk cap" parts happened to be listed. This
    # row is directly under U6, about 2.5 mm off its courtyard, so the move is roughly a
    # tenfold improvement and it is free: it also gives the power row back the 7.1 mm
    # that C164 needs, which is what stopped the board growing 2.2 mm.
    # Clustered so they stay side by side; which of the two lands nearer its own VCAP pin
    # is a routing question, not a placement one.
    # ⚠ C112 GOES BACK IN THE PACKED BLOCK, AND THE REASON IS GEOMETRY, NOT OVERSIGHT.
    # It wants to sit directly under VCAP1 on U6's -Y edge, and it was hand-placed there
    # -- which produced THREE courtyard violations (against U6 itself and the SWD pads
    # TP1/TP2) that the placement asserts could not see, because they measure BODY
    # clearance and this is a COURTYARD overlap. DRC found them, hidden among the twenty
    # declared sensor-triplet overlaps as a count of 23 rather than 20. That is exactly
    # the failure mode this file worries about elsewhere.
    #
    # The band between U6's courtyard and the MCU decoupling row below it is 1.30 mm.
    # An 0805 courtyard is 2.05 and needs 2.35 with its gaps, so it was never going to
    # fit; and the board cannot be made longer to open the band, because CONDUIT_Y0 is
    # 0.11 mm inside the endplate's exterior-wall limit. An 0402 would fit and is ruled
    # out by this file's own note -- 2.2 uF in an 0402 is marginal.
    #
    # So C112 packs with the rest of the MCU's decoupling, about 12 mm from VCAP1. That
    # is half of the 25 mm it started at and not what a core-regulator capacitor
    # deserves. THE LEVER, if it ever matters: the five SWD pads sit in that row purely
    # because there was space, and moving them would free the x C112 wants. That costs a
    # row somewhere else, which costs board length, which is the 0.11 mm above.
    # C113 is unaffected -- VCAP2 is on the +X edge, where there is a 7.6 mm strip.
    _pwr_row_y = y - 0.5
    _spread(P, _pwr_row_y,
            [("C%d" % (141 + k), "power-input decoupling", "0402") for k in range(3)],
            x0, x1)
    # ⚠ C113 IS PLACED BY HAND BECAUSE ITS PIN IS ON A DIFFERENT EDGE. VCAP1 and VCAP2
    # are not neighbours on the LQFP176: pin 81 is on the package's -Y edge and pin 125
    # is on its +X edge, 12.7 mm across and 7.3 mm up from the centre. One row under the
    # MCU can serve the first and never the second -- clustered there, C113 measured
    # 22.6 mm from the pin it exists for, which is no better than the 25 mm it started
    # at. The H7's core regulator is not a rail to be decoupled loosely; ST specifies
    # 2.2 uF at each VCAP pin and the part boots intermittently rather than cleanly
    # without it, which is the worst way for a fault to present.
    # So it goes in the 7.60 mm strip between U6's +X courtyard and the tail mount, at
    # the pin's own Y -- DERIVED from the LQFP pin numbering, see _lqfp_pin_offset.
    # ⚠ C112 SHARES THE SAME STRIP, at the -Y end of it, nearest its own pin. It does
    # NOT go under the MCU where VCAP1 actually is: that band is 1.30 mm between U6's
    # courtyard and the decoupling row below, an 0805 needs 2.35, and the board cannot
    # grow to open it -- CONDUIT_Y0 is 0.11 mm inside the endplate's wall limit. Placed
    # there by hand it produced three courtyard violations (U6, TP1, TP2) that the
    # placement asserts could not see, because they measure BODY clearance and this is a
    # COURTYARD overlap; DRC reported 23 where 20 are declared, which is exactly how a
    # real fault hides among expected ones. Packing it into either neighbouring block
    # spills that block into a new row and breaks the same conduit assert.
    # So it goes in the strip, about 8 mm from VCAP1 instead of 25 -- worse than C113's
    # 4 mm and much better than the alternative. An 0402 would fit under the MCU and is
    # ruled out by this file's own note: 2.2 uF in an 0402 is marginal.
    _c112_x = _part_x("U6") + CRTYD[_MCU_PKG][0] / 2 + CRTYD_GAP + CRTYD["0805C"][0] / 2
    _c112_y = (_part_y("U6") - CRTYD[_MCU_PKG][1] / 2) + CRTYD["0805C"][1] / 2
    add("C112", "H7 core regulator cap, VCAP1 -- REQUIRED; in the +X strip at the -Y "
        "end, nearest its own pin", "0805C", _c112_x, _c112_y)

    # ⚠ AND THE TAIL MOUNT OWNS THE PIN'S OWN Y. The M4's button head is 7.6 across, so
    # a part has to stay _head_r + PKG_CLR + its own half-height clear of the screw axis
    # -- the placement assert caught C113 at -1.92 and said the head would crush it,
    # which is exactly the check doing its job. So the cap sits at the closest Y the
    # head allows, not at the pin's Y: about 3 mm further -Y, which still lands it ~4 mm
    # from VCAP2 against the 22.6 mm a row under the MCU could manage.
    _c113_x = _part_x("U6") + CRTYD[_MCU_PKG][0] / 2 + CRTYD_GAP + CRTYD["0805C"][0] / 2
    _c113_y = _part_y("U6") - _lqfp_pin_offset(VCAP2_PIN)[1]   # CAD y = -footprint y
    # mount_points() is defined below this function, so the tail screw is rebuilt from
    # the same two constants it uses rather than imported -- if either moves, this moves.
    _head_clear = TP.JACK_HEAD_D / 2 + PKG_CLR + CRTYD["0805C"][1] / 2
    _tail_my = Y_TAIL - MOUNT_KEEP
    if abs(MOUNT_X_TAIL - _c113_x) < CRTYD["0805C"][0] / 2 + TP.JACK_HEAD_D / 2             and abs(_c113_y - _tail_my) < _head_clear:
        _c113_y = _tail_my - _head_clear         # step -Y, away from the head
    add("C113", "H7 core regulator cap, VCAP2 -- REQUIRED; hand-placed beside its own "
        "pin on the +X edge, stepped clear of the tail mount's head", "0805C",
        _c113_x, _c113_y)
    y -= 1.0 + CRTYD_GAP

    # ⚠ THE DECOUPLING IS A RING ROUND THE PACKAGE NOW, NOT A ROW IN THE PACKER.
    # _block fills horizontal rows spanning the whole board width, which is a PACKING
    # strategy with no idea which pin a part serves -- so the MCU's twelve 0402s came out
    # in one line at a fixed y, strung from x -36.7 to -2.0. Eight were more than 5 mm off
    # the body and the farthest was 26.5. At that distance the pin-cap-return loop is
    # 15-20 nH and the capacitor does nothing above a few MHz: they were twelve parts on
    # the right net doing none of the job the net exists for. (The file already knew the
    # shape of this -- see the C112/C113 notes above, 12 mm and 22.6 mm from their own
    # VCAP pins, hand-placed out of the row for exactly this reason. Those two were the
    # symptom that got noticed; the other twelve were the same bug, unexamined.)
    # An LQFP176 has VDD/VSS pairs on all four sides and this board has NO back side to
    # put caps on (Economic tier is single-sided), so they ring the package on top.
    # Six west, six south: the +X strip is already C112/C113's, and the +Y side has 0.15 mm
    # before the sensing strip -- and digital decoupling does not belong in the analog
    # field anyway.
    # ⚠ DERIVED FROM U6, NOT TYPED. The MCU wants to move -Y (ULPI is 60 MHz against the
    # TDM lanes' few MHz, and it is currently jammed +Y against the strip, which optimises
    # the wrong bus). Hanging these off _part_x/_part_y means that move carries them along
    # instead of stranding them, which is how the row got stale in the first place.
    # Even spacing, not pin-exact: the LQFP176 pin table is not in the extracted datasheet
    # text and I will not invent pin numbers. Worst case a cap is half a side (~7 mm) from
    # its nearest VDD pair against 26.5 now, typical 2-4. Pin-exact placement using
    # _lqfp_pin_offset() is a further improvement once the pin list is in hand.
    # ⚠ -X AND +X, NOT -Y, AND THE -Y BAND IS WHY. Between U6's courtyard and the power
    # row there is 11.3 mm, and it already carries the power-input row AND the block with
    # R30/R31 and the five SWD pads. Both collided with a -Y arm in turn, and the obvious
    # fix -- push those rows -Y -- lengthens the board and breaks the conduit assert:
    # CONDUIT_Y0 has 0.11 mm inside the endplate's exterior-wall limit, so nothing down
    # here may grow -Y at all. The two X flanks are genuinely open, so the ring uses them.
    # Eight -X (27.4 mm of clear edge) and four +X, the +X four sitting OUTBOARD of
    # C112/C113 -- those two own the inner lane of that strip and are there because their
    # own VCAP pins are. 4.3 mm off the package for those four, 0.7 for the other eight.
    _dec_off = CRTYD[_MCU_PKG][0] / 2 + CRTYD_GAP + CRTYD["0402"][1] / 2
    _dec_off_e = (CRTYD[_MCU_PKG][0] / 2 + CRTYD_GAP + CRTYD["0805C"][0]
                  + CRTYD_GAP + CRTYD["0402"][1] / 2)
    # ⚠ THE RING IS BACK TO EIGHT WEST AND FOUR EAST, AND THE REASON IS THAT THE TAIL MOUNT
    # LEFT THE +X STRIP (2026-09-29, user). It was briefly rebalanced nine/three because the
    # M4's button head landed on C111 -- 0.25 mm centre to centre -- and a step-away would not
    # fit either way (-Y hit C110 at 1.205 mm, +Y hit R50 at 0.771, where two 0402s need
    # 2.10). That was solving the collision by moving NINE capacitors, and it cost the board
    # its 0 unconnected / 0 violation baseline: the placement change invalidated the SAI_FS
    # post-route repair and the searched bring-up-pad sites, which are both measured against
    # ONE finished route. 10 unconnected and 15 violations, 11 of them SAI_FS.
    # The user's answer was better and is the one in place: move the MOUNT, not the copper.
    # MOUNT_X_TAIL is on the -X plinth now, so nothing here has to dodge a screw head at all,
    # and the ring goes back to the even span it wants. Cost: ONE 0402 (R30) instead of nine.
    # ⚠ AND THIS IS WHY _assert_mount_heads_clear() EXISTS RATHER THAN A GUARD HERE. A rule
    # written into this loop would have to be rewritten every time the mount moves; the assert
    # simply refuses any placement that puts a part under a head, wherever either one goes.
    for _k in range(8):
        add("C%d" % (100 + _k), "MCU decoupling -- -X edge of the package", "0402",
            _part_x("U6") - _dec_off,
            _part_y("U6") + (_k - 3.5) / 3.5 * 11.0, 90.0)
    for _k in range(4):
        add("C%d" % (108 + _k), "MCU decoupling -- +X edge, outboard of C112/C113",
            "0402", _part_x("U6") + _dec_off_e,
            _part_y("U6") + (_k - 1.5) / 1.5 * 9.0, 90.0)

    # ⚠ THE TWO STRAPS GO TO THEIR PINS. They were loose items in the row below, which put
    # R30 26 mm from the BOOT0 pin it pulls down and R31 14 mm from NRST -- so the router
    # escaped both nets INTO the package interior and hauled them across it, through the
    # band where ULPI_DIR, LED_GATE and I2C2_SCL are already fighting for room (the user
    # picked that congestion out of the routed board, 2026-09-25). A pull-up or pull-down's
    # position is not its value; it belongs at the pin, and anywhere else is a net the
    # router has to carry for no reason.
    # They sit in the WEST STRIP, which is 4% copper and the emptiest board on this half,
    # rather than north of the MCU where the handover band is already at 39.5% on In2.
    # ⚠ WEST OF x -16, BECAUSE THE BRIDGE BEARINGS SIT OVER THE STRIP. The band
    # x -16..0, y -49..51 carries the bearing block from z 0 to 16, and the board's top
    # face is at 13.80 -- so NOTHING may stand on the board there. Putting these two at
    # x -12.60 cost 0.481 mm3 of overlap against bridge_bearings, caught by the gate.
    # That also explains why this strip measures 4% copper and reads as "free board": it
    # is free of COPPER because it cannot hold a component, which is not the same thing.
    # ⚠ THESE ARE CAD COORDINATES, NOT BOARD-LOCAL ONES, and getting that wrong put both
    # parts in the string array against Cf9A. CAD = local + (CX, CY) = local + (-3.55,
    # -28.315). Board-local (-14.0, -31.0) and (-14.0, -41.3) -- beside the MCU's west
    # flank, west of its courtyard at -11.10 and of the decoupling column at -8.22.
    # ⚠ R30 STEPS 1.00 mm -Y FOR THE TAIL MOUNT'S HEAD (2026-09-29). The tail M4 moved to the
    # -X plinth, and this is the one part that was under it: 3.545 mm from the screw axis where
    # a 0402 at rot 90 needs 5.025 by CENTRES -- but the guard measures COURTYARD to the head
    # ⚠ THIS IS THE WHOLE COST OF THE MOUNT MOVE -- one 0402, against the nine capacitors that
    # moving the copper instead required. It stays west of CAD x -16 (the bridge bearings sit
    # over x -16..0 and nothing may stand on the board there) and keeps 9.31 mm to R31.
    # It is 1.00 mm further from the BOOT0 pin it pulls down, which is the price and it is small.
    add("R30", "BOOT0 pull-down -- at the pin, stepped clear of the tail mount's head",
        "0402", -17.55, -60.50, rot=90.0)
    add("R31", "NRST pull-up -- at the pin", "0402", -17.55, -69.63, rot=90.0)

    # ⚠ THE BRING-UP PADS, AND EVERY ONE OF THESE FOUR NUMBERS WAS SEARCHED, NOT CHOSEN.
    # An earlier attempt lined them up in a convenient empty row, which left the router an
    # 11.9 mm haul to reach +3V3A; it stranded, and the pressure cost the USB PHY's own
    # supply pin its connection. These sites come from scratchpad/padsite.py, which sweeps
    # a grid over the FINISHED board for a clear 1.5 mm circle that already overlaps its
    # own net's copper -- so no track is needed at all -- and rejects anything inside a
    # footprint's courtyard, because a pad under a part is electrically legal and
    # physically unprobeable. Clearance headroom over the 0.127 rule, per pad:
    #   TP6 I2C2_SDA 1.696 (D1.0)   TP7 I2C2_SCL 0.743 (D1.0)   TP8 BOOT0 0.492
    #   TP9 +24V 4.747   TP10 +5V 1.214   TP11 +3V3A 1.956
    # ⚠ AND THEY ARE PLACED AFTER ROUTING (post_route_refs in elec/optical.py). The CAD
    # still carries them because the fab, the geometry check and this model all need them;
    # only the ROUTER is kept from seeing them.
    # ⚠ CAD COORDINATES = board-local + (-3.55, -28.315).
    for _ref, _desc, _lx, _ly in (

            # ⚠ TP8 IS PROVISIONAL AND MUST BE RE-SEARCHED (2026-09-29). Its old site put it
            # 0.4 mm inside the tail mount's button head once that mount moved to the -X
            # plinth, and a pad under a screw head cannot be probed -- which is why
            # _assert_mount_heads_clear covers TP packages too. This position clears the head
            # by 1.86 mm and sits clear of R30/R31, but it was NOT produced by padsite.py, so
            # it almost certainly does not overlap its own net's copper and will cost BOOT0 a
            # track it should not need.
            # ⚠ ALL SIX PADS NEED RE-SEARCHING AGAINST THE NEW ROUTE ANYWAY, so this is not an
            # extra debt: padsite.py sweeps the FINISHED board, and any placement change
            # invalidates every site it found. The current 15 violations include four on TP7
            # for exactly that reason.
            ("TP8", "bring-up pad -- BOOT0 (hold HIGH at reset)", -12.606, -23.735),
            ("TP9", "bring-up pad -- +24V rail", -20.106, -79.735),
            ("TP10", "bring-up pad -- +5V rail", 21.394, -66.735),
            ("TP11", "bring-up pad -- +3V3A rail", 17.894, -16.235)):
        add(_ref, _desc, "TP", _lx - 3.55, _ly - 28.315)
    for _ref, _desc, _lx, _ly in (
            ("TP6", "bring-up pad -- I2C2 SDA (ROM bootloader bus)", 6.394, 54.265),
            ("TP7", "bring-up pad -- I2C2 SCL (ROM bootloader bus)", 7.394, 61.765)):
        add(_ref, _desc, "TP_SMALL", _lx - 3.55, _ly - 28.315)

    # ⚠ THE PER-CELL SHDNZ PULL-UPS AND THEIR PADS -- item 6, converter isolation. One
    # 0402 and one 1.0 mm pad per converter, in the one clear pocket each cell has: a
    # 1.74 mm circle (an 0402's circumscribed courtyard) sits 2 mm from pin 14 at the SAME
    # cell-frame offset (-3.46, +2.00) in all five cells, because the cells are one pattern
    # repeated. All five converters are rot 180 at x 11.9, y spaced 18.727.
    # ⚠ THE RESISTOR IS VERTICAL (rot 90) SO ITS SOUTH PAD FACES +3V3D. The channel via
    # this pull-up feeds from sits at (8.85, y+0.75), south-east of the site; a horizontal
    # part would put the +3V3D pad on the far side and make that stub cross back under the
    # body. SHDNZ takes the longer stub instead, which is free -- it is a DC-static line.
    # ⚠ AND BOTH ARE PLACED AFTER ROUTING (post_route_refs), so these coordinates are
    # measured against the FINISHED board rather than negotiated with the router.
    # ⚠ THE OFFSETS ARE SEARCHED AGAINST THE ROUTE, AND THE FIRST GUESS WAS WRONG TWICE.
    # (-3.46, +2.00) came from the route BEFORE pin 14 was freed and does not survive it --
    # the router re-used the pocket. And the resistor was modelled as its circumscribed
    # CIRCLE, 1.74 mm across against a 1.5 x 0.9 courtyard, which rejected every site an
    # 0402 actually fits in: as a rectangle the same search finds (-3.462, +3.50) legal in
    # ALL FIVE cells at 0.510 mm of headroom, where the circle offered 0.090.
    # The pad then has to clear the resistor's own courtyard -- 0.75 + 1.025 = 1.8 mm, and
    # the 1.6 mm first guess was five courtyard overlaps in the DRC report. It sits at
    # (-3.810, +6.950), 3.45 mm clear of it.
    for _k, _cy in enumerate((62.0187, 43.2918, 24.565, 5.8382, -12.8887)):
        add("Rs%d1" % (_k + 1), "U%d SHDNZ pull-up (10k to IOVDD)" % (14 + _k), "0402",
            11.9 - 3.462 - 3.55, _cy - 0.75 + 3.500 - 28.315, rot=90.0)
        # ⚠ NO PAD OF ITS OWN -- the resistor's SHDNZ land is the access point. A 1.0 mm
        # pad fits (searched: cell offset (-3.810, +6.950), 0.348 mm headroom) but sits
        # 3.45 mm from the resistor and would need its own stub, which is ~4 mm more copper
        # per cell in the analog strip -- 20 mm over five, and keeping copper out of there
        # is why the per-cell pull-up was chosen over a shared spine in the first place.

    y = _block(P, y,
                     # ⚠ THE SWD PADS, WITHOUT WHICH THIS BOARD CANNOT BE PROGRAMMED
                     # AT ALL -- see the long note in elec/optical.py. They sit in the
                     # MCU's own decoupling block because that is where SWDIO, SWCLK and
                     # NRST already are, so the pads cost three short stubs instead of
                     # three runs across the tail.
                     [("TP1", "SWD pad -- SWDIO", "TP"),
                        ("TP2", "SWD pad -- SWCLK", "TP"),
                        ("TP3", "SWD pad -- NRST (connect under reset)", "TP"),
                        ("TP4", "SWD pad -- GND", "TP"),
                        ("TP5", "SWD pad -- +3V3D target sense", "TP")]
                     # ⚠ R36/R38 ARE HERE FOR BOARD LENGTH, NOT BECAUSE THEY BELONG HERE.
                     # They are Q1's gate series and pull-down and they want to be beside
                     # Q1, which is in the power row -- but trimming the board to V5_PRE
                     # took that row's span from 61.54 to 54.81 mm and these two spilled
                     # into a third row, 3.90 mm of parts costing 1.03 mm of board length
                     # and breaking the conduit's exterior-wall assert by 1.07. This row
                     # was measured 70% empty. Same trade, and the same reasoning, as
                     # C127 in the crystal row below -- one row away instead of one row
                     # longer. Electrically cheap: the LED row switches at the lock-in
                     # carrier, not an edge rate where a few mm of gate lead matters.
                     + [("R36", "LED driver gate resistor", "0402"),
                        ("R38", "LED gate pull-down -- emitters OFF in reset", "0402")],
                     x0, x1)
    # ⚠ THE PHY IS NO LONGER HERE. It used to sit in this row, between the MCU and the
    # connector, on the reasoning that it owns both ends -- 12 ULPI signals up to the
    # MCU, D+/D- down to the port. That balanced the two runs, and it was the wrong
    # trade: ULPI is 60 MHz and forgives a long run (12 mm of mismatch is 0.36% of a
    # bit), while D+/D- is 480 Mbps and forgives nothing. Splitting the difference
    # served the tolerant link at the expense of the critical one.
    # The PHY now lives in the USB cluster at the -Y edge; see section 4b.
    # ⚠ ONLY THE MCU'S CRYSTAL IS LEFT IN THIS ROW. Y2, its two load caps, the PHY's
    # three decoupling caps and R37 all belong to U7, and U7 is 19 to 45 mm away at the
    # -Y edge -- see the PHY SUPPORT CLUSTER in section 4b for why that is a defect and
    # not merely a long trace.
    # ⚠ AND IT IS PLACED, NOT PACKED. _spread distributes a row across the FULL board
    # width, which is right for decoupling and wrong for a crystal: with the PHY's parts
    # gone this row held three, and the packer put Y1 at one edge with its two load caps
    # 29 and 57 mm away. That is the same bug as the PHY's, arrived at from the other
    # direction -- the row did not go stale, it just never had a reason to keep these
    # three together, and "legal" was all the packer was ever asked for.
    # A crystal and its load caps are ONE part in three pieces. They go side by side, at
    # the +X end of the row because the MCU they clock is anchored +X.
    _y1_h = CRTYD["3225"][1]
    _y1_y = y - _y1_h / 2
    _y1_x = x1 - CRTYD["3225"][0] / 2
    add("Y1", "25 MHz crystal -- MCU HSE", "3225", _y1_x, _y1_y)
    _c_dx = CRTYD["3225"][0] / 2 + CRTYD_GAP + CRTYD["0402"][0] / 2
    add("C123", "crystal load cap -- Y1 OSC_IN", "0402", _y1_x - _c_dx, _y1_y)
    add("C124", "crystal load cap -- Y1 OSC_OUT", "0402",
        _y1_x - _c_dx - CRTYD["0402"][0] - CRTYD_GAP, _y1_y)
    y = _y1_y - _y1_h / 2 - CRTYD_GAP
    # U11 is the mid-rail reference the 20 TIAs sit on: single-supply transimpedance needs
    # a bias for the non-inverting inputs, and all 20 quad channels are spoken for.
    # ⚠ THE TWO LDOs TRAVEL WITH THEIR CAPACITORS -- see _item_w. Before this, U8 sat
    # 26.2 mm from its nearest output capacitor and U9 sat 23.1 mm from its, because the
    # packer spread this row evenly and had no idea which capacitor belonged to which
    # regulator. For an LDO the output capacitor is a COMPENSATION ELEMENT, not a filter:
    # both parts were characterised with it at the pin, and 26 mm of track is inductance
    # inside the feedback loop of a device whose stability depends on it.
    y = _block(P, y, [(("C164", "U8 input bulk -- V5_PRE has no other local cap", "0805C"),
                       ("U8", "LDO -- 3V3 digital, TAB package (0.51 W)", "SOT-223"),
                       ("C131", "bulk cap -- 3V3 digital, U8's OUTPUT cap", "0805C")),
                      (("C140", "U9 input bypass -- +5V, the quiet side of FB1", "0402"),
                       ("U9", "LDO -- 3V3 analog (low noise)", "SOT-23-5"),
                       ("C132", "bulk cap -- 3V3 analog, U9's OUTPUT cap", "0805C")),
                      # ⚠ AND SO DOES THE MID DIVIDER, WHICH IS THE SAME DEFECT ONE ROW
                      # LATER. R34 and R35 were loose items in this list, so the packer
                      # spread them 23 mm from U11 -- and MID_RAW, the 4.5 k junction
                      # between them, ran 25 mm across the board into U11 pin 3. That is a
                      # high-impedance antenna feeding the reference ALL TWENTY TIAs sit
                      # on: whatever it picks up arrives at every channel's non-inverting
                      # input at once, which is the one place on this board where a common
                      # error cannot be told from signal. It also cost the router the
                      # +3V3A hop from U11.5 to R34.1, 21 mm, one of the six the board
                      # still fails on.
                      # Divider first so its junction is the pin nearest U11.
                      (("R34", "mid-rail divider, top -- travels with U11", "0402"),
                       ("R35", "mid-rail divider, bottom -- travels with U11", "0402"),
                       ("U11", "single op-amp -- TIA mid-rail reference buffer",
                        "SOT-23-5")),
                      ("Q1", "N-ch MOSFET -- LED row driver", "SOT-23"),
                      ("FB1", "ferrite bead -- analog rail isolation", "0603"),
                      ("C133", "reference bypass", "0805C"),
                      # ⚠ THESE THREE WERE MISSING AND ARE NOT OPTIONAL. They surfaced
                      # when elec/optical.py turned this table into an actual netlist --
                      # which is the point of doing that, because a part that no net
                      # needs looks exactly like a part nobody noticed was absent.
                      #   R37: the ULPI PHY's BIAS resistor. A USB3343 sets its
                      #     transmitter drive current through it, so it is a 1% part and
                      #     without it the PHY does not meet the eye diagram at all.
                      #   R38: a pull-down on the LED row's gate. Without it the ten
                      #     emitters' state while the MCU is in reset is whatever the
                      #     gate capacitance happens to hold -- they must be OFF.
                      #   C112/C113: the H7's CORE REGULATOR caps on VCAP1/VCAP2. The
                      #     part does not boot reliably without them, and it fails
                      #     intermittently rather than cleanly, which is the worst way
                      #     for a missing part to announce itself. 0805 because they are
                      #     2.2 uF and an 0402 at that value is marginal.
                      # R37 IS NOT HERE ANY MORE -- it moved to the PHY cluster at the
                      # -Y edge, where a part that sets a precision current belongs.
                      ],
                     x0, x1,
                     # ⚠ A CORRIDOR THROUGH THE WALL, AT THE PHY's OWN X (user,
                     # 2026-09-25: "it would be useful to split up the long east west wall
                     # so it can have a clear path to the MCU"). U7 sits at x 13.18 and
                     # every ULPI net has to climb from it to the MCU, crossing this row --
                     # the only one of the three southern rows that reaches that far east
                     # (the buck's stops at x +1, and the crystal row is already clear from
                     # -1.8 to 16.3). So the split is needed HERE and only here.
                     # ⚠ 5.5 mm WAS NOT ENOUGH, AND THE ESTIMATE THAT SIZED IT COUNTED
                     # THE WRONG THING. "15 tracks at a 0.4 mm pitch" is the width 12 ULPI
                     # nets need if they arrive as bare tracks -- but they arrive off a
                     # QFN's escape vias, and those land IN the corridor and eat about
                     # 0.9 mm of its width each. Measured on the routed board: 6 vias
                     # inside, 5 of them ULPI, so a third of the corridor was spent on the
                     # vias of the very nets it exists to carry and ULPI_CK, ULPI_D0 and
                     # ULPI_D5 never got across. Same defect as the row it was cut into:
                     # the wall was never the parts, it was their vias.
                     # 7 mm centred on the PHY's own x, and 7 is a CEILING rather than a
                     # preference: at 8 the block needs another row and the board grows
                     # past the endplate's conduit limit. 9 was tried first and appeared
                     # to cost nothing, because _spread was silently overlapping the row
                     # it squeezed -- it surfaced 30 minutes later as
                     # "courtyards_overlap: C133 + FB1". _reserve_split now refuses to
                     # overflow, so what fits here is what actually fits.
                     reserve=(9.70, 16.70))

    # ⚠ C127 GOES IN THE CRYSTAL ROW, NOT THE POWER ROW, AND THE BOARD LENGTH IS WHY.
    # It belongs beside U9 (it is the SPX3819's noise bypass, the reason that part was
    # chosen), but the power row was exactly full: adding a nineteenth part spilled the
    # packer into a new row, grew the board 2.2 mm at the -Y end and broke the conduit's
    # exterior-wall assert by 0.62. The crystal row above has free width, so the cap sits
    # in it at U9's OWN X -- read back, not re-derived -- which puts it one row away
    # instead of one row longer.
    add("C127", "analog LDO noise bypass -- 1 uF on the SPX3819's BYP pin", "0402",
        _part_x("U9"), _y1_y)
    # ⚠ AND C114 GOES THE SAME WAY, FOR THE SAME REASON, MEASURED THE SAME WAY. Putting
    # the MID divider's bypass in the power row beside R34 spilled the packer into a new
    # row and broke the conduit's exterior-wall assert by 1.07 mm -- 0.62 last time, and
    # the row has not got any emptier since. The board's -Y end is where the connectors
    # live and it cannot grow (user), so the cap sits one row away at the DIVIDER'S own X.
    #
    # It costs nothing electrically, and the reason is worth stating because it is NOT true
    # of the decoupling caps this row is full of: a supply bypass has to be at the pin
    # because its job is set by loop inductance, and 6 mm of trace ruins it. C114's job is
    # a POLE, set by 901 ohm and 1 uF, and 6 mm of trace against 901 ohm is nothing. Put
    # differently: this cap filters a node, it does not decouple a pin.
    add("C114", "MID divider bypass -- 1 uF; keeps the LED row's 48 kHz off the reference "
        "all twenty TIAs share", "0402", _part_x("R34"), _y1_y)

    # ---- 3e. THE AUDIO CONVERTERS, in the escape annulus -X of the MCU (2026-09-21) ----
    # Five TLV320ADC3140s, one per quad (see elec/optical.py for why the MCU's own ADCs
    # went). They go in the 25 x 27 mm of empty board -X of U6 -- the annulus the twenty
    # analog nets used to cross to reach the LQFP's pins. Now those nets END here, a
    # converter sits where they arrive, and only seven SAI lines and two I2C pairs continue
    # to the MCU.
    # ⚠ EACH CELL IS LAID PIN BY PIN, OFF THE PLACED PART'S OWN PAD COORDINATES. Two
    # layouts came before this one and both lost the cells: a grid of caps under the part
    # (101 unconnected), then caps on the right SIDES but in the wrong ORDER along each
    # side (59) -- IN1P's cap at the far end from IN1P, DREG's under IOVDD, and a solid
    # row of caps under the three SAI pins with no way out between them. The part is
    # turned 180, which puts (relative to its centre, read back through pcbnew):
    #   +X side  pin 1 AVDD y-1.25, 2 AREG -0.75, 3 VREF -0.25, 4 AVSS, 6 IN1P +1.25
    #   +Y side  pins 7..12 = IN1M +1.25, IN2P +0.75, IN2M +0.25, IN3P -0.25, IN3M -0.75,
    #            IN4P -1.25; pin 13 IN4M on the -X side at y +1.25
    #   -Y side  19 IOVDD x-1.25, 21 SDOUT -0.25, 22 BCLK +0.25, 23 FSYNC +0.75, 24 DREG +1.25
    #   -X side  SHDNZ, address straps, I2C -- nothing, it is the routing side
    # and every capacitor sits at its own pin's coordinate. The eight input couplings
    # (INxP from the TIA, INxM to GND: SBAS993B Fig. 31) take two rows on end above the
    # part -- the INxM caps of pins 7/9/11 in the far row, each in the gap between two
    # near-row caps, directly above its pin -- and the bottom row leaves a 1.8 mm corridor
    # at x -0.6..+1.1 for the three SAI lines.
    _cx0 = COMPUTE_X0 + EDGE_KEEP
    _cx1 = _part_x("U6") - CRTYD[_MCU_PKG][0] / 2 - CRTYD_GAP
    _q, _c = CRTYD["WQFN-24"][0], CRTYD["0402"]          # 5.26; (1.95, 1.03)
    # ⚠ NARROW CELLS, SO THE ROUTING SIDE HAS A CHANNEL (2026-09-22). Each part's -X side
    # (SHDNZ, the address straps, SCL, SDA) faced the next cell's +X column across ~0.5 mm,
    # and that column's ground vias filled the gap: SHDNZ failed on all five parts. The +X
    # column is now two caps ON END beside their pins (AREG, VREF) with AVDD's cap moved to
    # the bottom row, and IN4M's cap went to the far row -- 1.3 mm off every cell, so the
    # channels between cells open from ~0.5 to ~2.5 mm.
    _rx = _q / 2 + CRTYD_GAP + _c[1] / 2                  # the +X column, caps on end
    _left = -CELL_FAN["IN4M"] + _c[1] / 2                 # IN4M's far cap is the -X extreme
    _cw = _left + (_rx + _c[1] / 2)
    # ⚠ THE ANNULUS IS EMPTY NOW AND ITS GUARD IS RETIRED. This asserted that three
    # converter cells fit -X of the MCU, which was true and load-bearing while they lived
    # there. They are east of the comb since the signal flow went west-to-east, and the
    # only thing still positioned off this geometry was R50/R51 -- two I2C pull-ups that
    # the move had stranded ~35 mm from the bus they pull up. With those placed at their
    # own bus (below), nothing is left here, and the assert was blocking the -X reclaim by
    # demanding width for cells that had moved out. A guard outliving its subject reads
    # exactly like a real constraint; this one cost a board-narrowing before it was spotted.
    _cgap = ((_cx1 - _cx0) - 3 * _cw) / 2
    _near = CELL_NEAR                                      # near input row / bottom row, |y|
    _far = _near + _c[0] + CRTYD_GAP                       # far input row
    _ch = (_far + _c[0] / 2) + (_near + _c[0] / 2)
    _cy_top = _part_y("U6") + CRTYD[_MCU_PKG][1] / 2
    _cy_gap = CRTYD[_MCU_PKG][1] - 2 * _ch
    assert _cy_gap >= 0, "two converter cells do not fit beside U6 (%.2f short)" % -_cy_gap
    # ⚠ THE SPARE HEIGHT GOES ABOVE THE CELLS FIRST (2026-09-22). All twenty TIA outputs
    # arrive down the strip and have to turn +X to reach the cells' input rows; with the
    # spare all between the rows, row 1's far caps sat against the strip's end and 7 of the
    # 16 open nets were outputs bound for row 1 that had no band to fan out through.
    _band = 0.6 * _cy_gap

    def _cell(col, row):
        """The part's centre for a cell."""
        return (_cx0 + col * (_cw + _cgap) + _left,
                _cy_top - _band - row * (_ch + _cy_gap - _band) - _far - _c[0] / 2)

    # ⚠ QUADS 1 AND 2'S CONVERTERS LIVE AT THE +Y END, NOT BESIDE THE MCU (2026-09-22). With
    # all five in the annulus the board plateaued at 14-17 unconnected over six routings:
    # five cells and their caps in 25 x 27 mm, fed by twenty outputs funnelled down a
    # 13.6 mm strip. The +Y wrap is 14.4 x 62 mm of board holding nothing but one grip.
    # Moved there, U14/U15 take the eight LONGEST analog runs off the strip entirely (quads
    # 1-2 sit at its +Y end), and the annulus keeps three cells in one row. What crosses
    # the strip instead is digital -- two SAI lanes, BCLK, FSYNC, I2C and +3V3D -- which
    # needs no pads on the way and can run under the In1 ground plane, away from the
    # summing nodes on F.Cu. These two cells are turned the other way up (inputs -Y, toward
    # their quads): every offset below is mirrored through the part's centre by `_s`.
    # ⚠ AND FOUR IN THE ANNULUS IS WORSE, MEASURED (2026-09-22). U15 starves at the wrap --
    # of its four inputs only TIA_OUT_3A reaches its coupling cap, because it sits on the far
    # side of the jack head's keep-out and cannot move -X (its x is already the keep-out edge
    # plus the cell's own half-width). Moving it back to the annulus to fix that gave 26
    # unconnected and 2 violations against 9 for the split, so the earlier reading that five
    # cells in the annulus was too crowded was NOT confounded by the missing +3V3D bus after
    # all: the annulus is genuinely the binding constraint, and a starved U15 costs less than
    # a fourth cell there. Keep the 1 + 4 split; U15's access is the thing to fix, not its home.
    # ⚠ ALL FIVE NOW SIT IN THE STRIP, EACH BESIDE ITS OWN QUAD (2026-09-22), and the reason
    # everything above was hard is that A CELL IS MUCH SMALLER THAN THIS FILE ASSUMED.
    # Measured on the placed board, one converter and its thirteen caps span 5.6 x 9.6 mm.
    # The half-width this code kept using, _rx + _c[1] / 2, is 13.38 -- it is a ROTATION
    # RADIUS, not an extent, and reasoning with it made a 5.6 mm part look 27 mm wide. That
    # is why the cells were ever exiled to the wrap and the annulus in the first place.
    # At 5.6 wide, five of them stack in 58 mm of the strip's 103 and need 7.6 mm of width
    # beside the op-amp column -- which is growth on the -X side, the direction the user
    # already opened ("as much as we want -x of the optical sensors"). So each cell goes
    # DIRECTLY WEST OF THE QUAD IT SERVES, at that quad's own centroid: the analog run is
    # ~10 mm instead of the ~40 that starved U15, and nothing crosses the strip any more.
    # ⚠ AND THE CHANNEL WEST OF THE COLUMN IS A REAL DIMENSION, not slack to be minimised.
    # Sat at EDGE_KEEP the column left 1.7 mm between the board edge and the first cap --
    # and that 1.7 has to carry the +3V3D via column AND the I2C spine, which it cannot:
    # measured, the gaps either side of the +3V3D vias are 0.55 and 0.18 mm, and a 0.6 mm
    # via needs 1.2. Every bus that wants to run the length of the column was therefore
    # competing for a lane that was never wide enough for one of them, which is most of
    # what the router kept failing to do.
    # The room is on the OTHER side and was simply unused: x 72..74 on the placed board is
    # empty, between the last cell cap at 71.7 and the TIA block at 74. Moving the column
    # 1.0 mm east spends it, widens the channel to 1.85, and SHORTENS the analog runs into
    # the converters, because the TIAs are east.
    # Swept by routing six placements in parallel (.ins/routefan.sh), not by reasoning:
    #   bus 1.8 -> 9 open (5 analog)   <- here      bus 2.2 -> 12 open (8 analog)
    #   bus 2.0 -> 13                               bus 2.6 -> 13
    # all at 0 violations. The differences are draws from a chaotic map rather than points
    # on a curve, so this is the best sample and not an optimum -- but it is the best
    # sample of six, and 1.8 still leaves the I2C spine its via lane.
    ADC_BUS_CH = 1.8
    assert ADC_BUS_CH >= EDGE_KEEP, "the bus channel is also the part-to-edge keepout"
    # ⚠ EAST OF THE COMB NOW (2026-09-23), not out at the strip's -X edge. Three things
    # were wrong with the old home and only one of them was routing. It put the converters
    # DOWNSTREAM of nothing -- the signal had to come back west to reach them -- it sat at
    # x -46.3 where string_clr_at() wants 1.45 mm and the WQFN-24 leaves 1.45, i.e. zero
    # margin under the widest part of the string's swing, and it is the whole reason the
    # board had a -X outcropping at all. East of the slots the cells are downstream of the
    # TIAs, the clearance question disappears (nothing overhead past the termination), and
    # STRIP_GROW_MX can go, which squares the board's outer border off (user).
    # ⚠ ADC_BUS_CH, NOT EDGE_KEEP -- and dropping it was a regression. The old column used
    # a 1.8 mm BUS CHANNEL west of the cells, and its value was not a guess: it was swept by
    # routing six placements in parallel (.ins/routefan.sh) because the corridor west of the
    # column is what every north-south analog and I2C run shares. Moving the column east of
    # the comb, that got rewritten as EDGE_KEEP -- which is the part-to-edge rule, 1.2, and
    # says nothing about a bus. It cost 0.6 mm of a lane that had been measured for, and the
    # first route showed exactly that: the I2C2_SCL spine ran at x 1.37 against a slot
    # keepout reaching 1.50, so all five converters' SCL stubs and vias came back as
    # items_not_allowed. Replacing a measured number with a plausible-looking one is how
    # that kind of thing gets lost, and the name was the only thing carrying the measurement.
    # 2.4 reproduces the corridor width the sweep liked (2.18 mm clear, 6 tracks) now that
    # the slot keepout rather than the board edge sets the west side of it.
    # ⚠ 4.2, BECAUSE THE CHANNEL CARRIES THE CROSSINGS TOO, NOT JUST THE SPINE. 2.4 was
    # sized for the I2C spine alone and reproduced the corridor width the old sweep liked.
    # It is the wrong requirement: all twenty TIA outputs have to CROSS this channel to
    # reach their coupling caps, and once the comb crossings were assigned they all parked
    # their east ends in it -- 1.50..3.75 wide, with corridor stubs ending at 2.55. The
    # result was five DRC violations, two of them real shorts, every one of them a
    # corridor track against I2C2_SCL or its vias, and the board went 12 unconnected to 19.
    # There is no narrower answer available: the comb ends at 1.35 and the keepout at 1.50,
    # so ANY endpoint east of the comb is either in this channel or inside a cell. The
    # channel has to be big enough for both jobs.
    ADC_BUS_CH = 4.2
    assert ADC_BUS_CH >= EDGE_KEEP, "the bus channel is also the part-to-edge keepout"
    _adc_x = O_SLOT_X1 + ADC_BUS_CH + 2.8                      # 2.8 = half the measured cell
    for k in range(5):
        qx = _adc_x
        # ⚠ THE CAP ROW GOES ON THE PAIR'S CENTRE, NOT THE PART'S BODY (user, 2026-09-24:
        # "we also want component placement symmetry"). Centring the PACKAGE looks right and
        # is not: every input pin is on this part's north edge, so its coupling caps sit
        # CELL_NEAR above it, and a centred package puts them 3.75 mm toward the odd string.
        # Measured on the placed board, that made the two strings of a pair profoundly
        # unlike each other -- string 1's output reached its cap with a 0.93 mm jog and
        # string 2's needed 8.43 -- and no routing pattern can be symmetric across a pair
        # whose two halves are that different. Everything ELSE in the pair was already
        # mirror-perfect: op-amp, both detectors, emitter, feedback R and C, decoupler and
        # ballast all sit at identical offsets from their own string.
        # Dropping the body by CELL_NEAR puts the caps on the centre line and the two climbs
        # become +-4.68: mirror images, which is what lets one pattern serve both.
        qy = ((string_y_at(2 * k, SENSE_X) + string_y_at(2 * k + 1, SENSE_X)) / 2
              - CELL_NEAR)
        _s = 1.0
        t = k + 1
        add("U%d" % (14 + k), "audio ADC -- TLV320ADC3140, 4 ch, quad U%d's outputs" % t,
            "WQFN-24", qx, qy, 180.0 if _s > 0 else 0.0)
        # ⚠ ROTATION IS WHICH PAD FACES THE PIN. An 0402 at 90 has pad 1 at the BOTTOM, at
        # 270 on top. Every cap here is wired pad 1 = the net nearer the part's pins' far
        # side, so: above the part the input caps (pad 2 = the ADC pin for Ci, pad 1 for Cm)
        # and below it the rail caps (pad 1 = the rail pin) are turned to face the pins.
        # ⚠ THE INPUT FAN IS A GEOMETRY, NOT A SEARCH (2026-09-21). The top pins run
        # 13 (left side) 12 11 10 9 8 7 6 (right side) at 0.5 pitch, alternating INxP/INxM,
        # and the caps for 12/10/8/6 sit in the near row with 11/9/7 threading up between
        # them to the far row. Near caps at 1.2 pitch put every cap within 0.25 of its own
        # pin's x, so the fan only ever WIDENS -- no two traces converge -- and each thread
        # clears the near pads either side by 0.215. With the caps at their earlier,
        # wider-flung positions the paths crossed and the router left 12 of these open.
        # elec/optical.py lays the fan itself ("tracks"), from these same offsets.
        for ref, dx, dy, rot in (("Cm%d4" % t, CELL_FAN["IN4M"], _far, 90.0),
                                 ("Ci%d4" % t, CELL_FAN["IN4P"], _near, 270.0),
                                 ("Ci%d3" % t, CELL_FAN["IN3P"], _near, 270.0),
                                 ("Ci%d2" % t, CELL_FAN["IN2P"], _near, 270.0),
                                 ("Ci%d1" % t, CELL_FAN["IN1P"], _near, 270.0),
                                 ("Cm%d3" % t, CELL_FAN["IN3M"], _far, 90.0),
                                 ("Cm%d2" % t, CELL_FAN["IN2M"], _far, 90.0),
                                 ("Cm%d1" % t, CELL_FAN["IN1M"], _far, 90.0),
                                 # bottom: IOVDD under pin 19, DREG beside pin 24, and a 2.5 mm
                                 # corridor between them for SDOUT/BCLK/FSYNC
                                 ("Cs%d8" % t, -1.25, -_near, 270.0),
                                 ("Cs%d6" % t, 1.90, -_near, 270.0),
                                 ("Cs%d1" % t, 3.10, -_near, 270.0),   # AVDD, pin 1 at +X low
                                 # +X column on end: AREG (pin 2, y -0.75) rail pad on top,
                                 # VREF (pin 3, y -0.25) rail pad at the bottom
                                 ("Cs%d3" % t, _rx, -1.20, 270.0),
                                 ("Cs%d5" % t, _rx, 0.90, 90.0)):
            add(ref, "ADC input AC coupling" if ref[1] in "im" else "ADC supply bypass",
                "0402", qx + _s * dx, qy + _s * dy, rot if _s > 0 else (rot + 180.0) % 360.0)
    # ⚠ AT THE BUS, NOT IN THE ANNULUS. These were placed off _cell(2, 1) -- a slot in the
    # converter block back when that block sat -X of the MCU. The converters moved east and
    # these did not, leaving two pull-ups ~35 mm from the only five parts on their net. A
    # pull-up is not critical about position, which is exactly why nothing complained.
    # Beside the middle converter, so the bus is pulled up near its electrical centre.
    # outboard of the cell's OWN +X column (Cs?3/Cs?5 sit at _rx), not on top of it
    # ⚠ AND SOUTH OF THE LAST CELL, NOT BESIDE THE MIDDLE ONE (user, 2026-09-24). Beside
    # U16 put two parts inside converter cell 3 that the other four cells do not have --
    # the only asymmetry left in the array once the cap row was centred, and the user spotted
    # it in the render before any check did. The rule it breaks is theirs: a tile has to be
    # a self-contained thing or the copies are not copies. One pull-up pair serves the whole
    # bus, so it belongs with the other shared analog hardware (Q1, U11, FB1), not inside
    # one tile.
    # The "electrical centre" argument it replaces is real and does not matter here: I2C2
    # runs at 400 kHz open-drain, where a pull-up's position on the bus is worth nothing
    # measurable. Being INSIDE a repeating cell costs something visible on every render.
    # ⚠ AND EAST OF THE ESCAPE LANES, not just east of the cell. The strip east of the
    # converters carries every bus that has to reach the border -- +3V3A, SAI_SCK,
    # SAI_SD1..4 and SAI_FS, the outermost at x 22.50 -- and the pull-ups sat at
    # 16.375, right under SAI_SCK's crossing. They are 400 kHz open-drain pull-ups on
    # a bus whose length is already irrelevant (see above), so they yield.
    _pu_x = _adc_x + _rx + _c[1] + CRTYD_GAP + 7.70
    _pu_y = _part_y("U18") - (CELL_FAR + CRTYD["0402"][0] + 2 * CRTYD_GAP)
    for m, (ref, desc) in enumerate((("R50", "I2C2 SCL pull-up"), ("R51", "I2C2 SDA pull-up"))):
        add(ref, desc, "0402", _pu_x,
            _pu_y + (m - 0.5) * (CRTYD["0402"][0] + CRTYD_GAP), 90.0)

    # ---- 3b/3b-i/3d ARE GONE: THE MAGNETIC PATH LEFT THIS BOARD (user, 2026-09-15) ----
    # This file used to carry the magnetic pickup's own ADC (U12, a PCM1808, with C150-153
    # and R37/R38), a note reserving the phantom-power protection for a jack stage that was
    # going to land here, and an open question about how to get audio across to the panel.
    # All three are answered by the same decision: THE PICKUP NOW LANDS ON THE OUTPUT PANEL
    # BOARD, on screw terminals, and is converted there.
    #
    # It is the better split and not just a relocation:
    #   * The panel is physically NEARER the pickup than this board is, so the analog run
    #     got shorter rather than longer.
    #   * NO ANALOG SIGNAL CROSSES THE INSTRUMENT any more. The 8-way link this section
    #     owed the panel -- AGND, AUDIO, GND, +5V, BCK, LRCK, DIN, RELAY -- does not exist,
    #     because nothing has to cross. That link had no room on the -Y edge anyway: the
    #     band is 37.42 wide, J1 takes 8.94 and J2 took 20.0, and an 8-way side-entry PH is
    #     21.28. The question recorded here as "NOT DECIDED" decided itself.
    #   * DIRECT MODE ends up wholly on one PCB -- pickup, buffer, relay, jack -- so the
    #     instrument plays with no Pi, no firmware and no cable in the path. Split across
    #     two boards it needed both of them alive.
    #   * The phantom-power protection is BUILT, not reserved: R9/C1/D5 on the panel.
    #
    # WHAT IT COSTS THIS BOARD: nothing. It loses seven parts and a connector size, and
    # the -Y edge goes back to its own USB plus its own power.
    # WHAT IT COSTS THE PANEL: a local 24->5 V buck, since deleting the link deleted the
    # 5 V that used to arrive on it. That is written up in elec/output_panel.py.

    # ---- 3c. LOCAL 24 -> 5 V, AND IT GOES AT THE FAR END ON PURPOSE ----
    # The trunk delivers 24 V (see J2). One switching stage is therefore unavoidable --
    # 24->3V3 linearly is 6.2 W -- so the whole question is WHERE, and the answer is: as
    # far from the photodiode array as this board has room for, which is right here at the
    # -Y tail beside the connector the 24 V arrives on. The input path is then ~10 mm long
    # instead of crossing the board, and the only thing between the switcher and the sense
    # zone is the MAGNETIC channel, which is line level -- four to five orders of magnitude
    # louder than the nanoamps the TIAs read, and therefore the right neighbour for it.
    # The two 3V3 LDOs still follow, so nothing downstream of 5 V sees the switching node.
    # ⚠ PLACED EXPLICITLY, NOT PACKED, and pushed to the -X side. The packer spread it
    # across the full width, which put the switching node in the middle of the board and
    # -- once the USB cluster moved to the -Y edge -- directly between the PHY and its
    # connector. Both problems answer to the same move: the buck belongs beside the 24 V
    # inlet it is fed from, and that inlet is now the -X connector. Power on one side,
    # USB on the other, which is also the right answer for noise.
    # ⚠ THE ROW IS RESERVED HERE AND FILLED LATER, once the board's -Y face is known.
    # Every Y on this board is derived from the part list marching down, so a typed
    # coordinate is stale the moment anything above it changes size -- which is exactly
    # what happened the first time this was written: taking the buck out of the packer
    # shortened the board by its row height, and the hand-typed cluster below ended up
    # off the -Y edge.
    # ⚠ THIS ROW'S X OFFSETS ARE HAND-CHOSEN, AND THE FIRST SET WAS CHOSEN BADLY.
    # Measured on the placed board 2026-09-17, before the reorder below:
    #     U13 -> C160, the 24 V input bulk      13.5 mm
    #     U13 -> C161, the 24 V input HF cap    18.0 mm
    #     U13 -> C162, the 5 V output bulk      21.5 mm
    # The input loop of a 1.1 MHz switcher -- C160/C161 to VIN, through the package, out
    # of GND and back -- is the highest di/dt loop on the board, and at those distances
    # it encloses area that radiates into twenty transimpedance amplifiers reading
    # nanoamps. That is the one thing this board's entire layout is arranged to avoid.
    #
    # ⚠ AND IT MAKES A LIE OF AN ARGUMENT MADE ELSEWHERE. The commit that merged PWR_GND
    # into GND said the switcher stays quiet because "U13, C160 and C162 sit in one row
    # so the high-di/dt loop is short". They did sit in one row -- a 31 mm row with the
    # parts spaced along it. That sentence was written from reading the source instead of
    # measuring the board. The merge is still right; it just was not doing this work.
    #
    # ORDER NOW FOLLOWS THE CURRENT, not the schematic. Parts are contiguous at
    # CRTYD_GAP, and the sequence is chosen from U13's own pinout (SOT-23-6: 1 CB,
    # 2 GND, 3 FB on one edge; 4 EN, 5 VIN, 6 SW on the other, so SW and CB are both on
    # the package's LEFT and FB on its RIGHT):
    #     C160 C161 | U13 | C163 | L1 | C162 | R40 R41
    #       bulk+HF first and adjacent -- the input loop, which matters most
    #       C163 the bootstrap, next to the CB/SW corner it serves
    #       L1 next, keeping the SW node (the dV/dt radiator) short
    #       C162 immediately past L1, at the output node
    #       R40/R41 last, with R40's top AT the output node it senses
    # giving U13->C161 3.2 mm, U13->C160 6.7, U13->L1 6.9, L1->C162 5.0.
    #
    # ⚠ WHAT THIS ORDER COSTS, stated rather than hidden and MEASURED rather than
    # estimated: FB runs 15.4 mm from R40 back to U13 pin 3 (17.5 from R41), past the
    # inductor. An earlier draft of this note said "~13 mm" from arithmetic; the placed
    # board says 15.4.
    #
    # FB is the divider's midpoint, so its source impedance is R40||R41 = 8 kohm -- high
    # enough that 15 mm beside a switching node is a real antenna and not a pedantic
    # one. THE MITIGATION IS THE STACK-UP, and this board has it: F.Cu / In1.Cu solid
    # GND / In2.Cu signal / B.Cu, so FB routed on In2.Cu has the whole ground plane
    # between it and SW on F.Cu. That is a routing obligation, not a placement one,
    # which is why it is written here where the placement that created it lives.
    #
    # The alternative orders all buy a short FB with a long SW node -- putting R40/R41
    # beside U13 pushes L1 about 4 mm further out, and SW measured 5.9 mm from pin 6 to
    # L1 today. SW is the radiator and it cannot be shielded by a layer change, because
    # it has to reach the inductor on the surface. So this is the better half of a trade
    # a single row cannot avoid.
    #
    # NOT ADDED, deliberately: a feedforward capacitor across R40 would lower FB's
    # impedance at high frequency and help transient response, and TI suggests one for
    # this part. It is a part added for a problem nobody has measured on this board yet;
    # the layer change costs nothing and should be tried first.
    # LMR33630CRNXR since 2026-09-22 (see U13 in elec/optical.py): its two VIN/PGND pairs
    # sit on OPPOSITE sides, so each gets a 100 nF hard against it (C161 -X, C165 +X), and
    # VCC's 1 uF (C166) and a second output 22 uF (C167) join the row.
    _buck_order = (("C160", "24 V input bulk -- 50 V part, see 1206C", "1206C"),
                   ("C161", "24 V input HF bypass -- the VIN/PGND pair on U13's -X side", "0402"),
                   ("U13", "buck -- 24V -> 5V, the board's only switcher", "RNX12"),
                   ("C165", "24 V input HF bypass -- the VIN/PGND pair on U13's +X side", "0402"),
                   ("C163", "bootstrap -- BOOT to SW", "0402"),
                   ("C166", "buck VCC bypass, 1 uF", "0402"),
                   ("L1", "buck output inductor", "IND-4040"),
                   ("C162", "5 V output bulk", "0805C"),
                   ("C167", "5 V output bulk, second", "0805C"),
                   ("R40", "feedback divider -- top, at the output node", "0402"),
                   ("R41", "feedback divider -- bottom", "0402"))
    # ⚠ DERIVED, NOT TYPED. This was -37.10, a hardcoded absolute left behind when the
    # board's -X edge moved; the row then sat 6.14 mm outside the board and only
    # _assert_field_clear caught it. Pinned to the edge so the two cannot drift again.
    _BUCK_X0 = COMPUTE_X0 + EDGE_KEEP    # the row's -X edge, on the board's own keep-out
    _buck, _bx = [], _BUCK_X0
    for _r, _d, _p in _buck_order:
        _w = CRTYD[_p][0]
        _buck.append((_r, _d, _p, _bx + _w / 2.0))
        _bx += _w + CRTYD_GAP
    _buck_h = max(CRTYD[_p][1] for _, _, _p, _ in _buck)
    y -= CRTYD_GAP
    _buck_y = y - _buck_h / 2.0
    y -= _buck_h

    # ---- 4. the -Y EDGE: every cable leaves the board here ----
    # Both mouths face -Y and their outer faces are FLUSH, so the two plugs present as one
    # cable exit rather than two at different depths. J1 sets PCB_YM; J2 is referenced to
    # the same face so a deeper or shallower connector cannot silently step one of them.
    # ⚠ THE BOARD'S -Y FACE IS SET BY THE DEEPER OF THE TWO CONNECTORS, not by J1.
    # It used to be reserved from the USB-C alone, and the XH's LAND reaches 12.09 back
    # into the board against the USB-C's 9.51 -- so the 2.58 difference was board that
    # the packer above had already filled. C160, the 24 V bulk cap, ended up sitting ON
    # J2's pads 3 and 4: DRC called it a short between +24V and an unused cavity, which
    # is exactly what it was.
    # ⚠ THE BAND IS DEEP ENOUGH FOR TWO ROWS NOW, and the extra 1.06 mm buys the only
    # thing on this board that could not be bought any other way: a USB-C whose data
    # pads escape INBOARD, the way a USB-C's data pads have to.
    #
    # A USB-C receptacle's 16 pads sit 8.25 mm behind its mouth, on 0.5 mm pitch, with a
    # 1 mm through-plated shell tab either side of them. There is no route out of that
    # row except straight inboard, between the tabs -- which means the part the pair
    # goes to has to BE inboard. It was beside instead, and the 22 mm of copper that
    # implies had to cross a shell tab that pierces all four layers. That was not a
    # routing problem with a routing answer; it was the placement saying one thing and
    # the connector's own geometry saying another.
    _uc_w, _uc_d = CRTYD["USB-C"]
    # TURNED 90 deg -- see the ESD array's placement -- so its envelope turns with it
    _esd_d, _esd_w = CRTYD["SOT-563"]
    _phy_w, _phy_d = CRTYD["QFN-24"]
    # ⚠ THE CHAIN IS SPACED FOR ITS GROUND PAD, not for its courtyards. CRTYD_GAP is
    # 0.15 and legal, and at 0.15 the ESD array's centre pin -- its ground, where the
    # diodes dump what they clamp -- is boxed in: the pair's two rails leave either side
    # of it and there is nowhere within reach to put a via down to the plane. The
    # stitcher said so by name rather than quietly leaving the pad on the pour, and a
    # protection device whose ground is a pour connection the router may orphan is not
    # protecting anything. A millimetre of lane either side is what it costs.
    _chain_gap = 1.0
    # ⚠ THE PHY END OF THE CHAIN HOLDS A ROW OF PARTS, AND THE PINS SAY WHICH. The
    # USB3343's socket-facing side carries DP and DM (13, 14) and then VDD33, VBAT, VBUS
    # and ID (15-18) -- per the datasheet, not the invented map this gap was first sized
    # for. Those four each want a part within reach: VDD33's 1 uF regulator cap, the 3V3
    # bypass, and VBUS's 20 k series resistor. They sit in ONE ROW here, outboard (+X) of
    # the pair, behind the same 2 mm fan lane every face of this QFN gets.
    #   2.0 fan lane + 1.03 row + ~0.6 to the ESD array  ->  3.6
    _PHY_FAN = 2.0
    _phy_gap = _PHY_FAN + CRTYD["0402"][1] + 0.57
    _conn_depth = max(CRTYD["XH-SM-4Y"][1],
                      # socket, then the ESD array in line with its pad row, then the
                      # PHY behind that: the chain in signal order, in a straight line
                      _uc_d + _chain_gap + _esd_d + _phy_gap + _phy_d)
    edge_y = y - _conn_depth                                # the board's -Y face
    # J2 TAKES THE -X END AND J1 THE +X. The 24 V inlet gains the -X end, next to the
    # buck it feeds; the USB-C gains the +X end, and the whole high-speed chain lays out
    # behind it IN SIGNAL ORDER. The cable run is a wash -- both plugs turn +X to the
    # conduit, so one gets shorter by roughly what the other gains.
    # ⚠ ALL FOUR CAVITIES ARE POPULATED, and this string said "2 cavities empty" until
    # 2026-09-18. The netlist doubles both rails -- 1=GND 2=+24V 3=+24V 4=GND -- and has
    # since the contact doubling went in; this description predates it. It is the line a
    # person reads while crimping, and it was telling them to make a 2-wire cable for a
    # 4-crimp connector. BOM.md's cable row was already right (4 x 26 AWG); only this
    # was wrong.
    add("J2", "power in -- 2-way: 1=PWR_GND 2=+24V",
        "XH-SM-4Y",
        COMPUTE_X0 + EDGE_KEEP + CRTYD["XH-SM-4Y"][0] / 2,
        edge_y + CRTYD["XH-SM-4Y"][1] / 2)
    # ⚠ THE CHAIN SITS INBOARD OF THE +X EDGE, AND THE PHY'S PINOUT IS WHY. With DP/DM
    # facing the socket, the USB3343's cyclic pin order puts pins 19-24 -- RBIAS, the
    # crystal's XO/XI, RESETB, VDD18 -- on the face toward +X. Hard against the edge that
    # face had 1.8 mm of board, and a 26 MHz crystal, its two load caps, the bias
    # resistor and the 1V8 regulator cap do not fit in 1.8 mm. There is no rotation that
    # fixes it: a QFN cannot be mirrored, so pointing the pair at the socket FIXES which
    # way pins 19-24 face. What moves is the chain. The pocket below is sized from its
    # contents, and the -Y edge has 32 mm between J2 and J1 to give it from.
    #   fan lane + R37/C122 column + crystal + load-cap column, less what the socket's
    #   half-width already gives  ->  _CHAIN_DX
    # PHY DM (-0.75 from its centre) straight over the ESD array's DM (+0.95 from ITS
    # centre): 1.7. Only D+ then fans, and it fans -X -- away from pads 15-17, whose
    # escapes the old 1.0 put D- straight across. VDD33, VBAT and VBUS all came back
    # unconnected at 1.0.
    _PAIR_DX = 1.7
    _pocket = (_PHY_FAN + CRTYD["0402"][1] + CRTYD_GAP + CRTYD["3225"][1]
               + CRTYD_GAP + CRTYD["0402"][1])
    _CHAIN_DX = _pocket - (_uc_w / 2 - _PAIR_DX - _phy_w / 2) + 0.05
    _j1_x = TAIL_X1 - EDGE_KEEP - _uc_w / 2 - _CHAIN_DX
    add("J1", "USB-C receptacle -- 10ch audio + MIDI + DFU", "USB-C",
        _j1_x, edge_y + _uc_d / 2)
    # ⚠ THE CC RESISTORS GO TO THE SOCKET, WHICH IS BOTH WHERE THEY BELONG AND WHERE THE
    # ROUTING NEEDS THEM GONE FROM. They were loose items in the power row -- 24 mm from
    # J1, on a net that exists only between J1's CC pins and ground -- and that row is the
    # BARRIER: 15 parts filling their span at the 0.15 mm courtyard minimum, whose 26
    # escape vias shadow 38% of the board's width on EVERY layer, inner ones included.
    # A part that has no reason to be in a wall should not be part of the wall.
    #
    # Taking two 0402s out gives the row back ~5 mm, and _spread hands that straight to
    # the gaps between everything left in it. They land in the open board north-west of
    # the socket, 5-6 mm from the pins they pull down, which for a 5k1 to ground is a
    # distance with no job to do.
    add("R32", "USB-C CC1 pull-down 5k1 -- at the socket", "0402",
        _j1_x - _uc_w / 2 - 2.2, edge_y + _uc_d / 2)
    add("R33", "USB-C CC2 pull-down 5k1 -- at the socket", "0402",
        _j1_x - _uc_w / 2 - 4.5, edge_y + _uc_d / 2)

    # J2 -- POWER ONLY. 24 V FROM THE TRUNK, and NOT USB VBUS: MCU ~200-300 mA + PHY ~50
    # + 21 op-amp channels ~40 is already past a USB port before an emitter is lit.
    #
    # ⚠ IT NO LONGER CARRIES THE MAGNETIC PICKUP'S AUDIO TAP, and that is why the plug
    # above is still modelled as a 6-way. The tap moved to the output panel's own screw
    # terminals (J8 there), leaving elec/optical.py's J2 as an S4B-XH-SM4-TB whose four
    # ways are 1=GND 2=+24V 3=+24V 4=GND and nothing else. Four power ways plus two audio
    # is exactly the six this file still sizes the conduit against.
    #
    # ⚠ AND LED CURRENT IS NOT THE FIRST SNR LEVER. This said it was; BOM.md said it was
    # the second; the noise budget re-derived in elec/optical.py on 2026-09-18 says
    # neither. The dominant term is the op-amp's own voltage noise over a plateau that
    # ends at GBW/noise-gain, so the first lever is the amplifier's BANDWIDTH -- slower is
    # quieter here -- and emitter drive comes after it.
    # 24 V rather than a delivered 5 V (user, 2026-09-14) because the alternative is a
    # 5 V rail run ~600 mm from the keyhead, sharing a return with the Pi -- and this
    # board's LED driver switches at 48 kHz SYNCHRONOUSLY WITH SAMPLING, so that return
    # current is the one noise source ambient subtraction cannot cancel. Local conversion
    # keeps it on this board. It costs the board its switcher-free property; see U13.
    # AUDIO_GND is a dedicated pin, not shared with PWR_GND and emphatically not with USB
    # ground, for the same reason.

    # ---- 4b. THE USB CHAIN, IN THE ORDER THE SIGNAL TRAVELS ----
    # ⚠ PLACED BY WHICH WAY THE PINS FACE, which is the lesson this board taught twice.
    # The first re-plan put the chain together -- PHY, ESD array and socket in one group
    # instead of scattered across three packed rows -- and that was right and not enough.
    # Together is not the same as IN ORDER: the PHY's D+/D- pins are on its +X face, and
    # the group was laid out with the socket to its -X, so the pair's first move was
    # backwards around the package that had just driven it. The crystal sat in front of
    # those same pins, 1.7 mm away, for good measure.
    #
    # A high-speed pair is a direction before it is a distance. So the chain now runs +X
    # in signal order -- PHY, ESD array, socket -- with the ESD array stepped inboard to
    # meet the socket's pad row where it escapes, and nothing at all in front of the PHY.
    # ⚠ AN ESCAPE LANE, NOT A COURTYARD GAP. CRTYD_GAP is 0.15 -- legal, and useless
    # here: the pair has to come off the PHY's pad face, open out to the via pitch and
    # turn, and none of that happens in 0.15 mm. Packed at the courtyard gap the PHY's
    # D+/D- pins had 0.15 mm of board in front of them and the router reported no escape
    # at all, which read as a routing failure and was a placement one. Two millimetres
    # is what the fan-out actually occupies.
    # ⚠ AND IT SITS BEHIND THE ESD ARRAY, WHICH SITS BEHIND THE SOCKET. The chain is a
    # straight line inboard, in the order the signal travels, because inboard is the only
    # direction a USB-C's data pads can leave: they are 8.25 mm behind its mouth on 0.5 mm
    # pitch with a through-plated shell tab either side, so the route out is between the
    # tabs or it is nothing.
    #
    # This costs 2.92 mm of band depth over packing the PHY beside the socket, and for one
    # afternoon the board could not afford it -- the conduit limit was derived from the
    # chassis rail's datum instead of the instrument's exterior, which made the budget look
    # 12.84 mm tighter than it is (see _WALL_Y). Against the real budget it is 2.92 of
    # 14.75 mm spare, and it buys a pair with no corner in it at all.
    # TURNED so D+/D- face the ESD array. Unturned they face +X, which on a chain that
    # runs in Y means the pair's first move is sideways out of the package and then back
    # across it -- and the 12 ULPI signals, which leave the two faces at right angles to
    # those, turn with it and still point at the MCU. The rotation costs nothing and is
    # the difference between a straight pair and no pair.
    # +_PAIR_DX: see its definition -- D- runs straight, only D+ fans.
    add("U7", "USB 2.0 high-speed ULPI PHY", "QFN-24",
        _j1_x + _PAIR_DX, edge_y + _uc_d + _chain_gap + _esd_d + _phy_gap + _phy_d / 2,
        rot=270.0)
    # ⚠ OFFSET BY HALF ITS OWN PAD SPAN, so the two faces land where the two hops need
    # them. A SOT-563's pads face +-X and this hop runs in Y, which reads like the wrong
    # package until you notice the part is a PASS-THROUGH: D+ appears on pins 1 and 6,
    # D- on 3 and 4, and the run is meant to enter one face and leave the other. Centred
    # on the socket, BOTH faces sat beside its pad row and the outgoing pair had to
    # double back around the part it had just left. Shifted -X by half the pad span, the
    # +X face sits directly over the socket's pad row -- a 3 mm drop straight down it --
    # and the -X face looks back down the board at the PHY.
    # ⚠ TURNED 180 FROM WHERE IT WAS, BECAUSE THE REAL PHY PUTS DP ON THE OTHER SIDE.
    # With the datasheet pinout DP (13) is -X of DM (14). At 270 the array presented DP
    # on its +X side, so the pair had to cross itself between two parts 3.6 mm apart;
    # at 90 the array's PHY-facing pads are DP -X / DM +X, matching. It is a pass-through
    # (DP on 1 and 6, DM on 3 and 4), so the socket-facing side keeps a valid pair too.
    add("U10", "USB data-line ESD array -- inboard of the socket's pad row", "SOT-563",
        _j1_x, edge_y + _uc_d + _chain_gap + _esd_d / 2, rot=90.0)
    # ---- 4b-i. THE PHY'S SUPPORT PARTS, WHICH DID NOT FOLLOW IT DOWN HERE ----
    # ⚠ THIS IS A STALE-PLACEMENT BUG, NOT A ROUTING ONE, and it is the same shape as the
    # two this file already records: a derivation that stayed legal after the thing it
    # derived from moved. When the PHY left the compute rows for the -Y edge (section 4b)
    # it left behind everything that serves it -- its 24 MHz crystal, that crystal's two
    # load caps, its three decoupling caps and its bias resistor. All seven stayed packed
    # in rows 19 to 45 mm up the board, and every one of them was still "placed": legal
    # courtyards, clean overlap gate, a render that looks right.
    #
    # WHAT THAT ACTUALLY MEANS, part by part:
    #   * Y2 sat 43 mm from the XI/XO pins it drives. A crystal's load is the PCB as much
    #     as the caps; 43 mm of track is an antenna on both a high-impedance oscillator
    #     node and a 24 MHz reference the whole USB link is timed from.
    #   * C120-C122 are DECOUPLING, and decoupling 19 mm from its die is decoration. The
    #     loop inductance it exists to cancel is dominated by the trip out and back.
    #   * R37 sets the PHY's transmitter drive CURRENT to 1%. It was 15.6 mm away, and it
    #     was one of the four nets the router could not finish at all.
    # Their proximity is the specification. Two columns immediately -X of U7, in the
    # pocket between the buck and the socket, which was empty.
    # ⚠ REBUILT FOR THE DATASHEET PINOUT. The cluster that stood here was fitted to an
    # invented map (crystal on the -X face, RBIAS beside the pair). The real USB3343 puts:
    #   socket face (-Y):  DP -1.25  DM -0.75  VDD33 -0.25  VBAT +0.25  VBUS +0.75  ID +1.25
    #   +X face:           RBIAS -1.25  XO -0.75  XI -0.25  RESETB +0.25  VDD18 +0.75  STP +1.25
    # (offsets along the face from the package centre, CAD frame). Everything below is
    # placed off those numbers, and every face keeps the 2 mm fan lane.
    # ⚠ ONE EXPRESSION, NOT TWO COPIES OF ONE: read U7 back, never re-derive it -- a copy
    # that drifted by 1.2 mm once put R37's pad on U10's and shorted PHY_RBIAS to USB_DP.
    _ux, _phy_y = _part_x("U7"), _part_y("U7")
    _r_w, _r_h = CRTYD["0402"]              # an 0402 unrotated; rotated it is (_r_h, _r_w)

    # SOCKET-FACE ROW, in the PHY-to-ESD gap, all +X of the pair (which leaves at -1.25 /
    # -0.75 and needs its lane). Ordered by the pad each part serves.
    _row_y = _phy_y - _phy_d / 2 - _PHY_FAN - _r_h / 2
    _row_x0 = _ux + 0.30
    for _k, (_ref, _desc) in enumerate((
            ("C120", "PHY VDD33 regulator output cap, 1 uF -- pads 15 and 18"),
            ("R39", "PHY VBUS series 20 k, device-only -- pad 17"),
            ("C121", "PHY VBAT/VDDIO bypass -- pad 16 and 9"))):
        add(_ref, _desc, "0402", _row_x0 + _r_w / 2 + _k * (_r_w + CRTYD_GAP), _row_y)
    # ⚠ C119: A SECOND BYPASS, AT PIN 9, BECAUSE ONE CAP CANNOT SERVE BOTH PINS IT NAMES.
    # C121's description reads "pad 16 and 9" and the row above is ordered "by the pad each
    # part serves" -- but VBAT (16) is on the SOCKET FACE and VDDIO (9) is on another, so a cap
    # in this row is adjacent to 16 and 9.194 mm from 9. Measured, not assumed.
    # That is wrong twice over, and the second reason is the one that matters more:
    #   * ROUTING. VDDIO is the last unconnected net on this board. Its escape corridor runs
    #     -X, away from every +3V3D pad -- the nearest is 2.756 mm and is another U7 pin -- so
    #     the router has nothing to reach. A via cannot help: none fits at any size once the
    #     neighbours route (O0.40 reaches +0.0697 mm against a 0.127 rule), and escape vias on
    #     this edge made the board monotonically worse (2 -> 3 -> 5 unconnected).
    #   * DECOUPLING. VDDIO sources the ULPI output drivers' switching current at 60 MHz. Its
    #     bypass belongs AT the pin; 9.194 mm of loop is not a bypass, whatever the netlist says.
    # So pin 16 keeps C121 and pin 9 gets its own, which is what one-bypass-per-supply-pin means.
    # ⚠ PLACED RELATIVE TO U7, per this section's own rule ("read U7 back, never re-derive it").
    # The offsets put it at file (113.000, 173.040): collinear with pin 9's land so the run is a
    # straight -X hop, and its courtyard's +X edge lands 0.10 mm clear of U7's, which starts at
    # 114.056 -- measured off the board, not guessed. Checked against every other courtyard on
    # the board: nothing overlaps, and the 3 x 4 mm region outboard of the pin holds no pads.
    # ⚠ rot 180 SO PAD 1 FACES THE PIN. _c() wires pad 1 to the rail and pad 2 to ground, and
    # an 0402's pad 1 sits at -x unrotated, i.e. pointing AWAY. Unrotated this cap would offer
    # the router its ground pad.
    add("C119", "PHY VDDIO bypass -- AT pad 9, which C121 is 9.19 mm from", "0402",
        _part_x("U7") - 3.731, _part_y("U7") + 0.250, 180.0)
    # ⚠ C130 LEAVES THE POWER ROW, AND IT IS BOTH A ROUTING FIX AND A CORRECTION. It is
    # the VBUS SENSE FILTER -- the C of an RC whose R is R39's 20 k -- and it was sitting
    # 24 mm from R39, in the middle of the wall the ULPI nets have to cross. An RC filter
    # whose two halves are at opposite ends of the board is not a filter anybody drew; it
    # is where the packer happened to put a part called "bulk cap". Beside R39 it does its
    # job, and the 2.8 mm it gives back is what lets the corridor below be 5.5 mm instead
    # of the 2.7 the row could otherwise afford.
    add("C130", "VBUS sense filter -- the C of R39's RC; see the note", "0805C",
        _part_x("R39") + 2.6, _part_y("R39") - 2.9)


    # +X POCKET, three columns out from the +X face.
    # col 1: R37 by RBIAS (socket end), C122 by VDD18 (MCU end). Turned 90 so the column
    # is one 0402 wide, and spaced to leave the XI/XO pair a clear channel between them.
    _c1 = _ux + _phy_w / 2 + _PHY_FAN + _r_h / 2
    add("R37", "PHY RBIAS 8k06 1% -- by pad 19", "0402", _c1, _phy_y - 2.30, rot=90.0)
    add("C122", "PHY VDD18 regulator output cap, 1 uF -- by pad 23", "0402",
        _c1, _phy_y + 1.60, rot=90.0)
    # col 2: the crystal, centred on XI/XO (-0.25 / -0.75), turned 90 so the column is
    # the 3225's short side (its XI/XO pads are diagonal, so no turn "faces" them).
    _c2 = _c1 + _r_h / 2 + CRTYD_GAP + CRTYD["3225"][1] / 2
    add("Y2", "26 MHz crystal -- PHY reference, facing XI/XO", "3225",
        _c2, _phy_y - 0.50, rot=90.0)
    # col 3: its load caps, one beside each crystal pad.
    _c3 = _c2 + CRTYD["3225"][1] / 2 + CRTYD_GAP + _r_h / 2
    add("C125", "crystal load cap -- Y2 XI", "0402", _c3, _phy_y - 1.50, rot=90.0)
    add("C126", "crystal load cap -- Y2 XO", "0402", _c3, _phy_y + 0.60, rot=90.0)

    for _ref, _desc, _pkg, _bx in _buck:
        add(_ref, _desc, _pkg, _bx, _buck_y)

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

# ⚠ THESE BELONG TO THE OUTPUT PANEL AND MUST NOT BE IN _MPN_RULES. They were, and two
# of them collided: _MPN_RULES matches by LONGEST PREFIX, so the panel's "D8" (relay coil
# flyback) and "D9" (output clamp) beat this board's bare "D" rule and captured D8 and D9
# -- which on THIS board are two of the ten IR EMITTERS. Both would have been quoted as
# unresolved SOD-523 diodes, and nothing could have caught it: the CAD was consistent
# with itself, the netlist was consistent with itself, and DRC does not read either.
# The exact-ref table exists BECAUSE designators are not a clean namespace within a
# board; this was the same failure ACROSS boards. Kept here as documentation of the
# panel's open lines, and deliberately not reachable from mpn().
# elec/mpn_check.py now compares this table against the netlist and is what found it.
_OUTPUT_PANEL_OPEN = (
    ("U14",  (MPN_UNKNOWN,       "",         1.20,  "I2S stereo audio DAC, TSSOP-20. OPEN: "
                                                    "PCM5102A-class is the obvious pick (no "
                                                    "MCLK needed, integrated charge-pump "
                                                    "output, 2 Vrms). CONFIRM the part and "
                                                    "its LCSC stock before layout")),
    ("U15",  (MPN_UNKNOWN,       "",         0.20,  "output buffer op-amp, SOT-23-5. OPEN. "
                                                    "WANTED: rail-to-rail output, >=10 mA "
                                                    "drive into a long cable, and low noise "
                                                    "-- it is the last thing before the jack")),
    ("K1",   (MPN_UNKNOWN,       "",         1.50,  "LATCHING signal relay, 2-coil, SMD. OPEN. "
                                                    "LATCHING is the requirement, not a "
                                                    "preference: a held coil draws current "
                                                    "and hums at the audio it is switching. "
                                                    "De-energised state MUST be the direct "
                                                    "path -- see section 3d")),
    ("Q2",   (MPN_UNKNOWN,       "",         0.05,  "relay coil driver, SOT-23. OPEN: any "
                                                    "logic-level N-ch; AO3400A (C20917, "
                                                    "already on this board as Q1) would do "
                                                    "and would not add a line")),
    ("D8",   (MPN_UNKNOWN,       "",         0.03,  "relay coil flyback, SOD-523. OPEN")),
    ("D9",   (MPN_UNKNOWN,       "",         0.05,  "output clamp, SOD-523. OPEN: bidirectional, "
                                                    "and it sits INSIDE C170 -- it catches the "
                                                    "insertion edge a DC block passes, not the "
                                                    "48 V itself")),
)

# ref-prefix -> (mpn, lcsc, unit_usd, note). Longest prefix wins, so "PD" beats "P".
_MPN_RULES = (
    # --- resolved, verified in LCSC stock 2026-08-01 ---
    ("U6",   ("STM32H743IIT6",   "C89597",   10.005, "LQFP176; same die as the ZIT6 (OTG_HS, "
                                                    "2 MB). @10 price. 335 in stock 2026-09-21. "
                                                    "Its own ADCs are no longer used -- the "
                                                    "five TLV320ADC3140s convert")),
    ("U7",   ("USB3343-CP",      "C633347",  2.6398, "ULPI HS PHY, QFN-24. @10 price. "
                                                "*** OUT OF STOCK at LCSC 2026-08-04 ***")),
    ("U10",  ("USBLC6-2SC6",     "C7519",    0.1829, "USB ESD array, @5+. NOTE SOT-23-6, not the "
                                                    "modelled SOT-563 -- envelope grows")),
    ("U11",  ("TLV9061IDBVR",    "C398358",  0.2505, "single of the same family as U1-U5, so the "
                                                    "mid-rail buffer matches the TIAs. SOT-23-5 "
                                                    "(DBV) -- NOT the SC70 DCK part, whose pinout "
                                                    "differs (TI SBOS839 Table 5-1). "
                                                    "C693480 was WRONG: that is a P6KE39CA TVS")),
    # (U12, the PCM1808, is GONE with the magnetic channel -- it is on the output panel
    #  now, where the pickup lands. Same part, same reasoning, different board.)
    ("U8",   ("AMS1117-3.3",     "C6186",    0.2028, "3V3 DIGITAL, SOT-223 tab, @5+. 0.51 W will "
                                                    "not fit a SOT-23-5. Noisy, but it feeds "
                                                    "the MCU, not the front end")),
    ("U9",   ("SPX3819M5-L-3-3/TR", "C9055", 0.1903, "3V3 ANALOG, 40 uVrms, SOT-23-5, @10+. Low load "
                                                    "(~40 mA) so the small package is fine")),
    # ⚠ THE DUAL, NOT THE QUAD (2026-09-23). Same die, same datasheet, same 10 MHz /
    # 10 nV/rtHz / 500 fA -- the packaging was the entire sourcing problem. JLCPCB stocks
    # 34,405 of this against 107 of the TLV9064SIRTER, "Economic and Standard" either way,
    # and ten duals cost $15.00 a run against the quad's $48.16. One per string; see the
    # summing-node argument at OP_PKG for why it is also the better circuit.
    ("U",    ("TLV9062IDGKR",    "C398356",  0.15,   "dual op-amp, VSSOP-8, 10 MHz GBW, @50+ "
                                                    "500 fA Ib -- the TIA part. 34k in stock")),
    # ⚠ ONE "Y" RULE CANNOT COVER BOTH CRYSTALS, and the old one quietly did: it put
    # a 25 MHz part on Y2, whose job is to clock the PHY at 26. The datasheet audit fixed
    # the netlist and left this table saying "confirm vs USB3343". Per-ref now, and the
    # frequency is the least of it -- CL and ESR are what decide whether an oscillator
    # starts and runs on frequency, and the USB334x fixes both (CL 20 pF, ESR <= 30 ohm).
    ("Y1",   ("TX322525M4LBDD2T", "C5308007", 0.0959, "25 MHz 3225, CL 20 pF, ESR <= 30 ohm "
                                                    "-- MCU HSE")),
    ("Y2",   ("K3A260002010",    "C2835957", 0.0959, "26 MHz 3225, CL 20 pF, ESR <= 30 ohm "
                                                    "-- the USB334x's own limits, T4.13")),
    ("Q1",   ("AO3400A",         "C20917",   0.0849, "N-ch logic-level FET, SOT-23, LED row gate, @5+")),
    # Bare copper. It is a PLACED part as far as the CAD is concerned -- it occupies
    # board area and has to clear its neighbours -- and not a part at all as far as the
    # fab is concerned, which is why it costs nothing and carries no LCSC line.
    ("TP",   ("bare copper pad", "NONE",     0.0,    "SWD test pad -- no component, no "
                                                    "paste, excluded from the BOM and "
                                                    "the CPL by the footprint")),
    ("J1",   ("TYPE-C-31-M-12",  "C165948",  0.1709, "USB-C 16P, @5+; the modelled envelope IS this part")),
    ("U13",  ("LMR33630CRNXR",   "C2071783", 1.82,  "24V->5V synchronous buck, VQFN-HR RNX 2x3, 3 A, "
                                                    "2.1 MHz, 36 V abs max (user, 2026-09-22: the "
                                                    "TPS560430's 600 mA was 105 % used worst case "
                                                    "with the five converters). No FPWM variant is "
                                                    "stocked; at 2.1 MHz / 4.7 uH it stays in CCM "
                                                    "(fixed frequency) above ~0.2 A. 793 in stock")),
    ("L1",   ("SWPA4030S4R7MT",  "C57269",   0.12,  "buck output inductor, 4.7 uH shielded, 4.0 x 4.0 "
                                                    "x 3.0, Isat 3.2 A, DCR 78 mohm. 0.40 A pk-pk "
                                                    "ripple at 2.1 MHz. SHIELDED is not optional -- "
                                                    "an unshielded inductor radiates into 20 TIAs. "
                                                    "42,221 in stock 2026-09-22")),
    # ⚠ "600" IN A FERRITE BEAD PART NUMBER USUALLY MEANS 60 OHM. Murata and Sunlord
    # both code impedance as two digits and a decade multiplier, so BLM18PG600SN1D --
    # 136,668 in stock, the obvious hit for "600 ohm bead 0603" -- is SIXTY ohms, and
    # 601 is the six hundred this board asked for. It is the kind of error nothing
    # downstream can catch: the right package, the right footprint, a tenth of the
    # filtering, and no DRC or netlist check that could ever see it.
    # GZ1608D601TF: 600R@100MHz, 200 mA, DCR 450 mohm, 937,432 in stock 2026-09-17.
    # The rail behind it draws about 11 mA (five TLV9064 at 2 mA, U11, and the 327 uA
    # mid-rail divider), so 200 mA is thirteen times over and the bead drops 7 mV
    # against an LDO with volts of headroom.
    ("FB1",  ("GZ1608D601TF",    "C1002",    0.05,  "0603 ferrite bead, 600R@100MHz, 200 mA, "
                                                    "DCR 450 mohm -- splits the buck's 5 V from "
                                                    "the analog LDO's")),
    # --- generic passives: JLCPCB BASIC classes, exact value set at schematic capture ---
    ("Rf",   ("0402 thick-film R", "BASIC",  0.002, "TIA feedback, per-string value")),
    ("Cf",   ("0402 C0G MLCC",   "BASIC",    0.004, "TIA feedback cap -- C0G, not X7R: the "
                                                    "anti-alias pole must not drift with bias")),
    ("Cd",   ("0402 X7R MLCC",   "BASIC",    0.002, "op-amp decoupling")),
    ("C1",   ("0402 X7R MLCC",   "BASIC",    0.002, "decoupling / crystal load (load caps C0G)")),
    ("C13",  ("0805 X7R MLCC",   "BASIC",    0.01,  "bulk")),
    ("C14",  ("0402 X7R MLCC",   "BASIC",    0.002, "power-input decoupling")),
    ("R",    ("0402 thick-film R", "BASIC",  0.002, "per-string LED ballast")),
    ("Cs",   ("0402 X5R MLCC",   "BASIC",    0.004, "audio ADC supply / reference bypass "
                                                    "(1 uF, 10 uF 6.3 V and 100 nF per SBAS993B "
                                                    "Figure 165)")),
    ("Ci",   ("0402 C0G MLCC",   "BASIC",    0.004, "audio ADC input coupling, 10 nF C0G -- "
                                                    "the channel's signal rides a 48 kHz "
                                                    "carrier, so 10 nF into 20 k is ample")),
    ("Cm",   ("0402 C0G MLCC",   "BASIC",    0.004, "audio ADC INxM coupling to GND, 10 nF C0G "
                                                    "(SBAS993B Fig. 31, single-ended AC-coupled)")),
    # --- OPEN: see BOM.md. These three block ordering. ---
    # RESOLVED. The emitter is 0805 940 nm and WIDE (~120 deg full) because narrow-beam
    # simply is not made in this package -- see the note below and BOM.md. Angle is the one
    # spec to re-confirm on the datasheet at layout; everything else is checked.
    # ⚠ THE IR17-21C IS UNBUYABLE: 34 in stock against a 214 MOQ, pre-order only, and both
    # consignment listings at zero. Replaced by the Lite-On LTE-C9901, verified against the
    # primary datasheet (DS50-2017-0074) rather than a distributor attribute line -- which
    # mattered twice over. JLCPCB quotes "5 mW/sr@20mA" and that is the spec MINIMUM; the
    # TYPICAL is 8 and the max 10, so the part is better than its listing. And the height
    # is 0.98, not the "0603 parts are under 0.8" that had been assumed: it is TALLER than
    # the 0805 it replaces, so the optical gap shrinks instead of growing.
    # +10.9 dB optical at typ (+8.8 at spec min) = +5.4 dB of shot-limited SNR, and the
    # 60 mA DC rating keeps the emitter-current lever that the budget's last line depends on.
    # ⚠ 65 deg IS THE FULL ANGLE -- the datasheet's symbol is 2*theta-1/2, so the half angle
    # is 32.5. At the 1.22 gap a 1.3 mm string subtends 28.0 deg, which leaves 0.13 mm of
    # LATERAL margin to the half-power contour. That is the tightest thing about this part
    # and it is a placement tolerance, not an optics one. theta-1/2 is a half-power point
    # and not a cutoff (the pattern is still ~0.2 at 60 deg), so overrunning it costs a
    # little signal rather than the measurement -- but check it at bring-up.
    # MSL 3, so it needs dry-pack handling; JLC does this, but it is on the traveller.
    ("D",    ("LTE-C9901",       "C2683614", 0.1988, "IR emitter 940 nm, 0603, Lite-On, @1. "
                                                    "8 mW/sr TYP (5 min, 10 max) at 20 mA, 65 deg "
                                                    "FULL angle, 0.98 tall, 60 mA DC. 1.7k in "
                                                    "stock = ~17 runs; thinnest part on the board")),
    # RESOLVED, and the no-consignment dilemma was a false alarm: the LCSC-stocked X01
    # CARRIES THE SAME DAYLIGHT FILTER (740-1040 nm, matched to 830-950 nm emitters),
    # same 0.42 mm2 area, same 0805 2.0x1.25x0.7. It is a drop-in for the absent X02.
    # ⚠ THE ONE PART WITH NO SECOND SOURCE, and it was worth proving rather than
    # ⚠ SUPERSEDED 2026-09-21 -- the detector is the Everlight PD15-22B now (see PD_DY).
    # The sweep below looked only at 0805 lands; the full catalogue (802 photodiodes)
    # has filtered parts in bigger packages, and redesigning the triplet around one
    # was cheaper than the stock problem. Kept for the history.
    # assuming. LCSC's whole catalogue was swept for a DAYLIGHT-FILTERED PIN photodiode
    # in an 0805 land on 2026-09-17 and there is exactly one: this. The near misses all
    # fail on the filter, which is the thing that cannot be given up --
    #   TEMD7000X01   0805, 3,904 in stock, but 350-1120 nm: unfiltered
    #   VEMD1060X01   0805, 1,914 in stock, 350-1070 nm: unfiltered
    #   VEMD8081      5,501 in stock, but 4.8 x 2.5, visible-ENHANCED, and CD 33 pF
    # -- and the filter is load-bearing at Rf = 4M7, where 617 nA of photocurrent
    # saturates the TIA and open room light on an unfiltered diode is already of that
    # order. A package change would also land on the sensing cell, the most constrained
    # geometry on the board.
    # So stock is a PURCHASING problem, not a design one: 95 pieces is four boards, and
    # the project's basis is ten (see "PCB cost basis" in BOM.md, 10 x 20 = 200). Build
    # 2 or 5 and re-check, or pre-order; the reel MOQ is 3,000, which is not the answer.
    ("PD",   ("PD15-22B/TR8",    "C161211",  0.067, "Everlight filtered Si PIN, black epoxy "
                                                    "(730-1100 nm), PEAK 940 nm = the emitter's. "
                                                    "Isc 6.5 uA/(mW/cm2) typ, 4.0 min (@875 nm); "
                                                    "6 pF at VR 5 V, zero-bias C not published. "
                                                    "3.3 x 2.8 x 1.1. 11,271 in stock "
                                                    "2026-09-21 (the VEMD4110X01 it replaces had "
                                                    "95, at $0.58)")),
    # CLOSED 2026-09-17 against JST's own drawing (XH series, SMT type shrouded
    # header): S4B-XH-SM4-TB is A = 7.5, B = 15.0 -- the number this line used to ask
    # somebody to confirm. The six-way S6B recorded here before was 20.0, and the two
    # extra ways it existed for moved to the output panel with the magnetic audio tap.
    # LCSC stocks the (LF)(SN) form, C161861, 20,992 pieces; the bare S4B-XH-SM4-TB
    # listing (C20561980) is zero, which is the same trap the lever board's J1 hit.
    ("J2",   ("S4B-XH-SM4-TB",   "C161861",  0.45,  "4 way SMT side-entry XH on the -Y edge: "
                                                    "24V, PWR_GND, 2 cavities empty. "
                                                    "B = 15.0 per JST")),
)


# EXACT refs, checked before the prefix rules. These exist because reference designators
# are NOT a clean namespace: the string-3 LED ballast is "R3" and the BOOT0 pull-down is
# "R30", so any prefix rule for the R3x group silently swallows a ballast and quietly
# reassigns it from 0603 to 0402. That is exactly the class of stale-derivation bug this
# file guards against elsewhere -- it evaluates fine and is simply wrong -- so the
# ambiguous group is spelled out instead of pattern-matched.
_MPN_EXACT = {r: ("0402 thick-film R", "BASIC", 0.002, "pulls / divider / gate")
              for r in ("R30", "R31", "R32", "R33", "R34", "R35", "R36", "R37", "R38", "R39",
                        "R50", "R51")}
# The five SHDNZ pull-ups. Spelled out for the same reason as the group above: "Rs11" is
# not in any R-prefix group's namespace and should not be quietly adopted by one.
_MPN_EXACT.update({"Rs%d1" % k: ("0402 thick-film R", "BASIC", 0.002,
                                 "converter SHDNZ pull-up -- ground its pad to isolate "
                                 "that converter from the I2C bus")
                   for k in range(1, 6)})
# The five audio converters: exact, because the bare "U" rule is the TIA quad's.
_MPN_EXACT.update({r: ("TLV320ADC3140IRTWT", "C1852021", 3.6456,
                       "TI 4-ch 768 kHz audio ADC, WQFN-24 (RTW). 106 dB SNR (2 Vrms diff). "
                       "306 in stock 2026-09-21; the IRTWR reel (C882863) had 67")
                   for r in ("U14", "U15", "U16", "U17", "U18")})
# C112/C113 are the H7's 0805 VCAP pair, but "C112".startswith("C1") would file them
# under the 0402 line -- the same namespace collision the groups below guard against.
_MPN_EXACT.update({r: ("0805 X7R MLCC", "BASIC", 0.01, "H7 core regulator cap (VCAP)")
                   for r in ("C112", "C113")})
# The audio-ADC bulk/bypass caps are 0805, but "C150".startswith("C1") would file them
# under the 0402 line -- the same namespace collision as R3 vs R30. Spelled out.
_MPN_EXACT.update({r: ("0805 X7R MLCC", "BASIC", 0.01, "audio ADC bypass / DC block")
                   for r in ("C150", "C152", "C153")})
# The buck's furniture: same namespace hazards as the groups above. R40/R41 would fall to
# the 0603 LED-ballast rule and C161/C163 to the 0402 line by accident rather than by
# decision, and C162 is 0805 while C160 is the only 1206 on the board.
_MPN_EXACT.update({r: ("0402 thick-film R", "BASIC", 0.002, "buck feedback divider")
                   for r in ("R40", "R41")})
_MPN_EXACT.update({r: ("0402 X7R MLCC", "BASIC", 0.004, "buck HF bypass / bootstrap")
                   for r in ("C161", "C163", "C165", "C166")})
_MPN_EXACT["C167"] = ("0805 X7R MLCC", "BASIC", 0.01, "buck 5 V output bulk, second")
_MPN_EXACT["C162"] = ("0805 X7R MLCC", "BASIC", 0.01, "buck 5 V output bulk")
_MPN_EXACT["C164"] = ("0805 X7R MLCC", "BASIC", 0.01,
                       "U8 input bulk -- V5_PRE's only local capacitor")
# The output stage (3d). Same namespace hazards again -- R42-R45 would fall to the
# 0603 ballast rule and C171-C173 to the 0402 line by accident rather than decision.
_MPN_EXACT.update({r: ("0402 thick-film R", "BASIC", 0.002, "output stage -- series / gain / filter")
                   for r in ("R42", "R43", "R44", "R45")})
_MPN_EXACT.update({r: ("0402 X7R MLCC", "BASIC", 0.004, "DAC bypass / output filter")
                   for r in ("C172", "C173")})
_MPN_EXACT["C171"] = ("0805 X7R MLCC", "BASIC", 0.01, "DAC analog supply bypass")
# ⚠ THE ONE CAPACITOR ON THIS BOARD THAT IS A SAFETY PART, not a bypass. 100 V is the
# RATING, not margin: during a phantom-power fault it sits charged to 48 V
# continuously. Oversized on purpose (~2.2 uF) so the signal swing ACROSS it stays
# small, which is what makes an X7R part's voltage coefficient a non-issue instead of
# a distortion argument. See section 3b-i.
_MPN_EXACT["C170"] = ("1210 X7R MLCC 100 V", "BASIC", 0.05,
                      "1210 100 V output DC block -- phantom-power protection")
_MPN_EXACT["C160"] = ("1206 X7R MLCC 50 V", "BASIC", 0.03,
                      "1206 50 V input bulk -- an 0805 50 V part loses most of its "
                      "capacitance at 24 V DC bias, so the case size is the derating, "
                      "not the voltage rating")


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


def part_wh(p, table=None):
    """A part's (w, h) envelope AS PLACED. Rotation swaps the axes, and every consumer
    of these tables has to go through here or a rotated part is modelled at the wrong
    size -- which is the kind of error that looks fine in the render and fails at the
    fab."""
    t = PKG if table is None else table
    dx, dy = t[p["pkg"]][0], t[p["pkg"]][1]
    if float(p.get("rot", 0.0)) % 180.0 == 90.0:
        dx, dy = dy, dx
    return dx, dy


def part_span(p):
    dx, dy = part_wh(p)
    return (p["x"] - dx / 2, p["x"] + dx / 2, p["y"] - dy / 2, p["y"] + dy / 2)


# ⚠ THE LAND, NOT THE MOUTH. This was the USB-C's BODY half-depth, which put the
# board's -Y edge on the connector's front face -- and the footprint's pads reach
# further back than the shell does, so part of J1's land sat off the board. The edge
# follows the courtyard now; the mouth still overhangs it, which is what a
# panel-facing connector is supposed to do.
PCB_YM = part("J1")["y"] - CRTYD["USB-C"][1] / 2   # -Y end = the connector's LAND
PCB_L  = PCB_YP - PCB_YM
# ⚠ O-BAND, EXPERIMENTAL (user asked to try it, 2026-09-23). The board is a C: the +Y wrap
# reaches the main body only through the sensing strip, so every digital net between U6 and
# the converters crosses the analog strip. Closing it into an O gives them their own path.
# The +X edge is NOT free -- three things bound it, all measured:
#   1. BEARING SUPPORT. The bridge bearings span x -16.0..0.0 at z 0..16 on every string,
#      and the ARM WALL round them is the 1.6 mm from -17.6 to -16.0. The board stops at
#      -18.0, not -17.6: the 0.4 fit gap has to come out of the BOARD's side, because
#      taking it from -17.6 would thin that wall to 1.2 and it is what holds the bearings
#      that carry string tension. Wall 1.6 intact, air 0.4, board edge -18.0.
#   2. GUIDE RODS -- AND THE BAND DOES NOT NEED HOLES FOR THEM (user, 2026-09-23). Five sit
#      on the near row at x -20.0 and the band crosses that row, but the rods top out at
#      z 2.80, 6.73 mm BELOW the board, and they GO IN BEFORE THE PICKUP. Nothing ever has
#      to pass through the band. The holes that were here cost 1.40 mm necks at five points
#      -- about three traces past each rod -- and deleting them gives the full 5.35 mm for
#      the band's whole length. See INSTALL_NOTES.md: the order is load-bearing now.
#   3. PRINTABILITY. Across the strip's y range the endplate tops out at z 13.9, and the
#      band wants z 9.3..11.13. Cutting only the board's own slot would leave a ROOF of
#      endplate at 11.13..13.9 -- an overhang. The cut has to run to the top instead, which
#      it can, because nothing sits above 13.9 there. ~3000 mm3 of endplate, not the 20268
#      recorded in WORKLIST (that figure was for a full-width opening).
# O_BAND_X0 = None keeps the C. Set it to test the O; the endplate is NOT yet cut for it,
# so the overlap gate will fail on bridge_endplate until that work is done.
O_BAND_X0 = None
_STRIP_X0 = PCB_X0 if O_BAND_X0 is None else O_BAND_X0
O_ROD_HOLE_D = 3.9                                     # kept for the record; nothing uses it
O_ROD_HOLES = []                                       # none -- rods go in before the board

# ── THE O, PROPERLY THIS TIME ────────────────────────────────────────────────
# ⚠ I BUILT THIS WRONG TWICE BEFORE READING THE USER'S DRAWING. The first attempt widened
# the sensing strip 5.35 mm eastward and called it an O; it is not, it is a fatter C, and
# it routed WORSE (10 and 12 unconnected against the C's 9) because one path made wider is
# not a second path. The second reading had the +X band crossing the bearings and concluded
# an O was geometrically impossible. Both missed what the user said plainly: THE BEARINGS
# ARE THE HOLE. The band goes round them on the far side, at x 8.23..23.46 -- 15 mm of
# board, wider than the sensing strip -- and the two wraps close the ring.
#
# The hole is sized outward from the bearings themselves, so it follows them if they move:
#   the bearings, x -16.0..0.0, y +-45.25 (the outermost string plus half a bearing);
#   + MIN_WALL_2P of endplate all round them, because that block carries string tension;
#   + a 45 deg RAMP for the block to climb from the board's seat back up to the bearing
#     top without an overhang -- currently 0, see _O_RAMP.
# ⚠ AND THE BLOCK CANNOT GO AWAY, however good the creep margin looks. The AXLE is Ø8.0
# centred at z 8.0, so it spans z 4.0..12.0 and its bore tops at 12.20 -- straight through
# the board's own band of 10.55..12.15 (user). The block has to carry material all round
# that bore at full height, which is what the hole is for. The creep number says the block
# could be far thinner; the axle says it cannot be absent.
O_SHAPE = True
BE_ARM_W = 4.80          # bridge_endplate.ARM_W; mirrored, it imports US
_BRG_X0 = D.BRIDGE_AXLE_X - D.BRIDGE_BEARING_OD / 2
_BRG_X1 = D.BRIDGE_AXLE_X + D.BRIDGE_BEARING_OD / 2
# ⚠ THE HOLE'S Y IS SET BY THE ARMS, NOT THE BEARINGS, and sizing it off the bearings
# alone quietly decapitated the axle. The arms stand at y +-48.40 and are 4.80 wide, so
# they reach 50.80 -- outside a hole sized to the outermost bearing at 46.85. That put them
# in the BOARD's footprint, the relief cut is the board's own outline, and it took the top
# 1.61 mm off the axle bore: 20% of a Ø8 shaft, open at the top, on both arms. The user
# spotted it in the render.
# Creep was never the risk there (the 90 deg turn loads -X and -Z, and the bore's floor and
# -X wall are both intact below the cut). RETENTION was: this endplate holds the axle with
# NO FASTENER, and an open-topped bore has nothing to stop it lifting out.
_BRG_Y = max(max(abs(D.string_y(i)) for i in range(D.N_STRINGS)) + D.BRIDGE_BEARING_W / 2,
             D.BRIDGE_ARM_Y + BE_ARM_W / 2)
_BRG_TOP = D.BRIDGE_BEARING_Z + D.BRIDGE_BEARING_OD / 2
# ⚠ RAMP ALLOWANCE OFF (user, 2026-09-23: "ignore printability, I want to see what it
# looks like"). It reserved a 45 deg run for the block to climb from the board's seat to
# the bearing top, and measuring says it buys nothing anyway: with it at 0 the ONLY
# unsupported material left anywhere in this region is the axle bore's own crown at
# x -10..-7, which is pre-existing and printable_bore already handles. A vertical wall
# from the seat to the bearing top does not grow outward with height, so it is not an
# overhang. Turn this back on if a print says otherwise.
_O_RAMP = 0.0                                          # was _BRG_TOP - PLINTH_TOP
# ⚠ A COMB, NOT ONE OPENING (user, 2026-09-23). One 30 x 105 hole is the lazy shape and it
# costs the board its whole middle. What actually pokes through the board's plane is:
#   * ten BEARINGS, 5.0 wide on a 9.5 pitch, reaching z 16.0;
#   * two ARMS at y +-48.40, 4.80 wide, which hold the axle and must stay full height;
#   * and between the bearings the endplate's COMB FINGERS, which reach z 16.0 today but
#     are doing retention rather than carrying load (nothing pushes the axle +Z) -- so they
#     are cut down to the board's underside and the board's own strips take that job over.
# That leaves 4.00 mm of PCB between adjacent slots: eleven tracks per signal layer, and
# each strip only has to carry the four nets of its two neighbouring strings. Those strips
# are the ONLY way the detectors reach the +X band, so the comb is not cosmetic -- with one
# big hole the 20 summing nodes would have to detour ~100 mm round the wraps.
# ⚠ EACH SLOT IS AN L, NOT A RECTANGLE, because two different things pass through it and
# they are not the same width (user: "the cuts running too far along y both at the + and -
# ends"). Over the BEARING the slot has to be the bearing's 5.00 plus fit. Past the
# bearing's edge the only thing left is the STRING, 2.032 at the heaviest gauge this
# instrument is built for -- and a rectangle carried the bearing's width all the way to the
# string exit, 1.48 mm too wide per side over 2.54 of length. 75.4 mm2 across ten slots,
# and it came off the +X end of every comb strip, which is exactly where the four nets per
# strip have to funnel.
#
# The string segment needs no vibration allowance: the speaking length ENDS at the bearing
# top, so past x = BRIDGE_AXLE_X the string is dead and only needs a running fit.
_BRG_EDGE = D.BRIDGE_AXLE_X + _BRG_HALF          # -1.19, where the bearing leaves the board
_BRG_HY = D.BRIDGE_BEARING_W / 2 + O_SLOT_CLR    # 2.75
_STR_HY = D.STRING_GAUGE_MAX / 2 + O_SLOT_CLR    # 1.27
O_SLOTS = ([[O_SLOT_X0, D.string_y(i) - _BRG_HY,
             _BRG_EDGE + O_SLOT_CLR, D.string_y(i) + _BRG_HY]
            for i in range(D.N_STRINGS)]
           + [[_BRG_EDGE, D.string_y(i) - _STR_HY,
               O_SLOT_X1, D.string_y(i) + _STR_HY]
              for i in range(D.N_STRINGS)])
# ⚠ NO ARM SLOTS ANY MORE. There were two, one per axle arm, because the arms stood to the
# bearing top at 16.0 and had to pass through the board. They stop at the board's SEAT now
# (bridge_endplate.ARM_TOP), so nothing outboard of the last bearing pokes up at all. Two
# slots' worth of copper comes back, at the +Y and -Y ends of the comb where the summing
# nodes are most crowded -- and the arms' +X edges stop being the board's worst print
# overhang. The slot list is bearings only.
_strip = abs(D.string_y(1) - D.string_y(0)) - (D.BRIDGE_BEARING_W + 2 * O_SLOT_CLR)
assert _strip >= 2 * D.MIN_WALL_2P, (
    "the comb's strips are %.2f mm -- under two walls of PCB" % _strip)
O_HOLE_X0, O_HOLE_X1, O_HOLE_Y = O_SLOT_X0, O_SLOT_X1, _BRG_Y   # kept for the endplate
_SECTIONS = ((HEAD_Y0, PCB_YP, PCB_X1S, TAIL_X1),      # +Y wrap, over the endplate
             (Y_TAIL, HEAD_Y0, STRIP_X1, TAIL_X1),     # full width; _o_hole() cuts the O
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
    # ⚠ BOTH ARE ON THE -X PLINTH NOW, AND THE SKEW IS GONE (user, 2026-09-29: "There seems
    # to be more open space over on the -x side, and that's closer to the optical sensors
    # which are the main thing we need to lock in position"). This SUPERSEDES the previous
    # note here, which said the asymmetry was deliberate and had the tail pushed hard +X to
    # get out of the MCU's way.
    # Both points are what this board exists to locate: the sensor triplets have to land on
    # the integrated lid's slots, and the sensing hardware is the -X column, so two screws in
    # one line beside it constrain the thing that matters more directly than a diagonal did.
    # ⚠ AND THE +X STRIP WAS THE EXPENSIVE SIDE. It already carries C112, C113, R50, TP7 and
    # four ring caps; a 7.6 mm button head in there landed on C111, and clearing it by moving
    # COPPER took nine capacitors -- which invalidated the SAI_FS post-route repair and the
    # searched bring-up-pad sites and cost the board its 0/0 baseline (10 unconnected, 15
    # violations, 11 of them SAI_FS). On -X the whole bill is R30 stepping 1.18 mm and TP8
    # needing the re-search it needed anyway. Move the mount, not the copper.
    # The MCU does NOT follow the screw west -- see _mcu_x1, which used to derive from
    # MOUNT_X_TAIL and dragged U6 41 mm off the board the moment this changed.
    # Both still land in the plinth, which is the only hard requirement, and MOUNT_X_HEAD is
    # the westmost axis that keeps MIN_WALL_2P of plinth outboard of the insert.
    return [(MOUNT_X_HEAD, HEAD_Y0 + MOUNT_KEEP),      # -12.00, hard -X
            (MOUNT_X_TAIL, Y_TAIL - MOUNT_KEEP)]       # +2.40, hard +X


# ⚠⚠ NOTHING MAY STAND UNDER EITHER SCREW HEAD, AND THIS IS THE GUARD THAT WAS MISSING.
# The same fault reached this board THREE times: C112 and C113 each got a hand-written
# step-away beside their own placement, and C111 got none, because the decoupling ring was
# added later and places by pin with no knowledge of the mount. A per-part guard written
# next to one part cannot protect the parts added after it -- so this one runs over every
# placement against every mount point, once, after both exist.
# COURTYARD against the head CIRCLE, not centre-to-centre: the C113 note records that a
# body-clearance check is what let a courtyard overlap through, and a 0402's extents swap
# when it is rotated 90 degrees, which a radius comparison cannot see.
def _assert_mount_heads_clear():
    _hr = TP.JACK_HEAD_D / 2.0
    for _mx, _my in mount_points():
        for _p in PARTS:
            _cr = CRTYD.get(_p.get("pkg"))
            if not _cr:
                continue
            _w, _h = _cr
            if abs(float(_p.get("rot", 0.0)) % 180.0 - 90.0) < 1e-6:
                _w, _h = _h, _w
            _dx = max(0.0, abs(_p["x"] - _mx) - _w / 2.0)
            _dy = max(0.0, abs(_p["y"] - _my) - _h / 2.0)
            _d = math.hypot(_dx, _dy) - _hr
            assert _d >= PKG_CLR, (
                "%s's courtyard is %.3f mm from the M4 head at (%.2f, %.2f) -- the head "
                "would sit on it (needs %.2f)" % (_p["ref"], _d, _mx, _my, PKG_CLR))


_assert_mount_heads_clear()


# ROUTED-OUTLINE FILLETS. A PCB outline is CNC-ROUTED, not cut from plate, so any polygon
# is fine -- but the mill cannot cut a sharp INTERNAL corner. Every concave corner comes
# out with the cutter's radius whether it is drawn or not, so it is drawn: the model was
# optimistic by ROUT_R at three places. External corners stay sharp (the mill goes round
# the outside of those).
ROUT_R = 1.0                                   # ~2 mm router bit, the OUTLINE
# ⚠ THE SLOTS ARE MILLED WITH A DIFFERENT, SMALLER BIT AND THE MODEL HAD THEM SHARP.
# JLCPCB routes irregular internal cutouts with a 1.0 mm bit (0.8 on request), so no slot
# corner can be sharp -- the cutter simply cannot reach into one. The model drew 20 sharp
# rectangles, which is the UNSAFE direction: a sharp corner shows MORE opening than the
# fab will deliver, so anything checked against it is checked against a hole that will not
# exist. Per slot it is 0.32 mm2 of material the model was giving away, all of it in the
# corners, which is exactly where a bearing shoulder or a string would find it.
# Modelled as the MORPHOLOGICAL OPENING of the nominal polygon -- erode by the bit radius,
# dilate back -- which is literally what the tool does: the milled region is everywhere the
# centre of a radius-R disc can reach, swept by that disc. It needs no corner bookkeeping
# and it is right by construction in every case, including the two that catch hand-written
# fillet lists: a CONVEX corner of the opening rounds (the tool cannot get in), a REFLEX
# one stays sharp (the tool goes round the outside of the material that juts in), and a
# feature narrower than the bit vanishes instead of being quietly drawn.
MILL_D = 1.0                                   # internal-cutout bit
MILL_R = MILL_D / 2
assert min(_s[3] - _s[1] for _s in O_SLOTS) >= MILL_D, (
    "a slot is narrower than the %.1f mm cutter and cannot be milled at all" % MILL_D)


def _slot_polys():
    """The slots as MERGED per-string polygons -- the bearing rect and the string rect of
    one string overlap, so cutting them separately would invent two interior corners that
    are not there. Eight vertices: six convex (the cutter rounds them) and the two at the
    step, which are reflex and stay sharp."""
    n = D.N_STRINGS
    out = []
    for i in range(n):
        bx0, by0, bx1, by1 = O_SLOTS[i]
        sx0, sy0, sx1, sy1 = O_SLOTS[n + i]
        assert sx0 <= bx1 + 1e-9, "string slot %d no longer meets its bearing slot" % i
        out.append([(bx0, by0), (bx1, by0), (bx1, sy0), (sx1, sy0),
                    (sx1, sy1), (bx1, sy1), (bx1, by1), (bx0, by1)])
    return out


def _milled(poly, t, zc, grow=0.0):
    """`poly` as the cutter actually leaves it: opened by the bit radius. `grow` shrinks
    the opening first, for a slip-fit copy of the board."""
    wp = cq.Workplane("XY", origin=(0.0, 0.0, zc)).polyline(poly).close()
    if abs(grow) > 1e-9:
        wp = wp.offset2D(-grow)
    wp = wp.offset2D(-MILL_R).offset2D(MILL_R, kind="arc")
    return wp.extrude(t / 2 + 1.0, both=True)


def _concave():
    """The internal corners, where a section steps NARROWER than its neighbour.

    The -Y wrap -> compute step at (COMPUTE_X0, WRAP_Y) USED to be one. It is not any more:
    the compute section now runs -X to PCB_X1S, the same edge the wrap and the strip use, so
    that side of the board is a single straight line and there is no corner there to cut.
    Filleting a point that sits mid-edge would notch the outline rather than relieve it, so
    the entry is generated from the geometry instead of listed.

    ⚠ AND EVERY ENTRY IS NOW DERIVED FROM _SECTIONS. The +X pair used to be listed
    unconditionally off PCB_X0, which was correct only while the strip was narrower than
    the wraps. Squaring the board off made those two points MID-EDGE on a straight line --
    and NearestToPointSelector does not fail on a point that is not a corner, it happily
    returns the nearest edge and fillets it. A phantom fillet notches the outline and
    nothing complains. Generated from the real steps instead, so it cannot go stale."""
    corners = []
    for (ay0, ay1, ax1, ax0), (by0, by1, bx1, bx0) in zip(_SECTIONS, _SECTIONS[1:]):
        # ⚠ ay0, NOT ay1. _SECTIONS is listed TOP-DOWN, so section n meets section
        # n+1 at n's LOW edge: ay0 == by1 for every consecutive pair. ay1 is n's far
        # edge, a straight run of outline with no corner on it at all. This was
        # unreachable while every section shared one -X edge (no steps -> no corners
        # -> empty list), and trimming the strip to V5_PRE is what first generated
        # one: both corners came out a whole section too far +Y. That is the phantom
        # fillet this docstring warns about, arriving by the other door.
        seam = ay0                             # the two sections meet here
        if bx0 < ax0 - 1e-9:                   # +X edge steps IN going -Y: concave
            corners.append((bx0, seam))
        if ax0 < bx0 - 1e-9:
            corners.append((ax0, seam))
        if bx1 > ax1 + 1e-9:                   # -X edge steps IN
            corners.append((bx1, seam))
        if ax1 > bx1 + 1e-9:
            corners.append((ax1, seam))
    return corners


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
    if O_SHAPE:
        # each slot SHRINKS by `grow` where the outline grows: a slip-fit copy of the board
        # must stay clear of what pokes through it on the inside too. AS MILLED, not as
        # drawn -- see MILL_D.
        for poly in _slot_polys():
            out = out.cut(_milled(poly, t, zc, grow))
    for fx, fy in _concave():
        out = out.edges(NearestToPointSelector((fx, fy, zc))).fillet(ROUT_R + grow)
    return out


def _part_solid(p):
    """Package standing UP from the board's top face (single-sided, components at the
    strings). None where the package has NO BODY: a test point is bare copper, PKG['TP']
    height 0.00, and a zero-height box is not a solid -- OCC raises Standard_DomainError
    and takes the whole build with it. Nothing to draw is not the same as an error."""
    dx, dy = part_wh(p)
    dz = PKG[p["pkg"]][2]
    if dz <= 0.0:
        return None
    return box_at(dx, dy, dz, x=p["x"], y=p["y"], z=PCB_TOP + dz / 2)


def opt_pcb() -> cq.Workplane:
    """The assembled optical strip: FR4 + EVERY placed component at its true Z, all
    facing UP. Fab/purchased -> NO standalone STEP (cadkit convention); it exists in the
    assembly as the fit-check that it clears the strings and fits the carrier."""
    pcb = _outline()
    for p in PARTS:
        body = _part_solid(p)
        if body is not None:                          # bare pads (TP) have no body
            pcb = pcb.union(body)
    # ⚠⚠ THE M4 CLEARANCE HOLES ARE BACK, WHICH IS THE 2026-09-23 INSTRUCTION COMPLETED
    # (user: "get rid of the M4 mounting holes. We can add them back later based on where
    # there's available space"). The space has now been found and the fab data has them: both
    # mounts sit on the -X plinth, and elec/optical.py emits them through BOARD_NOTES
    # ["cutouts"] as Edge.Cuts circles with router keepouts.
    # Until this, the board was held by NOTHING while the endplate still built anchors,
    # inserts and screws to mount_points() -- and the overlap gate had been reporting the
    # consequence all along as optical_pcb <-> optical_screw_0/1, a 4.0 mm shank crossing
    # 1.6 mm of laminate at each point. A fab house would have shipped solid laminate there.
    # ⚠ CYLINDERS, NOT box_at. The note this replaces records that they were SQUARE prisms
    # when they last existed here -- which is both a CAD/fab divergence and the reason the
    # FreeCAD render showed square holes. `cyl` matches what the mill actually makes.
    # ⚠ AND FROM mount_points(), THE SAME SOURCE THE SCREW AND THE FAB READ. Three things
    # have to agree here -- the CAD plate, the Edge.Cuts circle and the screw -- and the last
    # time they were hand-typed the placement disagreed with both (Cd11 sitting 0.47 mm inside
    # where the head one belongs). Driven off one function they cannot drift.
    # cad_geom_check compares the CAD's hole count against the routed board's and reported
    # "the CAD plate has 10 hole(s), the routed board 12" until this was added.
    for _mx, _my in mount_points():
        pcb = pcb.cut(cyl(M4.shaft_clr_d, PCB_T + 2.0, PCB_BOT - 1.0)
                      .translate((_mx, _my, 0.0)))
    # ⚠ NO JACK ACCESS HOLE, BECAUSE THE JACK IS NOT UNDER THE BOARD. This cut it, and
    # elec/optical.py emitted the matching circle on Edge.Cuts -- where it was a FAB
    # DEFECT, not a hole: the jack sits at x -33.93 and the board's -X edge is at -32.16,
    # so the O4.4 circle straddles the edge. On Edge.Cuts that is "invalid_outline: Circle
    # + Segment" (the one unexplained violation that survived every route this week) and
    # it stretched the routed outline's bounding box to 61.19 x 188.53 against the CAD's
    # 57.21, which is the CAD/fab disagreement cad_geom_check has been reporting. One
    # object, both findings.
    #
    # The invariant is "a driver can reach the jack", and the board satisfies it by not
    # being there: 1.775 mm of clear air from the screw centre to the board edge against
    # the 1.444 a 2.5 mm hex key needs across corners. Asserted below rather than assumed,
    # because the margin is 0.33 mm and the strip has moved in X twice this month.
    # ⚠ _s[2], NOT _s[3] -- THIS ASSERT WAS VACUOUS (2026-09-29). _SECTIONS tuples are
    # (y0, y1, x1, x0): [2] is the -X edge (-32.156) and [3] is TAIL_X1, the +X edge
    # (+25.056). Reading [3] compared the jack at x -33.93 against the FAR side of the board
    # and computed a 58.99 mm gap, so the assert passed unconditionally and could never catch
    # the one thing it exists to catch -- the strip growing -X into the driver. The comment
    # above had the right number all along (1.775 mm); only the code was measuring the wrong
    # edge. With [2] it reproduces 1.775 against the 1.444 a 2.5 mm hex key needs.
    _x0 = min(_s[2] for _s in _SECTIONS)          # the board's -X edge
    gap = _x0 - JACK_ACCESS_XY[0] if JACK_ACCESS_XY[0] < _x0 else 0.0
    assert gap >= _HEX25_R, (
        "the pickup-height jack at x %.2f is %.2f from the board's -X edge at %.2f, and a "
        "2.5 mm hex key needs %.3f. The board is in the driver's way: either move the "
        "strip +X or cut jack_access() again -- and if you cut it, cut it as a NOTCH in "
        "the outline, not as a circle on Edge.Cuts straddling the edge."
        % (JACK_ACCESS_XY[0], gap, _x0, _HEX25_R))
    return pcb


def jack_access(grow: float = 0.0) -> cq.Workplane:
    """The pickup jack's access hole, as a cutter. Shared: the board cuts it, and
    the endplate cuts the SAME hole through the pad under it -- both are in the
    screw's way, and one description keeps them concentric."""
    jx, jy = JACK_ACCESS_XY
    return (cq.Workplane("XY")
            .add(cq.Solid.makeCylinder(JACK_ACCESS_D / 2 + grow, 40.0,
                                       pnt=cq.Vector(jx, jy, PCB_BOT - 20.0))))


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
APER_X1 = BAND_X0 - D.MIN_WALL_2P                # -26.66: leaves a FULL two-bead strip of
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
    # ⚠ THERE IS NO COVER ANY MORE (COVER_T 0). Return None rather than a zero-height box:
    # OCCT raises Standard_DomainError on a 0 mm extrude, so the endplate's union of this
    # blew up with a stack trace that says nothing about covers. Callers skip a None.
    if COVER_T <= 0.0:
        return None
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


# ── CABLE CONDUIT -- both plugs leave the board and drop into the body here ──────────
# REQUIREMENT (user): get the USB-C and the 6-way XH down into the instrument WITHOUT any
# cut-out in the magnetic pickup's top panel, through a channel big enough to pass a
# CONNECTOR -- one at a time -- not merely a cable.
#
# The deck is never touched, and the reason is a happy accident of where the two parts end:
# the deck's +X edge is TP.PX0 = -16.60 and the ENDPLATE begins there, so -Y of the board
# the endplate's own top face is open sky at x -16.60..8.60. The conduit is a plain vertical
# shaft in that face. Probed: the endplate is solid at every z from 6.00 down through the
# fill slab across y -100..-131, so the shaft has material to pass through for its whole
# depth and breaks out into the foot box below.
#
# SIZED BY WHAT MUST PASS, not by the cable:
#   XHP-6 plug      17.40 x 5.75 -- B4B-XH-A 4-way is 12.4 on JST's drawing (already in
#                                   BOM.md) and XH pitch is 2.5. The same extrapolation
#                                   predicted the S6B's B = 20.0, which the LCSC page then
#                                   confirmed, so it is a checked method rather than a guess.
#   USB-C overmold  12.35 x 6.50 -- the USB-IF MAXIMUM, so ANY cable passes, not just one
#                                   particular vendor's boot.
# Worst of each axis + 1.5 clearance for a hand-fed pass-through.
# ORIENTATION: the shaft is LONG IN Y and NARROW IN X, and that is the whole trick. A plug
# is fed through with its wide axis along Y -- the direction the endplate has 27 mm to
# spare -- so X only has to clear the plug's THIN axis. Sizing it the other way up needed
# 20.40 of X and left 2.40 mm walls in a structural slab; this way X needs 9.50 and the
# walls are 7.85. Y is generous anyway because it also has to span where the cable turns
# down, which is past the back of a mated plug.
CONDUIT_CLR = 1.5
# ⚠ THE BOARD'S CONNECTOR IS A 4-WAY, NOT A 6-WAY, AND THIS SIZES THE CONDUIT. Audited
# 2026-09-18 against the netlist: elec/optical.py's J2 is an S4B-XH-SM4-TB -- "S4B" is
# four circuits -- carrying 1=GND 2=+24V 3=+24V 4=GND and nothing else. This constant is
# a SIX-way housing, and by its own formula a 4-way is 12.4 rather than 17.40.
#
# It is not cosmetic, because _COND_PASS below takes max(_XH4_W, _USBC_W): the conduit is
# sized to pass a plug 5 mm wider than the one that exists, through an endplate wall this
# file already asserts is out of room. opt_cables() draws the same 6-way plug and a
# six-conductor bundle for a four-conductor cable.
#
# The likely history is the same one that left a 24 V tee on the CAN rail for this board
# (see src/wiring.py): it was going to sit on the four-wire CAN-plus-power bus, which is a
# 6-pin XH at the motors, and it ended up with USB to the panel and power-only on a 4-way.
# Flagged rather than changed -- CONDUIT_W, _COND_PASS and the endplate wall all move
# together, and the assertion below is what would catch a bad edit.
# ⚠ APPLIED 2026-09-25, having been "flagged rather than changed" above since 2026-09-18.
# J2 IS AN S4B -- four circuits -- so this was sizing the conduit to pass a plug 5 mm wider
# than the one that exists. It stopped being cosmetic the moment board length became the
# binding constraint: _COND_PASS was 20.40 on a six-way that is not fitted, and that number
# is what the endplate wall is asserted against.
_XH4_W, _XH4_D = 12.4, 5.75                                   # S4B-XH housing, 4 way
_USBC_W, _USBC_H = 12.35, 6.50                                # USB-IF MAX overmold
# Plug body length along the mating axis. ASSUMPTIONS, and the ones to check against real
# cable before cutting metal -- overmolds are not standardised.
# J1 IS A STRAIGHT PLUG, and the right-angle idea it replaces was wrong -- J2 is what kills
# it. J1 sits -X of J2, so its lead must cross J2's footprint to reach the shaft. A
# right-angle leaves +X *at the plug*, which is exactly where J2's body is: the cable turned
# +X at y -112.85, dead inside J2's -120.85..-106.85 span, and clipped straight through it
# (user-caught from a render).
#
# The escape is not a detour but a LONGER plug. A straight USB-C's own back face lands at
# -126.85, already 6.00 mm clear of J2's -120.85, so the lead turns +X in free space with a
# single bend and no doubling back. A right-angle would have needed exit +X, turn -Y, turn
# +X again -- three bends to solve a problem the straight plug does not have.
#
# So the earlier claim that the angled plug saved a bend was true only in isolation; once
# the neighbouring connector is in the picture it costs two. J2 stays straight for its own
# reason: it sits nearly over the shaft already.
#
# PLUG_L IS A PURCHASING SPEC, NOT A MEASUREMENT. Nothing is ordered yet, and overmold
# LENGTH is not standardised -- USB-IF fixes the cross-section (12.35 x 6.50) but not this,
# and surveyed parts run ~10-25 mm. So rather than guess a number and hope, the geometry is
# made insensitive to it in the direction that matters and the number becomes a rule for
# what to BUY, which is checkable at order time:
#
#   SHORT plug -- the dangerous case, because it was what put J1's lead into J2. Removed as
#     a risk entirely: a lead that crosses a neighbour now turns at whichever back face is
#     further -Y, ITS OWN OR THE NEIGHBOUR'S. A short plug just runs a little further in
#     free air before turning. No length can make it clip.
#   LONG plug -- only eats conduit depth, and there is a hard limit past which the -Y
#     exterior wall drops under MIN_WALL_2P. So the BOM specifies a maximum overmold and
#     the assertion below holds the model to it. See _WALL_Y for where that limit is and
#     why it is a surveyed number rather than a derived one.
#
# ⚠ THAT MAXIMUM TIGHTENED FROM 20 TO 17.5 (2026-09-15), and this is the constant that
# absorbed it -- which is what it was built for. Spacing the layout by COURTYARD rather
# than by BODY moved the board's -Y face 2.58 mm further out (the XH's land reaches back
# further than the USB-C's, and the deeper of the two now sets the edge), and that came
# straight off the conduit's depth budget. Nothing about the instrument changed; the
# rule for what to buy did. Surveyed USB-C overmolds run ~10-25 mm, so <= 17.5 narrows
# the choice without leaving it -- it rules out the long boots, not the market.
PLUG_L = {"J1": 17.5, "J2": 14.0}    # USB-C boot (SHORT -- see below); XHP-6 + relief
# ⚠ J1 IS BACK AT 17.5 -- A STOCK USB-C BOOT -- AND THE EXPERIMENT THAT MOVED IT IS WORTH
# KEEPING. Through _COND_SPAN -> CONDUIT_D -> CONDUIT_Y0, this one number caps the board's
# LENGTH: at 17.5 neither the ULPI corridor past 7 mm nor ANY east-edge routing lane fits,
# not 3 mm and not 1. Shortening it to 14.0 (a real short-overmold cable) bought 2.2 mm of
# board and let both in.
# It bought no CONNECTED NETS. Measured both ways with the same escapes: 9 mm corridor +
# 3 mm east lane on the longer board gives 5 unconnected / 0 unexpected, and 7 mm + no lane
# on the stock-cable board gives 5 unconnected / 0 unexpected. Identical. So the shorter
# board wins on everything else -- no constraint on which USB-C cable the owner may use,
# and no cable-vs-endplate clash (the conduit mouth tracks PCB_YM, so growing the board
# walked it south and left endplate material for the lead to cross, 94.2 mm3).
# Leave 17.5. If a future change makes board length worth buying again, 14.0 is the lever
# and 12.4 is its floor -- below that _COND_PASS, getting a plug THROUGH the shaft, binds
# instead and nothing further is won.
# J1 IS A STRAIGHT PLUG, and the right-angle idea it replaces was wrong -- J2 is what kills
# it. J1 sits -X of J2, so its lead must cross J2's footprint to reach the shaft. A
# right-angle leaves +X *at the plug*, which is exactly where J2's body is: the cable turned
# +X at y -112.85, dead inside J2's -120.85..-106.85 span, and clipped straight through it
# (user-caught from a render).
#
# The escape is not a detour but a LONGER plug. A straight USB-C's own back face lands at
# -126.85, already 6.00 mm clear of J2's -120.85, so the lead turns +X in free space with a
# single bend and no doubling back. A right-angle would have needed exit +X, turn -Y, turn
# +X again -- three bends to solve a problem the straight plug does not have.
#
# So the earlier claim that the angled plug saved a bend was true only in isolation; once
# the neighbouring connector is in the picture it costs two. J2 stays straight for its own
# reason: it sits nearly over the shaft already.
#
# PLUG_L IS A PURCHASING SPEC, NOT A MEASUREMENT. Nothing is ordered yet, and overmold
# LENGTH is not standardised -- USB-IF fixes the cross-section (12.35 x 6.50) but not this,
# and surveyed parts run ~10-25 mm. So rather than guess a number and hope, the geometry is
# made insensitive to it in the direction that matters and the number becomes a rule for
# what to BUY, which is checkable at order time:
#
#   SHORT plug -- the dangerous case, because it was what put J1's lead into J2. Removed as
#     a risk entirely: a lead that crosses a neighbour now turns at whichever back face is
#     further -Y, ITS OWN OR THE NEIGHBOUR'S. A short plug just runs a little further in
#     free air before turning. No length can make it clip.
#   LONG plug -- only eats conduit depth, and there is a hard limit past which the -Y
#     exterior wall drops under MIN_WALL_2P. So the BOM specifies a maximum overmold and
#     the assertion below holds the model to it. See _WALL_Y for where that limit is and
#     why it is a surveyed number rather than a derived one.
#
# ⚠ THAT MAXIMUM TIGHTENED FROM 20 TO 17.5 (2026-09-15), and this is the constant that
# absorbed it -- which is what it was built for. Spacing the layout by COURTYARD rather
# than by BODY moved the board's -Y face 2.58 mm further out (the XH's land reaches back
# further than the USB-C's, and the deeper of the two now sets the edge), and that came
# straight off the conduit's depth budget. Nothing about the instrument changed; the
# rule for what to buy did. Surveyed USB-C overmolds run ~10-25 mm, so <= 17.5 narrows
# the choice without leaving it -- it rules out the long boots, not the market.
PLUG_L = {"J1": 17.5, "J2": 14.0}    # USB-C boot (SHORT -- see below); XHP-6 + relief
# ⚠ J1's 14.0 IS A REQUIREMENT ON THE CABLE, NOT A MEASUREMENT OF AN ARBITRARY ONE. It was
# 17.5, and that number -- through _COND_SPAN -> CONDUIT_D -> CONDUIT_Y0 -- was the single
# thing capping this board's LENGTH, and through length its ROUTABILITY. At 17.5 neither
# the ULPI corridor past 7 mm nor any east-edge routing lane fits at all; not 3 mm, not 1.
# At 14.0 both fit (board 188.53 -> 190.73), and the 9 mm corridor is the one measured
# configuration in which every ULPI net routes.
# So the build needs a SHORT-OVERMOLD USB-C cable: 14.0 mm or less from the connector face
# to the back of the boot. That is a common stock item, but it is a real constraint and
# belongs in the BOM rather than in someone's head -- a standard 17.5 mm boot will not fit
# the endplate, and the assertion at the bottom of this file is what will say so.
# The floor is 12.4: below that _COND_PASS (getting a plug THROUGH the shaft) binds instead
# and nothing further is won, so there is no reason to specify tighter than 14.
# ⚠ THE -Y BUDGET IS A MEASUREMENT, NOT A DERIVATION (user, 2026-09-16). There are
# 37.25 mm between this board's -Y edge and the instrument's -Y exterior in the model on
# main, and that whole span is available -- to the board, the conduit, the mated plug and
# the cable's bend alike. Nothing may leave it; everything inside it is ours to spend.
#
# It used to be derived instead, as CH.Y_LO + MIN_WALL_2P, and the derivation was wrong by
# 12.84 mm: CH.Y_LO is the chassis rail's DATUM, and it was being read as the outside of
# the instrument when there is structure beyond it. That is a bad kind of wrong -- it does
# not fail, it just quietly charges the layout for room it already had. It cost the USB
# chain 0.85 mm, which was enough to stop the PHY sitting behind the socket where it
# belongs, and the pair took a corner to avoid a wall that was not there.
#
# ANCHORED TO THE BOARD EDGE AS SURVEYED, not to PCB_YM, which is the whole point: PCB_YM
# moves when the layout grows, so measuring the budget from it would make the budget move
# with the thing it is supposed to constrain and the assertion could never fail.
YM_AT_SURVEY = -109.54                                        # PCB_YM on main when measured
Y_BUDGET     = 37.25                                          # board -Y edge -> instrument
_WALL_Y = YM_AT_SURVEY - Y_BUDGET + D.MIN_WALL_2P             # -145.19, conduit's -Y limit
CONDUIT_W = max(_XH4_D, _USBC_H) + 2 * CONDUIT_CLR            #  9.50, along X (thin axis)
# Y answers TWO separate requirements and must satisfy the larger. Sizing it on the span
# alone was a latent bug: it happened to be big enough only because the straight USB-C plug
# was longer than the XH is wide, so shortening a plug would have quietly made the shaft too
# narrow to PASS one.
_COND_PASS = max(_XH4_W, _USBC_W) + 2 * CONDUIT_CLR           # 20.40: get a plug THROUGH
_COND_SPAN = max(PLUG_L.values()) + 2 * CONDUIT_CLR           # 20.50: reach past a MATED plug
CONDUIT_D = max(_COND_PASS, _COND_SPAN)                       # 20.40, along Y
CONDUIT_Y1 = PCB_YM - 2.0                                     # -124.58, clear of the board
CONDUIT_Y0 = CONDUIT_Y1 - CONDUIT_D
assert CONDUIT_Y0 >= _WALL_Y - 1e-9, (
    f"conduit reaches y {CONDUIT_Y0:.2f}, past the {D.MIN_WALL_2P} exterior wall limit "
    f"{_WALL_Y:.2f} -- the longest plug ({max(PLUG_L.values()):.1f}) no longer fits the "
    f"endplate. Specify a shorter overmold or move the board +Y.")
CONDUIT_XC = (BAND_X0 + D.BRIDGE_BASE_X1) / 2                 # centred in the endplate band


# The channel is OPEN TO -X, and that is a printing requirement, not a convenience. The
# endplate builds +X -> -X, so a blind vertical shaft would have material RESUME across its
# whole -X face -- a 20.40 x 21 bridge over void, anchored only at its Y edges. Chamfering
# that face at 45 deg cannot close it either: 20.40 of Y needs 10.2 mm of X and the shaft
# would run out through XLO before it got there. Running the void out through the -X face
# instead means material never resumes at all, every layer is a simple notch rooted on the
# one below, and the cable arrives directly in the chassis interior where it needs to be.
CONDUIT_X1 = D.BRIDGE_BASE_X1 - D.MIN_WALL_2P                 # 23.46, +X wall kept
RUN_Z      = DECK_TOP - 16.0                                  # harness plane in the box
CONDUIT_Z0 = RUN_Z - 4.75                                     # floor, half a bundle below


def opt_conduit(grow: float = 0.0) -> cq.Workplane:
    """The channel cutter: down from the endplate's top face, then out its -X face."""
    x1 = CONDUIT_X1 + grow
    # -X limit is the endplate's OWN FACE, not past it. Running 4 mm further -X (the first
    # attempt) chewed 19.5 mm out of the 57.4 mm +Z RETENTION LIP, which protrudes -X in
    # exactly this -Y bay and is what stops the endplate lifting out of the deck. Stopping
    # at the face keeps the lip whole AND still prints: the void ends at the part's own -X
    # surface, so material never resumes behind it. The cable clears the lip by height
    # instead -- the lip hangs in the deck-bottom Z band and the harness plane is well below
    # it, so the run passes underneath rather than through.
    x0 = BAND_X0 - grow
    return box_at(x1 - x0, CONDUIT_D + 2 * grow, (DECK_TOP + 1.0) - (CONDUIT_Z0 - grow),
                  x=(x0 + x1) / 2, y=(CONDUIT_Y0 + CONDUIT_Y1) / 2,
                  z=((CONDUIT_Z0 - grow) + DECK_TOP + 1.0) / 2)


def pi_target():
    """The Pi's centre in world coords -- where the USB run terminates.

    LAZY import: electronics imports chassis, and THIS module is imported by
    bridge_endplate, so a module-level import risks the cycle that already had to be
    untangled once in electronics.py."""
    from . import electronics as EL
    bb = EL.pi5().val().BoundingBox()
    return ((bb.xmin + bb.xmax) / 2, (bb.ymin + bb.ymax) / 2, (bb.zmin + bb.zmax) / 2)


from . import motor_bank as _MB                            # no cycle: motor_bank imports neither
PI_RUN_Z = _MB.SEAT_TOP + 4.5                             # the USB run's last legs: one cable OD
                                                          # over the BANK -- not just over the motor:
                                                          # each bay stands up past its tee, and the
                                                          # bus-A trunk rides the mouths just above


def pi_column_x():
    """X of the USB run's last +Y leg: three cable diameters +X of the Pi's +X face. The
    compute boards stand against the keyhead endplate with string 1's motor 1.6 mm off the
    Pi, so the run crosses that motor's Y band here, down at PI_RUN_Z just over the motor
    top, and turns -X into the Pi only once it is at the Pi's Y. Three diameters, not one,
    keeps it off the bay wiring's riser column (wiring.BAY_X, one mm inside the motor's
    -X face). Lazy import, as pi_target."""
    from . import electronics as EL
    return EL.pi5().val().BoundingBox().xmax + 3 * 2.6


def usb_run_length():
    """Routed path length, board plug -> Pi, as (segments, total_mm). Orthogonal, because a
    harness follows the box rather than flying point to point. This is what picks the cable
    length off the shelf, so it is computed rather than eyeballed."""
    px, py, pz = pi_target()
    zc = PCB_TOP + PKG["USB-C"][2] / 2
    y_turn = PCB_YM - PLUG_L["J1"] / 2
    segs = [("+X to the shaft", abs((CONDUIT_XC - 2.2) - part("J1")["x"])),
            ("down the shaft", zc - RUN_Z),
            ("along Y", abs(py - y_turn)),
            ("-X to the keyhead", abs(pi_column_x() - (CONDUIT_XC - 2.2))),
            ("down over the motor bank", RUN_Z - PI_RUN_Z),
            ("-X into the Pi", abs(pi_column_x() - px)),
            ("down into the Pi", abs(pz - PI_RUN_Z))]
    return segs, sum(v for _, v in segs)


def opt_cables(which: str = "all") -> cq.Workplane:
    """The MALE connectors and their cable, at true diameter -- an assembly aid, not a part.

    ⚠ SPLIT BY WHAT THE CABLE IS, because one grey solid could not say. `which` is
    "usb" (J1's plug, its lead, and the long haul to the Pi), "pwr" (J2's plug and its
    24 V lead), or "all". The build registers the two separately so each carries its own
    name and its own colour in the viewer -- violet for USB and red for 24 V, the same
    scheme the loose wires already use -- and so either can be hidden on its own while
    tracing a route. As one part they were a single near-black mass, which also broke the
    project's rule that black is reserved for TPU.

    Modelled so the route can be planned rather than assumed: each plug leaves its socket
    along -Y, runs to the conduit's mouth and turns down it. The USB-C socket sits -X of the
    endplate, so its lead also has to travel +X to reach the shaft -- which is the one thing
    about this route that is not obvious from a side view."""
    USB_OD, XH_OD = 2.6, 4.0          # slim shielded USB-2 (BOM wire table); 6x 26 AWG bundle
    out = None

    def add(s):
        nonlocal out
        out = s if out is None else out.union(s)

    _WANT = {"usb": ("J1",), "pwr": ("J2",), "all": ("J1", "J2")}[which]
    _yturn, _path, _od = {}, {}, {}
    # ⚠ EACH LEAD TAKES THE CONDUIT SIDE NEAREST ITS OWN PLUG, and it used to take the far
    # one. J1 sits at x +9.88 and dropped at -2.2; J2 sits at -29.29 and dropped at +2.2 --
    # so each lead had to cross the OTHER's drop column to reach its own, and the two
    # leads interpenetrated. Swapping the offsets removes both crossings at once: no lead
    # passes over a column it does not own, and neither run reaches the other's x band.
    # (Splitting opt_cables in two is what exposed this. As one unioned solid the clash
    # was absorbed silently; tightening the crossing test alone made it WORSE -- 9.4 mm3
    # to 40.2 -- because both leads then turned down at the same y. The offsets were the
    # actual fault.)
    for ref, w, h, od, xoff in (("J1", _USBC_W, _USBC_H, USB_OD, +2.2),
                                ("J2", _XH4_W, _XH4_D, XH_OD, -2.2)):
        if ref not in _WANT:
            continue
        p, plen = part(ref), PLUG_L[ref]
        zc = PCB_TOP + PKG[p["pkg"]][2] / 2                   # cable/plug centre height
        add(box_at(w, plen, h, x=p["x"], y=PCB_YM - plen / 2, z=zc))
        # TURN AT WHICHEVER BACK FACE IS FURTHER -Y -- its own, or that of any neighbour the
        # lead has to cross in X. Deriving it from the plug's own length alone is what let
        # the right-angle J1 drive through J2; deriving it from the neighbour alone would
        # make a LONG plug double back on itself. Taking the deeper of the two is correct
        # for every plug length, so no overmold dimension can produce a clash.
        # ⚠ THE CROSSING TEST WAS SHORT BY THE CABLE'S OWN RADIUS, and the 9.4 mm3 it let
        # through was invisible until opt_cables was split in two: as ONE unioned solid the
        # power lead and the USB plug could interpenetrate and the union simply absorbed it.
        # The run's SOLID is |dx| + od wide (see the box below), so it reaches od/2 past the
        # endpoints this test used -- J2's path stops at x 2.2 but its copper reaches 4.2,
        # and the USB-C plug's overmold starts at 3.88. Test the solid, not the path.
        lo = min(p["x"], CONDUIT_XC + xoff) - od / 2.0
        hi = max(p["x"], CONDUIT_XC + xoff) + od / 2.0
        backs = [PCB_YM - plen]
        crosses = []
        for q in ("J1", "J2"):
            if q == ref:
                continue
            qx, qw = part(q)["x"], (_USBC_W if q == "J1" else _XH4_W)
            if lo < qx + qw / 2 and hi > qx - qw / 2:
                backs.append(PCB_YM - PLUG_L[q])       # crosses q: clear q's back face too
                crosses.append(q)
        y_turn = min(backs) - CONDUIT_CLR
        assert CONDUIT_Y0 < y_turn < CONDUIT_Y1, \
            f"{ref}: cable turns down at y {y_turn:.2f}, outside the conduit"
        # the lead as a PATH, built once at the end as one octagonal cable (helpers.oct_cable)
        # -- it used to be separate boxes and cylinders added piece by piece
        z_end = USB_Z if ref == "J1" else PWR_Z_TURN
        _yturn[ref] = y_turn
        col = CONDUIT_XC + xoff
        _path[ref] = [(p["x"], PCB_YM - plen, zc), (p["x"], y_turn, zc), (col, y_turn, zc),
                      (col, y_turn, z_end)]
        _od[ref] = od
    # ---- and on to the OUTPUT BOARD, which is where both cables actually go ----------------
    # ⚠ THEY USED TO GO TO THE PI, AND ONE OF THEM THROUGH THE RAIL. The USB lead ran the
    # length of the instrument to the Pi, through the middle of the -Y rail's section
    # (y -134.83 against a rail at -139.15..-128.75) -- a collision that was PARKED in the
    # gate's deferred list, which is exactly why nobody saw it. And the 24 V lead stopped at
    # the bottom of the conduit, connected to nothing (user: "the red one stops short and
    # doesn't go very far at all"). The USB hub moved onto the output board: its J4 is "hub
    # downstream -> the optical board, ~100 mm", and its J9 is "24 V out to the optical pickup
    # board". Both are a few centimetres from the conduit's foot.
    from .electronics import op_origin, op_top, OP_BOARD_X
    if "J2" in _WANT:
        # 24 V: across the conduit's floor to its +Y side, down the slot (opt_pwr_slot) into
        # the endplate's board recess, and onto J9 from above -- J9 is a top-entry XH.
        xd = CONDUIT_XC - 2.2
        j9 = op_top("J9")
        _path["J2"] += [(xd, PWR_Y, PWR_Z_TURN), (xd, PWR_Y, PWR_Z_REC),
                        (j9[0], PWR_Y, PWR_Z_REC), (j9[0], j9[1], PWR_Z_REC), j9]
        add(oct_cable(_path["J2"], _od["J2"]))
    if "J1" not in _WANT:
        return out
    # USB: out through the conduit's mouth into the bay -- the only part of that mouth the
    # rail leaves open is y -128.75..-124.58 -- over the output board, down, and into the
    # USB-A plug standing in J4's mouth on the board's -X edge.
    xu = CONDUIT_XC + 2.2
    ua_mouth = op_origin()[0] - OP_BOARD_X / 2          # the board's -X edge = J4's mouth
    ua_end = ua_mouth - USBA_PLUG_L
    zc4 = op_top("J4")[2] - 3.3                         # USB-A shell axis, mid-height
    y4 = op_top("J4")[1]
    add(box_at(USBA_PLUG_L, USBA_PLUG_W, USBA_PLUG_H, x=(ua_mouth + ua_end) / 2, y=y4, z=zc4))
    _path["J1"] += [(xu, USB_Y, USB_Z), (BAND_X0 - 1.0, USB_Y, USB_Z),
                    (USB_DROP_X, USB_Y, USB_Z), (USB_DROP_X, y4, USB_Z),
                    (USB_DROP_X, y4, zc4), (ua_end, y4, zc4)]
    add(oct_cable(_path["J1"], _od["J1"]))
    return out


# Where the two optical leads run below the conduit's plug level (see opt_cables).
USB_Z = RUN_Z + 2.1                     # -7.5: the USB turns ABOVE the 24 V lead's column
PWR_Z_TURN = RUN_Z - 2.4                # -12.0: the 24 V lead turns under the USB's run,
                                        # 0.35 over the conduit floor at CONDUIT_Z0
USB_Y = -126.6                          # both leads' y in the conduit's open mouth strip
PWR_Y = -126.4                          # (y -128.75..-124.58, the rail on one side)
PWR_Z_REC = -25.5                       # the 24 V lead crossing into the board recess,
                                        # 0.3 under its roof at FOOT_Z
USB_DROP_X = -84.0                      # the USB drops to J4's height out in the bay, -X of
                                        # the 24 V loop and clear of the board-to-Pi lead
USBA_PLUG_L, USBA_PLUG_W, USBA_PLUG_H = 25.0, 16.0, 8.0   # USB-A male, past the mouth
XH_OD = 4.0                             # the 24 V lead (6x 26 AWG), as opt_cables draws it


def opt_pwr_slot() -> cq.Workplane:
    """The endplate cut the 24 V lead drops through, from the conduit's floor into the
    output board's recess. It runs out through the endplate's -X face rather than stopping
    inside it: the part prints -X off its +X face, so a void that ended inside would leave a
    face of material printed over it -- a bridge. Open to the -X face, its only X-facing end
    is at +X, which the print meets as a floor."""
    x0, x1 = BAND_X0 - 1.0, CONDUIT_XC + 5.0
    y0, y1 = PWR_Y - 2.2, -120.8        # into the recess, which starts at -122.8
    # up past the lead's own turn: it crosses the conduit's +Y wall at PWR_Z_TURN, above the
    # conduit's floor, so a slot that stopped at the floor left 2.8 mm3 of wall in the lead
    z0, z1 = PWR_Z_REC - 2.1, PWR_Z_TURN + XH_OD / 2 + 0.5
    return box_at(x1 - x0, y1 - y0, z1 - z0, x=(x0 + x1) / 2, y=(y0 + y1) / 2,
                  z=(z0 + z1) / 2)


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
    if O_BAND_X0 is None and (STRIP_X1 < BAND_X1 - STRIP_GROW_MX - 1e-9
                              or PCB_X0 > BAND_X0 + STRIP_GROW_PX + 1e-9):
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
    # ⚠ AND IT IS BOUNDED IN X BY THE BEARINGS, WHICH IS WHY THE OP-AMPS COULD MOVE. A
    # string runs from the nut in -X, over its bearing, and then DOWN to the changer: past
    # _STRING_EXIT_X it has already crossed this board's z band and is below the copper.
    # So the +X band is the one place on the board with nothing overhead, and a SOIC-14
    # there is free where the same part at the sensor row pins the whole assembly 0.61 mm
    # below the axle. Bound at O_SLOT_X1 rather than at _STRING_EXIT_X so the slot's own
    # clearance is on the safe side of the test.
    # ⚠ AND THE BUDGET IS A FUNCTION OF X, NOT A CONSTANT -- see string_budget_at(). The
    # part's -X edge is its worst case: that is where the string swings widest. What is
    # asserted is the MARGIN each part achieves over the raw budget, not a flat gap: the
    # flat gap charged every part on the board the swing of a string 20 mm away, which is
    # what kept a 1.75 mm package out of a band that comfortably takes one.
    for p in PARTS:
        dz = PKG[p["pkg"]][2]
        x0, _, y0, y1 = part_span(p)
        if y1 <= -SENSE_HL or y0 >= SENSE_HL or x0 >= O_SLOT_X1 - 1e-9:
            continue
        clr = STRING_BOT_MIN - (PCB_TOP + dz)
        got = clr / string_budget_at(x0)
        if got < CLR_MARGIN_MIN - 1e-9:
            raise AssertionError(
                f"optical strip: {p['ref']} ({p['desc']}, {p['pkg']}) stands to "
                f"Z={PCB_TOP + dz:.2f} under the sensing field, leaving {clr:.2f} to the "
                f"lowest string at {STRING_BOT_MIN:.2f} -- {got:.2f}x the "
                f"{string_budget_at(x0):.2f} budget at x={x0:.2f}, under the "
                f"{CLR_MARGIN_MIN}x floor")
    # 5. the COVER must clear the strings above and the parts below it -- WHEN THERE IS ONE.
    # ⚠ BOTH CHECKS BELOW ARE ABOUT A LID THAT NO LONGER EXISTS. With COVER_T at 0 the
    # "cover underside" collapses onto the sensor face, so every part taller than the
    # emitter fails a test whose subject has been deleted. Guard them rather than delete
    # them: the cover comes back the moment someone sets COVER_T, and check 4 above already
    # guards the thing that still matters, which is parts against the STRINGS.
    if COVER_T <= 0.0:
        return
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
    # Against the HEAD, not the hole. This used to keep parts 3.2 from the screw axis --
    # a clearance-hole ring -- while the button head that actually lands on the board
    # reaches 3.8 (and was drawn at 3.5, which hid it). A part inside that radius is
    # crushed by the screw that is supposed to be holding the board.
    _head_r = TP.JACK_HEAD_D / 2
    for mx, my in mount_points():
        for q in PARTS:
            x0, x1, y0, y1 = part_span(q)
            gap = math.hypot(max(x0 - mx, mx - x1, 0.0), max(y0 - my, my - y1, 0.0)) - _head_r
            if gap < PKG_CLR - 1e-9:
                raise AssertionError(
                    f"optical strip: {q['ref']} ({q['desc']}) is {gap:.2f} from the "
                    f"O{TP.JACK_HEAD_D} button head of the M4 mount at ({mx:.2f}, "
                    f"{my:.2f}) -- under PKG_CLR {PKG_CLR}; the head would crush it")
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
    # 8. NOTHING may stand in the jack's access hole. This is the one feature on the
    # board that is defined by ABSENCE, which makes it the easiest to lose: the parts are
    # unioned onto the board AFTER the hole is cut, so a component that drifts over it
    # simply plugs it back up. The result is still one clean printable solid, still gate-
    # green, and still wrong -- the screw underneath becomes unreachable and nobody finds
    # out until an assembled instrument needs its pickup height set. Assert the intent
    # (a clear line of sight to the screw) rather than the placement that happens to give
    # it, so this survives the cluster being moved again.
    _jx, _jy = JACK_ACCESS_XY
    for p in PARTS:
        x0, x1, y0, y1 = part_span(p)
        dx = max(x0 - _jx, _jx - x1, 0.0)
        dy = max(y0 - _jy, _jy - y1, 0.0)
        gap = math.hypot(dx, dy) - JACK_ACCESS_D / 2
        if gap < PKG_CLR - 1e-9:
            raise AssertionError(
                f"optical strip: {p['ref']} ({p['desc']}, {p['pkg']}) is {gap:.2f} from "
                f"the jack's O{JACK_ACCESS_D} access hole at ({_jx:.2f}, {_jy:.2f}) -- "
                f"under PKG_CLR {PKG_CLR}. That hole is a driver's only route to the "
                f"pickup-height screw; a part over it plugs it silently.")
    # 9. the board must clear the deck it rides over
    if STANDOFF < 1.6:
        raise AssertionError(
            f"optical strip: only {STANDOFF:.2f} between the board and the deck at "
            f"{DECK_TOP:.2f} -- no room for the carrier's ledges")


_assert_field_clear()
