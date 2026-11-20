"""NUT CLAMP, WEDGE-PAD VERSION (2026-11-19). Supersedes nut_inplane_study's -X screw: a slot cut in
the plate's own plane from its -X edge into the string window would cut the plate in two (the window
already opens to the outside, where the string comes in). A screw in a plate's plane can only act
on an EDGE. So:

  ANCHOR  per string, 304, 4 mm, laser. Its +X leg is BLUE (string turns down over the laser-cut
          r1.5 corner, runs down its -X edge). Its back leg carries a SLOPE (ALPHA from vertical,
          wider at the top) and, above it, a closed slot the LID passes through.
  PAD     per string, 304, 4 mm, laser: the WEDGE itself (user). Vertical +X face on the string,
          sloped -X face on the anchor's slope, an M3 square nut in a closed pocket reached by a
          slot from its top edge (a slot from an edge into a closed pocket cuts nothing free).
          Pulled UP, it rides the slope +X onto the string. The string's own pull on it is upward
          too, so it tightens the wedge rather than loosening it.
  LID     ONE plate for all ten strings, 304, laser, lying flat (XY). Threads through the closed
          slots in all ten anchors, like the axle. Ten slotted holes (the pad moves ~2.3 mm in X
          with gauge). The screw's head bears on it.
  SCREW   M3 cap (2.5 key), from ABOVE, through the lid, into the pad's nut. Head behind the nut,
          clear of the strings and the bar.

Every clamp load stays in steel: pad -> string -> blue -> anchor floor -> back leg slope -> pad;
the screw's pull: pad nut -> screw -> lid -> anchor slot.

Run:  PYTHONPATH=. py -3.12 src/test/nut_wedge_study.py
"""
from __future__ import annotations

import math
import os

import cadquery as cq

from src import dimensions as D
from src import nut_block_v2 as N
from src.test import nut_clamp_study as S

# ── knobs ───────────────────────────────────────────────────────────────────────────────────
T_PL = 4.0
S.XB_FACE, S.ZB_TOP, S.RB = -13.0, -8.0, 1.5
BLUE_X1 = -3.3                                   # green from -2.7
ALPHA = 30.0                                     # slope, from vertical
TA = math.tan(math.radians(ALPHA))
G_LO, G_HI = 0.010 * 25.4, D.STRING_GAUGE_MAX
OPEN = 0.5                                       # extra opening to thread the heaviest string
PAD_H, SLOPE_H = 10.0, 7.0                       # pad height; the sloped band at its foot (>= 3 mm contact + travel)
PAD_WT = 8.2                                     # pad width above the slope
PAD_WB = PAD_WT + SLOPE_H * TA
SC = 4.1                                         # screw axis, from the pad's +X face (lid is a comb: no end wall)
SLOT_W, NUT_S, NUT_M = 3.4, 5.5, 1.8
LID_T = 6.0
WASHER = 0.5                                     # ISO 7089 M3 under the head (spreads it on the slot)
CLR = 0.3
X_BACK = N.X_BACK

T, MU, SF = N.STRING_T, N.MU, 2.0
YIELD = 205.0
PROOF_M3 = 2260.0

# ── derived positions ───────────────────────────────────────────────────────────────────────
X_F = lambda g: S.XB_FACE - g                                   # pad +X face, clamped
Z_TOP_THIN = S.corner_c()[1] - 1.0                              # pad top, thinnest string, clamped
Z_B = lambda xf: (Z_TOP_THIN - PAD_H) - (X_F(G_LO) - xf) / TA   # pad bottom: lower as it sits -X
XF_OPEN = X_F(G_HI) - OPEN
ZB_THIN, ZB_OPEN = Z_B(X_F(G_LO)), Z_B(XF_OPEN)
FLOOR = ZB_OPEN - 0.6
# slope line on the anchor: through the pad's foot corner when clamped on the thinnest string
SL_P = (X_F(G_LO) - PAD_WB, ZB_THIN)
x_slope = lambda z: SL_P[0] + (z - SL_P[1]) * TA
LID_Z0 = Z_TOP_THIN + 0.5
LID_Z1 = LID_Z0 + LID_T
LEG_FACE = XF_OPEN - PAD_WT - CLR                               # back leg's vertical face, above the slope
SCREW_X = lambda xf: xf - SC
LEG_X0 = min(X_BACK, SL_P[0] - (SL_P[1] - FLOOR) * TA - 3.38)
LID_X0 = LEG_X0 + 3.0                           # 3 mm wall closes the lid slot at -X: it carries the lid's heel (~560 N up)
# pad's nut pocket: nut pulled up against the pocket's top; room below for the tip
SCREW_L = 16.0
POCKET_TOP_V, POCKET_BOT_V = 8.0, 0.8
def nut_top(zb):            # z of the pocket's top land
    return zb + POCKET_TOP_V


