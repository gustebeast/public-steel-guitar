"""A board's pour clearance is a choice, never KiCad's silent 0.5 mm default (lead, 2026-11-24).

    "C:/Program Files/KiCad/10.0/bin/python.exe" test_zone_clearance_required.py

brain_board lost output_panel's 0.2 in a merge and ran every pour at 0.5 with no word said
(layout.zone_clearance_check says what that cost). On a scratch project (elec/ + out/):
  1  zone_clearance set                              -> nothing said, layout goes on
  2  unset, project does not opt in                  -> loud warning naming the board
  3  unset, pcb_declared.py REQUIRE_ZONE_CLEARANCE   -> SystemExit naming the board
  4  set to 0.5 explicitly, project opts in          -> accepted (an explicit 0.5 is a choice)
Fails without the check (cadkit d5d43d7): layout has no zone_clearance_check, so 2 and 3
pass silently.
Exit 0 = PASS.
"""
import contextlib
import io
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    import wx
    wx.DisableAsserts()
except Exception:
    pass
import layout  # noqa: E402

PHRASE = "zone_clearance unset, KiCad 0.5 used, nobody chose it"


def project(opt_in):
    root = tempfile.mkdtemp(prefix="zcreq_")
    elec = os.path.join(root, "elec")
    os.makedirs(os.path.join(elec, "out"))
    with open(os.path.join(elec, "pcb_declared.py"), "w", encoding="utf-8") as fh:
        fh.write("def declared(board, vtype, refs):\n    return False\n")
        if opt_in:
            fh.write("REQUIRE_ZONE_CLEARANCE = True\n")
    return os.path.join(elec, "out", "demo_board")


def run(stem, notes):
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            got = getattr(layout, "zone_clearance_check", lambda s, n: None)(stem, notes)
        return "ok", got, out.getvalue()
    except SystemExit as e:
        return "exit", str(e), out.getvalue()


def main():
    os.environ.pop("PCBFLOW_PROJECT", None)
    bad = []

    def want(ok, msg):
        print("%s %s" % ("PASS" if ok else "FAIL", msg))
        if not ok:
            bad.append(msg)

    k, got, said = run(project(False), {"zone_clearance": 0.2})
    want(k == "ok" and got is None and not said, "1 set: nothing said")
    k, got, said = run(project(False), {})
    want(k == "ok" and PHRASE in said and "demo_board" in said, "2 unset, no opt-in: warns naming the board")
    k, got, said = run(project(True), {})
    want(k == "exit" and PHRASE in got and "demo_board" in got, "3 unset, opted in: refused naming the board")
    k, got, said = run(project(True), {"zone_clearance": 0.5})
    want(k == "ok" and got is None, "4 explicit 0.5, opted in: accepted")
    return bad


if __name__ == "__main__":
    bad = main()
    print("PASS" if not bad else "FAIL: %d" % len(bad))
    sys.stdout.flush()
    os._exit(1 if bad else 0)
