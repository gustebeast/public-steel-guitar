"""Even slots across the south half, and an assignment that shortens what is connected.

    py -3.12 elec/place_slots.py            # report only
    py -3.12 elec/place_slots.py --write    # also write elec/out/place_slots.json

Then route with the override in place:

    OPT_SLOTS=1 py -3.12 elec/optical.py && ... layout/route as usual

⚠ THIS IS A SUGGESTION MACHINE, NOT A PLACER, AND THE DIFFERENCE MATTERS. It moves only
the parts whose position is not doing a job, it never changes the board outline, and its
output is a file the CAD reads on request rather than an edit to the CAD. If it makes the
board worse, delete the json.

WHY IT EXISTS (user, 2026-09-25): "place components evenly spaced in our available PCB
trying to put things that will connect closer together, then view the auto route attempt
and continue to move as need be". The measurement behind it is that the south's component
rows are a BARRIER, not a background: their escape vias pierce every layer, 26 of them in
one row shadowing 38% of the board's width, and where two such rows disagree about where
their gaps are, only 42% of the width is clear through both. Average copper density in
that region is 6-11%, which is why it took a person looking at the board to see it.

THE TWO HALVES

  SLOTS      A grid over the south's free area. Pitch is one 0402 courtyard plus a
             channel wide enough for a track and its clearance, so BY CONSTRUCTION every
             pair of neighbouring slots has a routable gap between them -- which is the
             property the packed rows lost. Slots overlapping a fixed part, a keep-away
             or the board edge are dropped.

  ASSIGNMENT Greedy by connectivity (most-connected part first, into the slot that adds
             least wirelength), then improvement sweeps of single moves and pairwise
             swaps while they help. Wirelength is HPWL -- half the perimeter of a net's
             bounding box -- which is the standard cheap stand-in for routed length and
             is good enough to rank placements.

WHAT IS FIXED, AND WHY EACH ONE (see the user's own list, 2026-09-25):

  north of the border      the string array is finished and verified; nothing here may
                           touch it.
  the buck, U13 and L1     the loudest thing on the board. 52.7 mm from the nearest
                           detector, and near-field coupling falls off as 1/r^3, so
                           halving that distance is ~8x the coupling.
  the reference chain      R34/R35/C114/U11 feed the non-inverting input of all twenty
                           TIAs. Whatever they pick up is common to every channel, and a
                           common error is the one thing neither the lock-in, nor SUM,
                           nor DIFF can reject.
  connectors               J1/J2 are at the -Y edge because the cables are.
  every IC                 big parts anchor the layout; moving them is a decision, not a
                           search.
  decoupling               any small part already hugging an IC. A bypass capacitor's job
                           is set by LOOP INDUCTANCE, so its position IS its value and
                           spreading it evenly is not a neutral act -- it is a downgrade.
                           This is the class the "spread everything" instinct gets wrong,
                           so it is detected by proximity rather than trusted to a list.

Everything else -- test points, pull-ups and pull-downs, series resistors, the CC
resistors, standalone filters -- has a value but not a position, and may move.
"""
from __future__ import annotations

import collections
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from src import optical_pickup as OP  # noqa: E402

BORDER_LOCAL = -19.0            # board-local y: the string array's south edge
TRACK_CH = 0.55                 # a 0.25 track plus clearance either side
HUG_MM = 2.6                    # a small part this close to an IC is its decoupling
KEEP = {"U13", "L1", "R34", "R35", "C114", "U11"}   # noise-critical, see the header
KEEP_CLR = 1.0                  # extra room left around a fixed part


def _cy():
    ys = [v for s in OP._SECTIONS for v in (s[0], s[1])]
    return (min(ys) + max(ys)) / 2.0


