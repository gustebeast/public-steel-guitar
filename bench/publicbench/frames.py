"""motor_ctrl R2's link: U7 (a CH340C) on the board's USART1, every line inside a checked frame.

The host's copy of firmware/motor_ctrl/frame.h, which says why. On the wire each frame is

    0x00  COBS(payload, CRC-16/CCITT-FALSE high byte first)  0x00

and a frame carries whole lines only, so a frame lost to a bad CRC loses lines and never splices
two halves into a third. FramedSerial wraps the port so the callers still see a byte stream of
lines: R1 (the MCU's own USB, ttyACM) and R2 (ttyUSB) look the same above open_motor().

The baud rate is the firmware's: LINK_BAUD in firmware/motor_ctrl/link.h, read from there, so
a CH343P in U7's place changes one line in one file.

U7's DTR# / RTS# reach BOOT0 / NRST through a crossed pair that acts only when they DIFFER, so
opening and closing the port (Linux raises both together) never resets the board. reset() and
rom() set both lines in ONE ioctl, so they are never seen half-changed.
"""
from __future__ import annotations

import glob
import os
import re
import struct
import time

FRAME_MAX = 300                 # frame.h: "W addr crc\n" and a 256-byte page fit in one
LINK_H = os.path.join(os.path.dirname(__file__), "..", "..", "firmware", "motor_ctrl", "link.h")
CH340 = ("1a86", "7523")        # U7
HUB = ("1a86", "8091")          # the CH334 hubs on output_panel / optical: their bridges, not U7


def link_baud(path: str = LINK_H) -> int:
    """LINK_BAUD from the firmware's link.h: the one place the rate is written."""
    m = re.search(r"#define\s+LINK_BAUD\s+(\d+)u?", open(path).read())
    if not m:
        raise RuntimeError("no LINK_BAUD in " + path)
    return int(m.group(1))


def crc16(data: bytes) -> int:
    c = 0xFFFF
    for b in data:
        c ^= b << 8
        for _ in range(8):
            c = ((c << 1) ^ 0x1021) if c & 0x8000 else c << 1
            c &= 0xFFFF
    return c


def encode(payload: bytes) -> bytes:
    if len(payload) > FRAME_MAX:
        raise ValueError("frame payload %d > %d" % (len(payload), FRAME_MAX))
    crc = crc16(payload)
    body = bytes(payload) + bytes([crc >> 8, crc & 0xFF])
    out = bytearray(b"\x00")
    block = bytearray()
    for b in body:
        if b == 0:
            out += bytes([len(block) + 1]) + block
            block.clear()
        else:
            block.append(b)
            if len(block) == 254:
                out += b"\xff" + block
                block.clear()
    out += bytes([len(block) + 1]) + block + b"\x00"
    return bytes(out)


def _cobs_decode(enc: bytes) -> bytes | None:
    out = bytearray()
    i = 0
    while i < len(enc):
        code = enc[i]
        i += 1
        if code == 0 or i + code - 1 > len(enc):
            return None
        out += enc[i:i + code - 1]
        i += code - 1
        if code != 0xFF and i < len(enc):
            out.append(0)
    return bytes(out)


class Deframer:
    """Wire bytes in, good payloads out; bad frames counted, as frame_feed() does."""

    def __init__(self):
        self.buf = bytearray()
        self.bad = 0

    def feed(self, data: bytes) -> list[bytes]:
        got = []
        for b in data:
            if b:
                self.buf.append(b)
                continue
            if self.buf:                        # 00 00 is no frame, and not an error
                body = _cobs_decode(bytes(self.buf))
                if (body is None or len(body) < 2 or len(body) > FRAME_MAX + 2
                        or crc16(body[:-2]) != (body[-2] << 8 | body[-1])):
                    self.bad += 1
                else:
                    got.append(body[:-2])
                self.buf.clear()
        return got


def pack_lines(data: bytes) -> list[bytes]:
    """Split one write into frames, each ending on a line, none over FRAME_MAX. A write that
    fits goes whole, so the loader's "W" line and its page (which may hold 0x0a) stay one."""
    data = bytes(data)
    out = []
    while len(data) > FRAME_MAX:
        cut = data.rfind(b"\n", 0, FRAME_MAX) + 1
        if cut <= 0:
            raise ValueError("a line longer than a frame (%d)" % FRAME_MAX)
        out.append(data[:cut])
        data = data[cut:]
    if data:
        out.append(data)
    return out


