"""The M3 socket head cap screw (ISO 4762, the 2.5 mm key) and its drop-in brass insert, as the
benches and the direct instrument use them.

Lifted out of src/belt_tensioner.py (lead, 2026-11-17, v1 removal round 3) so that the
instrument's parts do not import a v1 belt clamp for a screw. belt_tensioner reads it back.
"""

from __future__ import annotations

from . import dimensions as D
from cadkit.fasteners import FastenerSpec

HEAD_D   = 5.5
HEAD_H   = 3.0
SCREW_L  = 12.0
INS_D    = 4.7            # McMaster 94459A130, brass heat-set M3: OD over the knurl 4.7,
INS_L    = 4.3            # installed length 4.3 (pilot end 3.9). OFF THE DRAWING -- MEASURE
                          # one before printing. It is not heat-set here: it drops into a
                          # side pocket and the screw pulls it against a shoulder.
INS_SLIP = 0.1            # the pocket over the insert's OD, so a printed slot takes a
                          # knurled part by hand.
M3 = FastenerSpec(
    name="M3", screw_d=3.0, pitch=0.5, selftap_d=3.2, shaft_clr_d=D.M3_CLR_D,
    insert_pilot_d=INS_D, insert_depth=INS_L, insert_l=INS_L, insert_bore_d=3.4,
    boss_prot=5.0)
INS_POCKET = INS_D + INS_SLIP                # 4.8 the pocket's bore
