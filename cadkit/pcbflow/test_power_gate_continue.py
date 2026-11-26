"""finish's power gate: the pre-close gate reports and the run goes on; the gate on the
finished board is the verdict (lead, 2026-11-26: brain_board fold9 stopped at the pre-close
gate on two router-thin paths after 2 h, and close_last never ran).

    py -3.12 test_power_gate_continue.py

Source checks (finish() drives KiCad and the router; its order is the thing under test):
the pre-close call writes <stem>.power_gate.pre.txt and does not raise; a second _power_gate
call writes <stem>.power_gate.txt after close_last; a FAIL there (or a gate that did not run)
raises SystemExit only after the summary line is printed. Exit 0 = PASS.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "finish.py"), encoding="utf-8").read().replace("\r\n", "\n")
body = src[src.index("\ndef finish("):]
bad = []
pre = body.find('_power_gate(stem, ".power_gate.pre.txt")')
fin = body.find("power_final = _power_gate(stem)")
close = body.find('_run("close_last.py", stem)')
summary = body.find('print("%s: %d unconnected, %d violation(s)%s%s%s%s"')
verdict = body.find('raise SystemExit("finish: the finished board fails the power gate')
if pre < 0:
    bad.append("no pre-close gate writing .power_gate.pre.txt")
elif "raise SystemExit" in body[pre:pre + 400]:
    bad.append("the pre-close gate still stops the run")
if "not finishing" in src:
    bad.append("the old 'not finishing it' stop is still in finish.py")
if fin < 0 or close < 0 or fin < close:
    bad.append("no final gate after close_last")
if summary < 0 or verdict < 0 or verdict < summary:
    bad.append("the final gate's FAIL does not fail the run after the summary line")
if not re.search(r"power_final is None or \(power_final and power_final\[0\]\)", body):
    bad.append("a final gate that did not run is not a failure")
for b_ in bad:
    print("  FAIL:", b_)
print("PASS" if not bad else "FAIL")
sys.exit(1 if bad else 0)
