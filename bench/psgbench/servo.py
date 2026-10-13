"""The MKS SERVO42D's CAN commands, as far as the bench needs them.

Checked 2026-10-13 against Makerbase's "MKS SERVO42D/57D_CAN User Manual" V1.0.5: the
checksum, every code and field below, 0x4000 counts per turn, and the move replies. The
manual's own example frames are in tests/test_sim.py. Its defaults: CAN id 1, 500 kbit/s,
replies on. NOT yet checked against a motor, and the motors' firmware version is unknown
(the manual's history says F4 and F5 were reworked in later releases).

Two things the manual says that a test must respect:
  * commands over the bus work in the SR_ work modes; SR_vFOC (mode 5) is the closed-loop
    one that reaches 3000 rpm. set_mode() sets it; it is kept by the motor.
  * F5 (absolute) takes a new target while the last move is still running; F4 (relative)
    is not said to.
`acc` 0 means no ramp at all. What 1..255 mean in rpm per second is not in this manual's
text (remembered from another edition as one rpm every (256 - acc) x 50 microseconds):
measure it.

A frame is: CAN id = the motor's address (1..), data = code, parameters, checksum, where
checksum = (id + every data byte before it) & 0xFF. Multi-byte fields are big-endian.
The encoder counts 0x4000 (16384) per turn of the motor shaft.
"""
from __future__ import annotations

from .link import Frame

COUNTS_PER_TURN = 0x4000

READ_ENCODER = 0x31         # reply: int48 accumulated counts
READ_SPEED = 0x32           # reply: int16 rpm
READ_ERROR = 0x39           # reply: int32 angle error, 51200 per turn
ENABLE = 0xF3               # 1 byte: 1 on, 0 off
SET_MODE = 0x82             # 1 byte: 0..2 pulse-input modes, 3 SR_OPEN, 4 SR_CLOSE, 5 SR_vFOC
SR_VFOC = 5
MOVE_REL = 0xF4             # speed u16, acc u8, int24 counts, relative
MOVE_ABS = 0xF5             # speed u16, acc u8, int24 counts, absolute
# a move is answered twice: status 1 when it starts, 2 when it has arrived
# (0 = refused, 3 = stopped by an end limit)
STARTED, ARRIVED, LIMIT = 1, 2, 3


def pack(can_id: int, body: bytes) -> bytes:
    return bytes(body) + bytes([(can_id + sum(body)) & 0xFF])


def check(can_id: int, data: bytes) -> bool:
    return len(data) >= 2 and data[-1] == (can_id + sum(data[:-1])) & 0xFF


def _i24(v: int) -> bytes:
    if not -0x800000 <= v <= 0x7FFFFF:
        raise ValueError("a move of %d counts does not fit 24 bits" % v)
    return (v & 0xFFFFFF).to_bytes(3, "big")


def move(code: int, counts: int, rpm: int, acc: int) -> bytes:
    if not (0 <= rpm <= 3000 and 0 <= acc <= 255):
        raise ValueError("speed 0..3000 rpm, acc 0..255")
    return bytes([code]) + rpm.to_bytes(2, "big") + bytes([acc]) + _i24(counts)


def parse(can_id: int, data: bytes):
    """(code, value) of a reply, or None if its checksum is wrong."""
    if not check(can_id, data):
        return None
    code, body = data[0], data[1:-1]
    if code == READ_ENCODER:
        return code, int.from_bytes(body[:6], "big", signed=True)
    if code in (READ_SPEED, READ_ERROR):
        return code, int.from_bytes(body, "big", signed=True)
    return code, body[0] if body else None


class Servo:
    def __init__(self, link, can_id: int, bus: int = 0):
        self.link, self.id, self.bus = link, can_id, bus

    def _send(self, body: bytes, at=None) -> int:
        return self.link.send(self.id, pack(self.id, body), at=at, bus=self.bus)

    def _mine(self, code):
        return lambda f: f.bus == self.bus and f.id == self.id and f.data[:1] == bytes([code])

    def enable(self, on=True, at=None):
        return self._send(bytes([ENABLE, 1 if on else 0]), at)

    def set_mode(self, mode: int = SR_VFOC, at=None):
        return self._send(bytes([SET_MODE, mode]), at)

    def move_rel(self, counts: int, rpm: int, acc: int, at=None) -> int:
        """Turn by `counts` (16384 per turn) from where it is. Returns the frame's sequence
        number: link.sent[seq] is when the command left."""
        return self._send(move(MOVE_REL, counts, rpm, acc), at)

    def move_abs(self, counts: int, rpm: int, acc: int, at=None) -> int:
        return self._send(move(MOVE_ABS, counts, rpm, acc), at)

    def ask_position(self, at=None) -> int:
        return self._send(bytes([READ_ENCODER]), at)

    def position(self, timeout=0.5) -> int:
        """Ask and wait: accumulated encoder counts."""
        n = len(self.link.rx)
        self.ask_position()
        f = self.link.wait_frame(self._mine(READ_ENCODER), n, timeout)
        if f is None:
            raise TimeoutError("motor %d did not answer" % self.id)
        return parse(self.id, f.data)[1]

    def positions(self, frames: list[Frame]):
        """[(t, counts)] from every encoder reply of this motor in `frames`."""
        out = []
        for f in frames:
            if self._mine(READ_ENCODER)(f):
                p = parse(self.id, f.data)
                if p:
                    out.append((f.t, p[1]))
        return out

    def arrived(self, frames: list[Frame]):
        """[t] of every "move complete" reply of this motor in `frames`."""
        return [f.t for f in frames
                if f.bus == self.bus and f.id == self.id and f.data[:1] in (bytes([MOVE_REL]), bytes([MOVE_ABS]))
                and (parse(self.id, f.data) or (0, 0))[1] == ARRIVED]
