"""Write a board's base loader through its MCU's ROM, over its own CH340C: output_panel R2,
optical R2 and motor_ctrl R2, hands-free (cadkit M43). Nothing of ours has to run on the board, so a blank chip
or a broken loader is no obstacle.

    python3 -m publicbench.romflash output_panel build/boot.bin
    python3 -m publicbench.romflash optical build/boot/optical.bin
    python3 -m publicbench.romflash output_panel --port /dev/ttyUSB1 --verify-only build/boot.bin
    python3 -m publicbench.romflash motor_ctrl build/r2/boot.bin     (motorflash --rom calls this)

THE STRAIGHT PAIR (both boards): the bridge's DTR# low lifts BOOT0 (Q7 / Q2), its RTS# low pulls
NRST (D9 / D11). Linux raises DTR# and RTS# on EVERY open of a tty, so any program that opens
the port holds the MCU in reset for as long as it has it -- wchisp included, which is why this
tool speaks the ROM's protocol itself rather than handing the port on (docs/bronner-work-items.md,
output_panel ROM path). It owns both lines from the moment the port opens:
  open    both lines released right after the kernel's raise (pyserial sets DTR, then RTS: BOOT0
          is already falling when NRST lets go, so the open's glitch is a plain reset), and
          HUPCL cleared, so the close leaves them where this tool put them
  rom()   BOOT0 up, NRST down for RESET_S, NRST up with BOOT0 still up, BOOT0 held BOOT_HOLD_S
          while the chip samples it, then released: the chip is in its ROM loader
  run()   NRST down for RESET_S with BOOT0 low, then up: the chip starts what was written

motor_ctrl R2 is the CROSSED pair instead (Q1 / Q2, elec/motor_ctrl.py M19): DTR# low with RTS#
high lifts BOOT0, RTS# low with DTR# high pulls NRST, and both alike do nothing -- so any open is
harmless there. CrossedLines drives it the way frames.FramedSerial.rom() / reset() do.

THE TWO ROMS:
  output_panel  CH32V307 (motor_ctrl's too): WCH's serial ISP, the protocol wchisp speaks (read off its source,
                ch32-rs/wchisp, and written again here: no code of it is in this repo). 57 AB
                cmd len16 payload sum8 out, 55 AA cmd status len16 payload sum8 back; identify,
                read config (UID), key, erase, program and verify in 56-byte XOR-keyed chunks,
                end. 115200 8N1.
  optical       STM32H743: ST's USART bootloader on USART1 PB14 / PB15 (AN2606, AN3155): 0x7F to
                start, 0x79 ACK, extended erase of the sectors the image covers, write and read
                back 256 bytes at a time. 115200 8E1.

⚠ PROVEN IN SIMULATION ONLY (bench/tests/test_romflash.py: both ROMs, the line timing, the
open's glitch). The bench check owed: the real NRST rise through R6 / C54 (R29 / C on optical)
against RESET_S and BOOT_HOLD_S, on a scope or by the ROM simply answering.
"""
from __future__ import annotations

import argparse
import glob
import os
import random
import re
import struct
import sys
import time

from . import frames

RESET_S = 0.02            # NRST held low: R6 10k x C54 100 nF is 1 ms, so 20 is plenty
BOOT_HOLD_S = 0.05        # BOOT0 held up after NRST lets go: the ROM samples it at reset
SETTLE_S = 0.02           # after the hold, before the first byte

# Each board's bridge hangs off its own CH334 hub on a known port: a blank MCU has no USB device
# of its own to find the board by, so the port number is the board's name.
BOARDS = {
    "output_panel": {"rom": "wch", "hub_port": 4},     # J3 -> U4 port 4 -> U17 (M43)
    "optical": {"rom": "st", "hub_port": 2},           # J1 -> U31 DN2 -> U32 (M43)
    "motor_ctrl": {"rom": "wch", "crossed": True},     # J4 -> U7, no hub (frames.find_r2_port)
}


class RomError(RuntimeError):
    pass


