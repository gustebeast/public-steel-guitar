"""LEADER CABLE STUDY (user, 2026-11-19): replace the string's ball in the yoke's keyhole with a short
steel LEADER that lives in the instrument. The leader's barrel sits in the keyhole plate (seated once,
at assembly); the leader runs +X along the screw axis, wraps the bend bearing (it, not the string,
lives on that bearing) and rises on the string's drop line to a LINK -- a laser-cut 304 plate in the
lane's plane with one window: the string's ball seats under the top slit, the leader's end fitting on
the bottom slit. The string leaves the link straight up along Z to the bridge bearing.

The question here: does the link fit on the drop line between the bearings, over the whole travel,
for every row?

    PYTHONPATH=. py -3.12 src/test/leader_study.py
"""
from __future__ import annotations

import math
import os

import cadquery as cq

from src import dimensions as D
from src import direct_bench as B

# ── the parts (TO MEASURE: the leader's barrel) ─────────────────────────────────────────────
CABLE_D = 1.2                    # bicycle shift inner cable (1.1-1.2)
NIP_D, NIP_L = 4.0, 4.5          # its barrel end, ~Ø4 x 4.5 (coaxial) -- measure one
BALL_D, BALL_L = D.STRING_NUT_D, D.STRING_NUT_L       # Ø4 x 3, measured
T_LINK = 4.0                     # plate, Y (the lane is 2 x LANE_HW = 5.2 wide)
TINE = 1.2                       # metal over the ball / under the barrel
WALL = 0.8                       # beside the window
WIN_W = max(BALL_D, NIP_D) + 0.4
WIN_H = BALL_L + NIP_L + 0.8     # both fit at once, each slides in on its own
SLIT_TOP = 2.7                   # the .080's swollen neck (~2.45) passes; Ø4 never
SLIT_BOT = 2.0                   # the leader (1.2); the barrel never
CHAMF = 1.0                      # the link's four corners
LINK_W = WIN_W + 2 * WALL
LINK_H = WIN_H + 2 * TINE
CLR = 0.5                        # off a bearing's rim

TRAVEL = B.T_TRAVEL              # 15.6: the nut's whole run; the link rides it 1:1


def link_outline():
    """(x, z) corners, string axis at x = 0, link bottom at z = 0."""
    hw, h, c = LINK_W / 2, LINK_H, CHAMF
    return [(-hw + c, 0), (hw - c, 0), (hw, c), (hw, h - c), (hw - c, h), (-hw + c, h), (-hw, h - c), (-hw, c)]


def link_solid():
    pts = link_outline()
    w = cq.Workplane("XZ").polyline(pts).close().extrude(T_LINK / 2, both=True)
    w = w.cut(cq.Workplane("XY").box(WIN_W, T_LINK + 2, WIN_H).translate((0, 0, TINE + WIN_H / 2)))
    w = w.cut(cq.Workplane("XY").box(SLIT_TOP, T_LINK + 2, TINE + 2).translate((0, 0, LINK_H - TINE / 2)))
    w = w.cut(cq.Workplane("XY").box(SLIT_BOT, T_LINK + 2, TINE + 2).translate((0, 0, TINE / 2)))
    return w


def _edge_pts(pts, n=40):
    out = []
    for (x0, z0), (x1, z1) in zip(pts, pts[1:] + pts[:1]):
        out += [(x0 + (x1 - x0) * k / n, z0 + (z1 - z0) * k / n) for k in range(n)]
    return out


def clearance(pts, centre, r):
    return min(math.hypot(x - centre[0], z - centre[1]) for x, z in _edge_pts(pts)) - r


