"""Route a HANDFUL of nets alone on the real placement -- the fast iteration loop.

THE WHOLE-BOARD ROUTE IS THE WRONG UNIT FOR "why does this net fail". optical takes
FIFTY-SEVEN MINUTES. Every placement idea therefore costs an hour to refute, which is
what turned six bad ideas into six wasted afternoons: by the time a result lands the
reasoning that produced it has gone cold, and the temptation is to change three things
at once so the hour buys more -- at which point the result cannot attribute anything.

So hand freerouting a DSN carrying only the nets in question, on the real placement,
with every pad still an obstacle. A trial is TWELVE SECONDS against the full route's
fifty-seven minutes.

READ THE ANSWER THE RIGHT WAY ROUND. This is generalised from elec/pinsearch.py and it
inherits the asymmetry that matters:

  * FAILS  -> decisive. With the competing nets removed the net had the board nearly to
             itself and still could not get through. That is geometry, and no amount of
             routing order or pass count will fix it: the placement has to move.
  * ROUTES -> weak. It says a path exists when nothing else wants the space, which is
             not the question the full board asks. Confirm with finish.py.

That asymmetry is the whole value. Six of this board's dead ends -- U15's haul, the
straight +3V3D link, the 3-segment dogleg, the Ci/Cm swap -- were hours spent proving
impossibility the slow way.

    py -3.12 .ins/solo.py I2C2_SCL,SAI_SD4     -- these nets
    py -3.12 .ins/solo.py --from-drc           -- every net the last full route failed
    py -3.12 .ins/solo.py --from-drc --wiring  -- ... carrying the pre-laid copper (see below)

⚠ IT ROUTES THE DSN ON DISK. It does NOT run the generator: see finish.py's
_check_fresh for what a stale netlist costs. Refresh with
    py -3.12 elec/optical.py
    <kicad-python> elec/layout.py elec/out/optical
    <kicad-python> elec/route.py elec/out/optical --dsn-only
"""
import io
import json
import math
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STEM = os.path.join(ROOT, "elec", "out", "optical")
JAVA = os.path.expandvars(
    r"%LOCALAPPDATA%\Programs\temurin\jdk-25.0.4.1+1-jre\bin\java.exe")
JAR = os.path.expandvars(
    r"%LOCALAPPDATA%\Programs\freerouting\freerouting.jar")


def failing_nets(drc=STEM + ".finish.drc.json"):
    """The nets the last full route left unconnected, in the order it reported them."""
    d = json.load(io.open(drc, encoding="utf-8"))
    out = []
    for u in d.get("unconnected_items", []):
        for it in u.get("items", []):
            m = re.search(r"\[([^\]]+)\]", it.get("description", ""))
            if m and m.group(1) not in out:
                out.append(m.group(1))
    return out


def filter_dsn(src, dst, nets, keep_wiring=False):
    """Keep only `nets` in the network block, and by default drop the wiring.

    ⚠ KEEPING THE WIRING LOOKS RIGHT AND IS NOT, WHICH COST THE FIRST TRIAL. The pre-laid
    segments are most of what the strip's traffic has to squeeze past, so carrying them
    in as obstacles ought to be the more faithful question. But the DSN's wires name nets
    that this filter has just removed from the network block, and freerouting does not
    reject them -- it reports "0 unrouted and 624 violations" and returns a session with
    no new copper at all. An answer of NOTHING ROUTED that means "the input was
    malformed" is indistinguishable from the one finding this tool exists to make.

    So `keep_wiring` stays available and stays off. Without it the net is routed on a
    board that is bare copper and full pads -- which only sharpens the reading below:
    a net that fails HERE fails with the board to itself.
    """
    txt = io.open(src, encoding="utf-8", errors="replace").read()
    i, j = txt.index("  (network"), txt.index("  (wiring")
    blk, want = txt[i:j], set(nets)
    seen, kept = set(), []
    for m in re.finditer(r"    \(net (\S+)\n(?:      .*\n)*?    \)\n", blk):
        seen.add(m.group(1))
        if m.group(1) in want:
            kept.append(m.group(0))
    missing = sorted(want - seen)
    if missing:
        raise SystemExit("not nets on this board: %s" % ", ".join(missing))
    wiring = txt[j:] if keep_wiring else "  (wiring\n  )\n)\n"
    head = blk[:blk.index("    (net ")]
    io.open(dst, "w", encoding="utf-8").write(txt[:i] + head + "".join(kept)
                                              + "  )\n" + wiring)
    return len(kept)


def route(nets, keep_wiring=False, passes=6):
    t0 = time.time()
    n = filter_dsn(STEM + ".dsn", STEM + ".solo.dsn", nets, keep_wiring)
    r = subprocess.run([JAVA, "-Djava.awt.headless=true", "-jar", JAR,
                        "-de", STEM + ".solo.dsn", "-do", STEM + ".solo.ses",
                        "-mp", str(passes), "-mt", "1"],
                       capture_output=True, text=True)
    log = (r.stdout or "") + (r.stderr or "")
    ses = io.open(STEM + ".solo.ses", encoding="utf-8", errors="replace").read()
    # per-net: how much copper came back, and on how many wires.
    # ⚠ THE .ses NESTS WIRES INSIDE THEIR NET, it does not tag each one. A regex looking
    # for a trailing (net X) after every (path ...) matches nothing and reports every net
    # as NOTHING ROUTED -- which is this tool's one alarming output, raised by a parser
    # bug rather than by the board.
    per, length = {}, 0.0
    for nm in re.finditer(r'      \(net "([^"]+)"\n((?:        .*\n)*)', ses):
        name, body = nm.group(1), nm.group(2)
        e = per.setdefault(name, {"wires": 0, "mm": 0.0, "vias": 0})
        e["vias"] += body.count("(via ")
        # coordinates come two to a line, so a per-number line pattern matches nothing
        for pm in re.finditer(r"\(path \S+ [0-9.]+\n((?:[ \t]+-?[0-9.]+[ \t]+-?[0-9.]+\n)+)",
                              body):
            xs = [float(v) for v in pm.group(1).split()]
            pts = list(zip(xs[0::2], xs[1::2]))
            d = sum(math.dist(pts[k], pts[k + 1])
                    for k in range(len(pts) - 1)) / 10000.0
            e["wires"] += 1
            e["mm"] += d
            length += d
    # freerouting says so itself when it gives up on a connection
    incomplete = [l.strip() for l in log.splitlines()
                  if "incomplete" in l.lower() or "unrouted" in l.lower()]
    return {"nets": n, "vias": ses.count("(via "), "mm": round(length, 1),
            "per": per, "incomplete": incomplete, "sec": round(time.time() - t0, 1)}


if __name__ == "__main__":
    args = [a for a in sys.argv[1:]]
    free = "--wiring" in args
    args = [a for a in args if a != "--wiring"]
    if not args or args[0] == "--from-drc":
        nets = failing_nets()
        print("from the last full route: %d failing net(s)" % len(nets))
    else:
        nets = [s for s in args[0].split(",") if s]
    res = route(nets, keep_wiring=free)
    print("%d net(s), %s pre-laid copper, %.0fs: %d via(s), %.1f mm"
          % (res["nets"], "with" if free else "without", res["sec"],
             res["vias"], res["mm"]))
    for net in nets:
        e = res["per"].get(net)
        print("  %-14s %s" % (net, "%2d wire(s) %6.1f mm, %d via(s)"
                              % (e["wires"], e["mm"], e["vias"])
                              if e else "NOTHING ROUTED"))
    for l in res["incomplete"]:
        print("  ! %s" % l)
