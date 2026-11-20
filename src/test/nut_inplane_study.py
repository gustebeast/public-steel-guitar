"""NUT CLAMP PROPOSAL (2026-11-19): every steel part is a flat laser-cut 4 mm 304 plate, one per
string, standing in the string's own plane -- the same pocket-per-string layout as nut_block_v2.

Per string, in the string's plane (XZ), at nut_block_v2's frame (X = 0 old break, +X to bridge,
Z = 0 string top):

  GREEN   crown plate. Moves only in Z. Crown r2 at x 0.85; runs straight down to a ledge at the
          endplate bottom, where a U-bent snippet of the string pinches under a common DATUM edge
          (green sits at datum - gauge). Height screw from -X under the anchor plate (v2 wedge).
  ANCHOR  the U plate. Fixed: hangs on the Ø8 axle shaft (the bridge axle SKU) through every plate,
          the axle in the printed fingers as in v2. Its +X leg is BLUE: the string turns down over
          a laser-cut r1.5 corner and runs down its -X edge. Its -X leg holds an M3 square nut in a
          window; an M3 x 10 cap screw (2.5 key) runs along X in a slot cut in the plate and pushes
          ORANGE, a small pad plate, against the string. Screw, nut, both legs and the web are one
          steel loop: the clamp force never reaches plastic, and everything loads IN-PLANE, where a
          4 mm plate is strong. Tail leaves the window bottom sideways into the gap, then down.

Run:  PYTHONPATH=. py -3.12 src/test/nut_inplane_study.py    (prints checks, writes PNG + STEPs)
"""
from __future__ import annotations

import math
import os

import cadquery as cq

from src import dimensions as D
from src import nut_block_v2 as N
from src.test import nut_clamp_study as S

# ── the layout ──────────────────────────────────────────────────────────────────────────────
T_PL = 4.0                       # plate, 304
S.XB_FACE, S.ZB_TOP, S.RB = -11.0, -7.0, 1.5     # blue's string edge, top, corner (laser-cut radius)
X_BACK = N.X_BACK                # -31.5, today's -X face
G_LO, G_HI = 0.010 * 25.4, D.STRING_GAUGE_MAX

BLUE_X1 = -3.3                   # blue's +X edge; green starts at -2.7 (0.6 air)
PAD_D, PAD_H = 5.25, 10.0        # orange: chosen with the screw length so ONE screw fits every gauge
WEB_TOP = -20.5                  # window floor; orange stands on it
SCREW_Z = WEB_TOP + PAD_H / 2    # -15.5
LEG_X0, LEG_X1 = -26.3, -20.3    # the nut leg
NUT_S, NUT_M = 5.5, 1.8          # DIN 562 M3 square nut
NUT_X0, NUT_X1 = -23.8, -23.8 + NUT_M + 0.1
SCREW_L, HEAD_H, HEAD_D = 10.0, 3.0, 5.5           # ISO 4762 M3 x 10
SLOT_W = 3.3
LEG_TOP = -9.0
ROD_C, ROD_HOLE = (-20.5, -27.5), D.BRIDGE_AXLE_D + 0.4
PLATE_BOT = -34.0

# ── loads ───────────────────────────────────────────────────────────────────────────────────
T, MU, SF = N.STRING_T, N.MU, 2.0
YIELD_304 = 205.0                # JLCCNC's floor for their 304


