"""A kelvin tie sits on its shunt's land; two held parts may not overlap (brain_board fold12-15, 2026-11-27).

    py -3.12 test_kelvin_seat.py

fold12-14: the PA/PB sense ties NT11 / NT12 / NT21 / NT22 (no courtyard) went where the net graph
put them -- NT11 mid-path on FL1.4 -> R70.1, PA_VBUS 0.60 mm -- and A30 read all four NOT ON.
fold15_s2: p22's hand holds for NT21 / NT22 sat under D20's snapshot hold, found as a 0.0015 mm
DRC clearance five hours later. fold15's geometry (R75 R_0805 shunt, NetTie-2_SMD_Pad0.5mm,
D20 SOD-323 courtyard), no files:
1. Free ties on a free shunt are seated by a group on the shunt: p22's hand offsets
   ([-0.9125, 1.2, 90] / [0.9125, 1.2, 90]), and each tie's pad is on its land at every turn.
2. A shunt that is a member of another group: the ties join that group, still on the land.
3. A hand rule that holds a tie ON its land is kept; OFF its land (fold14's NT11) it is refused;
   held while its shunt is free, it is refused (its land is not known yet).
4. A 10k resistor is no shunt: a tie on it is not seated.
5. hold_overlaps: fold15's D20 against NT21 / NT22 is found; p23's D20 (0.6 north) is clear; a tie
   on its own shunt is not an overlap.
Exit 0 = PASS.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import place_intent as pi  # noqa: E402

bad = []


def pad(num, net, xy, size):
    return dict(num=num, net=net, xy=list(xy), size=list(size), rot=0.0, tht=False)


R75 = dict(side="F", pads=[pad("1", "PB_VBUS", (-0.9125, 0), (1.025, 1.4)), pad("2", "PB_VCC", (0.9125, 0), (1.025, 1.4))],
           crtyd=[[1.675, 0.945], [1.675, -0.945], [-1.675, -0.945], [-1.675, 0.945]], fab=[-1.05, 1.05, -0.675, 0.675])
D20 = dict(side="F", pads=[pad("1", "PA_GATE", (-0.7, 0), (0.6, 0.6)), pad("2", "PA_GCLAMP", (0.7, 0), (0.6, 0.6))],
           crtyd=[[-1.295, -0.75], [1.295, -0.75], [1.295, 0.75], [-1.295, 0.75]], fab=None)


def tie(a, b):
    return dict(side="F", pads=[pad("1", a, (-0.5, 0), (0.5, 0.5)), pad("2", b, (0.5, 0), (0.5, 0.5))], crtyd=None, fab=None)


def board():
    return {"R75": R75, "D20": D20, "NT21": tie("PB_VBUS", "PB_ISENP_K"), "NT22": tie("PB_VCC", "PB_VCC_K"),
            "U21": dict(side="F", pads=[pad("1", "PB_ISENP_K", (0, 0), (0.3, 0.3))],
                        crtyd=[[-1, -1], [1, -1], [1, 1], [-1, 1]], fab=None)}


VAL = {"R75": "10mR", "D20": "BAT54", "U21": "INA"}
WANT = {"NT21": [-0.9125, 1.2, 90.0], "NT22": [0.9125, 1.2, 90.0]}


def on_land_world(parts, rules, pl):
    """{tie: on?} with every group's members expanded from the anchor's world pose pl."""
    out = {}
    for r in rules:
        if r.get("kind") != "group":
            continue
        ax, ay, ar = pl[r["anchor"]]
        pose = {r["anchor"]: (ax, ay, ar)}
        for m, (dx, dy, dr) in r["members"].items():
            o = pi._rot([[dx, dy]], ar)[0]
            pose[m] = (ax + o[0], ay + o[1], (ar + dr) % 360.0)
        for t, (s, land, tp) in pi.kelvin_ties(parts, VAL)[0].items():
            if t in pose and s in pose:
                out[t] = pi._on_land(parts, s, pose[s], land, t, pose[t], tp)
    return out


# 1. free ties on a free shunt
P = board()
rules, lines, refused = pi.kelvin_seats([], P, VAL)
print("1:", lines, refused)
g = [r for r in rules if r.get("kind") == "group"]
if refused or len(g) != 1 or g[0]["anchor"] != "R75":
    bad.append("1: wanted one group on R75, got %s / refused %s" % (g, refused))
else:
    for t, w in WANT.items():
        if not np.allclose(g[0]["members"].get(t, [9, 9, 9]), w, atol=1e-3):
            bad.append("1: %s seated at %s, wants p22's %s" % (t, g[0]["members"].get(t), w))
    for a in (0.0, 90.0, 180.0, 270.0, 33.0):
        got = on_land_world(P, rules, {"R75": (-51.215, -20.3, a)})
        if got != {"NT21": True, "NT22": True}:
            bad.append("1: shunt at %g deg: ties on land %s" % (a, got))

# 2. the shunt is a member of another group (anchored on U21)
rules, lines, refused = pi.kelvin_seats([dict(kind="group", anchor="U21", members={"R75": [3.0, -2.0, 90.0]}, hard=True)],
                                        P, VAL)
print("2:", lines, refused)
g = [r for r in rules if r.get("kind") == "group"]
if refused or len(g) != 1 or set(g[0]["members"]) != {"R75", "NT21", "NT22"}:
    bad.append("2: ties not added to U21's group: %s" % g)
else:
    for a in (0.0, 180.0, 45.0):
        got = on_land_world(P, rules, {"U21": (10.0, 5.0, a)})
        if got != {"NT21": True, "NT22": True}:
            bad.append("2: anchor at %g deg: ties on land %s" % (a, got))

# 3. hand rules: on the land (p22), off it (fold14's NT11 spot), held with the shunt free
fx = lambda ref, x, y, r=90.0: dict(kind="fixed", ref=ref, xy=[x, y], rot=r, hold="physical", why="t", hard=True)
p22 = [fx("R75", -51.215, -20.3, 0.0), fx("NT21", -52.13, -19.1), fx("NT22", -50.30, -19.1)]
_, lines, refused = pi.kelvin_seats(p22, P, VAL)
print("3 on:", lines, refused)
if refused:
    bad.append("3: p22's on-land holds refused: %s" % refused)
_, _, refused = pi.kelvin_seats([fx("R75", -51.215, -20.3, 0.0), fx("NT21", -52.13, -17.6), fx("NT22", -50.30, -19.1)], P, VAL)
print("3 off:", refused)
if len(refused) != 1 or "NT21" not in refused[0] or "NOT ON" not in refused[0]:
    bad.append("3: NT21 held 1.5 mm off its land was not refused by name: %s" % refused)
_, _, refused = pi.kelvin_seats([fx("NT21", -52.13, -19.1)], P, VAL)
print("3 free shunt:", refused)
if not any("NT21" in x and "cannot be" in x for x in refused):
    bad.append("3: a held tie on a free shunt was not refused: %s" % refused)

# 4. a 10k resistor is no shunt
rules, lines, refused = pi.kelvin_seats([], P, dict(VAL, R75="10k"))
print("4:", lines)
if lines or refused or any(r.get("kind") == "group" for r in rules):
    bad.append("4: ties seated on a 10k resistor: %s" % lines)

# 5. held-part overlaps
d20 = lambda y: dict(kind="fixed", ref="D20", xy=[-50.815, y], rot=0.0, hold="snapshot", why="t", hard=True)
got = pi.hold_overlaps(p22 + [d20(-18.0)], P, VAL)
print("5 fold15:", got)
if not (any("D20 x NT22" in x for x in got) and any("D20 x NT21" in x for x in got)):
    bad.append("5: fold15's D20 / NT21 / NT22 overlap not found: %s" % got)
got = pi.hold_overlaps(p22 + [d20(-17.4)], P, VAL)
print("5 p23:", got)
if got:
    bad.append("5: p23's D20 (0.6 north) still reads overlapping: %s" % got)
if any("R75" in x for x in pi.hold_overlaps(p22, P, VAL)):
    bad.append("5: a kelvin tie on its own shunt read as an overlap")

print("\n".join(bad) if bad else "PASS")
sys.exit(1 if bad else 0)
