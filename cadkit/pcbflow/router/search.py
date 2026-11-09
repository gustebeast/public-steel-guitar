"""The compiled inner loops: A* over (layer, row, col) and the occupancy stamps.

Everything here works on flat arrays over a WINDOW of the board: a box of rows/cols, all
routing layers. Index s = (k * h + i) * w + j inside the window."""
from __future__ import annotations

import heapq

import numpy as np
from numba import njit

SQ2 = np.float32(1.41421356)
DI = np.array([0, 0, 1, -1, 1, 1, -1, -1], np.int64)
DJ = np.array([1, -1, 0, 0, 1, -1, 1, -1], np.int64)
DL = np.array([1, 1, 1, 1, SQ2, SQ2, SQ2, SQ2], np.float32)


@njit(cache=True)
def astar(cell, via_cell, src, tgt, L, h, w, via_cost, tb, dir_cost):
    """Multi-source A* to the nearest target.

    cell[L*h*w]      cost of standing on a cell (inf = forbidden)
    via_cell[h*w]    cost multiplier of a via at (i, j) (inf = forbidden)
    src, tgt         bool[L*h*w]
    tb               target bounding box (i0, i1, j0, j1) for the heuristic
    dir_cost[L, 2]   extra cost per unit step for (horizontal, vertical) moves on each layer
    Returns the path as an array of flat indices from target back to source (empty if none)."""
    n = L * h * w
    g = np.full(n, np.inf, np.float32)
    par = np.full(n, -1, np.int64)
    done = np.zeros(n, np.bool_)
    heap = [(np.float32(0.0), np.int64(0))]
    heap.pop()
    ti0, ti1, tj0, tj1 = tb[0], tb[1], tb[2], tb[3]
    for s in range(n):
        if src[s] and cell[s] < np.inf:
            g[s] = 0.0
            heapq.heappush(heap, (np.float32(0.0), np.int64(s)))
    hit = -1
    while len(heap) > 0:
        f, s = heapq.heappop(heap)
        if done[s]:
            continue
        done[s] = True
        if tgt[s]:
            hit = s
            break
        k = s // (h * w)
        r = s - k * h * w
        i = r // w
        j = r - i * w
        gs = g[s]
        for d in range(8):
            ii = i + DI[d]
            jj = j + DJ[d]
            if ii < 0 or ii >= h or jj < 0 or jj >= w:
                continue
            t = (k * h + ii) * w + jj
            if done[t]:
                continue
            c = cell[t]
            if c == np.inf:
                continue
            step = DL[d] * c
            if DI[d] == 0:
                step += DL[d] * dir_cost[k, 0]
            elif DJ[d] == 0:
                step += DL[d] * dir_cost[k, 1]
            else:
                step += DL[d] * 0.5 * (dir_cost[k, 0] + dir_cost[k, 1])
            ng = gs + step
            if ng < g[t]:
                g[t] = ng
                par[t] = s
                di = 0 if ti0 <= ii <= ti1 else (ti0 - ii if ii < ti0 else ii - ti1)
                dj = 0 if tj0 <= jj <= tj1 else (tj0 - jj if jj < tj0 else jj - tj1)
                hh = (max(di, dj) - min(di, dj)) + SQ2 * min(di, dj)
                heapq.heappush(heap, (np.float32(ng + hh), np.int64(t)))
        vc = via_cell[r]
        if vc < np.inf:
            for k2 in range(L):
                if k2 == k:
                    continue
                t = (k2 * h + i) * w + j
                if done[t] or cell[t] == np.inf:
                    continue
                ng = gs + via_cost * vc
                if ng < g[t]:
                    g[t] = ng
                    par[t] = s
                    di = 0 if ti0 <= i <= ti1 else (ti0 - i if i < ti0 else i - ti1)
                    dj = 0 if tj0 <= j <= tj1 else (tj0 - j if j < tj0 else j - tj1)
                    hh = (max(di, dj) - min(di, dj)) + SQ2 * min(di, dj)
                    heapq.heappush(heap, (np.float32(ng + hh), np.int64(t)))
    if hit < 0:
        return np.empty(0, np.int64)
    out = []
    s = hit
    while s >= 0:
        out.append(s)
        s = par[s]
    return np.array(out, np.int64)


