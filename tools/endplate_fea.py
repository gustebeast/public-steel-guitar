"""Linear-elastic FEA of the direct-drive endplate under the strings' open-pitch bearing loads
(gmsh + scikit-fem + pyamg: py -3.12 -m pip install gmsh scikit-fem meshio pyamg).

    py -3.12 tools/endplate_fea.py <out dir> <mesh h mm> [plate beads] [none|short|long axles]

Run from the worktree root. Supports: the body's walls and floor at x_j. Steel axles are meshed
in, bonded in their bores (an upper bound on what slip-fit axles give)."""
import sys, json, math, time
sys.path.insert(0, '.')
import numpy as np
D_ = sys.argv[1]; H = float(sys.argv[2])
t0 = time.time()
import cadquery as cq
from src import direct_bench as d
if len(sys.argv) > 3:
    d.EP_PLATE_N = int(sys.argv[3])
    d.ROD_PLATE = (d.X_BEND - d.R - d.BRG_CLR - d.EP_PLATE_N * d.D.BEAD, d.ROD_PLATE[1])
    d.endplate_full.cache_clear()
print('plate %d beads: x_j %.2f' % (d.EP_PLATE_N, d.ROD_PLATE[0]), flush=True)
step = D_ + '/ep.step'
cq.exporters.export(d.endplate_full(), step)
T0 = [math.sqrt(2) * (f + 6) / 0.95 for f in d.SPRING_F]          # open pitch, N
rows = dict(d.axle_zs())
rowz = {0: rows['db_bend_axle_ra'], 1: rows['db_bend_axle_rb'], 2: rows['db_bend_axle_rc']}
zb = rows['db_bridge_axle']
xb, r_b = d.X_BEND, (d.D.BRIDGE_AXLE_D + 0.2) / 2
xj = d.ep_x()['x_j']
(_, _), (yo0, yo1), (zo0, _) = d.body_box()['outer']
(_, _), (yi0, yi1), (zi0, _) = d.body_box()['inner']
pitch = abs(d.y_of(0) - d.y_of(1))

import gmsh
gmsh.initialize(); gmsh.option.setNumber('General.Terminal', 0)
AX = sys.argv[4] if len(sys.argv) > 4 else 'none'
ents = gmsh.model.occ.importShapes(step)
cyl = []
if AX != 'none':                     # steel axles meshed in, bonded in their bores
    if AX == 'long':
        ya, yb = yo0 + 0.5, yo1 - 3.0
    else:
        ya, yb = d.axle_span()
    for zc in list(rowz.values()) + [zb]:
        cyl.append((3, gmsh.model.occ.addCylinder(xb, ya, zc, 0, yb - ya, 0, r_b)))
    gmsh.model.occ.fragment([e_ for e_ in ents if e_[0] == 3], cyl)
gmsh.model.occ.synchronize()
steel_vol = set()
for dim, tag in gmsh.model.getEntities(3):
    x0_, y0_, z0_, x1_, y1_, z1_ = gmsh.model.getBoundingBox(3, tag)
    if AX != 'none' and x1_ - x0_ < 2 * r_b + 0.05 and abs((x0_ + x1_) / 2 - xb) < 0.05 and z1_ - z0_ < 2 * r_b + 0.05:
        steel_vol.add(tag)
print('axles: %s, %d steel volume(s)' % (AX, len(steel_vol)), flush=True)
gmsh.option.setNumber('Mesh.MeshSizeMax', H); gmsh.option.setNumber('Mesh.MeshSizeMin', H / 4)
gmsh.option.setNumber('Mesh.MeshSizeFromCurvature', 12)
gmsh.model.mesh.generate(3)
_, coords, _ = gmsh.model.mesh.getNodes()
P = coords.reshape(-1, 3)
tl, ml_ = [], []
for dim, tag in gmsh.model.getEntities(3):
    et, tags, conn = gmsh.model.mesh.getElements(3, tag)
    tt = np.array(conn[list(et).index(4)]).reshape(-1, 4).astype(np.int64) - 1
    tl.append(tt); ml_.append(np.full(len(tt), tag in steel_vol))
