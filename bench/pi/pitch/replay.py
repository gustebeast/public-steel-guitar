"""replay.py: run the C detector over a directory of takes, real or synthetic, end to end.

    make && python3 replay.py <dir> [--mix sum|diff]

Every <stem>.f32 in <dir> is run through `pitchrun` (with --mix, the .npz's SUM or DIFF instead).
A take is SCORED if a <stem>.json sits beside it (takes.py writes one for every synthetic take);
otherwise it is REPORTED: its note-ons, and the pitch each held, for a person to hold against
what was played. Exit status 1 if any scored take fails.

A real capture (`python3 -m publicbench.panel capture --strings 1,7,10 --seconds 10` writes
/tmp/take_s<N>.npz and .f32) is dropped in as it is. To score one, write its .json by hand:
    {"plucks": [1.20, 3.05], "expect_on": 2,
     "pitch": [[0, 293.3], [9.9, 293.3]],      breakpoints, s and Hz, straight lines between
     "held": [1.35, 2.9]}                      where the median error is taken (or null)
"plucks" are the times you plucked (read off the envelope in a plot, or the report below);
"expect_on" how many note-ons the take should give; "pitch" what the string was sounding.

A take passes on:
  ons      == expect_on (a slide or a damp gives none of its own)
  onset    first pluck -> its ON, under 25 ms              (envelope; design 1-2 ms + filter)
  pitch    first pluck -> 5 committed frames in a row within 20 cents, under 60 ms
  octave   committed frames an octave off: 0
  error    median |cents| over `held`, under 10
Committed means steady >= 2 (pitch.h).
"""
import glob
import json
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
STEP = 0.002            # a frame every 2 ms (pitch.h PITCH_HOP at 12 kHz)


def run(path):
    """[(t, committed Hz or 0, event)] for one float32 file."""
    out = subprocess.run([os.path.join(HERE, "pitchrun"), path], capture_output=True,
                         text=True, check=True).stdout.split("\n")
    rows = [ln.split() for ln in out if ln]
    return [(float(r[0]), float(r[1]) if int(r[5]) >= 2 else 0.0, r[4]) for r in rows]


def truth_hz(pts, t):
    p = np.asarray(pts, dtype=float)
    return float(np.interp(t, p[:, 0], p[:, 1]))


def score(frames, tr):
    """(ons, onset s, pitch s, octave count, median error cents, octave times, pass)"""
    ons = [t for t, _, e in frames if e == "ON"]
    plucks = tr.get("plucks") or []
    if not plucks:                                      # hands off: nothing may be heard
        voiced = sum(1 for _, hz, _ in frames if hz > 0)
        return len(ons), np.nan, np.nan, 0, np.nan, [], len(ons) == 0 and voiced == 0
    t0 = plucks[0]
    onset = min((t - t0 for t in ons if t >= t0 - 0.002), default=np.nan)
    voiced = [(t, 1200 * np.log2(hz / truth_hz(tr["pitch"], t)))
              for t, hz, _ in frames if hz > 0 and t >= t0]
    good, first = 0, np.nan
    for t, c in voiced:
        good = good + 1 if abs(c) < 20 else 0
        if good == 5:
            first = t - STEP * 4 - t0
            break
    octs = [t - t0 for t, c in voiced if abs(abs(c) - 1200) < 60]
    h = tr.get("held")
    held = [abs(c) for t, c in voiced if h and h[0] < t < h[1]]
    err = np.median(held) if held else np.nan
    ok = (len(ons) == tr.get("expect_on", len(plucks)) and onset < 0.025 and first < 0.06
          and not octs and (err < 10 if h else True))
    return len(ons), onset, first, len(octs), err, octs, ok


def report(frames):
    """For a take with no truth: each note-on, and the pitch the string settled on after it."""
    ons = [i for i, (_, _, e) in enumerate(frames) if e == "ON"]
    lines = []
    for j, i in enumerate(ons):
        end = ons[j + 1] if j + 1 < len(ons) else len(frames)
        hz = [f[1] for f in frames[i:end] if f[1] > 0]
        lines.append("    ON at %7.3f s: %s" % (
            frames[i][0], ("%.1f Hz median of %d frames (%.1f to %.1f)" % (
                np.median(hz), len(hz), min(hz), max(hz))) if hz else "never committed a pitch"))
    voiced = sum(1 for f in frames if f[1] > 0)
    lines.append("    %d note-on(s), %d committed frame(s) of %d" % (len(ons), voiced, len(frames)))
    return "\n".join(lines)


def replay(d, mix=None):
    """Score or report every take in d; returns the number of failures."""
    stems = sorted(p[:-4] for p in glob.glob(os.path.join(d, "*.f32")))
    if not stems:
        print("no .f32 takes in %s" % d)
        return 1
    bad = 0
    print("take                      ONs  onset ms  pitch ms  octave  error c")
    for stem in stems:
        path = stem + ".f32"
        if mix:
            z = np.load(stem + ".npz")
            path = stem + "." + mix + ".tmp.f32"
            z[mix].astype(np.float32).tofile(path)
        frames = run(path)
        if mix:
            os.remove(path)
        name = os.path.basename(stem)
        if not os.path.exists(stem + ".json"):
            print("%-24s  (no .json: reported, not scored)\n%s" % (name, report(frames)))
            continue
        with open(stem + ".json") as fh:
            tr = json.load(fh)
        ons, onset, first, octave, err, octs, ok = score(frames, tr)
        bad += not ok
        print("%-24s %4d %9.1f %9.1f %7d %8.1f %s%s" % (
            name, ons, 1e3 * onset, 1e3 * first, octave, err, "" if ok else "  <-- FAIL",
            ("  octave at %s s" % ", ".join("%.3f" % t for t in octs[:4])) if octs else ""))
    print("%d take(s) failed" % bad)
    return bad


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    mix = None
    for a in argv:
        if a.startswith("--mix"):
            mix = a.split("=", 1)[1] if "=" in a else argv[argv.index(a) + 1]
            args = [x for x in args if x != mix]
    if not args:
        print(__doc__)
        return 2
    return 1 if replay(args[0], mix) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
