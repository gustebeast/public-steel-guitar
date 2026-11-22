"""rasterpath.py GERBER_DIR BOARD RES_MM --specs SPECS.json [--open-ok]  (the pre-order gate)
   rasterpath.py GERBER_DIR BOARD RES_MM "NAME:LAYERS@x,y>LAYERS@x,y:amps" ...   (one-off points)

--specs takes power_specs.py's JSON (every quality.power_paths entry: both ends as the part's
pads on the net, the width the current needs, inner layers scaled to outer-equivalent) and
prints PASS / WARN / FAIL per path from widepath.judge -- the model is described there. Exit 1
on any FAIL. --open-ok (finish's pre-close gate only) reports a path with no copper at all as
OPEN, not FAIL (widepath.judge open_is_fail); the pre-order gate never passes it.

Widest (maximin) copper path between two points on ORDERED gerbers, no nets needed.
Each copper layer is rasterised exactly as fabbed (traces, flashes, pour regions); layers
join only through the drill file's PLATED holes (a via barrel carries pi*d*25/35 mm of
equivalent track, quality's derating). Width at a pixel = 2 x distance to the nearest
non-copper pixel. Bottleneck = the largest t for which A and B are joined through pixels
of width >= t (binary search, flood fill per layer). Points are in GERBER coordinates
(x, y as written in the files, y negative down the board); LAYERS like F or FB or FI1I2B.

⚠ IT JUDGES WHAT IS FABBED, NOT THE NETS OR quality A1 (R1 check, 2026-11-20). A1 lets a pour
join everything it touches, so a pour island closed with 0.2 mm of track read as full width;
the ordered R1 gerbers carry no net attributes and their board files were regenerated since.
Copper of different nets never touches, so connectivity in the raster IS the net. Measured on
the ordered R1 boards: output_panel +24V_IN 4.14 mm against 4.12 asked at 6.67 A; pi_cap
+5V_PI 0.89 mm (a 1.0 mm neck) against 1.37 at 3 A. Reads ~0.05-0.1 mm under a track's
nominal width at 0.025 mm. Pre-order gate wiring (every quality.power_paths entry, FAIL under
quality.required_width_mm) is still to do.
"""
import math
import os
import re
import sys

import json

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import widepath  # noqa: E402  (the shared core: close_last's CLOSE_POUR_GUARD=2 judges with it too)

GD, NAME, RES = sys.argv[1], sys.argv[2], float(sys.argv[3])
FILES = {"F": "F_Cu.gtl", "I1": "In1_Cu.g1", "I2": "In2_Cu.g2", "B": "B_Cu.gbl"}
PLATING = widepath.PLATING


def macro_poly(name, params, macros):
    """Flash shapes of an aperture as polygons/circles relative to the flash point."""
    if name == "C":
        return [("circle", 0, 0, params[0] / 2)]
    if name == "R":
        w, h = params[0], params[1]
        return [("poly", [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)])]
    if name == "O":
        w, h = params[0], params[1]
        r = min(w, h) / 2
        if w >= h:
            return [("poly", [(-w / 2 + r, -h / 2), (w / 2 - r, -h / 2), (w / 2 - r, h / 2), (-w / 2 + r, h / 2)]),
                    ("circle", -w / 2 + r, 0, r), ("circle", w / 2 - r, 0, r)]
        return [("poly", [(-w / 2, -h / 2 + r), (w / 2, -h / 2 + r), (w / 2, h / 2 - r), (-w / 2, h / 2 - r)]),
                ("circle", 0, -h / 2 + r, r), ("circle", 0, h / 2 - r, r)]
    if name == "RoundRect":
        r = params[0]
        pts = [(params[1 + 2 * k], params[2 + 2 * k]) for k in range(4)]
        out = [("poly", pts)] + [("circle", x, y, r) for x, y in pts]
        for k in range(4):           # rounded edges: thick lines between corners
            out.append(("line", pts[k], pts[(k + 1) % 4], 2 * r))
        return out
    if name in macros:               # FreePoly: outline primitive 4 with rotation param
        nums = macros[name]
        n = int(nums[2])
        pts = [(nums[3 + 2 * k], nums[4 + 2 * k]) for k in range(n + 1)]
        rot = math.radians(params[0] if params else 0.0)
        c, s = math.cos(rot), math.sin(rot)
        return [("poly", [(x * c - y * s, x * s + y * c) for x, y in pts])]
    raise ValueError("aperture %s" % name)


