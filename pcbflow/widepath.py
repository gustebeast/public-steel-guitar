"""widepath.py -- the widest-path core shared by rasterpath.py (the pre-order gate, on gerbers)
and close_last.py (CLOSE_POUR_GUARD=2, on the board being closed).

ONE implementation, so the gate and the guard cannot disagree about what "carries the current"
means (lead, 2026-11-20). Callers rasterise copper onto a grid of RES mm per layer and hand
this module boolean masks, the plated holes, and the two ENDS of each path, all in pixels.

THE MODEL
  width at a pixel  = 2 x distance to the nearest non-copper pixel (EDT) x RES. A drilled hole
                      stays copper in the plane (its barrel is copper all round it).
  ends              = every pad of the part on the net, not one pin's centre: the current
                      splits over a USB-C socket's four VBUS pins or a FET's four drain pins,
                      and a 0.3 mm pin is not the path's width. End pixels count as infinitely
                      wide, so the path is measured from the pad's EDGE.
  via fields        = plated holes joining the same two pieces of copper ADD: the pieces join
                      at t when the barrels between them sum to >= t (a hole of d carries
                      pi*d*25/35 mm, quality's derating). One 0.3 mm via is 0.67 mm; eight in
                      a field are 5.4.
  bottleneck        = the largest t at which the ends are joined (binary search, flood fill).
  neck length       = along the best path, the least total length of copper narrower than the
                      current needs (0-cost wide pixels, csgraph Dijkstra; a via field under
                      the need counts as a 1.6 mm neck -- its barrel is the board's thickness).

THE VERDICT (lead, 2026-11-20). IPC-2221 width is a heating proxy for a LONG track: a neck
shorter than about twice its own width inside a wide pour spreads its heat sideways and does
not run at the IPC temperature (R1 pi_cap's 1.0 mm neck in a 2.2 mm path). So:
  PASS  bottleneck >= need
  WARN  under need, but the narrow copper is no longer than NECK_RATIO x the bottleneck
  FAIL  under need and longer than that
If that rule proves wrong either way, the next model is path resistance (a Laplace solve for
drop and I^2R on a coarse local grid) -- held in reserve, not built.

CLI (KiCad's python has numpy and PIL but no scipy):
    py -3.12 widepath.py IN.npz OUT.json
IN.npz: res, layers, mask_<layer> (bool HxW), holes (N x 3: cx, cy, barrel_mm), specs (JSON:
[{name, need, a: {layer: [[x, y], ...polygon px...], ...}, b: {...}}, ...]).
OUT.json: {name: {width, neck, verdict}}.
"""
import json
import sys

import numpy as np

PLATING = 25.0 / 35.0          # quality's barrel derating: a hole of d carries pi*d*PLATING mm
NECK_RATIO = 2.0               # FAIL only a neck longer than this x its own width
VIA_LEN = 1.6                  # mm: a via field under the need is a neck this long
INF_W = 1e3


def widths(masks, res):
    """{layer: bool mask} -> {layer: float32 width map in mm}."""
    from scipy import ndimage   # lazily: KiCad's python imports this module and has no scipy
    return {k: (2.0 * ndimage.distance_transform_edt(m) * res).astype(np.float32)
            for k, m in masks.items()}


def end_masks(shape, end):
    """{layer: [polygon px]} -> {layer: bool mask} of the end's pads."""
    from PIL import Image, ImageDraw
    H, W = shape
    out = {}
    for k, polys in end.items():
        im = Image.new("1", (W, H), 0)
        d = ImageDraw.Draw(im)
        for p in polys:
            if len(p) >= 3:
                d.polygon([tuple(q) for q in p], fill=1)
            elif len(p) == 1:
                d.point(tuple(p[0]), fill=1)
        out[k] = np.array(im, dtype=bool)
    return out


