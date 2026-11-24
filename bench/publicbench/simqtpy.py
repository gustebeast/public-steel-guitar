"""The QT Py bench firmware's logic (firmware/qtpy_bench: axis.c, tmc.c, bench.c), compiled
natively against a pretend TMC2209 and a pretend step timer, so its planner and its command line
can be tested with no board. Proves the code's arithmetic and protocol; says nothing about the
real timer, UART or motor.

The compiler is $NATIVE_CC if set (e.g. "python -m ziglang cc"), else gcc or cc on the PATH.
"""
from __future__ import annotations

import ctypes
import hashlib
import math
import os
import shlex
import shutil
import subprocess
import sys
import tempfile

FW = os.path.join(os.path.dirname(__file__), "..", "..", "firmware", "qtpy_bench")
SRCS = ("axis.c", "tmc.c", "bench.c")
HDRS = ("axis.h", "tmc.h", "bench.h")

SHIM = r"""
#include <string.h>
#include "bench.h"
#include "tmc.h"

static bench_t B;
static uint32_t regs[128];
static int en, fail, writes, armed, dir;
static uint32_t first;
static int32_t mscnt_off;   /* the driver's counter minus pos * per: set from Python (SimRig) */

static void s_enable(void *c, int on) { (void)c; en = on; }
static int s_write(void *c, uint8_t r, uint32_t v) {
    (void)c;
    if (fail) return -10;
    writes++;
    regs[TMC_IFCNT] = (regs[TMC_IFCNT] + 1) & 0xFF;
    if (r == TMC_GSTAT) regs[r] &= ~v; else regs[r] = v;
    return 0;
}
static int s_read(void *c, uint8_t r, uint32_t *v) {
    (void)c;
    if (fail) return -10;
    if (r == TMC_MSCNT)   /* the driver's counter follows the steps sent, at this MRES */
        regs[r] = (uint32_t)(B.ax.pos * (int32_t)tmc_mscnt_per_step(B.mres) + mscnt_off) & 1023u;
    *v = regs[r];
    return 0;
}
static void s_start(void *c, int d, uint32_t f) { (void)c; armed = 1; dir = d; first = f; }
static void s_stop(void *c) { (void)c; armed = 0; }
static void s_nop(void *c) { (void)c; }

#ifdef _WIN32
#define EXPORT __declspec(dllexport)
#else
#define EXPORT
#endif

EXPORT void sim_reset(uint32_t rsense) {
    bench_ops_t o = {s_enable, s_read, s_write, s_start, s_stop, s_nop, s_nop, 0};
    memset(regs, 0, sizeof regs);
    en = fail = writes = armed = dir = 0; first = 0; mscnt_off = 0;
    bench_init(&B, &o, rsense);
}
EXPORT int sim_line(const char *line, char *out, int n) { return bench_line(&B, line, out, n); }
/* runs the armed move to its end as the timer ISR would: the intervals, in ticks */
EXPORT int sim_run(uint32_t *iv, int max, int stop_after) {
    int k = 0;
    if (!armed) return 0;
    if (k < max) iv[k] = first;
    k++;
    for (;;) {
        if (stop_after >= 0 && k > stop_after) return k;
        uint32_t t = bench_step_isr(&B);
        if (!t) { armed = 0; return k; }
        if (k < max) iv[k] = t;
        k++;
    }
}
EXPORT int sim_armed(void) { return armed; }
EXPORT int sim_dir(void) { return dir; }
EXPORT int sim_en(void) { return en; }
EXPORT int sim_writes(void) { return writes; }
EXPORT void sim_fail(int f) { fail = f; }
EXPORT uint32_t sim_reg(int r) { return regs[r]; }
EXPORT void sim_set_reg(int r, uint32_t v) { regs[r] = v; }
EXPORT int32_t sim_pos(void) { return B.ax.pos; }
EXPORT void sim_set_mscnt_off(int32_t o) { mscnt_off = o; }
EXPORT uint32_t sim_per(void) { return tmc_mscnt_per_step(B.mres); }
EXPORT uint8_t sim_crc(const uint8_t *d, int n) { return tmc_crc(d, n); }
EXPORT void sim_write_dg(uint8_t *o, uint8_t a, uint8_t r, uint32_t v) { tmc_write_dg(o, a, r, v); }
EXPORT void sim_read_dg(uint8_t *o, uint8_t a, uint8_t r) { tmc_read_dg(o, a, r); }
EXPORT int sim_parse(const uint8_t *i, uint8_t r, uint32_t *v) { return tmc_parse_reply(i, r, v); }
EXPORT uint32_t sim_cs(uint32_t ma, uint32_t rs) { return tmc_cs_for_ma(ma, rs); }
EXPORT uint32_t sim_ma(uint32_t cs, uint32_t rs) { return tmc_ma_for_cs(cs, rs); }
EXPORT uint32_t sim_chop(int code, int dedge) { return tmc_chopconf(code, dedge); }
"""


