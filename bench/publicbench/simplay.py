"""motor_ctrl's play path in the simulator: firmware/motor_ctrl/play.c, compiled for this computer
and driven through ctypes, between two python-can buses. With simlever.SimLever on bus B and
sim.SimServo on bus A, a test runs the whole control path on the code that goes on the boards:
lever.c's frames in, play.c's motor frames out. Needs a native C compiler (gcc / cc).
"""
from __future__ import annotations

import ctypes
import hashlib
import os
import subprocess
import tempfile
import threading
import time

from .simlever import compiler

FW = os.path.join(os.path.dirname(__file__), "..", "..", "firmware", "motor_ctrl")


class Frame(ctypes.Structure):
    _fields_ = [("id", ctypes.c_uint32), ("ext", ctypes.c_uint8), ("len", ctypes.c_uint8),
                ("d", ctypes.c_uint8 * 8)]


SHIM = r'''
#include <stddef.h>
#include "play.h"
size_t sim_size(void) { return sizeof(play_t); }
size_t sim_table_size(void) { return sizeof(play_table_t); }
int sim_state(const play_t *p, unsigned s) { return p->state[s]; }
int sim_target(const play_t *p, unsigned s) { return p->target[s]; }
int sim_base(const play_t *p, unsigned s) { return p->base[s]; }
unsigned sim_moves(const play_t *p) { return p->moves; }
unsigned sim_pos(const play_t *p, unsigned c) { return p->pos[c]; }
'''

_LIB = None


def lib():
    global _LIB
    if _LIB is not None:
        return _LIB
    cc = compiler()
    if not cc:
        raise RuntimeError("no native C compiler for the play simulator")
    srcs = [os.path.join(FW, n) for n in ("play.c", "play.h")]
    h = hashlib.sha1(SHIM.encode() + b"".join(open(p, "rb").read() for p in srcs)).hexdigest()[:12]
    d = os.path.join(tempfile.gettempdir(), "public-simplay-" + h)
    so = os.path.join(d, "libplay.so")
    if not os.path.exists(so):
        os.makedirs(d, exist_ok=True)
        shim = os.path.join(d, "shim.c")
        open(shim, "w").write(SHIM)
        subprocess.run([cc, "-O2", "-Wall", "-Wextra", "-Werror", "-shared", "-fPIC", "-I", FW,
                        srcs[0], shim, "-o", so + ".tmp"], check=True)
        os.replace(so + ".tmp", so)
    L = ctypes.CDLL(so)
    P, F, U, I = ctypes.c_void_p, ctypes.POINTER(Frame), ctypes.c_uint, ctypes.c_int
    for name, args, res in (
            ("sim_size", [], ctypes.c_size_t), ("sim_table_size", [], ctypes.c_size_t),
            ("sim_state", [P, U], I), ("sim_target", [P, U], I), ("sim_base", [P, U], I),
            ("sim_moves", [P], U), ("sim_pos", [P, U], U),
            ("play_crc32", [ctypes.c_char_p, ctypes.c_uint32], ctypes.c_uint32),
            ("play_table_ok", [ctypes.c_char_p], I),
            ("play_init", [P, ctypes.c_char_p], None),
            ("play_rx", [P, ctypes.c_uint8, F, ctypes.c_uint32], None),
            ("play_poll", [P, ctypes.c_uint32, F], I),
            ("play_rebase", [P], None),
            ("play_cents", [P, ctypes.c_uint8], ctypes.c_int32),
            ("play_counts", [ctypes.c_char_p, ctypes.c_uint8, ctypes.c_int32], ctypes.c_int32)):
        f = getattr(L, name)
        f.argtypes, f.restype = args, res
    _LIB = L
    return L


class Play:
    """One play_t, stepped by hand."""

    def __init__(self, table: bytes | None):
        self.L = lib()
        assert table is None or len(table) == self.L.sim_table_size(), "copedent.SIZE vs play.h"
        self.buf = ctypes.create_string_buffer(self.L.sim_size())
        self.table = table
        self.L.play_init(self.buf, table)

    def rx(self, bus, can_id, data: bytes, now_us, ext=False):
        f = Frame(can_id, int(ext), len(data))
        for i, b in enumerate(data[:8]):
            f.d[i] = b
        self.L.play_rx(self.buf, bus, ctypes.byref(f), now_us & 0xFFFFFFFF)

    def poll(self, now_us):
        f = Frame()
        if self.L.play_poll(self.buf, now_us & 0xFFFFFFFF, ctypes.byref(f)):
            return f.id, bytes(f.d[:f.len])
        return None

    def cents(self, s): return self.L.play_cents(self.buf, s)
    def state(self, s): return self.L.sim_state(self.buf, s)
    def target(self, s): return self.L.sim_target(self.buf, s)
    def base(self, s): return self.L.sim_base(self.buf, s)
    def moves(self): return self.L.sim_moves(self.buf)
    def rebase(self): self.L.play_rebase(self.buf)


class SimMotorCtrl(threading.Thread):
    """motor_ctrl's main loop in real time: frames off bus B and A into play_rx, play_poll's frames
    onto bus A, one at a time as the controller's mailbox empties (one frame's wire time apart)."""

    def __init__(self, table: bytes, a_channel="public-sim-a", b_channel="public-sim-b",
                 bitrate=500_000):
        super().__init__(daemon=True)
        import can
        self._can = can
        self.a = can.Bus(channel=a_channel, interface="virtual")
        self.b = can.Bus(channel=b_channel, interface="virtual")
        self.play = Play(table)
        self.frame_s = 130 / bitrate                # an 8-byte frame with its stuffing
        self.t0 = time.monotonic()
        self.lock = threading.Lock()
        self.sent: list[tuple[float, int, bytes]] = []   # (time.monotonic(), id, data) onto bus A
        self._run = True

    def now_us(self):
        return int((time.monotonic() - self.t0) * 1e6)

    def run(self):
        free_at = 0.0
        while self._run:
            with self.lock:
                for bus, b in ((1, self.b), (0, self.a)):
                    m = b.recv(0)
                    while m is not None:
                        self.play.rx(bus, m.arbitration_id, bytes(m.data), self.now_us(), m.is_extended_id)
                        m = b.recv(0)
                t = time.monotonic()
                if t >= free_at:
                    f = self.play.poll(self.now_us())
                    if f:
                        self.a.send(self._can.Message(arbitration_id=f[0], data=f[1], is_extended_id=False))
                        self.sent.append((t, f[0], f[1]))
                        free_at = t + self.frame_s
            time.sleep(0.0002)

    def stop(self):
        self._run = False
        self.join(1.0)
        self.a.shutdown()
        self.b.shutdown()
