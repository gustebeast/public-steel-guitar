"""Memory-gated job launcher (Windows): start a heavy job only when the RAM it needs is free.

    py -3.12 memgate.py [--name KIND] [--need GB] [--cap GB] [--margin GB] [--max N] -- CMD ARGS...
    py -3.12 memgate.py status

Replaces a fixed "at most N routes" rule. Before launching CMD it waits until

    available physical RAM  -  RAM still owed to running gated jobs  >=  need + margin

where a running job is owed (its need - what it uses now), so a job that has not ramped up
yet still holds its share. `need` defaults to the largest RAM peak recorded for KIND (x1.15),
or 4 GB before any record exists. `margin` is what stays free for everything else on the
machine (viewer, browser, KiCad, builds): by day (08:00-22:00) max(6 GB, the recorded
peak of a full CAD build x1.15) -- builds start ungated whenever an MR lands, so one may
begin after a route was admitted -- and 3 GB at night. Record a build peak once with
    memgate.py --name build --need 0 --margin 0 -- <the build command>

CMD and every process it starts run inside one Windows job object that
  * caps their total COMMITTED memory at --cap GB (default: 2x the largest commit peak
    recorded for KIND, at least 12 GB). Past the cap an allocation fails inside that job
    (MemoryError) -- the job dies, the rest of the machine does not page itself to a crawl;
  * is killed as a whole when memgate exits (TaskStop, Ctrl+C), so no orphan python is left.

On exit the job's peak RAM (sum of its processes' working sets, sampled every 5 s, and
never below any one process's own peak) and peak commit are appended to peaks.json, so the
next launch of KIND asks for what that work really used.

State lives in %LOCALAPPDATA%/cadkit/memgate (running.json, peaks.json, lock), or $MEMGATE_STATE.

⚠ RAM, NOT COMMIT, IS WHAT RUNS OUT HERE (brain_board routes, 2026-11-20). A route commits
~5.5 GB but touches 2-3 GB; the page file is system-managed (52 GB, commit limit 83 GB, peak
page-file use 2.2 GB), so the 4-route failure of 11-17 was physical RAM. Admission therefore
counts available RAM; the commit cap is only a runaway guard.
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import json
import msvcrt
import os
import shutil
import subprocess
import sys
import time

GB = 1 << 30
STATE = os.environ.get("MEMGATE_STATE") or os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "cadkit", "memgate")
SAMPLE_S = 5
WAIT_S = 30
DEFAULT_NEED_GB = 4.0
NEED_FACTOR = 1.15
MIN_CAP_GB = 12.0
MIN_NEED_GB = 0.5

k32 = ctypes.WinDLL("kernel32", use_last_error=True)


class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [("dwLength", wt.DWORD), ("dwMemoryLoad", wt.DWORD),
                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]


class BASIC_LIMIT(ctypes.Structure):
    _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", wt.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wt.DWORD),
                ("Affinity", ctypes.c_size_t), ("PriorityClass", wt.DWORD),
                ("SchedulingClass", wt.DWORD)]


class IO_COUNTERS(ctypes.Structure):
    _fields_ = [(n, ctypes.c_ulonglong) for n in ("r", "w", "o", "rb", "wb", "ob")]


class EXTENDED_LIMIT(ctypes.Structure):
    _fields_ = [("Basic", BASIC_LIMIT), ("Io", IO_COUNTERS),
                ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]


class PMC(ctypes.Structure):
    _fields_ = [("cb", wt.DWORD), ("PageFaultCount", wt.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                ("a", ctypes.c_size_t), ("b", ctypes.c_size_t), ("c", ctypes.c_size_t),
                ("d", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t)]


JobObjectBasicProcessIdList, JobObjectExtendedLimitInformation = 3, 9
LIMIT_JOB_MEMORY, LIMIT_KILL_ON_CLOSE = 0x200, 0x2000
QUERY = 0x1000 | 0x0010          # PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ
STILL_ACTIVE = 259

k32.CreateJobObjectW.restype = wt.HANDLE
k32.OpenProcess.restype = wt.HANDLE
k32.GetCurrentProcess.restype = wt.HANDLE
for _f, _a in ((k32.SetInformationJobObject, [wt.HANDLE, ctypes.c_int, ctypes.c_void_p, wt.DWORD]),
               (k32.QueryInformationJobObject, [wt.HANDLE, ctypes.c_int, ctypes.c_void_p, wt.DWORD,
                                                ctypes.c_void_p]),
               (k32.AssignProcessToJobObject, [wt.HANDLE, wt.HANDLE]),
               (k32.K32GetProcessMemoryInfo, [wt.HANDLE, ctypes.c_void_p, wt.DWORD]),
               (k32.GetExitCodeProcess, [wt.HANDLE, ctypes.POINTER(wt.DWORD)]),
               (k32.CloseHandle, [wt.HANDLE])):
    _f.argtypes = _a


def avail_ram():
    m = MEMORYSTATUSEX()
    m.dwLength = ctypes.sizeof(m)
    k32.GlobalMemoryStatusEx(ctypes.byref(m))
    return m.ullAvailPhys, m.ullTotalPhys


def alive(pid):
    h = k32.OpenProcess(QUERY, False, pid)
    if not h:
        return False
    code = wt.DWORD()
    ok = k32.GetExitCodeProcess(h, ctypes.byref(code))
    k32.CloseHandle(h)
    return bool(ok) and code.value == STILL_ACTIVE


def proc_mem(pid):
    """(working set, own peak working set) of one process, bytes; (0, 0) if gone."""
    h = k32.OpenProcess(QUERY, False, pid)
    if not h:
        return 0, 0
    c = PMC()
    c.cb = ctypes.sizeof(c)
    ok = k32.K32GetProcessMemoryInfo(h, ctypes.byref(c), c.cb)
    k32.CloseHandle(h)
    return (c.WorkingSetSize, c.PeakWorkingSetSize) if ok else (0, 0)


# ------------------------------------------------------------------ shared state

class Lock:
    def __enter__(self):
        os.makedirs(STATE, exist_ok=True)
        self.f = open(os.path.join(STATE, "lock"), "a+b")
        while True:
            try:
                msvcrt.locking(self.f.fileno(), msvcrt.LK_LOCK, 1)
                return self
            except OSError:
                continue

    def __exit__(self, *a):
        self.f.seek(0)
        msvcrt.locking(self.f.fileno(), msvcrt.LK_UNLCK, 1)
        self.f.close()


def _load(name, default):
    try:
        return json.load(open(os.path.join(STATE, name), encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _save(name, obj):
    p = os.path.join(STATE, name)
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1)
    os.replace(p + ".tmp", p)


def running():
    """The running gated jobs, dead ones dropped (call under Lock)."""
    jobs = {k: v for k, v in _load("running.json", {}).items() if alive(int(k))}
    _save("running.json", jobs)
    return jobs


def owed(jobs):
    return sum(max(0.0, j["need"] - j["ws"]) for j in jobs.values())


def default_margin():
    """By day, room for one ungated full CAD build to start after we admit (11-17: 4 routes
    + a build ran the machine out of RAM): max(6 GB, recorded build peak x1.15). Night 3 GB."""
    if not 8 <= time.localtime().tm_hour < 22:
        return 3.0
    h = [r["peak_ram_gb"] for r in history("build") if r["rc"] == 0][-8:]
    return max(6.0, round(max(h) * NEED_FACTOR, 1)) if h else 6.0


def history(kind):
    return [r for r in _load("peaks.json", []) if r.get("name") == kind]


def need_for(kind):
    # only clean finishes: a job that failed early or hit its cap never reached its real peak
    h = [r["peak_ram_gb"] for r in history(kind) if r["rc"] == 0 and not r["cap_hit"]][-8:]
    return max(MIN_NEED_GB, round(max(h) * NEED_FACTOR, 2)) if h else DEFAULT_NEED_GB


def cap_for(kind):
    h = [r["peak_commit_gb"] for r in history(kind)][-8:]
    return max(MIN_CAP_GB, round(2 * max(h), 1) if h else 0.0)


# ------------------------------------------------------------------ the job

def make_job(cap_gb):
    job = k32.CreateJobObjectW(None, None)
    if not job:
        raise OSError(ctypes.get_last_error(), "CreateJobObject")
    info = EXTENDED_LIMIT()
    info.Basic.LimitFlags = LIMIT_JOB_MEMORY | LIMIT_KILL_ON_CLOSE
    info.JobMemoryLimit = int(cap_gb * GB)
    if not k32.SetInformationJobObject(job, JobObjectExtendedLimitInformation,
                                       ctypes.byref(info), ctypes.sizeof(info)):
        raise OSError(ctypes.get_last_error(), "SetInformationJobObject")
    return job


def job_pids(job):
    n = 512
    buf = (ctypes.c_size_t * (n + 1))()      # 2 DWORDs pack into the first slot
    if not k32.QueryInformationJobObject(job, JobObjectBasicProcessIdList, buf,
                                         ctypes.sizeof(buf), None):
        return []
    count = buf[0] >> 32
    return [buf[1 + i] for i in range(min(count, n))]


def job_commit_peak(job):
    info = EXTENDED_LIMIT()
    k32.QueryInformationJobObject(job, JobObjectExtendedLimitInformation, ctypes.byref(info),
                                  ctypes.sizeof(info), None)
    return info.PeakJobMemoryUsed


def admit(kind, need, margin, max_jobs):
    told = False
    while True:
        with Lock():
            jobs = running()
            avail, _ = avail_ram()
            free = avail / GB - owed(jobs)
            if free >= need + margin and (max_jobs is None or len(jobs) < max_jobs):
                jobs[str(os.getpid())] = {"name": kind, "need": need, "ws": 0.0,
                                          "start": time.strftime("%m-%d %H:%M")}
                _save("running.json", jobs)
                print("memgate: %s admitted -- %.1f GB free after %.1f GB owed to %d job(s); "
                      "needs %.1f + %.1f margin" % (kind, free, owed(jobs) - need, len(jobs) - 1,
                                                     need, margin), flush=True)
                return
        if not told:
            print("memgate: %s waiting -- %.1f GB free, needs %.1f + %.1f margin%s" % (
                kind, free, need, margin,
                "" if max_jobs is None else ", %d/%d jobs" % (len(jobs), max_jobs)), flush=True)
            told = True
        time.sleep(WAIT_S)
        margin = margin if margin_fixed else default_margin()


def run(kind, need, cap, margin, max_jobs, cmd):
    admit(kind, need, margin, max_jobs)
    job = make_job(cap)
    # memgate joins the job first so everything CMD spawns inherits it; closing memgate
    # (normally or killed) closes the last handle and KILL_ON_JOB_CLOSE ends the tree
    if not k32.AssignProcessToJobObject(job, k32.GetCurrentProcess()):
        raise OSError(ctypes.get_last_error(), "AssignProcessToJobObject")
    t0 = time.time()
    # resolve CMD on PATH first: CreateProcess searches System32 before PATH, so a bare
    # "bash" from a Git Bash shell would start WSL's bash.exe instead
    p = subprocess.Popen([shutil.which(cmd[0]) or cmd[0]] + cmd[1:])
    peak = 0
    me = os.getpid()
    while p.poll() is None:
        total = 0
        for pid in job_pids(job):
            ws, own_peak = proc_mem(pid)
            total += ws
            if pid != me:
                peak = max(peak, own_peak)
        peak = max(peak, total)
        with Lock():
            jobs = _load("running.json", {})
            if str(me) in jobs:
                jobs[str(me)]["ws"] = round(total / GB, 2)
                _save("running.json", jobs)
        time.sleep(SAMPLE_S)
    commit = job_commit_peak(job)
    rec = {"name": kind, "end": time.strftime("%Y-%m-%d %H:%M"), "rc": p.returncode,
           "minutes": round((time.time() - t0) / 60, 1), "peak_ram_gb": round(peak / GB, 2),
           "peak_commit_gb": round(commit / GB, 2), "cap_gb": cap,
           "cap_hit": commit >= 0.98 * cap * GB, "cmd": " ".join(cmd)[:300]}
    with Lock():
        jobs = _load("running.json", {})
        jobs.pop(str(me), None)
        _save("running.json", jobs)
        _save("peaks.json", _load("peaks.json", []) + [rec])
    print("memgate: %s done rc %s in %.0f min -- peak RAM %.2f GB, peak commit %.2f GB%s" % (
        kind, p.returncode, rec["minutes"], rec["peak_ram_gb"], rec["peak_commit_gb"],
        " (CAP %.1f GB HIT)" % cap if rec["cap_hit"] else ""), flush=True)
    return p.returncode


def status():
    with Lock():
        jobs = running()
    avail, total = avail_ram()
    print("RAM %.1f GB available of %.1f; %.1f GB owed to %d gated job(s); margin now %.0f GB"
          % (avail / GB, total / GB, owed(jobs), len(jobs), default_margin()))
    for pid, j in jobs.items():
        print("  pid %s  %-10s since %s  uses %.1f / needs %.1f GB" % (
            pid, j["name"], j["start"], j["ws"], j["need"]))
    kinds = sorted({r["name"] for r in _load("peaks.json", [])})
    for k in kinds:
        h = history(k)
        print("  %-10s %d run(s), need next %.1f GB, cap %.0f GB, last peak RAM %.2f commit %.2f"
              % (k, len(h), need_for(k), cap_for(k), h[-1]["peak_ram_gb"], h[-1]["peak_commit_gb"]))


margin_fixed = False

if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["status"]:
        status()
        sys.exit(0)
    if "--" not in a:
        sys.exit(__doc__)
    opts, cmd = a[:a.index("--")], a[a.index("--") + 1:]
    o = dict(zip(opts[::2], opts[1::2]))
    kind = o.get("--name", "job")
    margin_fixed = "--margin" in o
    sys.exit(run(kind,
                 float(o["--need"]) if "--need" in o else need_for(kind),
                 float(o["--cap"]) if "--cap" in o else cap_for(kind),
                 float(o["--margin"]) if margin_fixed else default_margin(),
                 int(o["--max"]) if "--max" in o else None,
                 cmd))
