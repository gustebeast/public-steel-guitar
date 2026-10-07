"""Can the pickup piece slide OUT of the instrument? -- the whole way, not where it parks.

    py -3.12 -m tools.check_deck_slide            # report, exit = number of blockers
    py -3.12 -m tools.check_deck_slide --png f    # also write the section picture

WHY THIS EXISTS (user, 2026-10-07). The deck is a stack of panels that pull straight out
-X once the keyhead endplate and nut block are off, and the pickup piece is one of them.
Everything that hangs under it -- its skirt and end walls, the height plate, the jack
screws, the retention screw -- therefore travels the LENGTH of the body on its way in and
out, and has to clear everything it passes. check_overlaps compares parts where they
sit, and every fit this piece has was checked at its three parked positions; nothing
checked the road between them and the end of the instrument.

HOW. A part sliding along X sweeps the prism of its own YZ silhouette, so the question is
two-dimensional: does the piece's silhouette, seen down the X axis, cross the silhouette
of anything it passes? Both are rasterised from the parts' own tessellations on a
CELL grid. A fixed part only counts where it lies -X of the moving geometry that would
reach it (the piece's own span is taken in slabs, so its +X features are not held
against things beside its -X end).

What comes off BEFORE the piece does (OFF_FIRST) is listed, not hidden: if one of those
is not really removed first, it is a blocker this did not count.
"""
from __future__ import annotations

import argparse
import sys

import numpy as np

CELL = 0.1            # mm per raster cell
TESS = 0.05           # tessellation chord error
SLAB = 10.0           # the piece's own X span is walked in slabs this long
# an overlap thinner than this in Y or Z is two faces of a sliding fit meeting in the
# raster, not material in the way (a cell of tessellation error each side)
TOUCH = 0.25

MOVING = ("top_plate_0", "top_plate_color_0", "pickup", "pickup_zplate",
          "pickup_jack_screw_", "pickup_jack_insert_", "pickup_retention_")
# off the instrument before the pickup piece can move, and why
OFF_FIRST = {
    "top_plate_": "the deck panels -X of the piece: the stack comes out in order",
    "top_plate_color_": "...their colour layers",
    "keyhead_endplate": "caps the deck grooves' -X end; first thing off",
    "nut_wrap_rod": "the nut block, off with the keyhead endplate",
    "nut_slide_": "the nut block, off with the keyhead endplate",
    "string_": "strings are off before the nut block is",
    "ui_": "the UI station is built onto the mid panel and leaves with it (ui_panel.py)",
    "fret_pcb_": "the fret-light boards are screwed to the mid / keyhead panels",
    "fret_m4_": "...their screws and inserts",
    "fret_pogo_": "...and the pogo pins between them",
    "wire_pickup": "the pickup's own lead, unplugged and drawn out with it",
    "wire_ui": "LOOSE LEAD left in the body: unplugged from the UI board, push it down",
    "wire_fret_led": "LOOSE LEAD left in the body: unplugged from the fret board, push it down",
}
NEAR = 3.0            # report fixed things that pass within this of the piece


def _is(name, prefixes):
    return any(name == p or name.startswith(p) for p in prefixes)


def _tris(wp):
    """(n, 3, 3) triangle corners of everything in a Workplane / shape."""
    out = []
    for v in (wp.vals() if hasattr(wp, "vals") else [wp]):
        if not hasattr(v, "tessellate"):
            continue
        vs, ts = v.tessellate(TESS)
        if not ts:
            continue
        p = np.array([(q.x, q.y, q.z) for q in vs])
        out.append(p[np.array(ts)])
    return np.concatenate(out) if out else np.zeros((0, 3, 3))


