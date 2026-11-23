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


class FreedOutsideRegions(ValueError):
    """A window freed a part bound to a region the round did not name (a held cluster)."""


def _inpoly(x, y, poly):
    inside, n = False, len(poly)
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside


def _clip(poly, x0, x1, y0, y1):
    """poly (intent frame) clipped to the box x0..x1, y0..y1 (Sutherland-Hodgman: the clip box
    is convex, so an L-shaped region clips correctly)."""
    def edge(pts, inside, cut):
        out = []
        for i, q in enumerate(pts):
            p_ = pts[i - 1]
            if inside(q):
                if not inside(p_):
                    out.append(cut(p_, q))
                out.append(q)
            elif inside(p_):
                out.append(cut(p_, q))
        return out
    def at_x(xv):
        return lambda p_, q: (xv, p_[1] + (q[1] - p_[1]) * (xv - p_[0]) / (q[0] - p_[0]))
    def at_y(yv):
        return lambda p_, q: (p_[0] + (q[0] - p_[0]) * (yv - p_[1]) / (q[1] - p_[1]), yv)
    pts = [tuple(v) for v in poly]
    for inside, cut in ((lambda q: q[0] >= x0, at_x(x0)), (lambda q: q[0] <= x1, at_x(x1)),
                        (lambda q: q[1] >= y0, at_y(y0)), (lambda q: q[1] <= y1, at_y(y1))):
        pts = edge(pts, inside, cut)
        if not pts:
            return []
    return [[round(x, 3), round(y, 3)] for x, y in pts]


def _holds_win(poly, wins):
    """Does a region polygon (intent frame) contain a window's (KiCad box) centre? Not mere
    overlap: W49k's window met the moved boost region by 2.3 mm, which named it by accident."""
    return any(_inpoly((a + b) / 2.0 - 100.0, 100.0 - (c + d) / 2.0, poly) for a, b, c, d in wins)