class _UF:
    def __init__(self):
        self.up = {}

    def f(self, a):
        up = self.up
        up.setdefault(a, a)
        while up[a] != a:
            up[a] = up[up[a]]
            a = up[a]
        return a

    def u(self, a, b):
        self.up[self.f(a)] = self.f(b)


def _fields(lab, holes):
    """{(piece_a, piece_b): summed barrel} over the holes joining two pieces of copper."""
    sums = {}
    for (cx, cy, barrel) in holes:
        cx, cy = int(round(cx)), int(round(cy))
        on = []
        for k, L in lab.items():
            if 0 <= cy < L.shape[0] and 0 <= cx < L.shape[1] and L[cy, cx]:
                on.append((k, int(L[cy, cx])))
        for i in range(len(on)):
            for j in range(i + 1, len(on)):
                key = (on[i], on[j]) if on[i] < on[j] else (on[j], on[i])
                sums[key] = sums.get(key, 0.0) + barrel
    return sums


def joined(t, width, holes, A, B):
    """Are the ends A and B ({layer: bool mask}) linked through copper of width >= t?"""
    from scipy import ndimage
    lab = {k: ndimage.label(w >= t)[0] for k, w in width.items()}
    uf = _UF()
    for (a, b), s in _fields(lab, holes).items():
        if s >= t:
            uf.u(a, b)

    def seeds(E):
        out = set()
        for k, m in E.items():
            if k in lab:
                for v in np.unique(lab[k][m]):
                    if v:
                        out.add(uf.f((k, int(v))))
        return out
    return bool(seeds(A) & seeds(B))


def bottleneck(width, holes, A, B, res, hi=12.0):
    """The widest t (mm) at which A and B are joined, to within res/2; 0.0 if never."""
    if not joined(res, width, holes, A, B):
        return 0.0
    lo = res
    while hi - lo > res / 2:
        mid = (lo + hi) / 2
        if joined(mid, width, holes, A, B):
            lo = mid
        else:
            hi = mid
    return lo


NECK_MAX_PX = 2_000_000          # over this, the neck search runs on a 2x coarser grid


