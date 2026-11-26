"""widepath.judge says WHERE a WARN / FAIL is (widepath.locate).  py -3.12 test_widepath_locate.py

The brain_board ec3 case, drawn small: an F strip and a B strip overlap under a via field. The
vias sit OFF the axis of a track exactly as wide as the need, so the copper around each is
narrower than the need and widepath does not count them (6 routes read WARN 1.44 for it).
locate must name that via field, list the vias it did not count with their copper width, and
the same vias ON the axis of a wider track must PASS."""
import numpy as np
import widepath

RES = 0.05


def board(via_y_off, track_w):
    H, W = 200, 400                      # 10 x 20 mm
    yc = H // 2
    half = int(round(track_w / 2 / RES))
    F = np.zeros((H, W), bool)
    B = np.zeros((H, W), bool)
    F[yc - half:yc + half, 20:240] = True     # F from the left end to x 12 mm
    B[yc - half:yc + half, 160:380] = True    # B from x 8 mm to the right end
    holes = []
    for x in (180, 200, 220):                 # 3 vias in the overlap, 1 mm pitch
        for dy in ((-via_y_off, via_y_off) if via_y_off else (0,)):
            holes.append((float(x), float(yc + dy / RES), np.pi * 0.3 * 25.0 / 35.0))
    A = {"F": np.zeros((H, W), bool)}
    A["F"][yc - half:yc + half, 20:60] = True       # pad ends span the strip
    Bm = {"B": np.zeros((H, W), bool)}
    Bm["B"][yc - half:yc + half, 340:380] = True
    return widepath.widths({"F": F, "B": B}, RES), holes, A, Bm


bad = 0
w, h, A, B = board(0.6, 2.6)
r = widepath.judge(w, h, A, B, RES, 2.6)
v = [f for f in r.get("where", ()) if f["kind"] == "vias"]
ok = r["verdict"] != "PASS" and v and len(v[0]["lost"]) >= 1 and all(wl < 2.0 for _, wl in v[0]["lost"])
print("ok " if ok else "BAD", "off-axis vias in a need-wide track:", r["verdict"], "%.2f" % r["width"], v[:1])
bad += not ok
w, h, A, B = board(0.0, 3.0)
r = widepath.judge(w, h, A, B, RES, 1.9)       # 3 on-axis barrels = 2.02
ok = r["verdict"] == "PASS"
print("ok " if ok else "BAD", "on-axis vias in a wider track:", r["verdict"], "%.2f" % r["width"])
bad += not ok
# a foreign strip just as wide, inside the path's crop box, unconnected (2026-11-25: +24V_LED's
# FAIL named the +24V tracks beside its fuse): never the neck; the path's own pinch is
H, W_ = 200, 400
Fm = np.zeros((H, W_), bool)
Fm[90:108, 20:380] = True          # own strip, 0.90 mm
Fm[90:108, 200:220] = False        # ... with a notch: 0.60 mm at x 10-11 mm
Fm[93:105, 200:220] = True
Fm[90:190, 362:380] = True         # ... turning down the right edge, so the box spans y 4.5-9.5 mm
Fm[150:162, 60:340] = True         # foreign strip as wide as the pinch (0.60), inside that box
w = widepath.widths({"F": Fm}, RES)
A = {"F": np.zeros((H, W_), bool)}; A["F"][90:108, 20:40] = True
Bm = {"F": np.zeros((H, W_), bool)}; Bm["F"][175:190, 362:380] = True
r = widepath.judge(w, [], A, Bm, RES, 0.9)
cu = [f for f in r.get("where", ()) if f["kind"] == "copper"]
ok = r["verdict"] != "PASS" and cu and all(f["at"][1] < 130 for f in cu)
print("ok " if ok else "BAD", "foreign strip in the box is not named:", r["verdict"], "%.2f" % r["width"], cu)
bad += not ok
print("widepath locate:", "FAIL %d" % bad if bad else "PASS")
raise SystemExit(1 if bad else 0)