def build(base, src, wins, small=8, keep_nets=("OSC_IN", "OSC_OUT"), keep_prefix=("Y",),
          stem="output_board", why="window hold: source placement outside the re-seat windows",
          by="window_intent", confine=True, keepouts=(), regions=None, force=()):
    """regions: the regions this round may free parts from (None: every region holding a
    window's centre). A freed part bound to any other region raises FreedOutsideRegions -- the self-check
    for a held cluster pulled into a window (W49k, 2026-11-19: the boost cluster moved +17.7 in
    the base still had its OLD seats inside the window, and nine of its parts were freed)."""
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

    force = set(force)          # freed whatever their size (a moved keep-out displaced them: W49k CM5)

    def freeable(ref):
        x, y = pl[ref][:2]
        if ref in force:
            return inwin(x, y)
        return (inwin(x, y) and pads.get(ref, 99) <= small and not (nets.get(ref, set()) & keep_nets)
                and not ref.startswith(tuple(keep_prefix)))

    # ⚠ RELEASE BY THE HOLD'S OWN SEAT, NOT THE SOURCE'S (W49k, 2026-11-19): a base that moves
    # held parts (the widened board's boost cluster, +17.7) still has their OLD seats in the
    # source placement; judged there, a cluster that left the window was released into it.
    def releasable(r):
        x, y = r.get("xy") or pl[r["ref"]][:2]
        ref = r["ref"]
        if ref in force:
            return inwin(x, y)
        return (inwin(x, y) and pads.get(ref, 99) <= small and not (nets.get(ref, set()) & keep_nets)
                and not ref.startswith(tuple(keep_prefix)))
    rel = {r["ref"] for r in R if r["kind"] == "fixed" and r.get("ref") in pl
           and str(r.get("why", "")).startswith("mR: held where mP0 put it") and releasable(r)}
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
                        hold="snapshot", why=why, src=by))   # a remembered position (pi.is_snapshot)
    # each freed part stays inside its OWN region too (lead 2026-11-19, W49k round 2: a window
    # straddling power / compute frees both, but a compute part may re-seat only inside compute):
    # it is bound to its window clipped to its region; unbound parts get the window alone
    bound0 = {}
    for r in R:
        if r["kind"] == "in_region":
            for ref in r.get("refs") or ():
                bound0[ref] = r.get("region")
    rpoly = {r.get("name"): r.get("poly") for r in R if r["kind"] == "region"}
    if confine and free:
        for k, (a, b, c, d) in enumerate(wins):
            mine = [r for r in free if a <= pl[r][0] + 100.0 <= b and c <= 100.0 - pl[r][1] <= d]
            if not mine:
                continue
            # a freed part near the window's edge must still fit where it was: the region grows to
            # cover each member's courtyard (as a circle) at its source position plus GROW_MM
            # (W48: F204 sat 0.4 mm inside the edge, its courtyard past it -> NO ROOM)
            for r in mine:
                cy = parts[r].get("crtyd") or [[0.0, 0.0]]
                rad = max(math.hypot(*v) for v in cy) + GROW_MM
                xk, yk = pl[r][0] + 100.0, 100.0 - pl[r][1]
                a, b, c, d = min(a, xk - rad), max(b, xk + rad), min(c, yk - rad), max(d, yk + rad)
            box = [[a - 100.0, 100.0 - c], [b - 100.0, 100.0 - c], [b - 100.0, 100.0 - d], [a - 100.0, 100.0 - d]]
            groups = {}
            for r in mine:
                groups.setdefault(bound0.get(r) if rpoly.get(bound0.get(r)) else None, []).append(r)
            for reg, refs in sorted(groups.items(), key=lambda kv: str(kv[0])):
                poly, nm = box, "win%d" % k
                if reg is not None:
                    cl = _clip(rpoly[reg], a - 100.0, b - 100.0, 100.0 - d, 100.0 - c)
                    if len(cl) >= 3:
                        poly, nm = cl, "win%d_%s" % (k, reg)
                    else:
                        print("window_intent: window %d misses region %s entirely -- %s bound to the window "
                              "alone" % (k, reg, " ".join(refs)))
                # held parts inside the window are not ITS members: a window that takes in a held
                # connector (W49k CM5: J201) made region_leaks claim it for the window and stop
                seat = {r_["ref"]: r_["xy"] for r_ in R + add if r_["kind"] == "fixed" and r_.get("xy")}
                inside = sorted(r_ for r_, (x_, y_) in seat.items()
                                if a <= x_ + 100.0 <= b and c <= 100.0 - y_ <= d)
                add.append(dict(kind="region", name=nm, poly=poly, transient=True,
                                **({"free": inside} if inside else {}),
                                why="window_intent re-seat window (KiCad %g-%g x %g-%g)%s"
                                    % (a, b, c, d, " within region %s" % reg if nm != "win%d" % k else ""),
                                src=by))
                add.append(dict(kind="in_region", refs=refs, region=nm, hard=True, transient=True,
                                why="freed by window_intent: re-seat inside its own window%s"
                                    % (" and its own region" if nm != "win%d" % k else ""), src=by))
    # --keepout: a box no FREED part may sit in (held parts keep their spot: they are the
    # "except" list). For a power path a window must not crowd -- W48 freed C322 into the
    # 3 A +24V_LED run F203.2 -> J240.9 and quality A1 found it pinched to 0.65 of 1.37 mm.
    for k, (a, b, c, d) in enumerate(keepouts):
        # a held part whose COURTYARD reaches the box is excepted too, not just one whose
        # centre is in it (W48k: F203 and J240 sit beside the box, courtyards 1.5-3 mm in,
        # and the intent check stopped the flow on them)
        def _touches(r, x, y):
            cy = parts.get(r, {}).get("crtyd") or [[0.0, 0.0]]
            rad = max(math.hypot(*v) for v in cy)
            xk, yk = x + 100.0, 100.0 - y
            dx, dy = max(a - xk, 0.0, xk - b), max(c - yk, 0.0, yk - d)
            return math.hypot(dx, dy) <= rad
        inside = sorted(r for r, (x, y, _) in pl.items() if r not in free and _touches(r, x, y))
        add.append(dict(kind="keepout", poly=[[a - 100.0, 100.0 - c], [b - 100.0, 100.0 - c],
                                              [b - 100.0, 100.0 - d], [a - 100.0, 100.0 - d]],
                        **({"except": inside} if inside else {}), transient=True,
                        why="window_intent keep-out %d (KiCad %g-%g x %g-%g): no freed part here" % (k, a, b, c, d),
                        src=by))
    # SELF-CHECK: every freed part must belong to a region the round names (or no region)
    bound = {}
    for r in R:
        if r["kind"] == "in_region":
            for ref in r.get("refs") or ():
                bound[ref] = r.get("region")
    polys = {r.get("name"): r.get("poly") or [] for r in R if r["kind"] == "region"}
    ok = set(regions) if regions is not None else {n for n, pg in polys.items() if pg and _holds_win(pg, wins)}
    bad = sorted("%s (region %s)" % (ref, bound[ref]) for ref in free if bound.get(ref) and bound[ref] not in ok)
    if bad:
        raise FreedOutsideRegions("window freed %d part(s) bound to regions it does not name (%s): %s"
                                  % (len(bad), ", ".join(sorted(ok)) or "none", "; ".join(bad)))
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
    ap.add_argument("--free", action="append", default=[], help="a ref freed whatever its pad count "
                    "(it must sit in a window); comma lists allowed")
    ap.add_argument("--region", action="append", help="a region this round may free parts from "
                    "(default: every region holding a window's centre); a freed part of any other stops the build")
    a = ap.parse_args()
    wins = [tuple(float(v) for v in w.split(",")) for w in a.win]
    rules, rel, free, nheld = build(json.load(open(a.base)), a.src, wins, a.small,
                                    a.keep_net or ("OSC_IN", "OSC_OUT"), a.keep_prefix or ("Y",), a.stem,
                                    confine=not a.no_confine,
                                    keepouts=[tuple(float(v) for v in w.split(",")) for w in a.keepout],
                                    regions=a.region, force=[x for v in a.free for x in v.split(",") if x])
    json.dump(rules, open(a.out, "w"), indent=0)
    print("released mP0 holds:", " ".join(rel))
    print("held already", nheld, "added holds", sum(1 for r in rules if r.get("transient") and r["kind"] == "fixed"), "free", len(free))
    print("free:", " ".join(free))


if __name__ == "__main__":
    main()