def neck_length(width, holes, A, B, res, t, need):
    """Least total length (mm) of copper narrower than `need` on any path of width >= t.

    A long pour is millions of pixels, and the graph over them is what peaked the gate at
    9.7 GB: over NECK_MAX_PX the search runs on every second pixel (widths by max-pooling,
    so a neck is never made to look narrower than it is), lengths scaled to match."""
    n_px = sum(int((w >= t).sum()) for w in width.values())
    if n_px > NECK_MAX_PX:
        def pool(a, fn):
            H, W = a.shape
            a = a[:H - H % 2, :W - W % 2]
            return fn(fn(a[0::2, 0::2], a[1::2, 0::2]), fn(a[0::2, 1::2], a[1::2, 1::2]))
        width = {k: pool(w, np.maximum) for k, w in width.items()}
        A = {k: pool(m, np.logical_or) for k, m in A.items()}
        B = {k: pool(m, np.logical_or) for k, m in B.items()}
        holes = [(cx / 2.0, cy / 2.0, b) for (cx, cy, b) in holes]
        res = res * 2.0
    from scipy import ndimage
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import dijkstra
    lab = {k: ndimage.label(w >= t)[0] for k, w in width.items()}
    # keep only the pieces reachable from A (crop the problem to them)
    uf = _UF()
    fields = _fields(lab, holes)
    for (a, b), s in fields.items():
        if s >= t:
            uf.u(a, b)
    roots = set()
    for k, m in A.items():
        if k in lab:
            roots |= {uf.f((k, int(v))) for v in np.unique(lab[k][m]) if v}
    keep = {k: np.isin(lab[k], [v for v in range(1, int(lab[k].max()) + 1)
                                if uf.f((k, v)) in roots]) for k in lab}
    base, idx, cost = 0, {}, {}
    for k, m in keep.items():
        n = int(m.sum())
        ix = np.full(m.shape, -1, dtype=np.int32)
        ix[m] = np.arange(base, base + n, dtype=np.int32)
        idx[k] = ix
        cost[k] = np.where(width[k] < need, res, 1e-6 * res).astype(np.float32)
        base += n
    if base == 0:
        return float("inf")
    rows, cols, ws = [], [], []
    for k, ix in idx.items():
        c = cost[k]
        for sl_a, sl_b in (((slice(None), slice(None, -1)), (slice(None), slice(1, None))),
                           ((slice(None, -1), slice(None)), (slice(1, None), slice(None)))):
            a, b = ix[sl_a], ix[sl_b]
            ok = (a >= 0) & (b >= 0)
            ca, cb = c[sl_a][ok], c[sl_b][ok]
            a, b = a[ok], b[ok]
            rows += [a, b]
            cols += [b, a]
            ws += [cb, ca]
    for (pa, pb), s in fields.items():
        if s < t or uf.f(pa) not in roots:
            continue
        # every hole of the field joins its two pieces; one edge per hole is enough
        for (cx, cy, _b) in holes:
            cx, cy = int(round(cx)), int(round(cy))
            if not (0 <= cy < lab[pa[0]].shape[0] and 0 <= cx < lab[pa[0]].shape[1]):
                continue
            ia = idx[pa[0]][cy, cx] if lab[pa[0]][cy, cx] == pa[1] else -1
            ib = idx[pb[0]][cy, cx] if lab[pb[0]][cy, cx] == pb[1] else -1
            if ia >= 0 and ib >= 0:
                w = VIA_LEN if s < need else 1e-6
                rows += [np.array([ia, ib], np.int32)]
                cols += [np.array([ib, ia], np.int32)]
                ws += [np.array([w, w], np.float32)]
    src = np.concatenate([idx[k][m & (idx[k] >= 0)] for k, m in A.items() if k in idx] or [np.zeros(0, np.int32)])
    dst = np.concatenate([idx[k][m & (idx[k] >= 0)] for k, m in B.items() if k in idx] or [np.zeros(0, np.int32)])
    if not len(src) or not len(dst):
        return float("inf")
    # one super-source joined to every A pixel at (almost) zero cost
    S = base
    rows.append(np.full(len(src), S, dtype=np.int32))
    cols.append(src.astype(np.int32))
    ws.append(np.full(len(src), 1e-9, dtype=np.float32))
    g = coo_matrix((np.concatenate(ws), (np.concatenate(rows), np.concatenate(cols))),
                   shape=(base + 1, base + 1)).tocsr()
    d = dijkstra(g, indices=S)
    return float(np.min(d[dst]))


def _crop(width, holes, A, B, res):
    """Everything judge needs, cut down to the copper joined to A at the lowest threshold.

    ⚠ THE WHOLE BOARD FOR EVERY PATH COST 9.8 GB (brain_board ws1 gate, 2026-11-20): 4 layers at
    6846 x 4136 px, labelled again at every step of every path's binary search, and the neck
    search built its graph over whole pours. A path lives in the copper its ends touch, so the
    arrays are cut to that copper's bounding box (all layers, joined through holes) first."""
    from scipy import ndimage
    lab = {k: ndimage.label(w >= res)[0] for k, w in width.items()}
    uf = _UF()
    for (a, b), s in _fields(lab, holes).items():
        if s >= res:
            uf.u(a, b)
    roots = set()
    for k, m in A.items():
        if k in lab:
            roots |= {uf.f((k, int(v))) for v in np.unique(lab[k][m]) if v}
    y0 = x0 = 10 ** 9
    y1 = x1 = -1
    for k, L in lab.items():
        ids = [v for v in range(1, int(L.max()) + 1) if uf.f((k, v)) in roots]
        if not ids:
            continue
        ys, xs = np.nonzero(np.isin(L, ids))
        y0, y1 = min(y0, int(ys.min())), max(y1, int(ys.max()))
        x0, x1 = min(x0, int(xs.min())), max(x1, int(xs.max()))
    del lab
    if y1 < 0:
        return width, holes, A, B
    H, W = next(iter(width.values())).shape
    y0, x0, y1, x1 = max(0, y0 - 2), max(0, x0 - 2), min(H, y1 + 3), min(W, x1 + 3)
    sl = (slice(y0, y1), slice(x0, x1))
    cw = {k: w[sl].copy() for k, w in width.items()}
    ch = [(cx - x0, cy - y0, b) for (cx, cy, b) in holes
          if x0 <= int(round(cx)) < x1 and y0 <= int(round(cy)) < y1]
    return cw, ch, {k: m[sl] for k, m in A.items()}, {k: m[sl] for k, m in B.items()}


