"""The lever boards on bus B: decode what they send, and the commands they take.

    python3 -m publicbench.levers list                 every board's uid, slot and status
    python3 -m publicbench.levers watch                positions as they change
    python3 -m publicbench.levers assign <uid> <slot>  give a board its lever (stored on the board)
    python3 -m publicbench.levers cal <slot>           rest, then full travel, then store
    python3 -m publicbench.levers thresh <slot> <mglt> <mght>   the MA730's field thresholds

The ids, ops and status bits are read from firmware/lever_sensor/lever.h, which is where they are
written down and explained; nothing here restates a number. Through motor_ctrl (MotorCtrlLink, bus
B is its bus 1) or any link with the same send / rx (CanLink, bus 0, for an adapter or the
simulator).
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
from dataclasses import dataclass

LEVER_H = os.path.join(os.path.dirname(__file__), "..", "..", "firmware", "lever_sensor", "lever.h")


def constants(path: str = LEVER_H) -> dict[str, int]:
    """Every plain #define in lever.h: numbers (0x.., ..u) and characters ('R')."""
    out = {}
    for name, v in re.findall(r"^#define\s+(\w+)\s+(0x[0-9A-Fa-f]+u?|\d+u?|'.')", open(path).read(), re.M):
        out[name] = ord(v[1]) if v.startswith("'") else int(v.rstrip("u"), 0)
    return out


K = constants()


@dataclass(frozen=True)
class Pos:
    t: float
    slot: int
    pos: float | None       # 0 at rest .. 1 at full travel; None uncalibrated
    status: int
    seq: int


@dataclass(frozen=True)
class Diag:
    t: float
    slot: int
    raw: int
    rest: int
    full: int
    field: int
    version: int


@dataclass(frozen=True)
class Hello:
    t: float
    uid: int
    slot: int | None
    version: int
    mode: int               # 0 application, 1 loader
    status: int


@dataclass(frozen=True)
class Reply:
    t: float
    slot: int
    op: str
    ok: bool


def decode(t: float, can_id: int, d: bytes):
    """One received frame as a Pos / Diag / Hello / Reply, or None if it is not a lever's."""
    if can_id & ~0xFFFFFF == K["ID_HELLO"] and len(d) >= 8:
        slot = d[4]
        return Hello(t, int.from_bytes(d[:4], "little"), None if slot == K["SLOT_NONE"] else slot,
                     d[5], d[6], d[7])
    base, slot = can_id & ~0xF, can_id & 0xF
    if base == K["ID_POS"] and len(d) >= 4:
        p = int.from_bytes(d[:2], "little")
        return Pos(t, slot, None if p == K["POS_NONE"] else p / K["POS_FULL"], d[2], d[3])
    if base == K["ID_DIAG"] and len(d) >= 8:
        u = lambda i: int.from_bytes(d[i:i + 2], "little")
        return Diag(t, slot, u(0), u(2), u(4), d[6], d[7])
    if base == K["ID_REPLY"] and len(d) >= 2:
        return Reply(t, slot, chr(d[0]), bool(d[1]))
    return None


STATUS = [("LV_MGL", "field weak"), ("LV_MGH", "field strong"), ("LV_UNCAL", "uncalibrated"),
          ("LV_UNSAVED", "unsaved"), ("LV_OUTSIDE", "past an end stop")]


def status_text(s: int) -> str:
    return ", ".join(w for name, w in STATUS if s & K[name]) or "ok"


