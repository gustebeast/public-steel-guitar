"""Every exported printed part through cadkit.slicer_check, 0.8 nozzle, report only.
docs/print-accuracy-sweep.md reads the result. Two things differ from a plain run, both
because the plain result was impossible (errors of 40 to 60 mm):

1. Deck panels and chassis segments come from the build cache as one fused object in assembly
   pose (tools.print_check.load_part), with the declared build direction: their exported STEPs
   are each re-centred, so the base and colour STEPs do not line up.
2. A lateral error counts only if one layer of Z cannot explain it: beads of layer i against
   the model at layers i-1, i, i+1, least error kept. Without this a bridge or ceiling laid one
   layer off the mid-layer section reads as the whole span, tens of mm, in one layer. Stair
   steps and shelf heights stay visible as ZSTEP.

    py -3.12 tools/slicer_sweep.py      resumable; results in .slicer_sweep/
"""
import concurrent.futures as cf, json, os, pathlib, subprocess, sys, time

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / ".slicer_sweep"
WT = str(ROOT)
MAIN = ROOT                 # the print STEPs: run it where a build has written them
LIMIT = 1200
JOBS = 2


def measure2(SC):
    import numpy as np
    from scipy.spatial import cKDTree

    def measure(V, F, layers):
        FN = SC._normals(V, F)
        off = SC.align(layers, V, F, FN)
        secs = []
        for c in layers:
            seg, nrm = SC.section(V, F, FN, c["z"])
            if len(seg):
                b, bi = SC._sample(seg)
                secs.append((b, nrm[bi]))
            else:
                secs.append(None)
        beads = []
        for c in layers:
            p, i = SC._sample(c["seg"])
            beads.append((p + off, c["w"][i]))
        out = []
        n = len(layers)
        for k, c in enumerate(layers):
            near = [m for m in (k - 1, k, k + 1) if 0 <= m < n]
            if secs[k] is not None:                      # MISSING: outline k, beads k-1..k+1
                b = secs[k][0]
                best = None
                for m in near:
                    p, w = beads[m]
                    d, j = cKDTree(p).query(b, k=min(6, len(p)))
                    d, j = d.reshape(len(b), -1), j.reshape(len(b), -1)
                    e = (d - w[j] / 2.0).min(axis=1)
                    best = e if best is None else np.minimum(best, e)
                keep = best > SC.MIN_ERR
                out.append(np.column_stack([np.zeros(keep.sum()), b[keep], np.full(keep.sum(), c["z"]),
                                            best[keep], best[keep] * SC.STEP * c["h"]]))
            p, w = beads[k]                              # EXCESS: beads k, outlines k-1..k+1
            best = None
            for m in near:
                if secs[m] is None:
                    continue
                b, nn = secs[m]
                d, j = cKDTree(b).query(p)
                outside = ((p - b[j]) * nn[j]).sum(axis=1) > 0.0
                e = np.where(outside, w / 2.0 + d, w / 2.0 - d)
                best = e if best is None else np.minimum(best, e)
            if best is None:
                continue
            keep = best > SC.MIN_ERR
            out.append(np.column_stack([np.ones(keep.sum()), p[keep], np.full(keep.sum(), c["z"]),
                                        best[keep], best[keep] * SC.STEP * c["h"]]))
        return (np.vstack(out) if out else np.empty((0, 6))), off
    return measure


def one(name, src):
    os.chdir(WT); sys.path.insert(0, WT)
    import numpy as np
    import cadquery as cq
    from cadkit import slicer_check as SC
    SC.measure = measure2(SC)
    t0 = time.time()
    if src == "cache":
        from tools import print_check as PC
        shape = PC.load_part(name)[0]
        up = PC.up_of(name)[0]
    else:
        shape, up = cq.importers.importStep(src).val(), (0.0, 0.0, 1.0)
    V, F = SC.mesh_of(shape)
    t1 = time.time()
    sites, layers, stats = SC.check(V, F, up, OUT / "work" / name)
    sites = [dict(s, at=tuple(float(x) for x in s["at"])) for s in sites]
    json.dump({"name": name, "src": src, "up": list(up), "stats": stats, "tris": len(F),
               "box": [V.min(axis=0).tolist(), V.max(axis=0).tolist()],
               "t_mesh": t1 - t0, "t_check": time.time() - t1,
               "sites": [{k: (v if isinstance(v, (tuple, str)) else float(v)) for k, v in s.items()}
                         for s in sites]},
              open(OUT / (name + ".json"), "w"), indent=0)


def jobs():
    out = []
    for mat in ("petg-gf", "pctg", "tpu"):
        for p in sorted((MAIN / mat).glob("*.step")):
            n = p.stem
            if n.startswith("test_") or n.endswith("_color") or n.endswith("_light"):
                continue
            cached = n.startswith("chassis_") or n.startswith("top_plate_")
            out.append((n, "cache" if cached else str(p)))
    return out


def run(job):
    name, src = job
    if (OUT / (name + ".json")).exists():
        return name, "cached", 0.0
    t = time.time()
    try:
        r = subprocess.run([sys.executable, __file__, "--one", name, src], capture_output=True, text=True,
                           errors="replace", timeout=LIMIT, creationflags=subprocess.BELOW_NORMAL_PRIORITY_CLASS)
        st = "ok" if r.returncode == 0 else "FAILED " + r.stderr[-260:].replace("\n", " ")
    except subprocess.TimeoutExpired:
        st = "TIMEOUT"
    return name, st, time.time() - t


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    if len(sys.argv) > 1 and sys.argv[1] == "--one":
        one(sys.argv[2], sys.argv[3])
        sys.exit(0)
    js = jobs()
    log = open(OUT / "progress.log", "a", encoding="utf-8")
    print("parts", len(js), file=log, flush=True)
    t0 = time.time()
    with cf.ThreadPoolExecutor(JOBS) as ex:
        for i, (n, st, dt) in enumerate(ex.map(run, js), 1):
            print("%3d/%d %6.0f s  %-26s %5.0f s  %s" % (i, len(js), time.time() - t0, n, dt, st[:300]),
                  file=log, flush=True)
    print("DONE %.0f s" % (time.time() - t0), file=log, flush=True)
