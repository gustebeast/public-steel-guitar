"""The two ways the bench reaches a CAN bus, behind one interface.

    MotorCtrlLink   the instrument's own motor controller over its USB serial port, running
                    firmware/motor_ctrl. Frames are sent at a time on the BOARD's clock and
                    received frames carry the board's time, so timing is the board's, not
                    this computer's.
    CanLink         python-can: a USB-CAN adapter (socketcan), or the in-process "virtual"
                    bus the simulator uses. Timing is this computer's, good to a millisecond
                    or so.

Both give times in SECONDS ON THIS COMPUTER'S time.monotonic() clock. For the board that is a
conversion, from a clock offset measured by asking it the time (see MotorCtrlLink.sync).
"""
from __future__ import annotations

import heapq
import threading
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class Frame:
    t: float            # when it was received (or left), seconds, time.monotonic()
    bus: int            # 0 = bus A (motors), 1 = bus B (levers)
    id: int
    data: bytes


# how long before a frame is due CanLink stops sleeping and spins. Short: a spinning thread
# holds Python's interpreter lock, and the simulator lives in the same process.
SPIN = 0.0003


class _Base:
    def __init__(self):
        self.rx: list[Frame] = []           # every frame received, in order
        self.sent: dict[int, float] = {}    # sequence number -> when the frame left
        self._seq = 0
        self._cv = threading.Condition()

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def _got(self, f: Frame):
        with self._cv:
            self.rx.append(f)
            self._cv.notify_all()

    def _left(self, seq: int, t: float):
        with self._cv:
            self.sent[seq] = t
            self._cv.notify_all()

    def wait(self, pred, timeout=1.0):
        """Block until pred() is true (checked on every frame in or out); its value, or None."""
        end = time.monotonic() + timeout
        with self._cv:
            while True:
                v = pred()
                if v:
                    return v
                left = end - time.monotonic()
                if left <= 0:
                    return None
                self._cv.wait(left)

    def wait_frame(self, match, after=0, timeout=1.0):
        """The first received frame at index >= after for which match(frame) is true."""
        def look():
            for f in self.rx[after:]:
                if match(f):
                    return f
        return self.wait(look, timeout)


class CanLink(_Base):
    """A python-can bus. `at` times are kept by a thread on this computer."""

    def __init__(self, channel="can0", interface="socketcan", **kw):
        super().__init__()
        import can
        self._can = can
        self.bus = can.Bus(channel=channel, interface=interface, **kw)
        self._heap: list = []
        self._wake = threading.Condition()
        self._run = True
        threading.Thread(target=self._reader, daemon=True).start()
        threading.Thread(target=self._sender, daemon=True).start()

    def send(self, can_id: int, data: bytes, at: float | None = None, bus: int = 0) -> int:
        seq = self._next_seq()
        with self._wake:
            heapq.heappush(self._heap, (at or 0.0, seq, can_id, bytes(data)))
            self._wake.notify()
        return seq

    def _sender(self):
        while self._run:
            with self._wake:
                while self._run:
                    d = self._heap[0][0] - time.monotonic() if self._heap else 0.1
                    if self._heap and d <= SPIN:
                        break
                    self._wake.wait(min(max(d - SPIN, 0.0001), 0.1))
                if not self._run:
                    return
                at, seq, can_id, data = heapq.heappop(self._heap)
            while time.monotonic() < at:                # the last SPIN seconds, spinning
                pass
            self.bus.send(self._can.Message(arbitration_id=can_id, data=data,
                                            is_extended_id=can_id > 0x7FF))
            self._left(seq, time.monotonic())

    def _reader(self):
        while self._run:
            m = self.bus.recv(0.1)
            if m is not None:
                self._got(Frame(time.monotonic(), 0, m.arbitration_id, bytes(m.data)))

    def close(self):
        self._run = False
        self.bus.shutdown()


class MotorCtrlLink(_Base):
    """firmware/motor_ctrl on a serial port (its line protocol is at the top of main.c)."""

    def __init__(self, port="/dev/ttyACM0"):
        super().__init__()
        import serial
        self.ser = serial.Serial(port, 115200, timeout=0.1)
        self.offset = None              # computer time - board time, seconds
        self.errors: list[str] = []
        self._times: list[tuple[float, int]] = []
        self._run = True
        threading.Thread(target=self._reader, daemon=True).start()
        self.sync()

    def _write(self, line: str):
        self.ser.write((line + "\n").encode())

    def sync(self, n=40) -> float:
        """Measure the clock offset: ask the time n times and keep the quickest round trip,
        whose reply sat least long in a USB frame. Returns that round trip, seconds."""
        best = None
        for _ in range(n):
            k = len(self._times)
            t0 = time.monotonic()
            self._write("T")
            got = self.wait(lambda: self._times[k] if len(self._times) > k else None, 0.5)
            if got is None:
                continue
            t1, dev_us = got
            if best is None or t1 - t0 < best[0]:
                best = (t1 - t0, (t0 + t1) / 2.0 - dev_us / 1e6)
        if best is None:
            raise RuntimeError("the motor controller does not answer on %s" % self.ser.port)
        self.offset = best[1]
        return best[0]

    def send(self, can_id: int, data: bytes, at: float | None = None, bus: int = 0) -> int:
        seq = self._next_seq()
        t_us = 0 if at is None else max(0, int(round((at - self.offset) * 1e6)))
        self._write("Q %d %d %d %X %s" % (seq, t_us, bus, can_id, bytes(data).hex()))
        return seq

    def set_rate(self, bus: int, bps: int):
        self._write("B %d %d" % (bus, bps))

    def _reader(self):
        buf = b""
        while self._run:
            buf += self.ser.read(4096)
            *lines, buf = buf.split(b"\n")
            now = time.monotonic()
            for raw in lines:
                p = raw.decode("ascii", "replace").split()
                if not p:
                    continue
                if p[0] == "T":
                    with self._cv:
                        self._times.append((now, int(p[1])))
                        self._cv.notify_all()
                elif p[0] == "R" and self.offset is not None:
                    self._got(Frame(int(p[2]) / 1e6 + self.offset, int(p[1]), int(p[3], 16),
                                    bytes.fromhex(p[4]) if len(p) > 4 else b""))
                elif p[0] == "D" and self.offset is not None and p[4] == "1":
                    self._left(int(p[1]), int(p[3]) / 1e6 + self.offset)
                elif p[0] in ("E", "L"):
                    self.errors.append(" ".join(p))

    def close(self):
        self._run = False
        self.ser.close()
