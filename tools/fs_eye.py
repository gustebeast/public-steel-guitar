"""Full-speed USB over the lever bus pair: the eye at the last board of an arm (docs/lever-usb-flash.md).

    py -3.12 tools/fs_eye.py
"""
import sys
import numpy as np

def run(lens, cload_pf, z0=110.0, vf=0.66, rs=90.0, tr=4e-9, cend=10e-12, bits=400, seed=1, zseg=None):
    c0 = 3e8 * vf
    L = z0 / c0; C = 1.0 / (z0 * c0)           # per metre
    dx = 0.01
    pos, x = [], 0.0
    for l in lens:
        x += l; pos.append(x)
    n = int(round(x / dx)) + 1
    dt = 0.5 * dx / c0
    V = np.zeros(n); I = np.zeros(n - 1)
    Cn = np.full(n, C * dx); Cn[0] *= 0.5; Cn[-1] *= 0.5
    for p in pos[:-1]:
        Cn[int(round(p / dx))] += cload_pf * 1e-12
    Cn[-1] += cend + cload_pf * 1e-12          # the target board itself
    ub = 1.0 / 12e6
    rng = np.random.default_rng(seed)
    data = rng.integers(0, 2, bits) * 2 - 1
    T = bits * ub
    steps = int(T / dt)
    out_t, out_v = [], []
    for k in range(steps):
        t = k * dt
        b = min(int(t / ub), bits - 1)
        prev = data[b - 1] if b else data[0]
        f = min(1.0, (t - b * ub) / tr)
        vs = 3.3 * (prev + (data[b] - prev) * f) / 2 * 2   # +-3.3 V differential swing (FS 0/3.3 each line)
        vs /= 2
        # source node
        i_src = (vs - V[0]) / rs
        V[0] += dt / Cn[0] * (i_src - I[0])
        V[1:-1] += dt / Cn[1:-1] * (I[:-1] - I[1:])
        V[-1] += dt / Cn[-1] * I[-1]
        I += dt / (L * dx) * (V[:-1] - V[1:])
        out_t.append(t); out_v.append(V[-1])
    t = np.array(out_t); v = np.array(out_v)
    # eye: sample the far end around mid bit after the line delay; find best sampling phase
    delay = x / c0
    best = None
    for ph in np.linspace(0.05, 0.95, 37):
        ts = delay + (np.arange(20, bits - 2) + ph) * ub
        vv = np.interp(ts, t, v)
        exp = data[20:bits - 2]
        open_ = min(vv[exp > 0].min(), -vv[exp < 0].max())
        if best is None or open_ > best[0]:
            best = (open_, ph)
    # width of the eye at +-0.2 V (FS receiver sensitivity)
    ok = []
    for ph in np.linspace(0.0, 1.0, 101):
        ts = delay + (np.arange(20, bits - 2) + ph) * ub
        vv = np.interp(ts, t, v)
        exp = data[20:bits - 2]
        ok.append(vv[exp > 0].min() > 0.2 and vv[exp < 0].max() < -0.2)
    width = sum(ok) / 101.0
    return best[0], width, delay

cases = {
    "lever arm, 6 boards, 0.8 m then 0.25 m hops": [0.8] + [0.25] * 5,
    "pedal arm, 5 boards, 1.5 m then 0.1 m hops": [1.5] + [0.1] * 4,
    "long arm, 6 boards, 2.0 m then 0.3 m hops": [2.0] + [0.3] * 5,
}
for cl in (40, 25, 10):
    for tr in (4e-9, 20e-9):
        for name, lens in cases.items():
            o, w, d = run(lens, cl, tr=tr)
            print("load %2d pF/board  edge %2d ns  %-46s eye %.2f V  width %3.0f %% of a bit  (delay %.1f ns)"
                  % (cl, tr * 1e9, name, o, 100 * w, d * 1e9))