def _netlist():
    """{net: [refs]} from the generated netlist, power and ground left out.

    ⚠ GND AND THE RAILS ARE NOT WIRELENGTH. They reach almost every part, so including
    them makes every placement equally good and the optimiser blind. They are poured or
    trunked, not routed point to point."""
    path = os.path.join(HERE, "out", "optical.net")
    txt = open(path, encoding="utf-8").read()
    out = {}
    for m in re.finditer(r'\(net\s*\(code "?\d+"?\)\s*\(name "([^"]+)"\)(.*?)'
                         r'(?=\(net\s*\(code|\Z)', txt, re.S):
        name = m.group(1)
        if name == "GND" or name.startswith(("+3V3", "+5V", "+24V", "V5_PRE", "VBUS")):
            continue
        refs = sorted({r for r, _p in re.findall(r'\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)',
                                                 m.group(2))})
        if len(refs) > 1:
            out[name] = refs
    return out


def _parts():
    """ref -> dict(x, y, w, h, pkg) in BOARD-LOCAL mm."""
    cy = _cy()
    out = {}
    for p in OP.PARTS:
        w, h = OP.CRTYD[p["pkg"]][0], OP.CRTYD[p["pkg"]][1]
        out[p["ref"]] = {"x": p["x"], "y": p["y"] - cy, "w": w, "h": h, "pkg": p["pkg"],
                         "cadx": p["x"], "cady": p["y"]}
    return out


def _bypass(parts):
    """Every part with one pad on GND and one on a rail: a bypass, whatever it is called.

    ⚠ PROXIMITY WAS THE WRONG TEST AND THE FIRST RUN PROVED IT. Detecting decoupling as
    "a small part hugging an IC" missed C108-C111 and C141/C143, which sit in a column a
    little further out than the threshold -- and the optimiser cheerfully moved them 45 to
    68 mm across the board, which for a bypass capacitor is not a move, it is a deletion.
    Its whole job is the loop it closes, and the loop is the position.
    So the test is what the part IS, read off the netlist: GND on one pad and a supply on
    the other. That cannot drift out of range of a threshold."""
    path = os.path.join(HERE, "out", "optical.net")
    txt = open(path, encoding="utf-8").read()
    on = collections.defaultdict(set)
    for m in re.finditer(r'\(net\s*\(code "?\d+"?\)\s*\(name "([^"]+)"\)(.*?)'
                         r'(?=\(net\s*\(code|\Z)', txt, re.S):
        for r, _pin in re.findall(r'\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)', m.group(2)):
            on[r].add(m.group(1))
    rails = ("+3V3", "+5V", "+24V", "V5_PRE", "VBUS", "VCAP", "VBAT", "VREF", "AVDD",
             "IOVDD", "DREG", "AREG", "PHY_1V8", "PHY_VDD33", "LDO_BYP", "BUCK_VCC")
    out = set()
    for ref, nets in on.items():
        if "GND" in nets and any(n.startswith(rails) for n in nets) and len(nets) == 2:
            out.add(ref)
    return out


def _fixed(parts):
    """The refs this routine may not move, each with the reason, so the report can say."""
    why = {}
    ics = [r for r, p in parts.items()
           if p["pkg"] in ("LQFP176", "QFN-24", "WQFN-24", "SOT-223", "SOT-23-5",
                           "SOT-23", "SOT-563", "USB-C", "XH-SM-4Y", "RNX12", "IND-4040",
                           "3225", "PD15", "0603OPT", "VSSOP-8", "TP")]
    for ref, p in parts.items():
        if p["y"] > BORDER_LOCAL:
            why[ref] = "north of the border"
        elif ref in KEEP:
            why[ref] = "noise-critical"
        elif p["pkg"] in ("LQFP176", "QFN-24", "WQFN-24", "SOT-223", "SOT-23-5", "SOT-23",
                          "SOT-563", "USB-C", "XH-SM-4Y", "RNX12", "IND-4040", "3225"):
            why[ref] = "an IC, a connector or an inductor"
    for ref in _bypass(parts):
        if ref in parts and ref not in why and parts[ref]["y"] <= BORDER_LOCAL:
            why[ref] = "a bypass -- its position IS its value"
    for ref, p in parts.items():
        if ref in why or p["pkg"] == "TP":
            continue
        for ic in ics:
            q = parts[ic]
            dx = max(abs(p["x"] - q["x"]) - (p["w"] + q["w"]) / 2, 0.0)
            dy = max(abs(p["y"] - q["y"]) - (p["h"] + q["h"]) / 2, 0.0)
            if math.hypot(dx, dy) <= HUG_MM:
                why[ref] = "decoupling at %s" % ic
                break
    return why


