"""swaps.py: a run's proposal, accepted, reaches the netlist exactly as the generator would write it (2026-11-22).

    py -3.12 test_swaps.py RUN_DIR PLAIN.net SWAPPED.net

brain_board: RUN_DIR = esc13_pre9 (pin_swaps.json proposes FL3 / FL4's winding swap, 7 -> 3), PLAIN.net =
srcPS24 (D+ on 1-4), SWAPPED.net = srcPS25 (the generator's own D- on 1-4 build).
1. accept + apply_accepted on a copy of PLAIN gives FL3 / FL4 exactly SWAPPED's pin-to-net map, and every
   other pin unchanged.
2. applying again to SWAPPED says "already carried" and changes nothing.
3. a pin moved off both the before and after nets stops it (SystemExit).
4. `accept` without the run's proposal for a named ref adds nothing; twice for one ref stops it.
Exit 0 = PASS. Writes only in a temp dir.
"""
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import swaps  # noqa: E402


def main(run, plain, swapped):
    bad = []
    t = tempfile.mkdtemp()
    acc = os.path.join(t, "acc.json")
    got = swaps.accept(run, acc, "brain_board", why="test")
    if sorted(got) != ["FL3", "FL4"]:
        bad.append("accept took %s, want FL3 / FL4" % got)
    net = os.path.join(t, "b.net")
    shutil.copy(plain, net)
    print("\n".join(swaps.apply_accepted(net, "brain_board", acc)))
    a = swaps.netlist_pins(open(net, encoding="utf-8").read())
    w = swaps.netlist_pins(open(swapped, encoding="utf-8").read())
    p = swaps.netlist_pins(open(plain, encoding="utf-8").read())
    for k in set(a) | set(w):
        if a.get(k) != w.get(k):
            bad.append("%s.%s: applied %s, generator %s" % (k + (a.get(k), w.get(k))))
    if sum(1 for k in p if p[k] != a.get(k)) != 8:
        bad.append("%d pins moved, want 8" % sum(1 for k in p if p[k] != a.get(k)))
    net2 = os.path.join(t, "s.net")
    shutil.copy(swapped, net2)
    ln = swaps.apply_accepted(net2, "brain_board", acc)
    if not all("already carried" in x for x in ln) or open(net2, encoding="utf-8").read() != open(swapped, encoding="utf-8").read():
        bad.append("re-apply on the generator's build was not a no-op: %s" % ln)
    d = json.load(open(acc))
    d["brain_board"][0]["nets"] = {k: "NOPE" for k in d["brain_board"][0]["nets"]}
    json.dump(d, open(acc, "w"))
    try:
        swaps.apply_accepted(net2, "brain_board", acc)
        bad.append("a swap whose nets match neither side did not stop")
    except SystemExit:
        pass
    acc2 = os.path.join(t, "acc2.json")
    if swaps.accept(run, acc2, "b", why="t", refs={"U1"}):
        bad.append("accept of a ref the run did not propose added something")
    swaps.accept(run, acc2, "b", why="t", refs={"FL3"})
    try:
        swaps.accept(run, acc2, "b", why="t", refs={"FL3"})
        bad.append("accepting FL3 twice did not stop")
    except SystemExit:
        pass
    shutil.rmtree(t, ignore_errors=True)
    return bad


if __name__ == "__main__":
    bad = main(*[os.path.abspath(x) for x in sys.argv[1:4]])
    for x in bad[:20]:
        print("  FAIL:", x)
    print("PASS" if not bad else "FAIL")
    sys.exit(1 if bad else 0)