def parse(path):
    txt = open(path, encoding="utf-8", errors="replace").read()
    macros = {}
    for m in re.finditer(r"%AM(\w+)\*(.*?)%", txt, re.S):
        body = m.group(2)
        if m.group(1).startswith("FreePoly"):
            prim = [l for l in body.split("*") if l.strip().startswith("4,")][0]
            macros[m.group(1)] = [float(v) for v in prim.replace("\n", "").split(",")[:-1] if v.strip() and "$" not in v]
    ap = {}
    for m in re.finditer(r"%ADD(\d+)([A-Za-z_]\w*),?([^*]*)\*%", txt):
        params = [float(v) for v in m.group(3).split("X") if v.strip()] if m.group(3) else []
        ap[m.group(1)] = (m.group(2), params)
    ops = []
    cur, x, y, reg, poly = None, 0.0, 0.0, False, []
    for line in txt.splitlines():
        line = line.strip()
        if line.startswith("%") or line.startswith("G04"):
            continue
        if line.startswith("G36"):
            reg, poly = True, []
            continue
        if line.startswith("G37"):
            if len(poly) > 2:
                ops.append(("region", poly))
            reg = False
            continue
        m = re.match(r"(?:G54)?D(\d+)\*$", line)
        if m and int(m.group(1)) >= 10:
            cur = m.group(1)
            continue
        m = re.match(r"(?:G0[123])?(?:X(-?\d+))?(?:Y(-?\d+))?(?:I-?\d+)?(?:J-?\d+)?D0([123])\*", line)
        if not m:
            continue
        nx = int(m.group(1)) / 1e6 if m.group(1) else x
        ny = int(m.group(2)) / 1e6 if m.group(2) else y
        op = m.group(3)
        if reg:
            if op == "2":
                if len(poly) > 2:
                    ops.append(("region", poly))
                poly = [(nx, ny)]
            else:
                if not poly:
                    poly = [(x, y)]
                poly.append((nx, ny))
        elif op == "1" and cur in ap:
            nm, pr = ap[cur]
            w = pr[0] if nm == "C" else (min(pr[0], pr[1]) if nm in ("R", "O") else 0.1)
            ops.append(("trace", (x, y), (nx, ny), w))
        elif op == "3" and cur in ap:
            ops.append(("flash", (nx, ny), macro_poly(ap[cur][0], ap[cur][1], macros)))
        x, y = nx, ny
    return ops


layers = {k: parse(os.path.join(GD, "%s-%s" % (NAME, f))) for k, f in FILES.items()
          if os.path.isfile(os.path.join(GD, "%s-%s" % (NAME, f)))}
holes = []
tools, t, plated = {}, None, {}
pend = None
for line in open(os.path.join(GD, NAME + ".drl"), errors="replace"):
    line = line.strip()
    if "TA.AperFunction" in line:
        pend = "NonPlated" not in line
        continue
    m = re.match(r"T(\d+)C([\d.]+)", line)
    if m:
        tools[m.group(1)] = float(m.group(2))
        plated[m.group(1)] = pend if pend is not None else True
        continue
    m = re.match(r"T(\d+)$", line)
    if m:
        t = m.group(1)
        continue
    m = re.match(r"X(-?[\d.]+)Y(-?[\d.]+)", line)
    if m and t in tools and plated.get(t):
        holes.append((float(m.group(1)), float(m.group(2)), tools[t]))

xs, ys = [], []
for ops in layers.values():
    for o in ops:
        pts = o[1] if o[0] == "region" else [o[1]] + ([o[2]] if o[0] == "trace" else [])
        for p in pts:
            xs.append(p[0]); ys.append(p[1])
x0, x1, y0, y1 = min(xs) - 2, max(xs) + 2, min(ys) - 2, max(ys) + 2
W, H = int((x1 - x0) / RES) + 1, int((y1 - y0) / RES) + 1
px = lambda x, y: ((x - x0) / RES, (y1 - y) / RES)
print("%s: %d x %d px at %.3f mm, %d plated holes" % (NAME, W, H, RES, len(holes)), flush=True)