tets = np.concatenate(tl); is_steel = np.concatenate(ml_)
gmsh.finalize()
used = np.unique(tets); remap = -np.ones(len(P), np.int64); remap[used] = np.arange(len(used))
P = P[used]; tets = remap[tets]
print('mesh: %d nodes, %d tets (%.0f s)' % (len(P), len(tets), time.time() - t0), flush=True)

import skfem as fem
from skfem.models.elasticity import linear_elasticity, lame_parameters
from skfem.helpers import dot
m = fem.MeshTet(P.T.copy(), tets.T.copy())
e = fem.ElementVector(fem.ElementTetP2())
ib = fem.Basis(m, e, intorder=2)
E, NU = 5000.0, 0.36                                               # PETG-GF as printed, MPa
lam, mu = lame_parameters(E, NU)
lam_s, mu_s = lame_parameters(200000.0, 0.29)
b0 = ib.with_element(fem.ElementTetP0())
LAM = np.where(is_steel, lam_s, lam); MU = np.where(is_steel, mu_s, mu)
from skfem.helpers import ddot, sym_grad as _sg, div
@fem.BilinearForm
def elast(u, v, w):
    return 2 * w.mu * ddot(_sg(u), _sg(v)) + w.lam * div(u) * div(v)
K = fem.asm(elast, ib, lam=b0.interpolate(LAM), mu=b0.interpolate(MU))
print('steel tets %d of %d' % (is_steel.sum(), len(is_steel)), flush=True)
print('K assembled: %d dofs (%.0f s)' % (K.shape[0], time.time() - t0), flush=True)

mid = m.p[:, m.facets].mean(axis=1)                                # facet midpoints
bnd = m.boundary_facets()
# the bore facets: on a bore's circular part (radius r_b in XZ about the axle)
groups = []                                                       # (facets, F vector, y-centre)
for i in range(d.N):
    T = T0[i]; yi = d.y_of(i)
    for zc, F in ((zb, np.array([-T, 0, -T])), (rowz[d.level(i)], np.array([-T, 0, T]))):
        c = mid[:, bnd]
        rr = np.hypot(c[0] - xb, c[2] - zc)
        sel = bnd[(abs(rr - r_b) < 0.35) & (abs(c[1] - yi) < pitch)]
        groups.append((sel, F, yi))

def traction(sel, F, yi):
    fb = fem.FacetBasis(m, e, facets=sel, intorder=3)
    Fh = F / np.linalg.norm(F)
    def wgt(w):
        x, y = w.x[0], w.x[1]
        n = w.n
        cosv = -(n[0] * Fh[0] + n[1] * Fh[1] + n[2] * Fh[2])
        return np.maximum(cosv, 0) * np.maximum(1 - abs(y - yi) / pitch, 0)
    @fem.Functional
    def area(w):
        return wgt(w)
    a = area.assemble(fb)
    k = np.linalg.norm(F) / a
    @fem.LinearForm
    def lf(v, w):
        s = k * wgt(w)
        return s * (v[0] * Fh[0] + v[1] * Fh[1] + v[2] * Fh[2])
    return lf.assemble(fb)

f = np.zeros(K.shape[0])
for sel, F, yi in groups:
    f += traction(sel, F, yi)
print('loads: total Fx %.0f N, Fz %.0f N over %d groups' % (sum(g[1][0] for g in groups), sum(g[1][2] for g in groups), len(groups)), flush=True)

# supports on the -X face (x = xj): the body's end bears there. Walls: outside the inner y span.
# Floor: under the inner floor top.
on_face = bnd[abs(mid[0, bnd] - xj) < 0.05]
cy, cz = mid[1, on_face], mid[2, on_face]
walls = on_face[(cy < yi0) | (cy > yi1)]
floor = on_face[(cz < zi0) & (cy >= yi0) & (cy <= yi1)]
print('support facets: -X face %d, walls %d, floor %d; face z %.1f..%.1f, floor top %.1f' % (
    len(on_face), len(walls), len(floor), cz.min(), cz.max(), zi0), flush=True)
comps = ib.split_indices(); X = ib.doflocs
B = np.zeros((K.shape[0], 6))
for c, idx in enumerate(comps):
    B[idx, c] = 1.0
