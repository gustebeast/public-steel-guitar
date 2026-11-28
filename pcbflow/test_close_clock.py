"""close_last's clock counts its child processes' CPU (brain_board fold13 / fold15_s1, 2026-11-27).

    "C:/Program Files/KiCad/10.0/bin/python.exe" test_close_clock.py

fold15_s1: "close_last: out of time after 600 s" on an attempt finish timed at 1268 s -- the
pour guard's widepath.py subprocess ran 668 s that process_time never saw, and finish's
CLOSE_TOTAL_S (the child's own CPU) did not see it either. No board:
1. A child that burns ~1.5 s of CPU through _run_child moves close_last's clock by that much,
   while this process's own CPU hardly moves.
2. A failing child still raises CalledProcessError (subprocess.run(check=True) did), and its
   CPU is still counted.
3. The line close_last prints at exit is the one finish's regex reads.
Exit 0 = PASS.
"""
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import close_last as CL  # noqa: E402

bad = []
burn = "import time\nt=time.process_time()\nwhile time.process_time()-t<1.5: pass\n"
py = CL._scipy_py()

# 1. a child's CPU is on the clock
c0, p0 = CL._clock(), time.process_time()
CL._run_child(py + ["-c", burn])
dc, dp = CL._clock() - c0, time.process_time() - p0
print("1: clock +%.2f s, own CPU +%.2f s, CHILD_CPU %.2f" % (dc, dp, CL.CHILD_CPU[0]))
if dc < 1.3:
    bad.append("1: a 1.5 s child moved the clock only %.2f s" % dc)
if dp > 0.5:
    bad.append("1: the child's CPU showed up as this process's own (%.2f s)" % dp)

# 2. a failing child raises, and is counted
n0 = CL.CHILD_CPU[0]
try:
    CL._run_child(py + ["-c", burn.replace("1.5", "0.5") + "raise SystemExit(3)\n"])
    bad.append("2: a child exiting 3 did not raise")
except Exception as e:  # noqa: BLE001
    import subprocess
    print("2: raised", type(e).__name__, getattr(e, "returncode", None))
    if not isinstance(e, subprocess.CalledProcessError) or e.returncode != 3:
        bad.append("2: raised %r, wants CalledProcessError rc 3" % (e,))
if CL.CHILD_CPU[0] - n0 < 0.35:
    bad.append("2: a failing child's CPU was not counted (+%.2f s)" % (CL.CHILD_CPU[0] - n0))

# 3. finish reads the exit line
line = "close_last: CPU %.0f s own, CHILD_CPU %.1f s in child processes" % (time.process_time(), CL.CHILD_CPU[0])
got = re.findall(r"CHILD_CPU ([0-9.]+) s", line)
print("3:", line, "->", got)
if not got or abs(float(got[-1]) - CL.CHILD_CPU[0]) > 0.06:
    bad.append("3: finish's regex reads %s from %r" % (got, line))

print("\n".join(bad) if bad else "PASS")
sys.stdout.flush()
os._exit(1 if bad else 0)
