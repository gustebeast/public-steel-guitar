"""Window re-seat intent: keep a finished placement, free only the small parts inside some windows.

    py -3.12 window_intent.py BASE.json SRC_DIR OUT.json --win x0,x1,y0,y1 [--win ...]
        [--small 8] [--keep-net OSC_IN --keep-net OSC_OUT] [--keep-prefix Y]

BASE.json  the intent rules to start from. Holds marked "transient" (a previous window round's) are
           dropped first, so rounds stack: the new source placement replaces them.
SRC_DIR    a place_flow output dir (output_board.board.json + .parts.json) whose placement is kept.
--win      KiCad coordinates (x0, x1, y0, y1); the intent's local frame is x-100, 100-y.

Every placed part outside the windows gets a hard, transient "fixed" hold at its SRC_DIR position
(transient: region_leaks does not count it as bound, see place_intent). Inside a window, parts with
<= --small pads go free unless they touch a --keep-net or their ref starts with --keep-prefix; old
"mR: held where mP0 put it" holds on such parts are released, since they pin the very cluster that
fails. Each freed part is held IN ITS OWN WINDOW (a "win<k>" region + hard in_region; --no-confine
drops that). --keepout x0,x1,y0,y1 bans freed parts from a box (a power path), held parts excepted): unconfined, intent48's D201 left the ribbon corner for the MCU window 46 mm away and
R84 went 22.6 mm. place_init keeps the last in_region rule for a part, so the window binding wins
over the part's own region; check the result with region_strays. Use it for placement-list rounds: screen with place_flow --to-routability, then replays.
"""
import argparse
import json
import math
import os


GROW_MM = 1.0


def build(base, src, wins, small=8, keep_nets=("OSC_IN", "OSC_OUT"), keep_prefix=("Y",),
          stem="output_board", why="window hold: source placement outside the re-seat windows",
          by="window_intent", confine=True, keepouts=()):
    R = [r for r in base if not r.get("transient")]
    pl = json.load(open(os.path.join(src, stem + ".board.json")))["placements"]
    parts = json.load(open(os.path.join(src, stem + ".parts.json")))["parts"]
    pads, nets = {}, {}
    for ref, p in parts.items():
        pp = p.get("pads", [])
        pads[ref] = len(pp)
        nets[ref] = {q.get("net") for q in pp if isinstance(q, dict)}
    keep_nets = set(keep_nets)

    def inwin(x, y):
        xk, yk = x + 100.0, 100.0 - y
        return any(a <= xk <= b and c <= yk <= d for a, b, c, d in wins)

    def freeable(ref):
        x, y = pl[ref][:2]
        return (inwin(x, y) and pads.get(ref, 99) <= small and not (nets.get(ref, set()) & keep_nets)
                and not ref.startswith(tuple(keep_prefix)))

    rel = {r["ref"] for r in R if r["kind"] == "fixed" and r.get("ref") in pl
           and str(r.get("why", "")).startswith("mR: held where mP0 put it") and freeable(r["ref"])}
    R = [r for r in R if not (r["kind"] == "fixed" and r.get("ref") in rel)]
    held = {r["ref"] for r in R if r["kind"] in ("fixed", "pin", "panel") and r.get("ref")}
    free, add = [], []
    for ref, (x, y, rot) in pl.items():
        if ref in held:
            continue
        if freeable(ref):
            free.append(ref)
            continue
        add.append(dict(kind="fixed", ref=ref, xy=[x, y], rot=rot, hard=True, transient=True,
                        why=why, src=by))
    if confine and free:
        for k, (a, b, c, d) in enumerate(wins):
            mine = [r for r in free if a <= pl[r][0] + 100.0 <= b and c <= 100.0 - pl[r][1] <= d]
            if not mine:
                continue
            nm = "win%d" % k
            # a freed part near the window's edge must still fit where it was: the region grows to
            # cover each member's courtyard (as a circle) at its source position plus GROW_MM
            # (W48: F204 sat 0.4 mm inside the edge, its courtyard past it -> NO ROOM)
            for r in mine:
                cy = parts[r].get("crtyd") or [[0.0, 0.0]]
                rad = max(math.hypot(*v) for v in cy) + GROW_MM
                xk, yk = pl[r][0] + 100.0, 100.0 - pl[r][1]
                a, b, c, d = min(a, xk - rad), max(b, xk + rad), min(c, yk - rad), max(d, yk + rad)
            add.append(dict(kind="region", name=nm, poly=[[a - 100.0, 100.0 - c], [b - 100.0, 100.0 - c],
                                                          [b - 100.0, 100.0 - d], [a - 100.0, 100.0 - d]],
                            transient=True, why="window_intent re-seat window (KiCad %g-%g x %g-%g)" % (a, b, c, d),
                            src=by))
            add.append(dict(kind="in_region", refs=mine, region=nm, hard=True, transient=True,
                            why="freed by window_intent: re-seat inside its own window", src=by))
    # --keepout: a box no FREED part may sit in (held parts keep their spot: they are the
    # "except" list). For a power path a window must not crowd -- W48 freed C322 into the
    # 3 A +24V_LED run F203.2 -> J240.9 and quality A1 found it pinched to 0.65 of 1.37 mm.
    for k, (a, b, c, d) in enumerate(keepouts):
        inside = sorted(r for r, (x, y, _) in pl.items() if r not in free
                        and a <= x + 100.0 <= b and c <= 100.0 - y <= d)
        add.append(dict(kind="keepout", poly=[[a - 100.0, 100.0 - c], [b - 100.0, 100.0 - c],
                                              [b - 100.0, 100.0 - d], [a - 100.0, 100.0 - d]],
                        **({"except": inside} if inside else {}), transient=True,
                        why="window_intent keep-out %d (KiCad %g-%g x %g-%g): no freed part here" % (k, a, b, c, d),
                        src=by))
    return R + add, sorted(rel), sorted(free), len(held)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("base"); ap.add_argument("src"); ap.add_argument("out")
    ap.add_argument("--win", action="append", required=True)
    ap.add_argument("--small", type=int, default=8)
    ap.add_argument("--keep-net", action="append")
    ap.add_argument("--keep-prefix", action="append")
    ap.add_argument("--stem", default="output_board")
    ap.add_argument("--no-confine", action="store_true")
    ap.add_argument("--keepout", action="append", default=[], help="x0,x1,y0,y1 (KiCad): no freed part inside")
    a = ap.parse_args()
    wins = [tuple(float(v) for v in w.split(",")) for w in a.win]
    rules, rel, free, nheld = build(json.load(open(a.base)), a.src, wins, a.small,
                                    a.keep_net or ("OSC_IN", "OSC_OUT"), a.keep_prefix or ("Y",), a.stem,
                                    confine=not a.no_confine,
                                    keepouts=[tuple(float(v) for v in w.split(",")) for w in a.keepout])
    json.dump(rules, open(a.out, "w"), indent=0)
    print("released mP0 holds:", " ".join(rel))
    print("held already", nheld, "added holds", sum(1 for r in rules if r.get("transient") and r["kind"] == "fixed"), "free", len(free))
    print("free:", " ".join(free))


if __name__ == "__main__":
    main()
