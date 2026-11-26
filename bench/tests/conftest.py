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


# A test skipped because the TOOLCHAIN is missing is a test that did not run, and a green
# summary hides it: on 2026-11-25 this PC had lost ziglang, python-can and pyserial, and the
# native firmware tests had been skipping silently. Such skips now fail the run, loudly, unless
# BENCH_ALLOW_SKIP=1 says that is intended. Skips for a reason of the platform (the Pi-only
# termios test) are not the toolchain and stay plain skips.
import os  # noqa: E402

TOOLCHAIN = ("no native C compiler", "could not import 'can'", "could not import 'serial'",
             "No module named 'can'", "No module named 'serial'")
_missing = []


def pytest_runtest_logreport(report):
    if report.skipped and isinstance(report.longrepr, tuple):
        reason = str(report.longrepr[2])
        if any(k in reason for k in TOOLCHAIN):
            _missing.append((report.nodeid, reason))


def pytest_terminal_summary(terminalreporter):
    if not _missing:
        return
    tr = terminalreporter
    reasons = sorted({r.replace("Skipped: ", "") for _, r in _missing})
    tr.section("TOOLCHAIN MISSING: %d test(s) did not run" % len(_missing), sep="!", red=True, bold=True)
    for r in reasons:
        tr.write_line("  " + r, red=True)
    tr.write_line("  fix: py -3.12 -m pip install ziglang python-can pyserial (or set NATIVE_CC / install gcc);"
                  " BENCH_ALLOW_SKIP=1 to accept the skips", red=True)


def pytest_sessionfinish(session, exitstatus):
    if _missing and os.environ.get("BENCH_ALLOW_SKIP") != "1" and exitstatus == 0:
        session.exitstatus = 1