# ── the two lines ──────────────────────────────────────────────────────────────────────────────
class Lines:
    """The straight pair. `set(dtr, rts)` drives both in one go (True = asserted = pin LOW =
    BOOT0 up / NRST down); `sleep` is time.sleep, or the simulator's clock."""

    def __init__(self, set_fn, sleep=time.sleep):
        self.set, self.sleep = set_fn, sleep

    def rom(self):
        self.set(True, True)                 # BOOT0 up, NRST down
        self.sleep(RESET_S)
        self.set(True, False)                # NRST up, BOOT0 still up: the ROM
        self.sleep(BOOT_HOLD_S)
        self.set(False, False)               # both released; the ROM stays
        self.sleep(SETTLE_S)

    def run(self):
        self.set(False, True)                # NRST down, BOOT0 low
        self.sleep(RESET_S)
        self.set(False, False)               # the chip starts what is in flash


class CrossedLines(Lines):
    """motor_ctrl R2's pair: BOOT0 up = DTR# asserted alone, NRST down = RTS# asserted alone,
    both alike = rest. The same sequences as frames.FramedSerial.rom() / reset()."""

    def rom(self):
        self.set(False, True)                # NRST down
        self.sleep(RESET_S)
        self.set(True, False)                # NRST up and BOOT0 up, in one go
        self.sleep(BOOT_HOLD_S)
        self.set(True, True)                 # rest; the ROM stays
        self.sleep(SETTLE_S)

    def run(self):
        self.set(False, True)                # NRST down, BOOT0 not lifted
        self.sleep(RESET_S)
        self.set(True, True)


def clear_hupcl(fd: int):
    """The close then leaves DTR# / RTS# where they are, not both raised (Linux, the Pi)."""
    import termios
    a = termios.tcgetattr(fd)
    a[2] &= ~termios.HUPCL
    termios.tcsetattr(fd, termios.TCSANOW, a)


def open_port(path: str, parity: str):
    """The port with both lines released from the first moment pyserial can, and HUPCL off."""
    import serial
    s = serial.Serial()
    s.port, s.baudrate, s.timeout, s.write_timeout = path, 115200, 0.5, 2
    s.parity = serial.PARITY_EVEN if parity == "E" else serial.PARITY_NONE
    s.dtr = s.rts = False                    # applied right after the kernel's raise
    s.open()
    clear_hupcl(s.fileno())
    return s


def find_port(board: str) -> str | None:
    """The CH340 (1a86:7523) behind a CH334 (1a86:8091) on the board's hub port.
    <BOARD>_PORT in the environment overrides (OUTPUT_PANEL_PORT, OPTICAL_PORT)."""
    env = os.environ.get(board.upper() + "_PORT")
    if env:
        return env
    if board == "motor_ctrl":
        return frames.find_r2_port()                    # MOTOR_PORT overrides there
    want = BOARDS[board]["hub_port"]
    for tty in sorted(glob.glob("/sys/class/tty/ttyUSB*")):
        dev = os.path.dirname(os.path.realpath(tty + "/device/.."))
        if frames._usb_ids(dev) != frames.CH340:
            continue
        m = re.search(r"\.(\d+)$", os.path.basename(dev))
        if m and int(m.group(1)) == want and frames._usb_ids(os.path.dirname(dev)) == frames.HUB:
            return "/dev/" + os.path.basename(tty)
    return None


def _read(port, n: int, wait: float) -> bytes:
    end, out = time.monotonic() + wait, b""
    while len(out) < n and time.monotonic() < end:
        out += port.read(n - len(out))
    if len(out) < n:
        raise RomError("the ROM went quiet (%d of %d bytes)" % (len(out), n))
    return out


# ── WCH serial ISP (output_panel's CH32V307) ───────────────────────────────────────────────────
IDENTIFY, ISP_END, ISP_KEY, ERASE, PROGRAM, VERIFY, READ_CONFIG = 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7
CFG_ALL = 0x1F
CHUNK = 56                 # program / verify data per frame
SECTOR = 1024
MIN_SECTORS = 8            # erase at least this many: the CH32V30x's ROM wants it; 8 K never
                           # reaches output_panel's application at 0x8000
WCH_TYPE_V30X = 0x17


def wch_frame(raw: bytes) -> bytes:
    return b"\x57\xab" + raw + bytes([sum(raw) & 0xFF])


