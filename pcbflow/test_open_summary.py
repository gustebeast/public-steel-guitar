"""ownroute's summary names a net ripped in part, not only a failed one (brain_board vip_s2, 2026-11-24).

    py -3.12 test_open_summary.py

The finish rips only the joins that still share, so V5_PRE kept most of its copper, n_open 3,
not failed -- and the summary said "10 net(s) left open" where KiCad counted 121 open joins.
A fake router and nets: one failed net, one net open in part, one whole.

Fails without the fix: the line lists FAIL_A only and says 1 net(s).
Exit 0 = PASS.
"""
import contextlib
import io
import os
import sys
import tempfile
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
stub = types.ModuleType("router")
stub.congestion = types.SimpleNamespace(report=lambda r: None, pair_dives=lambda r: None)
stub.emit = types.SimpleNamespace(write=lambda m, nets, path: 7)
sys.modules["router"] = stub
import ownroute  # noqa: E402


class R:
    def frozen_audit(self, *a, **k):
        return False


def net(name, failed=False, n_open=0):
    return types.SimpleNamespace(name=name, failed=failed, n_open=n_open)


nets = [net("FAIL_A", failed=True), net("V5_PRE", n_open=3), net("WHOLE")]
stem = os.path.join(tempfile.mkdtemp(prefix="opensum_"), "b")
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    ownroute._write(stem, None, R(), nets, [nets[0]], 0.0)
line = buf.getvalue()
bad = []
for ok, msg in ((" 2 net(s) left open (1 failed, 1 in part)" in line, "counts failed + in part"),
                ("FAIL_A" in line and "V5_PRE (3)" in line, "names both, with the part count"),
                ("WHOLE" not in line, "a whole net is not listed")):
    print("%s %s" % ("PASS" if ok else "FAIL", msg))
    if not ok:
        bad.append(msg)
print(line.strip())
print("PASS" if not bad else "FAIL: %d" % len(bad))
sys.exit(1 if bad else 0)
