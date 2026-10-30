"""Where the real slicer's beads differ from the model: the slicer is the oracle, not a rule.

    py -3.12 -m cadkit.slicer_check part.step --up 0,0,1
    py -3.12 -m cadkit.slicer_check --test

A part in its print pose goes to the slicer, the G-code comes back as beads, and every layer's
beads are measured against the same layer of the same mesh:

    MISSING  model outline no bead reaches: by how far the outline stands off the beads
    EXCESS   bead standing outside the model: by how far
    ZSTEP    a flat face between layers: by how far the nearest layer boundary misses it

A site is a connected run of one kind over MIN_ERR, ranked by the volume of the error. A sharp
square corner under a 0.82 bead is 0.17 by geometry alone, which is why MIN_ERR sits over it.
Nothing here decides what to change: it says what the slicer laid.

THE SLICER IS RUN, NEVER LINKED OR REIMPLEMENTED. Bambu Studio's command line runs headless with
its own --datadir (a folder of ours, so it shares no config with an open window) and a run that
changes the set of open windows raises. The user's presets are read, flattened through their
`inherits` chain and written to that folder. Their files are not touched.

Needs Bambu Studio installed; numpy, scipy and trimesh only.
"""

import argparse
import json
import math
import os
import pathlib
import re
import subprocess
import tempfile

import numpy as np

SLICER = pathlib.Path(r"C:/Program Files/Bambu Studio")
PRINTER = "Bambu Lab X2D 0.8 nozzle"
PROCESS = "0.40mm PETG GF"
FILAMENT = "Tinmorry PETG GF @Bambu Lab X2D 0.8 nozzle"
BED = "Textured PEI Plate"
BED_CENTRE = np.array([128.0, 128.0])

MIN_ERR = 0.20           # an error smaller than this is not a site (a square corner is 0.17)
STEP = 0.10              # bead and outline sample spacing
ZSTEP_MIN = 0.05         # a flat face this far off a layer boundary is reported
VOXEL = 0.5              # samples this close are one site
NOT_MODEL = ("Custom", "Support", "Brim", "Skirt", "Prime tower", "Wipe")


# ── the slicer ───────────────────────────────────────────────────────────────
def _windows():
    """The slicers running without a --datadir of ours: the user's. Parallel runs of this
    tool are not a fault; another window is."""
    ps = ("Get-CimInstance Win32_Process -Filter \"name='bambu-studio.exe'\" | "
          "Where-Object { $_.CommandLine -notmatch '--datadir' } | "
          "ForEach-Object { $_.ProcessId }")
    out = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                         capture_output=True, text=True).stdout
    return set(out.split())


