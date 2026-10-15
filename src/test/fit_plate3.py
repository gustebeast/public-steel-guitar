"""JOINERY PLATE 3: plate 2's rules (fit_plate2) on the pairs it left open.

    py -3.12 -m src.test.fit_plate3            # every pair's dims, corners, overhangs, walls, gap
    py -3.12 -m src.test.fit_plate3 --export   # ...and write src/test/test_plate3_petg_gf.step

WHAT PLATE 2 TAUGHT (the user's fingers, 2026-10-14, PETG-GF):
  nozzle-made tenon, layer-made socket (either way up): EVEN all along; 0.25 a short joint,
            0.30 a long one; 0.35 a touch of wobble (B) / not printed (A3 came off the bed).
  both halves layer-made (C standing, D mouth up): tight at entry and seated, loose between
            -- each layer's outline bulges where it turns at the joint's ends, so the fit is
            the ENDS' wherever the two halves' ends meet; the middle wobbles even at 0.25.

SO THIS PLATE:
  ll_standing, ll_mouth_up   again, lower (0.15-0.25), with an end LEAD-IN on every
                             layer-made half (fit_plate2.LEAD) to take the ends out of it
  nl_mouth_up                A3 again (0.35, its number is 1), on a foot this time
  nn                         nozzle tenon, nozzle socket (plate 1's round head) on the new rules
  ln                         layer tenon (head up), nozzle socket -- A's mirror

Left out: a tenon printed HEAD-DOWN (its base's mating face hangs flat over air either side
of the neck) or SIDEWAYS (the head cantilevers off the neck): neither prints as drawn, so
each is a different joint, not another orientation of this one.
"""
from __future__ import annotations

import sys

from . import fit_plate2 as P2

TAG = "p3"
LEAD = {"lead": P2.LEAD_P3}       # what plate 3 printed (0.2 at the tip, gone by 1.6)

# (name, tenon prints, socket prints, clearances[, options]) as fit_plate2.PAIRS; "N" a
# socket standing on its end too (its profile in the layers)
PAIRS = [
    ("nl_mouth_up", "N", "down", (0.35,)),
    ("ll_standing", "up", "up", (0.15, 0.20, 0.25), LEAD),
    ("ll_mouth_up", "up", "down", (0.15, 0.20, 0.25), LEAD),
    ("nn", "N", "N", (0.25, 0.30, 0.35)),
    ("ln", "up", "N", (0.20, 0.25, 0.30), LEAD),
]


def plate():
    return P2.plate(PAIRS, TAG)


def main(argv=None):
    return P2.main(argv, PAIRS, TAG, "test_plate3_petg_gf.step")


if __name__ == "__main__":
    sys.exit(main())
