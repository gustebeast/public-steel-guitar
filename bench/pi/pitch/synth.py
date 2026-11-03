"""synth.py: score the C detector end to end on synthetic takes, until real plucked captures exist.

    make && python3 synth.py [seed] [--mix sum|diff] [--keep DIR]

Writes each string's takes into a directory in exactly the files `panel capture` writes (takes.py:
.npz, .f32, and the truth as .json), then runs replay.py over that directory -- the same path a
real capture takes. Per string: a pluck from silence then a damp, a pluck then a two-semitone bar
slide, a re-pluck while it still rings, and hands off (no note-on, nothing voiced). String 1 runs
twice more with sensor A's 2nd harmonic at 1.5 x its fundamental, as measured (bench,
2026-11-02; H2A is the factor that gives it with takes.py's sensor geometry).
Levels and the floor are the R1 board's on the MSA (takes.py). Exit status 1 if a take fails.
"""
import os
import shutil
import sys
import tempfile

import numpy as np

import replay
import takes

H2A = 1.8          # sensor A at xs 0.06, plucked at 0.18: its 2nd is 0.83 x its 1st; x 1.8 = 1.5


def main(argv):
    seed = int(next((a for a in argv if a.isdigit()), 1))
    mix = "sum" if "--mix" in argv and argv[argv.index("--mix") + 1] == "sum" else "diff"
    keep = argv[argv.index("--keep") + 1] if "--keep" in argv else None
    d = keep or tempfile.mkdtemp(prefix="pitch_synth_")
    os.makedirs(d, exist_ok=True)
    rng = np.random.default_rng(seed)
    for s, f0 in enumerate(takes.STRINGS, 1):
        for kind in ("pluck", "slide", "repluck", "silence"):
            for h2a in ((1.0, H2A) if s == 1 and kind != "silence" else (1.0,)):
                A, B, tr = takes.take(kind, f0, rng, h2a=h2a)
                tag = "" if h2a == 1.0 else "_h2"
                takes.write(os.path.join(d, "s%02d_%s%s" % (s, kind, tag)), A, B,
                            dict(tr, string=s, seed=seed, h2a=h2a), mix=mix)
    bad = replay.replay(d)
    if keep:
        print("takes kept in %s" % d)
    else:
        shutil.rmtree(d)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