class WchIsp:
    def __init__(self, port):
        self.p = port
        self.chip = self.type = None
        self.key = None

    def cmd(self, c: int, payload: bytes, wait=1.0) -> bytes:
        self.p.write(wch_frame(bytes([c]) + struct.pack("<H", len(payload)) + payload))
        if _read(self.p, 2, wait) != b"\x55\xaa":
            raise RomError("WCH ROM: bad reply header")
        head = _read(self.p, 4, wait)
        n = struct.unpack("<H", head[2:4])[0]
        body = _read(self.p, n, wait)
        if _read(self.p, 1, wait)[0] != (sum(head) + sum(body)) & 0xFF:
            raise RomError("WCH ROM: bad reply checksum")
        if head[0] != c:
            raise RomError("WCH ROM: reply to 0x%02X for 0x%02X" % (head[0], c))
        return body

    def identify(self):
        r = self.cmd(IDENTIFY, b"\x00\x00" + b"MCU ISP & WCH.CN")
        self.chip, self.type = r[0], r[1]
        if self.type != WCH_TYPE_V30X:
            raise RomError("WCH ROM: chip 0x%02X type 0x%02X, not a CH32V30x" % (self.chip, self.type))

    def unlock(self):
        cfg = self.cmd(READ_CONFIG, bytes([CFG_ALL, 0]))
        uid = cfg[18:26]
        if len(uid) != 8:
            raise RomError("WCH ROM: no UID in the config (%d bytes)" % len(cfg))
        s = sum(uid) & 0xFF
        self.key = bytes([s] * 7 + [(s + self.chip) & 0xFF])
        r = self.cmd(ISP_KEY, bytes(30))
        if r[0] != sum(self.key) & 0xFF:
            raise RomError("WCH ROM: key refused")

    def erase(self, size: int):
        n = max(MIN_SECTORS, -(-size // SECTOR))
        self.cmd(ERASE, struct.pack("<I", n), wait=5.0)

    def _chunks(self, c: int, img: bytes):
        for a in range(0, len(img), CHUNK):
            d = img[a:a + CHUNK]
            enc = bytes(b ^ self.key[i % 8] for i, b in enumerate(d))
            yield a, self.cmd(c, struct.pack("<IB", a, random.randrange(256)) + enc, wait=1.0)

    def program(self, img: bytes):
        for _a, _r in self._chunks(PROGRAM, img):
            pass
        # an empty write at the end commits the last chunk (wchisp: required)
        self.cmd(PROGRAM, struct.pack("<IB", len(img), random.randrange(256)))

    def verify(self, img: bytes):
        for a, r in self._chunks(VERIFY, img):
            if r[0] != 0:
                raise RomError("WCH ROM: verify differs at 0x%X" % a)

    def end(self):
        self.cmd(ISP_END, b"\x01")


def wch_flash(port, img: bytes, verify_only=False, log=print):
    isp = WchIsp(port)
    isp.identify()
    log("WCH ROM: chip 0x%02X type 0x%02X" % (isp.chip, isp.type))
    isp.unlock()
    if not verify_only:
        isp.erase(len(img))
        isp.program(img)
        log("WCH ROM: %d bytes written" % len(img))
    isp.verify(img)
    log("WCH ROM: verified")
    isp.end()


# ── ST USART bootloader (optical's STM32H743) ──────────────────────────────────────────────────
ACK, NACK = 0x79, 0x1F
ST_GET_ID, ST_READ, ST_WRITE, ST_EXT_ERASE = 0x02, 0x11, 0x31, 0x44
H7_FLASH = 0x08000000
H7_SECTOR = 128 * 1024
H7_PID = 0x450
ST_BLOCK = 256


def _xor(b: bytes) -> int:
    x = 0
    for v in b:
        x ^= v
    return x


class StBoot:
    def __init__(self, port):
        self.p = port

    def ack(self, wait=1.0):
        r = _read(self.p, 1, wait)[0]
        if r != ACK:
            raise RomError("ST ROM: %s" % ("NACK" if r == NACK else "0x%02X, not an ACK" % r))

    def connect(self):
        self.p.write(b"\x7f")
        self.ack()

    def cmd(self, c: int):
        self.p.write(bytes([c, c ^ 0xFF]))
        self.ack()

    def get_id(self) -> int:
        self.cmd(ST_GET_ID)
        n = _read(self.p, 1, 1.0)[0] + 1
        pid = int.from_bytes(_read(self.p, n, 1.0), "big")
        self.ack()
        return pid

    def erase_sectors(self, sectors: list[int]):
        self.cmd(ST_EXT_ERASE)
        body = struct.pack(">H", len(sectors) - 1) + b"".join(struct.pack(">H", s) for s in sectors)
        self.p.write(body + bytes([_xor(body)]))
        self.ack(wait=10.0 * len(sectors))          # a 128 K sector is seconds, worst case

    def _addr(self, a: int):
        b = struct.pack(">I", a)
        self.p.write(b + bytes([_xor(b)]))
        self.ack()

    def write(self, a: int, data: bytes):
        self.cmd(ST_WRITE)
        self._addr(a)
        body = bytes([len(data) - 1]) + data
        self.p.write(body + bytes([_xor(body)]))
        self.ack(wait=2.0)

    def read(self, a: int, n: int) -> bytes:
        self.cmd(ST_READ)
        self._addr(a)
        self.p.write(bytes([n - 1, (n - 1) ^ 0xFF]))
        self.ack()
        return _read(self.p, n, 2.0)


def st_flash(port, img: bytes, verify_only=False, log=print):
    st = StBoot(port)
    st.connect()
    pid = st.get_id()
    if pid != H7_PID:
        raise RomError("ST ROM: product 0x%03X, not an STM32H74x (0x450)" % pid)
    log("ST ROM: STM32H74x")
    # the H7 writes whole 32-byte flash words: pad the image to one with erased bytes
    img = img + b"\xff" * (-len(img) % 32)
    if not verify_only:
        st.erase_sectors(list(range(-(-len(img) // H7_SECTOR))))
        for a in range(0, len(img), ST_BLOCK):
            st.write(H7_FLASH + a, img[a:a + ST_BLOCK])
        log("ST ROM: %d bytes written" % len(img))
    for a in range(0, len(img), ST_BLOCK):
        n = min(ST_BLOCK, len(img) - a)
        if st.read(H7_FLASH + a, n) != img[a:a + n]:
            raise RomError("ST ROM: verify differs in 0x%X..0x%X" % (H7_FLASH + a, H7_FLASH + a + n))
    log("ST ROM: verified")


# ── the whole job ──────────────────────────────────────────────────────────────────────────────
def flash(board: str, port, lines: Lines, img: bytes, verify_only=False, log=print):
    """Into the ROM, write and verify, then out of it with BOOT0 low. The lines are put back to
    a plain run even when the write fails, so the board is never left held in reset or in ROM."""
    lines.rom()
    try:
        (wch_flash if BOARDS[board]["rom"] == "wch" else st_flash)(port, img, verify_only, log)
    finally:
        lines.run()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("board", choices=sorted(BOARDS))
    ap.add_argument("image", help="the .bin (never the .elf): the board's base loader")
    ap.add_argument("--port", help="the bridge's tty; default: found by its hub port")
    ap.add_argument("--verify-only", action="store_true", help="compare, write nothing")
    a = ap.parse_args(argv)
    img = open(a.image, "rb").read()
    path = a.port or find_port(a.board)
    if not path:
        raise SystemExit("no %s bridge found: is the board powered and its USB lead in? "
                         "(or --port / %s_PORT)" % (a.board, a.board.upper()))
    s = open_port(path, "N" if BOARDS[a.board]["rom"] == "wch" else "E")
    try:
        kind = CrossedLines if BOARDS[a.board].get("crossed") else Lines
        lines = kind(lambda dtr, rts: frames.set_lines(s.fileno(), dtr, rts))
        flash(a.board, s, lines, img, a.verify_only)
    except RomError as e:
        raise SystemExit("%s: %s" % (a.board, e))
    finally:
        s.close()                            # HUPCL is off: the lines stay released
    print("%s: done; it is running what was written" % a.board)


if __name__ == "__main__":
    sys.exit(main())
