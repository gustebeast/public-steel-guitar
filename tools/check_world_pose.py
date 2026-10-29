"""WORLD-POSE GATE: a part drawn ONCE is authored where it sits -- not posed into place.

    py -3.12 tools/check_world_pose.py          # builds the model (minutes); the build runs
                                                # it for free on the components it just made

THE RULE (user, 2026-10-22, on finding the belt clamps and the vertical lever's housing
checked for printing along the wrong axis: "we should have a rule that blocks this unless
the part is rendered multiple times"). A part is modelled in WORLD coordinates at its station
(leg-orientation rule, 2026-09-10): every direction in its code -- its PRINT_UP, its joints'
facings, the user's "+Y face" -- means what it means in the viewer. A part placed with a
ROTATION or a MIRROR has a private frame, and every one of those directions silently means
something else once it is in the instrument. That is only worth it when the part is drawn
more than once (ten clamps, five lever stations): one authored copy, placed N times.

HOW. Each printed part in src.build.PARTS is the solid as AUTHORED. Each assembly component
that is that solid moved (same vertex count and volume, the vertices in the same order --
cq's move/rotate/mirror keep the topology) gives the rigid map from one to the other
(Procrustes on the vertices). A part with any instance under a rotation or mirror and only
ONE instance in the assembly fails. Components that are not a moved PARTS solid (rebuilt per
station, regenerated joinery) are not judged; the count of those is printed.

ACCEPTED holds the offenders that predate the rule, each by name -- the gate fails on any
other, so the list can only shrink.
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ROT_TOL = 1e-6        # |R - I| below this is no rotation
FIT_TOL = 1e-3        # vertex residual (relative to size) for "the same solid, moved"

# printed parts posed into place while drawn once -- known debt, named. Re-author each where
# it sits and delete its line; a NEW name here needs the user's say-so.
ACCEPTED = {
}


def _solid(wp):
    return wp.val() if hasattr(wp, "val") else wp


def _verts(shape):
    return np.array([v.toTuple() for v in shape.Vertices()])


def _map(A, B):
    """(R, err): the rigid map (a mirror allowed) taking vertex list A onto B, in order."""
    a0, b0 = A - A.mean(0), B - B.mean(0)
    U, _, Vt = np.linalg.svd(a0.T @ b0)
    R = (U @ Vt).T
    # ⚠ A PROPER ROTATION FIRST (Kabsch's sign fix). When the vertices are coplanar -- a
    # plain ring has one seam vertex per circle, all four on one plane -- the singular
    # vector across that plane has an arbitrary sign, and pi_spacer, drawn where it sits,
    # read "MIRRORED" against its own PARTS solid (build #968). A mirror is only what no
    # rotation fits.
    if np.linalg.det(R) < 0:
        D = np.diag([1.0, 1.0, -1.0])
        Rp = (U @ D @ Vt).T
        if np.abs(a0 @ Rp.T - b0).max() / max(1.0, np.abs(a0).max()) <= FIT_TOL:
            R = Rp
    err = np.abs(a0 @ R.T - b0).max() / max(1.0, np.abs(a0).max())
    return R, err


def _describe(R):
    if np.linalg.det(R) < 0:
        return "MIRRORED"
    ang = np.degrees(np.arccos(np.clip((np.trace(R) - 1) / 2, -1, 1)))
    w = np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]])
    ax = w / np.linalg.norm(w) if np.linalg.norm(w) > 1e-9 else np.array([1.0, 0, 0])
    return "rotated %.0f deg about (%.2f, %.2f, %.2f)" % (ang, *ax)


def posed(parts, comps):
    """{part: [(component, R)]} for every assembly component that is a PARTS solid moved,
    and the names of components that matched none."""
    keyed = {}
    for pn, shp in parts.items():
        V = _verts(shp)
        keyed.setdefault(len(V), []).append((pn, shp.Volume(), V))
    out, unmatched = {pn: [] for pn in parts}, []
    for cn, shp in comps:
        V = _verts(shp)
        hit = False
        for pn, vol, A in keyed.get(len(V), []):
            if abs(shp.Volume() - vol) > 1e-6 * max(vol, 1.0):
                continue
            R, err = _map(A, V)
            if err <= FIT_TOL:
                out[pn].append((cn, R))
                hit = True
                break
        if not hit:
            unmatched.append(cn)
    return out, unmatched


def gate(parts, comps, accepted=ACCEPTED, log=print):
    """Number of NEW offenders (not in `accepted`). parts {name: shape}, comps [(name, shape)]."""
    found, unmatched = posed(parts, comps)
    bad, known = [], []
    for pn, inst in sorted(found.items()):
        turned = [(cn, R) for cn, R in inst if np.abs(R - np.eye(3)).max() > ROT_TOL]
        if turned and len(inst) == 1:
            cn, R = turned[0]
            (known if pn in accepted else bad).append("%s (drawn once, as %s): %s" % (pn, cn, _describe(R)))
    judged = sum(len(v) for v in found.values())
    unseen = sorted(pn for pn, inst in found.items() if not inst)
    if unseen:      # rebuilt per station, or not in the assembly: this gate cannot see them
        log("  not judged (no assembly component is this solid moved): " + ", ".join(unseen))
    for line in known:
        log("  accepted: " + line)
    for line in bad:
        log("  POSED INTO PLACE: " + line)
    log("WORLD-POSE GATE: %s -- %d component(s) judged, %d not a moved printed part, "
        "%d accepted, %d new" % ("RED" if bad else "green", judged, len(unmatched), len(known), len(bad)))
    stale = sorted(set(accepted) - {l.split(" ")[0] for l in known})
    if stale:
        log("  (ACCEPTED names that no longer offend -- delete them: %s)" % ", ".join(stale))
    return len(bad)


def main():
    from src import build as B
    parts = {n: _solid(B.PARTS[n][0]()) for n in B.PARTS}
    comps = [(n, _solid(wp)) for n, wp in B.collect_components()]
    return 1 if gate(parts, comps) else 0


if __name__ == "__main__":
    sys.exit(main())
