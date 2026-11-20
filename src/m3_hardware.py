"""The M3 socket head cap screw (ISO 4762, the 2.5 mm key) and its drop-in brass insert, as the
benches and the direct instrument use them.

Lifted out of src/belt_tensioner.py (lead, 2026-11-17, v1 removal round 3) so that the
instrument's parts do not import a v1 belt clamp for a screw. belt_tensioner reads it back.
"""

from __future__ import annotations

from . import dimensions as D
import dataclasses as _dc

from cadkit.fasteners import M3 as _CK_M3

HEAD_D   = 5.5
HEAD_H   = 3.0
SCREW_L  = 12.0
# THE INSERT IS cadkit.fasteners.M3's (user, 2026-11-17: every fitted insert's pocket from cadkit, by
# mode -- HEAT_SET 4.8 round, NUT 5.5 round / 5.1 sideways); only the clearance is this project's.
M3 = _dc.replace(_CK_M3, shaft_clr_d=D.M3_CLR_D)
INS_D    = M3.insert_od       # 4.7 over the knurl (McMaster 94459A130)
INS_L    = M3.insert_l        # 4.3
# AN M3's FREE CLEARANCE, PRINTED ROUND along the build (user, 2026-11-17, bench: 3.6 "has a pretty
# tight grip on the M3" in the old sleeve's fin, 3.7 slides). Not for laser-cut steel (3.4 there),
# nor for a hole sideways to the build (a teardrop prints over: 3.4 is free there).
CLR_PRINTED_D = 3.7
# THE BELT CLAMP'S SIDE-ENTRY SLOT ALONE keeps its own 4.8 (bench-proven r6, locked): a slot the
# insert slides into sideways, not a pocket. Nothing else may use INS_POCKET.
INS_SLIP = 0.1
INS_POCKET = INS_D + INS_SLIP                # 4.8 the pocket's bore