def string_min_x(z0, z1, g=G_HI):
    """-X-most point of the string (surface) in a Z band, over blue's corner."""
    cx, cz = S.corner_c()
    r = S.RB + g
    xs = []
    for i in range(41):
        z = z0 + (z1 - z0) * i / 40
        if z <= cz:
            xs.append(S.XB_FACE - g)
        elif z < cz + r * math.cos(math.radians(S.break_deg(g))):
            xs.append(cx - math.sqrt(r * r - (z - cz) ** 2))
        else:                                       # on the straight run to the crown
            p1, p2 = S.tangent_points(g)
            xs.append(p2[0] + (z - p2[1]) * (p1[0] - p2[0]) / (p1[1] - p2[1]) - g / 2)
    return min(xs) if xs else 0.0


def checks():
    out = []
    bh, bl = S.break_deg(G_HI), S.break_deg(G_LO)
    out.append(("break >= 15", bh >= 15, f".080 {bh:.1f}, .010 {bl:.1f} deg; bar clearance {S.bar_clearance():.1f}"))
    turn = math.radians(90 - bh)
    n = SF * T * math.exp(-MU * turn) / (2 * MU)
    f = n * (TA + 2 * MU)
    out.append(("screw pull", f < PROOF_M3 / 2, f"clamp {n:.0f} N needs {f:.0f} N of screw (M3 A2-70 proof {PROOF_M3:.0f}); ~{0.2 * f * 3 / 1000:.2f} N.m"))
    out.append(("pad travel", True, f"{X_F(G_LO) - XF_OPEN:.2f} mm in X = {(X_F(G_LO) - XF_OPEN) / TA:.2f} mm up the slope"))
    # blue leg, in-plane cantilever from the window floor
    bw = BLUE_X1 - S.XB_FACE
    I = T_PL * bw ** 3 / 12
    zc = ZB_THIN + PAD_H / 2
    m = n * (zc - FLOOR) + T * (S.corner_c()[1] - FLOOR)
    sb = m * (bw / 2) / I
    out.append(("blue leg", sb < YIELD, f"{sb:.0f} MPa at the {n:.0f} N clamp (yield {YIELD:.0f})"))
    # lid: cantilever off the back leg's face to the screw, one lane wide
    lev = SCREW_X(X_F(G_LO)) - LEG_FACE
    sl = f * lev * (LID_T / 2) / (D.NUT_PITCH * LID_T ** 3 / 12)
    out.append(("lid", sl < YIELD, f"{sl:.0f} MPa ({LID_T} mm plate, lever {lev:.1f})"))
    # the comb's notch puts the washer at the lane centre, where the string is: clear it above the lid
    smin = string_min_x(LID_Z1, LID_Z1 + WASHER + 3.0)
    wash_end = SCREW_X(X_F(G_LO)) + 3.5
    out.append(("washer + head clear of the string", wash_end <= smin - 0.4, f"washer to x {wash_end:.2f}, string at {smin:.2f}"))
    sh = string_min_x(LID_Z0, LID_Z1)
    out.append(("shank clear of the .080", SCREW_X(X_F(G_LO)) + 1.5 <= sh - 0.4, f"shank to x {SCREW_X(X_F(G_LO)) + 1.5:.2f}, string at {sh:.2f}"))
    # comb tine root: notch root to the washer's centre at its furthest
    root = SCREW_X(XF_OPEN) - SLOT_W / 2
    st = f * (SCREW_X(X_F(G_LO)) - root) * (LID_T / 2) / ((D.NUT_PITCH - SLOT_W) * LID_T ** 3 / 12)
    out.append(("lid tines", st < YIELD, f"{st:.0f} MPa at the notch root"))
    # screw length: tip inside the pocket, nut fully engaged, both ends of travel
    for name, zb in (("thinnest, clamped", ZB_THIN), (".080, open", ZB_OPEN)):
        top = nut_top(zb)
        tip = LID_Z1 + WASHER - SCREW_L
        ok = (tip <= top - NUT_M - 0.3) and (tip >= zb + POCKET_BOT_V)
        out.append((f"M3x{SCREW_L:.0f} at {name}", ok, f"nut {top - NUT_M:.2f}..{top:.2f}, tip {tip:.2f}, pocket floor {zb + POCKET_BOT_V:.2f}"))
    out.append(("inside the -X face", LEG_X0 >= X_BACK - 0.01, f"anchor from x {LEG_X0:.2f} (face {X_BACK})"))
    out.append(("tail through the gap", True, f".080 {G_HI:.2f} in {D.NUT_PITCH - T_PL - 2 * N.PLATE_CLR_Y:.1f} (.070 easy)"))
    return out