def clusters(parts, why, byp):
    """Rigid groups: an IC with its bypasses, kept at their exact relative offsets.

    ⚠ THE CLUSTER IS THE UNIT, NOT THE PART, AND THE FIRST VERSION HAD THIS BACKWARDS
    (user, 2026-09-25). Freezing every bypass where it stood left 14 of 72 parts movable
    and made the placer pointless -- but a bypass does not need to be at a FIXED POINT, it
    needs to be at ITS PIN. Carry the capacitor with the part it serves and the loop is
    preserved exactly, wherever the pair ends up. That is what lets a whole regulator and
    its caps cross the board without costing a picohenry, and it is how the CAD's own row
    packer already moves the two LDOs.
    """
    own = {}
    ics = [r for r, p in parts.items()
           if p["pkg"] in ("LQFP176", "QFN-24", "WQFN-24", "SOT-223", "SOT-23-5",
                           "SOT-23", "SOT-563", "USB-C", "XH-SM-4Y", "RNX12", "3225")]
    for ref in byp:
        if ref not in parts:
            continue
        near = [(math.hypot(parts[ref]["x"] - parts[i]["x"],
                            parts[ref]["y"] - parts[i]["y"]), i) for i in ics]
        if near:
            own[ref] = min(near)[1]
    groups = collections.defaultdict(list)
    for ref, p in parts.items():
        if p["y"] > BORDER_LOCAL:
            continue
        groups[own.get(ref, ref)].append(ref)
    out = {}
    for head, members in groups.items():
        xs = [parts[r]["x"] for r in members]
        ys = [parts[r]["y"] for r in members]
        cx = (min(xs) + max(xs)) / 2.0
        cy = (min(ys) + max(ys)) / 2.0
        w = max(parts[r]["x"] + parts[r]["w"] / 2 for r in members) -             min(parts[r]["x"] - parts[r]["w"] / 2 for r in members)
        h = max(parts[r]["y"] + parts[r]["h"] / 2 for r in members) -             min(parts[r]["y"] - parts[r]["h"] / 2 for r in members)
        out[head] = {"members": members, "x": cx, "y": cy, "w": w, "h": h,
                     "off": {r: (parts[r]["x"] - cx, parts[r]["y"] - cy)
                             for r in members}}
    return out


def _slots(cl, fixed):
    """Slots that use ALL the free south, not the least room a track can pass through.

    ⚠ SIZED FROM THE AREA, NOT FROM A MINIMUM (user, 2026-09-25: "I was suggesting we slot
    based on using all the available PCB in the south, which I presume would be well above
    a single routable channel"). The first version took one courtyard plus 0.55 mm and
    produced 417 slots for the parts to huddle in, which reproduces the exact fault it was
    written to fix: the packed rows were evenly spread too, and being evenly spread at the
    minimum is what made them a wall.

    So: take the free area, divide it by the number of groups that have to live in it, and
    let THAT set the pitch -- floored by the largest group so nothing overlaps. Spacing
    comes out as whatever the board can afford, which is the point."""
    xs = [v for s in OP._SECTIONS for v in (s[2], s[3])]
    x0, x1 = min(xs) + 1.0, max(xs) - 1.0
    y1 = BORDER_LOCAL - 1.0
    y0 = min(c["y"] - c["h"] / 2 for c in cl.values()) + 1.0
    free = [h for h in cl if h not in fixed]
    blocks = [(cl[h]["x"], cl[h]["y"], cl[h]["w"] / 2 + KEEP_CLR, cl[h]["h"] / 2 + KEEP_CLR)
              for h in fixed if h in cl]
    area = (x1 - x0) * (y1 - y0) - sum(4 * bx * by for _a, _b, bx, by in blocks)
    cell = math.sqrt(max(area, 1.0) / max(len(free), 1))
    px = max(cell, max((cl[h]["w"] for h in free), default=1.0) + TRACK_CH)
    py = max(cell, max((cl[h]["h"] for h in free), default=1.0) + TRACK_CH)
    out = []
    for j in range(int((y1 - y0) / py)):
        for i in range(int((x1 - x0) / px)):
            x = x0 + px / 2 + i * px
            y = y0 + py / 2 + j * py
            if any(abs(x - bx) < brx + px / 2 and abs(y - by) < bry + py / 2
                   for bx, by, brx, bry in blocks):
                continue
            out.append((x, y))
    return out, px, py


