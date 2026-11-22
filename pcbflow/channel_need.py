"""channel_need.py -- channel needs -> hard placement keepouts (lead 2026-11-21).

    py -3.12 channel_need.py INTENT_IN BOARD_GEOM.json CHANNELS.json INTENT_OUT

A CHANNEL is the strip an around-band of a given need must find clear of MOVABLE parts. It is
stated as a need between named pads, never as an offset to a part: placement satisfies it.
  width = max(need, AROUND_NECK) + 2 x zone clearance + MARGIN      (0.6, 0.5, 0.3 here, the
          band generator's own walls and the raster margin -- pour_around)
Each channel is a Manhattan polyline of anchor points; every leg becomes a rectangle `width`
wide centred on it. Coordinates are expressions on pad boxes, e.g.
  {"x": "F202.1@right", "y": "F204.1@bottom + w/2"}
with @left @right @top @bottom @cx @cy and the terms w (this channel's width), numbers, + and -.
FIXED parts' courtyards (grown by CUT_GROW) are cut out of the keepout -- they are the channel's
walls, and a hard keepout over a fixed part is a broken rule. Holds listed in the spec's
"release" are dropped from the intent (with a soft `near` back to their IC) so placement can
move them out of the channel.

BOARD_GEOM.json: {REF: {"cy": [[x, y], ...], "pads": {PIN: [x0, x1, y0, y1]}}} in the gerber
frame, as KiCad writes it (board x = gx - 100, board y = 100 - gy for the brain board's sheet
origin; set ORIGIN for another sheet).

⚠ Take BOARD_GEOM from a layout of the SAME seats the intent holds (esc_pre15D's board had
R313 1.5 mm off its esc5 hold, and the derived cut was wrong by exactly that).
"""
import json
import re
import sys

AROUND_NECK, ZONE_CLR, MARGIN, CUT_GROW, MIN_RECT = 0.6, 0.5, 0.3, 0.3, 0.2
ORIGIN = (100.0, 100.0)


def width(need):
    return max(need, AROUND_NECK) + 2 * ZONE_CLR + MARGIN


def _side(box, s):
    x0, x1, y0, y1 = box
    return {"left": x0, "right": x1, "top": y0, "bottom": y1, "cx": (x0 + x1) / 2, "cy": (y0 + y1) / 2}[s]


def evaluate(expr, geom, w):
    tot = 0.0
    for sign, term in re.findall(r"([+-]?)\s*([^+\-\s][^+\-]*)", expr.replace(" ", "")):
        term = term.strip()
        if "@" in term:
            ref_pin, s = term.split("@")
            ref, pin = ref_pin.rsplit(".", 1)
            v = _side(geom[ref]["pads"][pin], s)
        elif term == "w/2":
            v = w / 2
        elif term == "w":
            v = w
        else:
            v = float(term)
        tot += -v if sign == "-" else v
    return tot


def legs(points, w):
    rs = []
    for (ax, ay), (bx, by) in zip(points, points[1:]):
        if abs(ay - by) < 1e-9:            # horizontal leg
            rs.append([min(ax, bx), max(ax, bx), ay - w / 2, ay + w / 2])
        elif abs(ax - bx) < 1e-9:          # vertical leg
            rs.append([ax - w / 2, ax + w / 2, min(ay, by), max(ay, by)])
        else:
            raise ValueError("channel legs must be axis-aligned: %r -> %r" % ((ax, ay), (bx, by)))
    return rs


def sub(rs, c):
    out = []
    for x0, x1, y0, y1 in rs:
        if c[1] <= x0 or c[0] >= x1 or c[3] <= y0 or c[2] >= y1:
            out.append([x0, x1, y0, y1])
            continue
        if c[0] > x0:
            out.append([x0, c[0], y0, y1])
        if c[1] < x1:
            out.append([c[1], x1, y0, y1])
        mx0, mx1 = max(x0, c[0]), min(x1, c[1])
        if c[2] > y0:
            out.append([mx0, mx1, y0, c[2]])
        if c[3] < y1:
            out.append([mx0, mx1, c[3], y1])
    return out


def bbox(g):
    if g["cy"]:
        p = g["cy"]
        return [min(q[0] for q in p), max(q[0] for q in p), min(q[1] for q in p), max(q[1] for q in p)]
    bs = list(g["pads"].values())
    return [min(b[0] for b in bs), max(b[1] for b in bs), min(b[2] for b in bs), max(b[3] for b in bs)]


def keepouts(intent, geom, spec, log=print):
    release = spec.get("release", {})
    fixed = {r["ref"] for r in intent if r.get("kind") == "fixed"}
    # a rigid cell's members are fixed with their anchor (esc11_pre3, 2026-11-22: the +24V channel
    # off Q209.5 kept 0.62 mm over Q209, a boost cell member, and the intent check called it BROKEN)
    for r in intent:
        if r.get("kind") == "group" and r.get("anchor") in fixed:
            fixed |= set(r.get("members", {}))
    fixed -= set(release)
    rules = []
    for ch in spec["channels"]:
        w = width(ch["need"])
        pts = [(evaluate(p["x"], geom, w), evaluate(p["y"], geom, w)) for p in ch["points"]]
        rs = legs(pts, w)
        for ref in sorted(fixed):
            if ref in geom:
                c = bbox(geom[ref])
                rs = sub(rs, [c[0] - CUT_GROW, c[1] + CUT_GROW, c[2] - CUT_GROW, c[3] + CUT_GROW])
        rs = [r for r in rs if r[1] - r[0] > MIN_RECT and r[3] - r[2] > MIN_RECT]
        b = lambda gx, gy: [round(gx - ORIGIN[0], 3), round(ORIGIN[1] - gy, 3)]
        for x0, x1, y0, y1 in rs:
            rules.append({"kind": "keepout", "hard": True,
                          "poly": [b(x0, y0), b(x1, y0), b(x1, y1), b(x0, y1)],
                          "why": "%s channel need %s: %.2f mm wide (need %.2f, floor %.1f, + 2 x %.1f zone "
                                 "clearance + %.1f), fixed courtyards cut out (channel_need.py)"
                                 % (ch["net"], ch.get("name", ""), w, ch["need"], AROUND_NECK, ZONE_CLR, MARGIN),
                          "src": ch.get("src", "channel need")})
        log("%s %s: %.2f wide, %d keepout rect(s)" % (ch["net"], ch.get("name", ""), w, len(rs)))
    out = [r for r in intent if not (r.get("kind") == "fixed" and r.get("ref") in release)] + rules
    for ref, rel in release.items():
        out.append({"kind": "near", "ref": ref, "target": rel["near"], "max_mm": rel.get("max_mm", 8.0),
                    "hard": False, "why": rel["why"], "src": "channel_need.py"})
    return out


if __name__ == "__main__":
    intent = json.load(open(sys.argv[1]))
    geom = json.load(open(sys.argv[2]))
    spec = json.load(open(sys.argv[3]))
    json.dump(keepouts(intent, geom, spec), open(sys.argv[4], "w"), indent=0)
