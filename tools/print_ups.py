"""Which way each printed component of the assembly built, in the pose it stands in.

    ups(components)  ->  {name: (x, y, z)}          for cadkit.web.export(layers=...)

The exported print STEPs are the record: each is the part as it goes on the bed, +Z up. So a
placed copy needs no name lookup and no pose from the build. Its vertices are matched against a
STEP's by shape, and the rigid map between the two carries +Z onto the copy. The STEPs are read as
text, for their VERTEX_POINTs only, which takes milliseconds where importing one takes seconds.

A component no STEP matches (a STEP older than the part, a fused pair) falls back on the declared
direction of a part drawn where it sits (print_check.up_of). One with neither stays smooth in the
viewer, and that is not an error.
"""

from __future__ import annotations

import pathlib
import re

import numpy as np

from tools.web_materials import MATERIALS, material_of

ROOT = pathlib.Path(__file__).resolve().parent.parent
_POINT = re.compile(r"#(\d+)\s*=\s*CARTESIAN_POINT\(\s*'[^']*'\s*,\s*\(\s*([^)]*)\)\s*\)\s*;")
_VERTEX = re.compile(r"=\s*VERTEX_POINT\(\s*'[^']*'\s*,\s*#(\d+)\s*\)\s*;")
_TOL = 2e-3


def _step_vertices(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    pts = {m.group(1): m.group(2) for m in _POINT.finditer(text)}
    v = [[float(c) for c in pts[r].split(",")] for r in _VERTEX.findall(text) if r in pts]
    return np.array(v) if v else None


def _sig(v):
    """What a rigid move leaves alone: the sorted distances from the centroid."""
    return np.sort(np.linalg.norm(v - v.mean(axis=0), axis=1))


def _rigid(a, b):
    """The rotation (or mirror) taking vertex set `a` onto `b`, centred, in no particular
    order; None if no pair of principal frames lands them on each other."""
    from scipy.spatial import cKDTree
    _, ua = np.linalg.eigh(a.T @ a)
    _, ub = np.linalg.eigh(b.T @ b)
    tree = cKDTree(b)
    best = None
    for sx in (1, -1):
        for sy in (1, -1):
            for sz in (1, -1):
                R = ub @ np.diag((sx, sy, sz)) @ ua.T
                d = tree.query(a @ R.T)[0].max()
                if best is None or d < best[0]:
                    best = (d, R)
    return best[1] if best[0] < 10 * _TOL else None


def _steps():
    out = []
    for mat in MATERIALS:
        for p in sorted((ROOT / mat).glob("*.step")):
            v = _step_vertices(p)
            if v is not None and len(v) >= 4:
                out.append((p.stem, v - v.mean(axis=0), _sig(v)))
    return out


def _declared(name):
    from tools.print_check import _value, up_of
    base = re.sub(r"(_\d+)+$", "", name)
    if base == "top_plate_color":
        return tuple(float(x) for x in _value("src.top_plate", "PIECE_UP"))
    if base == "nut_slide_insert":
        return tuple(float(x) for x in _value("src.nut_block", "INSERT_UP"))
    if base == "chassis_light":
        return tuple(float(x) for x in _value("src.chassis", "PRINT_UP"))
    try:
        return up_of(name)[0]
    except (KeyError, ValueError, FileNotFoundError):
        return None


def ups(components):
    """{name: build direction} of the printed components among [(name, workplane)]."""
    steps = _steps()
    out, matched, declared, none = {}, 0, 0, []
    for name, wp in components:
        mat = material_of(name)
        if mat is None or not mat.startswith(MATERIALS):
            continue
        try:
            solid = wp.val() if hasattr(wp, "val") else wp
            v = np.array([p.toTuple() for p in solid.Vertices()])
        except Exception:
            v = np.empty((0, 3))
        up = None
        if len(v) >= 4:
            c = v - v.mean(axis=0)
            s = _sig(v)
            for _stem, sv, ss in steps:
                if len(ss) == len(s) and np.abs(ss - s).max() < _TOL * 5:
                    R = _rigid(sv, c)
                    if R is not None:
                        up = tuple(float(x) for x in R[:, 2])
                        break
        if up is not None:
            matched += 1
        else:
            up = _declared(name)
            declared += up is not None
        if up is None:
            none.append(name)
        else:
            out[name] = up
    print("  layer lines: %d parts from their print STEP, %d declared, %d smooth%s"
          % (matched, declared, len(none), (": " + ", ".join(none[:8])) if none else ""))
    return out