def limits(i):
    """Highest and lowest the link may sit on string i's drop line (its bottom's z), from the two
    bearings: (z_bottom_max, z_bottom_min)."""
    g = D.STRING_GAUGE[i]
    xs = g / 2                                           # the drop line (string's centre)
    br = (B.BR_C[0], B.BR_C[1]); bd = (B.X_BEND, B.z_level(B.level(i)) + B.R)
    base = [(x + xs, z) for x, z in link_outline()]
    # bisect each limit
    def ok_top(zb):
        return clearance([(x, z + zb) for x, z in base], br, B.R) >= CLR
    def ok_bot(zb):
        return clearance([(x, z + zb) for x, z in base], bd, B.R) >= CLR
    lo, hi = bd[1], br[1]
    a, b = bd[1] - 30, br[1]                              # top: highest zb that is ok
    for _ in range(50):
        m = (a + b) / 2
        a, b = (m, b) if ok_top(m) else (a, m)
    top = a
    a, b = bd[1] - 30, br[1] + 30                          # bottom: lowest zb that is ok
    a = bd[1]
    for _ in range(50):
        m = (a + b) / 2
        a, b = (a, m) if ok_bot(m) else (m, b)
    bot = b
    return top, bot


def report():
    print(f"link {LINK_W:.1f} wide (X) x {LINK_H:.1f} tall x {T_LINK} thick; travel {TRAVEL}")
    print(" str row  drop  room for the link's bottom   needs   spare")
    rows = []
    for i in range(D.N_STRINGS):
        top, bot = limits(i)
        drop = B.BR_C[1] - (B.z_level(B.level(i)) + B.R)
        room = top - bot
        spare = room - TRAVEL
        rows.append((i, spare))
        print(f" {i + 1:3d}  {B.level(i)}   {drop:5.1f}   {bot:7.1f} .. {top:6.1f} = {room:5.1f}   {TRAVEL:5.1f}  {spare:+6.1f}")
    return rows


def draw(path="leader_study.png"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Polygon
    BG, W, Bc, O, G = "#36383d", "#e5e5e5", "#00b4d8", "#ff6b00", "#39ff14"
    fig, axs = plt.subplots(1, 2, figsize=(13, 11)); fig.patch.set_facecolor(BG)
    for ax, i in ((axs[0], 9), (axs[1], 8)):
        ax.set_facecolor(BG)
        g = D.STRING_GAUGE[i]; xs = g / 2
        zc = B.z_level(B.level(i)) + B.R
        for c in (B.BR_C, (B.X_BEND, zc)):
            ax.add_patch(Circle(c, B.R, fc="#555", ec="#ccc"))
            ax.add_patch(Circle(c, B.R + CLR, fc="none", ec="#888", ls=":"))
        top, bot = limits(i)
        for zb, col, lab in ((top, O, "slack end (t = 0)"), (top - TRAVEL, "#ffd60a", "full travel")):
            pts = [(x + xs, z + zb) for x, z in link_outline()]
            ax.add_patch(Polygon(pts, closed=True, fc="none", ec=col, lw=2, label=lab))
            ax.add_patch(Polygon([(xs - WIN_W / 2, zb + TINE), (xs + WIN_W / 2, zb + TINE), (xs + WIN_W / 2, zb + TINE + WIN_H),
                                  (xs - WIN_W / 2, zb + TINE + WIN_H)], closed=True, fc="none", ec=col, lw=1))
        ax.plot([xs, xs], [B.BR_C[1], zc], color=W, lw=1.2, ls="--")
        ax.axhspan(bot, top, xmin=0, xmax=1, color="#2a9d8f", alpha=0.15)
        ax.set_title(f"string {i + 1}, row {B.level(i)}: room {top - bot:.1f}, needs {TRAVEL}", color="w")
        ax.set_xlim(-18, 12); ax.set_ylim(min(zc - 10, bot - 15), B.BR_C[1] + 10); ax.set_aspect("equal")
        ax.tick_params(colors="#999"); [s.set_color("#666") for s in ax.spines.values()]
        ax.legend(facecolor=BG, labelcolor="w", fontsize=8, loc="lower left")
    fig.suptitle("Leader link on the drop line: bridge bearing above, bend bearing below (to scale, mm)", color="w")
    plt.savefig(path, dpi=110, facecolor=BG, bbox_inches="tight")


if __name__ == "__main__":
    rows = report()
    os.makedirs("quotes", exist_ok=True)
    cq.exporters.export(link_solid(), "quotes/leader_link.step")
    draw()
    print("wrote leader_study.png, quotes/leader_link.step")
