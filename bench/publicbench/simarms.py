"""motor_ctrl R2's arm and lane switching, firmware/motor_ctrl/arms.c as it is, through ctypes
(as simlever.py runs lever.c). Needs a native C compiler."""
from __future__ import annotations

import ctypes
import hashlib
import os
import re
import subprocess
import tempfile

from .simlever import compiler

FW = os.path.join(os.path.dirname(__file__), "..", "..", "firmware", "motor_ctrl")
ARMS_H = os.path.join(FW, "arms.h")


def constants() -> dict[str, int]:
    return {n: int(v.rstrip("u"), 0) for n, v in
            re.findall(r"^#define\s+(\w+)\s+(\d+u?)\b", open(ARMS_H).read(), re.M)}


K = constants()
N = K["ARMS"]


class ArmsT(ctypes.Structure):
    _fields_ = [("power", ctypes.c_uint8 * N), ("usb", ctypes.c_uint8 * N), ("lane", ctypes.c_uint8),
                ("start", ctypes.c_uint8), ("cycle", ctypes.c_uint8), ("arm", ctypes.c_uint8),
                ("stop", ctypes.c_uint8), ("start_at", ctypes.c_uint32), ("stop_at", ctypes.c_uint32),
                ("on_pending", ctypes.c_uint8 * N), ("on_at", ctypes.c_uint32 * N)]


_LIB = None


def lib():
    global _LIB
    if _LIB is not None:
        return _LIB
    cc = compiler()
    if not cc:
        raise RuntimeError("no native C compiler for the arms simulator")
    srcs = [os.path.join(FW, "arms.c"), ARMS_H]
    shim = "#include <stddef.h>\n#include \"arms.h\"\nsize_t sim_arms_size(void) { return sizeof(arms_t); }\n"
    h = hashlib.sha1(shim.encode() + b"".join(open(p, "rb").read() for p in srcs)).hexdigest()[:12]
    d = os.path.join(tempfile.gettempdir(), "public-simarms-" + h)
    so = os.path.join(d, "libarms.so")
    if not os.path.exists(so):
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "shim.c"), "w").write(shim)
        subprocess.run([cc, "-O2", "-Wall", "-Wextra", "-Werror", "-shared", "-fPIC", "-I", FW,
                        srcs[0], os.path.join(d, "shim.c"), "-o", so + ".tmp"], check=True)
        os.replace(so + ".tmp", so)
    L = ctypes.CDLL(so)
    P, U, U32 = ctypes.POINTER(ArmsT), ctypes.c_uint, ctypes.c_uint32
    for name, args, res in (("sim_arms_size", [], ctypes.c_size_t),
                            ("arms_init", [P], None),
                            ("arms_power", [P, U, U, U32], ctypes.c_int),
                            ("arms_flash", [P, U, U32, U, U32], ctypes.c_int),
                            ("arms_poll", [P, U32], None),
                            ("arms_busy", [P], ctypes.c_int)):
        f = getattr(L, name)
        f.argtypes, f.restype = args, res
    assert L.sim_arms_size() == ctypes.sizeof(ArmsT), "arms_t and ArmsT differ"
    _LIB = L
    return L


class Arms:
    """One arms_t, stepped by hand."""

    def __init__(self):
        self.L = lib()
        self.s = ArmsT()
        self.L.arms_init(ctypes.byref(self.s))

    def power(self, arm, what, now_us): return bool(self.L.arms_power(ctypes.byref(self.s), arm, what, now_us & 0xFFFFFFFF))
    def flash(self, arm, ms, cycle, now_us): return bool(self.L.arms_flash(ctypes.byref(self.s), arm, ms, int(cycle), now_us & 0xFFFFFFFF))
    def poll(self, now_us): self.L.arms_poll(ctypes.byref(self.s), now_us & 0xFFFFFFFF)
    def busy(self): return bool(self.L.arms_busy(ctypes.byref(self.s)))
    def powered(self, arm): return bool(self.s.power[arm])
    def usb(self, arm): return bool(self.s.usb[arm])
    def lane(self): return bool(self.s.lane)