def compiler() -> list[str] | None:
    env = os.environ.get("NATIVE_CC")
    if env:
        return shlex.split(env, posix=os.name != "nt")
    for name in ("gcc", "cc"):
        p = shutil.which(name)
        if p:
            return [p]
    return None


_LIB = None
TICK_HZ = 8_000_000


def lib():
    global _LIB
    if _LIB is not None:
        return _LIB
    cc = compiler()
    if not cc:
        raise RuntimeError("no native C compiler for the QT Py simulator")
    paths = [os.path.join(FW, n) for n in SRCS + HDRS]
    h = hashlib.sha1(SHIM.encode() + b"".join(open(p, "rb").read() for p in paths)).hexdigest()[:12]
    d = os.path.join(tempfile.gettempdir(), "public-simqtpy-" + h)
    so = os.path.join(d, "qtpy.dll" if sys.platform == "win32" else "libqtpy.so")
    if not os.path.exists(so):
        os.makedirs(d, exist_ok=True)
        shim = os.path.join(d, "shim.c")
        open(shim, "w").write(SHIM)
        subprocess.run(cc + ["-O2", "-Wall", "-Wextra", "-Werror", "-shared", "-fPIC", "-I", FW,
                             *[os.path.join(FW, s) for s in SRCS], shim, "-o", so + ".tmp"],
                       check=True)
        os.replace(so + ".tmp", so)
    L = ctypes.CDLL(so)
    U32, I32, P = ctypes.c_uint32, ctypes.c_int32, ctypes.c_char_p
    B = ctypes.POINTER(ctypes.c_uint8)
    for name, args, res in (
            ("sim_reset", [U32], None),
            ("sim_line", [P, ctypes.c_char_p, ctypes.c_int], ctypes.c_int),
            ("sim_run", [ctypes.POINTER(U32), ctypes.c_int, ctypes.c_int], ctypes.c_int),
            ("sim_armed", [], ctypes.c_int), ("sim_dir", [], ctypes.c_int),
            ("sim_en", [], ctypes.c_int), ("sim_writes", [], ctypes.c_int),
            ("sim_fail", [ctypes.c_int], None),
            ("sim_reg", [ctypes.c_int], U32), ("sim_set_reg", [ctypes.c_int, U32], None),
            ("sim_pos", [], I32), ("sim_set_mscnt_off", [I32], None), ("sim_per", [], U32),
            ("sim_crc", [B, ctypes.c_int], ctypes.c_uint8),
            ("sim_write_dg", [B, ctypes.c_uint8, ctypes.c_uint8, U32], None),
            ("sim_read_dg", [B, ctypes.c_uint8, ctypes.c_uint8], None),
            ("sim_parse", [B, ctypes.c_uint8, ctypes.POINTER(U32)], ctypes.c_int),
            ("sim_cs", [U32, U32], U32), ("sim_ma", [U32, U32], U32),
            ("sim_chop", [ctypes.c_int, ctypes.c_int], U32)):
        f = getattr(L, name)
        f.argtypes, f.restype = args, res
    _LIB = L
    return L


class QtPy:
    """One pretend board: send() a command line, run() an armed move to its end."""

    def __init__(self, rsense_mohm: int = 110):
        self.L = lib()
        self.L.sim_reset(rsense_mohm)

    def send(self, line: str) -> str:
        buf = ctypes.create_string_buffer(200)
        n = self.L.sim_line(line.encode(), buf, 160)
        return buf.raw[:n].decode()

    def run(self, max_steps: int = 1_000_000, stop_after: int = -1) -> list[int]:
        """The intervals (ticks) before each step of the armed move."""
        arr = (ctypes.c_uint32 * max_steps)()
        k = self.L.sim_run(arr, max_steps, stop_after)
        return list(arr[:min(k, max_steps)])

    def fields(self, reply: str) -> dict:
        assert reply.startswith("ok"), reply
        return {k: v for k, _, v in (w.partition("=") for w in reply.split()[1:]) if _}


