"""A16 net-tie inheritance: a net joined through a net tie (NT*) takes its parent's net_volts.

    "C:/Program Files/KiCad/10.0/bin/python.exe" cadkit/pcbflow/test_quality_a16_ties.py \
        <stem of a board with a Kelvin tie, e.g. the brain board: PB_VCC -NT- PB_VCC_K>

  0  as declared (parent only)          -> the tied net passes, "inherited from <parent>
                                           through net tie NT..", at the parent's number
  1  parent raised to 7.77 V            -> the tied net reads 7.77 V: the number travels
  2  the tied net declared itself       -> its own entry wins ("declared"), not the parent's
  3  parent undeclared too              -> the tied net FAILs as undeclared: inheritance
                                           never invents a voltage

On a copy, in a temp dir (test_quality_a16.py's harness). Exit 0 = every case as it should.
"""
from __future__ import annotations

import fnmatch
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from test_quality_a16 import _case          # noqa: E402  (wx asserts off, pcbnew, quality)

PARENT, TIED = "PB_VCC", "PB_VCC_K"


def _row(rows, net):
    return [(st, t) for st, s, t in rows if s == net]


def _drop(q, *nets):
    nv = q["net_volts"]
    for k in [k for k in nv if any(fnmatch.fnmatchcase(n, k) for n in nets)]:
        del nv[k]


def main(stem):
    ok = True

    def check(name, cond, rows):
        nonlocal ok
        print("%s  %s: %s" % ("PASS" if cond else "FAIL", name, rows))
        ok &= bool(cond)

    r0 = _row(_case(stem, "as is", lambda q: _drop(q, TIED) if TIED in q["net_volts"] else None), TIED)
    check("0 inherited", r0 and r0[0][0] != "FAIL" and "inherited from %s through net tie NT" % PARENT in r0[0][1], r0)

    def raise_parent(q):
        _drop(q, TIED)
        q["net_volts"][PARENT] = {"v": 7.77, "why": "test"}
    r1 = _row(_case(stem, "raised", raise_parent), TIED)
    check("1 number travels", r1 and "7.77 V" in r1[0][1] and "inherited" in r1[0][1], r1)

    def own(q):
        q["net_volts"][TIED] = {"v": 3.21, "why": "test"}
    r2 = _row(_case(stem, "own", own), TIED)
    check("2 own entry wins", r2 and "3.21 V" in r2[0][1] and "(declared)" in r2[0][1], r2)

    r3 = _row(_case(stem, "undeclared", lambda q: _drop(q, PARENT, TIED)), TIED)
    check("3 no invention", r3 and r3[0][0] == "FAIL" and "no worst-case voltage" in r3[0][1], r3)
    return ok


if __name__ == "__main__":
    good = main(os.path.abspath(sys.argv[1]))
    sys.stdout.flush()
    os._exit(0 if good else 1)
