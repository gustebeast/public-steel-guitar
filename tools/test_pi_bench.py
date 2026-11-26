"""tools/pi_bench.py without the Pi: folder names, and the shell a run sends."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import pi_bench as P  # noqa: E402


def test_one_folder_per_state_of_the_code():
    assert P.label("agent/brenner-x", "0123456789abcdef", None) == "agent-brenner-x-01234567"
    assert P.label("main", "0123456789abcdef", "feedfacecafe") == "main-01234567-dirty-feedface"
    assert P.label("", "0123456789", None) == "detached-01234567"


def test_a_run_checks_the_pedal_demo_first_and_always_restarts_the_phone():
    sh = P.run_script("bench-runs/x", "openloop", ["--only", "speed"], phone=True, bg=None)
    guard, rest = sh.split("; ", 1)
    assert guard.startswith("if pgrep -f '[p]ublicbench.pedaldrive'") and "exit 3" in sh
    assert rest.index("trap") < rest.index("systemctl stop") < rest.index("python3 -u -m publicbench.openloop")
    assert "systemctl start public-steel-guitar-phone' EXIT" in sh and "HUP INT TERM" in sh
    assert "--only speed" in sh


def test_the_guard_does_not_match_its_own_shell():
    # pgrep -f matches whole command lines: the run's own must not contain what it looks for
    sh = P.run_script("bench-runs/x", "gates", ["2"], phone=True, bg="gates.log")
    pattern = P.PEDAL                              # a regex: the bracket matches 'p'
    assert not re.search(pattern, sh)
    assert re.search(pattern, "python3 -u -m publicbench.pedaldrive --semitones 2")


def test_background_runs_keep_the_trap_inside_the_detached_shell():
    sh = P.run_script("bench-runs/x", "rampsweep", [], phone=True, bg="rampsweep-1.log")
    assert "nohup bash -c" in sh and sh.index("nohup") < sh.index("trap")
    assert "> rampsweep-1.log 2>&1" in sh


def test_keep_phone_leaves_the_service_alone():
    sh = P.run_script("bench-runs/x", "qtpy", ["st"], phone=False, bg=None)
    assert "systemctl" not in sh