def checks():
    out = []
    b_hi, b_lo = S.break_deg(G_HI), S.break_deg(G_LO)
    out.append(("break .080 >= 15", b_hi >= 15, f".080 {b_hi:.1f} deg, .010 {b_lo:.1f} deg"))
    out.append(("bar clearance >= 0.8", S.bar_clearance() >= 0.8, f"{S.bar_clearance():.1f}"))
    # one screw length for every gauge: head underside between the leg and the -X face
    for g in (G_LO, G_HI):
        tip = S.XB_FACE - g - PAD_D                   # where the tip meets orange
        under = tip - SCREW_L
        ok = (under <= LEG_X0 + 0.05) and (under - HEAD_H >= X_BACK)
        out.append((f"M3x10 fits at {g / 25.4:.3f}", ok,
                    f"tip {tip:.2f}, head {under:.2f}..{under - HEAD_H:.2f} (leg {LEG_X0}, face {X_BACK})"))
    # clamp
    turn = math.radians(90 - S.break_deg(G_HI))
    t_cl = T * math.exp(-MU * turn)
    n = SF * t_cl / (2 * MU)
    out.append(("clamp force (2x slip, mu .15)", n < 2260 / 2, f"{n:.0f} N; M3 A2-70 proof 2260 N; ~{0.2 * n * 3 / 1000:.2f} N.m"))
    # blue leg, in-plane: clamp at the screw, string pull at the corner, root at the window floor
    bw = BLUE_X1 - S.XB_FACE
    I = T_PL * bw ** 3 / 12
    cz = S.corner_c()[1]
    m = n * (SCREW_Z - WEB_TOP) + T * math.cos(math.radians(S.break_deg(G_HI))) * (cz - WEB_TOP)
    s_blue = m * (bw / 2) / I
    out.append(("blue leg stress", s_blue < YIELD_304, f"{s_blue:.0f} MPa at 2x clamp ({s_blue * 0.6:.0f} at the force that just holds)"))
    lw = LEG_X1 - LEG_X0
    s_leg = n * (SCREW_Z - WEB_TOP) * (lw / 2) / (T_PL * lw ** 3 / 12)
    out.append(("nut leg stress", s_leg < YIELD_304, f"{s_leg:.0f} MPa at 2x clamp"))
    # what sticks out of the plate into the gap: head and nut, 0.75 a side; two neighbours = 1.5
    gap = D.NUT_PITCH - T_PL - 2 * N.PLATE_CLR_Y
    out.append(("head/nut in the gap", 2 * (HEAD_D - T_PL) / 2 <= gap, f"{HEAD_D - T_PL:.1f} of a {gap:.1f} gap (fingers relieved there)"))
    out.append(("tail through the gap", G_HI + 0.2 <= gap, f".080 = {G_HI:.2f} in {gap:.1f}"))
    return out


def anchor_plate():
    """The U plate, profile in XZ, 4 mm in Y (centred on the string)."""
    def box(x0, x1, z0, z1):
        return cq.Workplane("XY").box(x1 - x0, T_PL, z1 - z0, centered=(False, True, False)).translate((x0, 0, z0))
    p = box(LEG_X0, BLUE_X1, PLATE_BOT, S.ZB_TOP)
    p = p.cut(box(LEG_X1, S.XB_FACE, WEB_TOP, S.ZB_TOP + 1))                 # the window
    p = p.cut(box(LEG_X0 - 1, LEG_X1, LEG_TOP, S.ZB_TOP + 1))                # nut leg is lower
    p = p.cut(box(LEG_X0 - 1, LEG_X1 + 0.1, SCREW_Z - SLOT_W / 2, SCREW_Z + SLOT_W / 2))   # screw slot
    p = p.cut(box(NUT_X0, NUT_X1, SCREW_Z - (NUT_S + 0.1) / 2, SCREW_Z + (NUT_S + 0.1) / 2))  # nut window
    p = p.cut(cq.Workplane("XZ").center(*ROD_C).circle(ROD_HOLE / 2).extrude(T_PL, both=True))
    p = p.edges("|Y").edges(cq.selectors.NearestToPointSelector((S.XB_FACE, 0, S.ZB_TOP))).fillet(S.RB)
    return p


def pad_plate():
    return cq.Workplane("XY").box(PAD_D, T_PL, PAD_H, centered=(False, True, False)).translate(
        (S.XB_FACE - G_HI - PAD_D, 0, WEB_TOP))


