"""A hard satellite with no room moves what holds it (brain_board po18, 2026-11-26).

    py -3.12 test_hard_room.py

C3 (U5's VIN cap, hard 2.55 mm to U5.2 and U5.1) found NO ROOM: U5 was first dropped with
those pins facing the board edge, C3 was skipped, and after the local pass turned U5 its soft
sibling C18 held the one seat. Synthetic boards, no files.
1. EVICT: U0 and U1 are fixed with a one-cap gap between U0.1 and U1.1. C1 (soft, U0.1) seats
   first and takes the gap; C9 (hard 1.0 mm, U1.1) must get it, and C1 is re-seated by its
   rule elsewhere, not dropped.
2. TURN: U1 is free, pulled against the -X edge by J1, and turned so its VIN pin faces that
   edge with no room. C9 (hard 1.0 mm, U1.1) must seat: U1 is turned for it.
3. TURN WITH A HARD MATE: as 2, plus L1 (big, placed before U1's satellites) held by a hard
   `near` to U1.8 -- on po18 L1 pinned U5's turn. U1 turns with L1 re-seated round it, and
   both hard rules hold.
Exit 0 = PASS.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import place_init as pin  # noqa: E402

bad = []


def box(w, h):
    return [[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]]


def part(w, h, pads):
    return dict(crtyd=box(w, h), fab=[-w / 2, w / 2, -h / 2, h / 2], at=[0, 0, 0], side="F",
                pads=[dict(num=str(i + 1), net=n, xy=xy, size=[0.5, 0.5], rot=0.0) for i, (n, xy) in enumerate(pads)])


def cap(a, b):
    return part(1.6, 0.9, [(a, [-0.5, 0]), (b, [0.5, 0])])


def ic(pin1_net, pin1_xy, tag):
    return part(4.0, 4.0, [(pin1_net, pin1_xy)] + [("%s%d" % (tag, k), [-pin1_xy[0], -1.5 + 0.5 * k]) for k in range(7)])


def run(name, parts, notes, rules, check):
    try:
        pl, log, why = pin.place(parts, notes, rules)
    except SystemExit as e:
        bad.append("%s: place refused: %s" % (name, e))
        return
    hard = [r for r in rules if r.get("hard") and r["kind"] == "decap"]
    for r in hard:
        s = pin._slack(r, parts, pl) if r["cap"] in pl else float("-inf")
        print("%s: %s %s slack %.2f" % (name, r["cap"], pl.get(r["cap"]), s))
        if s < -0.05:
            bad.append("%s: hard %s has no seat (slack %.2f)" % (name, r["cap"], s))
    check(pl, log)
    for l_ in log:
        if l_.startswith("HARD SATELLITE"):
            print("   ", l_)


# 1. EVICT -- U0.1 (+X side) and U1.1 (-X side) face one gap that holds one cap; room for C1
# elsewhere above U0
parts1 = {"U0": ic("VA", [1.75, 0.0], "A"), "U1": ic("VIN", [-1.75, 0.0], "B"),
          "C1": cap("VA", "GND"), "C9": cap("VIN", "GND")}
notes1 = dict(outline_poly=[[0, 0], [11.0, 0], [11.0, 9.0], [0, 9.0]], cutouts=[], placements={})
rules1 = [dict(kind="outline", hard=True),
          dict(kind="fixed", ref="U0", xy=[2.2, 2.5], rot=0.0, hard=True, hold="mechanical", why="test"),
          dict(kind="fixed", ref="U1", xy=[8.8, 2.5], rot=0.0, hard=True, hold="mechanical", why="test"),
          dict(kind="keepout", poly=[[4.2, 4.6], [6.8, 4.6], [6.8, 9.0], [4.2, 9.0]], hard=True, why="test"),
          dict(kind="decap", cap="C1", pin="U0.1", max_mm=3.0, hard=False, src="soft"),
          dict(kind="decap", cap="C9", pin="U1.1", max_mm=1.0, hard=True, src="datasheet")]


def chk1(pl, log):
    if "C1" not in pl:
        bad.append("1: the soft C1 was not re-seated")


run("1 evict", parts1, notes1, rules1, chk1)

# 2. TURN -- J1 at the -X edge pulls U1 (VIN at its -X side) against it; nothing fits between
parts2 = {"J1": part(1.0, 4.0, [("VIN", [0.0, -1.0]), ("GND", [0.0, 1.0])]),
          "U1": ic("VIN", [-1.75, 0.0], "B"), "C9": cap("VIN", "GND")}
notes2 = dict(outline_poly=[[0, 0], [14.0, 0], [14.0, 5.0], [0, 5.0]], cutouts=[], placements={})
rules2 = [dict(kind="outline", hard=True),
          dict(kind="fixed", ref="J1", xy=[0.6, 2.5], rot=0.0, hard=True, hold="mechanical", why="test"),
          dict(kind="decap", cap="C9", pin="U1.1", max_mm=1.0, hard=True, src="datasheet")]
run("2 turn", parts2, notes2, rules2, lambda pl, log: None)

# 3. TURN WITH A HARD MATE
parts3 = dict(parts2, L1=part(4.0, 6.0, [("B6", [-1.5, 0.0]), ("OUT", [1.5, 0.0])]))
notes3 = dict(notes2, outline_poly=[[0, 0], [18.0, 0], [18.0, 9.0], [0, 9.0]])
near3 = dict(kind="near", ref="L1", target="U1.8", max_mm=3.0, hard=True, src="datasheet")
rules3 = rules2 + [near3, dict(kind="apart", a=["L1"], b=["J1"], min_mm=1.0, hard=False, src="test")]


def chk3(pl, log):
    s = pin._slack(near3, parts3, pl) if "L1" in pl else float("-inf")
    print("3 turn+mate: L1 %s U1 %s near slack %.2f" % (pl.get("L1"), pl.get("U1"), s))
    if s < -0.05:
        bad.append("3: L1 lost its hard near U1.8 (slack %.2f)" % s)


run("3 turn+mate", parts3, notes3, rules3, chk3)

print("\n".join(bad) if bad else "PASS")
sys.exit(1 if bad else 0)
