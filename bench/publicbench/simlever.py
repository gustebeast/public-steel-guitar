"""A pretend lever board running the REAL lever logic: firmware/lever_sensor/lever.c, compiled
for this computer and driven through ctypes, on a python-can bus. Only main.c's hardware is
pretend (the MA730, the flash page, the controller); every frame it sends was made by the code
that goes on the board. Needs a native C compiler (gcc / cc).
"""
from __future__ import annotations

import ctypes
import hashlib
import os
import shutil
import subprocess
import tempfile
import threading
import time

FW = os.path.join(os.path.dirname(__file__), "..", "..", "firmware", "lever_sensor")

# the parts of main.c the simulator stands in for: the handful of fields it reads and clears
SHIM = r'''
#include <stddef.h>
#include "lever.h"
size_t sim_size(void) { return sizeof(lever_t); }
int sim_take_save(lever_t *l, lever_cfg_t *out)
{
    if (!l->want_save) return 0;
    l->want_save = 0; *out = l->cfg; l->unsaved = 0; return 1;
}
int sim_take_loader(lever_t *l) { int w = l->want_loader; l->want_loader = 0; if (w && l->reply_n) l->reply.d[1] = 0; return w; }
int sim_take_thresh(lever_t *l) { int w = l->want_thresh; l->want_thresh = 0; return w; }
unsigned sim_slot(const lever_t *l) { return l->cfg.slot; }
'''


class Frame(ctypes.Structure):
    _fields_ = [("id", ctypes.c_uint32), ("ext", ctypes.c_uint8), ("len", ctypes.c_uint8),
                ("d", ctypes.c_uint8 * 8)]


class Cfg(ctypes.Structure):
    _fields_ = [("magic", ctypes.c_uint32), ("slot", ctypes.c_uint8), ("mglt", ctypes.c_uint8),
                ("mght", ctypes.c_uint8), ("spare", ctypes.c_uint8), ("rest", ctypes.c_uint16),
                ("full", ctypes.c_uint16), ("crc", ctypes.c_uint32)]


def compiler() -> str | None:
    return shutil.which("gcc") or shutil.which("cc")


_LIB = None


def lib():
    """lever.c + SHIM as a shared library, built once per source version."""
    global _LIB
    if _LIB is not None:
        return _LIB
    cc = compiler()
    if not cc:
        raise RuntimeError("no native C compiler for the lever simulator")
    srcs = [os.path.join(FW, "lever.c"), os.path.join(FW, "lever.h")]
    h = hashlib.sha1(SHIM.encode() + b"".join(open(p, "rb").read() for p in srcs)).hexdigest()[:12]
    d = os.path.join(tempfile.gettempdir(), "public-simlever-" + h)
    so = os.path.join(d, "liblever.so")
    if not os.path.exists(so):
        os.makedirs(d, exist_ok=True)
        shim = os.path.join(d, "shim.c")
        open(shim, "w").write(SHIM)
        subprocess.run([cc, "-O2", "-Wall", "-Wextra", "-Werror", "-shared", "-fPIC", "-I", FW,
                        srcs[0], shim, "-o", so + ".tmp"], check=True)
        os.replace(so + ".tmp", so)
    L = ctypes.CDLL(so)
    P, F, C = ctypes.c_void_p, ctypes.POINTER(Frame), ctypes.POINTER(Cfg)
    for name, args, res in (
            ("sim_size", [], ctypes.c_size_t),
            ("lever_init", [P, C, ctypes.c_uint32, ctypes.c_uint32], None),
            ("lever_sample", [P, ctypes.c_uint16], None),
            ("lever_field", [P, ctypes.c_uint8], None),
            ("lever_raw", [P], ctypes.c_uint16),
            ("lever_pos", [P], ctypes.c_uint16),
            ("lever_status", [P], ctypes.c_uint8),
            ("lever_poll", [P, ctypes.c_uint32, F], ctypes.c_int),
            ("lever_rx", [P, F], None),
            ("lever_crc32", [ctypes.c_char_p, ctypes.c_uint32], ctypes.c_uint32),
            ("lever_cfg_ok", [C], ctypes.c_int),
            ("sim_take_save", [P, C], ctypes.c_int),
            ("sim_take_loader", [P], ctypes.c_int),
            ("sim_take_thresh", [P], ctypes.c_int),
            ("sim_slot", [P], ctypes.c_uint)):
        f = getattr(L, name)
        f.argtypes, f.restype = args, res
    _LIB = L
    return L