def set_lines(fd: int, dtr: bool, rts: bool):
    """Both modem lines in one TIOCMSET. True = asserted = the CH340's pin LOW."""
    import fcntl, termios                       # Linux: the bench is the Pi
    bits = struct.unpack("I", fcntl.ioctl(fd, termios.TIOCMGET, struct.pack("I", 0)))[0]
    bits &= ~(termios.TIOCM_DTR | termios.TIOCM_RTS)
    bits |= (termios.TIOCM_DTR if dtr else 0) | (termios.TIOCM_RTS if rts else 0)
    fcntl.ioctl(fd, termios.TIOCMSET, struct.pack("I", bits))


class FramedSerial:
    """A pyserial port with frames under it; read()/write()/readline() as a plain port's."""

    def __init__(self, port: str, baud: int | None = None, timeout=0.1, write_timeout=None):
        import serial
        self.ser = serial.Serial(port, baud or link_baud(), timeout=timeout,
                                 write_timeout=write_timeout)
        self.port = port
        self.de = Deframer()
        self.pending = bytearray()

    @property
    def bad(self) -> int:
        return self.de.bad

    @property
    def timeout(self):
        return self.ser.timeout

    @timeout.setter
    def timeout(self, v):
        self.ser.timeout = v

    def write(self, data: bytes) -> int:
        for p in pack_lines(data):
            self.ser.write(encode(p))
        return len(data)

    def _pull(self, block: bool):
        raw = self.ser.read(max(1, self.ser.in_waiting)) if block else self.ser.read(self.ser.in_waiting)
        for p in self.de.feed(raw):
            self.pending += p

    def read(self, n: int = 1) -> bytes:
        """Up to n payload bytes, waiting at most about the port's timeout for the first."""
        end = None if self.ser.timeout is None else time.monotonic() + self.ser.timeout
        while not self.pending:
            self._pull(True)
            if end is not None and time.monotonic() >= end:
                break
        self._pull(False)
        got = bytes(self.pending[:n])
        del self.pending[:n]
        return got

    def readline(self) -> bytes:
        end = None if self.ser.timeout is None else time.monotonic() + self.ser.timeout
        while b"\n" not in self.pending:
            self._pull(True)
            if end is not None and time.monotonic() >= end:
                break
        i = self.pending.find(b"\n") + 1 or len(self.pending)
        got = bytes(self.pending[:i])
        del self.pending[:i]
        return got

    def reset_input_buffer(self):
        self.ser.reset_input_buffer()
        self.de.buf.clear()
        self.pending.clear()

    def reset(self, hold=0.02):
        """Pulse NRST through U7 (DTR# high, RTS# low), BOOT0 left low: the board restarts."""
        set_lines(self.ser.fileno(), dtr=False, rts=True)
        time.sleep(hold)
        set_lines(self.ser.fileno(), dtr=True, rts=True)

    def rom(self, hold=0.05):
        """Restart into WCH's ROM loader: reset, then BOOT0 high (DTR# low, RTS# high) in the
        same ioctl that lets reset go, held while the chip samples it, then both alike."""
        fd = self.ser.fileno()
        set_lines(fd, dtr=False, rts=True)
        time.sleep(0.02)
        set_lines(fd, dtr=True, rts=False)
        time.sleep(hold)
        set_lines(fd, dtr=True, rts=True)

    def close(self):
        self.ser.close()


def _usb_ids(dev: str) -> tuple[str, str] | None:
    try:
        return tuple(open(os.path.join(dev, f)).read().strip() for f in ("idVendor", "idProduct"))
    except OSError:
        return None


def find_r2_port() -> str | None:
    """U7: a CH340 that is not behind a CH334 hub (those are the panel's / optical's bridges).
    MOTOR_PORT in the environment overrides."""
    if os.environ.get("MOTOR_PORT"):
        return os.environ["MOTOR_PORT"]
    for tty in sorted(glob.glob("/sys/class/tty/ttyUSB*")):
        iface = os.path.realpath(tty + "/device/..")      # the USB interface
        dev = os.path.dirname(iface)                       # its device
        if _usb_ids(dev) != CH340:
            continue
        up, hub = os.path.dirname(dev), False
        while re.match(r"(usb\d+|\d+-[\d.]+)$", os.path.basename(up)):         # up to the root hub
            if _usb_ids(up) == HUB:
                hub = True
                break
            up = os.path.dirname(up)
        if not hub:
            return "/dev/" + os.path.basename(tty)
    return None
