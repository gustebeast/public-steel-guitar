"""widepath.neck_length is a EUCLIDEAN length, not a Manhattan one.  py -3.12 test_widepath_neck.py

brain_board SW5_2 (lead 2026-11-25): the old 4-connected graph read a neck that rises while it
runs as dx + dy -- 1.13 mm for ~0.95 of copper -- and FAILed it. A 0.5 mm strip 2 mm long between
two wide blocks must read ~2 mm laid along an axis AND at 45 deg (the old graph: 2.83 at 45)."""
import numpy as np
import widepath

RES = 0.025


def strip(diag, L=2.0, w=0.5, need=1.0, wide=None):
    H = W = 400                                    # 10 x 10 mm
    yy, xx = np.mgrid[0:H, 0:W] * RES
    c = np.array([5.0, 5.0])
    u = np.array([1.0, 1.0]) / np.sqrt(2) if diag else np.array([1.0, 0.0])
    n = np.array([-u[1], u[0]])
    s = (xx - c[0]) * u[0] + (yy - c[1]) * u[1]    # along the strip
    t = (xx - c[0]) * n[0] + (yy - c[1]) * n[1]    # across it
    F = (np.abs(s) <= L / 2) & (np.abs(t) <= w / 2)
    if wide:                                       # a WIDE strip with the narrow piece as its pinch
        F |= (np.abs(s) > L / 2) & (np.abs(s) <= 2.5) & (np.abs(t) <= wide / 2)
    blk = lambda s0: (np.abs(s - s0) <= 1.0) & (np.abs(t) <= 1.5)
    A, B = blk(-L / 2 - 1.0), blk(L / 2 + 1.0)
    F |= A | B
    r = widepath.judge(widepath.widths({"F": F}, RES), [], {"F": A}, {"F": B}, RES, need, where=False)
    return r


bad = 0
for diag in (False, True):
    r = strip(diag)
    ok = 1.9 <= r["neck"] <= 2.0 * 1.09 and 0.45 <= r["width"] <= 0.56
    print("ok " if ok else "BAD", "0.5 x 2 mm strip", "45 deg" if diag else "on axis",
          "neck %.2f width %.2f %s" % (r["neck"], r["width"], r["verdict"]))
    bad += not ok
# a slight pinch (1.5 wide, 0.3 long) in a 1.6 strip, need 1.58: only a thin line of pixels on the
# ridge at the pinch reads under the need, and at 45 deg a diagonal step may not hop it for free
# (cb039d5 read motor_ctrl's +24V_LED and brain's SW necks 0.00 under their need)
for diag in (False, True):
    r = strip(diag, L=0.3, w=1.5, wide=1.6, need=1.58)
    ok = r["neck"] >= 0.05 and r["verdict"] != "PASS"
    print("ok " if ok else "BAD", "1.5 x 0.3 pinch in a 1.6 strip", "45 deg" if diag else "on axis",
          "neck %.2f width %.2f %s" % (r["neck"], r["width"], r["verdict"]))
    bad += not ok
raise SystemExit(bad)
