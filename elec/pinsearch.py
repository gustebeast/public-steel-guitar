"""Score a string->pair assignment by routing THE SENSORS ALONE, fast.

THE WHOLE BOARD IS THE WRONG UNIT FOR THIS QUESTION. A permutation moves twenty nets and
nothing else -- the strip geometry, the ULPI bus, the USB pair and the power entry are
identical in every candidate. Routing 96 nets to learn about 20 costs ten minutes a
trial, which caps the search at a handful of guesses, and guesses are exactly what keeps
being refuted on this board.

So a trial hands freerouting a DSN carrying ONLY the TIA_OUT_* nets, on the real
placement, with the pre-laid wiring dropped. Every PAD is still there and still an
obstacle, so the escape out of U6 and the squeeze past the strip's own parts are real;
what is removed is competition from nets a permutation cannot change.

IT RANKS CANDIDATES, IT DOES NOT ACCEPT THEM. Four cheap metrics have predicted
improvements the router refuted here -- straight-line crossings, weighted far-edge cost,
per-edge inversions, and the near/far split driven to zero by rotating the MCU. This is
not one of those: it IS the router, on the real placement. But it cannot see a candidate
that would have made the other 76 nets route differently, because they are absent.
Confirm a winner with finish.py before believing it.

UNCONNECTED COUNT WILL NOT DISCRIMINATE. With the board to itself the analog nets mostly
route whatever the assignment, so the score is VIAS first and length second: a mapping
that forces nets across each other pays in layer changes, which is the cost that matters
in a 13.6 mm strip.

    py -3.12 elec/pinsearch.py                       -- score the mapping as it stands
    py -3.12 elec/pinsearch.py 1,10,3,4,5,6,7,8,9,2  -- string i takes string P[i]'s pair
"""
import io
import math
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STEM = os.path.join(HERE, "out", "optical")
SRC = os.path.join(HERE, "optical.py")
KI = r"C:\Program Files\KiCad\10.0\bin\python.exe"
JAVA = os.path.expandvars(r"%LOCALAPPDATA%\Programs\temurin\jdk-25.0.4.1+1-jre\bin\java.exe")
JAR = (r"C:\Users\gus\AppData\Local\Temp\claude"
       r"\C--Users-gus-Sync-Documents-Archive-3D-public-steel-guitar"
       r"\d7576032-b257-4aee-8a45-89e587fe4007\scratchpad\freerouting.jar")
ANALOG = re.compile(r"^TIA_OUT_[0-9]+[AB]$")
PAIR_RE = re.compile(r'\("([^"]+)",\s*"([^"]+)"\)')


def permuted(src, perm):
    """ADC_PAIRS rewritten so string i owns the pair string perm[i-1] owns today."""
    m = re.search(r"ADC_PAIRS = \(\n((?:.*\n)*?)\)\n", src)
    rows = [l for l in m.group(1).split("\n") if l.strip().startswith("(")]
    assert len(rows) == 10, len(rows)
    pins = [PAIR_RE.search(r).groups() for r in rows]
    new = [pins[perm[i] - 1] for i in range(10)]
    body = "".join('    ("%s", "%s"),   # string %d\n' % (a, b, i + 1)
                   for i, (a, b) in enumerate(new))
    return src[:m.start(1)] + body + src[m.end(1):]


def filter_dsn(src, dst):
    """Keep only the analog nets, and drop the pre-laid wiring so they route free."""
    txt = io.open(src, encoding="utf-8", errors="replace").read()
    i, j = txt.index("  (network"), txt.index("  (wiring")
    blk = txt[i:j]
    kept = [m.group(0) for m in
            re.finditer(r"    \(net (\S+)\n(?:      .*\n)*?    \)\n", blk)
            if ANALOG.match(m.group(1))]
    head = blk[:blk.index("    (net ")]
    io.open(dst, "w", encoding="utf-8").write(
        txt[:i] + head + "".join(kept) + "  )\n  (wiring\n  )\n)\n")
    return len(kept)


def trial(perm=None):
    t0 = time.time()
    original = io.open(SRC, encoding="utf-8").read()
    try:
        if perm:
            io.open(SRC, "w", encoding="utf-8", newline="\r\n").write(permuted(original, perm))
        r = subprocess.run([sys.executable, SRC], cwd=ROOT, capture_output=True, text=True)
        if r.returncode:
            return {"error": (r.stderr or r.stdout).strip().split("\n")[-1][:110]}
        subprocess.run([KI, os.path.join(HERE, "layout.py"), STEM], cwd=ROOT,
                       capture_output=True)
        subprocess.run([KI, os.path.join(HERE, "route.py"), STEM, "--dsn-only"], cwd=ROOT,
                       capture_output=True)
    finally:
        io.open(SRC, "w", encoding="utf-8", newline="\r\n").write(original)
    n = filter_dsn(STEM + ".dsn", STEM + ".solo.dsn")
    subprocess.run([JAVA, "-Djava.awt.headless=true", "-jar", JAR,
                    "-de", STEM + ".solo.dsn", "-do", STEM + ".solo.ses",
                    "-mp", "6", "-mt", "1"], capture_output=True)
    ses = io.open(STEM + ".solo.ses", encoding="utf-8", errors="replace").read()
    length = 0.0
    for m in re.finditer(r"\(path\s+\S+\s+[0-9.]+\s+([^()]+)\)", ses):
        xs = [float(v) for v in m.group(1).split()]
        pts = list(zip(xs[0::2], xs[1::2]))
        length += sum(math.dist(pts[k], pts[k + 1]) for k in range(len(pts) - 1)) / 10000.0
    return {"nets": n, "vias": ses.count("(via "), "mm": round(length, 1),
            "sec": round(time.time() - t0, 1)}


if __name__ == "__main__":
    p = [int(x) for x in sys.argv[1].split(",")] if len(sys.argv) > 1 else None
    print("perm %-30s %s" % (p or "as-is", trial(p)))