masks = {}
for k, ops in layers.items():
    im = Image.new("1", (W, H), 0)
    d = ImageDraw.Draw(im)
    for o in ops:
        if o[0] == "region":
            d.polygon([px(*p) for p in o[1]], fill=1)
        elif o[0] == "trace":
            (ax, ay), (bx, by), w = o[1], o[2], o[3]
            r = w / 2 / RES
            d.line([px(ax, ay), px(bx, by)], fill=1, width=max(1, int(round(w / RES))))
            for (cx, cy) in (px(ax, ay), px(bx, by)):
                d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=1)
        else:
            (fx, fy) = o[1]
            for sh in o[2]:
                if sh[0] == "circle":
                    cx, cy = px(fx + sh[1], fy + sh[2]); r = sh[3] / RES
                    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=1)
                elif sh[0] == "poly":
                    d.polygon([px(fx + a, fy + b) for a, b in sh[1]], fill=1)
                else:
                    (a, b), (c, e), w = sh[1], sh[2], sh[3]
                    d.line([px(fx + a, fy + b), px(fx + c, fy + e)], fill=1, width=max(1, int(round(w / RES))))
    # a drilled hole stays copper in the plane: its barrel is copper all round it (widepath)
    masks[k] = np.array(im, dtype=bool)
    print("  %s rasterised: %.1f %% copper" % (k, 100.0 * masks[k].mean()), flush=True)

hole_px = [(px(hx, hy)[0], px(hx, hy)[1], math.pi * hd * PLATING) for hx, hy, hd in holes]


def layerset(s):
    return re.findall(r"I1|I2|F|B", s)


if sys.argv[4] == "--specs":
    data = json.load(open(sys.argv[5], encoding="utf-8"))
    width = widepath.widths(masks, RES)
    for k, f in (data.get("scale") or {}).items():
        if k in width and f != 1.0:
            width[k] *= f            # inner copper as outer-equivalent width
    shape = next(iter(width.values())).shape
    # KiCad y runs down the board, gerber y up: a board point (x, y) is gerber (x, -y)
    gpx = lambda q: px(q[0], -q[1])
    open_is_fail = "--open-ok" not in sys.argv[6:]
    n = {"PASS": 0, "WARN": 0, "FAIL": 0, "OPEN": 0}
    for sp in data["specs"]:
        A = widepath.end_masks(shape, {k: [[gpx(q) for q in p] for p in ps] for k, ps in sp["a"].items()})
        B = widepath.end_masks(shape, {k: [[gpx(q) for q in p] for p in ps] for k, ps in sp["b"].items()})
        dn = sp.get("declared_neck")
        r = widepath.judge(width, hole_px, A, B, RES, sp["need"], open_is_fail=open_is_fail, declared=dn)
        n[r["verdict"]] += 1
        tag = ""
        if r.get("declared"):
            tag = "  declared neck (>= %.2f, <= %.2f mm): %s" % (dn["min_w"], dn["max_len"], dn["key"])
        elif r.get("declared_broken"):
            tag = "  DECLARED NECK BROKEN (wants >= %.2f wide, <= %.2f long): %s" % (dn["min_w"], dn["max_len"], dn["key"])
        print("%s %-44s %5.2f A  %.2f mm (wants %.2f)  neck %s%s" % (
            r["verdict"], sp["name"], sp["amps"], r["width"], sp["need"],
            "%.2f mm" % r["neck"] if r["neck"] != float("inf") else "-", tag), flush=True)
    print("rasterpath: %d FAIL, %s%d WARN, %d PASS of %d power paths"
          % (n["FAIL"], "" if open_is_fail else "%d OPEN, " % n["OPEN"], n["WARN"], n["PASS"],
             len(data["specs"])))
    sys.stdout.flush()
    os._exit(1 if n["FAIL"] else 0)

width = widepath.widths(masks, RES)
for spec in sys.argv[4:]:
    nm, ab, amps = spec.split(":")
    a, b = ab.split(">")
    la, pa = a.split("@"); lb, pb = b.split("@")
    pa, pb = tuple(map(float, pa.split(","))), tuple(map(float, pb.split(",")))
    A = {k: np.zeros(next(iter(width.values())).shape, bool) for k in layerset(la)}
    B = {k: np.zeros(next(iter(width.values())).shape, bool) for k in layerset(lb)}
    for E, p in ((A, pa), (B, pb)):
        cx, cy = px(*p)
        for k in E:
            E[k][int(round(cy)), int(round(cx))] = True
    print("== %s (%s A): bottleneck %.2f mm" % (nm, amps, widepath.bottleneck(width, hole_px, A, B, RES)), flush=True)
sys.stdout.flush()
os._exit(0)
