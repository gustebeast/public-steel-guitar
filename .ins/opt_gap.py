"""What the sensor-to-string GAP is worth, and what the cover costs to keep.

WHY THIS EXISTS: optical_pickup.py lists four levers for the thin-string problem --
emitter beam angle (unavailable), per-string LED current, TIA gain, and distance from the
termination. The GAP is not on that list, and OPT_GAP is the one number in the whole Z
stack that is a bare round 3.0 with a comment saying what it is and not why. Every other
datum there is derived. So it has never been costed.

THE MODEL, and it is a model -- say so rather than quoting its output as measurement:

  emitter is ~120 deg full angle (IR17-21C), i.e. roughly Lambertian, so on-axis
  irradiance at the string goes as 1/h^2;
  the illuminated LENGTH of string grows with h as the cone spreads, ~h;
  so power intercepted by a string of diameter D goes as (1/h^2)(D)(h) = D/h;
  the string scatters and a detector of area A at ~h collects ~A/h^2 of it;
  => SIGNAL ~ D.A / h^3.

n = 3 sits between the 1/h^2 of a plane target and the 1/h^4 of a point one, which is
what a LINE target should give. It is not measured. Treat every dB below as +-a few, and
as a RANKING of options rather than a prediction.

Everything else is read from elec/optical.py's own noise budget, which is careful and
already includes photon shot noise: 143 nA of signal on the thinnest string, Rf = 1M,
MID = 0.33 V, and the per-term input-referred noise densities.
"""
import math

# ── from elec/optical.py's budget, unchanged ────────────────────────────────
I_SIG = 143e-9          # A, thinnest string, at today's gap
RF = 1e6                # ohm
MID, RAIL = 0.33, 3.3   # V -- the TIA sits at MID and swings up
N_SHOT = 0.15           # pA/rtHz, signal shot, at today's signal
N_RF = 0.13             # pA/rtHz, sqrt(4kT/Rf)
N_EN = 0.09             # pA/rtHz, en x 2 pi f Cin at 60 kHz
N_MISC = math.hypot(0.02, 0.02)

# ── the Z stack as built ────────────────────────────────────────────────────
GAP_THICK = 3.000       # sensor face -> THICKEST string underside (the datum)
GAP_THIN = 3.838        # -> THINNEST string. 0.84 further, and it sets SNR.
COVER_GAP, COVER_T = 0.300, 1.600
CLEAR = 1.100           # cover top -> thickest string underside


def noise(gain, rf=RF):
    """Total input-referred noise when the signal is `gain` x today's, with Rf `rf`.

    Only shot scales with signal (as sqrt), and only Rf thermal with Rf (as 1/sqrt)."""
    return math.sqrt((N_SHOT * math.sqrt(gain)) ** 2
                     + (N_RF * math.sqrt(RF / rf)) ** 2
                     + N_EN ** 2 + N_MISC ** 2)


def snr_db(gain, rf=RF):
    base = I_SIG / noise(1.0)
    return 20 * math.log10((I_SIG * gain * (rf / RF)) / noise(gain, rf)
                           / (base * 1.0)) if False else \
        20 * math.log10((I_SIG * gain) / noise(gain, rf) / base)


def gain_for(new_thin_gap):
    return (GAP_THIN / new_thin_gap) ** 3


AMB_HEADROOM = (RAIL - MID) / RF        # A of DC photocurrent before the TIA clips

print("as built: thin-string gap %.3f mm, SNR reference 0 dB" % GAP_THIN)
print("          ambient headroom %.2f uA (Rf %.0f k, MID %.2f V)"
      % (AMB_HEADROOM * 1e6, RF / 1e3, MID))
