"""Test-only portability.

Windows' time.monotonic() is GetTickCount64 with a 15.6 ms tick. The bench's links stamp frames
with it, and leverisp tells "answered after the hold" from "before" by comparing those stamps, so
on Windows a hello sent just before t0 can carry t0's own tick and count as after it. The Pi's
monotonic clock has nanosecond resolution and needs none of this. Under test on Windows, the
clock becomes perf_counter, which is also monotonic and has sub-microsecond resolution.
"""
import sys
import time

if sys.platform == "win32":
    time.monotonic = time.perf_counter
