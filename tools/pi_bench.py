"""The bench code of THIS worktree, on the Pi, in one command: pushed to its own folder there,
then tested or run in it. The Pi's own copy (~/public-steel-guitar, what the phone service and the
pedal demo run) is never touched.

    py -3.12 tools/pi_bench.py push                       copy it over; print the folder
    py -3.12 tools/pi_bench.py test                       push, then the bench suite on the Pi
    py -3.12 tools/pi_bench.py test -- tests/test_gates.py -x
    py -3.12 tools/pi_bench.py run openloop --only speed  push, then python3 -m publicbench.openloop ...
    py -3.12 tools/pi_bench.py run rampsweep --bg         ... detached, output to a log on the Pi
    py -3.12 tools/pi_bench.py list                       the pushed folders, newest first
    py -3.12 tools/pi_bench.py prune --keep 5             delete all but the newest 5 (asks first)

WHY (2026-11-25): a day of SERVO42D runs meant pushing files by hand about ten times: a
git-archive into a side folder, scp of single files, tars into /tmp to run the native tests the
PC could not compile, and stopping and restarting the phone service around every run.

WHAT GOES: the worktree's bench/ and firmware/ as they are on disk: tracked files, with
uncommitted edits, and untracked files that git does not ignore. It lands in
~/bench-runs/<branch>-<commit>[-dirty-<hash of the edits>], so each state of the code has its own
folder and a run's results can be traced to the code that made them.

RUN, SAFELY (lead, 2026-11-25):
  * it REFUSES to start while the pedal demo (publicbench.pedaldrive) runs: no override. Both
    drive the same motor through the same port;
  * the phone service shares motor_ctrl's serial port, so `run` stops it first and starts it
    again in a shell `trap ... EXIT` on the Pi: a run that crashes, is interrupted, or loses this
    ssh connection still brings it back. --keep-phone leaves it alone (a run that needs no port);
  * --bg detaches the run (nohup) with the same trap inside it, and prints the log's path.
`prune` deletes folders on the Pi, so it lists them and asks before it does; nothing else here
deletes anything.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import os
import shlex
import subprocess
import sys
import tarfile
import time

HOST = os.environ.get("PI_BENCH_HOST", "gus@public-steel-guitar.local")
RUNS = "bench-runs"                         # under the Pi user's home
PHONE = "public-steel-guitar-phone"
PEDAL = "[p]ublicbench.pedaldrive"          # the bracket keeps pgrep from matching its own shell
DIRS = ("bench", "firmware")
SSH = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10"]


def git(*args, cwd=None) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                          text=True).stdout


def root() -> str:
    return git("rev-parse", "--show-toplevel").strip()


def files(top: str) -> list[str]:
    """Tracked plus untracked-not-ignored files under DIRS, as they are on disk."""
    out = git("ls-files", "--cached", "--others", "--exclude-standard", "-z", "--", *DIRS, cwd=top)
    return sorted({f for f in out.split("\0") if f and os.path.isfile(os.path.join(top, f))})


def label(branch: str, commit: str, dirty: str | None) -> str:
    """The folder's name: one per state of the code."""
    safe = "".join(c if c.isalnum() or c in "-._" else "-" for c in branch) or "detached"
    return "%s-%s%s" % (safe, commit[:8], "-dirty-" + dirty[:8] if dirty else "")


def state(top: str) -> str:
    branch = git("rev-parse", "--abbrev-ref", "HEAD", cwd=top).strip()
    commit = git("rev-parse", "HEAD", cwd=top).strip()
    changed = git("status", "--porcelain", "--", *DIRS, cwd=top)
    dirty = None
    if changed.strip():
        h = hashlib.sha1(changed.encode())
        for f in sorted(line[3:].strip() for line in changed.splitlines()):
            p = os.path.join(top, f)
            if os.path.isfile(p):
                h.update(open(p, "rb").read())
        dirty = h.hexdigest()
    return label(branch, commit, dirty)


