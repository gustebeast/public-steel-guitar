"""widepath.judge `declared`: a bounded declared neck is WARN only while the copper keeps to it.

    py -3.12 cadkit/pcbflow/test_declared_neck.py

Two 3 x 3 mm lands joined by a 0.5 mm strip 1.3 mm long, judged at need 0.70 (VIN_CM5 at
U205, brain_board esc11: 0.49 for 1.33 in the pregate):
  1  undeclared                               -> FAIL (neck > 2 x width)
  2  declared min_w 0.45, max_len 1.8         -> WARN, the key named (measured 1.73: the land
     junctions count, as on the board)
  3  declared max_len 1.5 (copper longer)     -> FAIL, declared_broken
  4  declared min_w 0.6 (copper narrower)     -> FAIL, declared_broken
Exit code 0 = all as expected.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import widepath  # noqa: E402

res = 0.025
H, W = int(4 / res), int(8.3 / res)
m = np.zeros((H, W), bool)
m[int(0.5 / res):int(3.5 / res), 0:int(3 / res)] = True                       # land A
m[int(0.5 / res):int(3.5 / res), int(4.3 / res):int(7.3 / res)] = True        # land B
m[int(1.75 / res):int(2.25 / res), int(3 / res):int(4.3 / res)] = True        # the strip
width = widepath.widths({"F": m}, res)
A = {"F": np.zeros((H, W), bool)}
A["F"][int(1.5 / res):int(2.5 / res), int(0.5 / res):int(1.5 / res)] = True
B = {"F": np.zeros((H, W), bool)}
B["F"][int(1.5 / res):int(2.5 / res), int(5.8 / res):int(6.8 / res)] = True
bad = []


def case(name, want, **kw):
    r = widepath.judge({k: v.copy() for k, v in width.items()}, [], A, B, res, 0.70, **kw)
    ok = want(r)
    print("%s %s: %s" % ("ok " if ok else "BAD", name, r))
    if not ok:
        bad.append(name)


case("1 undeclared", lambda r: r["verdict"] == "FAIL" and "declared" not in r)
case("2 declared, kept", lambda r: r["verdict"] == "WARN" and r.get("declared") == "k",
     declared=dict(key="k", min_w=0.45, max_len=1.8))
case("3 declared, longer", lambda r: r["verdict"] == "FAIL" and r.get("declared_broken") == "k",
     declared=dict(key="k", min_w=0.45, max_len=1.5))
case("4 declared, narrower", lambda r: r["verdict"] == "FAIL" and r.get("declared_broken") == "k",
     declared=dict(key="k", min_w=0.6, max_len=1.8))
print("declared neck: %s" % ("PASS" if not bad else "FAIL " + ",".join(bad)))
sys.exit(1 if bad else 0)