def _load(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def _flatten(index, kind, j):
    inh = j.get("inherits") or ""
    base = _flatten(index, kind, _load(index[kind, inh])) if inh else {}
    base.update(j)
    return base


def presets(work, printer=PRINTER, process=PROCESS, filament=FILAMENT):
    """(machine, process, filament) as flat .json in `work`, read from the install and the
    user's own presets. Returns the paths."""
    work = pathlib.Path(work)
    work.mkdir(parents=True, exist_ok=True)
    index = {}
    roots = [SLICER / "resources" / "profiles" / "BBL"]
    user = pathlib.Path(os.environ["APPDATA"]) / "BambuStudio" / "user"
    if user.exists():
        roots += [d for d in user.iterdir() if d.is_dir()]
    for root in roots:
        for kind in ("machine", "process", "filament"):
            for p in (root / kind).rglob("*.json"):
                try:
                    name = _load(p).get("name")
                except (ValueError, OSError):
                    continue
                if name:
                    index[kind, name] = p
    out = []
    for kind, name in (("machine", printer), ("process", process), ("filament", filament)):
        j = _flatten(index, kind, _load(index[kind, name]))
        j.update(inherits="", type=kind)
        j["from"] = "system" if kind == "machine" else "User"
        p = work / (kind + ".json")
        p.write_text(json.dumps(j, indent=1), encoding="utf-8")
        out.append(p)
    return out


def run_slicer(stl, work, settings):
    """The G-code text for an STL, sliced headless with `settings` from presets()."""
    work = pathlib.Path(work)
    out = work / "out"
    data = work / "datadir"
    data.mkdir(parents=True, exist_ok=True)
    before = _windows()
    r = subprocess.run([str(SLICER / "bambu-studio.exe"), "--datadir", str(data),
                        "--load-settings", "%s;%s" % (settings[0], settings[1]),
                        "--load-filaments", str(settings[2]), "--curr-bed-type", BED,
                        "--arrange", "0", "--orient", "0", "--slice", "1",
                        "--outputdir", str(out), str(stl)], cwd=str(work),
                       capture_output=True, text=True)
    if _windows() != before:
        raise RuntimeError("the set of open slicer windows changed during a slice")
    gcode = out / "plate_1.gcode"
    if r.returncode or not gcode.exists():
        res = out / "result.json"
        why = _load(res).get("error_string") if res.exists() else "no result"
        raise RuntimeError("slicer exit %s: %s" % (r.returncode, why))
    return gcode.read_text(encoding="utf-8", errors="replace")


# ── the G-code ───────────────────────────────────────────────────────────────
def parse_gcode(text):
    """[{z (mid-layer), h, seg (n, 4) x0 y0 x1 y1, w (n), wall (n) bool}] of what prints as
    the part. A bead's width comes from its extrusion, not the LINE_WIDTH comment: Arachne
    varies it, and the area is a stadium, (w - h) h + pi h^2 / 4."""
    flow = float(re.search(r"; filament_flow_ratio = ([\d.]+)", text).group(1))
    dia = float(re.search(r"; filament_diameter = ([\d.]+)", text).group(1))
    area = math.pi * dia * dia / 4.0
    layers, cur, feat, x, y, h, z = [], None, "", None, None, None, None
    num = re.compile(r"([XYE])(-?[\d.]+)")
    for line in text.splitlines():
        if line.startswith("; Z_HEIGHT:"):
            z = float(line.split(":")[1])
        elif line.startswith("; LAYER_HEIGHT:"):
            h = float(line.split(":")[1])
            cur = {"z": z - h / 2.0, "h": h, "seg": [], "w": [], "wall": []}
            layers.append(cur)
        elif line.startswith("; FEATURE:"):
            feat = line.split(":")[1].strip()
        elif line.startswith(("G1 ", "G0 ")):
            f = dict((k, float(v)) for k, v in num.findall(line))
            nx, ny = f.get("X", x), f.get("Y", y)
            e = f.get("E", 0.0)
            if (cur is not None and e > 0.0 and x is not None and ("X" in f or "Y" in f)
                    and not feat.startswith(NOT_MODEL)):
                ln = math.hypot(nx - x, ny - y)
                if ln > 1e-6:
                    w = (e * area / flow) / (ln * cur["h"]) + cur["h"] * (1.0 - math.pi / 4.0)
                    cur["seg"].append((x, y, nx, ny))
                    cur["w"].append(w)
                    cur["wall"].append("wall" in feat.lower())
            x, y = nx, ny
    # ONE LAYER CAN COME IN SEVERAL PASSES (islands printed apart, each with its own header) and
    # a bridge has a pass at its own height between layers. Passes on one z are one layer, and
    # an in-between pass belongs to the layer it prints in.
    nom = sorted(c["h"] for c in layers)[len(layers) // 2]
    tops = sorted({round(c["z"] + c["h"] / 2.0, 3) for c in layers
                   if abs(c["h"] - nom) < 0.01})
    if tops and tops[0] > nom + 0.01:
        tops.insert(0, round(tops[0] - nom, 3))
    merged = {}
    for c in layers:
        top = c["z"] + c["h"] / 2.0
        key = next((t for t in tops if t >= top - 0.01), tops[-1])
        m = merged.setdefault(key, {"z": key - nom / 2.0, "h": nom, "seg": [], "w": [], "wall": []})
        for k in ("seg", "w", "wall"):
            m[k] += c[k]
    out = []
    for key in sorted(merged):
        c = merged[key]
        if any(c["wall"]):
            out.append({"z": c["z"], "h": c["h"], "seg": np.array(c["seg"]),
                        "w": np.array(c["w"]), "wall": np.array(c["wall"])})
    return out


def _sample(seg, step=STEP):
    """Points along segments, and which segment each came from."""
    d = seg[:, 2:] - seg[:, :2]
    n = np.maximum(np.ceil(np.hypot(*d.T) / step).astype(int), 1)
    i = np.repeat(np.arange(len(seg)), n)
    t = (np.concatenate([np.arange(k) for k in n]) + 0.5) / n[i]
    return seg[i, :2] + d[i] * t[:, None], i


# ── the model ────────────────────────────────────────────────────────────────
def section(V, F, FN, z):
    """A layer's outline: segments (n, 4) and each one's outward normal in the layer."""
    t = V[F]
    a = t[:, :, 2] - z
    a = np.where(a == 0.0, 1e-9, a)
    s = a > 0
    hit = np.flatnonzero(s.any(axis=1) & ~s.all(axis=1))
    if not len(hit):
        return np.empty((0, 4)), np.empty((0, 2))
    t, a, s = t[hit], a[hit], s[hit]
    # the vertex alone on its side of the plane, and the two edges out of it
    lone = np.where(s.sum(axis=1) == 1, s.argmax(axis=1), (~s).argmax(axis=1))
    k = np.arange(len(hit))
    p0, p1, p2 = t[k, lone], t[k, (lone + 1) % 3], t[k, (lone + 2) % 3]
    a0, a1, a2 = a[k, lone], a[k, (lone + 1) % 3], a[k, (lone + 2) % 3]
    q1 = p0 + (p1 - p0) * (a0 / (a0 - a1))[:, None]
    q2 = p0 + (p2 - p0) * (a0 / (a0 - a2))[:, None]
    n = FN[hit, :2]
    ln = np.maximum(np.hypot(*n.T), 1e-9)
    return np.hstack([q1[:, :2], q2[:, :2]]), n / ln[:, None]


def align(layers, V, F, FN):
    """The (dx, dy) that puts the G-code on the model: the bounding boxes first, then the outer
    edge of the walls onto the outline. The slicer places a part where it likes."""
    from scipy.spatial import cKDTree
    lo = np.array([min(c["seg"][:, [0, 2]].min() for c in layers),
                   min(c["seg"][:, [1, 3]].min() for c in layers)])
    hi = np.array([max(c["seg"][:, [0, 2]].max() for c in layers),
                   max(c["seg"][:, [1, 3]].max() for c in layers)])
    off = (V[:, :2].min(axis=0) + V[:, :2].max(axis=0) - lo - hi) / 2.0
    pick = layers[1:] or layers
    pick = pick[:: max(1, len(pick) // 6)]
    for _ in range(4):
        moves = []
        for c in pick:
            seg, nrm = section(V, F, FN, c["z"])
            if not len(seg) or not c["wall"].any():
                continue
            b, bi = _sample(seg, 0.5)
            p, i = _sample(c["seg"][c["wall"]], 0.5)
            w = c["w"][c["wall"]][i]
            p = p + off
            d, j = cKDTree(b).query(p)
            near = d < w * 0.75                       # a wall hugging the outline
            moves.append((b[j] - nrm[bi[j]] * (w / 2.0)[:, None] - p)[near])
        if not moves:
            break
        off = off + np.median(np.vstack(moves), axis=0)
    return off


def _normals(V, F):
    t = V[F]
    n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    return n / np.maximum(np.linalg.norm(n, axis=1), 1e-12)[:, None]


def measure(V, F, layers):
    """(samples (n, 6) kind x y z err dvol, the alignment), for a mesh in print pose."""
    from scipy.spatial import cKDTree
    FN = _normals(V, F)
    off = align(layers, V, F, FN)
    out = []
    for c in layers:
        seg, nrm = section(V, F, FN, c["z"])
        if not len(seg):
            continue
        b, bi = _sample(seg)
        n = nrm[bi]
        p, i = _sample(c["seg"])
        p = p + off
        w = c["w"][i]
        # MISSING: how far past the nearest bead's edge the outline stands. Across the few
        # nearest samples, because the widest bead need not have the nearest centre.
        d, j = cKDTree(p).query(b, k=min(6, len(p)))
        d, j = d.reshape(len(b), -1), j.reshape(len(b), -1)
        err = (d - w[j] / 2.0).min(axis=1)
        keep = err > MIN_ERR
        out.append(np.column_stack([np.full(keep.sum(), 0.0), b[keep], np.full(keep.sum(), c["z"]),
                                    err[keep], err[keep] * STEP * c["h"]]))
        # EXCESS: how far a bead's edge stands outside the outline
        d, j = cKDTree(b).query(p)
        outside = ((p - b[j]) * n[j]).sum(axis=1) > 0.0
        err = np.where(outside, w / 2.0 + d, w / 2.0 - d)
        keep = err > MIN_ERR
        out.append(np.column_stack([np.full(keep.sum(), 1.0), p[keep], np.full(keep.sum(), c["z"]),
                                    err[keep], err[keep] * STEP * c["h"]]))
    return (np.vstack(out) if out else np.empty((0, 6))), off


def z_steps(V, F, layers):
    """[site] for flat faces between layers: what the layer stack does to a shelf's height."""
    n = _normals(V, F)
    t = V[F]
    area = np.linalg.norm(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]), axis=1) / 2.0
    flat = np.abs(n[:, 2]) > 0.999
    edges = np.array(sorted({0.0} | {round(c["z"] + c["h"] / 2.0, 4) for c in layers}))
    sites = []
    tf, af = t[flat], area[flat]
    z = np.round(tf[:, :, 2].mean(axis=1), 3)
    for v in np.unique(z):
        off = np.abs(edges - v).min()
        if off >= ZSTEP_MIN and v > V[:, 2].min() + 1e-6:
            on = z == v
            a = af[on].sum()
            sites.append({"kind": "ZSTEP", "err": float(off), "max": float(off),
                          "vol": float(a * off), "z0": float(v), "z1": float(v), "layers": 1,
                          "long": math.sqrt(a),
                          "at": tuple(float(k) for k in tf[on].reshape(-1, 3).mean(axis=0))})
    return sites


def sites_of(samples):
    """Connected runs of one kind."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    from scipy.spatial import cKDTree
    sites = []
    for kind, name in ((0.0, "MISSING"), (1.0, "EXCESS")):
        s = samples[samples[:, 0] == kind]
        if not len(s):
            continue
        key, inv = np.unique(np.floor(s[:, 1:4] / VOXEL).astype(np.int64), axis=0,
                             return_inverse=True)
        inv = inv.ravel()
        pairs = cKDTree(key).query_pairs(1.8, output_type="ndarray")
        g = coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])),
                       shape=(len(key), len(key)))
        _, lab = connected_components(g, directed=False)
        lab = lab[inv]
        for k in np.unique(lab):
            q = s[lab == k]
            sites.append({"kind": name, "err": float(np.median(q[:, 4])),
                          "max": float(q[:, 4].max()), "vol": float(q[:, 5].sum()),
                          "z0": float(q[:, 3].min()), "z1": float(q[:, 3].max()),
                          "layers": len(np.unique(q[:, 3])),
                          "long": float(np.linalg.norm(q[:, 1:4].max(axis=0) - q[:, 1:4].min(axis=0))),
                          "at": tuple(float(v) for v in q[:, 1:4].mean(axis=0))})
    return sites


# ── a part ───────────────────────────────────────────────────────────────────
def _rot_to_z(up):
    u = np.asarray(up, float)
    u = u / np.linalg.norm(u)
    z = np.array([0.0, 0.0, 1.0])
    v = np.cross(u, z)
    s, c = np.linalg.norm(v), float(u @ z)
    if s < 1e-12:
        return np.eye(3) if c > 0 else np.diag([1.0, -1.0, -1.0])
    k = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]]) / s
    return np.eye(3) + k * s + k @ k * (1 - c)


def mesh_of(shape, tol=0.01, ang=0.1):
    v, f = shape.tessellate(tol, ang)
    return np.array([p.toTuple() for p in v]), np.array(f)


def check(V, F, up=(0, 0, 1), work=None, settings=None):
    """(sites, layers, stats) for a mesh in any pose, printing along `up`, largest error volume
    first. A site's `at` is in the frame the mesh came in, so it can be found on the part."""
    import trimesh
    R = _rot_to_z(up)
    B = np.asarray(V) @ R.T
    b0 = B[:, 2].min()
    B = B - (0.0, 0.0, b0)
    work = pathlib.Path(work or tempfile.mkdtemp(prefix="slicer_check")).resolve()
    work.mkdir(parents=True, exist_ok=True)
    settings = settings or presets(work / "presets")
    stl = work / "part.stl"
    # on the bed, where --arrange 0 leaves it: that switch is what guarantees it is not turned
    bed = (BED_CENTRE - (B[:, :2].min(axis=0) + B[:, :2].max(axis=0)) / 2.0).tolist() + [0.0]
    trimesh.Trimesh(B + bed, F, process=False).export(str(stl))
    layers = parse_gcode(run_slicer(stl, work, settings))
    samples, off = measure(B, F, layers)
    sites = sites_of(samples) + z_steps(B, F, layers)
    for s in sites:
        s["at"] = tuple((np.array(s["at"]) + (0.0, 0.0, b0)) @ R)
    sites.sort(key=lambda s: -s["vol"])
    top = layers[-1]["z"] + layers[-1]["h"] / 2.0
    return sites, layers, {"layers": len(layers), "top": top, "height": float(B[:, 2].max()),
                           "offset": tuple(off)}


def report(sites, stats, limit=20):
    print("  %d layers, top %.2f of model %.2f: %d site(s) over %.2f"
          % (stats["layers"], stats["top"], stats["height"], len(sites), MIN_ERR))
    for s in sites[:limit]:
        print("    %-7s %5.2f max %5.2f typical  %7.2f mm3  z %.1f..%.1f  %5.1f long  at (%.1f, %.1f, %.1f)"
              % (s["kind"], s["max"], s["err"], s["vol"], s["z0"], s["z1"], s["long"], *s["at"]))


# ── the sample parts: each one a known answer ───────────────────────────────
def samples():
    """{name: solid}: small parts whose right answer can be worked out by hand."""
    import cadquery as cq

    def box(x, y, z):
        return cq.Workplane("XY").box(x, y, z, centered=(True, True, False))

    out = {"plain_box": box(20, 20, 8),
           "shelf_on_layer": box(20, 20, 4).union(box(10, 20, 8).translate((-5, 0, 0))),
           "shelf_off_layer": box(20, 20, 4.2).union(box(10, 20, 8).translate((-5, 0, 0)))}
    for t in (0.25, 0.5, 0.6, 0.8, 1.2, 1.6):
        out["fin_%.2f" % t] = box(20, 20, 4).union(box(t, 20, 8))
    # a wedge whose edge runs to nothing, in the layer and across the layers
    out["wedge_in_layer"] = cq.Workplane("XY").polyline([(0, 0), (20, 0), (0, 5)]).close().extrude(8)
    out["wedge_across_layers"] = (cq.Workplane("XZ").polyline([(0, 0), (20, 0), (0, 5)]).close()
                                  .extrude(10))
    for a in (30, 60, 90, 120):
        r = math.radians(a)
        out["corner_%d" % a] = (cq.Workplane("XY")
                                .polyline([(-20, 0), (0, 0), (-20 * math.cos(r), 20 * math.sin(r))])
                                .close().extrude(6))
    pts = [(3 * math.cos(t), 3 * math.sin(t)) for t in np.radians(np.arange(-225, 46, 10))]
    out["teardrop"] = box(20, 12, 20).cut(
        cq.Workplane("XZ").center(0, 10).polyline(pts + [(0, 3 * math.sqrt(2))]).close()
        .extrude(20, both=True))
    out["hole_vertical"] = box(20, 20, 6).cut(cq.Workplane("XY").circle(2).extrude(10))
    return out


def self_test():
    root = pathlib.Path(tempfile.mkdtemp(prefix="slicer_check"))
    settings = presets(root / "presets")
    got = {}
    for name, wp in samples().items():
        V, F = mesh_of(wp.val())
        got[name] = check(V, F, work=root / name, settings=settings)
        print(name)
        report(got[name][0], got[name][2], 6)
    return got


def _main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("step", nargs="?")
    ap.add_argument("--up", default="0,0,1")
    ap.add_argument("--process", default=PROCESS)
    ap.add_argument("--filament", default=FILAMENT)
    ap.add_argument("--test", action="store_true")
    a = ap.parse_args()
    if a.test:
        self_test()
        return
    import cadquery as cq
    V, F = mesh_of(cq.importers.importStep(a.step).val())
    work = pathlib.Path(tempfile.mkdtemp(prefix="slicer_check"))
    settings = presets(work / "presets", process=a.process, filament=a.filament)
    sites, _, stats = check(V, F, tuple(float(x) for x in a.up.split(",")), work, settings)
    report(sites, stats)


if __name__ == "__main__":
    _main()