class Levers:
    """Lever state from a link's received frames, and commands out through it."""

    def __init__(self, link, bus: int = 1):
        self.link, self.bus = link, bus
        self._k = 0
        self.pos: dict[int, Pos] = {}
        self.diag: dict[int, Diag] = {}
        self.hello: dict[int, Hello] = {}
        self.replies: list[Reply] = []

    def update(self):
        rx = self.link.rx
        while self._k < len(rx):
            f = rx[self._k]
            self._k += 1
            if f.bus != self.bus:
                continue
            m = decode(f.t, f.id, f.data)
            if isinstance(m, Pos):
                self.pos[m.slot] = m
            elif isinstance(m, Diag):
                self.diag[m.slot] = m
            elif isinstance(m, Hello):
                self.hello[m.uid] = m
            elif isinstance(m, Reply):
                self.replies.append(m)

    def position(self, slot: int) -> float | None:
        self.update()
        p = self.pos.get(slot)
        return p.pos if p else None

    def _send(self, can_id: int, data: bytes):
        self.link.send(can_id, data, bus=self.bus)

    def command(self, slot: int, op: str, args: bytes = b"", timeout: float = 0.5) -> bool:
        """Send one CMD and wait for its REPLY; True if the board said ok."""
        self.update()
        n = len(self.replies)
        self._send(K["ID_CMD"] + slot, bytes([ord(op)]) + args)

        def got():
            self.update()
            for r in self.replies[n:]:
                if r.slot == slot and r.op == op:
                    return r
        r = self.link.wait(got, timeout)
        if r is None:
            raise TimeoutError("lever slot %d did not answer %r" % (slot, op))
        return r.ok

    def identify(self, wait: float = 0.3) -> dict[int, Hello]:
        """Every board says HELLO; returns them by uid."""
        self.update()
        t0 = time.monotonic()
        self._send(K["ID_ALL"], bytes([K["LC_HELLO"]]))
        time.sleep(wait)
        self.update()
        return {u: h for u, h in self.hello.items() if h.t >= t0 - 0.05}

    def assign(self, uid: int, slot: int, timeout: float = 0.5) -> bool:
        self.update()
        t0 = time.monotonic()
        self._send(K["ID_ALL"], bytes([K["LC_SLOT"]]) + uid.to_bytes(4, "little") + bytes([slot]))

        def took():
            self.update()
            h = self.hello.get(uid)
            return h if h and h.t >= t0 and h.slot == slot else None
        return self.link.wait(took, timeout) is not None

    def rest(self, slot): return self.command(slot, "R")
    def full(self, slot): return self.command(slot, "F")
    def save(self, slot): return self.command(slot, "W", timeout=1.0)
    def loader(self, slot): return self.command(slot, "B")

    def cal(self, slot, rest: int, full: int):
        return self.command(slot, "K", rest.to_bytes(2, "little") + full.to_bytes(2, "little"))

    def thresholds(self, slot, mglt: int, mght: int):
        return self.command(slot, "T", bytes([mglt, mght]), timeout=1.0)


def main(argv=None):
    a = argparse.ArgumentParser()
    a.add_argument("what", choices=["list", "watch", "assign", "cal", "thresh"])
    a.add_argument("args", nargs="*")
    o = a.parse_args(argv)
    from .link import MotorCtrlLink
    link = MotorCtrlLink()
    lv = Levers(link, bus=1)
    try:
        if o.what == "list":
            for h in sorted(lv.identify().values(), key=lambda h: (h.slot is None, h.slot or 0)):
                print("uid %08x  slot %-4s v%d %s  %s" % (h.uid, "-" if h.slot is None else h.slot,
                      h.version, "loader" if h.mode else "app", status_text(h.status)))
        elif o.what == "watch":
            last = {}
            while True:
                lv.update()
                for s, p in sorted(lv.pos.items()):
                    v = None if p.pos is None else round(p.pos, 3)
                    if last.get(s) != (v, p.status):
                        last[s] = (v, p.status)
                        print("%8.3f  slot %2d  %s  %s" % (p.t, s, "-" if v is None else "%.3f" % v,
                              status_text(p.status)))
                time.sleep(0.02)
        elif o.what == "assign":
            uid, slot = int(o.args[0], 16), int(o.args[1])
            print("ok" if lv.assign(uid, slot) else "no answer from %08x" % uid)
        elif o.what == "cal":
            slot = int(o.args[0])
            input("lever %d at REST, then Enter " % slot)
            lv.rest(slot)
            input("lever %d at FULL travel, then Enter " % slot)
            lv.full(slot)
            print("stored" if lv.save(slot) else "the board could not write its flash")
        elif o.what == "thresh":
            slot, lo, hi = (int(x) for x in o.args[:3])
            print("ok" if lv.thresholds(slot, lo, hi) else "refused")
    except KeyboardInterrupt:
        pass
    finally:
        link.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