@njit(cache=True)
def stamp(occ, gen, gval, L, H, W, pts_k, pts_i, pts_j, rads, all_layers, rec):
    """Add 1 to occ[k, i, j] for every cell whose centre is closer than rads[p] cells to a
    point, once per call (gen/gval dedupe), recording each touched flat index in rec.
    Returns the count. all_layers[p]: stamp the disk on every layer (a via)."""
    n = 0
    for p in range(pts_k.shape[0]):
        k0 = pts_k[p]
        ci = pts_i[p]
        cj = pts_j[p]
        rf = rads[p]
        r2 = rf * rf
        rad = int(np.ceil(rf))
        ka = 0 if all_layers[p] else k0
        kb = L if all_layers[p] else k0 + 1
        for di in range(-rad, rad + 1):
            ii = ci + di
            if ii < 0 or ii >= H:
                continue
            for dj in range(-rad, rad + 1):
                if di * di + dj * dj >= r2:
                    continue
                jj = cj + dj
                if jj < 0 or jj >= W:
                    continue
                for k in range(ka, kb):
                    s = (k * H + ii) * W + jj
                    if gen[s] != gval:
                        gen[s] = gval
                        occ[s] += 1
                        if n < rec.shape[0]:
                            rec[n] = s
                        n += 1
    return n


@njit(cache=True)
def unstamp(occ, rec, n):
    for q in range(n):
        occ[rec[q]] -= 1


# heading index d -> (di, dj) is DI[d], DJ[d]; turn class between two headings:
# 0 straight, 1 = 45 deg, 2 = 90 deg, 3 = 135 deg or more (forbidden: acute track corners)
@njit(cache=True)
def _turn(a, b):
    if a == 8 or a == b:
        return 0
    dot = DI[a] * DI[b] + DJ[a] * DJ[b]
    la = abs(DI[a]) + abs(DJ[a])
    lb = abs(DI[b]) + abs(DJ[b])
    # cos of the angle, scaled: unit-unit dot is 1/0/-1, diag-diag 2/0/-2, unit-diag 1/-1
    if la == lb:
        if dot == la:
            return 0
        if dot == 0:
            return 2
        return 3
    if dot > 0:
        return 1
    return 3


