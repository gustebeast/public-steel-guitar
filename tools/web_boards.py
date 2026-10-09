"""Circuit boards in the web view with their REAL parts on them, not boxes.

The CAD draws a board as its laminate plus one box per footprint (cadkit/board_geom):
right for clearances, wrong to look at. KiCad's library has a coloured STEP model for
most of those footprints, and each board's geom.json now says which model each
footprint names (cadkit/kicad_geom, "models"). This module swaps the boxes for the
models IN THE WEB EXPORT ONLY. The CAD, its gates and the STEP files are untouched.

    detail(meshed, shape_of)      # tools/web_export.export calls it; see there

HOW A BOARD IS FOUND IN THE ASSEMBLY. Nothing records where a module put its board:
each calls BOARDS.solid(...) and moves the result as it likes. But every board also
places its LETTERING (BOARDS.ink), unmodified, and the lettering's corners are a rigid
copy of the reference's. So the pose is fitted: a part whose corner count equals a
board's reference lettering is matched to it by a registration that does not depend on
vertex order, and accepted only if every corner lands within a micron. The board's own
solid is then the part that holds the laminate's corners at that pose.

WHAT HAPPENS TO THE BOXES. A footprint gets its model only if (a) the model file is on
this machine, (b) this instance actually draws that footprint (one of its box's top
corners is in the solid: a board may omit a part, or draw it in another part for
colour), and (c) the model, placed by KiCad's own rule, lands on the footprint's F.Fab
box. Its box is then cut off the board's solid. Anything that fails a test keeps its
box, and the run says how many did and why. A machine without KiCad's models gets the
boxes everywhere, as before.

THE PLACEMENT RULE is KiCad's (pcbnew/exporters/step, getModelLocation), in the board
frame geom.json uses (centred, +Y up, underside at z = 0):
    board <- T(x, y, top ? thickness : 0) . Rz(rot) . [bottom: Rx(180)]
             . T(offset) . Rz(-rz) . Ry(-ry) . Rx(-rx) <- model
"""

from __future__ import annotations

import glob
import json
import math
import os
import pathlib
import pickle

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
GEOM_DIR = ROOT / "elec" / "geom"
CACHE = ROOT / ".webview" / "boards"
MODEL_TOLERANCE = 0.03        # chord error for a component model: parts are small
SEP = "__"                    # <board part>__<ref> names a component's own part


# ── where KiCad keeps its models ──────────────────────────────────────────────────
def _model_dirs():
    out = {}
    for k, v in os.environ.items():
        if k.startswith("KICAD") and k.endswith("_3DMODEL_DIR") and os.path.isdir(v):
            out[k] = v
    cands = (glob.glob("C:/Program Files/KiCad/*/share/kicad/3dmodels")
             + glob.glob("/usr/share/kicad/3dmodels")
             + glob.glob("/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels"))
    return out, (sorted(cands)[-1] if cands else None)


def resolve_model(path, _dirs=[]):
    """A model path as the footprint writes it -> a file on this machine, or None."""
    if not _dirs:
        _dirs.append(_model_dirs())
    env, default = _dirs[0]
    p = path
    if p.startswith("${"):
        var, _, rest = p[2:].partition("}")
        base = env.get(var) or default
        if not base:
            return None
        p = base + rest
    for cand in (p, os.path.splitext(p)[0] + ".step", os.path.splitext(p)[0] + ".stp"):
        if os.path.isfile(cand) and cand.lower().endswith((".step", ".stp")):
            return cand
    return None


def load_model(path):
    """A STEP model -> (compound, [(face, (r, g, b) or None)]): colours as the file
    gives them, a face's own first, else its solid's."""
    from OCP.STEPCAFControl import STEPCAFControl_Reader
    from OCP.TDocStd import TDocStd_Document
    from OCP.TCollection import TCollection_ExtendedString
    from OCP.XCAFDoc import XCAFDoc_DocumentTool, XCAFDoc_ColorSurf, XCAFDoc_ColorGen
    from OCP.TDF import TDF_LabelSequence
    from OCP.Quantity import Quantity_Color
    from OCP.TopoDS import TopoDS_Iterator, TopoDS_Compound
    from OCP.TopAbs import TopAbs_FACE
    from OCP.BRep import BRep_Builder
    doc = TDocStd_Document(TCollection_ExtendedString("XmlOcaf"))
    rd = STEPCAFControl_Reader()
    rd.SetColorMode(True)
    rd.SetNameMode(False)
    if rd.ReadFile(path) != 1:
        raise IOError("cannot read " + path)
    rd.Transfer(doc)
    st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    ct = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())
    free = TDF_LabelSequence()
    st.GetFreeShapes(free)
    comp, bb = TopoDS_Compound(), BRep_Builder()
    bb.MakeCompound(comp)
    cols = []

    def own(s):
        c = Quantity_Color()
        for t in (XCAFDoc_ColorSurf, XCAFDoc_ColorGen):
            if ct.GetColor(s, t, c):
                return (c.Red(), c.Green(), c.Blue())
        return None

    def walk(s, inherited):
        c = own(s) or inherited
        if s.ShapeType() == TopAbs_FACE:
            cols.append((s, c))
            return
        it = TopoDS_Iterator(s)
        while it.More():
            walk(it.Value(), c)
            it.Next()

    for i in range(1, free.Length() + 1):
        s = st.GetShape_s(free.Value(i))
        bb.Add(comp, s)
        walk(s, None)
    return comp, cols


