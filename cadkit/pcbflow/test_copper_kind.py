"""place_flow._copper (intent kind "copper"): declared copper into notes, checked against its pads.

    py -3.12 cadkit/pcbflow/test_copper_kind.py

  1  tracks / vias land in notes; `frozen` adds the net to frozen_nets once
  2  a second pass (_pours runs twice) declares nothing again
  3  a pin in `on` with no track end on its pad -> SystemExit (a part moved off its copper)
Exit code 0 = all as expected.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import place_flow as pf  # noqa: E402


class P:
    """Two square pads: U1.1 at the origin, U2.1 at (5, 0), 0.5 mm."""
    PADS = {("U1", "1"): (0.0, 0.0), ("U2", "1"): (5.0, 0.0)}

    def pad_poly(self, ref, num):
        x, y = self.PADS[(ref, num)]
        return [[x - .25, y - .25], [x + .25, y - .25], [x + .25, y + .25], [x - .25, y + .25]]


rule = {"kind": "copper", "net": "SNS", "key": "t", "frozen": True, "on": ["U1.1", "U2.1"],
        "tracks": [{"layer": "F.Cu", "width": 0.2, "pts": [[0, 0], [2, 0]]},
                   {"layer": "In2.Cu", "width": 0.2, "pts": [[2, 0], [5, 0]]}],
        "vias": [[2, 0]]}
bad = []
notes = {}
lines = pf._copper(notes, P(), [rule])
ok = len(notes.get("tracks", ())) == 2 and len(notes.get("vias", ())) == 1 and notes.get("frozen_nets") == ["SNS"]
print("ok " if ok else "BAD", "1 declared into notes:", lines)
bad += [] if ok else ["1"]
pf._copper(notes, P(), [rule])
ok = len(notes["tracks"]) == 2 and len(notes["vias"]) == 1 and notes["frozen_nets"] == ["SNS"]
print("ok " if ok else "BAD", "2 idempotent")
bad += [] if ok else ["2"]
off = dict(rule, key="t2", tracks=[{"layer": "F.Cu", "width": 0.2, "pts": [[0, 0], [3, 0]]}])
try:
    pf._copper({}, P(), [off])
    print("BAD 3 a pad with no track end passed")
    bad.append("3")
except SystemExit as e:
    print("ok  3 stops:", str(e)[:90])
print("copper kind: %s" % ("PASS" if not bad else "FAIL " + ",".join(bad)))
sys.exit(1 if bad else 0)
