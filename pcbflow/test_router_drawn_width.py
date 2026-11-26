"""The router draws power copper at copper.draw_mm, and judges rails on the bare need.

    py -3.12 test_router_drawn_width.py

copper.draw_mm(need) = need + RASTER_MARGIN_MM up to 0.05, and drawn_width_mm(amps) is
draw_mm(required_width_mm(amps)), so the two can't disagree; every drawn width is over its
need. router.model sets a power net's width from draw_mm of its unrounded need (power_width
ndigits=None) and keeps the bare need in model.need; negotiate._rail_w picks rails on the need
(a stub +24V drawn 0.95 for need 0.90 and a signal drawn 0.45 for need 0.38: the second is no
rail). place_flow raises a stated width under the need to the drawn width. Exit 0 = PASS.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import copper  # noqa: E402
from router.model import power_width  # noqa: E402
from router.negotiate import Router  # noqa: E402

bad = []
q = {"temp_rise_c": 20.0}
for i in range(1, 400):
    a = i * 0.025
    need = copper.required_width_mm(a, "F.Cu", q)
    d = copper.draw_mm(need)
    if d != copper.drawn_width_mm(a, "F.Cu", q):
        bad.append("%.3f A: draw_mm %.2f != drawn_width_mm %.2f" % (a, d, copper.drawn_width_mm(a, "F.Cu", q)))
    if d < need + copper.RASTER_MARGIN_MM - 1e-9:
        bad.append("%.3f A: drawn %.2f under need %.4f + margin" % (a, d, need))
    pw = power_width({"net": "X", "amps": a, "from": "s", "to": []}, q, {}, ndigits=None)
    if abs(pw - need) > 1e-9:
        bad.append("%.3f A: power_width %.5f is not copper's need %.5f" % (a, pw, need))
if copper.draw_mm(0.8976) != 0.95:
    bad.append("+24V 3 A at 20 C: drawn %.2f, want 0.95" % copper.draw_mm(0.8976))


class N:
    def __init__(self, name, w):
        self.name, self.width, self.plane = name, w, False


class M:
    need = {"+24V": 0.90, "SIGX": 0.38}


r = Router.__new__(Router)
r.m = M()
if r._rail_w(N("+24V", 0.95)) != 0.90 or r._rail_w(N("SIGX", 0.45)) >= Router.RAIL_W_MIN:
    bad.append("_rail_w does not judge on the bare need")
if r._rail_w(N("STATED", 0.7)) != 0.7:
    bad.append("_rail_w: a net with no need should use its drawn width")
src = open(os.path.join(HERE, "router", "model.py"), encoding="utf-8").read()
for want in ("copper.draw_mm(need[n])", "power_width(pp, q, at, ndigits=None)", "self.need = "):
    if want not in src:
        bad.append("router/model.py: missing %r" % want)
if "nw[n] = min(POWER_W_MAX, copper.draw_mm(w))" not in open(os.path.join(HERE, "place_flow.py"), encoding="utf-8").read():
    bad.append("place_flow._raise_widths does not raise to the drawn width")
for b_ in bad[:20]:
    print("  FAIL:", b_)
print("PASS" if not bad else "FAIL")
sys.exit(1 if bad else 0)