def tarball(top: str, names: list[str]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as t:
        for n in names:
            t.add(os.path.join(top, n), arcname=n.replace(os.sep, "/"))
    return buf.getvalue()


def ssh(cmd: str, data: bytes | None = None, check=True) -> int:
    r = subprocess.run(SSH + [HOST, cmd], input=data)
    if check and r.returncode:
        raise SystemExit("on the Pi, exit %d: %s" % (r.returncode, cmd[:120]))
    return r.returncode


def push() -> str:
    top = root()
    names = files(top)
    dest = "%s/%s" % (RUNS, state(top))
    ssh("mkdir -p %s && tar -xf - -C %s" % (shlex.quote(dest), shlex.quote(dest)), tarball(top, names))
    print("pushed %d files to %s:~/%s" % (len(names), HOST.split("@")[-1], dest), file=sys.stderr)
    return dest


def run_script(dest: str, module: str, args: list[str], phone: bool, bg: str | None) -> str:
    """The shell the Pi runs: pedal demo check, phone off with a trap that puts it back, run."""
    cmd = "python3 -u -m publicbench.%s %s" % (module, " ".join(shlex.quote(a) for a in args))
    body = ["cd ~/%s/bench" % shlex.quote(dest)]
    if phone:
        body += ["was=$(systemctl is-active %s)" % PHONE,
                 "trap '[ \"$was\" = active ] && sudo systemctl start %s' EXIT" % PHONE,
                 "trap 'exit 129' HUP INT TERM",     # a signal (a dropped ssh) exits: the EXIT trap
                 "sudo systemctl stop %s" % PHONE]
    body.append(cmd)
    inner = "; ".join(body[:1]) + "; " + "; ".join(body[1:])
    # the message must not name the module plainly, or pgrep would find this very shell
    guard = ("if pgrep -f %s >/dev/null; then echo 'the pedal demo is running: stop it first "
             "(pkill -TERM -f \"[p]ython3 -u -m publicbench[.]pedaldrive\")' >&2; exit 3; fi"
             % shlex.quote(PEDAL))
    if bg:
        return "%s; nohup bash -c %s > %s 2>&1 < /dev/null & echo \"log: $HOME/%s\"" % (
            guard, shlex.quote(inner), shlex.quote(bg), bg)
    return "%s; %s" % (guard, inner)


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = a.add_subparsers(dest="cmd", required=True)
    sub.add_parser("push")
    t = sub.add_parser("test")
    t.add_argument("pytest", nargs=argparse.REMAINDER, help="after --: pytest arguments")
    r = sub.add_parser("run")
    r.add_argument("module", help="publicbench module, e.g. openloop, rampsweep, gates")
    r.add_argument("--keep-phone", action="store_true", help="leave the phone service running")
    r.add_argument("--bg", action="store_true", help="detach; output to ~/<module>-<time>.log")
    r.add_argument("args", nargs=argparse.REMAINDER)
    sub.add_parser("list")
    p = sub.add_parser("prune")
    p.add_argument("--keep", type=int, default=5)
    p.add_argument("--yes", action="store_true", help="do not ask")
    o = a.parse_args(argv)

    if o.cmd == "push":
        print(push())
    elif o.cmd == "test":
        dest = push()
        extra = [x for x in o.pytest if x != "--"] or ["tests/"]
        return ssh("cd ~/%s/bench && python3 -m pytest -q %s" % (
            shlex.quote(dest), " ".join(shlex.quote(x) for x in extra)), check=False)
    elif o.cmd == "run":
        if o.module == "pedaldrive":
            raise SystemExit("the pedal demo is started by hand (memory: pedal-demo), not by pi_bench")
        dest = push()
        bg = "%s-%s.log" % (o.module, time.strftime("%m%d-%H%M%S")) if o.bg else None
        return ssh(run_script(dest, o.module, [x for x in o.args if x != "--"], not o.keep_phone, bg),
                   check=False)
    elif o.cmd == "list":
        ssh("ls -1t ~/%s 2>/dev/null || true" % RUNS)
    elif o.cmd == "prune":
        out = subprocess.run(SSH + [HOST, "ls -1t ~/%s 2>/dev/null || true" % RUNS],
                             capture_output=True, text=True).stdout.split()
        old = out[o.keep:]
        if not old:
            print("nothing to prune (%d folders, keeping %d)" % (len(out), o.keep))
            return 0
        print("would delete on the Pi, ~/%s/:\n  %s" % (RUNS, "\n  ".join(old)))
        if not o.yes and input("delete these %d folders? [y/N] " % len(old)).strip().lower() != "y":
            print("kept")
            return 0
        ssh("cd ~/%s && rm -rf -- %s" % (RUNS, " ".join(shlex.quote(x) for x in old)))
        print("deleted %d" % len(old))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