class Grid(object):
    def __init__(self, y0, y1, z0, z1):
        self.y0, self.z0 = y0, z0
        self.ny = int(np.ceil((y1 - y0) / CELL)) + 1
        self.nz = int(np.ceil((z1 - z0) / CELL)) + 1

    def mask(self, tris):
        """Cells whose CENTRE lies in the YZ projection of any triangle."""
        m = np.zeros((self.ny, self.nz), dtype=bool)
        if not len(tris):
            return m
        y = (tris[:, :, 1] - self.y0) / CELL
        z = (tris[:, :, 2] - self.z0) / CELL
        ya = np.clip(np.floor(y.min(1)).astype(int), 0, self.ny - 1)
        yb = np.clip(np.ceil(y.max(1)).astype(int), 0, self.ny - 1)
        za = np.clip(np.floor(z.min(1)).astype(int), 0, self.nz - 1)
        zb = np.clip(np.ceil(z.max(1)).astype(int), 0, self.nz - 1)
        keep = (y.max(1) >= 0) & (y.min(1) <= self.ny) & (z.max(1) >= 0) & (z.min(1) <= self.nz)
        for i in np.nonzero(keep)[0]:
            (ay, by, cy), (az, bz, cz) = y[i], z[i]
            den = (bz - cz) * (ay - cy) + (cy - by) * (az - cz)
            if abs(den) < 1e-12:
                continue                      # edge-on to the view: no area
            gy, gz = np.mgrid[ya[i]:yb[i] + 1, za[i]:zb[i] + 1]
            py, pz = gy + 0.5, gz + 0.5
            u = ((bz - cz) * (py - cy) + (cy - by) * (pz - cz)) / den
            v = ((cz - az) * (py - cy) + (ay - cy) * (pz - cz)) / den
            m[ya[i]:yb[i] + 1, za[i]:zb[i] + 1] |= (u >= 0) & (v >= 0) & (u + v <= 1)
        return m

    def box(self, m):
        ys, zs = np.nonzero(m)
        return (self.y0 + ys.min() * CELL, self.y0 + (ys.max() + 1) * CELL,
                self.z0 + zs.min() * CELL, self.z0 + (zs.max() + 1) * CELL)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--png", help="write the section picture here")
    ap.add_argument("--extra", action="append", default=[], metavar="NAME:y0,y1,z0,z1",
                    help="a HYPOTHETICAL rectangle riding the piece's whole length, to "
                         "try a change before drawing it (repeatable)")
    a = ap.parse_args(argv)

    from src import build as B
    comps = [(c[0], c[1]) for c in B.collect_components()]
    mov = [(n, _tris(w)) for n, w in comps if _is(n, MOVING)]
    mov = [(n, t) for n, t in mov if len(t)]
    assert any(n == "top_plate_0" for n, _ in mov), "the pickup piece is not in the build"
    allm = np.concatenate([t for _, t in mov])
    x0, x1 = allm[:, :, 0].min(), allm[:, :, 0].max()
    for e in a.extra:
        nm, _, box = e.partition(":")
        ya, yb, za, zb = (float(v) for v in box.split(","))
        q = [(x1, ya, za), (x1, yb, za), (x1, yb, zb), (x1, ya, zb)]
        mov.append(("HYPOTHETICAL " + nm, np.array([[q[0], q[1], q[2]], [q[0], q[2], q[3]]])))
    allm = np.concatenate([t for _, t in mov])
    g = Grid(allm[:, :, 1].min() - 1, allm[:, :, 1].max() + 1,
             allm[:, :, 2].min() - 1, allm[:, :, 2].max() + 1)
    print("pickup piece: %d parts, x %.1f..%.1f, y %.1f..%.1f, z %.1f..%.1f; it leaves -X"
          % (len(mov), x1, x0, g.y0 + 1, g.y0 + g.ny * CELL - 1, g.z0 + 1, g.z0 + g.nz * CELL - 1))

    # the moving silhouette that can reach a fixed thing at x: everything +X of it
    edges = list(np.arange(x0, x1, SLAB)) + [x1]
    masks = {}                                # slab start -> {moving part: mask}

    def moving_at(xa):
        if xa not in masks:
            masks[xa] = {n: g.mask(t[t[:, :, 0].max(1) >= xa]) for n, t in mov}
        return masks[xa]

    from scipy import ndimage
    dist = {}                                 # slab start -> mm from each cell to the piece

    def gap_at(xa):
        if xa not in dist:
            tot = np.zeros((g.ny, g.nz), dtype=bool)
            for n_, d in moving_at(xa).items():
                if not n_.startswith("HYPOTHETICAL"):
                    tot |= d
            dist[xa] = ndimage.distance_transform_edt(~tot) * CELL
        return dist[xa]

    skipped, found, near = {}, [], {}
    for n, w in comps:
        if _is(n, MOVING):
            continue
        t = _tris(w)
        t = t[t[:, :, 0].min(1) < x1] if len(t) else t
        if not len(t):
            continue
        hits = {}
        zones = [(-1e9, x0)] + list(zip(edges[:-1], edges[1:]))
        for xa, xb in zones:
            sel = t[(t[:, :, 0].min(1) < xb) & (t[:, :, 0].max(1) >= xa)]
            if not len(sel):
                continue
            fm = g.mask(sel)
            if not fm.any():
                continue
            gp = gap_at(max(xa, x0))[fm].min()
            if gp < NEAR:
                ys, zs = np.nonzero(fm & (gap_at(max(xa, x0)) <= gp + CELL))
                near[n] = min(near.get(n, (9e9,)), (gp, g.y0 + ys.mean() * CELL, g.z0 + zs.mean() * CELL))
            for mn, mm in moving_at(max(xa, x0)).items():
                o = fm & mm
                if o.any():
                    hits[mn] = hits.get(mn, np.zeros_like(o)) | o
        for mn, o in hits.items():
            ya, yb, za, zb = g.box(o)
            if min(yb - ya, zb - za) <= TOUCH:
                continue
            row = (n, mn, o.sum() * CELL * CELL, ya, yb, za, zb, o)
            why = next((r for p, r in OFF_FIRST.items() if n == p or n.startswith(p)), None)
            if why:
                skipped.setdefault(n, why)
            else:
                found.append(row)

    found.sort(key=lambda r: -r[2])
    print("\n== IN THE WAY (%d pairs) ==" % len(found))
    for n, mn, area, ya, yb, za, zb, _ in found:
        print("  %-26s x %-24s %7.2f mm2   y %7.2f..%7.2f   z %6.2f..%6.2f"
              % (n, mn, area, ya, yb, za, zb))
    if not found:
        print("  nothing: the piece's silhouette clears everything it passes")
    print("\n== CLOSEST FIXED THINGS (within %.1f of the piece as drawn) ==" % NEAR)
    for n, (gp, y, z) in sorted(near.items(), key=lambda kv: kv[1]):
        if gp > 0 and not any(n == p or n.startswith(p) for p in OFF_FIRST):
            print("  %-26s %5.2f mm clear   near y %7.2f z %6.2f" % (n, gp, y, z))
    print("\n== counted as OFF FIRST (not blockers only if that is true) ==")
    for n in sorted(skipped):
        print("  %-26s %s" % (n, skipped[n]))

    if a.png:
        try:
            from PIL import Image
        except ImportError:
            print("no PIL: --png skipped")
        else:
            img = np.full((g.nz, g.ny, 3), 255, dtype=np.uint8)
            mm = np.zeros((g.ny, g.nz), dtype=bool)
            for d in moving_at(x0).values():
                mm |= d
            img[mm.T] = (150, 170, 200)
            for r in found:
                img[r[7].T] = (220, 40, 40)
            Image.fromarray(img[::-1]).save(a.png)
            print("wrote", a.png)
    return len(found)


if __name__ == "__main__":
    sys.exit(min(main(), 250))