def _hpwl(nets, pos):
    """Half-perimeter wirelength over every net both of whose ends we know."""
    tot = 0.0
    for refs in nets.values():
        pts = [pos[r] for r in refs if r in pos]
        if len(pts) < 2:
            continue
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        tot += (max(xs) - min(xs)) + (max(ys) - min(ys))
    return tot


def assign(parts, cl, fixed, slots, nets, sweeps=4):
    """Greedy by connectivity, then improvement sweeps -- over CLUSTERS.

    Not optimal and does not need to be: the routed board is the judge, and it disagrees
    with HPWL often enough that polishing this would be polishing the wrong number."""
    pos = {r: (p["x"], p["y"]) for r, p in parts.items()}
    free = [h for h in cl if h not in fixed]
    deg = collections.Counter()
    for refs in nets.values():
        for r in refs:
            deg[r] += 1
    free.sort(key=lambda h: -sum(deg[r] for r in cl[h]["members"]))
    by_ref = collections.defaultdict(list)
    for name, refs in nets.items():
        for r in refs:
            by_ref[r].append(name)

    def put(head, xy, pos):
        for r, (dx, dy) in cl[head]["off"].items():
            pos[r] = (xy[0] + dx, xy[1] + dy)

    def cost_of(head, xy, pos):
        """Only the nets this cluster touches -- nothing else can change."""
        trial = dict(pos)
        put(head, xy, trial)
        seen, tot = set(), 0.0
        for r in cl[head]["members"]:
            for name in by_ref[r]:
                if name in seen:
                    continue
                seen.add(name)
                pts = [trial[q] for q in nets[name] if q in trial]
                if len(pts) < 2:
                    continue
                xs, ys = [q[0] for q in pts], [q[1] for q in pts]
                tot += (max(xs) - min(xs)) + (max(ys) - min(ys))
        return tot

    open_slots = list(slots)
    at = {}
    for head in free:
        for r in cl[head]["members"]:
            pos.pop(r, None)
    for head in free:
        if not open_slots:
            # ⚠ NO SLOT MEANS STAY PUT, NOT VANISH. Leaving it out of `pos` removes its
            # nets from the score, which reads as an improvement.
            put(head, (cl[head]["x"], cl[head]["y"]), pos)
            continue
        i = min(range(len(open_slots)), key=lambda k: cost_of(head, open_slots[k], pos))
        at[head] = open_slots.pop(i)
        put(head, at[head], pos)

    for _ in range(sweeps):
        moved = 0
        for head in free:
            if head not in at:
                continue
            here = cost_of(head, at[head], pos)
            best, bc = None, here
            for i, sl in enumerate(open_slots):
                c = cost_of(head, sl, pos)
                if c < bc - 1e-9:
                    best, bc = i, c
            if best is not None:
                open_slots.append(at[head])
                at[head] = open_slots.pop(best)
                put(head, at[head], pos)
                moved += 1
        for a in free:
            for b in free:
                if a >= b or a not in at or b not in at:
                    continue
                before = cost_of(a, at[a], pos) + cost_of(b, at[b], pos)
                at[a], at[b] = at[b], at[a]
                put(a, at[a], pos)
                put(b, at[b], pos)
                if cost_of(a, at[a], pos) + cost_of(b, at[b], pos) >= before - 1e-9:
                    at[a], at[b] = at[b], at[a]
                    put(a, at[a], pos)
                    put(b, at[b], pos)
                else:
                    moved += 1
        if not moved:
            break
    return pos, free, at