print("          elec/optical.py calls 1 uA of ambient a realistic bright case (-9 dB)")
print()
print("%-42s %7s %7s %9s" % ("option", "gap", "signal", "SNR"))
opts = [
    ("as built", GAP_THIN, RF),
    ("clearance 1.10 -> 0.70", GAP_THIN - 0.40, RF),
    ("cover 1.6 -> 0.8 (1-bead; it will sag)", GAP_THIN - 0.80, RF),
    ("both of the above", GAP_THIN - 1.20, RF),
    # ⚠ WITHOUT THE COVER THE CLEARANCE CASE BECOMES THE PD, NOT THE EMITTER FACE. The
    # PD15 stands 1.10 off the board and the emitter 0.85, so the tallest thing under the
    # string is a photodiode 0.25 ABOVE the face that OPT_GAP measures from. Holding the
    # same 1.10 mm of air the cover has today gives OPT_GAP 1.35, not 1.10, and 5.4x rather
    # than the 7.8x a naive face-to-string reading predicts.
    ("NO COVER, 1.10 PD-to-string", 2.188, RF),
    ("NO COVER, 1.10 + Rf 1M -> 250k", 2.188, 250e3),
    ("NO COVER, 0.90 + Rf 250k", 1.988, 250e3),
]
for name, g, rf in opts:
    gn = gain_for(g)
    print("%-42s %6.3f %6.1fx %+8.1f dB%s"
          % (name, g, gn, snr_db(gn, rf),
             "   headroom %.1f uA" % ((RAIL - MID) / rf * 1e6) if rf != RF else ""))
print()
print("THE COVER IS PROTECTING HEADROOM, NOT NOISE. Removing it widens the detector's")
print("field of view; if that takes ambient from 1 uA to ~3.7 uA (the solid-angle ratio")
print("for +-30 deg -> +-60 deg) it passes %.2f uA and the TIA clips on a halogen wash."
      % (AMB_HEADROOM * 1e6))
print("Dropping Rf to 250k restores it four-fold and costs only the Rf thermal term,")
print("which the extra signal more than pays for -- see the last row.")


# ── PER-STRING BALANCE (user, 2026-09-23): "every string needs to function as a hard
# floor, but beyond that ... that should be balanced" ────────────────────────────────
#
# ⚠ CLOSING THE GAP MAKES THE BALANCE WORSE, which is the thing to know before spending
# it. The strings' centres are coplanar, so a thin string's surface sits a FIXED distance
# further from the sensor than a thick one's -- and that fixed offset is a bigger fraction
# of a small gap than of a large one. Shrinking the gap therefore helps the fat strings
# more than the thin ones and widens the spread the user wants closed.
#
# The board already carries both levers per string: R1-R10 set emitter current and Rf
# sets TIA gain, both "per-string VALUES" in optical_pickup.py's own words. Emitters run
# at 21 mA of a 65 mA rating, and shot-limited SNR grows as sqrt(current), so there is
# 10*log10(65/21) = +4.9 dB available where it is needed.
import sys
sys.path.insert(0, '.')
from src import dimensions as D  # noqa: E402

STRING_Z = D.STRING_Z
GAUGES = D.GAUGES_C6_IN


def per_string(face_z, i_led_mA=21.0):
    """(gap, signal) for each string at a given sensor-face height."""
    out = []
    for g_in in GAUGES:
        d = g_in * 25.4
        h = (STRING_Z - d / 2) - face_z
        out.append((h, d / h ** 3 * (i_led_mA / 21.0)))
    return out


def report(name, face_z, led=None):
    rows = per_string(face_z, 21.0) if led is None else \
        [per_string(face_z, c)[i] for i, c in enumerate(led)]
    ref = max(s for _, s in rows)
    db = [10 * math.log10(s / ref) for _, s in rows]
    print("%-34s spread %4.1f dB   worst string %d" % (name, max(db) - min(db),
                                                       db.index(min(db)) + 1))
    return db


print()
print("PER-STRING BALANCE (dB relative to the best string, C6 demo set):")
old = report("as built (face 11.984)", 11.984)
new = report("no cover  (face 13.634)", 13.634)
# rebalance: push current where it is short, capped at the 65 mA rating
need = [min(65.0, 21.0 * 10 ** (-d / 10.0)) for d in new]
bal = report("no cover + per-string current", 13.634, need)
print()
print("per-string emitter current to balance (mA, 65 max): %s"
      % ", ".join("%.0f" % c for c in need))
