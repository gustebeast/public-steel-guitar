"""A land that offers both pin orders reads straight (brain_board fold13, 2026-11-27).

    py -3.12 test_pair_twist_lands.py

fold13 warned TWIST USBB_J FL4 -> J2 and not the identical USBA_J FL3 -> J1: a USB-C receptacle
carries D+ / D- as A6 / A7 and again as B6 / B7, mirrored, and pair_twists judged ONE 0.5 mm pin
pair at each end -- the one a 0.1 mm rounding of its distance put first. fold13's world geometry,
no files (pads long along x, as placed):
1. J1 / FL3 (y 99) and J2 / FL4 (y 116 vs 128): both USB*_J hops read straight.
2. A real twist still reads twisted: FL3's chip side -> a TS3USB221 land on the old mirrored pins
   (U17, D- left of D+ on its +y face), and straight once the land is on the datasheet pins.
Exit 0 = PASS.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import place_intent as pi  # noqa: E402

bad = []


def part(w, h, pads):
    """pads: (num, net, (x, y) local, (sx, sy))"""
    return dict(crtyd=[[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]],
                fab=[-w / 2, w / 2, -h / 2, h / 2], side="F",
                pads=[dict(num=n, net=net, xy=list(xy), size=list(sz), rot=0.0) for n, net, xy, sz in pads])


def usbc(p, m):
    # J1 / J2 on fold13: centre x 26.79, the signal row at x +4.04, pads long along x
    c = (1.0, 0.3)
    return part(9.0, 9.0, [("A6", p, (4.04, -0.25), c), ("A7", m, (4.04, 0.25), c),
                           ("B6", p, (4.04, 0.75), c), ("B7", m, (4.04, -0.75), c)])


def cmc(pj, mj, p, m):
    # ACM2012 (FL3 / FL4): 1 DP_J, 2 DM_J on -x; 3 DM, 4 DP on +x
    c = (0.7, 0.45)
    return part(2.6, 1.8, [("1", pj, (-0.95, -0.4), c), ("2", mj, (-0.95, 0.4), c),
                           ("3", m, (0.95, 0.4), c), ("4", p, (0.95, -0.4), c)])


def sw(p, m, mirrored):
    # TS3USB221 land facing +y: pins 1 / 2 at x -0.75 / -0.25 (fold13 U17, pads long along y)
    c = (0.25, 0.7)
    a, b = (m, p) if mirrored else (p, m)
    return part(2.0, 2.0, [("1", a, (-0.75, 0.67), c), ("2", b, (-0.25, 0.67), c)])


def judge(parts, pl, nets):
    return {(a, b): v for _, a, b, v in pi.pair_twists(parts, pl, [dict(name=nets[0], nets=list(nets))])}


# 1. both receptacle hops
parts = {"J1": usbc("A_PJ", "A_MJ"), "FL3": cmc("A_PJ", "A_MJ", "A_P", "A_M"),
         "J2": usbc("B_PJ", "B_MJ"), "FL4": cmc("B_PJ", "B_MJ", "B_P", "B_M")}
pl = {"J1": (26.79, 100.0, 0.0), "FL3": (42.19, 99.2, 0.0),
      "J2": (26.79, 128.0, 0.0), "FL4": (42.28, 116.2, 0.0)}
for nets, hop in ((("A_PJ", "A_MJ"), ("FL3", "J1")), (("B_PJ", "B_MJ"), ("FL4", "J2"))):
    got = judge(parts, pl, nets)
    print("%s -> %s: %s" % (hop[0], hop[1], got))
    if got.get(hop) != "straight":
        bad.append("%s -> %s reads %s, wants straight" % (hop[0], hop[1], got.get(hop)))

# 2. a real twist (FL3's chip side -> a switch land at (50.28, 104.3)) is still found
for mirrored, want in ((True, "twisted"), (False, "straight")):
    parts2 = {"FL3": parts["FL3"], "U17": sw("A_P", "A_M", mirrored)}
    pl2 = {"FL3": pl["FL3"], "U17": (50.28, 104.3, 0.0)}
    got = judge(parts2, pl2, ("A_P", "A_M"))
    print("FL3 -> U17 (%s pins): %s" % ("mirrored" if mirrored else "datasheet", got))
    if got.get(("FL3", "U17")) != want:
        bad.append("FL3 -> U17 %s reads %s, wants %s" % ("mirrored" if mirrored else "datasheet",
                                                         got.get(("FL3", "U17")), want))

print("\n".join(bad) if bad else "PASS")
sys.exit(1 if bad else 0)
