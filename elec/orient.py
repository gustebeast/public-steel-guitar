"""Which way should each part face? Measured, not eyeballed.

    "C:/Program Files/KiCad/10.0/bin/python.exe" elec/orient.py elec/out/lever_sensor

⚠ ROTATION IS A ROUTING DECISION AND IT HIDES WELL. A part at the wrong angle does not
look wrong -- the courtyard is legal, the placement check passes, the render is fine --
and the only symptom is that some net downstream will not route. On lever_sensor the MCU
sat at 90 degrees with its CAN pins on the north edge while the transceiver they talk to
is south of it and a connector walls off the west side, so both signals had to travel
around the package. One of them made it. The other survived three rounds of being treated
as a routing problem: a wider escape fan, a via hop, a deterministic pre-route. It was a
placement problem the whole time, and one number would have said so.

THE NUMBER is the total distance from each pin to the centroid of the rest of its net. It
is crude -- it knows nothing about obstacles, layers or congestion -- and crude is the
point: it costs nothing, it needs no routing run, and a part that is 12% worse at its
current angle than at another is worth a second look before anyone routes anything.

It does NOT say "rotate this". A part may be held at its angle by something this cannot
see: a connector that has to face the board edge, a crystal that has to stay beside its
oscillator pins, a footprint whose courtyard is not square and would foul a neighbour if
turned. This reports; a person decides.
"""
from __future__ import annotations

import math
import os
import sys

import pcbnew
import wx

wx.DisableAsserts()          # see layout.py -- no modal dialogs in a build step


def score(fp, rot, targets):
    """Total pin-to-net-centroid distance if `fp` were rotated to `rot` degrees."""
    ctr = fp.GetCourtyard(pcbnew.F_CrtYd).BBox().GetCenter()
    d = math.radians(rot - fp.GetOrientationDegrees())
    total = 0.0
    for q in fp.Pads():
        net = q.GetNetname()
        others = [(x, y) for x, y, ref in targets.get(net, ()) if ref != fp.GetReference()]
        if not others:
            continue
        dx, dy = q.GetPosition().x - ctr.x, q.GetPosition().y - ctr.y
        rx = ctr.x + dx * math.cos(d) - dy * math.sin(d)
        ry = ctr.y + dx * math.sin(d) + dy * math.cos(d)
        tx = sum(o[0] for o in others) / len(others)
        ty = sum(o[1] for o in others) / len(others)
        total += math.hypot(rx - tx, ry - ty)
    return total


def report(stem, min_gain=0.08):
    board = pcbnew.LoadBoard(stem + ".kicad_pcb")
    targets = {}
    for fp in board.GetFootprints():
        for q in fp.Pads():
            net = q.GetNetname()
            # GND is everywhere, so it pulls every part toward the middle of the board
            # and tells you nothing. Plane nets are excluded for the same reason.
            if net and net != "GND":
                targets.setdefault(net, []).append(
                    (q.GetPosition().x, q.GetPosition().y, fp.GetReference()))

    rows = []
    for fp in board.GetFootprints():
        if len(list(fp.Pads())) < 3:
            continue          # a two-pad passive has no interesting orientation
        now = fp.GetOrientationDegrees() % 360
        scores = {r: score(fp, r, targets) for r in (0, 90, 180, 270)}
        best = min(scores, key=scores.get)
        if scores[now] <= 0 or best == now:
            continue
        gain = 1.0 - scores[best] / scores[now]
        if gain >= min_gain:
            rows.append((gain, fp.GetReference(), now, best,
                         pcbnew.ToMM(scores[now]), pcbnew.ToMM(scores[best])))
    rows.sort(reverse=True)
    if not rows:
        print("%s: every part is already at its best orientation by this measure"
              % os.path.basename(stem))
    for gain, ref, now, best, s_now, s_best in rows:
        print("  %-5s at %3d deg -> %3d deg would cut pin-to-net distance %.0f%% "
              "(%.1f -> %.1f mm)" % (ref, now, best, gain * 100, s_now, s_best))
    return rows


if __name__ == "__main__":
    for st in sys.argv[1:] or ["elec/out/optical"]:
        report(os.path.abspath(st))