def judge(width, holes, A, B, res, need, open_is_fail=True, declared=None):
    """{width, neck, verdict} for one path. A, B: {layer: bool mask} of the end pads.

    open_is_fail: a path with NO copper between its ends is FAIL (the pre-order gate: a power
    net still open at order time blocks the order) or OPEN (finish's pre-close gate,
    PCBFLOW_POWER_GATE: an unrouted net is close_last's to close, and the final gate judges it)."""
    # the ends count as infinitely wide: the path is measured from the pads' edges
    saved = {}
    for E in (A, B):
        for k, m in E.items():
            if k in width:
                saved.setdefault(k, width[k].copy())
                width[k][m] = INF_W
    try:
        cw, ch, cA, cB = _crop(width, holes, A, B, res)
    finally:
        for k, a in saved.items():
            width[k] = a
    w = bottleneck(cw, ch, cA, cB, res)
    if w <= 0.0:
        return dict(width=0.0, neck=float("inf"), verdict="FAIL" if open_is_fail else "OPEN")
    if w >= need:
        return dict(width=w, neck=0.0, verdict="PASS")
    n = neck_length(cw, ch, cA, cB, res, w, need)
    v = "FAIL" if n > NECK_RATIO * w else "WARN"
    # ⚠ A DECLARED NECK IS A CHECKED FACT, NOT AN EXEMPT (lead 2026-11-22, brain_board U205 VIN_CM5):
    # a part's pinout can bound the copper (SLVSGT7 puts FSW5 between VIN and its HF cap: 0.49 mm for
    # ~1.3 mm). The intent declares the neck's floor width and ceiling length; the path is WARN only
    # while the measured copper is no narrower AND no longer -- routing or fill that makes it worse FAILs.
    if v == "FAIL" and declared:
        if w >= float(declared["min_w"]) - 1e-6 and n <= float(declared["max_len"]) + 1e-6:
            return dict(width=w, neck=n, verdict="WARN", declared=declared.get("key", "declared"))
        return dict(width=w, neck=n, verdict="FAIL", declared_broken=declared.get("key", "declared"))
    return dict(width=w, neck=n, verdict=v)


def _cli(inp, outp):
    z = np.load(inp, allow_pickle=False)
    res = float(z["res"])
    names = [str(s) for s in z["layers"]]
    width = widths({k: z["mask_" + k] for k in names}, res)
    if "scale" in z.files:                 # inner copper as outer-equivalent width
        for k, f in json.loads(str(z["scale"])).items():
            if k in width and f != 1.0:
                width[k] *= f
    holes = [tuple(h) for h in z["holes"].tolist()]
    shape = width[names[0]].shape
    out = {}
    for sp in json.loads(str(z["specs"])):
        A, B = end_masks(shape, sp["a"]), end_masks(shape, sp["b"])
        out[sp["name"]] = judge(width, holes, A, B, res, float(sp["need"]))
    json.dump(out, open(outp, "w"))


if __name__ == "__main__":
    _cli(sys.argv[1], sys.argv[2])
