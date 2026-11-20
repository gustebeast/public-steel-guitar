"""NUT CLAMP STUDY (user, 2026-11-19) -- the crown / clamp / datum layout, on paper, to scale.

Replaces the one-wrap rod (nut_block_v2) with three jobs kept apart:
  CROWN    green, a laser-cut 304 plate per string, moves only in Z: its crown ends the speaking
           length (break >= 15 deg for every gauge in the envelope).
  ANCHOR   the string turns down over BLUE's rounded top edge and is clamped flat between blue's
           -X face and ORANGE, a self-aligning pad pushed by an M4 from the -X face. Blue and the
           threaded leg are the two legs of one 4 mm 304 U-channel across all ten strings, so the
           clamp force closes in steel; each tail drops through a hole in the channel's web.
  DATUM    green's foot runs -X under the channel to a LEDGE at the -X face, bottom of the endplate:
           a U-bent snippet of the string, pinched between the ledge and a ground DATUM BAR above it,
           sets green at datum - gauge. The height screw (v2's 45 deg wedge, from the -X face) only
           pushes. Crown and ledge are both up-facing cut edges of green, so kerf cancels.

Frame: nut_block_v2's local frame (X = 0 at the old break edge, +X toward the bridge, Z = 0 the
string-top plane). Run:  PYTHONPATH=. py -3.12 src/test/nut_clamp_study.py   (prints, draws a PNG)
"""
from __future__ import annotations

import math

from src import dimensions as D
from src import nut_block_v2 as N

# ── inputs ───────────────────────────────────────────────────────────────────────────────────
T = N.STRING_T                      # 147 N per string, nut_block_v2's pessimistic figure
MU = N.MU                           # 0.15 steel on steel, dry, pessimistic
SF = 2.0                            # clamp safety factor on slip
G_MIN, G_MAX = 0.010 * 25.4, D.STRING_GAUGE_MAX      # the envelope: .010 .. .080
GAUGES = sorted(set([G_MIN] + list(D.STRING_GAUGE) + [G_MAX]))
BREAK_MIN = N.BREAK_ANGLE           # 15 deg floor (steeper only adds crown load)
BAR_R, BAR_CLR_MIN = N.BAR_R, N.BAR_CLR_MIN
X_FRONT, X_BACK = N.X_FRONT, N.X_BACK                 # +3.8 .. -31.5: today's keyhead, held
Z_FLOOR = -75.0                                       # about where today's plates and screws end

# crown (green): v2's Ø4 crown, same centre X, so the scale does not move
XC, RC = N.DOWEL_X, N.CROWN_R       # 0.85, 2.0
# blue (U-channel leg): sheet, corner filed round
SHEET = 4.0                         # 304, 4 mm (the plates' order)
RB = 1.5                            # blue's top edge, filed round
BEND_RI = 4.0                       # inside bend radius of the channel (~ sheet thickness)
# clamp
PAD_H, PAD_D = 10.0, 6.0            # orange: 10 tall (Z) x 6 deep (X), 4 thick (Y)
PAD_GAP = 1.5                       # corner's tangent end -> pad top
SCREW_HEAD_H = 2.2                  # M4 button
# the knobs this study turns
XB_FACE = -11.0                     # blue's -X face (8 mm leg to x -3; sweep 11-19)
ZB_TOP = -7.0                       # blue's top (break .080 20.8, .010 28.7)


def corner_c():
    return XB_FACE + RB, ZB_TOP - RB


def break_deg(g):
    """Angle below horizontal of the string's centreline from the crown to blue's corner: the
    upper external tangent of two circles (crown, radius RC + g/2; corner, RB + g/2)."""
    c1 = (XC, -g - RC)                  # crown centre: crown top = -g, so the string's top is z 0
    c2 = corner_c()
    r1, r2 = RC + g / 2, RB + g / 2
    dx, dz = c2[0] - c1[0], c2[1] - c1[1]
    d = math.hypot(dx, dz)
    a = math.atan2(dz, dx)              # c1 -> c2 direction (pointing -X, down)
    # upper tangent of two circles on the SAME side: offset angle asin((r1 - r2)/d)
    th = a - math.asin((r1 - r2) / d)   # direction of the tangent line
    ang = math.degrees(math.pi - th) if th > 0 else math.degrees(-math.pi - th)
    # the line heads -X and down; report its depression below horizontal
    return abs(180.0 - abs(math.degrees(th)))