@njit(cache=True)
def astar_turn(cell, via_cell, src, tgt, L, h, w, via_cost, tb, dir_cost, t45, t90):
    """astar() with the heading in the state: a 45-degree turn costs t45, a 90-degree one
    t90, and anything sharper is not a move at all. What an engineer's eye does to a
    staircase -- one long run and one corner -- priced into the search, so the cheapest
    path is the tidy one rather than a tidied cheap one."""
    n = L * h * w
    N = n * 9
    g = np.full(N, np.inf, np.float32)
    par = np.full(N, -1, np.int64)
    done = np.zeros(N, np.bool_)
    heap = [(np.float32(0.0), np.int64(0))]
    heap.pop()
    ti0, ti1, tj0, tj1 = tb[0], tb[1], tb[2], tb[3]
    for s in range(n):
        if src[s] and cell[s] < np.inf:
            g[s * 9 + 8] = 0.0
            heapq.heappush(heap, (np.float32(0.0), np.int64(s * 9 + 8)))
    hit = -1
    while len(heap) > 0:
        f, q = heapq.heappop(heap)
        if done[q]:
            continue
        done[q] = True
        s = q // 9
        hd = q - s * 9
        if tgt[s]:
            hit = q
            break
        k = s // (h * w)
        r = s - k * h * w
        i = r // w
        j = r - i * w
        gs = g[q]
        for d in range(8):
            tc = _turn(hd, d)
            if tc == 3:
                continue
            ii = i + DI[d]
            jj = j + DJ[d]
            if ii < 0 or ii >= h or jj < 0 or jj >= w:
                continue
            t = (k * h + ii) * w + jj
            c = cell[t]
            if c == np.inf:
                continue
            qt = t * 9 + d
            if done[qt]:
                continue
            step = DL[d] * c
            if DI[d] == 0:
                step += DL[d] * dir_cost[k, 0]
            elif DJ[d] == 0:
                step += DL[d] * dir_cost[k, 1]
            else:
                step += DL[d] * 0.5 * (dir_cost[k, 0] + dir_cost[k, 1])
            if tc == 1:
                step += t45
            elif tc == 2:
                step += t90
            ng = gs + step
            if ng < g[qt]:
                g[qt] = ng
                par[qt] = q
                di = 0 if ti0 <= ii <= ti1 else (ti0 - ii if ii < ti0 else ii - ti1)
                dj = 0 if tj0 <= jj <= tj1 else (tj0 - jj if jj < tj0 else jj - tj1)
                hh = (max(di, dj) - min(di, dj)) + SQ2 * min(di, dj)
                heapq.heappush(heap, (np.float32(ng + hh), np.int64(qt)))
        vc = via_cell[r]
        if vc < np.inf:
            for k2 in range(L):
                if k2 == k:
                    continue
                t = (k2 * h + i) * w + j
                if cell[t] == np.inf:
                    continue
                qt = t * 9 + 8
                if done[qt]:
                    continue
                ng = gs + via_cost * vc
                if ng < g[qt]:
                    g[qt] = ng
                    par[qt] = q
                    di = 0 if ti0 <= i <= ti1 else (ti0 - i if i < ti0 else i - ti1)
                    dj = 0 if tj0 <= j <= tj1 else (tj0 - j if j < tj0 else j - tj1)
                    hh = (max(di, dj) - min(di, dj)) + SQ2 * min(di, dj)
                    heapq.heappush(heap, (np.float32(ng + hh), np.int64(qt)))
    if hit < 0:
        return np.empty(0, np.int64)
    out = []
    q = hit
    while q >= 0:
        out.append(q // 9)
        q = par[q]
    return np.array(out, np.int64)

# ----------------------------------------------------------------------------------------
# ⚠ A SEARCH MUST NOT PAY FOR THE WINDOW IT DOES NOT VISIT (optical, 2026-11-09): a plane
# net's pieces are joined in a whole-board window (10 M cells), and each 10-cell join spent
# 0.14 s allocating and clearing g/par/done over all of it -- 130 MB a call, a third of a
# round's searches. These kernels take persistent buffers and a generation stamp instead:
# st[q] < base means not seen this call, base = seen (g valid), base + 1 = closed.
# Same expansion order, same ties, same paths as astar()/astar_turn() at eps = 1.
@njit(cache=True)
def astar_s(cell, via_cell, src_idx, tgt, L, h, w, via_cost, tb, dir_cost, eps,
            g, par, st, base):
    heap = [(np.float32(0.0), np.int64(0))]
    heap.pop()
    ti0, ti1, tj0, tj1 = tb[0], tb[1], tb[2], tb[3]
    for a in range(src_idx.size):
        s = src_idx[a]
        if cell[s] < np.inf and st[s] < base:
            g[s] = 0.0
            par[s] = -1
            st[s] = base
            heapq.heappush(heap, (np.float32(0.0), np.int64(s)))
    hit = -1
    while len(heap) > 0:
        f, s = heapq.heappop(heap)
        if st[s] == base + 1:
            continue
        st[s] = base + 1
        if tgt[s]:
            hit = s
            break
        k = s // (h * w)
        r = s - k * h * w
        i = r // w
        j = r - i * w
        gs = g[s]
        for d in range(8):
            ii = i + DI[d]
            jj = j + DJ[d]
            if ii < 0 or ii >= h or jj < 0 or jj >= w:
                continue
            t = (k * h + ii) * w + jj
            if st[t] == base + 1:
                continue
            c = cell[t]
            if c == np.inf:
                continue
            step = DL[d] * c
            if DI[d] == 0:
                step += DL[d] * dir_cost[k, 0]
            elif DJ[d] == 0:
                step += DL[d] * dir_cost[k, 1]
            else:
                step += DL[d] * 0.5 * (dir_cost[k, 0] + dir_cost[k, 1])
            ng = gs + step
            if st[t] < base or ng < g[t]:
                g[t] = ng
                par[t] = s
                st[t] = base
                di = 0 if ti0 <= ii <= ti1 else (ti0 - ii if ii < ti0 else ii - ti1)
                dj = 0 if tj0 <= jj <= tj1 else (tj0 - jj if jj < tj0 else jj - tj1)
                hh = (max(di, dj) - min(di, dj)) + SQ2 * min(di, dj)
                heapq.heappush(heap, (np.float32(ng + eps * hh), np.int64(t)))
        vc = via_cell[r]
        if vc < np.inf:
            for k2 in range(L):
                if k2 == k:
                    continue
                t = (k2 * h + i) * w + j
                if st[t] == base + 1 or cell[t] == np.inf:
                    continue
                ng = gs + via_cost * vc
                if st[t] < base or ng < g[t]:
                    g[t] = ng
                    par[t] = s
                    st[t] = base
                    di = 0 if ti0 <= i <= ti1 else (ti0 - i if i < ti0 else i - ti1)
                    dj = 0 if tj0 <= j <= tj1 else (tj0 - j if j < tj0 else j - tj1)
                    hh = (max(di, dj) - min(di, dj)) + SQ2 * min(di, dj)
                    heapq.heappush(heap, (np.float32(ng + eps * hh), np.int64(t)))
    if hit < 0:
        return np.empty(0, np.int64)
    out = []
    s = hit
    while s >= 0:
        out.append(s)
        s = par[s]
    return np.array(out, np.int64)


@njit(cache=True)
def astar_turn_s(cell, via_cell, src_idx, tgt, L, h, w, via_cost, tb, dir_cost, t45, t90, eps,
                 g, par, st, base):
    heap = [(np.float32(0.0), np.int64(0))]
    heap.pop()
    ti0, ti1, tj0, tj1 = tb[0], tb[1], tb[2], tb[3]
    for a in range(src_idx.size):
        s = src_idx[a]
        q0 = s * 9 + 8
        if cell[s] < np.inf and st[q0] < base:
            g[q0] = 0.0
            par[q0] = -1
            st[q0] = base
            heapq.heappush(heap, (np.float32(0.0), np.int64(q0)))
    hit = -1
    while len(heap) > 0:
        f, q = heapq.heappop(heap)
        if st[q] == base + 1:
            continue
        st[q] = base + 1
        s = q // 9
        hd = q - s * 9
        if tgt[s]:
            hit = q
            break
        k = s // (h * w)
        r = s - k * h * w
        i = r // w
        j = r - i * w
        gs = g[q]
        for d in range(8):
            tc = _turn(hd, d)
            if tc == 3:
                continue
            ii = i + DI[d]
            jj = j + DJ[d]
            if ii < 0 or ii >= h or jj < 0 or jj >= w:
                continue
            t = (k * h + ii) * w + jj
            c = cell[t]
            if c == np.inf:
                continue
            qt = t * 9 + d
            if st[qt] == base + 1:
                continue
            step = DL[d] * c
            if DI[d] == 0:
                step += DL[d] * dir_cost[k, 0]
            elif DJ[d] == 0:
                step += DL[d] * dir_cost[k, 1]
            else:
                step += DL[d] * 0.5 * (dir_cost[k, 0] + dir_cost[k, 1])
            if tc == 1:
                step += t45
            elif tc == 2:
                step += t90
            ng = gs + step
            if st[qt] < base or ng < g[qt]:
                g[qt] = ng
                par[qt] = q
                st[qt] = base
                di = 0 if ti0 <= ii <= ti1 else (ti0 - ii if ii < ti0 else ii - ti1)
                dj = 0 if tj0 <= jj <= tj1 else (tj0 - jj if jj < tj0 else jj - tj1)
                hh = (max(di, dj) - min(di, dj)) + SQ2 * min(di, dj)
                heapq.heappush(heap, (np.float32(ng + eps * hh), np.int64(qt)))
        vc = via_cell[r]
        if vc < np.inf:
            for k2 in range(L):
                if k2 == k:
                    continue
                t = (k2 * h + i) * w + j
                if cell[t] == np.inf:
                    continue
                qt = t * 9 + 8
                if st[qt] == base + 1:
                    continue
                ng = gs + via_cost * vc
                if st[qt] < base or ng < g[qt]:
                    g[qt] = ng
                    par[qt] = q
                    st[qt] = base
                    di = 0 if ti0 <= i <= ti1 else (ti0 - i if i < ti0 else i - ti1)
                    dj = 0 if tj0 <= j <= tj1 else (tj0 - j if j < tj0 else j - tj1)
                    hh = (max(di, dj) - min(di, dj)) + SQ2 * min(di, dj)
                    heapq.heappush(heap, (np.float32(ng + eps * hh), np.int64(qt)))
    if hit < 0:
        return np.empty(0, np.int64)
    out = []
    q = hit
    while q >= 0:
        out.append(q // 9)
        q = par[q]
    return np.array(out, np.int64)


class Buffers:
    """The search's g / parent / stamp arrays, kept between calls and grown on demand.
    A call stamps base = 2 * generation; before the int32 stamp would overflow, wipe."""

    def __init__(self):
        self.n = 0
        self.gen = 0
        self.g = self.par = self.st = None

    def take(self, n):
        if n > self.n:
            self.n = n
            self.g = np.empty(n, np.float32)
            self.par = np.empty(n, np.int64)
            self.st = np.zeros(n, np.int32)
            self.gen = 0
        self.gen += 1
        if 2 * self.gen + 2 >= 2 ** 31 - 1:
            self.st[:] = 0
            self.gen = 1
        return self.g, self.par, self.st, np.int32(2 * self.gen)