def draw(path="nut_inplane_study.png"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle, Arc, Polygon
    BG, W, Gc, B, O, S_, Dc = "#36383d", "#e5e5e5", "#39ff14", "#00b4d8", "#ff6b00", "#9a9a9a", "#c77dff"
    fig, ax = plt.subplots(figsize=(11, 13)); fig.patch.set_facecolor(BG); ax.set_facecolor(BG)
    # anchor plate outline from the solid's mid-plane section
    sec = anchor_plate().section(0).val() if False else None
    solid = anchor_plate().val()
    face = cq.Workplane("XZ").add(solid).section().val() if False else None
    sl = solid.intersect(cq.Solid.makeBox(200, 0.01, 200, cq.Vector(-100, -0.005, -100)))
    for e in sl.Edges():
        if abs(e.Center().y) < 1e-3 or True:
            pts = [e.positionAt(t) for t in [i / 24 for i in range(25)]]
            ax.plot([p.x for p in pts], [p.z for p in pts], color=B, lw=1.6)
    # pad
    pd = (S.XB_FACE - G_HI - PAD_D, WEB_TOP)
    ax.add_patch(Rectangle(pd, PAD_D, PAD_H, fc="none", ec=O, lw=2.2))
    # screw + nut
    tip = S.XB_FACE - G_HI - PAD_D
    ax.add_patch(Rectangle((tip - SCREW_L, SCREW_Z - 1.5), SCREW_L, 3.0, fc=S_, ec=S_, alpha=0.9))
    ax.add_patch(Rectangle((tip - SCREW_L - HEAD_H, SCREW_Z - HEAD_D / 2), HEAD_H, HEAD_D, fc=S_, ec=S_))
    ax.add_patch(Rectangle((NUT_X0 + 0.05, SCREW_Z - NUT_S / 2), NUT_M, NUT_S, fc="#777", ec="#ccc", lw=0.8))
    # rod
    ax.add_patch(Circle(ROD_C, D.BRIDGE_AXLE_D / 2, fc="#666", ec="#ccc"))
    # green (schematic): crown arm, body down to the datum ledge
    gx0, gx1 = BLUE_X1 + 0.6, N.PLATE_X1
    zl = -66.0                                   # the ledge, near the endplate bottom (~-73.5)
    arc = [(N.DOWEL_X + 2 * math.cos(math.radians(a)), -G_LO - 2 + 2 * math.sin(math.radians(a))) for a in range(0, 181, 15)]
    green = [(gx1, zl - 8), (gx1, -2 - G_LO)] + arc + [(N.DOWEL_X - 2, -9.0), (gx0, -9.0), (gx0, zl + 3), (gx0 - 6, zl + 3),
                                                       (gx0 - 6, zl), (gx0 - 1, zl), (gx0 - 1, zl - 8)]
    ax.add_patch(Polygon(green, closed=True, fc="none", ec=Gc, lw=2.2))
    ax.add_patch(Rectangle((gx0 - 8, zl + 0.5), 7.5, 4.0, fc="none", ec=Dc, lw=2.0))
    ax.text(gx0 - 8, zl + 5.2, "DATUM edge (common, down-facing)\nU snippet on green's ledge", color=Dc, fontsize=8)
    # strings
    for g, col in ((G_LO, W), (G_HI, "#bbbbbb")):
        p1, p2 = S.tangent_points(g)
        ax.plot([N.DOWEL_X + 30, N.DOWEL_X], [-g / 2, -g / 2], color=col, lw=1.5)
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=col, lw=1.5)
        cx, cz = S.corner_c()
        ax.add_patch(Arc((cx, cz), 2 * (S.RB + g / 2), 2 * (S.RB + g / 2), theta1=90 + S.break_deg(g), theta2=180, color=col, lw=1.5))
        ax.plot([S.XB_FACE - g / 2] * 2, [cz, WEB_TOP], color=col, lw=1.5)
    ax.annotate("tail leaves sideways\ninto the gap", (S.XB_FACE - 1, WEB_TOP), (S.XB_FACE + 3, WEB_TOP - 12), color=W, fontsize=8,
                arrowprops=dict(arrowstyle="->", color=W))
    ax.plot([X_BACK, X_BACK], [5, -70], color="#888", ls="--", lw=1)
    ax.text(X_BACK + 0.3, 2, "-X face (today)", color="#888", fontsize=8)
    ax.add_patch(Circle((N.DOWEL_X, N.BAR_R), N.BAR_R, fc="none", ec="#888", ls=":", lw=1))
    ax.text(-25.5, -4, "ANCHOR plate (304, 4 mm, laser)", color=B, fontsize=9)
    ax.text(pd[0], WEB_TOP + PAD_H + 0.6, "ORANGE pad", color=O, fontsize=8)
    ax.text(-34, SCREW_Z + 4, "M3x10 + square nut", color=S_, fontsize=8)
    ax.text(ROD_C[0] - 5, ROD_C[1] - 7, "Ø8 axle shaft (v2's rod)", color="#ccc", fontsize=8)
    ax.text(gx1 + 0.5, -25, "GREEN crown plate\nmoves in Z only", color=Gc, fontsize=8)
    ax.set_xlim(-37, 30); ax.set_ylim(-80, 27); ax.set_aspect("equal")
    ax.tick_params(colors="#999"); [s.set_color("#666") for s in ax.spines.values()]
    ax.set_title("Nut clamp proposal: per-string laser plates, to scale (mm)", color="w")
    plt.savefig(path, dpi=130, facecolor=BG, bbox_inches="tight")


if __name__ == "__main__":
    for name, ok, val in checks():
        print(f"  [{'OK' if ok else 'FAIL'}] {name}: {val}")
    os.makedirs("quotes", exist_ok=True)
    a, p = anchor_plate(), pad_plate()
    cq.exporters.export(a, "quotes/nut_anchor_plate.step")
    cq.exporters.export(p, "quotes/nut_clamp_pad.step")
    bb = a.val().BoundingBox()
    print(f"  anchor plate {bb.xlen:.1f} x {bb.zlen:.1f} x {bb.ylen:.1f}; pad {PAD_D} x {PAD_H} x {T_PL}")
    draw()
    print("  wrote nut_inplane_study.png, quotes/nut_anchor_plate.step, quotes/nut_clamp_pad.step")