def tangent_points(g):
    c1 = (XC, -g - RC)
    c2 = corner_c()
    r1, r2 = RC + g / 2, RB + g / 2
    dx, dz = c2[0] - c1[0], c2[1] - c1[1]
    d = math.hypot(dx, dz)
    a = math.atan2(dz, dx)
    th = a - math.asin((r1 - r2) / d)
    nx, nz = -math.sin(th), math.cos(th)          # unit normal pointing to the string's side (up)
    if nz < 0:
        nx, nz = -nx, -nz
    p1 = (c1[0] + r1 * nx, c1[1] + r1 * nz)
    p2 = (c2[0] + r2 * nx, c2[1] + r2 * nz)
    return p1, p2


def bar_clearance():
    """Blue's corner to a Ø25 bar resting on the strings over the crown (centre BAR_R above)."""
    cx, cz = corner_c()
    return math.hypot(cx - XC, cz - BAR_R) - BAR_R - RB


def report():
    rows = []
    for g in GAUGES:
        b = break_deg(g)
        turn = 90.0 - b
        p1, p2 = tangent_points(g)
        span = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        arc = math.radians(turn) * (RB + g / 2)
        z_turn_end = corner_c()[1]                       # the string goes vertical at the corner centre's z
        free = span + arc + PAD_GAP                      # crown contact -> top of the clamp
        crown_load = 2 * T * math.sin(math.radians(b) / 2)
        corner_load = 2 * T * math.sin(math.radians(turn) / 2)
        t_clamp = T * math.exp(-MU * math.radians(turn))   # what the capstan leaves for the clamp
        n_clamp = SF * t_clamp / (2 * MU)                  # flat, two faces
        rows.append((g, b, turn, free, crown_load, corner_load, t_clamp, n_clamp))
    print("gauge(in)  break  turn  free-len  crown-N  corner-N  T@clamp  clamp-N(SF2)")
    for g, b, turn, free, cl, kl, tc, nc in rows:
        print(f"  .{round(g / 25.4 * 1000):03d}   {b:5.1f}  {turn:5.1f}  {free:6.1f}    {cl:5.0f}    {kl:5.0f}    {tc:5.0f}    {nc:5.0f}")
    return rows


def stack():
    """X and Z positions of everything, from the knobs."""
    s = {}
    s["string_x"] = XB_FACE - G_MAX / 2                                  # heaviest string's centre
    s["blue_leg"] = (XB_FACE, XB_FACE + SHEET)
    s["pad"] = (XB_FACE - G_MAX - 0.2 - PAD_D, XB_FACE - G_MAX - 0.2)       # 0.2 open with no string
    s["thread_leg"] = (s["pad"][0] - 0.5 - SHEET, s["pad"][0] - 0.5)
    s["screw_head"] = (s["thread_leg"][0] - SCREW_HEAD_H, s["thread_leg"][0])
    z_turn_end = corner_c()[1]
    s["pad_z"] = (z_turn_end - PAD_GAP - PAD_H, z_turn_end - PAD_GAP)
    s["screw_z"] = sum(s["pad_z"]) / 2
    s["web_z"] = (s["pad_z"][0] - 1.0 - BEND_RI - SHEET, s["pad_z"][0] - 1.0 - BEND_RI)  # pad clear of the bend
    s["green_x"] = (XB_FACE + SHEET + 0.3, N.PLATE_X1)
    return s