class Lever:
    """One lever_t, stepped by hand: the unit tests' handle on the firmware logic."""

    def __init__(self, uid=0x12345678, flash: Cfg | None = None, now_us=0):
        self.L = lib()
        self.buf = ctypes.create_string_buffer(self.L.sim_size())
        self.flash = flash
        self.uid = uid
        self.L.lever_init(self.buf, ctypes.byref(flash) if flash else None, uid, now_us)

    def sample(self, raw): self.L.lever_sample(self.buf, raw & 0x3FFF)
    def field(self, f): self.L.lever_field(self.buf, f)
    def raw(self): return self.L.lever_raw(self.buf)
    def pos(self): return self.L.lever_pos(self.buf)
    def status(self): return self.L.lever_status(self.buf)
    def slot(self): return self.L.sim_slot(self.buf)

    def poll(self, now_us):
        f = Frame()
        if self.L.lever_poll(self.buf, now_us & 0xFFFFFFFF, ctypes.byref(f)):
            return f.id, bool(f.ext), bytes(f.d[:f.len])
        return None

    def rx(self, can_id, data: bytes, ext=False):
        f = Frame(can_id, int(ext), len(data))
        for i, b in enumerate(data[:8]):
            f.d[i] = b
        self.L.lever_rx(self.buf, ctypes.byref(f))
        c = Cfg()
        if self.L.sim_take_save(self.buf, ctypes.byref(c)):
            self.flash = c                              # main.c's cfg_save, which works
        self.L.sim_take_loader(self.buf)
        self.L.sim_take_thresh(self.buf)

    def reboot(self, now_us=0):
        self.L.lever_init(self.buf, ctypes.byref(self.flash) if self.flash else None, self.uid, now_us)


class SimLever(threading.Thread):
    """A Lever on a python-can bus in real time: angle() gives the magnet's 14-bit angle now.
    The hardware filter is main.c's: this board's CMD id and the broadcast, nothing else."""

    def __init__(self, uid, angle, channel="public-sim", interface="virtual"):
        super().__init__(daemon=True)
        import can
        self._can = can
        self.bus = can.Bus(channel=channel, interface=interface)
        self.angle = angle
        self.t0 = time.monotonic()
        self.lv = Lever(uid, now_us=0)
        self.lock = threading.Lock()
        self._run = True

    def now_us(self):
        return int((time.monotonic() - self.t0) * 1e6)

    def reboot(self):
        with self.lock:
            self.lv.reboot(self.now_us())

    def run(self):
        from .levers import K
        sample = K["SAMPLE_US"] / 1e6
        nxt = time.monotonic()
        while self._run:
            with self.lock:
                self.lv.sample(int(self.angle()) & 0x3FFF)
                m = self.bus.recv(0)
                while m is not None:
                    slot = self.lv.slot()
                    if not m.is_extended_id and (m.arbitration_id == K["ID_ALL"] or
                                                 (slot < K["SLOTS"] and m.arbitration_id == K["ID_CMD"] + slot)):
                        self.lv.rx(m.arbitration_id, bytes(m.data))
                    m = self.bus.recv(0)
                while True:
                    f = self.lv.poll(self.now_us())
                    if f is None:
                        break
                    can_id, ext, d = f
                    self.bus.send(self._can.Message(arbitration_id=can_id, data=d, is_extended_id=ext))
            nxt += sample
            time.sleep(max(0.0, nxt - time.monotonic()))

    def stop(self):
        self._run = False
        self.join(1.0)
        self.bus.shutdown()
