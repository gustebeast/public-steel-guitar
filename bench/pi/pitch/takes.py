"""takes.py: synthetic string takes in the same files `panel capture` writes, with their truth.

A take is three files with one stem:
    <stem>.npz   sum, diff (float32, 48 kHz), fs, first, duty     -- as `panel capture` writes
    <stem>.f32   the mix the detector reads, raw float32          -- as `panel capture` writes
    <stem>.json  the truth: what was played, and when             -- ours; a real take may have one
So a real capture and a synthetic one go through replay.py the same way, and the user's takes only
have to be dropped into the directory (with a .json if they are to be scored, see replay.py).

The string, as two photodiodes see it (the optical board: sensors A and B under each string,
SUM = A + B, DIFF = A - B):
  * mode k of an ideal string plucked at xp (fraction of the length) has amplitude
    sin(k pi xp) / k^2, and a sensor at xs sees it times sin(k pi xs). Two sensors a little apart
    see different weights per harmonic, so the 2nd can be the loudest in one of them, as on
    string 1's sensor A (bench, 2026-11-02);
  * partials are stretched (stiffness B, f_k = k f0 sqrt(1 + B k^2)) and each decays faster than
    the one below;
  * the pick: a few ms of band-limited noise at the onset, the plectrum scraping off the string,
    plus the string's own release;
  * the floor: white, 13 counts rms, the R1 board's measured floor. Pluck level 300 rms.
Levels are the R1 board on the user's MSA, 2026-11-02 (docs/bronner-work-items.md).
"""
import json

import numpy as np

FS = 48000
FLOOR = 13.0            # counts rms, white
LEVEL = 300.0           # a pluck's rms over its first 100 ms, in the louder of SUM and DIFF
# string 1 as measured (293.3 Hz), the rest down to C2: the C6 copedent's open strings
STRINGS = [293.3, 329.6, 261.6, 220.0, 196.0, 164.8, 130.8, 110.0, 87.3, 65.4]


def string_wave(f0, n, rng, xp=0.18, xs=(0.06, 0.09), stiff=1e-4, decay=2.0, pick=0.4, h2a=1.0):
    """(A, B): what each sensor sees of one pluck, n samples, f0 a number or an array (a slide).
    Unscaled; the caller sets the level. h2a scales the 2nd harmonic in sensor A alone: 1.5 x the
    fundamental was measured there on string 1 (a sensor's own response, not the string's)."""
    t = np.arange(n) / FS
    f0 = np.broadcast_to(np.asarray(f0, dtype=float), (n,))
    ph = 2 * np.pi * np.cumsum(f0) / FS
    out = [np.zeros(n), np.zeros(n)]
    for k in range(1, 13):
        stretch = k * np.sqrt(1 + stiff * k * k)
        if np.max(f0) * stretch > 0.45 * FS:
            break
        a = np.sin(k * np.pi * xp) / k ** 2
        w = a * np.exp(-t * k / decay) * np.sin(stretch * ph + rng.uniform(0, 2 * np.pi))
        for s, x in enumerate(xs):
            out[s] += np.sin(k * np.pi * x) * w * (h2a if (k == 2 and s == 0) else 1.0)
    # the pick: 3 ms of noise, 300 Hz - 6 kHz, decaying, the same in both sensors with a little
    # of each sensor's own; `pick` is its peak against the string's
    m = int(0.003 * FS)
    raw = rng.normal(0, 1, m + 400)               # filtered long, then cut: no edge from the filter
    bp = np.convolve(raw, np.hanning(9) / 4.5, "same") - np.convolve(raw, np.hanning(161) / 80, "same")
    nz = bp[200:200 + m] * np.exp(-np.arange(m) / (0.001 * FS))
    peak = max(np.max(np.abs(o[:FS // 20])) for o in out) or 1.0
    for o in out:
        o[:m] += pick * peak * (nz + 0.3 * rng.normal(0, 1, m) * np.exp(-np.arange(m) / (0.001 * FS)))
    return out


def scaled(a, b, level=LEVEL):
    """Scale a pluck's two sensors so the louder of SUM and DIFF has `level` rms over 100 ms."""
    w = FS // 10
    g = level / max(np.sqrt(np.mean((a[:w] + b[:w]) ** 2)), np.sqrt(np.mean((a[:w] - b[:w]) ** 2)))
    return a * g, b * g


def take(kind, f0, rng, xs=(0.06, 0.09), h2a=1.0):
    """(A, B, truth). kind: pluck (then a damp), slide (two semitones up the bar), repluck
    (a second pluck while the first rings), silence (hands off). truth is the .json's body."""
    pre, n = int(0.3 * FS), int(1.5 * FS)
    A, B = np.zeros(pre + n), np.zeros(pre + n)
    pts = [[0.0, f0], [(pre + n) / FS, f0]]
    if kind == "silence":
        plucks, ons, held = [], 0, None
    elif kind == "pluck":
        a, b = scaled(*string_wave(f0, n, rng, xs=xs, h2a=h2a))
        damp = np.ones(n)
        d = int(0.9 * FS)
        damp[d:] = np.exp(-np.arange(n - d) / (0.05 * FS))
        A[pre:], B[pre:] = a * damp, b * damp
        plucks, ons, held = [pre / FS], 1, [pre / FS + 0.15, pre / FS + 0.8]
    elif kind == "slide":
        f = np.full(n, f0)
        s, e = int(0.4 * FS), int(0.7 * FS)
        f[s:e] = f0 * 2 ** (2 / 12 * np.linspace(0, 1, e - s))
        f[e:] = f0 * 2 ** (2 / 12)
        A[pre:], B[pre:] = scaled(*string_wave(f, n, rng, xs=xs, h2a=h2a))
        top = f0 * 2 ** (2 / 12)
        pts = [[0.0, f0], [(pre + s) / FS, f0], [(pre + e) / FS, top], [(pre + n) / FS, top]]
        plucks, ons, held = [pre / FS], 1, [pre / FS + 0.15, pre / FS + 0.38]
    elif kind == "repluck":
        m = int(0.6 * FS)
        A[pre:], B[pre:] = scaled(*string_wave(f0, n, rng, xs=xs, h2a=h2a))
        a2, b2 = scaled(*string_wave(f0, n - m, rng, xs=xs, h2a=h2a))
        A[pre + m:] = 0.3 * A[pre + m:] + a2
        B[pre + m:] = 0.3 * B[pre + m:] + b2
        plucks, ons, held = [pre / FS, (pre + m) / FS], 2, [pre / FS + 0.15, pre / FS + 0.55]
    else:
        raise ValueError(kind)
    A += rng.normal(0, FLOOR / np.sqrt(2), len(A))
    B += rng.normal(0, FLOOR / np.sqrt(2), len(B))
    truth = {"kind": kind, "plucks": plucks, "expect_on": ons, "pitch": pts, "held": held}
    return A, B, truth


def write(stem, A, B, truth=None, mix="diff", duty=None):
    """The take's files, as `panel capture` writes them, plus the truth if there is one."""
    sm, df = (A + B).astype(np.float32), (A - B).astype(np.float32)
    np.savez(stem + ".npz", sum=sm, diff=df, fs=float(FS), first=0, duty=duty if duty is not None else -1)
    (df if mix == "diff" else sm).tofile(stem + ".f32")
    if truth is not None:
        with open(stem + ".json", "w") as fh:
            json.dump(dict(truth, mix=mix, fs=FS), fh, indent=1)
