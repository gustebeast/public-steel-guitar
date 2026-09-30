"""How big can the Pi spacer's clamp actually be? (2026-09-29)

The envelope probe found the first cut collides two ways: the LAP runs into the Pi's own
top-side parts (108 mm3, and 108/(15*3*2.4) = 1.00, i.e. that box is SOLID -- a tall component,
not a graze), and the TAIL runs into chassis_2 at its far end.

Clamp quality is LAP x W, and the two trade against each other: reach less far in over the
laminate, run further along the edge. So sweep both against the real assembly instead of
picking a pair and hoping. The bar to beat is a O7.6 button head's pcb_hold_overlap() = 1.30 mm
on one small arc.

    py -3.12 -m tools._probe_pi_spacer_fit
"""
import cadquery as cq

from src.build import collect_components
from src import electronics as EL

SITE = (-510.0, -58.50)
T = 2.4
TAILS = (3.0, 4.0, 5.0)
LAPS = (2.0, 2.5, 3.0, 3.5, 4.0)
WS = (16.0, 20.0, 24.0, 28.0, 32.0)


def _hits(comps, env):
    out = []
    for n, s in comps:
        if (n.startswith("board_screw") or n.startswith("board_insert")
                or n == "pi_spacer"):
            continue            # ⚠ pi_spacer is IN the assembly now: it would find ITSELF
        try:
            it = s.intersect(env)
            v = it.Volume() if it.Solids() else 0.0
        except Exception:
            continue
        if v > 0.5:
            out.append((round(v, 1), n))
    return sorted(out, reverse=True)


def main():
    comps = [(n, wp.val()) for n, wp in collect_components()]
    hx, hy = SITE
    y_edge = EL.PI_FP[3]
    z_lap0 = EL.PI_Z + EL.BD_T

    print("LAP x W over the laminate (the clamp); a button head laps 1.30 on one arc\n")
    print("        " + "".join("%12s" % ("W %.0f" % w) for w in WS))
    best = None
    for lap in LAPS:
        row = ""
        for w in WS:
            env = (cq.Workplane("XY").box(w, lap, T)
                   .translate((hx, y_edge - lap / 2.0, z_lap0 + T / 2.0)).val())
            h = _hits(comps, env)
            row += "%12s" % ("clear" if not h else "%s %.0f" % (h[0][1][:7], h[0][0]))
            if not h and (best is None or lap * w > best[0] * best[1]):
                best = (lap, w)
        print("lap %4.1f%s" % (lap, row))

    print("\nTAIL past the screw (the shank's far end):")
    for tail in TAILS:
        y_out = hy + tail
        env = (cq.Workplane("XY").box(24.0, y_out - y_edge, (z_lap0 + T) - EL.PI_Z)
               .translate((hx, (y_edge + y_out) / 2.0, (EL.PI_Z + z_lap0 + T) / 2.0)).val())
        h = _hits(comps, env)
        print("  tail %4.1f -> y_out %7.2f   %s   (head edge %7.2f)"
              % (tail, y_out, "clear" if not h else
                 ", ".join("%s %.1f" % (n, v) for v, n in h), hy + 3.8))

    if best:
        print("\nbiggest clear clamp: lap %.1f x W %.1f = %.1f mm2 of laminate held"
              % (best[0], best[1], best[0] * best[1]))


if __name__ == "__main__":
    main()