def _box(x0, x1, z0, z1, t=T_PL):
    return cq.Workplane("XY").box(x1 - x0, t, z1 - z0, centered=(False, True, False)).translate((x0, 0, z0))


def _poly(pts, t=T_PL):
    return cq.Workplane("XZ").polyline(pts).close().extrude(t / 2, both=True)


def anchor_plate():
    top = -2.0
    z_sl_top = ZB_OPEN + SLOPE_H              # never above the pad's band top, even at its lowest
    outline = [(LEG_X0, -40.0 + 0), (BLUE_X1, -40.0), (BLUE_X1, S.ZB_TOP), (S.XB_FACE, S.ZB_TOP),
               (S.XB_FACE, FLOOR), (x_slope(FLOOR), FLOOR), (x_slope(z_sl_top), z_sl_top),
               (LEG_FACE, z_sl_top), (LEG_FACE, top), (LEG_X0, top)]
    zbot = FLOOR - 13.0
    outline[0] = (LEG_X0, zbot); outline[1] = (BLUE_X1, zbot)
    p = _poly(outline)
    p = p.cut(_box(LID_X0, LEG_FACE + 1, LID_Z0 - 0.1, LID_Z1 + 0.1))           # lid slot (opens to the window)
    rod = (LEG_X0 + 8.0, FLOOR - 6.5)
    p = p.cut(cq.Workplane("XZ").center(*rod).circle((D.BRIDGE_AXLE_D + 0.4) / 2).extrude(T_PL, both=True))
    p = p.edges("|Y").edges(cq.selectors.NearestToPointSelector((S.XB_FACE, 0, S.ZB_TOP))).fillet(S.RB)
    return p, rod


def pad_plate(xf, zb):
    pts = [(xf, zb), (xf, zb + PAD_H), (xf - PAD_WT, zb + PAD_H), (xf - PAD_WT, zb + SLOPE_H), (xf - PAD_WB, zb)]
    p = _poly(pts)
    sx = xf - SC
    p = p.cut(_box(sx - SLOT_W / 2, sx + SLOT_W / 2, zb + POCKET_TOP_V, zb + PAD_H + 1))       # slot from the top edge
    p = p.cut(_box(sx - (NUT_S + 0.2) / 2, sx + (NUT_S + 0.2) / 2, zb + POCKET_BOT_V, zb + POCKET_TOP_V))  # nut + tip room
    return p


def lid_plate():
    """Flat, XY, one per instrument: a COMB. A notch open to +X at every string; the screw sits in it,
    the washer bears on the tines either side. Its solid back threads through all ten anchors."""
    y0 = -(D.N_STRINGS - 1) / 2 * D.NUT_PITCH
    span = (D.N_STRINGS - 1) * D.NUT_PITCH + 2 * 6.0
    x1 = SCREW_X(X_F(G_LO)) + 3.5
    lid = cq.Workplane("XY").box(x1 - LID_X0, span, LID_T, centered=(False, True, False)).translate((LID_X0, 0, LID_Z0))
    root = SCREW_X(XF_OPEN) - SLOT_W / 2
    for i in range(D.N_STRINGS):
        y = y0 + i * D.NUT_PITCH
        lid = lid.cut(cq.Workplane("XY").box(x1 - root + 1, SLOT_W, LID_T + 2, centered=(False, True, False))
                      .translate((root, y, LID_Z0 - 1)).edges("|Z").fillet(SLOT_W / 2 - 0.01))
    return lid


