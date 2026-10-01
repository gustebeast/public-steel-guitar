"""Retention check: how far can a loose part be pushed before something stops it?

  py -3.12 -m tools.check_retention
  py -3.12 -m tools.check_retention --only kl_pcb_shim --travel 20

WHY THIS EXISTS. Half the parts in this instrument are held by SHAPE rather than by a
fastener -- the sensor boards and their shims slide down a groove and are pinned by the
chassis on the one axis the groove leaves open. That is a good scheme and it has a bad
failure mode: retention on five faces looks exactly like retention on four in a render,
in the overlap gate, and in every bead or ceiling check, because nothing here is
overlapping or unsupported. It is only wrong when you turn the instrument over.

It had already gone wrong twice by the time this was written, both found by eye rather
than by any tool. The vertical lever once had NO +X retention at all (an ad-hoc version
of this probe caught it). And both shims could be lifted straight out sideways: the near
web stopped 17 mm below them, so the far web was holding them alone -- and the plug
tunnel takes the far groove's flanks away at exactly that height (user, 2026-09-29: "the
PCB and shim retention seems a bit lacking for the levers").

WHAT IT DOES. Pushes each part along +-X, +-Y, +-Z in 0.25 mm steps and reports the
travel before it hits anything else in the assembly. `OUT` means it never hits anything
within --travel: that direction does not hold it.

READING IT. `0.00` is retained. A number is SLOP -- the part can rattle that far, and
5.75 in a groove means the groove is not there for most of the part's height. ONE open
direction is the normal, correct answer for a part installed along an axis, and which
one should match the install stroke; NONE is better still and is what the boards get,
since the shim closes the axis they went in on. Two or more means it can come out.

WHAT IT CANNOT SEE: a part that is retained at rest but escapes along a curved or
compound path, and a part held only by friction. It pushes along the six axes, which is
the test a part fails when the instrument is carried upside down.
"""

from __future__ import annotations

import argparse

DIRS = (("+X", (1, 0, 0)), ("-X", (-1, 0, 0)), ("+Y", (0, 1, 0)),
        ("-Y", (0, -1, 0)), ("+Z", (0, 0, 1)), ("-Z", (0, 0, -1)))

# the loose parts and the assembly each one lives in. A part that is screwed, fused or
# press-fitted is not listed: its retention is the fastener's, not the shape's.
LOOSE = ("kl_pcb", "kl_pcb_shim", "vkl_kv_pcb", "vkl_kv_pcb_shim",
         "lkr_kl_pcb", "lkr_kl_pcb_shim", "rkl_kl_pcb", "rkl_kl_pcb_shim",
         "rkr_kl_pcb", "rkr_kl_pcb_shim")


def _components():
    from src import build as B
    out = {}
    for c in B.lever_harness_components():
        nm = getattr(c, "name", None) or c[0]
        sh = getattr(c, "shape", None) or (c[1] if isinstance(c, (list, tuple)) else None)
        if sh is not None:
            out[nm] = sh.val() if hasattr(sh, "val") else sh
    return out


def travel(part, others, d, limit, step=0.25):
    """Free travel along `d` before `part` meets anything, or None if it gets away."""
    n = int(limit / step)
    for i in range(1, n + 1):
        t = step * i
        m = part.translate((d[0] * t, d[1] * t, d[2] * t))
        for s in others:
            try:
                if m.intersect(s).Volume() > 0.05:
                    return t - step
            except Exception:
                return t - step           # a boolean that will not run is a contact
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma-separated part names")
    ap.add_argument("--travel", type=float, default=15.0, help="how far to push (mm)")
    a = ap.parse_args()
    want = {s.strip() for s in a.only.split(",")} if a.only else None

    got = _components()
    loose = 0
    for nm in LOOSE:
        if nm not in got or (want and nm not in want):
            continue
        p = got[nm]
        pb = p.BoundingBox()
        # only the neighbours it could reach -- everything else is a boolean for nothing
        others = [s for k, s in got.items() if k != nm and _near(s.BoundingBox(), pb, a.travel)]
        free = []
        print("  %-18s" % nm, end="")
        for dn, d in DIRS:
            t = travel(p, others, d, a.travel)
            if t is None:
                free.append(dn)
            print("  %s %s" % (dn, "OUT  " if t is None else "%5.2f" % t), end="")
        # NONE open is the right answer for the boards, not a bug in the test: the shim
        # sits on top of each one, so the board is captive and the SHIM is the part the
        # chassis has to close. Only two or more open directions is a fault.
        print("   %s" % (("captive" if not free else "held on five faces") if len(free) < 2
                         else "LOOSE: open %s" % ",".join(free)), flush=True)
        loose += len(free) > 1
    print("\n%s" % ("every loose part is held on five faces." if not loose else
                    "%d part(s) with more than one open direction." % loose))
    return 0            # advisory: one open direction is by design, and which one is a


def _near(b, pb, m):    # judgement this cannot make
    return (b.xmin - m <= pb.xmax and b.xmax + m >= pb.xmin
            and b.ymin - m <= pb.ymax and b.ymax + m >= pb.ymin
            and b.zmin - m <= pb.zmax and b.zmax + m >= pb.zmin)


if __name__ == "__main__":
    raise SystemExit(main())
