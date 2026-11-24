"""THE CM5's WI-FI ANTENNA, INSIDE THE INSTRUMENT (user + lead, 2026-11-23).

The CM5's on-module PCB antenna fails all three of Raspberry Pi's placement rules here
(RP-008180-DS-8 4.1.2: it faces the drive's steel, the steel wall bar is 9.5 mm behind it, it
sits over the brain board), so Wi-Fi goes through the certified external kit, SC0480
(dtparam=ant2; elec/prices.json modules.antenna_kit_sc0480). AND NOTHING POKES OUT (user): the
dipole lives inside, behind plastic only.

WHERE (tools/check_antenna.py --search, cached build #1139): the body floor's -Y bay beside
motor 8, the dipole lying straight along -X at (y -74, z -100). Of every axis-aligned placement
inside the body that keeps 15 mm from metal and 10 mm from board copper within the cable's
reach, only four clusters exist; this one is the only one whose way out is short and all
plastic: 8 mm down through the floor, and -Y through the body wall's band BELOW the steel wall
bar (which stops at z -93.7). Margins as found: 15.8 to motor 8, 16.2 to wall_bar_0, 67.5 to
the brain board.

MOUNTING (branner, src.direct_bench's body): a plastic boss standing up off the floor at
BOSS_X carrying the kit's D-hole (D_HOLE_D with a flat at D_HOLE_FLAT, product brief
RP-008179-DS-3 Figure 1) on the axis, PANEL_T thick there; the bulkhead's hex and toothed washer
on its +X side, nut and antenna on its -X side; a saddle clip near the tip.

tools/check_antenna.py GATES THE MARGINS in every build: a motor or a wall bar that moves
toward the dipole fails the build instead of quietly detuning the Wi-Fi.
"""
from __future__ import annotations

BASE = (-238.0, -74.0, -100.0)      # the dipole's knurled base (where the SMA joins), mm
AXIS = (-1.0, 0.0, 0.0)             # the dipole lies from BASE along this
DIPOLE_L = 108.5                    # straight, incl. its Ø10 base (brief: 108.5 +- 1)
DIPOLE_R = 4.0                      # its Ø8 body ...
BASE_R, BASE_L = 5.0, 12.0          # ... and its Ø10 knurled base (brief Figure: Ø10), ~12 long
CONN_L = 14.0                       # the bulkhead SMA behind BASE (11 thread + 2 hex flange + the cable's boot)
CONN_R = 4.7                        # its 8 mm hex across corners / 2
BOSS_X = BASE[0] + 2.0              # the boss's -X face: the nut and washer sit between it and BASE
D_HOLE_D, D_HOLE_FLAT = 6.5, 6.0    # the kit's panel hole: Ø6.5 with one flat 6.0 across
PANEL_T = 2.75                      # 2.5-3.0 at the hole (11 mm of thread: washer, panel, nut, antenna)

METAL_MIN = 15.0                    # lead, 2026-11-23: >= 15 mm to any steel / metal
COPPER_MIN = 10.0                   # >= 10 mm to any board copper
CABLE_L = 205.0                     # the kit's U.FL cable
UFL = (-127.4, -83.8, -61.6)        # the CM5's U.FL, from Raspberry Pi's CM5 STEP placed on the brain board


def segments():
    """[(p0, p1, r)]: the dipole and the connector behind it, as capsules along AXIS."""
    a = AXIS
    at = lambda t: tuple(BASE[k] + a[k] * t for k in range(3))   # noqa: E731
    return [(at(0.0), at(BASE_L), BASE_R), (at(BASE_L), at(DIPOLE_L), DIPOLE_R),
            (at(-CONN_L), at(0.0), CONN_R)]


def solids():
    """The dipole and its connector as cadquery solids (cylinders), for exact distances."""
    import cadquery as cq
    out = []
    for p0, p1, r in segments():
        d = [p1[k] - p0[k] for k in range(3)]
        n = sum(v * v for v in d) ** 0.5
        out.append(cq.Solid.makeCylinder(r, n, cq.Vector(*p0), cq.Vector(*[v / n for v in d])))
    return out