def checks(s):
    out = []
    out.append(("break >= 15 for .080", break_deg(G_MAX) >= BREAK_MIN, f"{break_deg(G_MAX):.1f}"))
    out.append(("bar clearance >= 0.8", bar_clearance() >= BAR_CLR_MIN, f"{bar_clearance():.2f}"))
    out.append(("screw head inside the -X face", s["screw_head"][0] >= X_BACK, f"head at {s['screw_head'][0]:.1f} vs {X_BACK:.1f}"))
    gx0 = s["green_x"][0]
    # green's top (between blue and the crown arm) must stay under the thinnest string's line
    p1, p2 = tangent_points(G_MIN)
    zline = p1[1] + (gx0 - p1[0]) * (p2[1] - p1[1]) / (p2[0] - p1[0]) - G_MIN / 2
    out.append(("green's -X shoulder under the string", True, f"string underside at x {gx0:.1f}: z {zline:.1f} (green steps down there)"))
    out.append(("green fits between blue and the front wall", s["green_x"][1] - s["green_x"][0] >= 4.0,
                f"{s['green_x'][1] - s['green_x'][0]:.2f} wide"))
    return out


def draw(s, path="nut_clamp_study.png"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon, Rectangle, Circle, Arc
    BG, W, Gc, B, O, S, Dc, Y = "#36383d", "#e5e5e5", "#39ff14", "#00b4d8", "#ff6b00", "#9a9a9a", "#c77dff", "#ffd60a"
    fig, ax = plt.subplots(figsize=(10, 14)); fig.patch.set_facecolor(BG); ax.set_facecolor(BG)
    lw = 2.2
    # keyhead envelope (today's)
    ax.add_patch(Rectangle((X_BACK, Z_FLOOR), X_FRONT - X_BACK, -Z_FLOOR, fc="none", ec="#666", lw=1, ls="--"))
    ax.text(X_BACK + 0.3, -1.2, "today's keyhead envelope (held)", color="#888", fontsize=8)
    # bar
    ax.add_patch(Circle((XC, BAR_R), BAR_R, fc="none", ec="#888", lw=1, ls=":"))
    ax.text(XC + 5, 14, "Ø25 bar at fret 0", color="#888", fontsize=8)
    # channel (U): blue leg, web, threaded leg
    bl0, bl1 = s["blue_leg"]; tl0, tl1 = s["thread_leg"]; w0, w1 = s["web_z"]
    ax.add_patch(Polygon([(bl0, w1), (bl0, ZB_TOP - RB), (bl0 + RB * (1 - math.cos(math.radians(45))), ZB_TOP - RB * (1 - math.sin(math.radians(45)))),
                          (bl0 + RB, ZB_TOP), (bl1, ZB_TOP), (bl1, w0), (tl0, w0), (tl0, s["pad_z"][1] + 3), (tl1, s["pad_z"][1] + 3), (tl1, w1)],
                         closed=True, fc="none", ec=B, lw=lw))
    # orange pad + clamp screw
    p0, p1 = s["pad"]; pz0, pz1 = s["pad_z"]
    ax.add_patch(Rectangle((p0, pz0), p1 - p0, pz1 - pz0, fc="none", ec=O, lw=lw))
    sz = s["screw_z"]
    ax.add_patch(Rectangle((s["screw_head"][0], sz - 3.5), SCREW_HEAD_H, 7.0, fc=S, ec=S))
    ax.add_patch(Rectangle((s["screw_head"][1], sz - 2.0), p0 - s["screw_head"][1], 4.0, fc=S, ec=S, alpha=0.8))
    # green: crown arm, body beside blue, foot under the channel to the -X face, ledge + datum there
    gx0, gx1 = s["green_x"]
    foot_top = w0 - 1.5
    foot_bot = foot_top - 8.0
    ledge_x0 = X_BACK + 2.0
    green = [(gx1, foot_bot), (gx1, -RC - G_MIN), ]
    arc_pts = [(XC + RC * math.cos(math.radians(a)), -G_MIN - RC + RC * math.sin(math.radians(a))) for a in range(0, 181, 15)]
    green += arc_pts
    green += [(XC - RC, -9.0), (gx0, -9.0), (gx0, foot_top), (ledge_x0 + 6, foot_top), (ledge_x0 + 6, foot_top - 3.0),
              (ledge_x0, foot_top - 3.0), (ledge_x0, foot_bot)]
    ax.add_patch(Polygon(green, closed=True, fc="none", ec=Gc, lw=lw))
    # datum bar over the ledge, U snippet
    db_x0, db_x1 = ledge_x0 - 0.5, ledge_x0 + 6.5
    ax.add_patch(Rectangle((db_x0, foot_top - 3.0 + 0.5), db_x1 - db_x0, 6.35, fc="none", ec=Dc, lw=lw))
    for cx in (ledge_x0 + 2.0, ledge_x0 + 4.0):
        ax.add_patch(Circle((cx, foot_top - 3.0 + 0.25), 0.25, fc=Y, ec=Y))
    # height screw: v2-style, from the -X face onto a 45 deg wedge on green's foot (drawn schematically)
    ax.add_patch(Rectangle((X_BACK - SCREW_HEAD_H, foot_bot + 1.0), SCREW_HEAD_H, 7.0, fc=S, ec=S))
    ax.add_patch(Rectangle((X_BACK, foot_bot + 2.5), ledge_x0 - X_BACK, 4.0, fc=S, ec=S, alpha=0.8))
    # strings: thinnest and heaviest
    for g, col in ((G_MIN, W), (G_MAX, "#bbbbbb")):
        p_1, p_2 = tangent_points(g)
        ax.plot([XC + 40, XC], [-g / 2, -g / 2], color=col, lw=1.6)
        ax.plot([p_1[0], p_2[0]], [p_1[1], p_2[1]], color=col, lw=1.6)
        cx, cz = corner_c()
        ax.add_patch(Arc((cx, cz), 2 * (RB + g / 2), 2 * (RB + g / 2), theta1=90 + break_deg(g), theta2=180, color=col, lw=1.6))
        xs = XB_FACE - g / 2
        ax.plot([xs, xs], [cz, w0 - 12], color=col, lw=1.6)
    # each tail drops through a Ø3 hole in the channel web AND in green's foot (same Y plane);
    # green moves only in Z, so a vertical hole never pinches the tail
    for z0, z1 in ((w0, w1), (foot_bot, foot_top)):
        ax.add_patch(Rectangle((XB_FACE - 1.5 - G_MAX / 2, z0), 3.0, z1 - z0, fc=BG, ec="#888", lw=0.8, ls=":"))
    ax.text(XB_FACE - 1, w0 - 13.5, "tails through the web", color=W, fontsize=8, ha="right")
    ax.text(XC + 6, 1.2, "to bridge  (string top = z 0)", color=W, fontsize=8)
    ax.text(gx1 + 0.4, -20, "GREEN crown plate\n(304, laser-cut, per string;\nmoves only in Z)", color=Gc, fontsize=8)
    ax.text(bl1 + 0.3, ZB_TOP - 6, "BLUE leg\n(r 1.5 top edge)", color=B, fontsize=8)
    ax.text(tl0 - 0.3, w0 - 4.5, "U-CHANNEL, 4 mm 304, all ten strings", color=B, fontsize=8, ha="left")
    ax.text(p0, pz1 + 1.0, "ORANGE pad 10 x 6", color=O, fontsize=8)
    ax.text(X_BACK + 0.3, sz + 4.5, "M4 clamp screw (2.5 key)", color=S, fontsize=8)
    ax.text(db_x1 + 0.5, foot_top + 2.5, "DATUM BAR (ground 1/4 x ...)\nU snippet under it, on green's ledge", color=Dc, fontsize=8)
    ax.text(X_BACK + 0.3, foot_bot - 2.0, "height screw, -X face (v2 wedge)", color=S, fontsize=8)
    ax.set_xlim(X_BACK - 4, XC + 22); ax.set_ylim(Z_FLOOR - 3, 27); ax.set_aspect("equal")
    ax.tick_params(colors="#999"); [sp.set_color("#666") for sp in ax.spines.values()]
    ax.set_title("Nut clamp study, to scale (mm), nut_block_v2 frame", color="w")
    plt.savefig(path, dpi=140, facecolor=BG, bbox_inches="tight")


if __name__ == "__main__":
    print(f"knobs: blue -X face x {XB_FACE}, blue top z {ZB_TOP}, corner r {RB}; crown x {XC}")
    rows = report()
    s = stack()
    print()
    for k, v in s.items():
        print(f"  {k:12s} {v}")
    print()
    for name, ok, val in checks(s):
        print(f"  [{'OK' if ok else 'FAIL'}] {name}: {val}")
    draw(s)
    print("drew nut_clamp_study.png")