_MODELS = {}


def model_mesh(path):
    """mesh_shape() of a model file, with per-vertex colour; None if it will not load."""
    if path not in _MODELS:
        from tools.web_export import mesh_shape, ANGULAR
        try:
            comp, cols = load_model(path)
            _MODELS[path] = mesh_shape(comp, MODEL_TOLERANCE, ANGULAR, face_colors=cols, copy=False)
        except Exception as exc:
            print("web boards: %s will not load (%s)" % (os.path.basename(path), exc))
            _MODELS[path] = None
    return _MODELS[path]


# ── small rigid-transform kit (4x4, column vectors) ───────────────────────────────
def _T(x, y, z):
    m = np.eye(4)
    m[:3, 3] = (x, y, z)
    return m


def _R(axis, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    m = np.eye(4)
    i, j = {"x": (1, 2), "y": (2, 0), "z": (0, 1)}[axis]
    m[i, i], m[i, j], m[j, i], m[j, j] = c, -s, s, c
    return m


def footprint_matrix(f, model, thickness):
    ox, oy, oz = model["offset"]
    rx, ry, rz = model["rot"]
    m = _T(f["x"], f["y"], 0.0 if f["side"] == "B" else thickness) @ _R("z", f["rot"])
    if f["side"] == "B":
        m = m @ _R("x", 180.0)
    return m @ _T(ox, oy, oz) @ _R("z", -rz) @ _R("y", -ry) @ _R("x", -rx)


def _apply(m, pts):
    return pts @ m[:3, :3].T + m[:3, 3]


# ── finding a board in the assembly ───────────────────────────────────────────────
def _frames(P, k=3):
    """Candidate frames of a point set, built from points a rigid motion cannot move
    relative to the rest: the centroid, a point far from it, and a point far from that.
    Several candidates, because "the farthest" is a tie on a symmetric layout and
    float32 noise picks a different winner each side."""
    c = P.mean(0)
    d = np.linalg.norm(P - c, axis=1)
    out = []
    for i in np.argsort(-d)[:k]:
        a1 = P[i]
        d1 = np.linalg.norm(P - a1, axis=1)
        for j in np.argsort(-d1)[:k]:
            x = a1 - c
            z = np.cross(x, P[j] - c)
            if np.linalg.norm(x) < 1e-6 or np.linalg.norm(z) < 1e-6:
                continue
            x, z = x / np.linalg.norm(x), z / np.linalg.norm(z)
            m = np.eye(4)
            m[:3, 0], m[:3, 1], m[:3, 2], m[:3, 3] = x, np.cross(z, x), z, c
            out.append(m)
    return out


def _nearest(A, B):
    """For each row of A the index of the nearest row of B (brute force, in slices)."""
    out = np.empty(len(A), dtype=np.int64)
    for s in range(0, len(A), 512):
        d = ((A[s:s + 512, None, :] - B[None, :, :]) ** 2).sum(-1)
        out[s:s + 512] = d.argmin(1)
    return out


def fit_pose(ref, pts, tol=2e-3):
    """The proper rigid motion taking `ref` onto `pts` (the same corners, in any order),
    or None. A first guess from matching frames, each corner paired with its nearest
    under that guess, then the least-squares motion for the pairing; accepted only if
    the pairing is one-to-one and every corner lands within `tol`."""
    if len(ref) != len(pts) or len(ref) < 4:
        return None
    ref, pts = np.asarray(ref, dtype=float), np.asarray(pts, dtype=float)
    fa = _frames(ref, 1)
    if not fa:
        return None
    inv_a = np.linalg.inv(fa[0])
    for fb in _frames(pts):
        guess = fb @ inv_a
        moved = _apply(guess, ref)
        idx = _nearest(moved, pts)
        if len(np.unique(idx)) != len(idx) or np.abs(moved - pts[idx]).max() > 0.05:
            continue
        A, B = ref, pts[idx]
        ca, cb = A.mean(0), B.mean(0)
        U, _, Vt = np.linalg.svd((A - ca).T @ (B - cb))
        if np.linalg.det(Vt.T @ U.T) < 0:
            continue                   # a mirror image is not this board
        R = Vt.T @ U.T
        t = cb - R @ ca
        if np.abs(A @ R.T + t - B).max() > tol:
            continue
        m = np.eye(4)
        m[:3, :3], m[:3, 3] = R, t
        return m
    return None


def _reference_inks():
    """{(board, refs): corner array} for every board whose geom names a model, cached on
    the geom file's time (drawing the lettering costs seconds a board)."""
    from tools.web_export import shape_vertices, _topods
    out = {}
    CACHE.mkdir(parents=True, exist_ok=True)
    BG = None
    for path in sorted(GEOM_DIR.glob("*.geom.json")):
        board = path.name[:-len(".geom.json")]
        g = json.loads(path.read_text(encoding="utf-8"))
        if not any(f.get("models") for f in g["footprints"]):
            continue
        cf = CACHE / (board + ".ink.pkl")
        key = (path.stat().st_size, path.stat().st_mtime_ns)
        got = None
        if cf.exists():
            try:
                k, got = pickle.loads(cf.read_bytes())
                if k != key:
                    got = None
            except Exception:
                got = None
        if got is None:
            if BG is None:
                from src import board_geom as BG
            got = {}
            for refs in (True, False):
                try:
                    got[refs] = shape_vertices(_topods(BG.ink(board, refs=refs)))
                except Exception:
                    pass
            cf.write_bytes(pickle.dumps((key, got)))
        for refs, v in got.items():
            out[(board, refs)] = v
    return out


def _has(points, p, tol=0.01):
    return bool((np.abs(points - p).max(axis=1) < tol).any()) if len(points) else False


def detail(meshed, shape_of, log=print):
    """Swap footprint boxes for KiCad's models.

    meshed   {name: mesh_shape() result}, edited in place: a board's solid is re-meshed
             without the boxes that got a model, and each model is added as its own part
             named <board part>__<ref>.
    shape_of name -> the part's solid (cq.Workplane / cq.Shape / TopoDS_Shape); called
             only for the few board solids that have to be cut.
    Returns {model key: geo record} for the sidecar's shared table."""
    import cadquery as cq
    from tools.web_export import mesh_shape, _topods
    models_geo = {}
    if _model_dirs()[1] is None and not _model_dirs()[0]:
        log("web boards: KiCad's 3D models are not on this machine -- boards keep their boxes")
        return models_geo
    inks = _reference_inks()
    if not inks:
        return models_geo
    by_count = {}
    for key, v in inks.items():
        by_count.setdefault(len(v), []).append(key)
    found = []                                   # (board, pose, ink part)
    for name, m in meshed.items():
        v = m.get("verts")
        if v is None or len(v) not in by_count:
            continue
        for board, refs in by_count[len(v)]:
            pose = fit_pose(inks[(board, refs)], v.astype(float))
            if pose is not None:
                found.append((board, pose, name))
                break
    stats = {"boards": 0, "models": 0, "kept": {}}

    def keep(why):
        stats["kept"][why] = stats["kept"].get(why, 0) + 1

    used = set(n for _, _, n in found)
    per_board, counts = [], {}
    for board, pose, ink_name in found:
        g = json.loads((GEOM_DIR / (board + ".geom.json")).read_text(encoding="utf-8"))
        t = g["thickness_mm"]
        poly = g.get("outline_poly") or [(-g["outline_mm"][0] / 2, -g["outline_mm"][1] / 2),
                                         (g["outline_mm"][0] / 2, -g["outline_mm"][1] / 2),
                                         (g["outline_mm"][0] / 2, g["outline_mm"][1] / 2),
                                         (-g["outline_mm"][0] / 2, g["outline_mm"][1] / 2)]
        corners = _apply(pose, np.array([(x, y, z) for x, y in poly for z in (0.0, t)]))
        centre = _apply(pose, np.array([[0.0, 0.0, t / 2.0]]))[0]
        solid_name, best = None, 0.0
        for name, m in meshed.items():
            if name in used or SEP in name or m.get("verts") is None:
                continue
            lo, hi = m["pos"].min(0) - 0.01, m["pos"].max(0) + 0.01
            if not ((centre >= lo).all() and (centre <= hi).all()):
                continue
            v = m["verts"]
            share = sum(_has(v, c) for c in corners) / len(corners)
            if share > best:
                solid_name, best = name, share
        if solid_name is None or best < 0.5:
            keep("no solid found for the board at %s" % ink_name)
            continue
        per_board.append("%s<-%s" % (solid_name, board))
        used.add(solid_name)
        sv = meshed[solid_name]["verts"]
        local = _apply(np.linalg.inv(pose), sv.astype(float))    # the solid's corners, board frame
        cut, added = [], 0
        for f in g["footprints"]:
            ms = f.get("models") or []
            if not ms or not f.get("fab"):
                continue
            x0, x1, y0, y1 = f["fab"]
            back = f["side"] == "B"
            # how tall this instance drew it: a top corner of its box, found in the solid
            h = None
            for cx in (x0, x1):
                for cy in (y0, y1):
                    col = local[(np.abs(local[:, 0] - cx) < 0.01) & (np.abs(local[:, 1] - cy) < 0.01), 2]
                    col = col[col < -0.01] if back else col[col > t + 0.01]
                    if len(col):
                        h = max(h or 0.0, float(np.abs(col - (0.0 if back else t)).max()))
            if h is None:
                keep("not drawn on this instance")
                continue
            model = ms[0]
            if any(abs(s - 1.0) > 1e-6 for s in model["scale"]):
                keep("scaled model")
                continue
            path = resolve_model(model["file"])
            if path is None:
                keep("model file not in KiCad's library here")
                continue
            mm = model_mesh(path)
            if mm is None:
                keep("model would not load")
                continue
            fm = footprint_matrix(f, model, t)
            p = _apply(fm, mm["pos"].astype(float))
            lo, hi = p.min(0), p.max(0)
            cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
            fx, fy = (x0 + x1) / 2, (y0 + y1) / 2
            slack_x = max(1.0, 0.5 * (x1 - x0))
            slack_y = max(1.0, 0.5 * (y1 - y0))
            if abs(cx - fx) > slack_x or abs(cy - fy) > slack_y:
                keep("model does not land on its footprint")
                continue
            full = pose @ fm
            key = os.path.basename(path)
            models_geo[key] = mm["geo"]
            meshed[solid_name + SEP + f["ref"]] = {
                "pos": _apply(full, mm["pos"].astype(float)).astype(np.float32),
                "tri": mm["tri"], "col": mm.get("col"),
                "inst": {"i": key, "m": [round(float(x), 6) for x in full[:3].ravel()]}}
            added += 1
            z0, z1 = (-h - 0.05, -0.005) if back else (t + 0.005, t + h + 0.05)
            cut.append((x0 - 0.02, x1 + 0.02, y0 - 0.02, y1 + 0.02, z0, z1))
            if f.get("tht"):
                a0, a1, b0, b1 = f["tht"]
                cut.append((a0 - 0.02, a1 + 0.02, b0 - 0.02, b1 + 0.02,
                            (t + 0.005, t + 30.0) if back else (-30.0, -0.005)))
        counts[board] = counts.get(board, [0, 0])
        counts[board][0] += 1
        counts[board][1] += added
        if not added:
            continue
        try:
            boxes = None
            for c in cut:
                if len(c) == 5:
                    x0, x1, y0, y1, (z0, z1) = c
                else:
                    x0, x1, y0, y1, z0, z1 = c
                b = cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0).translate(
                    ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
                boxes = b if boxes is None else boxes.add(b)
            tool = cq.Compound.makeCompound([s for s in boxes.vals()])
            R, tr = pose[:3, :3], pose[:3, 3]
            from OCP.gp import gp_Trsf
            trsf = gp_Trsf()
            trsf.SetValues(R[0, 0], R[0, 1], R[0, 2], tr[0], R[1, 0], R[1, 1], R[1, 2], tr[1],
                           R[2, 0], R[2, 1], R[2, 2], tr[2])
            from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
            placed = cq.Shape.cast(BRepBuilderAPI_Transform(tool.wrapped, trsf, True).Shape())
            solid = cq.Shape.cast(_topods(shape_of(solid_name)))
            trimmed = solid.cut(placed)
            new = mesh_shape(trimmed.wrapped)
            if new is not None:
                meshed[solid_name] = new
        except Exception as exc:
            log("web boards: %s kept its boxes under the models (%s)" % (solid_name, exc))
        stats["boards"] += 1
        stats["models"] += added
    kept = "; ".join("%d %s" % (n, w) for w, n in sorted(stats["kept"].items())) or "none"
    log("web boards: %d board(s) carry %d real part model(s) [%s]; boxes kept: %s"
        % (stats["boards"], stats["models"],
           ", ".join("%s x%d: %d" % (b, n, k) for b, (n, k) in sorted(counts.items())), kept))
    return models_geo
