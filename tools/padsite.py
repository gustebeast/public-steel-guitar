"""Find a landing site for each bring-up pad on the FINISHED board.

⚠ THIS IS A REBUILD, NOT A REVIVAL. The original lived in `scratchpad/` and that directory
no longer exists -- no maze.py, no verify_path.py, no repair_search.track_gap. The tick
prompt still names them. Anything that has to be re-run every time the route changes cannot
live in a scratch directory, so this one is in tools/ and is committed.

WHY IT EXISTS. The six bring-up pads (TP6..TP11) are placed AFTER routing and are invisible
to the router -- see `post_route_refs`. That is what makes them cheap: moving one cannot
disturb a single track. It is also what makes them fragile: a site is only valid for the
route it was searched against, so EVERY placement change invalidates all six. Left stale they
cost real nets -- in the run that prompted this rebuild, four of nine unconnected items were
bring-up pads and both violations were TP10 sitting on a ULPI_D1 via.

WHAT A GOOD SITE IS, in the original's words: a clear circle that ALREADY OVERLAPS ITS OWN
NET'S COPPER, so the pad needs no track of its own. A pad that needs a track is a new net for
the router to carry, which is how these cost connections in the first place.
Rejected sites: inside any footprint's courtyard (a pad under a part is electrically legal
and physically unprobeable), too close to foreign copper, or off the board.

    py -3.12 -m tools.padsite            # report sites for every post-route pad
"""
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "elec"))

BOARD = os.path.join(ROOT, "elec", "out", "optical.kicad_pcb")
PAD_D = 1.0                       # the TP pad itself
PROBE_D = 1.5                     # the clear circle a probe tip needs
CLR = 0.127                       # this board's copper rule


def parse(path):
    s = open(path, encoding="utf-8").read()
    i = s.index("(")
    BS = chr(92)

    def node():
        nonlocal i
        i += 1
        out, buf = [], ""
        while True:
            c = s[i]
            if c == "(":
                if buf:
                    out.append(buf)
                    buf = ""
                out.append(node())
            elif c == ")":
                if buf:
                    out.append(buf)
                i += 1
                return out
            elif c == '"':
                if buf:
                    out.append(buf)
                    buf = ""
                i += 1
                t = ""
                while s[i] != '"':
                    if s[i] == BS:
                        i += 1
                    t += s[i]
                    i += 1
                i += 1
                out.append(t)
            elif c in " \t\r\n":
                if buf:
                    out.append(buf)
                    buf = ""
                i += 1
            else:
                buf += c
                i += 1

    return node()


def kids(n, tag):
    return [c for c in n if isinstance(c, list) and c and c[0] == tag]


def one(n, tag):
    k = kids(n, tag)
    return k[0] if k else None


