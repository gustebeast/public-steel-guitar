"""build_stamp: a board says when its inputs moved on, by hash.  py -3.12 test_build_stamp.py

A fake project (elec/x.py, elec/out/x.board.json / .net): stamped it reads current; the
generator edited -> STALE (source); the notes regenerated -> STALE (notes); an ECO's own
notes write, restamped -> current; the tool alone moved -> STALE, said as tool-only; no stamp
-> UNSTAMPED. mtime alone never counts: a touched, unchanged file stays current."""
import os
import tempfile
import time
import build_stamp as bs

d = tempfile.mkdtemp(prefix="stamp_")
os.makedirs(os.path.join(d, "elec", "out"))
src = os.path.join(d, "elec", "x.py")
stem = os.path.join(d, "elec", "out", "x")


def put(p, s):
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(s)


put(src, "placements = {'R3': (0, 0)}\n")
put(stem + ".board.json", "{}")
put(stem + ".net", "(export)")
bad, lines = 0, []
say = lines.append


def want(label, got, exp, has=None):
    global bad
    ok = got == exp and (has is None or any(has in l for l in lines[-1:]))
    print("ok " if ok else "BAD", label, got, lines[-1][:110] if lines and got != "current" else "")
    bad += not ok


want("no stamp", bs.check(stem, say), "unstamped", "UNSTAMPED BOARD")
bs.stamp(stem)
want("just stamped", bs.check(stem, say), "current")
t = time.time() + 100
os.utime(src, (t, t))
want("generator touched, not changed", bs.check(stem, say), "current")
put(src, "placements = {'R3': (20, 0)}\n")
want("generator edited", bs.check(stem, say), "stale", "source (x.py)")
put(src, "placements = {'R3': (0, 0)}\n")
put(stem + ".board.json", '{"placements": 1}')
want("notes regenerated", bs.check(stem, say), "stale", "notes (x.board.json)")
bs.restamp(stem, "notes")
want("ECO's own notes write, restamped", bs.check(stem, say), "current")
real = bs._tree
bs._tree = lambda: "0" * 16
want("only the tool moved", bs.check(stem, say), "stale", "Only the tool moved")
bs._tree = real
raise SystemExit(bad)