def main(argv):
    parts = _parts()
    nets = _netlist()
    why = _fixed(parts)
    byp = _bypass(parts)
    cl = clusters(parts, why, byp)
    # a cluster is fixed if its head is: the connectors are at the -Y edge because the
    # cables are, and the buck and the reference chain are placed against the strip's
    # noise budget rather than against wirelength
    fixed = {h for h in cl if h in KEEP or h.startswith("J")
             or any(m in KEEP for m in cl[h]["members"])}
    # ⚠ AND ANYTHING BIG IS AN ANCHOR. The MCU and its ring of bypasses is a 34 x 27 mm
    # cluster; letting it into the pool set the slot pitch to 34.8 mm, which fits ZERO
    # slots on a 53 mm board and placed nothing at all -- while still reporting a 47%
    # HPWL improvement, because the clusters it failed to place dropped out of the sum.
    # A number that improves when the routine does nothing is worse than no number.
    # Large parts are placed by a person for reasons that are not wirelength.
    fixed |= {h for h, c in cl.items() if c["w"] > 12.0 or c["h"] > 12.0}
    slots, px, py = _slots(cl, fixed)
    before = {r: (p["x"], p["y"]) for r, p in parts.items()}
    pos, free, at = assign(parts, cl, fixed, slots, nets)

    print("south of the border: %d part(s) in %d cluster(s); %d fixed, %d free"
          % (sum(len(c["members"]) for c in cl.values()), len(cl), len(fixed), len(free)))
    print("slots: %d at a %.1f x %.1f mm pitch -- the free area divided by the clusters "
          "that must live in it" % (len(slots), px, py))
    biggest = max(cl.values(), key=lambda c: c["w"] * c["h"])
    print("       (largest cluster %.1f x %.1f mm, so the gap between neighbours is "
          "about %.1f mm)" % (biggest["w"], biggest["h"], px - biggest["w"]))
    for h in sorted(fixed):
        print("   fixed: %-6s %s" % (h, ", ".join(cl[h]["members"][:6])))
    print()
    b, a = _hpwl(nets, before), _hpwl(nets, pos)
    print("HPWL over %d signal net(s):  %8.1f mm  ->  %8.1f mm   (%+.1f%%)"
          % (len(nets), b, a, 100 * (a - b) / max(b, 1)))
    moves = sorted(((math.hypot(pos[h][0] - before[h][0], pos[h][1] - before[h][1]), h)
                    for h in free if h in pos and h in before), reverse=True)
    print("moved %d cluster(s); the ten farthest:" % len(free))
    for d, h in moves[:10]:
        print("   %-6s %6.2f mm  %2d part(s)  (%7.2f,%7.2f) -> (%7.2f,%7.2f)"
              % (h, d, len(cl[h]["members"]), before[h][0], before[h][1],
                 pos[h][0], pos[h][1]))

    if "--write" in argv:
        cy = _cy()
        out = {r: [round(pos[r][0], 4), round(pos[r][1] + cy, 4)]
               for h in free for r in cl[h]["members"] if r in pos}
        path = os.path.join(HERE, "out", "place_slots.json")
        json.dump(out, open(path, "w", encoding="utf-8"), indent=1, sort_keys=True)
        print()
        print("wrote %s (%d part(s)) -- OPT_SLOTS=1 makes the CAD read it"
              % (os.path.basename(path), len(out)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