def seg_d(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    l2 = dx * dx + dy * dy
    t = 0.0 if l2 == 0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / l2))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def main():
    import elec.optical as O
    import src.optical_pickup as OP

    root = parse(BOARD)
    # ⚠ A SEGMENT'S (net ...) CARRIES THE NAME, NOT AN INDEX. Looking it up through a
    # number->name table built from top-level (net N "name") nodes silently produced "" for
    # every track, so no point on the board ever matched its own net and all six pads came
    # back "NO SITE". The rejection counters are what exposed it -- 40548 of 40548 points
    # failing the SAME criterion is a broken test, not a full board.

    segs, vias, courts = [], [], []
    for g in root:
        if not (isinstance(g, list) and g):
            continue
        if g[0] == "segment":
            a, b, n = one(g, "start"), one(g, "end"), one(g, "net")
            segs.append((float(a[1]), float(a[2]), float(b[1]), float(b[2]),
                         float(one(g, "width")[1]), (n[1] if n else ""),
                         one(g, "layer")[1]))
        elif g[0] == "via":
            a, n = one(g, "at"), one(g, "net")
            vias.append((float(a[1]), float(a[2]), float(one(g, "size")[1]),
                         (n[1] if n else "")))
        elif g[0] == "footprint":
            fa = one(g, "at")
            fx, fy = float(fa[1]), float(fa[2])
            ref = "?"
            for pr in kids(g, "property"):
                if pr[1] == "Reference":
                    ref = pr[2]
            courts.append((ref, fx, fy))

    CX, CY = O.CX, O.CY
    poly = O.BOARD_NOTES["outline_poly"]
    bx0 = min(p[0] for p in poly) + 100.0
    bx1 = max(p[0] for p in poly) + 100.0
    by0 = 100.0 - max(p[1] for p in poly)
    by1 = 100.0 - min(p[1] for p in poly)

    # ⚠ THE NET PER PAD COMES FROM THE SOURCE, NOT THE BOARD. Reading it back off the
    # footprint failed silently (every pad came out "net unknown") and a silent failure in a
    # SEARCH tool is the worst kind -- it reports "no site" exactly like a real dead end.
    # optical.py documents each pad's net in its own description, so that is the authority.
    TP_NET = {"TP6": "I2C2_SDA", "TP7": "I2C2_SCL", "TP8": "BOOT0",
              "TP9": "+24V", "TP10": "+5V", "TP11": "+3V3A"}
    want = {r: None for r in O.BOARD_NOTES["post_route_refs"] if r.startswith("TP")}
    tp_net = {r: TP_NET[r] for r in want if r in TP_NET}
    missing = [r for r in want if r not in TP_NET]
    assert not missing, "no net recorded for %s -- add it to TP_NET" % missing
    print("post-route pads: %s" % ", ".join(sorted(want)))
    print("board x %.2f..%.2f  y %.2f..%.2f\n" % (bx0, bx1, by0, by1))

    R_SELF = PAD_D / 2.0
    R_KEEP = PROBE_D / 2.0 + CLR
    for ref in sorted(want):
        net = tp_net.get(ref, "")
        if not net:
            print("%-5s  net unknown -- not on the board?" % ref)
            continue
        best = []
        # ⚠ COUNT WHY SITES ARE REJECTED. The first version returned "NO SITE" for all six
        # pads, which is the signature of a broken filter, not six dead ends -- and a search
        # tool that cannot say WHY it found nothing is indistinguishable from a broken one.
        # The bug was using distance from a footprint ORIGIN (> 3.0 mm) as a stand-in for
        # "not under a part". On a board carrying 253 parts that rejects nearly the whole
        # surface. Courtyards are read properly now, from the CAD's own table.
        n_tot = n_own = n_foreign = n_part = 0
        courts_xy = []
        for p_ in OP.PARTS:
            cr = OP.CRTYD.get(p_.get("pkg"))
            if not cr:
                continue
            w_, h_ = cr
            if abs(float(p_.get("rot", 0)) % 180 - 90) < 1e-6:
                w_, h_ = h_, w_
            fx_ = (p_["x"] - CX) + 100.0
            fy_ = 100.0 - (p_["y"] - CY)
            courts_xy.append((fx_, fy_, w_ / 2.0, h_ / 2.0))
        x = bx0 + 1.5
        while x <= bx1 - 1.5:
            y = by0 + 1.5
            while y <= by1 - 1.5:
                n_tot += 1
                own = 1e9
                foreign = 1e9
                for sx1, sy1, sx2, sy2, w, n, lay in segs:
                    if lay != "F.Cu":
                        continue
                    d = seg_d(x, y, sx1, sy1, sx2, sy2) - w / 2.0
                    if n == net:
                        own = min(own, d)
                    elif d < foreign:
                        foreign = d
                for vx, vy, vs, n in vias:
                    d = math.hypot(x - vx, y - vy) - vs / 2.0
                    if n == net:
                        own = min(own, d)
                    elif d < foreign:
                        foreign = d
                if own > R_SELF:
                    n_own += 1
                elif foreign < R_KEEP:
                    n_foreign += 1
                else:
                    under = False
                    for fx_, fy_, hw_, hh_ in courts_xy:
                        if abs(x - fx_) <= hw_ + R_KEEP and abs(y - fy_) <= hh_ + R_KEEP:
                            under = True
                            break
                    if not under:
                        # ⚠ AND NOT UNDER A SCREW HEAD EITHER. A pad a probe cannot reach is
                        # no more useful than a pad under a part, and the mounting screws are
                        # not in the CRTYD table -- the first run put TP8 3.47 mm from the
                        # tail mount's axis, inside a 7.6 mm button head.
                        # ⚠ COURTYARD AGAINST THE HEAD CIRCLE, exactly as
                        # optical_pickup._assert_mount_heads_clear does it -- NOT centre to
                        # centre. Written with centres first, and it passed TP8 at 5.23 mm
                        # which the assert then rejects at -0.33: a 2.5 mm courtyard is a
                        # 1.25 mm half-extent on each axis and that is the whole difference.
                        # The same centres-vs-courtyard slip cost a pass on R30 earlier the
                        # same day. Two tests of the same thing must agree, and the assert
                        # is the authority, so this mirrors it.
                        import src.top_plate as _TP
                        _hr = _TP.JACK_HEAD_D / 2.0
                        _hw = OP.CRTYD["TP"][0] / 2.0
                        _hh = OP.CRTYD["TP"][1] / 2.0
                        for _mx, _my in OP.mount_points():
                            _fx = (_mx - CX) + 100.0
                            _fy = 100.0 - (_my - CY)
                            _dx = max(0.0, abs(x - _fx) - _hw)
                            _dy = max(0.0, abs(y - _fy) - _hh)
                            if math.hypot(_dx, _dy) - _hr < OP.PKG_CLR:
                                under = True
                                break
                    if under:
                        n_part += 1
                    else:
                        best.append((round(foreign - R_KEEP, 3), round(x, 3), round(y, 3), 0.0))
                y += 0.5
            x += 0.5
        best.sort(reverse=True)
        cur = None
        for p in O.BOARD_NOTES["placements"]:
            pass
        if not best:
            print("%-5s %-10s  NO SITE   [of %d grid points: %d not on its own copper, "
                  "%d too close to foreign copper, %d under a part]"
                  % (ref, net, n_tot, n_own, n_foreign, n_part))
        else:
            hm, hx, hy, npart = best[0]
            print("%-5s %-10s  best (%.3f, %.3f) file  headroom %+.3f over the rule "
                  "  [%d sites of %d; rejected %d own / %d foreign / %d under a part]"
                  % (ref, net, hx, hy, hm, len(best), n_tot, n_own, n_foreign, n_part))
            print("        board-local (%.3f, %.3f)   CAD (%.3f, %.3f)"
                  % (hx - 100.0, 100.0 - hy,
                     hx - 100.0 + CX, 100.0 - hy + CY))


if __name__ == "__main__":
    main()
