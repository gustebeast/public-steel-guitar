"""A pretend lever board running the REAL lever logic: firmware/lever_sensor/lever.c and its CAN
loader's ldr.c, compiled for this computer and driven through ctypes, on a python-can bus. Only
main.c's and boot.c's hardware is pretend (the MA730, a 32 K flash, the controller); every frame
it sends was made by the code that goes on the board. Needs a native C compiler (gcc / cc).
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
import zlib

FW = os.path.join(os.path.dirname(__file__), "..", "..", "firmware", "lever_sensor")

# the parts of main.c the simulator stands in for: the handful of fields it reads and clears
SHIM = r'''
#include <stddef.h>
#include "lever.h"
#include "ldr.h"
size_t sim_size(void) { return sizeof(lever_t); }
size_t sim_ldr_size(void) { return sizeof(ldr_t); }
void sim_mode(lever_t *l, unsigned m) { l->mode = (uint8_t)m; }
void sim_ldr_slot(ldr_t *b, unsigned s) { b->slot = (uint8_t)s; }
int sim_ldr_go(ldr_t *b) { int g = b->go; b->go = 0; return g; }
int sim_take_save(lever_t *l, lever_cfg_t *out)
{
    if (!l->want_save) return 0;
    l->want_save = 0; *out = l->cfg; l->unsaved = 0; return 1;
}
int sim_take_loader(lever_t *l) { int w = l->want_loader; l->want_loader = 0; return w; }
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
ERASE = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_uint32, ctypes.c_uint32)
WRITE = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32))


def lib():
    """lever.c + SHIM as a shared library, built once per source version."""
    global _LIB
    if _LIB is not None:
        return _LIB
    cc = compiler()
    if not cc:
        raise RuntimeError("no native C compiler for the lever simulator")
    srcs = [os.path.join(FW, n) for n in ("lever.c", "ldr.c", "lever.h", "ldr.h")]
    h = hashlib.sha1(SHIM.encode() + b"".join(open(p, "rb").read() for p in srcs)).hexdigest()[:12]
    d = os.path.join(tempfile.gettempdir(), "public-simlever-" + h)
    so = os.path.join(d, "liblever.so")
    if not os.path.exists(so):
        os.makedirs(d, exist_ok=True)
        shim = os.path.join(d, "shim.c")
        open(shim, "w").write(SHIM)
        subprocess.run([cc, "-O2", "-Wall", "-Wextra", "-Werror", "-shared", "-fPIC", "-I", FW,
                        srcs[0], srcs[1], shim, "-o", so + ".tmp"], check=True)
        os.replace(so + ".tmp", so)
    L = ctypes.CDLL(so)
    P, F, C = ctypes.c_void_p, ctypes.POINTER(Frame), ctypes.POINTER(Cfg)
    U = ctypes.c_uint
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
            ("sim_slot", [P], ctypes.c_uint),
            ("sim_ldr_size", [], ctypes.c_size_t),
            ("sim_mode", [P, U], None),
            ("sim_ldr_slot", [P, U], None),
            ("sim_ldr_go", [P], ctypes.c_int),
            ("ldr_init", [P, P, ERASE, WRITE, ctypes.c_uint8], None),
            ("ldr_app_ok", [P], ctypes.c_int),
            ("ldr_rx", [P, F], None),
            ("ldr_poll", [P, F], ctypes.c_int)):
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
        assert len(data) <= 8, "a CAN frame carries 8 bytes, not %d" % len(data)
        f = Frame(can_id, int(ext), len(data))
        for i, b in enumerate(data[:8]):
            f.d[i] = b
        self.L.lever_rx(self.buf, ctypes.byref(f))
        c = Cfg()
        if self.L.sim_take_save(self.buf, ctypes.byref(c)):
            self.flash = c                              # main.c's cfg_save, which works
        self.want_loader = bool(self.L.sim_take_loader(self.buf)) or getattr(self, "want_loader", False)
        self.L.sim_take_thresh(self.buf)

    def reboot(self, now_us=0):
        self.L.lever_init(self.buf, ctypes.byref(self.flash) if self.flash else None, self.uid, now_us)


class Board:
    """A whole board, stepped by hand: the application (a Lever) or, after CMD 'B' or with no
    good image, the loader (ldr.c on a pretend 32 K flash), as boot.c decides at a reset."""

    def __init__(self, uid=0x12345678, flash: bytearray | None = None, app_image: bytes | None = None):
        self.L = lib()
        self.mem = flash if flash is not None else bytearray(b"\xff" * 0x8000)
        self._fl = (ctypes.c_uint8 * len(self.mem)).from_buffer(self.mem)
        self._erase, self._write = ERASE(self._do_erase), WRITE(self._do_write)
        if app_image is not None:                       # what `make swd` puts there (image.py)
            K = _k()
            c = zlib.crc32(app_image)
            self.mem[K["APP_AT"]:K["APP_AT"] + len(app_image)] = app_image
            self.mem[K["REC_AT"]:K["REC_AT"] + 16] = b"".join(
                v.to_bytes(4, "little") for v in (K["REC_MAGIC"], len(app_image), c, c ^ 0xFFFFFFFF))
        self.lv = Lever(uid)
        self.ldr = ctypes.create_string_buffer(self.L.sim_ldr_size())
        self.stay = False
        self.reset()

    def _do_erase(self, off, n):
        self.mem[off:off + n] = b"\xff" * n
        return 1

    def _do_write(self, off, page):
        data = ctypes.string_at(page, 256)
        old = self.mem[off:off + 256]
        self.mem[off:off + 256] = bytes(a & b for a, b in zip(old, data))   # flash only clears bits
        return 1

    def app_ok(self):
        return bool(self.L.ldr_app_ok(self._fl))

    def reset(self, now_us=0):
        self.lv.reboot(now_us)
        self.lv.want_loader = False
        self.in_loader = self.stay or not self.app_ok()
        self.stay = False
        if self.in_loader:
            self.L.sim_mode(self.lv.buf, 1)
            self.L.ldr_init(self.ldr, self._fl, self._erase, self._write, self.lv.slot())

    def accepts(self, can_id, ext):
        """boot.c's / main.c's hardware filter."""
        K = _k()
        slot = self.lv.slot()
        ids = {K["ID_ALL"]}
        if slot < K["SLOTS"]:
            ids.add(K["ID_CMD"] + slot)
            if self.in_loader:
                ids |= {K["ID_LDR"] + slot, K["ID_LDR_D"] + slot}
        return not ext and can_id in ids

    def rx(self, can_id, data: bytes, ext=False):
        self.lv.rx(can_id, data, ext)
        if self.in_loader:
            self.L.sim_ldr_slot(self.ldr, self.lv.slot())
            f = Frame(can_id, int(ext), len(data))
            for i, b in enumerate(data[:8]):
                f.d[i] = b
            self.L.ldr_rx(self.ldr, ctypes.byref(f))

    def poll(self, now_us):
        """Frames due, and any restart they lead to (after the reply has gone)."""
        out = []
        if self.in_loader:
            f = Frame()
            while self.L.ldr_poll(self.ldr, ctypes.byref(f)):
                out.append((f.id, bool(f.ext), bytes(f.d[:f.len])))
        while True:
            f = self.lv.poll(now_us)
            if f is None:
                break
            out.append(f)
        if self.in_loader and self.L.sim_ldr_go(self.ldr):
            self.reset(now_us)
        elif not self.in_loader and self.lv.want_loader:
            self.stay = True
            self.reset(now_us)
        return out


def _k():
    from .levers import K
    return K


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
        self.board = Board(uid, app_image=b"\x13" * 64)      # a stand-in application
        self.lv = self.board.lv
        self.lock = threading.Lock()
        self._run = True

    def now_us(self):
        return int((time.monotonic() - self.t0) * 1e6)

    def reboot(self):
        with self.lock:
            self.board.reset(self.now_us())

    def run(self):
        from .levers import K
        sample = K["SAMPLE_US"] / 1e6
        nxt = time.monotonic()
        while self._run:
            with self.lock:
                if not self.board.in_loader:                # the loader has no sensor to read
                    self.lv.sample(int(self.angle()) & 0x3FFF)
                m = self.bus.recv(0)
                while m is not None:
                    if self.board.accepts(m.arbitration_id, m.is_extended_id):
                        self.board.rx(m.arbitration_id, bytes(m.data))
                    m = self.bus.recv(0)
                for can_id, ext, d in self.board.poll(self.now_us()):
                    self.bus.send(self._can.Message(arbitration_id=can_id, data=d, is_extended_id=ext))
            nxt += sample
            time.sleep(max(0.0, nxt - time.monotonic()))

    def stop(self):
        self._run = False
        self.join(1.0)
        self.bus.shutdown()
