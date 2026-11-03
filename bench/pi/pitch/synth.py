"""synth.py: score the C detector on synthetic plucks at the bench's measured levels, until real
plucked captures exist (the bench package's `panel capture`).

    make && python3 synth.py [seed]

Levels from the R1 board on the MSA, 2026-11-02: plucks 200-650 rms against a floor of 11-14
counts, white. Each string gets three takes: a pluck from silence then a damp, a pluck then a
two-semitone bar slide, and a re-pluck while it still rings. A take passes on four numbers:
  onset    pluck -> ON event                          (envelope; design 1-2 ms + filter)
  pitch    pluck -> first committed frame within 20 cents that stays there for 5 frames
  octave   committed frames (steady >= 2) an octave off   (want 0)
  error    median |cents| over the held part
and a slide must give no ON, and a re-pluck exactly one.
"""
import os
import subprocess
import sys

import numpy as np

FS = 48000
HERE = os.path.dirname(os.path.abspath(__file__))
# string 1 as measured (293.3 Hz), the rest C6 down to C2
STRINGS = [293.3, 329.6, 261.6, 220.0, 196.0, 164.8, 130.8, 110.0, 87.3, 65.4]


def pluck(f0, n, rng, h2=0.5, rms=300.0, decay=2.0):
    """A plucked string as a displacement sensor sees it: harmonics falling as 1/k^2 (the
    2nd set by h2; 1.5 on sensor A of string 1), slightly stretched, each decaying faster
    than the one below. f0 may be an array (a slide)."""
    t = np.arange(n) / FS
    f0 = np.broadcast_to(np.asarray(f0, dtype=float), (n,))
    ph = 2 * np.pi * np.cumsum(f0) / FS
    y = np.zeros(n)
    for k in range(1, 9):
        a = h2 if k == 2 else 1.0 / k ** 2
        stretch = k * np.sqrt(1 + 1e-4 * k * k)
        if np.mean(f0) * stretch > 0.45 * FS:
            break
        y += a * np.exp(-t * k / decay) * np.sin(stretch * ph + rng.uniform(0, 2 * np.pi))
    return y * rms / np.sqrt(np.mean(y[:FS // 10] ** 2))


def take(kind, f0, rng, h2):
    """(samples, [(time, truth Hz or array-of-truth fn)], pluck times, expected ON count)"""
    pre, n = int(0.3 * FS), int(1.5 * FS)
    x = np.zeros(pre + n)
    if kind == "pluck":
        y = pluck(f0, n, rng, h2)
        y[int(0.9 * FS):] *= np.exp(-np.arange(n - int(0.9 * FS)) / (0.05 * FS))   # the damp
        x[pre:] = y
        truth = np.full(len(x), f0)
        plucks = [pre / FS]
    elif kind == "slide":
        f = np.full(n, f0)
        a, b = int(0.4 * FS), int(0.7 * FS)
        f[a:b] = f0 * 2 ** (2 / 12 * np.linspace(0, 1, b - a))
        f[b:] = f0 * 2 ** (2 / 12)
        x[pre:] = pluck(f, n, rng, h2)
        truth = np.concatenate([np.full(pre, f0), f])
        plucks = [pre / FS]
    else:                                                   # re-pluck while it rings
        m = int(0.6 * FS)
        x[pre:] = pluck(f0, n, rng, h2)
        x[pre + m:] = 0.3 * x[pre + m:] + pluck(f0, n - m, rng, h2)
        truth = np.full(len(x), f0)
        plucks = [pre / FS, (pre + m) / FS]
    x += rng.normal(0, 13.0, len(x))
    return x.astype(np.float32), truth, plucks


def run(x):
    path = os.path.join("/tmp", "pitch_synth.f32")
    x.tofile(path)
    out = subprocess.run([os.path.join(HERE, "pitchrun"), path], capture_output=True,
                         text=True, check=True).stdout.split("\n")
    rows = [ln.split() for ln in out if ln]
    return [(float(r[0]), float(r[1]) if int(r[5]) >= 2 else 0.0, r[4]) for r in rows]


def score(frames, truth, plucks):
    ons = [t for t, _, e in frames if e == "ON"]
    t0 = plucks[0]
    onset = min((t - t0 for t in ons if t >= t0 - 0.002), default=np.nan)
    voiced = [(t, hz, 1200 * np.log2(hz / truth[min(int(t * FS), len(truth) - 1)]))
              for t, hz, _ in frames if hz > 0 and t >= t0]
    good, first = 0, np.nan
    for t, hz, c in voiced:
        good = good + 1 if abs(c) < 20 else 0
        if good == 5:
            first = t - 0.002 * 4 - t0
            break
    octs = [t - t0 for t, _, c in voiced if abs(abs(c) - 1200) < 60]
    octave = len(octs)
    held = [abs(c) for t, _, c in voiced if t0 + 0.15 < t < t0 + 0.8]
    return len(ons), onset, first, octave, (np.median(held) if held else np.nan), octs


def main():
    rng = np.random.default_rng(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
    bad = 0
    print("string    Hz  take    h2  ONs  onset ms  pitch ms  octave  error c")
    for s, f0 in enumerate(STRINGS, 1):
        for kind in ("pluck", "slide", "repluck"):
            for h2 in ((0.25, 1.5) if s == 1 else (0.25,)):
                x, truth, plucks = take(kind, f0, rng, h2)
                ons, onset, first, octave, err, octs = score(run(x), truth, plucks)
                want = 2 if kind == "repluck" else 1
                ok = ons == want and octave == 0 and err < 10 and first < 0.06
                bad += not ok
                print("%6d %5.1f  %-7s %4.2f %4d %9.1f %9.1f %7d %8.1f %s %s" % (
                    s, f0, kind, h2, ons, 1e3 * onset, 1e3 * first, octave, err,
                    "" if ok else "  <-- FAIL",
                    ("octave at %s s" % ", ".join("%.3f" % t for t in octs[:4])) if octs else ""))
    print("%d take(s) failed" % bad)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