x_, y_, z_ = X[0], X[1], X[2]
for (a, b_, k) in ((1, 2, 3), (2, 0, 4), (0, 1, 5)):        # rotations about x, y, z
    ia, ib_ = comps[a], comps[b_]
    B[ia, k] = -X[b_][ia]; B[ib_, k] = X[a][ib_]
from skfem.helpers import grad, sym_grad, trace, eye
def solve(support_facets, name):
    keep = [ib.get_dofs(support_facets).all('u^1'), ib.get_dofs(walls).all('u^2'),
            ib.get_dofs(walls).all('u^3')]
    Dd = np.unique(np.concatenate(keep))
    t1 = time.time()
    import pyamg
    from scipy.sparse.linalg import cg
    Kc, fc, _, I = fem.condense(K, f, D=Dd)
    ml = pyamg.smoothed_aggregation_solver(Kc, B=B[I], max_coarse=2000)
    res = []
    xs, info = cg(Kc, fc, M=ml.aspreconditioner(), rtol=1e-7, maxiter=3000, callback=lambda xk: res.append(1))
    print('   cg iterations %d' % len(res), flush=True)
    u = np.zeros(K.shape[0]); u[I] = xs
    print('%s: solved (cg info %d, %.0f s)' % (name, info, time.time() - t1), flush=True)
    # stresses at element centroids, P2 -> project to P0
    e0 = fem.ElementVector(fem.ElementTetP0())
    def stress_comp(ii, jj):
        b0 = ib.with_element(fem.ElementTetP0())
        uh = ib.interpolate(u)
        G = sym_grad(uh)
        s = 2 * MU[:, None] * G[ii][jj] + (LAM[:, None] * (G[0][0] + G[1][1] + G[2][2]) if ii == jj else 0)
        return (s * ib.dx).sum(axis=1) / ib.dx.sum(axis=1)
    S = {k: stress_comp(*k) for k in [(0, 0), (1, 1), (2, 2), (0, 1), (0, 2), (1, 2)]}
    vm = np.sqrt(0.5 * ((S[0, 0] - S[1, 1]) ** 2 + (S[1, 1] - S[2, 2]) ** 2 + (S[2, 2] - S[0, 0]) ** 2)
                 + 3 * (S[0, 1] ** 2 + S[0, 2] ** 2 + S[1, 2] ** 2))
    # principal max (tension)
    sig = np.stack([np.stack([S[0, 0], S[0, 1], S[0, 2]], -1), np.stack([S[0, 1], S[1, 1], S[1, 2]], -1),
                    np.stack([S[0, 2], S[1, 2], S[2, 2]], -1)], -2)
    p1 = np.linalg.eigvalsh(sig)[:, -1]
    st_vm = vm[is_steel].max() if is_steel.any() else 0
    print('%s: steel axle peak von Mises %.0f MPa' % (name, st_vm))
    p1 = np.where(is_steel, 0, p1); vm = np.where(is_steel, 0, vm)
    cen = m.p[:, m.t].mean(axis=1)
    vol = ib.dx.sum(axis=1)
    disp = u[ib.nodal_dofs].T if False else None
    ux = u[ib.nodal_dofs[0]]; uz = u[ib.nodal_dofs[2]]
    order = np.argsort(-p1)
    print('%s: max |ux| %.3f mm, max |uz| %.3f mm' % (name, abs(ux).max(), abs(uz).max()))
    for q in (99.0, 99.9):
        print('%s: tension p1 %.1f pct = %.1f MPa; von Mises %.1f pct = %.1f MPa' % (name, q, np.percentile(p1, q), q, np.percentile(vm, q)))
    print('%s: top tension elements (MPa @ x,y,z):' % name)
    seen = []
    for k_ in order:
        c = cen[:, k_]
        if any(np.linalg.norm(c - s_) < 6 for s_ in seen):
            continue
        seen.append(c)
        print('   %6.1f  @ (%6.1f, %6.1f, %6.1f)  vm %5.1f' % (p1[k_], c[0], c[1], c[2], vm[k_]))
        if len(seen) >= 8:
            break
    np.savez(D_ + '/res_%s.npz' % name, p=m.p, t=m.t, p1=p1, vm=vm, u=u)

solve(np.concatenate([walls, floor]), 'walls_floor')
print('done %.0f s' % (time.time() - t0))