def dg(fn, *args, n=8) -> bytes:
    b = (ctypes.c_uint8 * n)()
    fn(b, *args)
    return bytes(b)


class SimRig:
    """A pretend bench for publicbench.qtpy and publicbench.gates: a serial port (write/readline)
    into the native firmware, plus a pretend TMC2209 counter and a pretend rotor.

    State, in MSCNT units (1/256 full step; 1024 per electrical cycle, 4 full steps):
      mscnt  the driver's microstep counter
      rotor  the shaft's electrical angle, unwrapped
    The rotor follows the field while the coils are on. When the field comes on, or after a
    power-up at MSCNT 0, it snaps to the nearest angle equal to MSCNT mod 1024 (at most 2 full
    steps away). `stick` stops it that many units short, which is the self-locking screw's
    friction. With the coils off it falls to the nearest full-step detent if `detent`, less
    `stick`. `counts_when_off` says whether STEP edges advance MSCNT with the outputs off: the
    question gate (i) asks. All of this is a model, not a measurement."""

    def __init__(self, counts_when_off=False, stick=0, detent=False):
        self.q = QtPy()
        self.L = self.q.L
        self.counts_when_off, self.stick, self.detent = counts_when_off, stick, detent
        self.mscnt = 0
        self.rotor = 0.0
        self.out = b""
        self.cycles = 0

    # what the driver is doing
    def energized(self, moving=False):
        L = self.L
        on = L.sim_en() and (L.sim_reg(0x6C) & 0xF) != 0
        held = moving or (L.sim_reg(0x10) & 31) != 0       # IHOLD 0 = freewheel at rest
        return bool(on and held)

    def _sync(self):
        self.L.sim_set_mscnt_off(self.mscnt - self.L.sim_pos() * self.L.sim_per())

    def snap(self):
        k = round((self.rotor - self.mscnt) / 1024)
        eq = self.mscnt + 1024 * k
        d = self.rotor - eq
        self.rotor = eq + math.copysign(min(abs(d), self.stick), d) if d else eq

    def settle(self):
        if self.detent:
            eq = round(self.rotor / 256) * 256
            d = self.rotor - eq
            self.rotor = eq + math.copysign(min(abs(d), self.stick), d) if d else eq

    # the serial port
    def reset_input_buffer(self):
        self.out = b""

    def write(self, data):
        L = self.L
        e0 = self.energized()
        p0 = L.sim_pos()
        r = self.q.send(data.decode().strip())
        steps = 0
        if L.sim_armed():
            if not e0 and self.energized(moving=True):
                self.snap()                                 # the field comes on to move
            n = len(self.q.run())
            steps = n * L.sim_dir()
            per = L.sim_per()
            if self.energized(moving=True):
                self.mscnt += steps * per
                self.rotor += steps * per
            elif self.counts_when_off:
                self.mscnt += steps * per
        self.mscnt %= 1024
        e1 = self.energized()
        if e0 and not e1:
            self.settle()
        if not e0 and e1:
            self.snap()
        self._sync()
        self.out += (r + "\n").encode()

    def readline(self):
        line, _, self.out = self.out.partition(b"\n")
        return line + b"\n" if line else b""

    # the bench
    def power_cycle(self, msg=""):
        """VM off and on, the QT Py kept on USB: the driver resets, MSCNT 0, GSTAT.reset"""
        self.cycles += 1
        if self.energized():
            self.settle()
        L = self.L
        self.mscnt = 0
        for reg, v in ((0x00, 0x101), (0x01, 1), (0x02, 0), (0x10, 0x00071F10), (0x6C, 0x10000053)):
            L.sim_set_reg(reg, v)
        if self.energized():
            self.snap()
        self._sync()

    def truth(self) -> float:
        """the shaft, in driver steps at the current resolution: an encoder's view"""
        return self.rotor / self.L.sim_per()