def draw(path="nut_wedge_study.png"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle, Arc
    BG, W, Gc, B, O, S_, L = "#36383d", "#e5e5e5", "#39ff14", "#00b4d8", "#ff6b00", "#9a9a9a", "#ffd60a"

    def outline(ax, solid, col, lw=1.8, ls="-"):
        cut = solid.val().intersect(cq.Solid.makeBox(300, 0.02, 300, cq.Vector(-150, -0.01, -150)))
        for e in cut.Edges():
            pts = [e.positionAt(t / 24) for t in range(25)]
            ax.plot([q.x for q in pts], [q.z for q in pts], color=col, lw=lw, ls=ls)

    fig, axs = plt.subplots(1, 2, figsize=(16, 11), gridspec_kw=dict(width_ratios=[1, 1]))
    fig.patch.set_facecolor(BG)
    a, rod = anchor_plate()
    for ax, g, xf, zb, title in ((axs[0], G_LO, X_F(G_LO), ZB_THIN, ".010, clamped"),
                                 (axs[1], G_HI, XF_OPEN, ZB_OPEN, ".080, open to thread")):
        ax.set_facecolor(BG)
        outline(ax, a, B)
        outline(ax, pad_plate(xf, zb), O, 2.2)
        lid = cq.Workplane("XY").box(SCREW_X(XF_OPEN) - SLOT_W / 2 - LID_X0, 0.02, LID_T, centered=(False, True, False)).translate((LID_X0, 0, LID_Z0))
        outline(ax, lid, L, 2.0)
        sx = SCREW_X(xf)
        ax.add_patch(Rectangle((sx - 1.5, LID_Z1 + WASHER - SCREW_L), 3.0, SCREW_L, fc=S_, ec=S_, alpha=0.9))
        ax.add_patch(Rectangle((sx - 2.75, LID_Z1 + WASHER), 5.5, 3.0, fc=S_, ec=S_))
        nt = nut_top(zb)
        ax.add_patch(Rectangle((sx - NUT_S / 2, nt - NUT_M), NUT_S, NUT_M, fc="#777", ec="#ddd", lw=0.8))
        ax.add_patch(Circle(rod, D.BRIDGE_AXLE_D / 2, fc="#666", ec="#ccc"))
        p1, p2 = S.tangent_points(g)
        ax.plot([N.DOWEL_X + 25, N.DOWEL_X], [-g / 2] * 2, color=W, lw=1.5)
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=W, lw=1.5)
        cx, cz = S.corner_c()
        ax.add_patch(Arc((cx, cz), 2 * (S.RB + g / 2), 2 * (S.RB + g / 2), theta1=90 + S.break_deg(g), theta2=180, color=W, lw=1.5))
        ax.plot([S.XB_FACE - g / 2] * 2, [cz, FLOOR], color=W, lw=1.5)
        # green crown plate (its top only)
        arc = [(N.DOWEL_X + 2 * math.cos(math.radians(t)), -g - 2 + 2 * math.sin(math.radians(t))) for t in range(0, 181, 15)]
        gx = [N.PLATE_X1] + [q[0] for q in arc] + [N.DOWEL_X - 2, BLUE_X1 + 0.6, BLUE_X1 + 0.6, N.PLATE_X1]
        gz = [-g - 2] + [q[1] for q in arc] + [-9.0, -9.0, FLOOR - 13, FLOOR - 13]
        ax.plot(gx + [gx[0]], gz + [gz[0]], color=Gc, lw=1.8)
        ax.plot([X_BACK] * 2, [3, FLOOR - 15], color="#888", ls="--", lw=1)
        ax.add_patch(Circle((N.DOWEL_X, N.BAR_R), N.BAR_R, fc="none", ec="#777", ls=":"))
        ax.set_title(title, color="w")
        ax.set_xlim(-36, 12); ax.set_ylim(FLOOR - 16, 12); ax.set_aspect("equal")
        ax.tick_params(colors="#999"); [s.set_color("#666") for s in ax.spines.values()]
    axs[0].text(-35, 9, "ANCHOR (blue)  PAD = wedge (orange)  LID, one for all ten (yellow)\nM3 from above into the pad's square nut; GREEN = crown plate",
                color=W, fontsize=9)
    fig.suptitle("Nut clamp, wedge-pad version, one string's plane, to scale (mm)", color="w")
    plt.savefig(path, dpi=120, facecolor=BG, bbox_inches="tight")


if __name__ == "__main__":
    for name, ok, val in checks():
        print(f"  [{'OK' if ok else 'FAIL'}] {name}: {val}")
    os.makedirs("quotes", exist_ok=True)
    a, _ = anchor_plate()
    cq.exporters.export(a, "quotes/nut_anchor_plate.step")
    cq.exporters.export(pad_plate(X_F(G_LO), ZB_THIN), "quotes/nut_clamp_pad.step")
    cq.exporters.export(lid_plate(), "quotes/nut_clamp_lid.step")
    for nm, sh in (("anchor", a), ("pad", pad_plate(X_F(G_LO), ZB_THIN)), ("lid", lid_plate())):
        bb = sh.val().BoundingBox(); print(f"  {nm}: {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f}, {len(sh.val().Solids())} piece(s)")
    draw()
    print("  wrote nut_wedge_study.png and quotes/*.step")
