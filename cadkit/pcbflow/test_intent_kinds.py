"""test_intent_kinds.py -- place_intent.KINDS against the code: no intent kind silently does nothing.

Fails when: check() knows a kind KINDS does not list (or the reverse); a kind names a stage whose
file never mentions it; a kind that can be hard has no gate (place_flow's BROKEN tuple, _near_broken,
or the region leak stop); grow_reach does not cover the "grow" kinds.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import place_intent as pi  # noqa: E402

FILES = {"init": "place_init.py", "cells": "place_cells.py", "flow": "place_flow.py",
         "layout": os.path.join("router", "model.py"), "check": "place_intent.py",
         "grow": "place_intent.py", "expand": "place_intent.py"}


def src(name):
    return open(os.path.join(HERE, name), encoding="utf-8").read()


def check_kinds():
    body = src("place_intent.py")
    i = body.index("\ndef check(")
    j = body.index("\ndef ", i + 1)
    return set(re.findall(r'k == "(\w+)"', body[i:j])) | set(re.findall(r'k in \(([^)]*)\)', body[i:j]) and
                                                            sum((re.findall(r'"(\w+)"', g) for g in
                                                                 re.findall(r'k in \(([^)]*)\)', body[i:j])), []))


def test_table_matches_check():
    ck = check_kinds()
    missing = ck - set(pi.KINDS)
    extra = set(pi.KINDS) - ck
    assert not missing, "check() kinds not in KINDS: %s" % sorted(missing)
    assert not extra, "KINDS entries check() does not know: %s" % sorted(extra)


def test_every_kind_has_a_consumer():
    for k, v in pi.KINDS.items():
        assert v["place"], "%s: no stage reads it" % k
        for st in v["place"]:
            assert '"%s"' % k in src(FILES[st]), "%s: says %s reads it, %s never mentions it" % (k, st, FILES[st])


def test_hard_kinds_are_gated():
    flow = src("place_flow.py")
    assert "pi.GATE_KINDS" in flow and "pi.is_hard(" in flow, "place_flow's BROKEN gate is not the table"
    for k, v in pi.KINDS.items():
        can_be_hard = v["gate"] is not None
        if v["gate"] == "broken":
            assert k in pi.GATE_KINDS
        elif v["gate"] == "near":
            assert "_near_broken" in flow
        elif v["gate"] == "region":
            assert "leak" in flow
        elif v["gate"] == "pad_copper":
            assert "PAD ON DECLARED COPPER" in flow and "pi.pad_copper(" in flow
        else:
            assert not v["hard"], "%s: hard by default with no gate" % k
        assert can_be_hard or not pi.is_hard({"kind": k}), k


def test_soft_kinds_soft_unless_asked():
    for k in ("between", "thermal", "apart", "chain", "tight"):
        assert not pi.is_hard({"kind": k}) and pi.is_hard({"kind": k, "hard": True}), k
    for k in ("outline", "keepout", "access", "mate", "decap"):
        assert pi.is_hard({"kind": k}) and not pi.is_hard({"kind": k, "hard": False}), k


def test_check_only_kinds_refuse_hard():
    # a kind no stage seats (place "check" alone) cannot be hard: it would only ever refuse
    P = pi.Placed({"D1": {"pads": [], "crtyd": [], "fab": None, "side": "F"}}, {"D1": [0.0, 0.0, 0]})
    for k, v in pi.KINDS.items():
        if v["place"] != ("check",):
            continue
        assert not v["hard"] and v["gate"] is None, k
        try:
            pi.check({"kind": k, "refs": ["D1"], "axis": "x", "pitch": 1.0, "hard": True}, P, {})
        except ValueError as e:
            assert "no seating stage" in str(e), (k, e)
        else:
            raise AssertionError("%s: a hard rule was accepted, and no stage seats it" % k)


def test_grow_covers_grow_kinds():
    part = {"ref": "J1", "x": 0.0, "y": 0.0, "rot": 0, "side": "F",
            "crtyd": [[-1, -1], [1, -1], [1, 1], [-1, 1]],
            "pads": [{"num": "1", "net": "A", "xy": [0.0, 0.0], "size": [1.0, 1.0]}]}
    for k, v in pi.KINDS.items():
        if "grow" not in v["place"]:
            continue
        rule = {"kind": k, "ref": "J1", "refs": ["J1"], "tool_d": 3.0, "dir": "up", "length": 10.0, "clear": 0.5}
        try:
            env = pi.reach_envelope(dict(part), rule)
        except Exception as e:  # noqa: BLE001
            raise AssertionError("%s: reach_envelope failed: %r" % (k, e))
        assert env is not None, "%s: grow kind with no envelope" % k


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f()
            print("ok", n)
